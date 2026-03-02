"""Transcript analyzer -- extracts patterns from Claude Code JSONL session logs.

Gathers transcripts from local machine and remote azlin VMs, analyzes them
for tool usage, strategy patterns, agent invocations, and workflow compliance.

Public API:
    TranscriptAnalyzer: Main analyzer class
    AnalysisReport: Structured analysis results
    gather_local_transcripts: Find all local JSONL files
    gather_remote_transcripts: Collect JSONL summaries from azlin VMs
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

__all__ = [
    "TranscriptAnalyzer",
    "AnalysisReport",
    "gather_local_transcripts",
    "gather_remote_transcripts",
]


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


def gather_local_transcripts(limit: int = 50) -> list[Path]:
    """Find local JSONL transcript files under ~/.claude/projects/.

    Searches the standard Claude Code transcript directory for JSONL
    files, returns the most recently modified ones up to ``limit``.
    """
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.is_dir():
        return []

    jsonl_files = sorted(
        projects_dir.rglob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return jsonl_files[:limit]


def gather_remote_transcripts(
    vm_names: list[str],
    azlin_path: str | None = None,
) -> dict[str, list[dict]]:
    """Gather transcript summaries from remote VMs via azlin.

    Runs a lightweight Python summariser over SSH on each VM.  Returns a
    dict mapping VM name to a list of per-session summary dicts.
    """
    if azlin_path is None:
        azlin_path = os.environ.get("AZLIN_PATH", shutil.which("azlin") or "azlin")

    remote_script = _build_remote_summary_script()
    results: dict[str, list[dict]] = {}

    for vm in vm_names:
        try:
            proc = subprocess.run(
                [
                    azlin_path,
                    "connect",
                    vm,
                    "--no-tmux",
                    "--",
                    "python3",
                    "-c",
                    remote_script,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                results[vm] = json.loads(proc.stdout.strip())
            else:
                results[vm] = []
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            results[vm] = []

    return results


def _build_remote_summary_script() -> str:
    """Return a self-contained Python script that summarises JSONL files remotely."""
    return (
        "import json, pathlib, collections, sys\n"
        "base = pathlib.Path.home() / '.claude' / 'projects'\n"
        "if not base.is_dir():\n"
        "    print('[]'); sys.exit(0)\n"
        "summaries = []\n"
        "for f in sorted(base.rglob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:\n"
        "    tools = collections.Counter()\n"
        "    msgs = 0\n"
        "    for line in f.open():\n"
        "        try:\n"
        "            obj = json.loads(line)\n"
        "        except json.JSONDecodeError:\n"
        "            continue\n"
        "        msgs += 1\n"
        "        if obj.get('type') == 'assistant':\n"
        "            for blk in (obj.get('message',{}).get('content',None) or []):\n"
        "                if isinstance(blk, dict) and blk.get('type') == 'tool_use':\n"
        "                    tools[blk.get('name','')] += 1\n"
        "    summaries.append({'file': str(f), 'messages': msgs, 'tools': dict(tools)})\n"
        "print(json.dumps(summaries))\n"
    )


# ── Pattern detection regexes ────────────────────────────────────────

_SKILL_RE = re.compile(r'Skill\s*\(\s*skill\s*=\s*["\']([^"\']+)["\']', re.I)
_SKILL_INVOKE_RE = re.compile(r'"?skill"?\s*[:=]\s*["\']([^"\']+)["\']', re.I)
_AGENT_RE = re.compile(r'(?:agent|subagent_type)\s*[:=]\s*["\']([^"\']+)["\']', re.I)

# Known strategy markers (keywords that signal a strategy from the dictionary)
_STRATEGY_KEYWORDS: dict[str, str] = {
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
_WORKFLOW_STEP_RE = re.compile(r"(?:step|workflow)\s+(\d+)", re.I)


class TranscriptAnalyzer:
    """Analyzes Claude Code JSONL transcripts for patterns and metrics.

    Usage::

        analyzer = TranscriptAnalyzer()
        transcripts = analyzer.gather_local(limit=30)
        report = analyzer.analyze(transcripts)
        print(report.report())
    """

    def __init__(self) -> None:
        self._report: AnalysisReport | None = None

    # ── Gathering ────────────────────────────────────────────────────

    def gather_local(self, limit: int = 50) -> list[Path]:
        """Find local JSONL transcript files."""
        return gather_local_transcripts(limit=limit)

    def gather_remote(
        self,
        vm_names: list[str],
        azlin_path: str | None = None,
    ) -> dict[str, list[dict]]:
        """Gather transcript summaries from remote azlin VMs."""
        return gather_remote_transcripts(vm_names, azlin_path=azlin_path)

    # ── Analysis ─────────────────────────────────────────────────────

    def analyze(self, transcripts: list[Path]) -> AnalysisReport:
        """Parse JSONL files and extract tool/strategy/agent patterns.

        Args:
            transcripts: Paths to JSONL transcript files.

        Returns:
            Populated AnalysisReport with extracted counters and rates.
        """
        report = AnalysisReport(total_transcripts=len(transcripts))
        workflow_steps_seen: dict[str, int] = {}
        workflow_steps_total: dict[str, int] = {}

        for path in transcripts:
            self._analyze_single(path, report, workflow_steps_seen, workflow_steps_total)

        # Compute compliance rates
        for step, total in workflow_steps_total.items():
            seen = workflow_steps_seen.get(step, 0)
            report.workflow_compliance[step] = round(seen / total, 2) if total else 0.0

        self._report = report
        return report

    def _analyze_single(
        self,
        path: Path,
        report: AnalysisReport,
        steps_seen: dict[str, int],
        steps_total: dict[str, int],
    ) -> None:
        """Analyze a single JSONL transcript file."""
        transcript_has_step: set[str] = set()

        try:
            with path.open() as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    report.total_messages += 1
                    entry_type = entry.get("type", "")

                    if entry_type == "assistant":
                        self._extract_assistant_patterns(entry, report, transcript_has_step)
                    elif entry_type == "user":
                        self._extract_user_patterns(entry, report)

        except (OSError, PermissionError):
            return

        # Mark which workflow steps appeared in this transcript
        for step in transcript_has_step:
            steps_seen[step] = steps_seen.get(step, 0) + 1
        # Every transcript could have every step
        for step in transcript_has_step:
            steps_total[step] = steps_total.get(step, 0) + 1

    def _extract_assistant_patterns(
        self,
        entry: dict,
        report: AnalysisReport,
        transcript_steps: set[str],
    ) -> None:
        """Extract patterns from an assistant message entry."""
        message = entry.get("message", {})
        content = message.get("content")
        if not isinstance(content, list):
            return

        for block in content:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type", "")

            if block_type == "tool_use":
                tool_name = block.get("name", "unknown")
                report.tool_usage[tool_name] += 1

                # Check tool input for skill/agent invocations
                tool_input = block.get("input", {})
                input_str = (
                    json.dumps(tool_input) if isinstance(tool_input, dict) else str(tool_input)
                )
                self._scan_for_skills(input_str, report)
                self._scan_for_agents(input_str, report)

            elif block_type == "text":
                text = block.get("text", "")
                self._scan_for_skills(text, report)
                self._scan_for_agents(text, report)
                self._scan_for_strategies(text, report)
                self._scan_for_workflow_steps(text, transcript_steps)

    def _extract_user_patterns(self, entry: dict, report: AnalysisReport) -> None:
        """Extract patterns from a user message entry."""
        message = entry.get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            text = " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
        else:
            text = str(content)
        self._scan_for_strategies(text, report)

    def _scan_for_skills(self, text: str, report: AnalysisReport) -> None:
        for match in _SKILL_RE.finditer(text):
            report.skill_invocations[match.group(1)] += 1
        for match in _SKILL_INVOKE_RE.finditer(text):
            report.skill_invocations[match.group(1)] += 1

    def _scan_for_agents(self, text: str, report: AnalysisReport) -> None:
        for match in _AGENT_RE.finditer(text):
            report.agent_types[match.group(1)] += 1

    def _scan_for_strategies(self, text: str, report: AnalysisReport) -> None:
        text_lower = text.lower()
        for keyword, strategy_name in _STRATEGY_KEYWORDS.items():
            if keyword in text_lower:
                report.strategy_patterns[strategy_name] += 1

    def _scan_for_workflow_steps(self, text: str, steps: set[str]) -> None:
        for match in _WORKFLOW_STEP_RE.finditer(text):
            steps.add(f"step_{match.group(1)}")

    # ── Reporting ────────────────────────────────────────────────────

    def report(self) -> str:
        """Produce a human-readable report from the most recent analysis.

        Raises:
            RuntimeError: If ``analyze()`` has not been called yet.
        """
        if self._report is None:
            raise RuntimeError("Call analyze() before report()")
        return format_report(self._report)

    # ── Strategy dictionary update ───────────────────────────────────

    def update_strategy_dictionary(self, dict_path: Path) -> int:
        """Append newly discovered strategy patterns to a STRATEGY_DICTIONARY.md.

        Returns the number of new patterns appended.
        """
        if self._report is None:
            raise RuntimeError("Call analyze() before update_strategy_dictionary()")

        existing_text = ""
        if dict_path.is_file():
            existing_text = dict_path.read_text()

        existing_lower = existing_text.lower()
        new_patterns: list[str] = []
        for pattern, count in self._report.strategy_patterns.most_common():
            if pattern.lower() not in existing_lower:
                new_patterns.append(pattern)

        if not new_patterns:
            return 0

        lines = [
            "",
            f"## Discovered Patterns ({datetime.now().strftime('%Y-%m-%d')})",
            "",
        ]
        for pattern in new_patterns:
            count = self._report.strategy_patterns[pattern]
            lines.append(f"- **{pattern}** (observed {count} time(s))")
        lines.append("")

        with dict_path.open("a") as fh:
            fh.write("\n".join(lines))

        return len(new_patterns)


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

    # Tool usage
    if report.tool_usage:
        sections.append("## Tool Usage (top 15)")
        for tool, count in report.tool_usage.most_common(15):
            bar = "#" * min(count, 40)
            sections.append(f"  {tool:<25} {count:>5}  {bar}")
        sections.append("")

    # Skill invocations
    if report.skill_invocations:
        sections.append("## Skill Invocations")
        for skill, count in report.skill_invocations.most_common(10):
            sections.append(f"  {skill:<30} {count:>4}")
        sections.append("")

    # Agent types
    if report.agent_types:
        sections.append("## Agent Types")
        for agent, count in report.agent_types.most_common(10):
            sections.append(f"  {agent:<30} {count:>4}")
        sections.append("")

    # Strategy patterns
    if report.strategy_patterns:
        sections.append("## Strategy Patterns")
        for pattern, count in report.strategy_patterns.most_common():
            sections.append(f"  {pattern:<40} {count:>4}")
        sections.append("")

    # Workflow compliance
    if report.workflow_compliance:
        sections.append("## Workflow Step Compliance")
        for step, rate in sorted(report.workflow_compliance.items()):
            pct = int(rate * 100)
            bar = "#" * (pct // 5)
            sections.append(f"  {step:<15} {pct:>3}%  {bar}")
        sections.append("")

    return "\n".join(sections)
