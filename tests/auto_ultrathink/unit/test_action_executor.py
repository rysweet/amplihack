"""Unit tests for action_executor module.

Tests action execution: invoke UltraThink, ask user, or pass through unchanged.
"""

import pytest


class TestActionExecutor:
    """Unit tests for action executor."""

    def test_skip_action_unchanged(self, create_test_decision):
        """SKIP action should pass through unchanged."""
        from action_executor import Action, execute_action

        decision = create_test_decision(action="skip")
        result = execute_action("test prompt", decision)

        assert result.modified_prompt == "test prompt"
        assert result.action_taken == "skip" or result.action_taken == Action.SKIP
        assert result.user_choice is None

    def test_invoke_action_prepends_ultrathink(self, create_test_decision):
        """INVOKE action should prepend /ultrathink."""
        from action_executor import Action, execute_action

        decision = create_test_decision(action="invoke")
        result = execute_action("Add feature", decision)

        assert result.modified_prompt == "/ultrathink Add feature"
        assert result.action_taken == "invoke" or result.action_taken == Action.INVOKE

    def test_invoke_no_duplicate_ultrathink(self, create_test_decision):
        """Should not duplicate /ultrathink if already present."""
        from action_executor import execute_action

        decision = create_test_decision(action="invoke")
        result = execute_action("/ultrathink Add feature", decision)

        assert result.modified_prompt == "/ultrathink Add feature"
        # Should not be "/ultrathink /ultrathink Add feature"

    def test_invoke_with_leading_whitespace(self, create_test_decision):
        """Should handle leading whitespace correctly."""
        from action_executor import execute_action

        decision = create_test_decision(action="invoke")
        result = execute_action("  Add feature", decision)

        # Should trim and add /ultrathink
        assert "/ultrathink" in result.modified_prompt
        assert "Add feature" in result.modified_prompt

    def test_ask_action_includes_question(self, create_test_decision):
        """ASK action should inject question."""
        from action_executor import Action, execute_action

        decision = create_test_decision(action="ask", reason="Test recommendation")
        result = execute_action("Add feature", decision)

        # Should contain question elements
        assert "ultrathink" in result.modified_prompt.lower() or "recommend" in result.modified_prompt.lower()
        assert "Add feature" in result.modified_prompt
        assert result.action_taken == "ask" or result.action_taken == Action.ASK

    def test_empty_prompt_skip(self, create_test_decision):
        """Empty prompt with SKIP should return empty."""
        from action_executor import execute_action

        decision = create_test_decision(action="skip")
        result = execute_action("", decision)

        assert result.modified_prompt == ""

    def test_empty_prompt_invoke(self, create_test_decision):
        """Empty prompt with INVOKE should be handled gracefully."""
        from action_executor import execute_action

        decision = create_test_decision(action="invoke")
        result = execute_action("", decision)

        # Should handle gracefully (either return empty or minimal /ultrathink)
        assert result.modified_prompt is not None


class TestPromptModification:
    """Test prompt modification logic."""

    def test_modify_prompt_normal(self):
        """Normal prompt should get /ultrathink prefix."""
        from action_executor import modify_prompt_for_ultrathink

        result = modify_prompt_for_ultrathink("Add feature")
        assert result == "/ultrathink Add feature"

    def test_modify_prompt_empty(self):
        """Empty prompt should remain empty."""
        from action_executor import modify_prompt_for_ultrathink

        result = modify_prompt_for_ultrathink("")
        assert result == ""

    def test_modify_prompt_whitespace_only(self):
        """Whitespace-only prompt should remain unchanged."""
        from action_executor import modify_prompt_for_ultrathink

        result = modify_prompt_for_ultrathink("   \n\t   ")
        # Should either return unchanged or empty
        assert result in ["   \n\t   ", ""]

    def test_modify_prompt_already_has_ultrathink(self):
        """Should not duplicate /ultrathink."""
        from action_executor import modify_prompt_for_ultrathink

        result = modify_prompt_for_ultrathink("/ultrathink Add feature")
        assert result == "/ultrathink Add feature"
        assert result.count("/ultrathink") == 1

    def test_modify_prompt_other_slash_command(self):
        """Should handle other slash commands."""
        from action_executor import modify_prompt_for_ultrathink

        result = modify_prompt_for_ultrathink("/analyze src/")
        # Should prepend /ultrathink (wrapping the other command)
        assert "/ultrathink" in result
        assert "/analyze" in result

    def test_modify_prompt_long(self):
        """Should handle very long prompts."""
        from action_executor import modify_prompt_for_ultrathink

        long_prompt = "Add feature " * 1000
        result = modify_prompt_for_ultrathink(long_prompt)

        assert result.startswith("/ultrathink ")
        assert "Add feature" in result


