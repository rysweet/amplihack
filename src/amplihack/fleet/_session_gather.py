"""Session context gathering -- PERCEIVE stage of the reasoning loop.

Gathers all context for a session via a single compound SSH command.

Public API:
    gather_context: Gather SessionContext for a single session.
    parse_context_output: Parse compound SSH output into SessionContext.
"""

from __future__ import annotations

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
) -> SessionContext:
    """PERCEIVE: Gather all context for a session in minimal SSH calls."""
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
        f'echo "===TMUX==="; '
        f"tmux capture-pane -t {sess} -p -S -40 2>/dev/null || echo 'NO_SESSION'; "
        f'echo "===CWD==="; '
        f'CWD=$(tmux display-message -t {sess} -p "#{{pane_current_path}}" 2>/dev/null); '
        f'echo "$CWD"; '
        f'echo "===GIT==="; '
        f'if [ -n "$CWD" ] && [ -d "$CWD/.git" ]; then '
        f'cd "$CWD"; '
        f'echo "BRANCH:$(git branch --show-current 2>/dev/null)"; '
        f'echo "REMOTE:$(git remote get-url origin 2>/dev/null)"; '
        f"echo \"MODIFIED:$(git diff --name-only HEAD 2>/dev/null | head -10 | tr '\\n' ',')\"; "
        f"fi; "
        f'echo "===TRANSCRIPT==="; '
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
