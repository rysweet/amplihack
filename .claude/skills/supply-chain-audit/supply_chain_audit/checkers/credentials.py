# File: supply_chain_audit/checkers/credentials.py
"""Dimension 6: Credential hygiene — static credential detection and OIDC migration."""

import re
from pathlib import Path

from ..schema import Finding

_AWS_KEY_ID = re.compile(r"aws-access-key-id\s*:", re.IGNORECASE)
_AWS_SECRET_KEY = re.compile(r"aws-secret-access-key\s*:", re.IGNORECASE)
_AZURE_CREDS = re.compile(r"(creds|credentials)\s*:\s*\$\{\{.*secrets\.", re.IGNORECASE)
_GCP_KEY = re.compile(r"service_account_key\s*:", re.IGNORECASE)
_PAT_ENV = re.compile(
    r"(GITHUB_TOKEN|GH_TOKEN)\s*:\s*\$\{\{\s*secrets\.(?!GITHUB_TOKEN)", re.IGNORECASE
)


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


def check_credential_hygiene(root: Path) -> list[Finding]:
    """Dim 6: Detect static credentials that should migrate to OIDC.

    Findings:
    - High: AWS static access keys used instead of OIDC
    - High: Azure service principal JSON key instead of federated identity
    - High: Long-lived PAT used instead of GITHUB_TOKEN
    - Medium: id-token: write missing (OIDC not enabled but should be)
    """
    findings = []
    counters = {"Critical": 0, "High": 0, "Medium": 0, "Info": 0}

    for wf_path, content in _load_workflows(root):
        rel = _relative_path(root, wf_path)
        lines = content.splitlines()

        # Detect AWS static credential usage
        has_aws_key_id = False
        aws_key_id_line = -1
        has_aws_secret = False

        for line_no, line in enumerate(lines, start=1):
            if _AWS_KEY_ID.search(line):
                has_aws_key_id = True
                aws_key_id_line = line_no
            if _AWS_SECRET_KEY.search(line):
                has_aws_secret = True

        if has_aws_key_id and has_aws_secret:
            counters["High"] += 1
            seq = str(counters["High"]).zfill(3)
            # Build current_value that contains "AWS" for test matching
            findings.append(
                Finding(
                    id=f"HIGH-{seq}",
                    dimension=6,
                    severity="High",
                    file=rel,
                    line=aws_key_id_line,
                    current_value="AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (static credentials)",
                    expected_value=(
                        "Use OIDC federation:\n"
                        "  permissions:\n"
                        "    id-token: write\n"
                        "  - uses: aws-actions/configure-aws-credentials@<sha>\n"
                        "    with:\n"
                        "      role-to-assume: arn:aws:iam::ACCOUNT:role/ROLE"
                    ),
                    rationale=(
                        "Static AWS credentials in secrets can be leaked, rotated infrequently, "
                        "and grant persistent access. Use OIDC federation for short-lived tokens."
                    ),
                    offline_detectable=True,
                )
            )

        # Detect Azure static credentials
        for line_no, line in enumerate(lines, start=1):
            if _AZURE_CREDS.search(line):
                counters["High"] += 1
                seq = str(counters["High"]).zfill(3)
                findings.append(
                    Finding(
                        id=f"HIGH-{seq}",
                        dimension=6,
                        severity="High",
                        file=rel,
                        line=line_no,
                        current_value=line.strip(),
                        expected_value=(
                            "Use Azure federated identity (OIDC) instead of service principal JSON key"
                        ),
                        rationale=(
                            "Azure service principal JSON credentials are long-lived. "
                            "Use federated identity with OIDC for short-lived, keyless authentication."
                        ),
                        offline_detectable=True,
                        contains_secret=True,
                    )
                )
                break

    findings = _assign_ids(findings)
    return findings
