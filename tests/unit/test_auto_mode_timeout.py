"""Unit tests for AutoMode timeout feature improvements.

Tests TDD-style for the auto mode timeout configuration changes:
1. Default timeout changed from 5.0 to 30.0 minutes
2. --no-timeout flag disables timeout (returns None)
3. Auto-detect Opus model from --model arg and use 60 min timeout
4. Priority: --no-timeout > explicit > auto-detect > default

Following TDD approach - these tests should FAIL initially until
the feature is implemented.
"""

import argparse
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from amplihack.launcher.auto_mode import AutoMode


class TestDefaultTimeout:
    """Test that default timeout is 30.0 minutes (not 5.0)."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_default_timeout_is_30_minutes(self, temp_working_dir):
        """Test that AutoMode uses 30.0 minute default timeout.

        Expected behavior:
        - Default query_timeout_minutes should be 30.0
        - query_timeout_seconds should be 1800.0 (30 * 60)

        This is a change from the previous default of 5.0 minutes.
        Rationale: 5 minutes is too short for complex agentic tasks.
        """
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test prompt",
            max_turns=5,
            working_dir=temp_working_dir,
            # NOTE: Not passing query_timeout_minutes - should use default
        )

        # Default should be 30.0 minutes = 1800 seconds
        assert auto_mode.query_timeout_seconds == 1800.0, (
            f"Default timeout should be 30 minutes (1800s), "
            f"got {auto_mode.query_timeout_seconds / 60} minutes"
        )


class TestNoTimeoutFlag:
    """Test --no-timeout flag disables timeout (sets to None)."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_none_timeout_accepted(self, temp_working_dir):
        """Test that AutoMode accepts None timeout without error.

        Expected behavior:
        - AutoMode should accept query_timeout_minutes=None
        - query_timeout_seconds should be None
        - No validation error should be raised

        This enables --no-timeout flag to disable timeout completely.
        """
        # This test should fail until AutoMode is updated to accept None
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test prompt",
            max_turns=5,
            working_dir=temp_working_dir,
            query_timeout_minutes=None,  # type: ignore  # Testing new feature
        )

        assert auto_mode.query_timeout_seconds is None, (
            "When query_timeout_minutes is None, query_timeout_seconds should be None (no timeout)"
        )

    def test_none_timeout_disables_validation(self, temp_working_dir):
        """Test that None timeout bypasses positive value validation.

        Expected behavior:
        - None should not trigger 'must be positive' validation error
        - None is a valid sentinel value meaning 'no timeout'
        """
        # Should not raise ValueError for None
        try:
            AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=temp_working_dir,
                query_timeout_minutes=None,  # type: ignore
            )
        except ValueError as e:
            pytest.fail(f"None should be accepted without validation error: {e}")


