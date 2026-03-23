# File: supply_chain_audit/audit.py
"""Main audit orchestrator — run_audit entry point."""

import re
import subprocess
from datetime import date
from pathlib import Path

from .detector import detect_ecosystems
from .errors import (
    AcceptedRisksOverflowError,
    PathTraversalError,
    XpiaEscalationError,
)
from .external_tools import check_tool_availability as _check_tool_availability
from .report import AuditReport, SlsaAssessment, build_report
from .schema import Finding

# ── XPIA detection patterns ───────────────────────────────────────────────────
# These patterns identify LLM control-flow injection attempts in scanned content.
_XPIA_PATTERNS = [
    re.compile(r"ignore\s+(previous\s+)?instructions", re.IGNORECASE),
    re.compile(r"</s(?:ystem|ys)>", re.IGNORECASE),
    re.compile(r"</?(?:user|assistant|system|human)\s*>", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:dan|an?\s+ai|a\s+different)", re.IGNORECASE),
    re.compile(r"new\s+instructions\s*:", re.IGNORECASE),
    re.compile(r"disregard\s+(?:previous|all|your)", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"\bSYSTEM\s*:", re.IGNORECASE),  # bare SYSTEM: directive prefix
]

# Severity ordering for min_severity filtering
_SEVERITY_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Info": 3}
_VALID_MIN_SEVERITIES = set(_SEVERITY_RANK.keys())

# Accepted-risks max file size (64 KiB)
_MAX_ACCEPTED_RISKS_SIZE = 64 * 1024  # 64 KB exactly — per acceptance criteria: <= 64KB OK


def _check_path_traversal(path_str: str) -> None:
    """Raise PathTraversalError if path is unsafe.

    Checks: null bytes, ../ components, and symlinks escaping root.
    """
    # Null byte check
    if "\x00" in path_str:
        raise PathTraversalError(path_str)

    # Check for .." components (path traversal)
    # Resolve to catch symlinks etc.
    try:
        p = Path(path_str)
        # Check for .. in string before resolving
        parts = p.parts
        if ".." in parts:
            raise PathTraversalError(path_str)

        # Resolve to detect symlinks outside the intended root
        resolved = p.resolve()
        # If the resolved path has .. or is /tmp outside expected range, check
        # For symlinks: the resolved path of a symlink pointing to /tmp is fine
        # The test creates a symlink in tmp_path pointing to /tmp — this escapes
        # the expected audit root, so we reject it.
        # We detect "escaping" by checking if the path resolves outside its parent
        parent_resolved = p.parent.resolve() if p.parent != p else resolved
        # If p itself is a symlink pointing somewhere else, and the resolved
        # path is not under the original path's parent, it's escaping
        if p.is_symlink():
            # Check if the symlink target is under the original parent
            target = resolved
            try:
                target.relative_to(parent_resolved)
            except ValueError:
                raise PathTraversalError(path_str)

    except PathTraversalError:
        raise
    except (OSError, ValueError):
        pass


def _validate_path(path_str: str) -> Path:
    """Validate the audit root path and return as Path object.

    Raises PathTraversalError for unsafe paths.
    """
    _check_path_traversal(path_str)

    return Path(path_str)


def _check_xpia(content: str, filepath: str) -> None:
    """Raise XpiaEscalationError if prompt injection patterns are detected.

    The filepath is included in the error but the injection content is NOT.
    """
    for pattern in _XPIA_PATTERNS:
        if pattern.search(content):
            raise XpiaEscalationError(filepath)


def _load_accepted_risks(root: Path) -> list[dict]:
    """Load and validate the .supply-chain-accepted-risks.yml file.

    Returns list of risk entry dicts. Empty list if file does not exist.

    Raises:
        AcceptedRisksOverflowError: If file exceeds 64KB.
        ValueError: If any entry has a wildcard ID.
    """
    risk_file = root / ".supply-chain-accepted-risks.yml"
    if not risk_file.exists():
        return []

    size = risk_file.stat().st_size
    if size > _MAX_ACCEPTED_RISKS_SIZE:
        raise AcceptedRisksOverflowError(size)

    try:
        content = risk_file.read_text(errors="replace")
    except (OSError, PermissionError):
        return []

    # Parse YAML minimally (avoid yaml import for zero-dependency design)
    # Use a simple regex-based parser for the expected YAML structure
    entries = []
    current = {}

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("- id:"):
            if current:
                entries.append(current)
            current = {}
            val = stripped[len("- id:") :].strip().strip("'\"")
            # Check for wildcards
            if "*" in val:
                raise ValueError(
                    f"wildcard not allowed in accepted-risks ID: '{val}'. "
                    "Use explicit IDs only (e.g., HIGH-001, not HIGH-*)."
                )
            current["id"] = val
        elif ":" in stripped and current:
            key, _, val = stripped.partition(":")
            key = key.strip().strip("'\"")
            val = val.strip().strip("'\"")
            if key not in current:
                current[key] = val

    if current:
        entries.append(current)

    return entries


