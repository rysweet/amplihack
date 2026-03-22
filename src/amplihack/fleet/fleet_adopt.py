"""Fleet session adoption — bring existing sessions under fleet management.

Allows users to start N tmux sessions manually, then hand them to the
fleet director. The director discovers existing sessions, infers what
they're working on (via tmux pane content and Claude Code JSONL logs),
creates tracking records, and begins observing.

Key principle: adoption is non-disruptive. The director OBSERVES existing
sessions without injecting commands or changing state.

Public API:
    SessionAdopter: Discovers and adopts existing tmux sessions
    AdoptedSession: Tracking record for an adopted session
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime

from amplihack.fleet._constants import SUBPROCESS_TIMEOUT_SECONDS
from amplihack.fleet._defaults import get_azlin_path
from amplihack.fleet._validation import validate_session_name, validate_vm_name
from amplihack.fleet.fleet_tasks import TaskPriority, TaskQueue

__all__ = ["SessionAdopter", "AdoptedSession"]

logger = logging.getLogger(__name__)


@dataclass
class AdoptedSession:
    """Tracking record for a session brought under fleet management."""

    vm_name: str
    session_name: str
    inferred_repo: str = ""
    inferred_branch: str = ""
    inferred_task: str = ""
    inferred_pr: str = ""
    working_directory: str = ""
    agent_type: str = ""  # claude, amplifier, copilot
    adopted_at: datetime | None = None
    task_id: str | None = None  # Fleet task ID once created


@dataclass
class SessionAdopter:
    """Discovers and adopts existing tmux sessions for fleet management.

    Non-disruptive: reads session state without modifying anything.
    """

    azlin_path: str = field(default_factory=get_azlin_path)

    def discover_sessions(self, vm_name: str) -> list[AdoptedSession]:
        """Discover all tmux sessions on a VM and infer their context.

        Uses a single SSH connection to gather all session data.
        """
        validate_vm_name(vm_name)
        # Single compound command: list sessions + get context for each
        discover_cmd = self._build_discover_command()

        try:
            result = subprocess.run(
                [self.azlin_path, "connect", vm_name, "--no-tmux", "--yes", "--", discover_cmd],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT_SECONDS,
            )

            if "===SESSION:" in result.stdout or "===DONE===" in result.stdout:
                return self._parse_discovery_output(vm_name, result.stdout)

            if result.returncode != 0:
                logger.warning(
                    "Session discovery command failed for %s (rc=%d): %s",
                    vm_name,
                    result.returncode,
                    result.stderr[:200],
                )
                return []

            return self._parse_discovery_output(vm_name, result.stdout)

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
            logger.warning("Session discovery failed for %s: %s", vm_name, exc)
            return []

    def adopt_sessions(
        self,
        vm_name: str,
        queue: TaskQueue,
        sessions: list[str] | None = None,
    ) -> list[AdoptedSession]:
        """Adopt sessions on a VM into the fleet task queue.

        Args:
            vm_name: Target VM
            queue: Task queue to add adopted tasks to
            sessions: Optional list of session names to adopt. If None, adopts all.

        Returns:
            List of adopted sessions with linked task IDs
        """
        validate_vm_name(vm_name)
        if sessions:
            for s in sessions:
                validate_session_name(s)
        discovered = self.discover_sessions(vm_name)

        if sessions:
            discovered = [s for s in discovered if s.session_name in sessions]

        adopted = []
        for session in discovered:
            # Create a tracking task for the adopted session
            prompt = session.inferred_task or f"Adopted session: {session.session_name}"
            task = queue.add_task(
                prompt=prompt,
                repo_url=session.inferred_repo,
                priority=TaskPriority.MEDIUM,
                agent_command=session.agent_type
                or os.environ.get("AMPLIHACK_AGENT_BINARY", "claude"),
            )
            # Mark as already running (don't try to start it)
            task.assign(vm_name, session.session_name)
            task.start()
            queue.save()

            session.task_id = task.id
            session.adopted_at = datetime.now()
            adopted.append(session)

        return adopted

    def _build_discover_command(self) -> str:
        """Build a compound SSH command that discovers all session contexts.

        Uses semicolons at statement boundaries so the script works even when
        newlines are stripped (azlin -> SSH -> bash -c collapses them).
        """
        return (
            'for session in $(tmux list-sessions -F "#{session_name}" 2>/dev/null); do '
            'echo "===SESSION:$session==="; '
            'CWD=$(tmux display-message -t "$session" -p "#{pane_current_path}" 2>/dev/null); '
            'echo "CWD:$CWD"; '
            'CMD=$(tmux display-message -t "$session" -p "#{pane_current_command}" 2>/dev/null); '
            'echo "CMD:$CMD"; '
            'if [ -n "$CWD" ] && [ -d "$CWD/.git" ]; then '
            'BRANCH=$(cd "$CWD" && git branch --show-current 2>/dev/null); '
            'REMOTE=$(cd "$CWD" && git remote get-url origin 2>/dev/null); '
            'echo "BRANCH:$BRANCH"; '
            'echo "REPO:$REMOTE"; '
            "fi; "
            'echo "PANE_START"; '
            'tmux capture-pane -t "$session" -p -S -5 2>/dev/null | tail -5; '
            'echo "PANE_END"; '
            "done; "
            'echo "===DONE==="'
        )

    def _parse_discovery_output(self, vm_name: str, output: str) -> list[AdoptedSession]:
        """Parse the compound discovery output into AdoptedSession records."""
        sessions = []
        current: AdoptedSession | None = None

        for line in output.split("\n"):
            line = line.strip()

            if line.startswith("===SESSION:") and line.endswith("==="):
                if current:
                    sessions.append(current)
                session_name = line[len("===SESSION:") : -len("===")]
                # Skip tmux placeholder names like "(none)" that aren't real sessions
                if not session_name or session_name.startswith("("):
                    current = None
                    continue
                try:
                    validate_session_name(session_name)
                except ValueError:
                    logger.warning(
                        "Skipping invalid session name from SSH output: %r", session_name
                    )
                    current = None
                    continue
                current = AdoptedSession(vm_name=vm_name, session_name=session_name)

            elif current:
                if line.startswith("CWD:"):
                    current.working_directory = line[4:]
                elif line.startswith("CMD:"):
                    cmd = line[4:].lower()
                    if "claude" in cmd or "node" in cmd:
                        current.agent_type = "claude"
                    elif "amplifier" in cmd:
                        current.agent_type = "amplifier"
                    elif "copilot" in cmd:
                        current.agent_type = "copilot"
                elif line.startswith("BRANCH:"):
                    current.inferred_branch = line[7:]
                elif line.startswith("REPO:"):
                    current.inferred_repo = line[5:]
                elif line.startswith("PR:"):
                    current.inferred_pr = line[3:]
                elif line.startswith("LAST_MSG:"):
                    if not current.inferred_task:
                        current.inferred_task = line[9:]

        if current:
            sessions.append(current)

        return sessions