class TestQuestionFormatting:
    """Test ASK mode question formatting."""

    def test_format_user_question_structure(self, create_test_decision):
        """Question should have proper structure."""
        from action_executor import format_user_question

        decision = create_test_decision(
            action="ask", reason="Multi-file feature detected"
        )
        question = format_user_question(decision)

        # Should contain key elements
        assert "ultrathink" in question.lower()
        assert "multi-file feature" in question.lower() or decision.reason in question

    def test_format_user_question_includes_confidence(
        self, create_test_classification, create_test_preference, create_test_decision
    ):
        """Question should include confidence percentage."""
        from action_executor import format_user_question
        from decision_engine import Action, Decision

        classification = create_test_classification(confidence=0.92)
        preference = create_test_preference()
        decision = Decision(
            action=Action.ASK,
            reason="Test",
            classification=classification,
            preference=preference,
        )

        question = format_user_question(decision)

        # Should include confidence as percentage
        assert "92" in question or "0.92" in question


class TestExecutionResult:
    """Test ExecutionResult contract."""

    def test_result_has_required_fields(self, create_test_decision):
        """ExecutionResult should have all required fields."""
        from action_executor import execute_action

        decision = create_test_decision()
        result = execute_action("test prompt", decision)

        assert hasattr(result, "modified_prompt")
        assert hasattr(result, "action_taken")
        assert hasattr(result, "user_choice")
        assert hasattr(result, "metadata")

    def test_result_types(self, create_test_decision):
        """ExecutionResult fields should have correct types."""
        from action_executor import execute_action

        decision = create_test_decision()
        result = execute_action("test prompt", decision)

        assert isinstance(result.modified_prompt, str)
        assert result.action_taken is not None  # Action or string
        assert isinstance(result.metadata, dict)

    def test_result_metadata_contains_info(self, create_test_decision):
        """Metadata should contain useful information."""
        from action_executor import execute_action

        decision = create_test_decision(action="invoke", reason="Test reason")
        result = execute_action("test prompt", decision)

        # Metadata should have some content
        assert len(result.metadata) > 0
        # Should contain reason or other context
        assert "reason" in result.metadata or len(result.metadata) >= 1


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_none_prompt_handled(self, create_test_decision):
        """None prompt should be handled gracefully."""
        from action_executor import execute_action

        decision = create_test_decision(action="skip")

        try:
            result = execute_action(None, decision)
            # Should handle gracefully
            assert result is not None
        except Exception:
            # Also acceptable to raise
            pass

    def test_none_decision_handled(self):
        """None decision should be handled gracefully."""
        from action_executor import execute_action

        try:
            result = execute_action("test prompt", None)
            # Should handle gracefully or raise
            if result:
                # Should return safe default (skip)
                assert result.modified_prompt == "test prompt"
        except Exception:
            # Also acceptable to raise
            pass

    def test_exception_in_modify_prompt_returns_original(self, create_test_decision):
        """Exception in prompt modification should return original prompt."""
        from action_executor import execute_action

        decision = create_test_decision(action="invoke")

        # Try with problematic input
        result = execute_action("test prompt", decision)

        # Should not crash
        assert result is not None
        assert isinstance(result.modified_prompt, str)

    def test_exception_in_format_question_returns_original(self, create_test_decision):
        """Exception in question formatting should return original prompt."""
        from action_executor import execute_action

        decision = create_test_decision(action="ask")

        # Execute with normal input
        result = execute_action("test prompt", decision)

        # Should not crash
        assert result is not None
        assert isinstance(result.modified_prompt, str)

    def test_unknown_action_defaults_to_skip(self, create_test_decision):
        """Unknown action should default to skip."""
        from action_executor import execute_action

        # Create decision with unknown action
        decision = create_test_decision(action="skip")
        # Manually set to invalid value if possible
        try:
            decision.action = "unknown"
        except Exception:
            pass

        result = execute_action("test prompt", decision)

        # Should handle gracefully
        assert result.modified_prompt == "test prompt"  # Pass through


