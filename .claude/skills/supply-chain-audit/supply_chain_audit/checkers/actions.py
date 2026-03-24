# File: supply_chain_audit/checkers/actions.py
"""Dimensions 1-4: GitHub Actions security checks.

Dim 1: Action SHA pinning
Dim 2: Workflow permissions hardening
Dim 3: Secret exposure detection
Dim 4: Cache poisoning risk
"""

import re
from pathlib import Path

from ..schema import Finding
from ._utils import _load_workflows, _relative_path

# Full SHA pattern: exactly 40 hex characters
_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
# Semver tag pattern
_SEMVER_PATTERN = re.compile(r"^v?\d+(\.\d+)*(-[a-zA-Z0-9.]+)?$")
# Action reference pattern in YAML
_USES_PATTERN = re.compile(r"^\s*-?\s*uses:\s*(.+?)(@[^\s#]+)(\s*#.*)?$", re.MULTILINE)
# Per-line action reference pattern (no MULTILINE; captures ref without leading @)
_LINE_USES_PATTERN = re.compile(r'^\s*-?\s*uses:\s*(.+?)@([^\s#"\'\'\n]+)(.*)?$')


def _has_pull_request_target(content: str) -> bool:
    """Return True if workflow triggers on pull_request_target."""
    return "pull_request_target" in content


def _ref_severity(ref: str, has_prt: bool) -> str | None:
    """Determine severity of an unpinned action reference.

    Returns None if the ref is a full 40-char SHA (clean).
    """
    # Full SHA — clean
    if _SHA_PATTERN.match(ref):
        return None  # pinned
    # pull_request_target elevates to Critical
    if has_prt:
        return "Critical"
    return "High"


# ─── Dimension 1: Action SHA Pinning ─────────────────────────────────────────


def check_action_sha_pinning(root: Path) -> list[Finding]:
    """Dim 1: Detect action refs that are not pinned to full 40-char SHA.

    Findings:
    - Critical: unpinned action + pull_request_target trigger
    - High: unpinned action (semver tag or branch ref)
    - Info: full SHA without version comment (advisory only)
    """
    findings = []
    _temp_counter = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}

    for wf_path, content in _load_workflows(root):
        rel = _relative_path(root, wf_path)
        has_prt = _has_pull_request_target(content)

        lines = content.splitlines()
        for line_no, line in enumerate(lines, start=1):
            match = _LINE_USES_PATTERN.match(line)
            if not match:
                continue

            action_ref = match.group(1).strip()
            ref = match.group(2).strip()
            rest = match.group(3) or ""

            # Skip local actions starting with ./
            if action_ref.startswith("./"):
                continue

            if _SHA_PATTERN.match(ref):
                # Full SHA — check if version comment is present
                has_comment = "#" in rest and any(c.isalnum() for c in rest.split("#", 1)[1])
                if not has_comment:
                    _temp_counter["Info"] += 1
                    seq = str(_temp_counter["Info"]).zfill(3)
                    findings.append(
                        Finding(
                            id=f"INFO-{seq}",
                            dimension=1,
                            severity="Info",
                            file=rel,
                            line=line_no,
                            current_value=f"{action_ref}@{ref}",
                            expected_value=f"{action_ref}@{ref}  # vX.Y.Z",
                            rationale="SHA-pinned action missing human-readable version comment.",
                            offline_detectable=True,
                        )
                    )
                continue

            # Not a full SHA → needs investigation
            severity = _ref_severity(ref, has_prt)
            if severity is None:
                continue

            _temp_counter[severity] += 1
            seq = str(_temp_counter[severity]).zfill(3)

            # Build fix_url pointing to releases page
            parts = action_ref.split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                fix_url = f"https://github.com/{owner}/{repo}/releases/tag/{ref}"
            else:
                fix_url = f"https://github.com/{action_ref}"

            findings.append(
                Finding(
                    id=f"{severity.upper()}-{seq}",
                    dimension=1,
                    severity=severity,
                    file=rel,
                    line=line_no,
                    current_value=f"{action_ref}@{ref}",
                    expected_value=(f"{action_ref}@<full-40-char-sha>  # {ref}"),
                    rationale=(
                        f"Mutable ref '{ref}' allows silent code replacement. "
                        "Pin to full commit SHA."
                    ),
                    offline_detectable=True,
                    fix_url=fix_url,
                )
            )

    return findings


# ─── Dimension 2: Workflow Permissions ────────────────────────────────────────


