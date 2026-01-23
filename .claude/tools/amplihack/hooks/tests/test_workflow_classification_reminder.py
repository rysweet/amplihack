#!/usr/bin/env python3
"""
Integration tests for workflow classification reminder hook.

Tests the hook's ability to detect topic boundaries and inject reminders.
"""

import json
import sys
from pathlib import Path

import pytest

# Add hook directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow_classification_reminder import WorkflowClassificationReminder


class TestTopicDetection:
    """Test topic boundary detection logic."""

    def setup_method(self):
        """Set up test environment."""
        # Mock the parent class initialization to avoid dependency on Claude Code environment
        import unittest.mock

        with unittest.mock.patch.object(WorkflowClassificationReminder, "_init_state_dir"):
            self.hook = WorkflowClassificationReminder()

        # Manually set up test directories
        self.hook._state_dir = Path("/tmp/test_classification_state")
        self.hook._state_dir.mkdir(parents=True, exist_ok=True)

        # Mock get_session_id to return consistent value
        self.hook.get_session_id = lambda: "test_session_123"

    def teardown_method(self):
        """Clean up test state."""
        import shutil

        if self.hook._state_dir.exists():
            shutil.rmtree(self.hook._state_dir)

    def test_first_turn_is_new_topic(self):
        """First turn of session should always be classified as new topic."""
        input_data = {"userMessage": "Hello, can you help me?", "turnCount": 0}

        result = self.hook.is_new_topic("Hello, can you help me?", input_data)
        assert result is True

    def test_turn_one_is_new_topic(self):
        """Turn 1 should also be classified as new topic."""
        input_data = {"userMessage": "Implement user authentication", "turnCount": 1}

        result = self.hook.is_new_topic("Implement user authentication", input_data)
        assert result is True

    def test_explicit_transition_detected(self):
        """Explicit transition keywords should trigger new topic."""
        transitions = [
            "now let's work on the database",
            "Next I want to add testing",
            "Switching to a different question",
            "Different topic: how does caching work?",
            "Moving on to the API design",
        ]

        input_data = {"turnCount": 5}

        for prompt in transitions:
            result = self.hook.is_new_topic(prompt, input_data)
            assert result is True, f"Should detect new topic in: {prompt}"

    def test_followup_keywords_not_new_topic(self):
        """Follow-up keywords at start should NOT be new topic."""
        followups = [
            "Also add the logout feature",
            "What about error handling?",
            "And we should update the tests",
            "Additionally, can you add validation?",
            "I meant to say we need caching",
        ]

        input_data = {"turnCount": 5}

        for prompt in followups:
            result = self.hook.is_new_topic(prompt, input_data)
            assert result is False, f"Should NOT detect new topic in: {prompt}"

    def test_recent_classification_not_new_topic(self):
        """Within 3 turns of last classification should be same topic."""
        # Simulate classification at turn 5
        state_file = self.hook.get_session_state_file()
        state_file.write_text(json.dumps({"last_classified_turn": 5}))

        # Turn 6, 7, 8 should be same topic
        for turn in [6, 7, 8]:
            input_data = {"turnCount": turn}
            result = self.hook.is_new_topic("Some follow-up work", input_data)
            assert result is False, f"Turn {turn} should be same topic (last classified at 5)"

        # Turn 9 should be new topic (more than 3 turns)
        input_data = {"turnCount": 9}
        result = self.hook.is_new_topic("Some new work", input_data)
        assert result is True, "Turn 9 should be new topic (>3 turns since last classification)"


class TestReminderGeneration:
    """Test reminder message generation."""

    def setup_method(self):
        """Set up test environment."""
        import unittest.mock

        with unittest.mock.patch.object(WorkflowClassificationReminder, "_init_state_dir"):
            self.hook = WorkflowClassificationReminder()

        self.hook._state_dir = Path("/tmp/test_classification_state")
        self.hook._state_dir.mkdir(parents=True, exist_ok=True)
        self.hook.get_session_id = lambda: "test_session_123"

    def test_reminder_contains_classification_options(self):
        """Reminder should list all three workflow options."""
        reminder = self.hook.build_reminder("Implement feature X")

        assert "Q&A" in reminder
        assert "INVESTIGATION" in reminder
        assert "DEFAULT" in reminder

    def test_reminder_contains_user_prompt_excerpt(self):
        """Reminder should include excerpt of user prompt."""
        prompt = "This is a very long user prompt that should be truncated in the reminder"
        reminder = self.hook.build_reminder(prompt)

        # Should contain start of prompt (truncated to 100 chars)
        assert "This is a very long user prompt" in reminder

    def test_reminder_contains_required_actions(self):
        """Reminder should specify required actions."""
        reminder = self.hook.build_reminder("Add feature")

        assert "WORKFLOW:" in reminder
        assert "Reason:" in reminder
        # Should mention execution method (recipes tool or direct execution)
        assert "Execute recipes tool" in reminder or "Execute directly" in reminder

    def test_reminder_formatted_as_system_reminder(self):
        """Process should wrap reminder in system-reminder tags."""
        input_data = {"userMessage": "New topic here", "turnCount": 0}

        result = self.hook.process(input_data)

        assert "additionalContext" in result
        assert (
            '<system-reminder source="hooks-workflow-classification">'
            in result["additionalContext"]
        )
        assert "</system-reminder>" in result["additionalContext"]


