"""Fleet log reader — intelligence from Claude Code JSONL session logs.

Reads Claude Code's JSONL trace logs from remote VMs to understand
what agents actually did beyond what tmux shows. Extracts:
- Tasks attempted and their outcomes
- Tools used and their results
- PRs created
- Errors encountered
- Token usage and cost
- Session duration and activity patterns

This powers the director's LEARN phase with deep session intelligence.

Public API:
    LogReader: Reads and parses Claude Code JSONL logs from remote VMs
    SessionSummary: Condensed summary of a Claude Code session
"""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass, field

from amplihack.fleet._defaults import get_azlin_path
from amplihack.fleet._validation import validate_vm_name

__all__ = ["LogReader", "SessionSummary"]


@dataclass
class SessionSummary:
    """Condensed intelligence from a Claude Code JSONL session log."""

    session_id: str = ""
    git_branch: str = ""
    cwd: str = ""
    message_count: int = 0
    tool_use_count: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    pr_urls: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    last_activity: str = ""
    topics: list[str] = field(default_factory=list)  # Inferred from content
    files_modified: list[str] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        return self.message_count > 0

    @property
    def has_pr(self) -> bool:
        return len(self.pr_urls) > 0

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "git_branch": self.git_branch,
            "cwd": self.cwd,
            "message_count": self.message_count,
            "tool_use_count": self.tool_use_count,
            "user_messages": self.user_messages,
            "assistant_messages": self.assistant_messages,
            "pr_urls": self.pr_urls,
            "errors": self.errors,
            "last_activity": self.last_activity,
            "topics": self.topics,
            "files_modified": self.files_modified,
        }