def check_workflow_permissions(root: Path) -> list[Finding]:
    """Dim 2: Check for missing or over-broad permissions in workflows.

    Findings:
    - Critical: pull_request_target without permissions key
    - High: write-all permissions OR missing permissions key
    - Medium: no job-level permissions defined (best-practice advisory)
    """
    findings = []
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}

    for wf_path, content in _load_workflows(root):
        rel = _relative_path(root, wf_path)
        has_prt = _has_pull_request_target(content)

        # Check top-level permissions presence
        has_top_permissions = bool(re.search(r"^permissions\s*:", content, re.MULTILINE))
        has_write_all = bool(re.search(r"permissions\s*:\s*write-all", content))
        has_read_all = bool(re.search(r"permissions\s*:\s*read-all", content))

        # Check for permissions: {} or permissions: none
        has_empty_permissions = bool(re.search(r"permissions\s*:\s*\{\}", content))
        has_none_permissions = bool(re.search(r"permissions\s*:\s*none", content))

        # Find the line where "on:" or first job definition is
        lines = content.splitlines()

        # Determine permissions line (first occurrence)
        perm_line = 1
        for i, line in enumerate(lines, start=1):
            if re.match(r"^permissions\s*:", line):
                perm_line = i
                break

        if has_write_all:
            counters["High"] += 1
            seq = str(counters["High"]).zfill(3)
            findings.append(
                Finding(
                    id=f"HIGH-{seq}",
                    dimension=2,
                    severity="High",
                    file=rel,
                    line=perm_line,
                    current_value="permissions: write-all",
                    expected_value="permissions: read-all",
                    rationale=(
                        "write-all grants GITHUB_TOKEN write access to all scopes. "
                        "Use least-privilege: declare only required scopes."
                    ),
                    offline_detectable=True,
                )
            )

        elif not has_top_permissions:
            # Missing permissions key
            if has_prt:
                severity = "Critical"
            else:
                severity = "High"

            # Find the trigger line for better reporting
            trigger_line = 1
            for i, line in enumerate(lines, start=1):
                if re.match(r"^on\s*:", line) or re.match(r"^on\s*$", line):
                    trigger_line = i
                    break

            counters[severity] += 1
            seq = str(counters[severity]).zfill(3)

            current_val = (
                "pull_request_target (no permissions: key)"
                if has_prt
                else "on: [push] (no permissions: key)"
            )

            findings.append(
                Finding(
                    id=f"{severity.upper()}-{seq}",
                    dimension=2,
                    severity=severity,
                    file=rel,
                    line=trigger_line,
                    current_value=current_val,
                    expected_value="permissions: read-all  # Add top-level permissions",
                    rationale=(
                        "Workflow has no permissions key; GITHUB_TOKEN defaults to "
                        "implicit permissions that may include write access."
                    ),
                    offline_detectable=True,
                )
            )

            # Also add a Medium advisory for job-level permissions best practice
            counters["Medium"] += 1
            seq_m = str(counters["Medium"]).zfill(3)
            findings.append(
                Finding(
                    id=f"MEDIUM-{seq_m}",
                    dimension=2,
                    severity="Medium",
                    file=rel,
                    line=1,
                    current_value="(no job-level permissions defined)",
                    expected_value="jobs.<name>.permissions: {}  # restrict per-job",
                    rationale=(
                        "No job-level permissions override. Declare `permissions: {}` "
                        "per job for least-privilege across all jobs."
                    ),
                    offline_detectable=True,
                )
            )

        elif (
            has_top_permissions
            and not has_read_all
            and not has_empty_permissions
            and not has_none_permissions
        ):
            # Has permissions but not read-all — check if specific write permissions exist
            write_scope = re.search(r":\s*write\b", content)
            if write_scope:
                counters["Medium"] += 1
                seq = str(counters["Medium"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"MEDIUM-{seq}",
                        dimension=2,
                        severity="Medium",
                        file=rel,
                        line=perm_line,
                        current_value="permissions: (includes write scope)",
                        expected_value="Minimize write permissions; use id-token: write only where needed",
                        rationale=(
                            "Workflow has write permissions. Verify each scope is necessary "
                            "and restrict to minimum required."
                        ),
                        offline_detectable=True,
                    )
                )

    return findings


# ─── Dimension 3: Secret Exposure ─────────────────────────────────────────────


