#!/usr/bin/env python3
"""
Workflow Classification Reminder Hook - System reminder for topic boundary classification.

Injects a system reminder when a new topic is detected, prompting the agent to classify
the request into the appropriate workflow and route through dev-orchestrator.

This hook fires on user.prompt.submitted and injects additionalContext as a system reminder.
"""

import sys
from pathlib import Path
from typing import Any

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class WorkflowClassificationReminder(HookProcessor):
    """Hook processor for workflow classification reminders."""

    def __init__(self):
        super().__init__("workflow_classification_reminder")
        # Initialize state directory (created after parent init which sets runtime_dir)
        self._init_state_dir()

    def _init_state_dir(self):
        """Initialize state directory after parent sets runtime_dir."""
        # Handle both production (runtime_dir set) and test (not set) environments
        try:
            state_parent = self.runtime_dir
        except AttributeError:
            # Test/standalone environment - use temp directory
            state_parent = Path("/tmp/.claude_test/runtime/logs")
            state_parent.mkdir(parents=True, exist_ok=True)

        self._state_dir = state_parent / "classification_state"
        self._state_dir.mkdir(parents=True, exist_ok=True)

    def get_session_state_file(self) -> Path:
        """Get the state file for current session."""
        session_id = self.get_session_id()
        return self._state_dir / f"{session_id}.json"

    def is_new_topic(self, user_prompt: str, input_data: dict) -> bool:
        """Detect if this is a new topic requiring classification.

        Args:
            user_prompt: The user's message
            input_data: Full input data from Claude Code

        Returns:
            True if this appears to be a new topic
        """
        # Always classify on first turn
        turn_count = input_data.get("turnCount", 0)
        if turn_count == 0 or turn_count == 1:
            return True

        # Check for explicit topic transition keywords
        transition_keywords = [
            "now let's",
            "next i want",
            "switching to",
            "different question",
            "different topic",
            "new task",
            "moving on to",
        ]
        prompt_lower = user_prompt.lower()
        if any(keyword in prompt_lower for keyword in transition_keywords):
            return True

        # Check for follow-up indicators (NOT new topics)
        followup_keywords = [
            "also",
            "what about",
            "and",
            "additionally",
            "furthermore",
            "i meant",
            "to clarify",
            "how's it going",
            "what's the status",
            "what's the progress",
        ]
        # If starts with follow-up keyword, it's NOT a new topic
        first_words = " ".join(prompt_lower.split()[:3])
        if any(keyword in first_words for keyword in followup_keywords):
            return False

        # Check state file for recent classification
        state_file = self.get_session_state_file()
        if state_file.exists():
            import json

            try:
                state = json.loads(state_file.read_text())
                last_turn = state.get("last_classified_turn", 0)

                # If we classified within last 3 turns, assume same topic
                if turn_count - last_turn <= 3:
                    return False
            except Exception as e:
                self.log(f"Could not read classification state (using default): {e}", "DEBUG")

        # Default: treat as new topic to be safe
        return True

    def save_classification_state(self, turn_count: int):
        """Save that we classified on this turn."""
        state_file = self.get_session_state_file()
        import json

        state = {"last_classified_turn": turn_count, "session_id": self.get_session_id()}
        state_file.write_text(json.dumps(state))

    def build_reminder(self, user_prompt: str) -> str:
        """Build the system reminder message."""
        truncated = user_prompt[:100] + ("..." if len(user_prompt) > 100 else "")
        return (
            f'NEW TOPIC DETECTED - Classify and Route\n\n'
            f'Request: "{truncated}"\n\n'
            "Classify (choose ONE):\n"
            '  Q&A         -> "what is", "explain", "how do I"        -> respond directly\n'
            '  OPERATIONS  -> "cleanup", "delete", "git status"       -> execute directly\n'
            "  INVESTIGATION/DEVELOPMENT -> all other non-trivial work -> use dev-orchestrator\n\n"
            "For INVESTIGATION or DEVELOPMENT tasks:\n"
            '  Invoke Skill(skill="dev-orchestrator") -- the smart-orchestrator will:\n'
            "    - Classify the task and formulate a clear goal\n"
            "    - Detect parallel workstreams if task has independent components\n"
            "    - Execute via recipe runner (single task or parallel workstreams)\n"
            "    - Reflect on goal achievement\n\n"
            "  Entry point: /dev <task description>\n"
            "  (Legacy: /ultrathink is deprecated -- use /dev)\n\n"
            "DO NOT start implementation without invoking dev-orchestrator first."
        )

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process user prompt submit event.

        Args:
            input_data: Input from Claude Code

        Returns:
            Additional context to inject (system reminder if new topic detected)
        """
        # Extract user prompt
        user_message = input_data.get("userMessage", "")
        if isinstance(user_message, dict):
            user_prompt = user_message.get("text", "")
        else:
            user_prompt = str(user_message)

        # Check if this is a new topic
        if not self.is_new_topic(user_prompt, input_data):
            self.log("Follow-up detected - skipping classification reminder")
            return {}

        # This is a new topic - inject reminder
        self.log("New topic detected - injecting classification reminder")
        reminder = self.build_reminder(user_prompt)

        # Save state
        turn_count = input_data.get("turnCount", 0)
        self.save_classification_state(turn_count)

        # Return system reminder format
        return {
            "additionalContext": f'<system-reminder source="hooks-workflow-classification">\n{reminder}\n</system-reminder>'
        }


def main():
    """Entry point for the workflow classification reminder hook."""
    hook = WorkflowClassificationReminder()
    hook.run()


if __name__ == "__main__":
    main()