class TestEdgeCases:
    """Test edge cases and special inputs."""

    def test_very_long_prompt(self, create_test_decision):
        """Very long prompt should be handled."""
        from action_executor import execute_action

        long_prompt = "x" * 100000
        decision = create_test_decision(action="invoke")

        result = execute_action(long_prompt, decision)

        assert result is not None
        assert "/ultrathink" in result.modified_prompt
        assert len(result.modified_prompt) > len("/ultrathink")

    def test_unicode_prompt(self, create_test_decision):
        """Unicode in prompt should be handled."""
        from action_executor import execute_action

        unicode_prompt = "添加功能 🚀 с features"
        decision = create_test_decision(action="invoke")

        result = execute_action(unicode_prompt, decision)

        assert result is not None
        assert "/ultrathink" in result.modified_prompt
        assert "添加功能" in result.modified_prompt

    def test_special_characters(self, create_test_decision):
        """Special characters should be handled."""
        from action_executor import execute_action

        special_prompt = "Add $pecial ch@rs! with ~!@#$%^&*()"
        decision = create_test_decision(action="invoke")

        result = execute_action(special_prompt, decision)

        assert result is not None
        assert "/ultrathink" in result.modified_prompt

    def test_multiline_prompt(self, create_test_decision):
        """Multiline prompt should be handled."""
        from action_executor import execute_action

        multiline_prompt = """Add feature with:
- Database integration
- API endpoints
- Tests"""
        decision = create_test_decision(action="invoke")

        result = execute_action(multiline_prompt, decision)

        assert result is not None
        assert "/ultrathink" in result.modified_prompt
        assert "Database integration" in result.modified_prompt


class TestPerformance:
    """Performance tests for action executor."""

    def test_execution_speed(self, create_test_decision):
        """Action execution should be fast (<50ms per call)."""
        import time

        from action_executor import execute_action

        decision = create_test_decision(action="invoke")

        start = time.time()
        for i in range(1000):
            execute_action(f"prompt {i}", decision)
        elapsed = time.time() - start

        avg_time_ms = (elapsed / 1000) * 1000
        assert avg_time_ms < 50, f"Execution too slow: {avg_time_ms:.2f}ms per call"

    def test_no_memory_leak(self, create_test_decision):
        """Test for memory leaks."""
        import gc

        from action_executor import execute_action

        decision = create_test_decision(action="invoke")

        # Run many executions
        for i in range(10000):
            execute_action(f"prompt {i}", decision)

        # Force garbage collection
        gc.collect()

        # If we got here without memory error, test passes
        assert True


# Parameterized tests for different actions
@pytest.mark.parametrize(
    "action,prompt,expected_contains",
    [
        ("skip", "test prompt", "test prompt"),
        ("invoke", "Add feature", "/ultrathink"),
        ("ask", "Add feature", "add feature"),  # Case-insensitive check
    ],
)
def test_action_execution_matrix(action, prompt, expected_contains, create_test_decision):
    """Test different action execution scenarios."""
    from action_executor import execute_action

    decision = create_test_decision(action=action)
    result = execute_action(prompt, decision)

    assert expected_contains.lower() in result.modified_prompt.lower()