class TestHookIntegration:
    """Test full hook processing flow."""

    def setup_method(self):
        """Set up test environment."""
        import unittest.mock

        with unittest.mock.patch.object(WorkflowClassificationReminder, "_init_state_dir"):
            self.hook = WorkflowClassificationReminder()

        self.hook._state_dir = Path("/tmp/test_classification_state")
        self.hook._state_dir.mkdir(parents=True, exist_ok=True)
        self.hook.get_session_id = lambda: "test_session_123"

    def teardown_method(self):
        """Clean up test state."""
        import shutil

        if self.hook._state_dir.exists():
            shutil.rmtree(self.hook._state_dir)

    def test_first_prompt_triggers_reminder(self):
        """First user prompt should trigger classification reminder."""
        input_data = {"userMessage": "Implement user authentication", "turnCount": 0}

        result = self.hook.process(input_data)

        assert "additionalContext" in result
        assert "NEW TOPIC DETECTED" in result["additionalContext"]
        assert "Workflow Classification Required" in result["additionalContext"]

    def test_followup_no_reminder(self):
        """Follow-up prompts should not trigger reminder."""
        # Simulate prior classification
        state_file = self.hook.get_session_state_file()
        state_file.write_text(json.dumps({"last_classified_turn": 3}))

        input_data = {"userMessage": "Also add logout functionality", "turnCount": 5}

        result = self.hook.process(input_data)

        # Should return empty dict (no injection)
        assert result == {}

    def test_state_persisted_after_classification(self):
        """Hook should persist classification state."""
        input_data = {"userMessage": "New topic", "turnCount": 7}

        self.hook.process(input_data)

        # State file should exist and contain turn count
        state_file = self.hook.get_session_state_file()
        assert state_file.exists()

        state = json.loads(state_file.read_text())
        assert state["last_classified_turn"] == 7

    def test_explicit_transition_triggers_reminder(self):
        """Explicit transition should trigger reminder even after recent classification."""
        # Simulate recent classification
        state_file = self.hook.get_session_state_file()
        state_file.write_text(json.dumps({"last_classified_turn": 8}))

        input_data = {"userMessage": "Now let's switch to testing", "turnCount": 9}

        result = self.hook.process(input_data)

        assert "additionalContext" in result
        assert "NEW TOPIC DETECTED" in result["additionalContext"]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Set up test environment."""
        import unittest.mock

        with unittest.mock.patch.object(WorkflowClassificationReminder, "_init_state_dir"):
            self.hook = WorkflowClassificationReminder()

        self.hook._state_dir = Path("/tmp/test_classification_state")
        self.hook._state_dir.mkdir(parents=True, exist_ok=True)
        self.hook.get_session_id = lambda: "test_session_123"

    def teardown_method(self):
        """Clean up test state."""
        import shutil

        if self.hook._state_dir.exists():
            shutil.rmtree(self.hook._state_dir)

    def test_corrupted_state_file_graceful_failure(self):
        """Corrupted state file should be ignored, not crash."""
        state_file = self.hook.get_session_state_file()
        state_file.write_text("corrupted json {{{")

        input_data = {"userMessage": "Some request", "turnCount": 5}

        # Should not raise exception
        result = self.hook.is_new_topic("Some request", input_data)

        # Should default to new topic when state is corrupted
        assert result is True

    def test_missing_turn_count_defaults_to_new_topic(self):
        """Missing turnCount should be treated as new topic."""
        input_data = {"userMessage": "Request without turnCount"}

        result = self.hook.is_new_topic("Request without turnCount", input_data)
        assert result is True

    def test_dict_user_message_format(self):
        """Should handle userMessage as dict with 'text' field."""
        input_data = {
            "userMessage": {"text": "Implement feature", "metadata": {"source": "cli"}},
            "turnCount": 0,
        }

        result = self.hook.process(input_data)

        assert "additionalContext" in result
        assert "Implement feature" in result["additionalContext"]

    def test_empty_user_message(self):
        """Empty user message should not crash."""
        input_data = {"userMessage": "", "turnCount": 0}

        # Should not raise exception
        result = self.hook.process(input_data)
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
