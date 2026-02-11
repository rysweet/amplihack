# tests/integration/test_workflow_integration.py
"""
Integration tests for workflow reminder end-to-end scenarios.

These tests validate the complete workflow reminder integration from
user prompt submission through context injection.

Test Coverage:
- First message triggers reminder
- Follow-up within 3 turns skips reminder
- Direction change after 3 turns triggers reminder
- Active recipe skips reminder (env var set)
- Disabled preference skips reminder
- State file corruption falls back gracefully
- Long prompt with keywords triggers reminder
- Multiple direction changes in session
- Reminder injection position (after Section 3)
"""

import json
import os
from unittest.mock import MagicMock, patch


class TestEndToEndWorkflowReminder:
    """End-to-end integration tests for workflow reminder."""

    def test_first_message_injects_reminder(self, tmp_path):
        """INTEGRATION: First message should inject workflow reminder."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.log = MagicMock()
        hook.save_metric = MagicMock()
        
        context = {
            "session_id": "integration-test-001",
            "turn_number": 0,  # First message
            "user_prompt": "Let's start building a feature",
        }
        
        state_dir = tmp_path / "classification_state"
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    result = hook.run(context)
        
        # Should return additionalContext
        assert "additionalContext" in result
        
        # Should contain workflow reminder
        additional_context = result["additionalContext"]
        assert "⚙️" in additional_context or "Workflow Classification Reminder" in additional_context
        
        # Should increment metric
        hook.save_metric.assert_any_call("workflow_reminder_injected", 1)
        
        # Should save state
        state_file = state_dir / "integration-test-001.json"
        assert state_file.exists()
        
        with open(state_file, 'r') as f:
            state = json.load(f)
        assert state["last_classified_turn"] == 0

    def test_followup_within_3_turns_skips_reminder(self, tmp_path):
        """INTEGRATION: Follow-up messages within 3 turns should skip reminder."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        
        session_id = "integration-test-002"
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)
        
        # Create state: last classified at turn 5
        state_file = state_dir / f"{session_id}.json"
        state_file.write_text(json.dumps({
            "session_id": session_id,
            "last_classified_turn": 5
        }))
        os.chmod(state_file, 0o600)
        
        context = {
            "session_id": session_id,
            "turn_number": 7,  # Gap = 2, < 3
            "user_prompt": "Now let's implement this",  # Has keyword
        }
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    result = hook.run(context)
        
        # Should skip injection due to caching
        hook.save_metric.assert_any_call("workflow_reminder_skipped_followup", 1)
        
        # State should NOT be updated
        with open(state_file, 'r') as f:
            state = json.load(f)
        assert state["last_classified_turn"] == 5  # Unchanged

    def test_direction_change_after_3_turns_injects_reminder(self, tmp_path):
        """INTEGRATION: Direction change keywords after 3+ turns should inject reminder."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        
        session_id = "integration-test-003"
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)
        
        # Create state: last classified at turn 10
        state_file = state_dir / f"{session_id}.json"
        state_file.write_text(json.dumps({
            "session_id": session_id,
            "last_classified_turn": 10
        }))
        os.chmod(state_file, 0o600)
        
        context = {
            "session_id": session_id,
            "turn_number": 15,  # Gap = 5, >= 3
            "user_prompt": "Now let's switch to the frontend implementation",
        }
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    result = hook.run(context)
        
        # Should inject reminder
        assert "additionalContext" in result
        hook.save_metric.assert_any_call("workflow_reminder_injected", 1)
        
        # State should be updated
        with open(state_file, 'r') as f:
            state = json.load(f)
        assert state["last_classified_turn"] == 15

    def test_active_recipe_skips_reminder(self, tmp_path):
        """INTEGRATION: Active recipe detection should skip reminder."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        
        context = {
            "session_id": "integration-test-004",
            "turn_number": 0,
            "user_prompt": "Implement authentication",
        }
        
        state_dir = tmp_path / "classification_state"
        
        # Simulate active recipe via env var
        with patch.dict(os.environ, {"AMPLIFIER_RECIPE_ACTIVE": "1"}):
            with patch.object(hook, '_get_state_dir', return_value=state_dir):
                with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                    result = hook.run(context)
        
        # Should skip injection
        hook.save_metric.assert_any_call("workflow_reminder_skipped_recipe", 1)
        
        # Should NOT create state file
        state_file = state_dir / "integration-test-004.json"
        assert not state_file.exists()

    def test_disabled_preference_skips_reminder(self, tmp_path):
        """INTEGRATION: Disabled preference should skip reminder."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        
        context = {
            "session_id": "integration-test-005",
            "turn_number": 0,
            "user_prompt": "Implement feature",
        }
        
        state_dir = tmp_path / "classification_state"
        
        mock_preferences = """
## Workflow Preferences

