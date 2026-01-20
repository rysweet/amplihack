"""Recipe session tracker for detecting workflow requirements."""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class WorkflowRequirement:
    """Result of workflow requirement detection."""

    required: bool
    reason: str
    confidence: float  # 0.0-1.0


class RecipeSessionTracker:
    """Tracks recipe sessions and determines workflow requirements."""

    # Keywords that indicate implementation work
    IMPLEMENTATION_KEYWORDS = [
        "implement",
        "add feature",
        "create",
        "build",
        "refactor",
        "fix bug",
        "modify",
        "change",
        "update",
        "add",
        "remove",
        "delete",
        "redesign",
    ]

    # Patterns that are exempt from workflow requirements
    EXEMPT_PATTERNS = [
        r"^what is",
        r"^how does.*work",
        r"^explain",
        r"^show me",
        r"^describe",
        r"^why",
        r"quick fix",
        r"typo",
        r"^read",
        r"^find",
        r"^search",
    ]

    def __init__(self, state_file: Optional[Path] = None):
        """Initialize tracker with optional state file path."""
        if state_file is None:
            state_file = Path.home() / ".amplifier" / "state" / "recipe_sessions.json"

        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load_state()

    def _load_state(self) -> dict:
        """Load state from file."""
        if not self.state_file.exists():
            return {"sessions": {}, "bypass_attempts": []}

        try:
            with open(self.state_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"sessions": {}, "bypass_attempts": []}

    def _save_state(self):
        """Save state to file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self._state, f, indent=2)
        except IOError:
            pass  # Fail gracefully if we can't save

    def is_workflow_required(self, user_prompt: str, context: dict) -> tuple[bool, str]:
        """
        Determine if prompt requires workflow execution.

        Returns:
            (required: bool, reason: str)
        """
        prompt_lower = user_prompt.lower().strip()

        # Check exempt patterns first (QA, investigation, etc.)
        for pattern in self.EXEMPT_PATTERNS:
            if re.match(pattern, prompt_lower):
                return False, f"exempt: matches '{pattern}'"

        # Check for implementation keywords
        for keyword in self.IMPLEMENTATION_KEYWORDS:
            if keyword in prompt_lower:
                return True, f"implementation keyword detected: '{keyword}'"

        # Check for multi-file changes
        if "multiple files" in prompt_lower or "several files" in prompt_lower:
            return True, "multi-file change detected"

        # Check for code file mentions with verbs
        code_file_pattern = r"\b(py|js|ts|go|java|cpp|c|h)\b.*\b(add|change|modify|update|fix)\b"
        if re.search(code_file_pattern, prompt_lower):
            return True, "code modification detected"

        return False, "no workflow requirement detected"

    def is_workflow_active(self, session_id: str) -> bool:
        """Check if a workflow is currently active for this session."""
        if not session_id:
            return False

        session = self._state["sessions"].get(session_id)
        if not session:
            return False

        return session.get("status") == "active"

    def mark_workflow_started(self, workflow_name: str, session_id: str):
        """Record workflow start - disables enforcement."""
        if not session_id:
            return

        self._state["sessions"][session_id] = {
            "workflow_name": workflow_name,
            "status": "active",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
        }
        self._save_state()

    def mark_workflow_completed(self, workflow_name: str, session_id: str):
        """Record workflow completion."""
        if not session_id:
            return

        session = self._state["sessions"].get(session_id)
        if session:
            session["status"] = "completed"
            session["completed_at"] = datetime.now().isoformat()
            self._save_state()

    def record_bypass_attempt(self, tool_name: str, session_id: str, blocked: bool):
        """Record a bypass attempt for auditing."""
        self._state["bypass_attempts"].append(
            {
                "tool_name": tool_name,
                "session_id": session_id,
                "blocked": blocked,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._save_state()

    def get_bypass_count(self, session_id: str) -> int:
        """Get number of bypass attempts in this session."""
        return sum(
            1 for attempt in self._state["bypass_attempts"] if attempt["session_id"] == session_id
        )