class TestExplicitTimeout:
    """Test explicit --query-timeout-minutes value is respected."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_explicit_timeout_15_minutes(self, temp_working_dir):
        """Test that explicit timeout value is used.

        Expected behavior:
        - query_timeout_minutes=15.0 should set query_timeout_seconds=900.0
        """
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test prompt",
            max_turns=5,
            working_dir=temp_working_dir,
            query_timeout_minutes=15.0,
        )

        assert auto_mode.query_timeout_seconds == 900.0, (
            f"Explicit 15 minute timeout should be 900s, got {auto_mode.query_timeout_seconds}"
        )

    def test_explicit_timeout_45_minutes(self, temp_working_dir):
        """Test that explicit 45 minute timeout is used.

        Expected behavior:
        - query_timeout_minutes=45.0 should set query_timeout_seconds=2700.0
        """
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test prompt",
            max_turns=5,
            working_dir=temp_working_dir,
            query_timeout_minutes=45.0,
        )

        assert auto_mode.query_timeout_seconds == 2700.0, (
            f"Explicit 45 minute timeout should be 2700s, got {auto_mode.query_timeout_seconds}"
        )


class TestOpusModelAutoDetection:
    """Test auto-detection of Opus model sets 60 minute timeout.

    Note: Opus detection is now handled in cli.resolve_timeout(), not AutoMode.__init__.
    These tests verify the CLI-level timeout resolution logic.
    """

    def test_opus_model_short_name_detection(self):
        """Test Opus model detection from '--model opus'.

        Expected behavior:
        - When model='opus', auto-detect and use 60 minute timeout
        - resolve_timeout should return 60.0

        Rationale: Opus models are typically used for complex, long-running
        tasks that benefit from longer timeouts.
        """
        from amplihack import cli

        parser = argparse.ArgumentParser()
        cli.add_auto_mode_args(parser)
        args = parser.parse_args([])  # Use default timeout (30.0)

        timeout = cli.resolve_timeout(args, model="opus")

        assert timeout == 60.0, (
            f"Opus model should auto-detect and use 60 minute timeout, got {timeout} minutes"
        )

    def test_opus_model_full_name_detection(self):
        """Test Opus model detection from '--model claude-opus-4-5-20251101'.

        Expected behavior:
        - When model contains 'opus', auto-detect and use 60 minute timeout
        - resolve_timeout should return 60.0
        """
        from amplihack import cli

        parser = argparse.ArgumentParser()
        cli.add_auto_mode_args(parser)
        args = parser.parse_args([])  # Use default timeout (30.0)

        timeout = cli.resolve_timeout(args, model="claude-opus-4-5-20251101")

        assert timeout == 60.0, (
            f"Opus model (full name) should use 60 minute timeout, got {timeout} minutes"
        )

    def test_non_opus_model_uses_default(self):
        """Test non-Opus model uses default timeout.

        Expected behavior:
        - When model='sonnet', use default 30 minute timeout
        - resolve_timeout should return 30.0
        """
        from amplihack import cli

        parser = argparse.ArgumentParser()
        cli.add_auto_mode_args(parser)
        args = parser.parse_args([])  # Use default timeout (30.0)

        timeout = cli.resolve_timeout(args, model="sonnet")

        assert timeout == 30.0, (
            f"Non-Opus model should use default 30 minute timeout, got {timeout} minutes"
        )


class TestTimeoutPriority:
    """Test timeout priority: --no-timeout > explicit > auto-detect > default.

    Note: Opus detection is now handled in cli.resolve_timeout(), not AutoMode.__init__.
    These tests verify the CLI-level timeout resolution logic.
    """

    def test_no_timeout_overrides_opus_detection(self):
        """Test --no-timeout takes priority over Opus model detection.

        Expected behavior:
        - --no-timeout should result in None timeout
        - Even when model='opus' is specified
        - Priority: --no-timeout > auto-detect
        """
        from amplihack import cli

        parser = argparse.ArgumentParser()
        cli.add_auto_mode_args(parser)
        args = parser.parse_args(["--no-timeout"])

        timeout = cli.resolve_timeout(args, model="opus")

        assert timeout is None, "--no-timeout (None) should override Opus auto-detection"

    def test_explicit_timeout_overrides_opus_detection(self):
        """Test explicit timeout takes priority over Opus model detection.

        Expected behavior:
        - --query-timeout-minutes=15.0 should be used
        - Even when model='opus' (which would default to 60 min)
        - Priority: explicit > auto-detect
        """
        from amplihack import cli

        parser = argparse.ArgumentParser()
        cli.add_auto_mode_args(parser)
        args = parser.parse_args(["--query-timeout-minutes", "15"])

        timeout = cli.resolve_timeout(args, model="opus")

        assert timeout == 15.0, (
            f"Explicit 15 minute timeout should override Opus 60 minute default, "
            f"got {timeout} minutes"
        )

    def test_opus_detection_overrides_default(self):
        """Test Opus model auto-detection takes priority over default.

        Expected behavior:
        - When model='opus' and no explicit timeout
        - Use 60 minute timeout (not 30 minute default)
        - Priority: auto-detect > default
        """
        from amplihack import cli

        parser = argparse.ArgumentParser()
        cli.add_auto_mode_args(parser)
        args = parser.parse_args([])  # Use default (30.0)

        timeout = cli.resolve_timeout(args, model="opus")

        assert timeout == 60.0, (
            f"Opus model should use 60 minute timeout over 30 minute default, got {timeout} minutes"
        )


class TestCLIArgumentParsing:
    """Test CLI argument parsing for timeout features."""

    def test_cli_default_timeout_is_30(self):
        """Test CLI default for --query-timeout-minutes is 30.0.

        Expected behavior:
        - ArgumentParser default should be 30.0 (not 5.0)
        """
        # Import CLI module to check argument defaults
        from amplihack import cli

        parser = argparse.ArgumentParser()
        cli.add_auto_mode_args(parser)

        args = parser.parse_args([])

        assert args.query_timeout_minutes == 30.0, (
            f"CLI default should be 30.0 minutes, got {args.query_timeout_minutes}"
        )

    def test_cli_no_timeout_flag_exists(self):
        """Test --no-timeout flag is recognized by CLI.

        Expected behavior:
        - --no-timeout should be a valid argument
        - When present, should set query_timeout_minutes to None
        """
        from amplihack import cli

        parser = argparse.ArgumentParser()
        cli.add_auto_mode_args(parser)

        # This should not raise an error
        args = parser.parse_args(["--no-timeout"])

        # Check the flag was parsed
        assert hasattr(args, "no_timeout"), "--no-timeout flag should exist"
        assert args.no_timeout is True, "--no-timeout should be True when specified"

    def test_cli_no_timeout_sets_none(self):
        """Test --no-timeout flag results in None timeout value.

        Expected behavior:
        - When --no-timeout is passed, the resolved timeout should be None
        """
        from amplihack import cli

        parser = argparse.ArgumentParser()
        cli.add_auto_mode_args(parser)

        args = parser.parse_args(["--no-timeout"])

        # The CLI should resolve --no-timeout to query_timeout_minutes=None
        # This may require a helper function like resolve_timeout(args)
        timeout = cli.resolve_timeout(args)  # type: ignore  # Testing new feature

        assert timeout is None, "--no-timeout should resolve to None timeout"

    def test_cli_explicit_timeout_overrides_no_timeout(self):
        """Test explicit timeout with --no-timeout raises error or uses explicit.

        Expected behavior:
        - Conflicting --no-timeout and --query-timeout-minutes should error
        - OR explicit value should take priority
        """
        from amplihack import cli

        parser = argparse.ArgumentParser()
        cli.add_auto_mode_args(parser)

        # Parse both flags - implementation should handle conflict
        args = parser.parse_args(["--no-timeout", "--query-timeout-minutes", "15"])

        # Either this should raise an error during resolution,
        # or explicit timeout should win
        try:
            timeout = cli.resolve_timeout(args)  # type: ignore
            # If no error, explicit should win (None from --no-timeout takes priority)
            assert timeout is None, "--no-timeout should take priority over explicit timeout"
        except ValueError:
            # Acceptable behavior - conflicting flags raise error
            pass


class TestEdgeCases:
    """Test edge cases for timeout handling."""

    @pytest.fixture
    def temp_working_dir(self):
        """Create temporary working directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_zero_timeout_still_rejected(self, temp_working_dir):
        """Test that zero timeout is still rejected.

        Expected behavior:
        - query_timeout_minutes=0 should raise ValueError
        - Only None (no timeout) and positive values are valid
        """
        with pytest.raises(ValueError, match="must be positive"):
            AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=temp_working_dir,
                query_timeout_minutes=0.0,
            )

    def test_negative_timeout_still_rejected(self, temp_working_dir):
        """Test that negative timeout is still rejected.

        Expected behavior:
        - query_timeout_minutes=-5.0 should raise ValueError
        """
        with pytest.raises(ValueError, match="must be positive"):
            AutoMode(
                sdk="claude",
                prompt="Test prompt",
                max_turns=5,
                working_dir=temp_working_dir,
                query_timeout_minutes=-5.0,
            )

    def test_very_long_timeout_warning_threshold_unchanged(self, temp_working_dir, capsys):
        """Test warning for very long timeouts still works.

        Expected behavior:
        - timeout > 120 minutes should print warning
        - This behavior should be unchanged
        """
        AutoMode(
            sdk="claude",
            prompt="Test prompt",
            max_turns=5,
            working_dir=temp_working_dir,
            query_timeout_minutes=130.0,
        )

        captured = capsys.readouterr()
        assert "Warning" in captured.err, "Very long timeout (>120 min) should print warning"

    def test_opus_detection_case_insensitive(self):
        """Test Opus model detection is case insensitive.

        Expected behavior:
        - model='OPUS', 'Opus', 'oPuS' should all detect as Opus
        - All should use 60 minute timeout

        Note: Opus detection is now handled in cli.resolve_timeout(), not AutoMode.__init__.
        """
        from amplihack import cli

        parser = argparse.ArgumentParser()
        cli.add_auto_mode_args(parser)
        args = parser.parse_args([])  # Use default timeout (30.0)

        for model_name in ["OPUS", "Opus", "oPuS", "CLAUDE-OPUS-4-5-20251101"]:
            timeout = cli.resolve_timeout(args, model=model_name)

            assert timeout == 60.0, (
                f"Model '{model_name}' should detect as Opus and use 60 min timeout, "
                f"got {timeout} minutes"
            )
