"""Integration tests for user_prompt_submit hook and preference injection.

Tests the integration between user prompt submission and preference injection system.
Ensures preferences are consistently injected on every message in REPL mode.
"""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.asyncio


class TestUserPromptSubmitIntegration:
    """Integration tests for UserPromptSubmit hook preference injection."""

    @pytest.fixture
    def temp_project_root(self):
        """Create temporary project root with preferences."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create necessary directory structure
            claude_dir = temp_path / ".claude"
            (claude_dir / "runtime" / "logs").mkdir(parents=True)
            (claude_dir / "context").mkdir(parents=True)
            (claude_dir / "tools" / "amplihack" / "hooks").mkdir(parents=True)

            # Create USER_PREFERENCES.md with pirate preference
            prefs_file = claude_dir / "context" / "USER_PREFERENCES.md"
            prefs_file.write_text("""# User Preferences

## MANDATORY - These preferences MUST be followed

### Communication Style
pirate (Always talk like a pirate)

### Verbosity
balanced

### Collaboration Style
interactive

### Update Frequency
regular

### Priority Type
balanced
""")
            yield temp_path

    @pytest.fixture
    def mock_user_prompt_submit_hook(self, temp_project_root):
        """Mock user_prompt_submit hook with temp project root."""
        # Add hook directory to path
        project_root = Path(__file__).parent.parent
        hooks_dir = project_root / ".claude" / "tools" / "amplihack" / "hooks"
        sys.path.insert(0, str(hooks_dir))

        try:
            from user_prompt_submit import UserPromptSubmitHook

            # Create hook instance
            hook = UserPromptSubmitHook()

            # Override project_root to use temp location
            hook.project_root = temp_project_root
            hook.log_dir = temp_project_root / ".claude" / "runtime" / "logs"
            hook.metrics_dir = temp_project_root / ".claude" / "runtime" / "metrics"

            # Ensure directories exist
            hook.log_dir.mkdir(parents=True, exist_ok=True)
            hook.metrics_dir.mkdir(parents=True, exist_ok=True)

            # Override find_user_preferences to only look in temp location
            original_find = hook.find_user_preferences

            def temp_find():
                pref_file = temp_project_root / ".claude" / "context" / "USER_PREFERENCES.md"
                if pref_file.exists():
                    return pref_file
                return None

            hook.find_user_preferences = temp_find

            yield hook
        finally:
            sys.path.pop(0)

    def test_user_prompt_submit_injects_preferences(self, mock_user_prompt_submit_hook):
        """Test that hook injects preferences on every message."""
        input_data = {
            "session_id": "test_123",
            "hook_event_name": "UserPromptSubmit",
            "prompt": "Tell me about Python",
        }

        result = mock_user_prompt_submit_hook.process(input_data)

        # Should return proper format with additionalContext
        assert "additionalContext" in result
        assert isinstance(result["additionalContext"], str)

        # Should contain preference text
        context = result["additionalContext"]
        assert len(context) > 0, "Context should not be empty"

        # Check for key indicators of preference injection
        assert (
            "PREFERENCES" in context or "preferences" in context.lower()
        ), "Should mention preferences"
        assert (
            "Communication Style" in context or "pirate" in context.lower()
        ), "Should include communication style"

    def test_pirate_preference_detection(self, mock_user_prompt_submit_hook):
        """Test specifically with pirate communication style."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "What is machine learning?",
        }

        result = mock_user_prompt_submit_hook.process(input_data)
        context = result["additionalContext"]

        # Should explicitly mention pirate style
        assert "pirate" in context.lower(), "Should explicitly mention pirate communication style"

        # Should include enforcement instruction
        assert (
            "style" in context.lower() or "response" in context.lower()
        ), "Should include style enforcement"

        # Should be in active preferences section
        assert "ACTIVE" in context or "MANDATORY" in context, "Should emphasize preference is active"

    def test_preference_consistency_across_messages(self, mock_user_prompt_submit_hook):
        """Test that preferences are injected consistently across multiple messages."""
        test_prompts = [
            "Tell me about Python",
            "Explain Docker",
            "What is REST API?",
            "Describe machine learning",
            "What are best practices?",
        ]

        results = []
        context_lengths = []

        for prompt in test_prompts:
            input_data = {"hook_event_name": "UserPromptSubmit", "prompt": prompt}

            result = mock_user_prompt_submit_hook.process(input_data)
            context = result["additionalContext"]

            # Track if context was injected
            has_context = len(context) > 0 and "pirate" in context.lower()
            results.append(has_context)
            context_lengths.append(len(context))

        # ALL messages should have preferences injected
        assert all(results), f"Consistency: {sum(results)}/{len(results)} (expected 100%)"

        # Calculate and verify consistency rate
        consistency_rate = sum(results) / len(results) * 100
        assert consistency_rate == 100.0, f"Expected 100% consistency, got {consistency_rate}%"

        # Context lengths should be similar (within reasonable variance)
        avg_length = sum(context_lengths) / len(context_lengths)
        for length in context_lengths:
            # Allow 20% variance
            assert abs(length - avg_length) / avg_length < 0.2, "Context lengths should be consistent"

    def test_multiple_preferences_simultaneously(self, mock_user_prompt_submit_hook):
        """Test with multiple preferences set."""
        input_data = {"hook_event_name": "UserPromptSubmit", "prompt": "Analyze this code"}

        result = mock_user_prompt_submit_hook.process(input_data)
        context = result["additionalContext"]

        # Should include multiple preference types
        expected_preferences = [
            "Communication Style",
            "Verbosity",
            "Collaboration Style",
            "Update Frequency",
            "Priority Type",
        ]

        found_count = sum(1 for pref in expected_preferences if pref in context)

        # Should find at least 4 out of 5 preferences
        assert (
            found_count >= 4
        ), f"Should include most preferences, found {found_count}/{len(expected_preferences)}"

        # Check proper formatting with bullet points
        assert "•" in context or "-" in context or "*" in context, "Should use bullet points"

        # Should have MANDATORY enforcement
        assert "MANDATORY" in context or "MUST" in context, "Should emphasize mandatory nature"

    def test_missing_preferences_file(self, temp_project_root):
        """Test when USER_PREFERENCES.md doesn't exist."""
        # Create hook with project root that has no preferences file
        project_root = Path(__file__).parent.parent
        hooks_dir = project_root / ".claude" / "tools" / "amplihack" / "hooks"
        sys.path.insert(0, str(hooks_dir))

        try:
            from user_prompt_submit import UserPromptSubmitHook

            # Create new temp directory WITHOUT preferences file
            with tempfile.TemporaryDirectory() as empty_temp_str:
                empty_temp = Path(empty_temp_str)
                (empty_temp / ".claude" / "runtime" / "logs").mkdir(parents=True)
                (empty_temp / ".claude" / "runtime" / "metrics").mkdir(parents=True)
                (empty_temp / ".claude" / "context").mkdir(parents=True)

                hook = UserPromptSubmitHook()
                hook.project_root = empty_temp
                hook.log_dir = empty_temp / ".claude" / "runtime" / "logs"
                hook.metrics_dir = empty_temp / ".claude" / "runtime" / "metrics"

                # Override find_user_preferences to only look in empty temp location
                def empty_find():
                    pref_file = empty_temp / ".claude" / "context" / "USER_PREFERENCES.md"
                    if pref_file.exists():
                        return pref_file
                    return None

                hook.find_user_preferences = empty_find

                # Clear cache to ensure fresh read
                hook._preferences_cache = None
                hook._cache_timestamp = None

                input_data = {"hook_event_name": "UserPromptSubmit", "prompt": "Test prompt"}

                # Should not crash
                result = hook.process(input_data)

                # Should return empty additionalContext gracefully
                assert "additionalContext" in result
                assert result["additionalContext"] == "", "Should return empty context when no preferences"

        finally:
            sys.path.pop(0)

    def test_performance_caching(self, mock_user_prompt_submit_hook):
        """Test that caching improves performance."""
        input_data = {"hook_event_name": "UserPromptSubmit", "prompt": "Test prompt"}

        # First call (cold - should read file)
        start_time = time.time()
        result1 = mock_user_prompt_submit_hook.process(input_data)
        first_call_time = time.time() - start_time

        # Second call (warm - should use cache)
        start_time = time.time()
        result2 = mock_user_prompt_submit_hook.process(input_data)
        second_call_time = time.time() - start_time

        # Both should return same context
        assert result1["additionalContext"] == result2["additionalContext"]

        # First call should be reasonably fast (< 200ms even on slow systems)
        assert first_call_time < 0.2, f"First call too slow: {first_call_time:.3f}s"

        # Second call should be faster or similar (cache benefit)
        # Note: We don't require it to be faster because file I/O might be cached by OS
        assert second_call_time < 0.2, f"Second call too slow: {second_call_time:.3f}s"

        # Verify cache is being used by checking internal state
        assert (
            mock_user_prompt_submit_hook._preferences_cache is not None
        ), "Cache should be populated"
        assert (
            mock_user_prompt_submit_hook._cache_timestamp is not None
        ), "Cache timestamp should be set"

    def test_preference_change_mid_session(self, mock_user_prompt_submit_hook, temp_project_root):
        """Test that preference changes are picked up mid-session."""
        input_data = {"hook_event_name": "UserPromptSubmit", "prompt": "Test prompt"}

        # Clear cache to ensure fresh read
        mock_user_prompt_submit_hook._preferences_cache = None
        mock_user_prompt_submit_hook._cache_timestamp = None

        # First call - get initial preferences
        result1 = mock_user_prompt_submit_hook.process(input_data)
        context1 = result1["additionalContext"]
        assert "pirate" in context1.lower(), "Should have pirate style initially"

        # Change preferences file
        prefs_file = temp_project_root / ".claude" / "context" / "USER_PREFERENCES.md"

        # Sleep to ensure file modification time changes
        time.sleep(0.05)

        prefs_file.write_text("""# User Preferences

## MANDATORY

### Communication Style
formal (Always use formal business language)

### Verbosity
concise
""")

        # Sleep to ensure modification time is different
        time.sleep(0.05)

        # Clear cache explicitly to force re-read (simulates cache invalidation)
        mock_user_prompt_submit_hook._preferences_cache = None
        mock_user_prompt_submit_hook._cache_timestamp = None

        # Second call - should pick up new preferences
        result2 = mock_user_prompt_submit_hook.process(input_data)
        context2 = result2["additionalContext"]

        # Should now have formal style instead of pirate
        assert "formal" in context2.lower(), "Should pick up changed preference"
        assert "pirate" not in context2.lower(), "Should not have old preference"

        # Cache should be invalidated and updated
        assert context1 != context2, "Context should change after preference update"

    def test_error_handling(self, mock_user_prompt_submit_hook, temp_project_root):
        """Test error handling with malformed preferences file."""
        # Create malformed preferences file (valid UTF-8 but odd formatting)
        prefs_file = temp_project_root / ".claude" / "context" / "USER_PREFERENCES.md"
        prefs_file.write_text("### Communication Style\n\n### Verbosity\n\n### Priority Type\n")

        input_data = {"hook_event_name": "UserPromptSubmit", "prompt": "Test prompt"}

        # Should not crash
        result = mock_user_prompt_submit_hook.process(input_data)

        # Should return valid response (possibly with empty or partial context)
        assert "additionalContext" in result
        assert isinstance(result["additionalContext"], str)

        # Hook should handle gracefully (always exit 0 equivalent)
        # No exception should be raised

    def test_empty_preferences_file(self, mock_user_prompt_submit_hook, temp_project_root):
        """Test handling of completely empty preferences file."""
        prefs_file = temp_project_root / ".claude" / "context" / "USER_PREFERENCES.md"

        # Sleep to ensure modification time changes
        time.sleep(0.05)

        prefs_file.write_text("")

        # Sleep to ensure modification time is different
        time.sleep(0.05)

        # Clear cache to force re-read of empty file
        mock_user_prompt_submit_hook._preferences_cache = None
        mock_user_prompt_submit_hook._cache_timestamp = None

        input_data = {"hook_event_name": "UserPromptSubmit", "prompt": "Test prompt"}

        result = mock_user_prompt_submit_hook.process(input_data)

        # Should handle gracefully with empty context
        assert "additionalContext" in result
        assert result["additionalContext"] == "", "Should return empty context for empty file"

    def test_preference_extraction_accuracy(self, mock_user_prompt_submit_hook):
        """Test that preference extraction is accurate."""
        input_data = {"hook_event_name": "UserPromptSubmit", "prompt": "Test prompt"}

        result = mock_user_prompt_submit_hook.process(input_data)
        context = result["additionalContext"]

        # Verify specific preference values are present
        assert "pirate" in context.lower(), "Should extract pirate communication style"
        assert "balanced" in context.lower(), "Should extract balanced verbosity"
        assert "interactive" in context.lower(), "Should extract interactive collaboration"

        # Verify enforcement instructions are present
        assert (
            "response" in context.lower() or "style" in context.lower()
        ), "Should include enforcement instructions"

    def test_context_format_structure(self, mock_user_prompt_submit_hook):
        """Test that context has proper structure and formatting."""
        input_data = {"hook_event_name": "UserPromptSubmit", "prompt": "Test prompt"}

        result = mock_user_prompt_submit_hook.process(input_data)
        context = result["additionalContext"]

        # Should start with clear header
        assert context.startswith("🎯"), "Should start with visual indicator"
        assert "ACTIVE" in context or "PREFERENCES" in context, "Should have clear header"

        # Should have bullet points for preferences
        lines = context.split("\n")
        bullet_lines = [line for line in lines if line.strip().startswith("•")]
        assert len(bullet_lines) >= 3, "Should have multiple bulleted preferences"

        # Should end with enforcement reminder
        assert "MUST" in context or "mandatory" in context.lower(), "Should have enforcement reminder"

    def test_hook_metrics_logging(self, mock_user_prompt_submit_hook):
        """Test that hook logs metrics correctly."""
        input_data = {"hook_event_name": "UserPromptSubmit", "prompt": "Test prompt"}

        result = mock_user_prompt_submit_hook.process(input_data)

        # Should have created metrics file
        metrics_file = (
            mock_user_prompt_submit_hook.metrics_dir / "user_prompt_submit_metrics.jsonl"
        )

        # Metrics file may or may not exist depending on implementation
        # But if it does exist, it should be valid JSON lines
        if metrics_file.exists():
            import json

            content = metrics_file.read_text()
            lines = [line for line in content.strip().split("\n") if line]

            # Each line should be valid JSON
            for line in lines:
                metric = json.loads(line)
                assert "timestamp" in metric
                assert "metric" in metric
                assert "value" in metric