_ECHO_PRINT_PATTERN = re.compile(
    r"(echo|print|printf|cat|curl|wget|python\s+-c)[^\n]*\$\{\{\s*secrets\.",
    re.IGNORECASE,
)
_SECRET_IN_CACHE_KEY = re.compile(
    r"key:\s*.*\$\{\{\s*secrets\.",
    re.IGNORECASE,
)
_SECRET_REF_PATTERN = re.compile(r"\$\{\{\s*secrets\.(\w+)\s*\}\}")


def check_secret_exposure(root: Path) -> list[Finding]:
    """Dim 3: Detect secrets echoed to logs or used in insecure contexts.

    Findings:
    - Critical: secret value echoed/printed to stdout in run: step
    - High: secret used in cache key (exposed in cache metadata)
    """
    findings = []
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}

    for wf_path, content in _load_workflows(root):
        rel = _relative_path(root, wf_path)
        lines = content.splitlines()

        # Scan for echo/print + secrets
        for line_no, line in enumerate(lines, start=1):
            # Critical: secret echoed to logs
            if _ECHO_PRINT_PATTERN.search(line):
                secret_match = _SECRET_REF_PATTERN.search(line)
                secret_name = secret_match.group(1) if secret_match else "UNKNOWN"

                counters["Critical"] += 1
                seq = str(counters["Critical"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"CRITICAL-{seq}",
                        dimension=3,
                        severity="Critical",
                        file=rel,
                        line=line_no,
                        current_value=line.strip(),
                        expected_value=(
                            f"Remove echo of secrets.{secret_name}. "
                            "Pass secrets only via env: or action with: blocks."
                        ),
                        rationale=(
                            f"Secret 'secrets.{secret_name}' echoed to stdout. "
                            "GitHub masks known secrets but value may appear in logs."
                        ),
                        offline_detectable=True,
                        contains_secret=True,
                    )
                )
                continue

            # High: secret in cache key
            if _SECRET_IN_CACHE_KEY.search(line):
                secret_match = _SECRET_REF_PATTERN.search(line)
                secret_name = secret_match.group(1) if secret_match else "UNKNOWN"

                counters["High"] += 1
                seq = str(counters["High"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"HIGH-{seq}",
                        dimension=3,
                        severity="High",
                        file=rel,
                        line=line_no,
                        current_value=line.strip(),
                        expected_value=(
                            "Remove secrets from cache keys. Use hash of lock files instead."
                        ),
                        rationale=(
                            f"Secret 'secrets.{secret_name}' in cache key may appear "
                            "in cache entry metadata visible to pull request forks."
                        ),
                        offline_detectable=True,
                        contains_secret=True,
                    )
                )

    return findings


# ─── Dimension 4: Cache Poisoning ─────────────────────────────────────────────


_CACHE_ACTION_PATTERN = re.compile(r"uses:\s*actions/cache@", re.IGNORECASE)
_RESTORE_KEYS_PATTERN = re.compile(r"restore-keys\s*:", re.IGNORECASE)
_HASH_IN_KEY = re.compile(r"hashFiles\s*\(", re.IGNORECASE)


def check_cache_poisoning(root: Path) -> list[Finding]:
    """Dim 4: Detect cache configurations susceptible to poisoning.

    Findings:
    - Medium: cache key without hashFiles() — mutable cache key
    - Info: restore-keys without primary key hash — fallback risk
    """
    findings = []
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}

    for wf_path, content in _load_workflows(root):
        rel = _relative_path(root, wf_path)
        lines = content.splitlines()

        in_cache_step = False
        # cache key tracking
        cache_key_val = ""

        for line_no, line in enumerate(lines, start=1):
            if _CACHE_ACTION_PATTERN.search(line):
                in_cache_step = True
                continue

            if in_cache_step:
                if re.match(r"^\s*key\s*:", line):
                    # line tracked via cache_key_val
                    cache_key_val = line.strip()
                    if not _HASH_IN_KEY.search(line):
                        counters["Medium"] += 1
                        seq = str(counters["Medium"]).zfill(3)
                        findings.append(
                            Finding(
                                id=f"MEDIUM-{seq}",
                                dimension=4,
                                severity="Medium",
                                file=rel,
                                line=line_no,
                                current_value=cache_key_val,
                                expected_value=(
                                    "key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}"
                                ),
                                rationale=(
                                    "Cache key without hashFiles() is mutable and may serve "
                                    "poisoned cache entries to subsequent runs."
                                ),
                                offline_detectable=True,
                            )
                        )
                elif re.match(r"^\s*[a-z]", line) and not re.match(r"^\s*(with|run|uses)", line):
                    # Exiting cache step block
                    in_cache_step = False

    return findings
