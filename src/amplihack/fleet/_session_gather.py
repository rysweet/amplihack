"""Session context gathering -- PERCEIVE stage of the reasoning loop.

Gathers all context for a session via a single compound SSH command.

Public API:
    gather_context: Gather SessionContext for a single session.
    parse_context_output: Parse compound SSH output into SessionContext.
"""

from __future__ import annotations

import shlex
import subprocess

from amplihack.fleet._session_context import SessionContext
from amplihack.fleet._status import infer_agent_status


def gather_context(
    azlin_path: str,
    vm_name: str,
    session_name: str,
    task_prompt: str,
    project_priorities: str,
) -> SessionContext:
    """PERCEIVE: Gather all context for a session in minimal SSH calls."""
    context = SessionContext(
        vm_name=vm_name,
        session_name=session_name,
        task_prompt=task_prompt,
        project_priorities=project_priorities,
    )

    # Single compound SSH command for everything
    gather_cmd = f"""
# Capture tmux pane
echo '===TMUX==='
tmux capture-pane -t {shlex.quote(session_name)} -p -S -40 2>/dev/null || echo 'NO_SESSION'

# Get session's working directory and git info
echo '===CWD==='
CWD=$(tmux display-message -t {shlex.quote(session_name)} -p '#{{pane_current_path}}' 2>/dev/null)
echo "$CWD"

echo '===GIT==='
if [ -n "$CWD" ] && [ -d "$CWD/.git" ]; then
    cd "$CWD"
    echo "BRANCH:$(git branch --show-current 2>/dev/null)"
    echo "REMOTE:$(git remote get-url origin 2>/dev/null)"
    echo "MODIFIED:$(git diff --name-only HEAD 2>/dev/null | head -10 | tr '\\n' ',')"
fi

# Check for JSONL transcript (last few meaningful entries)
echo '===TRANSCRIPT==='
if [ -n "$CWD" ]; then
    PROJECT_KEY=$(echo "$CWD" | sed 's|/|-|g')
    JSONL=$(ls -t ~/.claude/projects/$PROJECT_KEY/*.jsonl 2>/dev/null | head -1)
    if [ -n "$JSONL" ]; then
        # Get last few assistant messages for context
        tail -100 "$JSONL" 2>/dev/null | python3 -c "
import sys, json
msgs = []
for line in sys.stdin:
    try:
        obj = json.loads(line)
        if obj.get('type') == 'assistant':
            msg = obj.get('message',{{}})
            content = msg.get('content','')
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get('type') == 'text':
                        text = c.get('text','')[:200]
                        if text: msgs.append(text)
            elif isinstance(content, str) and content:
                msgs.append(content[:200])
        elif obj.get('type') == 'pr-link':
            msgs.append('PR_CREATED:' + obj.get('url',''))
    except Exception: pass
# Print last 5 messages
for m in msgs[-5:]:
    print(m)
" 2>/dev/null
    fi
fi
echo '===END==='
"""

    try:
        result = subprocess.run(
            [azlin_path, "connect", vm_name, "--no-tmux", "--", gather_cmd],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            parse_context_output(result.stdout, context)

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "Context gathering failed for %s/%s: %s", vm_name, session_name, exc
        )
        context.agent_status = "unreachable"

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

        elif label == "TRANSCRIPT" and i + 1 < len(sections):
            transcript = sections[i + 1].strip()
            if transcript:
                context.transcript_summary = transcript
                # Check for PR link in transcript
                for line in transcript.split("\n"):
                    if line.startswith("PR_CREATED:"):
                        context.pr_url = line[11:]