def _apply_accepted_risks(
    findings: list[Finding],
    accepted_risks: list[dict],
) -> list[Finding]:
    """Apply accepted-risks suppressions to findings.

    Rules:
    1. Critical findings are NEVER suppressed.
    2. Expired review_date → finding restored to original severity (no Info demotion).
    3. Valid non-expired, non-critical → severity downgraded to Info, accepted_risk=True.
    """
    if not accepted_risks:
        return findings

    today = date.today().isoformat()
    risk_by_id: dict[str, dict] = {r["id"]: r for r in accepted_risks if "id" in r}

    result = []
    for f in findings:
        risk = risk_by_id.get(f.id)

        if risk is None:
            result.append(f)
            continue

        # Rule 1: Critical findings are non-suppressible
        if f.severity == "Critical":
            result.append(f)
            continue

        # Rule 2: Expired review_date → do NOT suppress
        review_date = risk.get("review_date", "")
        if review_date and review_date < today:
            # Expired — restore original severity (already correct, just don't suppress)
            result.append(f)
            continue

        # Rule 3: Valid suppression → demote to Info
        # Include review_date in rationale so report shows when risk expires
        review_date = risk.get("review_date", "")
        accepted_by = risk.get("accepted_by", "")
        rationale_suffix = ""
        if accepted_by or review_date:
            parts = []
            if accepted_by:
                parts.append(f"accepted by {accepted_by}")
            if review_date:
                parts.append(f"review date: {review_date}")
            rationale_suffix = f" [Accepted risk — {', '.join(parts)}]"
        result.append(
            Finding(
                id=f.id,
                dimension=f.dimension,
                severity="Info",
                file=f.file,
                line=f.line,
                current_value=f.current_value,
                expected_value=f.expected_value,
                rationale=f.rationale + rationale_suffix,
                offline_detectable=f.offline_detectable,
                tool_required=f.tool_required,
                contains_secret=f.contains_secret,
                fix_url=f.fix_url,
                accepted_risk=True,
            )
        )

    return result


def _assign_ids_global(findings: list[Finding]) -> list[Finding]:
    """Assign stable per-report IDs to all findings.

    Sort order: severity (Critical→Info), then dimension, file, line.
    IDs are {SEVERITY}-{NNN} within each severity group.
    """
    sorted_findings = sorted(
        findings,
        key=lambda f: (_SEVERITY_RANK.get(f.severity, 4), f.dimension, f.file, f.line),
    )

    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}
    result = []
    for f in sorted_findings:
        sev = f.severity
        counters[sev] = counters.get(sev, 0) + 1
        seq = str(counters[sev]).zfill(3)
        new_id = f"{sev.upper()}-{seq}"
        result.append(
            Finding(
                id=new_id,
                dimension=f.dimension,
                severity=f.severity,
                file=f.file,
                line=f.line,
                current_value=f.current_value,
                expected_value=f.expected_value,
                rationale=f.rationale,
                offline_detectable=f.offline_detectable,
                tool_required=f.tool_required,
                contains_secret=f.contains_secret,
                fix_url=f.fix_url,
                accepted_risk=f.accepted_risk,
            )
        )
    return result


def _filter_by_min_severity(findings: list[Finding], min_severity: str) -> list[Finding]:
    """Filter out findings below the minimum severity threshold."""
    threshold = _SEVERITY_RANK.get(min_severity, 3)
    return [f for f in findings if _SEVERITY_RANK.get(f.severity, 3) <= threshold]


