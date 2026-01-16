"""Session management for GitHub Copilot CLI.

Handles session lifecycle, forking, and state preservation across sessions.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SessionState:
    """Session state data."""

    session_id: str
    fork_count: int = 0
    start_time: float = field(default_factory=time.time)
    last_fork_time: float = field(default_factory=time.time)
    total_turns: int = 0
    phase: str = "init"
    context: dict[str, Any] = field(default_factory=dict)


class CopilotSessionManager:
    """Manage Copilot CLI sessions with forking and state preservation.

    Handles:
    - Session lifecycle tracking
    - Forking sessions with --continue flag
    - Context preservation across forks
    - Session state persistence
    """

    def __init__(
        self, working_dir: Path, session_id: str, fork_threshold: float = 3600  # 60 minutes
    ):
        """Initialize session manager.

        Args:
            working_dir: Working directory for the session
            session_id: Unique session identifier
            fork_threshold: Time threshold for session forking (seconds)
        """
        self.working_dir = working_dir
        self.session_id = session_id
        self.fork_threshold = fork_threshold

        # State file location
        self.state_dir = working_dir / ".claude" / "runtime" / "copilot_sessions"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / f"{session_id}.json"

        # Initialize state
        self.state = SessionState(session_id=session_id)
        self._save_state()

    def _save_state(self) -> None:
        """Persist session state to file."""
        state_dict = {
            "session_id": self.state.session_id,
            "fork_count": self.state.fork_count,
            "start_time": self.state.start_time,
            "last_fork_time": self.state.last_fork_time,
            "total_turns": self.state.total_turns,
            "phase": self.state.phase,
            "context": self.state.context,
        }

        with open(self.state_file, "w") as f:
            json.dump(state_dict, f, indent=2)

    def _load_state(self) -> None:
        """Load session state from file."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                state_dict = json.load(f)
                self.state = SessionState(**state_dict)

    def should_fork(self) -> bool:
        """Check if session should be forked based on elapsed time.

        Returns:
            True if session duration exceeds fork threshold
        """
        elapsed = time.time() - self.state.last_fork_time
        return elapsed >= self.fork_threshold

    def fork_session(self, continuation_context: dict[str, Any]) -> str:
        """Fork current session using Copilot CLI --continue.

        Args:
            continuation_context: Context to pass to forked session

        Returns:
            New session ID for the fork
        """
        # Increment fork count
        self.state.fork_count += 1
        self.state.last_fork_time = time.time()

        # Store continuation context
        self.state.context["last_fork_context"] = continuation_context
        self._save_state()

        # Generate new session ID for fork
        fork_id = f"{self.session_id}_fork{self.state.fork_count}"

        # Create state file for forked session
        fork_state = SessionState(
            session_id=fork_id,
            fork_count=self.state.fork_count,
            start_time=time.time(),
            last_fork_time=time.time(),
            total_turns=self.state.total_turns,
            phase=self.state.phase,
            context=continuation_context,
        )

        fork_state_file = self.state_dir / f"{fork_id}.json"
        with open(fork_state_file, "w") as f:
            json.dump(
                {
                    "session_id": fork_state.session_id,
                    "fork_count": fork_state.fork_count,
                    "start_time": fork_state.start_time,
                    "last_fork_time": fork_state.last_fork_time,
                    "total_turns": fork_state.total_turns,
                    "phase": fork_state.phase,
                    "context": fork_state.context,
                },
                f,
                indent=2,
            )

        return fork_id

    def update_phase(self, phase: str) -> None:
        """Update current session phase.

        Args:
            phase: New phase (clarifying, planning, executing, evaluating, summarizing)
        """
        self.state.phase = phase
        self._save_state()

    def increment_turn(self) -> None:
        """Increment turn counter."""
        self.state.total_turns += 1
        self._save_state()

    def update_context(self, key: str, value: Any) -> None:
        """Update session context.

        Args:
            key: Context key
            value: Context value
        """
        self.state.context[key] = value
        self._save_state()

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get value from session context.

        Args:
            key: Context key
            default: Default value if key not found

        Returns:
            Context value or default
        """
        return self.state.context.get(key, default)

    def get_state(self) -> dict[str, Any]:
        """Return current session state as dict.

        Returns:
            Session state dictionary
        """
        self._load_state()
        return {
            "session_id": self.state.session_id,
            "fork_count": self.state.fork_count,
            "start_time": self.state.start_time,
            "last_fork_time": self.state.last_fork_time,
            "total_turns": self.state.total_turns,
            "phase": self.state.phase,
            "elapsed_seconds": time.time() - self.state.start_time,
            "time_until_fork": max(
                0, self.fork_threshold - (time.time() - self.state.last_fork_time)
            ),
        }

    def get_elapsed_time(self) -> float:
        """Get elapsed time since session start.

        Returns:
            Elapsed time in seconds
        """
        return time.time() - self.state.start_time

    def get_fork_count(self) -> int:
        """Get number of times session has been forked.

        Returns:
            Fork count
        """
        return self.state.fork_count

    def build_continuation_prompt(self) -> str:
        """Build continuation prompt for forked session.

        Returns:
            Prompt with context from previous session
        """
        context = self.state.context.get("last_fork_context", {})

        prompt = f"""Continue from previous session {self.state.session_id}.

Previous session summary:
- Total turns completed: {self.state.total_turns}
- Last phase: {self.state.phase}
- Fork count: {self.state.fork_count}

Context:
"""
        for key, value in context.items():
            prompt += f"\n{key}: {value}"

        prompt += "\n\nContinue execution from where we left off."
        return prompt

    def cleanup(self) -> None:
        """Clean up session state files (call at session end)."""
        if self.state_file.exists():
            self.state_file.unlink()


class SessionRegistry:
    """Registry of active and historical sessions."""

    def __init__(self, working_dir: Path):
        """Initialize session registry.

        Args:
            working_dir: Working directory
        """
        self.working_dir = working_dir
        self.registry_dir = working_dir / ".claude" / "runtime" / "copilot_sessions"
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.registry_dir / "registry.json"

    def register_session(self, session_id: str, metadata: dict[str, Any]) -> None:
        """Register a new session.

        Args:
            session_id: Session ID
            metadata: Session metadata
        """
        registry = self._load_registry()
        registry[session_id] = {
            "registered_at": time.time(),
            "metadata": metadata,
        }
        self._save_registry(registry)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session metadata.

        Args:
            session_id: Session ID

        Returns:
            Session metadata or None if not found
        """
        registry = self._load_registry()
        return registry.get(session_id)

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all registered sessions.

        Returns:
            List of session records
        """
        registry = self._load_registry()
        return [
            {"session_id": sid, **data} for sid, data in sorted(registry.items(), reverse=True)
        ]

    def _load_registry(self) -> dict[str, Any]:
        """Load registry from file."""
        if self.registry_file.exists():
            with open(self.registry_file) as f:
                return json.load(f)
        return {}

    def _save_registry(self, registry: dict[str, Any]) -> None:
        """Save registry to file."""
        with open(self.registry_file, "w") as f:
            json.dump(registry, f, indent=2)


__all__ = ["CopilotSessionManager", "SessionState", "SessionRegistry"]
