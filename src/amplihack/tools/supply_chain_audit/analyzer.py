# File: src/amplihack/tools/supply_chain_audit/analyzer.py
"""Core analysis engine for supply chain audit.

Dispatches per-vector analysis (Actions SHA/tag, PyPI version),
scans logs for IOCs, and computes three-tier verdicts with confidence.
"""

from __future__ import annotations

import fnmatch
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from .github_client import GitHubClient
from .models import (
    Advisory,
    AuditReport,
    Evidence,
    IOCMatch,
    RepoVerdict,
)

logger = logging.getLogger(__name__)


class Analyzer:
    """Supply chain audit analysis engine."""

    MAX_LOG_SIZE = 50 * 1024 * 1024  # 50 MB — truncate beyond this to prevent OOM

    def __init__(
        self,
        github_client: GitHubClient | None = None,
        max_workers: int = 4,
    ) -> None:
        self.github_client = github_client or GitHubClient()
        self.max_workers = max(1, max_workers)

    # -----------------------------------------------------------------------
    # Workflow Reference Analysis (Actions vector)
    # -----------------------------------------------------------------------

    def analyze_workflow_reference(
        self, workflow_content: str, advisory: Advisory
    ) -> list[Evidence]:
        """Analyze a workflow file for references to the advisory's package.

        Returns list of Evidence for each reference found.
        """
        evidence: list[Evidence] = []
        package = advisory.package_name

        # Find all uses: <package>@<ref> patterns
        pattern = re.compile(rf"uses:\s*{re.escape(package)}@(\S+)", re.IGNORECASE)
        matches = pattern.findall(workflow_content)

        if not matches:
            evidence.append(
                Evidence(
                    type="no_reference",
                    detail=f"Workflow does not reference {package}",
                    signal="safe",
                )
            )
            return evidence

        # O(1) set lookups instead of O(n) list scans
        safe_sha_set = frozenset(advisory.safe_shas) if advisory.safe_shas else frozenset()
        compromised_set = frozenset(advisory.compromised_versions)

        for ref in matches:
            # SHA pin: 7+ char hex string (full or abbreviated SHA)
            if re.match(r"^[0-9a-f]{7,40}$", ref):
                if ref in safe_sha_set:
                    evidence.append(
                        Evidence(
                            type="sha_pinned",
                            detail=f"Pinned to known-safe SHA: {ref}",
                            signal="safe",
                        )
                    )
                else:
                    evidence.append(
                        Evidence(
                            type="sha_pinned",
                            detail=f"Pinned to SHA: {ref} (not verified against advisory)",
                            signal="unknown",
                        )
                    )
            # Non-hex but in safe_shas (some actions use non-hex refs)
            elif ref in safe_sha_set:
                evidence.append(
                    Evidence(
                        type="sha_pinned",
                        detail=f"Pinned to known-safe ref: {ref}",
                        signal="safe",
                    )
                )
            else:
                # Tag or branch reference (mutable)
                if ref in compromised_set:
                    evidence.append(
                        Evidence(
                            type="tag_reference",
                            detail=f"References compromised tag: {ref}",
                            signal="risk",
                        )
                    )
                else:
                    evidence.append(
                        Evidence(
                            type="tag_reference",
                            detail=f"References mutable tag: {ref}",
                            signal="risk",
                        )
                    )

        return evidence

    # -----------------------------------------------------------------------
    # Lockfile Reference Analysis (PyPI vector)
    # -----------------------------------------------------------------------

    def analyze_lockfile_reference(
        self, lockfile_content: str, advisory: Advisory
    ) -> list[Evidence]:
        """Analyze lockfile/requirements for references to the advisory's package.

        Returns list of Evidence for version pinning status.
        """
        evidence: list[Evidence] = []
        package = advisory.package_name.lower()

        # Check for exact version pins: package==version
        pin_pattern = re.compile(rf"^{re.escape(package)}==([^\s,]+)", re.MULTILINE | re.IGNORECASE)
        pin_matches = pin_pattern.findall(lockfile_content)

        # Check for unpinned refs: package>=version, package~=version, etc.
        unpin_pattern = re.compile(
            rf"^{re.escape(package)}[><=~!]+[^\s,]+", re.MULTILINE | re.IGNORECASE
        )
        unpin_matches = unpin_pattern.findall(lockfile_content)
        # Filter out exact pins from unpinned matches
        exact_pins = {f"{package}=={v}" for v in pin_matches}
        unpin_matches = [m for m in unpin_matches if m.lower() not in exact_pins]

        if not pin_matches and not unpin_matches:
            # Package not mentioned at all
            if package not in lockfile_content.lower():
                evidence.append(
                    Evidence(
                        type="no_reference",
                        detail=f"Lockfile does not reference {advisory.package_name}",
                        signal="safe",
                    )
                )
                return evidence

        for version in pin_matches:
            if version in advisory.compromised_versions:
                evidence.append(
                    Evidence(
                        type="compromised_install",
                        detail=f"Pinned to compromised version: {version}",
                        signal="compromised",
                    )
                )
            elif advisory.safe_versions and version in advisory.safe_versions:
                evidence.append(
                    Evidence(
                        type="version_pinned",
                        detail=f"Pinned to known-safe version: {version}",
                        signal="safe",
                    )
                )
            else:
                evidence.append(
                    Evidence(
                        type="version_pinned",
                        detail=f"Pinned to version: {version}",
                        signal="safe",
                    )
                )

        if unpin_matches:
            for ref in unpin_matches:
                evidence.append(
                    Evidence(
                        type="version_unpinned",
                        detail=f"Unpinned version specifier: {ref}",
                        signal="risk",
                    )
                )

        return evidence

    # -----------------------------------------------------------------------
    # IOC Scanning
    # -----------------------------------------------------------------------

    def scan_for_iocs(
        self, log_content: str | None, advisory: Advisory, run_id: int
    ) -> list[IOCMatch]:
        """Scan log content for IOC patterns from the advisory.

        Returns list of IOCMatch for each found indicator.
        """
        if not log_content:
            return []

        iocs = advisory.iocs
        if iocs.is_empty():
            return []

        matches: list[IOCMatch] = []

        # Pre-build combined regex for fast line-level rejection.
        # Lines not matching any IOC literal are skipped entirely.
        all_literals: list[str] = []
        all_literals.extend(iocs.domains)
        all_literals.extend(iocs.ips)
        for fp in iocs.file_patterns:
            all_literals.append(fp.lstrip("*"))
        escaped = [re.escape(lit) for lit in all_literals if lit]
        quick_re = re.compile("|".join(escaped)) if escaped else None

        # Pre-extract file pattern literals for substring pre-check
        file_literals = [(fp, fp.lstrip("*")) for fp in iocs.file_patterns]

        for line in log_content.split("\n"):
            # Fast reject: skip lines with no IOC substring
            if quick_re and not quick_re.search(line):
                continue

            stripped = line.strip()

            for domain in iocs.domains:
                if domain in line:
                    matches.append(
                        IOCMatch(
                            ioc_type="domain",
                            pattern=domain,
                            found_in="run_log",
                            run_id=run_id,
                            line=stripped,
                        )
                    )

            for ip in iocs.ips:
                if ip in line:
                    matches.append(
                        IOCMatch(
                            ioc_type="ip",
                            pattern=ip,
                            found_in="run_log",
                            run_id=run_id,
                            line=stripped,
                        )
                    )

            for file_pat, literal in file_literals:
                # Check cheap literal substring first, fall back to fnmatch
                if literal in line or fnmatch.fnmatch(stripped, f"*{file_pat}*"):
                    matches.append(
                        IOCMatch(
                            ioc_type="file_pattern",
                            pattern=file_pat,
                            found_in="run_log",
                            run_id=run_id,
                            line=stripped,
                        )
                    )

        return matches

    # -----------------------------------------------------------------------
    # Install Log Analysis
    # -----------------------------------------------------------------------

    def analyze_install_log(
        self, log_content: str, advisory: Advisory, run_id: int
    ) -> list[Evidence]:
        """Analyze CI pip install logs for compromised version downloads.

        Returns list of Evidence for install-related signals.
        """
        evidence: list[Evidence] = []
        package = advisory.package_name.lower()

        # Pre-build and pre-lowercase pattern groups (avoid per-line allocation)
        compromised_groups: list[tuple[str, list[str]]] = []
        for version in advisory.compromised_versions:
            pats = [
                f"{package}-{version}".lower(),
                f"{package}=={version}".lower(),
                f"installed {package}-{version}".lower(),
                f"downloading {package}-{version}".lower(),
                f"collecting {package}=={version}".lower(),
            ]
            compromised_groups.append((version, pats))

        safe_groups: list[tuple[str, list[str]]] = []
        for version in advisory.safe_versions:
            pats = [
                f"{package}-{version}".lower(),
                f"{package}=={version}".lower(),
                f"installed {package}-{version}".lower(),
            ]
            safe_groups.append((version, pats))

        for line in log_content.split("\n"):
            line_lower = line.lower()

            # Fast pre-filter: skip lines that don't mention the package
            if package not in line_lower:
                continue

            # Check for compromised version installs
            for version, pats in compromised_groups:
                for pat in pats:
                    if pat in line_lower:
                        evidence.append(
                            Evidence(
                                type="compromised_install",
                                detail=f"Compromised version {version} found in log: {line.strip()}",
                                signal="compromised",
                            )
                        )
                        break

            # Check for safe version installs
            for version, pats in safe_groups:
                for pat in pats:
                    if pat in line_lower:
                        evidence.append(
                            Evidence(
                                type="version_pinned",
                                detail=f"Safe version {version} found in log: {line.strip()}",
                                signal="safe",
                            )
                        )
                        break

            # Check for cache usage
            if "using cached" in line_lower:
                evidence.append(
                    Evidence(
                        type="cache_used",
                        detail=f"Cached package used: {line.strip()}",
                        signal="safe",
                    )
                )

        return evidence

    # -----------------------------------------------------------------------
    # Verdict Computation
    # -----------------------------------------------------------------------

    def compute_verdict(
        self,
        evidence: list[Evidence],
        ioc_matches: list[IOCMatch],
    ) -> tuple[str, str]:
        """Compute three-tier verdict with confidence from evidence.

        Returns:
            (verdict, confidence) tuple.
            verdict: SAFE | COMPROMISED | INCONCLUSIVE
            confidence: HIGH | MEDIUM | LOW
        """
        if not evidence and not ioc_matches:
            return "INCONCLUSIVE", "LOW"

        signals = [e.signal for e in evidence]
        has_compromised = "compromised" in signals or len(ioc_matches) > 0
        has_risk = "risk" in signals
        has_unknown = "unknown" in signals
        safe_count = signals.count("safe")

        if has_compromised:
            compromised_count = signals.count("compromised") + len(ioc_matches)
            if compromised_count >= 2:
                return "COMPROMISED", "HIGH"
            return "COMPROMISED", "MEDIUM"

        if has_risk or has_unknown:
            return "INCONCLUSIVE", "MEDIUM"

        # All signals are safe
        if safe_count >= 3:
            return "SAFE", "HIGH"
        if safe_count >= 1:
            return "SAFE", "MEDIUM"

        return "INCONCLUSIVE", "LOW"

    # -----------------------------------------------------------------------
    # Per-Run Analysis (extracted for parallel execution)
    # -----------------------------------------------------------------------

    def _analyze_single_run(
        self,
        repo: str,
        run_data: dict,
        advisory: Advisory,
    ) -> tuple[list[Evidence], list[IOCMatch]]:
        """Analyze a single workflow run: fetch log, scan IOCs, check installs.

        Thread-safe — operates on independent data per run.
        """
        run_id = run_data.get("databaseId") if "databaseId" in run_data else run_data.get("id")
        if run_id is None:
            raise ValueError(f"Workflow run data missing both 'databaseId' and 'id': {run_data!r}")
        evidence: list[Evidence] = []
        ioc_matches: list[IOCMatch] = []

        try:
            log_content = self.github_client.get_run_logs(repo, run_id)
            if not log_content:
                evidence.append(
                    Evidence(
                        type="no_logs",
                        detail=f"No logs available for run {run_id}",
                        signal="unknown",
                    )
                )
                return evidence, ioc_matches

            # Truncate oversized logs to prevent OOM
            if len(log_content) > self.MAX_LOG_SIZE:
                logger.warning(
                    "Log for run %s truncated from %d to %d bytes",
                    run_id,
                    len(log_content),
                    self.MAX_LOG_SIZE,
                )
                log_content = log_content[: self.MAX_LOG_SIZE]

            # Scan for IOCs
            ioc_hits = self.scan_for_iocs(log_content, advisory, run_id)
            ioc_matches.extend(ioc_hits)
            for hit in ioc_hits:
                evidence.append(
                    Evidence(
                        type="ioc_match",
                        detail=f"IOC found: {hit.pattern} in run {run_id}",
                        signal="compromised",
                    )
                )

            # Analyze install logs for PyPI vector
            if advisory.attack_vector == "pypi":
                install_evidence = self.analyze_install_log(log_content, advisory, run_id)
                evidence.extend(install_evidence)

        except Exception as e:
            logger.warning("Failed to analyze run %s: %s", run_id, e)
            evidence.append(
                Evidence(
                    type="analysis_error",
                    detail=f"Failed to analyze run {run_id}: {e}",
                    signal="unknown",
                )
            )

        return evidence, ioc_matches

    # -----------------------------------------------------------------------
    # Per-Repo Analysis
    # -----------------------------------------------------------------------

    def analyze_repo(self, repo: str, advisory: Advisory, max_runs: int = 100) -> RepoVerdict:
        """Run full analysis on a single repository."""
        all_evidence: list[Evidence] = []
        all_ioc_matches: list[IOCMatch] = []

        # Get workflow files
        try:
            workflow_files = self.github_client.get_workflow_files(repo)
        except Exception as e:
            logger.warning("Failed to list workflow files for %s: %s", repo, e)
            workflow_files = []
            all_evidence.append(
                Evidence(
                    type="api_error",
                    detail=f"Failed to list workflow files for {repo}: {e}",
                    signal="unknown",
                )
            )

        has_reference = False

        for wf in workflow_files:
            path = wf.get("path", "") if isinstance(wf, dict) else str(wf)
            try:
                content = self.github_client.get_workflow_file_content(repo, path)
                ref_evidence = self.analyze_workflow_reference(content, advisory)
                if not any(e.type == "no_reference" for e in ref_evidence):
                    has_reference = True
                all_evidence.extend(ref_evidence)
            except Exception as e:
                logger.warning("Failed to read workflow %s: %s", path, e)

        # Get workflow runs during exposure window
        start_str = advisory.exposure_window_start.strftime("%Y-%m-%d")
        end_str = advisory.exposure_window_end.strftime("%Y-%m-%d")

        try:
            runs = self.github_client.get_workflow_runs(
                repo,
                created_after=start_str,
                created_before=end_str,
                max_runs=max_runs,
            )
        except Exception as e:
            logger.warning("Failed to get workflow runs for %s: %s", repo, e)
            runs = []

        # Parallel log fetch + analysis (I/O-bound subprocess calls)
        workers = min(self.max_workers, len(runs)) if runs else 1
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(self._analyze_single_run, repo, run, advisory) for run in runs]
            for future in futures:
                run_ev, run_iocs = future.result()
                all_evidence.extend(run_ev)
                all_ioc_matches.extend(run_iocs)
        runs_analyzed = len(runs)

        # If no workflow files reference the package, it's safe
        if not has_reference and not workflow_files:
            all_evidence.append(
                Evidence(
                    type="no_reference",
                    detail=f"Repository does not reference {advisory.package_name}",
                    signal="safe",
                )
            )

        verdict, confidence = self.compute_verdict(all_evidence, all_ioc_matches)

        return RepoVerdict(
            repo=repo,
            verdict=verdict,
            confidence=confidence,
            evidence=all_evidence,
            workflow_runs_analyzed=runs_analyzed,
            ioc_matches=all_ioc_matches,
        )

    # -----------------------------------------------------------------------
    # Multi-Repo Audit
    # -----------------------------------------------------------------------

    def audit(
        self,
        advisory: Advisory,
        repos: list[str],
        max_runs: int = 100,
    ) -> AuditReport:
        """Run audit across multiple repos for a single advisory.

        Args:
            advisory: The advisory to audit against.
            repos: List of repo names (owner/repo format).
            max_runs: Maximum workflow runs to analyze per repo.

        Returns:
            AuditReport with per-repo verdicts and summary.
        """
        verdicts: list[RepoVerdict] = []

        # Parallel repo analysis (each repo is independent I/O work)
        workers = min(self.max_workers, len(repos)) if repos else 1
        with ThreadPoolExecutor(max_workers=workers) as pool:
            # pool.map preserves input order
            verdicts = list(
                pool.map(
                    lambda repo: self.analyze_repo(repo, advisory, max_runs=max_runs),
                    repos,
                )
            )

        summary = {
            "safe": sum(1 for v in verdicts if v.verdict == "SAFE"),
            "compromised": sum(1 for v in verdicts if v.verdict == "COMPROMISED"),
            "inconclusive": sum(1 for v in verdicts if v.verdict == "INCONCLUSIVE"),
        }

        return AuditReport(
            advisory_id=advisory.id,
            advisory_title=advisory.title,
            scan_timestamp=datetime.now(UTC),
            repos_scanned=len(repos),
            summary=summary,
            verdicts=verdicts,
        )