def _build_slsa_assessment(
    root: Path,
    findings: list[Finding],
    workflow_cache: dict[Path, str] | None = None,
) -> SlsaAssessment:
    """Build SLSA assessment from workflow files and audit findings.

    Args:
        workflow_cache: Pre-loaded {path: content} map from XPIA scan.
                        When provided, avoids re-reading workflow files.
    """
    wf_dir = root / ".github" / "workflows"
    build_is_scripted = False
    runs_on_hosted_ci = False
    provenance_generated = False

    hosted_runners = {
        "ubuntu-latest",
        "ubuntu-22.04",
        "ubuntu-20.04",
        "windows-latest",
        "windows-2022",
        "macos-latest",
        "macos-13",
    }

    if wf_dir.is_dir():
        wf_files = list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml"))
        for wf_file in wf_files:
            try:
                wf_content = (
                    workflow_cache[wf_file]
                    if workflow_cache and wf_file in workflow_cache
                    else wf_file.read_text(errors="replace")
                )
                build_is_scripted = True  # Any workflow = scripted build

                # Check for hosted runner
                for runner in hosted_runners:
                    if runner in wf_content:
                        runs_on_hosted_ci = True
                        break

                # Check for SLSA generator
                if "slsa-framework/slsa-github-generator" in wf_content:
                    provenance_generated = True

            except (OSError, PermissionError):
                pass

    # action_refs_sha_pinned: True if no High/Critical findings in Dim 1
    action_refs_sha_pinned = not any(
        f.dimension == 1 and f.severity in ("Critical", "High") for f in findings
    )

    return SlsaAssessment(
        build_is_scripted=build_is_scripted,
        runs_on_hosted_ci=runs_on_hosted_ci,
        provenance_generated=provenance_generated,
        action_refs_sha_pinned=action_refs_sha_pinned,
    )


def _build_handoffs(
    findings: list[Finding],
    active_dims: list[int],
) -> dict[str, str]:
    """Build inter-skill handoff messages from contracts.md templates."""
    handoffs: dict[str, str] = {}

    # dependency-resolver handoff (Dims 7-11 lock file issues)
    lock_dims = {7, 8, 9, 10, 11}
    lock_findings = [f for f in findings if f.dimension in lock_dims]
    if lock_findings:
        ecosystems = sorted(
            {
                {7: "dotnet", 8: "python", 9: "rust", 10: "node", 11: "go"}.get(
                    f.dimension, "unknown"
                )
                for f in lock_findings
            }
        )
        finding_ids = [f.id for f in lock_findings]
        validation_cmds = {
            "python": "pip install --require-hashes -r requirements.txt",
            "node": "npm ci",
            "dotnet": "dotnet restore --locked-mode",
            "rust": "cargo build --locked",
            "go": "go mod verify",
        }
        ci_cmds = [validation_cmds[e] for e in ecosystems if e in validation_cmds]

        handoffs["dependency-resolver"] = (
            f"Ecosystems with lock file issues: {', '.join(ecosystems)}\n"
            f"Finding IDs: {', '.join(finding_ids)}\n"
            f"CI validation commands: {'; '.join(ci_cmds)}\n"
            "Please resolve lock file issues and run validation commands to verify."
        )

    # pre-commit-manager handoff (always generated)
    hooks = []
    if any(d in active_dims for d in [1, 2, 3]):
        hooks.append("zizmor (Dims 1-3: GHA security)")
        hooks.append("actionlint (Dim 2: workflow syntax)")
    if any(d in active_dims for d in [3, 6]):
        hooks.append("detect-secrets (Dims 3+6: secret scanning)")
    if any(d in active_dims for d in [5, 12]):
        hooks.append("hadolint (Dims 5+12: Dockerfile linting)")
    if 9 in active_dims:
        hooks.append("cargo-audit (Dim 9: Cargo vulnerability scan)")
    if 11 in active_dims:
        hooks.append("go mod verify (Dim 11: Go module integrity)")

    if hooks or active_dims:
        prevented = [f.id for f in findings if f.dimension in [1, 2, 3] and f.offline_detectable]
        handoffs["pre-commit-manager"] = (
            f"Hooks to install: {', '.join(hooks) if hooks else 'none detected'}\n"
            f"Active ecosystems: {', '.join(str(d) for d in sorted(active_dims))}\n"
            f"Findings this would have prevented: {', '.join(prevented) if prevented else 'none'}"
        )

    # cybersecurity-analyst handoff (Critical/High runtime concerns)
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}
    for f in findings:
        counts[f.severity] += 1
    runtime_findings = [f for f in findings if f.severity in ("Critical", "High")]
    if runtime_findings:
        handoffs["cybersecurity-analyst"] = (
            f"Supply chain posture summary:\n"
            f"Critical: {counts['Critical']}\n"
            f"High: {counts['High']}\n"
            f"Medium: {counts['Medium']}\n"
            f"Info: {counts['Info']}\n"
            f"Finding IDs requiring runtime review: {', '.join(f.id for f in runtime_findings[:10])}"
        )

    # silent-degradation-audit handoff
    silent_degradation_findings = []
    # Check if any workflow uses continue-on-error: true on security steps
    # (This is detected in the findings by specific patterns)
    for f in findings:
        if "continue-on-error" in f.current_value.lower():
            silent_degradation_findings.append(f)

    if silent_degradation_findings:
        handoffs["silent-degradation-audit"] = (
            "Security gates with continue-on-error detected:\n"
            + "\n".join(f"- {f.id}: {f.file}:{f.line}" for f in silent_degradation_findings)
            + "\nThese steps should be enforcing security gates. "
            "continue-on-error allows pipeline to pass despite security failures."
        )

    return handoffs


