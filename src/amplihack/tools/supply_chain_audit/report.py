# File: src/amplihack/tools/supply_chain_audit/report.py
"""Report generation for supply chain audit results.

Produces JSON and human-readable text reports from AuditReport.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import AuditReport


def generate_json_report(report: AuditReport) -> str:
    """Generate a JSON string from an AuditReport."""
    return json.dumps(report.to_dict(), indent=2)


def generate_text_report(report: AuditReport) -> str:
    """Generate a human-readable text summary from an AuditReport."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append(f"Supply Chain Audit Report: {report.advisory_id}")
    lines.append(f"Advisory: {report.advisory_title}")
    lines.append(f"Scan Time: {report.scan_timestamp.isoformat()}")
    lines.append(f"Repos Scanned: {report.repos_scanned}")
    lines.append("-" * 60)

    summary = report.summary
    lines.append(
        f"Summary: {summary.get('safe', 0)} SAFE | "
        f"{summary.get('compromised', 0)} COMPROMISED | "
        f"{summary.get('inconclusive', 0)} INCONCLUSIVE"
    )
    lines.append("=" * 60)

    for v in report.verdicts:
        icon = {"SAFE": "✅", "COMPROMISED": "🚨", "INCONCLUSIVE": "⚠️"}.get(v.verdict, "❓")
        lines.append(f"\n{icon} {v.repo}: {v.verdict} (confidence: {v.confidence})")
        lines.append(f"   Workflow runs analyzed: {v.workflow_runs_analyzed}")

        if v.evidence:
            lines.append("   Evidence:")
            for e in v.evidence:
                lines.append(f"     [{e.signal}] {e.type}: {e.detail}")

        if v.ioc_matches:
            lines.append("   IOC Matches:")
            for m in v.ioc_matches:
                lines.append(f"     [{m.ioc_type}] {m.pattern} in {m.found_in} (run {m.run_id})")

    lines.append("")
    return "\n".join(lines)


def write_report(report: AuditReport, path: str, fmt: str = "json") -> None:
    """Write report to a file with restricted permissions.

    Args:
        report: The audit report to write.
        path: Output file path.
        fmt: Format — 'json' or 'text'.

    Raises:
        ValueError: If path contains traversal characters.
    """
    if ".." in path:
        raise ValueError(f"Path traversal rejected: {path}")
    content = generate_json_report(report) if fmt == "json" else generate_text_report(report)
    p = Path(path)
    p.write_text(content, encoding="utf-8")
    p.chmod(0o600)  # Owner read/write only — reports may contain sensitive IOC data