class TestUserPromptSubmitErrorHandling:
    """Test error handling in user_prompt_submit integration."""

    def test_handles_unicode_in_preferences(self):
        """Test handling of unicode characters in preferences."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            claude_dir = temp_path / ".claude"
            (claude_dir / "context").mkdir(parents=True)
            (claude_dir / "runtime" / "logs").mkdir(parents=True)
            (claude_dir / "runtime" / "metrics").mkdir(parents=True)

            # Create preferences with unicode
            prefs_file = claude_dir / "context" / "USER_PREFERENCES.md"
            prefs_file.write_text(
                """### Communication Style
émojis and 日本語 supported

### Verbosity
详细 (detailed)
""",
                encoding="utf-8",
            )

            project_root = Path(__file__).parent.parent
            hooks_dir = project_root / ".claude" / "tools" / "amplihack" / "hooks"
            sys.path.insert(0, str(hooks_dir))

            try:
                from user_prompt_submit import UserPromptSubmitHook

                hook = UserPromptSubmitHook()
                hook.project_root = temp_path
                hook.log_dir = claude_dir / "runtime" / "logs"
                hook.metrics_dir = claude_dir / "runtime" / "metrics"

                input_data = {"hook_event_name": "UserPromptSubmit", "prompt": "Test"}

                # Should handle unicode gracefully
                result = hook.process(input_data)
                assert "additionalContext" in result
                context = result["additionalContext"]

                # Should preserve unicode characters
                assert isinstance(context, str)

            finally:
                sys.path.pop(0)

    def test_handles_very_large_preferences_file(self):
        """Test handling of unusually large preferences file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            claude_dir = temp_path / ".claude"
            (claude_dir / "context").mkdir(parents=True)
            (claude_dir / "runtime" / "logs").mkdir(parents=True)
            (claude_dir / "runtime" / "metrics").mkdir(parents=True)

            # Create large preferences file
            prefs_file = claude_dir / "context" / "USER_PREFERENCES.md"
            large_content = """### Communication Style
detailed

### Verbosity
verbose

"""
            # Add lots of learned patterns
            large_content += "## Learned Patterns\n\n"
            for i in range(100):
                large_content += f"### Pattern {i}\nSome learned pattern content\n\n"

            prefs_file.write_text(large_content)

            project_root = Path(__file__).parent.parent
            hooks_dir = project_root / ".claude" / "tools" / "amplihack" / "hooks"
            sys.path.insert(0, str(hooks_dir))

            try:
                from user_prompt_submit import UserPromptSubmitHook

                hook = UserPromptSubmitHook()
                hook.project_root = temp_path
                hook.log_dir = claude_dir / "runtime" / "logs"
                hook.metrics_dir = claude_dir / "runtime" / "metrics"

                input_data = {"hook_event_name": "UserPromptSubmit", "prompt": "Test"}

                # Should handle large file without crashing
                start_time = time.time()
                result = hook.process(input_data)
                elapsed = time.time() - start_time

                assert "additionalContext" in result
                # Should still be reasonably fast even with large file (< 500ms)
                assert elapsed < 0.5, f"Processing large file took too long: {elapsed:.3f}s"

            finally:
                sys.path.pop(0)