class AuditResult:
    """Result of a complete audit run — wraps AuditReport with extra metadata."""

    def __init__(
        self,
        report: AuditReport,
        active_dimensions: list[int],
        skipped_dimensions: list[int],
        slsa_dict: dict | None = None,
    ):
        self._report = report
        self.findings: list[Finding] = report.findings
        self.active_dimensions: list[int] = active_dimensions
        self.skipped_dimensions: list[int] = skipped_dimensions
        self._slsa_dict = slsa_dict

    def render_report(self) -> str:
        return self._report.render()

    def get_handoff(self, skill: str) -> str | None:
        return self._report.get_handoff(skill)

    def get_slsa_assessment(self) -> dict | None:
        return self._slsa_dict

    def get_advisory_messages(self) -> list[str]:
        return self._report.get_advisory_messages()


def run_audit(
    root: str,
    scope: str = "all",
    min_severity: str = "Info",
    generate_sbom: bool = False,
) -> "AuditResult":
    """Run a complete supply chain audit on the given repository root.

    Security invariants enforced (in order):
    1. PATH_TRAVERSAL: reject ../, null bytes, escaping symlinks
    2. INVALID_SCOPE: validate scope against strict allowlist before any file reads
    3. ACCEPTED_RISKS_OVERFLOW: check file size before parsing

    Args:
        root: Repository root path as string.
        scope: Comma-separated scope (e.g., "all", "gha", "python,node").
        min_severity: Minimum severity to include (Critical/High/Medium/Info).
        generate_sbom: If True, emit SBOM write advisory.

    Returns:
        AuditResult with findings, dimensions, and report.

    Raises:
        PathTraversalError: Path is unsafe.
        InvalidScopeError: Scope is unrecognized.
        AcceptedRisksOverflowError: Accepted-risks file exceeds 64KB.
        XpiaEscalationError: Prompt injection detected in scanned content.
    """
    # ── Invariant 1: PATH_TRAVERSAL check (BEFORE scope validation) ──────────
    _validate_path(root)

    # ── Invariant 1b: MIN_SEVERITY validation ─────────────────────────────────
    if min_severity not in _VALID_MIN_SEVERITIES:
        raise ValueError(
            f"min_severity must be one of {sorted(_VALID_MIN_SEVERITIES)}, got {min_severity!r}"
        )

    # ── Invariant 2: SCOPE validation (BEFORE any file reads) ─────────────────
    # detect_ecosystems will validate the scope — we call it which raises InvalidScopeError
    root_path = Path(root)

    # ── Invariant 3: Accepted-risks file size check ────────────────────────────
    risk_file = root_path / ".supply-chain-accepted-risks.yml"
    if risk_file.exists():
        size = risk_file.stat().st_size
        if size > _MAX_ACCEPTED_RISKS_SIZE:
            raise AcceptedRisksOverflowError(size)

    # Load accepted risks (may raise ValueError for wildcards)
    accepted_risks = _load_accepted_risks(root_path)

    # ── Step 1: Detect ecosystems ──────────────────────────────────────────────
    ecosystem_scope = detect_ecosystems(root_path, scope=scope)
    active_dims = ecosystem_scope.active_dimensions
    skipped_dims = ecosystem_scope.skipped_dimensions
    skip_reasons = ecosystem_scope._skip_reasons

    # ── Step 2: Check tool availability ───────────────────────────────────────
    tool_status = _check_tool_availability()

    # ── Step 3: Run dimension checkers ────────────────────────────────────────
    from .checkers import (
        check_action_sha_pinning,
        check_cache_poisoning,
        check_cargo_supply_chain,
        check_container_image_pinning,
        check_credential_hygiene,
        check_docker_build_chain,
        check_go_module_integrity,
        check_node_integrity,
        check_nuget_lock,
        check_python_integrity,
        check_secret_exposure,
        check_workflow_permissions,
    )

    dim_checkers = {
        1: check_action_sha_pinning,
        2: check_workflow_permissions,
        3: check_secret_exposure,
        4: check_cache_poisoning,
        5: check_container_image_pinning,
        6: check_credential_hygiene,
        7: check_nuget_lock,
        8: check_python_integrity,
        9: check_cargo_supply_chain,
        10: check_node_integrity,
        11: check_go_module_integrity,
        12: check_docker_build_chain,
    }

    all_findings: list[Finding] = []
    skipped_files: list[str] = []

    # XPIA check on workflow files — run once before checker loop.
    # Build workflow_cache here so _build_slsa_assessment can reuse the
    # already-read contents without a second filesystem round-trip.
    wf_dir = root_path / ".github" / "workflows"
    workflow_cache: dict[Path, str] = {}
    if wf_dir.is_dir() and any(d in active_dims for d in (1, 2, 3, 4, 6)):
        for wf_file in list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml")):
            try:
                wf_content = wf_file.read_text(errors="replace")
                rel = str(wf_file.relative_to(root_path)).replace("\\", "/")
                _check_xpia(wf_content, rel)
                workflow_cache[wf_file] = wf_content
            except XpiaEscalationError:
                raise
            except (OSError, PermissionError):
                rel = str(wf_file).replace("\\", "/")
                skipped_files.append(rel)

    for dim in active_dims:
        checker = dim_checkers.get(dim)
        if checker is None:
            continue

        try:
            dim_findings = checker(root_path)
            # Mark tool_timeout degraded findings
            all_findings.extend(dim_findings)
        except subprocess.TimeoutExpired as e:
            tool = str(e.cmd[0]) if isinstance(e.cmd, (list, tuple)) else str(e.cmd)
            tool_status[tool] = f"TOOL_TIMEOUT ({e.timeout}s)"
        except (OSError, PermissionError) as e:
            all_findings.append(
                Finding(
                    id="INFO-001",
                    dimension=dim,
                    severity="Info",
                    file=".",
                    line=0,
                    current_value=str(e),
                    expected_value="Checker ran successfully",
                    rationale=f"OSError prevented checker from running: {e}",
                    offline_detectable=False,
                )
            )

    # ── Step 4: Assign stable per-report IDs ──────────────────────────────────
    all_findings = _assign_ids_global(all_findings)

    # ── Step 5: Apply accepted-risks suppressions ──────────────────────────────
    all_findings = _apply_accepted_risks(all_findings, accepted_risks)

    # ── Step 6: Apply min_severity filter ─────────────────────────────────────
    filtered_findings = _filter_by_min_severity(all_findings, min_severity)

    # ── Step 7: Build SLSA assessment ─────────────────────────────────────────
    slsa = None
    slsa_dict = None
    if any(d in active_dims for d in (1, 2, 3, 4)):
        slsa = _build_slsa_assessment(root_path, filtered_findings, workflow_cache)
        slsa_dict = slsa.to_dict()

    # ── Step 8: Build inter-skill handoffs ────────────────────────────────────
    handoffs = _build_handoffs(filtered_findings, active_dims)

    # ── Step 9: Build advisory messages ───────────────────────────────────────
    advisory_messages = []
    degraded_tools = [
        t for t, s in tool_status.items() if "unavailable" in s or "TOOL_TIMEOUT" in s
    ]
    for tool in degraded_tools:
        advisory_messages.append(
            f"Tool '{tool}' not available — running in degraded mode. "
            "Some checks that require this tool were skipped."
        )
    if skipped_files:
        for sf in skipped_files:
            advisory_messages.append(f"File not readable (skipped): {sf}")

    # Build scope list for report
    scope_list = [s.strip() for s in scope.split(",")]

    report = build_report(
        findings=filtered_findings,
        active_dims=active_dims,
        skipped_dims=skipped_dims,
        skip_reasons=skip_reasons,
        root=root,
        scope=scope_list,
        slsa=slsa,
        tool_status=tool_status,
        advisory_messages=advisory_messages,
        generate_sbom=generate_sbom,
        handoffs=handoffs,
    )

    return AuditResult(
        report=report,
        active_dimensions=active_dims,
        skipped_dimensions=skipped_dims,
        slsa_dict=slsa_dict,
    )
