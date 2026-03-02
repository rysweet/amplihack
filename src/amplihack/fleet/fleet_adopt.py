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

import subprocess
from dataclasses import dataclass
from datetime import datetime

from amplihack.fleet._validation import validate_vm_name
from amplihack.fleet.fleet_tasks import TaskPriority, TaskQueue

__all__ = ["SessionAdopter", "AdoptedSession"]


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

    azlin_path: str = "/home/azureuser/src/azlin/.venv/bin/azlin"

    def discover_sessions(self, vm_name: str) -> list[AdoptedSession]:
        """Discover all tmux sessions on a VM and infer their context.

        Uses a single SSH connection to gather all session data.
        """
        validate_vm_name(vm_name)
        # Single compound command: list sessions + get context for each
        discover_cmd = self._build_discover_command()

        try:
            result = subprocess.run(
                [self.azlin_path, "connect", vm_name, "--no-tmux", "--", discover_cmd],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return []

            return self._parse_discovery_output(vm_name, result.stdout)

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
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
                agent_command=session.agent_type or "claude",
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
        """Build a compound SSH command that discovers all session contexts."""
        return """
# List all tmux sessions with their current pane commands
for session in $(tmux list-sessions -F '#{session_name}' 2>/dev/null); do
    echo "===SESSION:$session==="

    # Get current working directory of the session's active pane
    CWD=$(tmux display-message -t "$session" -p '#{pane_current_path}' 2>/dev/null)
    echo "CWD:$CWD"

    # Get the running command in the pane
    CMD=$(tmux display-message -t "$session" -p '#{pane_current_command}' 2>/dev/null)
    echo "CMD:$CMD"

    # Get git info if in a git repo
    if [ -n "$CWD" ] && [ -d "$CWD/.git" ]; then
        BRANCH=$(cd "$CWD" && git branch --show-current 2>/dev/null)
        REMOTE=$(cd "$CWD" && git remote get-url origin 2>/dev/null)
        echo "BRANCH:$BRANCH"
        echo "REPO:$REMOTE"
    fi

    # Capture last 5 lines of pane for context
    echo "PANE_START"
    tmux capture-pane -t "$session" -p -S -5 2>/dev/null | tail -5
    echo "PANE_END"

    # Check for Claude Code JSONL logs
    if [ -n "$CWD" ]; then
        # Find most recent JSONL in the Claude projects dir
        PROJECT_KEY=$(echo "$CWD" | sed 's|/|-|g')
        JSONL=$(ls -t ~/.claude/projects/$PROJECT_KEY/*.jsonl 2>/dev/null | head -1)
        if [ -n "$JSONL" ]; then
            echo "JSONL:$JSONL"
            # Get last few meaningful entries (assistant messages, pr-links)
            tail -50 "$JSONL" 2>/dev/null | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        obj = json.loads(line)
        t = obj.get('type','')
        if t == 'pr-link':
            print(f'PR:{obj.get(\"url\",\"\")}'[:200])
        elif t == 'assistant':
            msg = obj.get('message',{})
            content = msg.get('content','')
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get('type') == 'text':
                        text = c.get('text','')[:100]
                        if text: print(f'LAST_MSG:{text}')
                        break
    except Exception: pass
" 2>/dev/null | tail -3
        fi
    fi
done
echo "===DONE==="
"""

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
