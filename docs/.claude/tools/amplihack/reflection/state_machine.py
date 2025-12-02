"""State machine for interactive reflection workflow."""

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple


class ReflectionState(Enum):
    """States in the interactive reflection workflow."""

    IDLE = "idle"
    ANALYZING = "analyzing"
    AWAITING_APPROVAL = "awaiting_approval"
    CREATING_ISSUE = "creating_issue"
    AWAITING_WORK_DECISION = "awaiting_work_decision"
    STARTING_WORK = "starting_work"
    COMPLETED = "completed"


@dataclass
class ReflectionStateData:
    """Data for reflection state machine."""

    state: ReflectionState
    analysis: Optional[dict] = None
    issue_url: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None


class ReflectionStateMachine:
    """Manages interactive reflection workflow state."""

    def __init__(self, session_id: str, runtime_dir: Optional[Path] = None):
        """Initialize state machine for session."""
        self.session_id = session_id

        if runtime_dir is None:
            # Find .claude/runtime/ directory
            current = Path(__file__).resolve().parent
            while current != current.parent:
                claude_dir = current / ".claude"
                if claude_dir.exists():
                    runtime_dir = claude_dir / "runtime"
                    runtime_dir.mkdir(parents=True, exist_ok=True)
                    break
                current = current.parent

            if runtime_dir is None:
                raise ValueError("Could not find .claude/runtime/ directory")

        self.state_file = runtime_dir / f"reflection_state_{session_id}.json"

    def read_state(self) -> ReflectionStateData:
        """Read current state from file."""
        if not self.state_file.exists():
            return ReflectionStateData(state=ReflectionState.IDLE, session_id=self.session_id)

        try:
            with open(self.state_file) as f:
                data = json.load(f)
                data["state"] = ReflectionState(data["state"])
                return ReflectionStateData(**data)
        except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError):
            # Corrupt state file (missing fields), reset to IDLE
            return ReflectionStateData(state=ReflectionState.IDLE, session_id=self.session_id)

    def write_state(self, state_data: ReflectionStateData):
        """Write state to file."""
        data = asdict(state_data)
        data["state"] = state_data.state.value

        try:
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass  # Failed to write, will retry next time

    def detect_user_intent(self, message: str) -> Optional[str]:
        """Detect user intent from message text.

        Returns:
            "approve", "reject", or None
        """
        message_lower = message.lower().strip()

        # Approval keywords
        approval_keywords = [
            "yes",
            "y",
            "create issue",
            "go ahead",
            "approve",
            "ok",
            "sure",
            "do it",
            "proceed",
        ]
        if any(word in message_lower for word in approval_keywords):
            return "approve"

        # Rejection keywords
        rejection_keywords = ["no", "n", "skip", "cancel", "ignore", "don't", "do not"]
        if any(word in message_lower for word in rejection_keywords):
            return "reject"

        return None

    def transition(
        self, current_state: ReflectionState, user_intent: Optional[str]
    ) -> Tuple[ReflectionState, str]:
        """Determine next state based on current state and user intent.

        Returns:
            (new_state, action)
            action: "create_issue", "start_work", "rejected", "completed", "none"
        """
        transitions = {
            (ReflectionState.AWAITING_APPROVAL, "approve"): (
                ReflectionState.CREATING_ISSUE,
                "create_issue",
            ),
            (ReflectionState.AWAITING_APPROVAL, "reject"): (ReflectionState.COMPLETED, "rejected"),
            (ReflectionState.AWAITING_WORK_DECISION, "approve"): (
                ReflectionState.STARTING_WORK,
                "start_work",
            ),
            (ReflectionState.AWAITING_WORK_DECISION, "reject"): (
                ReflectionState.COMPLETED,
                "completed",
            ),
        }

        key = (current_state, user_intent)
        if key in transitions:
            return transitions[key]

        # No transition
        return current_state, "none"

    def cleanup(self):
        """Clean up state file."""
        if self.state_file.exists():
            try:
                self.state_file.unlink()
            except OSError:
                pass
