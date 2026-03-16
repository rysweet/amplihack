"""Transcript analyzer -- extracts patterns from Claude Code JSONL session logs.

Gathers transcripts from local machine and remote azlin VMs, analyzes them
for tool usage, strategy patterns, agent invocations, and workflow compliance.

Public API:
    TranscriptAnalyzer: Main analyzer class
    AnalysisReport: Structured analysis results
    gather_local_transcripts: Find all local JSONL files
    gather_remote_transcripts: Collect JSONL summaries from azlin VMs
    format_report: Format an AnalysisReport as readable text
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from amplihack.fleet._transcript_report import (
    AGENT_RE,
    ALL_EXPECTED_STEPS,
    SKILL_INVOKE_RE,
    SKILL_RE,
    STRATEGY_KEYWORDS,
    WORKFLOW_STEP_RE,
    AnalysisReport,
    format_report,
)
from amplihack.fleet._validation import validate_vm_name
from amplihack.utils.logging_utils import log_call

__all__ = [
    "TranscriptAnalyzer",
    "AnalysisReport",
    "gather_local_transcripts",
    "gather_remote_transcripts",
    "format_report",
]


@log_call
def gather_local_transcripts() -> list[Path]:
    """Find local JSONL transcript files under ~/.claude/projects/.

    Searches the standard Claude Code transcript directory for JSONL
    files, returns all of them sorted by most recently modified first.
    """
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.is_dir():
        return []

    @log_call
    def _safe_mtime(p: Path) -> float:
        try:
            return p.stat().st_mtime
        except (OSError, FileNotFoundError) as exc:
            logger.warning("Cannot stat transcript file %s: %s", p, exc)
            return 0.0

    return sorted(projects_dir.rglob("*.jsonl"), key=_safe_mtime, reverse=True)


@log_call
def gather_remote_transcripts(
    vm_names: list[str],
    azlin_path: str | None = None,
) -> dict[str, list[dict]]:
    """Gather transcript summaries from remote VMs via azlin."""
    if azlin_path is None:
        from amplihack.fleet._defaults import get_azlin_path

        azlin_path = get_azlin_path()

    remote_script = _build_remote_summary_script()
    results: dict[str, list[dict]] = {}

    for vm in vm_names:
        try:
            validate_vm_name(vm)
            proc = subprocess.run(
                [azlin_path, "connect", vm, "--no-tmux", "--", "python3", "-c", remote_script],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                results[vm] = json.loads(proc.stdout.strip())
            else:
                results[vm] = []
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as exc:
            logger.warning("Remote transcript gather failed for %s: %s", vm, exc)
            results[vm] = []

    return results


@log_call
def _build_remote_summary_script() -> str:
    """Return a self-contained Python script that summarises JSONL files remotely."""
    return (
        "import json, pathlib, collections, sys\n"
        "base = pathlib.Path.home() / '.claude' / 'projects'\n"
        "if not base.is_dir():\n"
        "    print('[]'); sys.exit(0)\n"
        "summaries = []\n"
        "for f in sorted(base.rglob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True):\n"
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


class TranscriptAnalyzer:
    """Analyzes Claude Code JSONL transcripts for patterns and metrics."""

    @log_call
    def __init__(self) -> None:
        self._report: AnalysisReport | None = None

    @log_call
    def gather_local(self) -> list[Path]:
        """Find local JSONL transcript files."""
        return gather_local_transcripts()

    @log_call
    def gather_remote(
        self, vm_names: list[str], azlin_path: str | None = None
    ) -> dict[str, list[dict]]:
        """Gather transcript summaries from remote azlin VMs."""
        return gather_remote_transcripts(vm_names, azlin_path=azlin_path)

    @log_call
    def analyze(self, transcripts: list[Path]) -> AnalysisReport:
        """Parse JSONL files and extract tool/strategy/agent patterns."""
        report = AnalysisReport(total_transcripts=len(transcripts))
        workflow_steps_seen: dict[str, int] = {}
        workflow_steps_total: dict[str, int] = {}

        for path in transcripts:
            self._analyze_single(path, report, workflow_steps_seen, workflow_steps_total)

        for step, total in workflow_steps_total.items():
            seen = workflow_steps_seen.get(step, 0)
            report.workflow_compliance[step] = round(seen / total, 2) if total else 0.0

        self._report = report
        return report

    @log_call
    def _analyze_single(self, path, report, steps_seen, steps_total):
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
        except (OSError, PermissionError) as exc:
            logger.warning("Cannot read transcript file %s: %s", path, exc)
            return

        for step in transcript_has_step:
            steps_seen[step] = steps_seen.get(step, 0) + 1
        for i in ALL_EXPECTED_STEPS:
            step_key = f"step_{i}"
            steps_total[step_key] = steps_total.get(step_key, 0) + 1

    @log_call
    def _extract_assistant_patterns(self, entry, report, transcript_steps):
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

    @log_call
    def _extract_user_patterns(self, entry, report):
        """Extract patterns from a user message entry."""
        message = entry.get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            text = " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
        else:
            text = str(content)
        self._scan_for_strategies(text, report)

    @log_call
    def _scan_for_skills(self, text, report):
        for match in SKILL_RE.finditer(text):
            report.skill_invocations[match.group(1)] += 1
        for match in SKILL_INVOKE_RE.finditer(text):
            report.skill_invocations[match.group(1)] += 1

    @log_call
    def _scan_for_agents(self, text, report):
        for match in AGENT_RE.finditer(text):
            report.agent_types[match.group(1)] += 1

    @log_call
    def _scan_for_strategies(self, text, report):
        text_lower = text.lower()
        for keyword, strategy_name in STRATEGY_KEYWORDS.items():
            if keyword in text_lower:
                report.strategy_patterns[strategy_name] += 1

    @log_call
    def _scan_for_workflow_steps(self, text, steps):
        for match in WORKFLOW_STEP_RE.finditer(text):
            steps.add(f"step_{match.group(1)}")

    @log_call
    def report(self) -> str:
        """Produce a human-readable report from the most recent analysis."""
        if self._report is None:
            raise RuntimeError("Call analyze() before report()")
        return format_report(self._report)

    @log_call
    def update_strategy_dictionary(self, dict_path: Path) -> int:
        """Append newly discovered strategy patterns to a STRATEGY_DICTIONARY.md."""
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

        lines = ["", f"## Discovered Patterns ({datetime.now().strftime('%Y-%m-%d')})", ""]
        for pattern in new_patterns:
            count = self._report.strategy_patterns[pattern]
            lines.append(f"- **{pattern}** (observed {count} time(s))")
        lines.append("")

        with dict_path.open("a") as fh:
            fh.write("\n".join(lines))

        return len(new_patterns)
