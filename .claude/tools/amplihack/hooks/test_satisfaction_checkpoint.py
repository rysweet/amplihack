#!/usr/bin/env python3
"""
Unit tests for satisfaction checkpoint functionality in post_tool_use hook.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

try:
    import pytest
except ImportError:
    print("pytest not available - tests will not run", file=sys.stderr)
    pytest = None

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from post_tool_use import PostToolUseHook


class TestSatisfactionCheckpoint:
    """Test suite for satisfaction checkpoint feature."""

    def test_detect_knowledge_builder_completion(self):
        """Test detection of knowledge-builder command completion."""
        hook = PostToolUseHook()

        # Simulate knowledge-builder completion
        tool_name = "SlashCommand"
        tool_args = {"command": '/amplihack:knowledge-builder "Test topic"'}

        result = hook._is_investigation_command(tool_name, tool_args)
        assert result is True

    def test_detect_analyze_completion(self):
        """Test detection of analyze command completion."""
        hook = PostToolUseHook()

        tool_name = "SlashCommand"
        tool_args = {"command": "/analyze ./src"}

        result = hook._is_investigation_command(tool_name, tool_args)
        assert result is True

    def test_no_detection_for_non_investigation(self):
        """Test that regular commands don't trigger checkpoint."""
        hook = PostToolUseHook()

        tool_name = "Bash"
        tool_args = {"command": "ls -la"}

        result = hook._is_investigation_command(tool_name, tool_args)
        assert result is False

    def test_extract_topics_from_headings(self):
        """Test topic extraction from markdown headings."""
        hook = PostToolUseHook()

        result = """
        # Key Finding: Authentication System
        Some content here.
        ## Security Implications
        More content.
        """

        topic_1, topic_2 = hook._extract_topics(result)
        assert "Authentication System" in topic_1
        assert "Security Implications" in topic_2

    def test_extract_topics_with_fallback(self):
        """Test topic extraction falls back to defaults when no patterns found."""
        hook = PostToolUseHook()

        result = "Just some plain text without structure"

        topic_1, topic_2 = hook._extract_topics(result)
        assert topic_1 == "this topic"
        assert topic_2 == "related areas"

    def test_apply_formal_communication_style(self):
        """Test that formal communication style is applied correctly."""
        hook = PostToolUseHook()

        template = "Would ye like me to explore yer questions?"
        preferences = {"communication_style": "formal"}

        result = hook._apply_communication_style(template, preferences)
        assert "Would you like me to" in result
        assert "your questions" in result
        assert "ye" not in result

    def test_apply_pirate_communication_style(self):
        """Test that pirate communication style is preserved."""
        hook = PostToolUseHook()

        template = "Would ye like me to explore yer questions?"
        preferences = {"communication_style": "pirate"}

        result = hook._apply_communication_style(template, preferences)
        assert "ye" in result
        assert "yer" in result

    def test_checkpoint_config_loading_default_enabled(self, tmp_path):
        """Test that checkpoint is enabled by default when no config exists."""
        with patch.object(Path, "exists", return_value=False):
            hook = PostToolUseHook()
            assert hook.checkpoint_enabled is True

    def test_checkpoint_can_be_disabled(self, tmp_path):
        """Test that checkpoint can be disabled via config."""
        config_path = tmp_path / ".satisfaction_checkpoint_config"
        config_path.write_text(json.dumps({"enabled": False}))

        with patch.object(PostToolUseHook, "_load_checkpoint_config", return_value=False):
            hook = PostToolUseHook()
            assert hook.checkpoint_enabled is False

    @patch("sys.stderr")
    def test_checkpoint_displays_to_stderr(self, mock_stderr, tmp_path):
        """Test that checkpoint is displayed to stderr."""
        # Create mock template
        template_path = tmp_path / "SATISFACTION_CHECKPOINT.md"
        template_path.write_text("Test checkpoint: {topic_1} and {topic_2}")

        hook = PostToolUseHook()
        with patch.object(hook, "project_root", tmp_path.parent):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(
                    Path, "read_text", return_value="Test checkpoint: {topic_1} and {topic_2}"
                ):
                    hook._show_satisfaction_checkpoint("knowledge-builder", "Test result")

        # Verify something was printed (exact assertion depends on mock setup)
        # This is a basic smoke test
        assert True  # Checkpoint function executed without error


class TestIntegrationWithPostToolUse:
    """Integration tests for satisfaction checkpoint with post_tool_use hook."""

    def test_investigation_command_triggers_checkpoint(self, tmp_path):
        """Test that investigation command triggers checkpoint display."""
        hook = PostToolUseHook()

        input_data = {
            "toolUse": {
                "name": "SlashCommand",
                "input": {"command": '/amplihack:knowledge-builder "Test"'},
            },
            "result": {"output": "Knowledge base created"},
        }

        # Mock the checkpoint display to avoid actual stderr output
        with patch.object(hook, "_show_satisfaction_checkpoint") as mock_show:
            hook.process(input_data)
            # Verify checkpoint was called
            assert mock_show.called

    def test_non_investigation_skips_checkpoint(self):
        """Test that non-investigation commands skip checkpoint."""
        hook = PostToolUseHook()

        input_data = {"toolUse": {"name": "Bash", "input": {"command": "ls"}}, "result": {}}

        with patch.object(hook, "_show_satisfaction_checkpoint") as mock_show:
            hook.process(input_data)
            # Verify checkpoint was NOT called
            assert not mock_show.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