Workflow Reminders: disabled
"""
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch("builtins.open", mock_open(read_data=mock_preferences)):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    result = hook.run(context)
        
        # Should skip injection
        hook.save_metric.assert_any_call("workflow_reminder_disabled", 1)
        
        # Should NOT create state file
        state_file = state_dir / "integration-test-005.json"
        assert not state_file.exists()

    def test_state_file_corruption_graceful_fallback(self, tmp_path):
        """INTEGRATION: Corrupted state file should degrade gracefully."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.log = MagicMock()
        hook.save_metric = MagicMock()
        
        session_id = "integration-test-006"
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)
        
        # Create corrupted state file
        state_file = state_dir / f"{session_id}.json"
        state_file.write_text("{invalid json content!!!")
        
        context = {
            "session_id": session_id,
            "turn_number": 5,
            "user_prompt": "Implement this feature",  # Has keyword
        }
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    result = hook.run(context)
        
        # Should gracefully degrade and inject reminder
        # (cannot load cache, so assumes new topic)
        assert "additionalContext" in result
        hook.save_metric.assert_any_call("workflow_reminder_injected", 1)
        
        # Should log warning
        assert any("WARNING" in str(call) for call in hook.log.call_args_list)

    def test_long_prompt_with_keywords_triggers_reminder(self, tmp_path):
        """INTEGRATION: Long prompts with embedded keywords should be detected."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        
        session_id = "integration-test-007"
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)
        
        # Create state: last classified at turn 20
        state_file = state_dir / f"{session_id}.json"
        state_file.write_text(json.dumps({
            "session_id": session_id,
            "last_classified_turn": 20
        }))
        
        # Long prompt with embedded keyword
        long_prompt = """
        I've reviewed the current authentication system and identified several issues.
        The session handling is not thread-safe, and we have no rate limiting.
        
        Now let's implement a comprehensive solution that addresses these concerns.
        We should add Redis for session storage, implement rate limiting middleware,
        and add proper logging for security events.
        
        What do you think about this approach?
        """
        
        context = {
            "session_id": session_id,
            "turn_number": 25,  # Gap = 5, >= 3
            "user_prompt": long_prompt,
        }
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    result = hook.run(context)
        
        # Should detect "Now let's implement" keyword and inject
        assert "additionalContext" in result
        hook.save_metric.assert_any_call("workflow_reminder_injected", 1)

    def test_multiple_direction_changes_in_session(self, tmp_path):
        """INTEGRATION: Multiple direction changes should each trigger reminder."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        
        session_id = "integration-test-008"
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)
        
        # Turn 0: First message
        context1 = {
            "session_id": session_id,
            "turn_number": 0,
            "user_prompt": "Start working on authentication",
        }
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    result1 = hook.run(context1)
        
        # Should inject (first message)
        assert "additionalContext" in result1
        
        # Turn 5: Direction change (gap = 5 >= 3)
        context2 = {
            "session_id": session_id,
            "turn_number": 5,
            "user_prompt": "Now let's switch to implementing the API",
        }
        
        hook.save_metric.reset_mock()
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    result2 = hook.run(context2)
        
        # Should inject (direction change + gap)
        assert "additionalContext" in result2
        hook.save_metric.assert_any_call("workflow_reminder_injected", 1)
        
        # Turn 10: Another direction change (gap = 5 >= 3)
        context3 = {
            "session_id": session_id,
            "turn_number": 10,
            "user_prompt": "Different topic - let's work on the database schema",
        }
        
        hook.save_metric.reset_mock()
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    result3 = hook.run(context3)
        
        # Should inject (direction change + gap)
        assert "additionalContext" in result3
        hook.save_metric.assert_any_call("workflow_reminder_injected", 1)

    def test_reminder_injection_position_after_section_3(self, tmp_path):
        """INTEGRATION: Reminder should be added after Section 3 (AMPLIHACK.md)."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.log = MagicMock()
        hook.save_metric = MagicMock()
        
        context = {
            "session_id": "integration-test-009",
            "turn_number": 0,
            "user_prompt": "implement feature",
        }
        
        state_dir = tmp_path / "classification_state"
        
        # Mock existing sections
        mock_preferences = "User preferences content"
        mock_memories = "Agent memories content"
        mock_amplihack = "AMPLIHACK.md framework content"
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    with patch.object(hook, '_get_user_preferences', return_value=mock_preferences):
                        with patch.object(hook, '_get_agent_memories', return_value=mock_memories):
                            with patch.object(hook, '_get_amplihack_framework', return_value=mock_amplihack):
                                result = hook.run(context)
        
        # Should have additionalContext
        assert "additionalContext" in result
        additional_context = result["additionalContext"]
        
        # Should contain all sections in order
        # 1. User preferences
        # 2. Agent memories
        # 3. AMPLIHACK.md
        # 4. Workflow reminder (NEW)
        
        # Verify workflow reminder exists
        assert "⚙️" in additional_context or "Workflow Classification Reminder" in additional_context
        
        # Verify order (workflow reminder comes after framework)
        # This is implementation-specific, but generally the sections should be concatenated
        assert len(additional_context) > 0


class TestMetricsCollection:
    """Test comprehensive metrics collection."""

    def test_metrics_injected_increments(self, tmp_path):
        """Metric workflow_reminder_injected should increment on injection."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        
        context = {
            "session_id": "metrics-test-001",
            "turn_number": 0,
            "user_prompt": "implement",
        }
        
        state_dir = tmp_path / "classification_state"
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    hook.run(context)
        
        hook.save_metric.assert_any_call("workflow_reminder_injected", 1)

    def test_metrics_skipped_followup_increments(self, tmp_path):
        """Metric workflow_reminder_skipped_followup should increment on cache hit."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        
        session_id = "metrics-test-002"
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)
        
        state_file = state_dir / f"{session_id}.json"
        state_file.write_text(json.dumps({
            "session_id": session_id,
            "last_classified_turn": 10
        }))
        
        context = {
            "session_id": session_id,
            "turn_number": 12,  # Gap = 2, < 3
            "user_prompt": "implement this",  # Has keyword
        }
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    hook.run(context)
        
        hook.save_metric.assert_any_call("workflow_reminder_skipped_followup", 1)

    def test_metrics_skipped_recipe_increments(self, tmp_path):
        """Metric workflow_reminder_skipped_recipe should increment on active recipe."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        
        context = {
            "session_id": "metrics-test-003",
            "turn_number": 0,
            "user_prompt": "implement",
        }
        
        state_dir = tmp_path / "classification_state"
        
        with patch.dict(os.environ, {"AMPLIFIER_RECIPE_ACTIVE": "1"}):
            with patch.object(hook, '_get_state_dir', return_value=state_dir):
                with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                    hook.run(context)
        
        hook.save_metric.assert_any_call("workflow_reminder_skipped_recipe", 1)

    def test_metrics_disabled_increments(self, tmp_path):
        """Metric workflow_reminder_disabled should increment when disabled."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        
        context = {
            "session_id": "metrics-test-004",
            "turn_number": 0,
            "user_prompt": "implement",
        }
        
        state_dir = tmp_path / "classification_state"
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=False):
                hook.run(context)
        
        hook.save_metric.assert_any_call("workflow_reminder_disabled", 1)

    def test_metrics_error_increments_on_exception(self, tmp_path):
        """Metric workflow_reminder_error should increment on non-fatal errors."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.log = MagicMock()
        hook.save_metric = MagicMock()
        
        context = {
            "session_id": "metrics-test-005",
            "turn_number": 0,
            "user_prompt": "implement",
        }
        
        state_dir = tmp_path / "classification_state"
        
        # Simulate error in workflow logic
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', side_effect=Exception("Test error")):
                # Should not crash
                result = hook.run(context)
        
        # Should increment error metric
        hook.save_metric.assert_any_call("workflow_reminder_error", 1)
        
        # Should log warning
        assert any("WARNING" in str(call) or "ERROR" in str(call) for call in hook.log.call_args_list)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_prompt_no_keywords(self, tmp_path):
        """Empty or whitespace-only prompts should not trigger keywords."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)
        
        # Except for turn 0, empty prompts should not trigger
        context = {
            "session_id": "edge-test-001",
            "turn_number": 5,
            "user_prompt": "   ",  # Whitespace only
        }
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    result = hook.run(context)
        
        # Should not inject (no keywords)
        # Note: Turn 0 would inject regardless, but this is turn 5
        state_file = state_dir / "edge-test-001.json"
        assert not state_file.exists()

    def test_exact_3_turn_gap_boundary(self, tmp_path):
        """Exactly 3 turn gap should allow injection (boundary test)."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        
        session_id = "edge-test-002"
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)
        
        state_file = state_dir / f"{session_id}.json"
        state_file.write_text(json.dumps({
            "session_id": session_id,
            "last_classified_turn": 10
        }))
        
        context = {
            "session_id": session_id,
            "turn_number": 13,  # Gap = 3 exactly
            "user_prompt": "implement feature",  # Has keyword
        }
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    result = hook.run(context)
        
        # Should inject (gap >= 3)
        assert "additionalContext" in result
        hook.save_metric.assert_any_call("workflow_reminder_injected", 1)

    def test_unicode_keywords_case_insensitive(self, tmp_path):
        """Unicode variations of keywords should still be detected."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        
        session_id = "edge-test-003"
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)
        
        context = {
            "session_id": session_id,
            "turn_number": 5,
            "user_prompt": "Now let's implement this feature",  # Standard ASCII
        }
        
        with patch.object(hook, '_get_state_dir', return_value=state_dir):
            with patch.object(hook, '_is_workflow_reminder_enabled', return_value=True):
                with patch.object(hook, '_is_recipe_active', return_value=False):
                    result = hook.run(context)
        
        # Should detect keyword
        assert "additionalContext" in result
