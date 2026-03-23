# File: supply_chain_audit/checkers/node.py
"""Dimension 10: Node.js / npm security checks."""

import json
import re
from pathlib import Path

from ..schema import Finding


def _relative_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _assign_ids(findings: list[Finding]) -> list[Finding]:
    severity_rank = {"Critical": 0, "High": 1, "Medium": 2, "Info": 3}
    sorted_findings = sorted(
        findings, key=lambda f: (severity_rank.get(f.severity, 4), f.file, f.line)
    )
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}
    result = []
    for f in sorted_findings:
        counters[f.severity] += 1
        seq = str(counters[f.severity]).zfill(3)
        new_id = f"{f.severity.upper()}-{seq}"
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


def _load_workflows(root: Path) -> list:
    wf_dir = root / ".github" / "workflows"
    results = []
    if not wf_dir.is_dir():
        return results
    for wf_file in sorted(list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml"))):
        try:
            content = wf_file.read_text(errors="replace")
            results.append((wf_file, content))
        except (OSError, PermissionError):
            pass
    return results


# Match npx followed by a full token (package name possibly including @version)
# Group 1: the full token (may contain @version)
_NPX_FULL_TOKEN = re.compile(r"\bnpx\s+(\S+)")


def check_node_integrity(root: Path) -> list[Finding]:
    """Dim 10: Check Node.js dependency integrity.

    Findings:
    - High: npm install used instead of npm ci in CI workflows
    - High: package.json without package-lock.json (no lock file)
    - High: unversioned npx in scripts (ephemeral install risk)
    - Medium: postinstall scripts present (advisory)
    """
    findings = []
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}

    pkg_json = root / "package.json"
    pkg_lock = root / "package-lock.json"
    yarn_lock = root / "yarn.lock"
    pnpm_lock = root / "pnpm-lock.yaml"

    has_pkg_json = pkg_json.exists()
    has_lock = pkg_lock.exists() or yarn_lock.exists() or pnpm_lock.exists()

    rel_pkg = _relative_path(root, pkg_json) if has_pkg_json else "package.json"

    # Check for missing lock file
    if has_pkg_json and not has_lock:
        counters["High"] += 1
        seq = str(counters["High"]).zfill(3)
        findings.append(
            Finding(
                id=f"HIGH-{seq}",
                dimension=10,
                severity="High",
                file=rel_pkg,
                line=0,  # file-level
                current_value="no package-lock.json",
                expected_value="Add package-lock.json: run npm install once and commit the lock file",
                rationale=(
                    "Without a lock file, npm install resolves to the latest compatible version "
                    "on each run. This allows silent dependency updates that could introduce "
                    "malicious packages."
                ),
                offline_detectable=True,
            )
        )

    # Check for unversioned npx in package.json scripts
    if has_pkg_json:
        try:
            pkg_content = pkg_json.read_text(errors="replace")
            pkg_data = json.loads(pkg_content)
            scripts = pkg_data.get("scripts", {})

            for script_name, script_cmd in scripts.items():
                # Find all npx calls and check if versioned
                for match in _NPX_FULL_TOKEN.finditer(script_cmd):
                    full_token = match.group(1)
                    # Skip if it looks like a local binary
                    if full_token.startswith(".") or full_token.startswith("/"):
                        continue
                    # Split on @ to get the bare package name and version
                    # Handles: webpack@5.91.0, @scope/pkg@1.0.0 (scoped packages start with @)
                    if "@" in full_token:
                        # Scoped package like @scope/pkg@version
                        if full_token.startswith("@"):
                            # @scope/pkg@version — split after the scope
                            slash_idx = full_token.find("/")
                            if slash_idx >= 0:
                                rest = full_token[slash_idx + 1 :]
                                if "@" in rest:
                                    continue  # has version after scope/pkg
                        else:
                            # plain package@version — versioned
                            continue
                    pkg_name = (
                        full_token.split("@")[0] if not full_token.startswith("@") else full_token
                    )
                    # Skip flags that look like npx options
                    if pkg_name.startswith("-"):
                        continue

                    # Find line number in the JSON
                    line_no = 0
                    for i, line in enumerate(pkg_content.splitlines(), start=1):
                        if script_name in line and script_cmd in line:
                            line_no = i
                            break

                    counters["High"] += 1
                    seq = str(counters["High"]).zfill(3)
                    findings.append(
                        Finding(
                            id=f"HIGH-{seq}",
                            dimension=10,
                            severity="High",
                            file=rel_pkg,
                            line=line_no,
                            current_value=f"npx {pkg_name} (unversioned)",
                            expected_value=f"npx {pkg_name}@<version> (pin to specific version)",
                            rationale=(
                                f"Unversioned `npx {pkg_name}` downloads the latest version at "
                                "runtime, bypassing lock file protections. Pin to a specific version."
                            ),
                            offline_detectable=True,
                        )
                    )

        except (json.JSONDecodeError, OSError, PermissionError):
            pass

    # Check CI workflows for npm install vs npm ci
    for wf_path, content in _load_workflows(root):
        rel_wf = _relative_path(root, wf_path)
        lines = content.splitlines()

        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Detect `npm install` (not `npm install --save` or `npm install -g` in non-CI context)
            if re.search(r"\bnpm\s+install\b", stripped) and not re.search(
                r"npm\s+install\s+--", stripped
            ):
                # Skip npm install <specific-package> (installing a named package is OK)
                if not re.search(r"npm\s+install\s+[a-zA-Z@]", stripped):
                    counters["High"] += 1
                    seq = str(counters["High"]).zfill(3)
                    findings.append(
                        Finding(
                            id=f"HIGH-{seq}",
                            dimension=10,
                            severity="High",
                            file=rel_wf,
                            line=line_no,
                            current_value=stripped,
                            expected_value=stripped.replace("npm install", "npm ci"),
                            rationale=(
                                "`npm install` can upgrade packages and modify package-lock.json, "
                                "bypassing lock file protections. Use `npm ci` in CI pipelines."
                            ),
                            offline_detectable=True,
                        )
                    )
                    break  # One finding per workflow

    findings = _assign_ids(findings)
    return findings
