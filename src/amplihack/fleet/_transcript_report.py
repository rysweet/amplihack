"""Transcript report formatting and pattern detection constants.

Extracted from transcript_analyzer.py to keep it under 300 LOC.

Public API:
    format_report: Format an AnalysisReport as readable text
    SKILL_RE / SKILL_INVOKE_RE / AGENT_RE: Pattern detection regexes
    STRATEGY_KEYWORDS: Known strategy markers
    WORKFLOW_STEP_RE: Workflow step markers
    ALL_EXPECTED_STEPS: Expected DEFAULT_WORKFLOW steps (0-22)
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

__all__ = [
    "format_report",
    "SKILL_RE",
    "SKILL_INVOKE_RE",
    "AGENT_RE",
    "STRATEGY_KEYWORDS",
    "WORKFLOW_STEP_RE",
    "ALL_EXPECTED_STEPS",
]

# ── Pattern detection regexes ────────────────────────────────────────

SKILL_RE = re.compile(r'Skill\s*\(\s*skill\s*=\s*["\']([^"\']+)["\']', re.I)
SKILL_INVOKE_RE = re.compile(r'"?skill"?\s*[:=]\s*["\']([^"\']+)["\']', re.I)
AGENT_RE = re.compile(r'(?:agent|subagent_type)\s*[:=]\s*["\']([^"\']+)["\']', re.I)

# Known strategy markers (keywords that signal a strategy from the dictionary)
STRATEGY_KEYWORDS: dict[str, str] = {
    "workflow compliance": "Workflow Compliance Check",
    "outside-in testing": "Outside-In Testing Gate",
    "philosophy enforcement": "Philosophy Enforcement",
    "parallel agent": "Parallel Agent Investigation",
    "multi-agent review": "Multi-Agent Review",
    "lock mode": "Lock Mode for Deep Work",
    "goal measurement": "Goal Measurement",
    "quality audit": "Quality Audit Cycle",
    "pre-commit diagnostic": "Pre-Commit Diagnostic",
    "ci diagnostic": "CI Diagnostic Recovery",
    "worktree isolation": "Worktree Isolation",
    "investigation before": "Investigation Before Implementation",
    "architect-first": "Architect-First Design",
    "sprint planning": "Sprint Planning with PM",
    "n-version": "N-Version for Critical Code",
    "debate for": "Debate for Architecture Decisions",
    "dry-run": "Dry-Run Validation",
    "session adoption": "Session Adoption Protocol",
    "morning briefing": "Morning Briefing",
    "escalation": "Escalation Protocol",
}

# Workflow step markers (detected in text blocks)
WORKFLOW_STEP_RE = re.compile(r"(?:step|workflow)\s+(\d+)", re.I)

# All expected DEFAULT_WORKFLOW steps (0 through 22)
ALL_EXPECTED_STEPS = list(range(0, 23))


@dataclass
class AnalysisReport:
    """Structured results from transcript analysis."""

    tool_usage: Counter = field(default_factory=Counter)
    skill_invocations: Counter = field(default_factory=Counter)
    agent_types: Counter = field(default_factory=Counter)
    strategy_patterns: Counter = field(default_factory=Counter)
    workflow_compliance: dict[str, float] = field(default_factory=dict)
    total_transcripts: int = 0
    total_messages: int = 0
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "tool_usage": dict(self.tool_usage.most_common()),
            "skill_invocations": dict(self.skill_invocations.most_common()),
            "agent_types": dict(self.agent_types.most_common()),
            "strategy_patterns": dict(self.strategy_patterns.most_common()),
            "workflow_compliance": self.workflow_compliance,
            "total_transcripts": self.total_transcripts,
            "total_messages": self.total_messages,
            "analysis_timestamp": self.analysis_timestamp,
        }


def format_report(report: AnalysisReport) -> str:
    """Format an AnalysisReport as a readable text report."""
    sections: list[str] = []

    sections.append("# Transcript Analysis Report")
    sections.append(f"Generated: {report.analysis_timestamp}")
    sections.append(
        f"Transcripts analyzed: {report.total_transcripts}  |  "
        f"Messages parsed: {report.total_messages}"
    )
    sections.append("")

    if report.tool_usage:
        sections.append("## Tool Usage (top 15)")
        for tool, count in report.tool_usage.most_common(15):
            bar = "#" * min(count, 40)
            sections.append(f"  {tool:<25} {count:>5}  {bar}")
        sections.append("")

    if report.skill_invocations:
        sections.append("## Skill Invocations")
        for skill, count in report.skill_invocations.most_common(10):
            sections.append(f"  {skill:<30} {count:>4}")
        sections.append("")

    if report.agent_types:
        sections.append("## Agent Types")
        for agent, count in report.agent_types.most_common(10):
            sections.append(f"  {agent:<30} {count:>4}")
        sections.append("")

    if report.strategy_patterns:
        sections.append("## Strategy Patterns")
        for pattern, count in report.strategy_patterns.most_common():
            sections.append(f"  {pattern:<40} {count:>4}")
        sections.append("")

    if report.workflow_compliance:
        sections.append("## Workflow Step Compliance")
        for step, rate in sorted(report.workflow_compliance.items()):
            pct = int(rate * 100)
            bar = "#" * (pct // 5)
            sections.append(f"  {step:<15} {pct:>3}%  {bar}")
        sections.append("")

    return "\n".join(sections)