@dataclass
class LogReader:
    """Reads Claude Code JSONL logs from remote VMs.

    Uses a single SSH connection per VM to find and parse logs.
    Extracts only the information the director needs — not raw logs.
    """

    azlin_path: str = field(default_factory=get_azlin_path)

    def read_session_log(
        self,
        vm_name: str,
        project_path: str,
        tail_lines: int = 200,
    ) -> SessionSummary | None:
        """Read the most recent Claude Code session log for a project.

        Args:
            vm_name: Target VM
            project_path: Working directory of the project (used to find logs)
            tail_lines: Number of lines to read from end of log

        Returns:
            SessionSummary or None if no log found
        """
        validate_vm_name(vm_name)
        # Build a command that finds and summarizes the log in one SSH call
        read_cmd = self._build_log_reader_command(project_path, tail_lines)

        try:
            result = subprocess.run(
                [self.azlin_path, "connect", vm_name, "--no-tmux", "--", read_cmd],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return None

            return self._parse_log_summary(result.stdout)

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
            import logging
            logging.getLogger(__name__).debug("read_session_log failed for %s: %s", vm_name, exc)
            return None

    def read_all_sessions(self, vm_name: str) -> list[SessionSummary]:
        """Read summaries from all Claude Code session logs on a VM."""
        find_cmd = """
# Find all Claude Code project directories with JSONL logs
for dir in ~/.claude/projects/*/; do
    LATEST=$(ls -t "$dir"*.jsonl 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        echo "===LOG:$LATEST==="
        # Extract key metrics in a single pass
        python3 -c "
import json, sys
stats = {'session':'','branch':'','cwd':'','msgs':0,'tools':0,'user':0,'asst':0,'prs':[],'errors':[],'files':[],'last':''}
with open(sys.argv[1]) as f:
    for line in f:
        try:
            obj = json.loads(line)
            t = obj.get('type','')
            if t == 'user': stats['user'] += 1; stats['msgs'] += 1
            elif t == 'assistant': stats['asst'] += 1; stats['msgs'] += 1
            elif t == 'progress': stats['tools'] += 1
            elif t == 'pr-link': stats['prs'].append(obj.get('url',''))
            if 'sessionId' in obj: stats['session'] = obj['sessionId']
            if 'gitBranch' in obj and obj['gitBranch']: stats['branch'] = obj['gitBranch']
            if 'cwd' in obj and obj['cwd']: stats['cwd'] = obj['cwd']
        except Exception: pass
print(json.dumps(stats))
" "$LATEST" 2>/dev/null
    fi
done
"""

        try:
            result = subprocess.run(
                [self.azlin_path, "connect", vm_name, "--no-tmux", "--", find_cmd],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                return []

            return self._parse_all_logs_output(result.stdout)

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
            import logging
            logging.getLogger(__name__).debug("read_all_sessions failed for %s: %s", vm_name, exc)
            return []

    def _build_log_reader_command(self, project_path: str, tail_lines: int) -> str:
        """Build SSH command to read and summarize a specific project's log."""
        tail_lines = max(1, min(tail_lines, 10000))
        # Convert project path to Claude's project key format
        safe_path = shlex.quote(project_path)
        return f"""
PROJECT_KEY=$(echo {safe_path} | sed 's|/|-|g')
JSONL=$(ls -t ~/.claude/projects/"$PROJECT_KEY"/*.jsonl 2>/dev/null | head -1)

if [ -z "$JSONL" ]; then
    echo "NO_LOG"
    exit 0
fi

# Extract summary stats from last N lines
tail -{tail_lines} "$JSONL" | python3 -c "
import json, sys
stats = {{'session':'','branch':'','cwd':'','msgs':0,'tools':0,'user':0,'asst':0,'prs':[],'errors':[],'files':[],'last':''}}
for line in sys.stdin:
    try:
        obj = json.loads(line)
        t = obj.get('type','')
        if t == 'user': stats['user'] += 1; stats['msgs'] += 1
        elif t == 'assistant': stats['asst'] += 1; stats['msgs'] += 1
        elif t == 'progress':
            stats['tools'] += 1
            data = obj.get('data',{{}})
            if isinstance(data, dict) and data.get('tool') in ('Write','Edit'):
                path = data.get('path','')
                if path and path not in stats['files']:
                    stats['files'].append(path)
        elif t == 'pr-link': stats['prs'].append(obj.get('url',''))
        if 'sessionId' in obj: stats['session'] = obj['sessionId']
        if 'gitBranch' in obj and obj['gitBranch']: stats['branch'] = obj['gitBranch']
        if 'cwd' in obj and obj['cwd']: stats['cwd'] = obj['cwd']
    except Exception: pass
print(json.dumps(stats))
" 2>/dev/null
"""

    def _parse_log_summary(self, output: str) -> SessionSummary | None:
        """Parse the remote log reader output."""
        for line in output.strip().split("\n"):
            line = line.strip()
            if line == "NO_LOG":
                return None
            try:
                stats = json.loads(line)
                return SessionSummary(
                    session_id=stats.get("session", ""),
                    git_branch=stats.get("branch", ""),
                    cwd=stats.get("cwd", ""),
                    message_count=stats.get("msgs", 0),
                    tool_use_count=stats.get("tools", 0),
                    user_messages=stats.get("user", 0),
                    assistant_messages=stats.get("asst", 0),
                    pr_urls=stats.get("prs", []),
                    errors=stats.get("errors", []),
                    files_modified=stats.get("files", []),
                )
            except (json.JSONDecodeError, KeyError):
                continue
        return None

    def _parse_all_logs_output(self, output: str) -> list[SessionSummary]:
        """Parse output from read_all_sessions."""
        summaries = []
        for line in output.strip().split("\n"):
            line = line.strip()
            if line.startswith("===LOG:"):
                continue
            try:
                stats = json.loads(line)
                summaries.append(
                    SessionSummary(
                        session_id=stats.get("session", ""),
                        git_branch=stats.get("branch", ""),
                        cwd=stats.get("cwd", ""),
                        message_count=stats.get("msgs", 0),
                        tool_use_count=stats.get("tools", 0),
                        user_messages=stats.get("user", 0),
                        assistant_messages=stats.get("asst", 0),
                        pr_urls=stats.get("prs", []),
                    )
                )
            except (json.JSONDecodeError, KeyError):
                continue
        return summaries
