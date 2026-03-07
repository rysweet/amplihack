"""Session context gathering -- PERCEIVE stage of the reasoning loop.

Gathers all context for a session via a single compound SSH command.

Public API:
    gather_context: Gather SessionContext for a single session.
    parse_context_output: Parse compound SSH output into SessionContext.
"""

from __future__ import annotations

import logging
import re
import shlex
import subprocess

from amplihack.fleet._constants import SUBPROCESS_TIMEOUT_SECONDS
from amplihack.fleet._session_context import SessionContext
from amplihack.fleet._status import infer_agent_status

__all__ = ["gather_context", "parse_context_output"]


def gather_context(
    azlin_path: str,
    vm_name: str,
    session_name: str,
    task_prompt: str,
    project_priorities: str,
    cached_tmux_capture: str = "",
) -> SessionContext:
    """PERCEIVE: Gather all context for a session in minimal SSH calls.

    Args:
        cached_tmux_capture: Pre-collected tmux output from Phase 1 (scout discovery).
            When provided, the SSH call still runs to collect git/transcript context,
            but the tmux capture section is replaced with the cached version,
            avoiding a redundant SSH poll of the same pane content.
    """
    context = SessionContext(
        vm_name=vm_name,
        session_name=session_name,
        task_prompt=task_prompt,
        project_priorities=project_priorities,
    )

    # Single compound SSH command — semicolons at statement boundaries
    # so the script works even when newlines are stripped by SSH.
    sess = shlex.quote(session_name)
    gather_cmd = (
        # Full tmux scrollback capture (no line limit)
        f'echo "===TMUX==="; '
        f"tmux capture-pane -t {sess} -p -S - 2>/dev/null || echo 'NO_SESSION'; "
        # Working directory
        f'echo "===CWD==="; '
        f'CWD=$(tmux display-message -t {sess} -p "#{{pane_current_path}}" 2>/dev/null); '
        f'echo "$CWD"; '
        # Git state
        f'echo "===GIT==="; '
        f'if [ -n "$CWD" ] && [ -d "$CWD/.git" ]; then '
        f'cd "$CWD"; '
        f'echo "BRANCH:$(git branch --show-current 2>/dev/null)"; '
        f'echo "REMOTE:$(git remote get-url origin 2>/dev/null)"; '
        f"echo \"MODIFIED:$(git diff --name-only HEAD 2>/dev/null | head -10 | tr '\\n' ',')\"; "
        # PR URL detection via gh CLI (more reliable than parsing git log)
        f'PRURL=$(gh pr list --head "$(git branch --show-current 2>/dev/null)" --json url --jq ".[0].url" 2>/dev/null); '
        f'if [ -n "$PRURL" ]; then echo "PR_URL:$PRURL"; fi; '
        f"fi; "
        # Transcript: first 50 + last 200 lines of user/assistant messages
        # from the most recent JSONL in ~/.claude/projects/<project-key>/
        f'echo "===TRANSCRIPT==="; '
        f'if [ -n "$CWD" ]; then '
        f'PKEY=$(echo "$CWD" | sed "s|/|-|g"); '
        f'JSONL=$(ls -t "$HOME/.claude/projects/$PKEY/"*.jsonl 2>/dev/null | head -1); '
        f'if [ -n "$JSONL" ]; then '
        # Extract user/assistant text lines via grep + sed (no python needed)
        f"MSGS=$(grep -E '\"type\":\"(user|assistant)\"' \"$JSONL\" 2>/dev/null "
        f"| grep -oP '\"text\":\"[^\"]*\"' "
        f"| sed 's/\"text\":\"//;s/\"$//' "
        f"| grep -v '^$'); "
        f'TOTAL=$(echo "$MSGS" | wc -l); '
        f'echo "TRANSCRIPT_LINES:$TOTAL"; '
        # First 50 lines (early context — what the user asked for)
        f'echo "---EARLY---"; '
        f'echo "$MSGS" | head -50; '
        # Last 200 lines (recent activity)
        f'echo "---RECENT---"; '
        f'echo "$MSGS" | tail -200; '
        f"fi; fi; "
        f'echo "===END==="'
    )

    try:
        result = subprocess.run(
            [azlin_path, "connect", vm_name, "--no-tmux", "--yes", "--", gather_cmd],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )

        if "===TMUX===" in result.stdout or "===END===" in result.stdout:
            parse_context_output(result.stdout, context)
        elif result.returncode == 0:
            parse_context_output(result.stdout, context)

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
        logging.getLogger(__name__).warning(
            "Context gathering failed for %s/%s: %s", vm_name, session_name, exc
        )
        context.agent_status = "unreachable"

    # Override with cached tmux capture from Phase 1 discovery (avoids double-poll)
    if cached_tmux_capture:
        context.tmux_capture = cached_tmux_capture
        context.agent_status = infer_agent_status(cached_tmux_capture)

    return context


def parse_context_output(output: str, context: SessionContext) -> None:
    """Parse the compound SSH output into SessionContext."""
    sections = output.split("===")

    for i, section in enumerate(sections):
        label = section.strip()

        if label == "TMUX" and i + 1 < len(sections):
            tmux_text = sections[i + 1].strip()
            if tmux_text == "NO_SESSION":
                context.agent_status = "no_session"
            else:
                context.tmux_capture = tmux_text
                context.agent_status = infer_agent_status(tmux_text)

        elif label == "CWD" and i + 1 < len(sections):
            context.working_directory = sections[i + 1].strip()

        elif label == "GIT" and i + 1 < len(sections):
            for line in sections[i + 1].strip().split("\n"):
                if line.startswith("BRANCH:"):
                    context.git_branch = line[7:]
                elif line.startswith("REMOTE:"):
                    context.repo_url = line[7:]
                elif line.startswith("MODIFIED:"):
                    files = [f.strip() for f in line[9:].split(",") if f.strip()]
                    context.files_modified = files
                elif line.startswith("PR_URL:"):
                    context.pr_url = line[7:].strip()

        elif label == "TRANSCRIPT" and i + 1 < len(sections):
            raw_transcript = sections[i + 1].strip()
            if raw_transcript:
                # Parse early + recent sections
                parts_text = raw_transcript
                early = ""
                recent = ""
                if "---EARLY---" in parts_text and "---RECENT---" in parts_text:
                    early_start = parts_text.index("---EARLY---") + len("---EARLY---")
                    recent_start = parts_text.index("---RECENT---")
                    early = parts_text[early_start:recent_start].strip()
                    recent = parts_text[recent_start + len("---RECENT---"):].strip()
                elif parts_text:
                    recent = parts_text

                # Combine: early context + separator + recent activity
                transcript_parts = []
                if early:
                    transcript_parts.append("=== Session start ===")
                    transcript_parts.append(early)
                if recent:
                    if early:
                        transcript_parts.append("\n=== Recent activity ===")
                    transcript_parts.append(recent)

                context.transcript_summary = "\n".join(transcript_parts)

                # Check for PR links in transcript
                for line in context.transcript_summary.split("\n"):
                    if "PR_CREATED:" in line:
                        context.pr_url = line.split("PR_CREATED:")[-1].strip()
                    elif "pull/" in line and "github.com" in line:
                        pr_match = re.search(r'https://github\.com/[^\s"]+/pull/\d+', line)
                        if pr_match:
                            context.pr_url = pr_match.group(0)
