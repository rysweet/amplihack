"""Tests for launcher detector.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from amplihack.hooks.launcher_detector import LauncherDetector, LauncherInfo


# ============================================================================
# UNIT TESTS (60%)
# ============================================================================

class TestLauncherInfo:
    """Unit tests for LauncherInfo dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        info = LauncherInfo(
            launcher_type="claude",
            command="amplihack test",
            detected_at="2025-01-17T12:00:00",
            environment={"USER": "testuser"}
        )
        data = info.to_dict()

        assert data["launcher_type"] == "claude"
        assert data["command"] == "amplihack test"
        assert data["detected_at"] == "2025-01-17T12:00:00"
        assert data["environment"] == {"USER": "testuser"}

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "launcher_type": "copilot",
            "command": "amplihack test",
            "detected_at": "2025-01-17T12:00:00",
            "environment": {"USER": "testuser"}
        }
        info = LauncherInfo.from_dict(data)

        assert info.launcher_type == "copilot"
        assert info.command == "amplihack test"
        assert info.detected_at == "2025-01-17T12:00:00"
        assert info.environment == {"USER": "testuser"}

    def test_round_trip_serialization(self):
        """Test that to_dict and from_dict are inverses."""
        original = LauncherInfo(
            launcher_type="codex",
            command="amplihack --help",
            detected_at="2025-01-17T12:00:00",
            environment={"HOME": "/home/test"}
        )
        data = original.to_dict()
        restored = LauncherInfo.from_dict(data)

        assert restored.launcher_type == original.launcher_type
        assert restored.command == original.command
        assert restored.detected_at == original.detected_at
        assert restored.environment == original.environment


class TestLauncherDetection:
    """Unit tests for launcher type detection."""

    def test_detect_claude_from_env(self):
        """Test Claude detection from environment variables."""
        with patch.dict(os.environ, {"CLAUDE_CODE_SESSION": "test-session"}):
            launcher_type = LauncherDetector._detect_launcher_type()
            assert launcher_type == "claude"

    def test_detect_copilot_from_env(self):
        """Test Copilot detection from environment variables."""
        with patch.dict(os.environ, {"GITHUB_COPILOT_TOKEN": "test-token"}):
            launcher_type = LauncherDetector._detect_launcher_type()
            assert launcher_type == "copilot"

    def test_detect_codex_from_env(self):
        """Test Codex detection from environment variables."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            launcher_type = LauncherDetector._detect_launcher_type()
            assert launcher_type == "codex"

    def test_detect_unknown_when_no_markers(self):
        """Test unknown detection when no markers present."""
        # Clear environment
        env_vars = [
            "CLAUDE_CODE_SESSION", "CLAUDE_SESSION_ID", "ANTHROPIC_API_KEY",
            "GITHUB_COPILOT_TOKEN", "GITHUB_TOKEN", "COPILOT_SESSION",
            "OPENAI_API_KEY", "CODEX_SESSION"
        ]
        env_patch = {var: None for var in env_vars}

        with patch.dict(os.environ, env_patch, clear=False):
            with patch.object(
                LauncherDetector, '_get_parent_process_name', return_value=None
            ):
                launcher_type = LauncherDetector._detect_launcher_type()
                assert launcher_type == "unknown"

    def test_detect_claude_from_parent_process(self):
        """Test Claude detection from parent process name."""
        with patch.object(
            LauncherDetector, '_get_parent_process_name', return_value="claude-code"
        ):
            launcher_type = LauncherDetector._detect_launcher_type()
            assert launcher_type == "claude"

    def test_detect_copilot_from_parent_process(self):
        """Test Copilot detection from parent process name."""
        with patch.object(
            LauncherDetector, '_get_parent_process_name',
            return_value="github-copilot"
        ):
            launcher_type = LauncherDetector._detect_launcher_type()
            assert launcher_type == "copilot"


class TestCommandGathering:
    """Unit tests for command line gathering."""

    def test_get_command(self):
        """Test command line gathering."""
        with patch.object(sys, 'argv', ["amplihack", "test", "--verbose"]):
            command = LauncherDetector._get_command()
            assert command == "amplihack test --verbose"

    def test_get_command_single_arg(self):
        """Test command with single argument."""
        with patch.object(sys, 'argv', ["amplihack"]):
            command = LauncherDetector._get_command()
            assert command == "amplihack"


class TestEnvironmentGathering:
    """Unit tests for environment variable gathering."""

    def test_gather_environment_sanitizes_keys(self):
        """Test that API keys are sanitized."""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "sk_test_1234567890abcdefghij"}
        ):
            env = LauncherDetector._gather_environment()
            # Should be sanitized
            assert env["ANTHROPIC_API_KEY"] == "sk_t...ghij"

    def test_gather_environment_short_key_not_sanitized(self):
        """Test that short keys are not sanitized."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "short"}):
            env = LauncherDetector._gather_environment()
            # Too short to sanitize
            assert env["ANTHROPIC_API_KEY"] == "short"

    def test_gather_environment_includes_non_sensitive(self):
        """Test that non-sensitive vars are included as-is."""
        with patch.dict(os.environ, {"USER": "testuser", "HOME": "/home/test"}):
            env = LauncherDetector._gather_environment()
            assert env["USER"] == "testuser"
            assert env["HOME"] == "/home/test"

    def test_gather_environment_skips_missing_vars(self):
        """Test that missing vars are not included."""
        with patch.dict(os.environ, {}, clear=True):
            env = LauncherDetector._gather_environment()
            # Should be empty or only contain vars from os.environ
            assert "NONEXISTENT_VAR" not in env


class TestStalenessCheck:
    """Unit tests for staleness checking."""

    def test_is_stale_with_fresh_context(self):
        """Test that fresh context is not stale."""
        context = LauncherInfo(
            launcher_type="claude",
            command="test",
            detected_at=datetime.now().isoformat(),
            environment={}
        )
        assert not LauncherDetector.is_stale(context)

    def test_is_stale_with_old_context(self):
        """Test that old context is stale."""
        old_time = datetime.now() - timedelta(seconds=400)
        context = LauncherInfo(
            launcher_type="claude",
            command="test",
            detected_at=old_time.isoformat(),
            environment={}
        )
        assert LauncherDetector.is_stale(context)

    def test_is_stale_with_none_context(self):
        """Test that None context is stale."""
        assert LauncherDetector.is_stale(None)

    def test_is_stale_with_invalid_timestamp(self):
        """Test that invalid timestamp is treated as stale."""
        context = LauncherInfo(
            launcher_type="claude",
            command="test",
            detected_at="invalid-timestamp",
            environment={}
        )
        assert LauncherDetector.is_stale(context)

    def test_is_stale_at_threshold(self):
        """Test staleness exactly at threshold (300 seconds)."""
        threshold_time = datetime.now() - timedelta(seconds=300)
        context = LauncherInfo(
            launcher_type="claude",
            command="test",
            detected_at=threshold_time.isoformat(),
            environment={}
        )
        # Exactly at threshold should not be stale
        # (uses > not >=)
        assert not LauncherDetector.is_stale(context)


# ============================================================================
# INTEGRATION TESTS (30%)
# ============================================================================

class TestDetectionIntegration:
    """Integration tests for full detection workflow."""

    def test_detect_returns_valid_launcher_info(self):
        """Test that detect() returns valid LauncherInfo."""
        with patch.dict(os.environ, {"CLAUDE_CODE_SESSION": "test"}):
            info = LauncherDetector.detect()

            assert isinstance(info, LauncherInfo)
            assert info.launcher_type in ["claude", "copilot", "codex", "unknown"]
            assert info.command != ""
            assert info.detected_at != ""
            assert isinstance(info.environment, dict)

    def test_detect_captures_environment(self):
        """Test that detect() captures environment variables."""
        with patch.dict(
            os.environ,
            {"CLAUDE_CODE_SESSION": "test", "USER": "testuser"}
        ):
            info = LauncherDetector.detect()
            assert "CLAUDE_CODE_SESSION" in info.environment
            assert "USER" in info.environment


class TestFileOperations:
    """Integration tests for file read/write operations."""

    def test_write_and_read_context(self, tmp_path):
        """Test writing and reading context file."""
        # Use temporary directory
        with patch.object(
            LauncherDetector, 'CONTEXT_FILE', tmp_path / "context.json"
        ):
            # Write context
            context_file = LauncherDetector.write_context(
                launcher_type="claude",
                command="test",
                extra_key="extra_value"
            )

            assert context_file.exists()

            # Read context
            context = LauncherDetector.read_context()

            assert context is not None
            assert context.launcher_type == "claude"
            assert context.command == "test"
            assert context.environment["extra_key"] == "extra_value"

    def test_read_context_missing_file(self, tmp_path):
        """Test reading when file doesn't exist."""
        with patch.object(
            LauncherDetector, 'CONTEXT_FILE',
            tmp_path / "nonexistent.json"
        ):
            context = LauncherDetector.read_context()
            assert context is None

    def test_read_context_invalid_json(self, tmp_path):
        """Test reading file with invalid JSON."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {")

        with patch.object(LauncherDetector, 'CONTEXT_FILE', invalid_file):
            context = LauncherDetector.read_context()
            assert context is None

    def test_read_context_missing_fields(self, tmp_path):
        """Test reading file with missing required fields."""
        incomplete_file = tmp_path / "incomplete.json"
        incomplete_file.write_text('{"launcher_type": "claude"}')

        with patch.object(LauncherDetector, 'CONTEXT_FILE', incomplete_file):
            context = LauncherDetector.read_context()
            assert context is None


# ============================================================================
# E2E TESTS (10%)
# ============================================================================

class TestEndToEnd:
    """End-to-end tests for complete workflows."""

    def test_complete_detection_and_persistence_workflow(self, tmp_path):
        """Test complete workflow from detection to persistence."""
        with patch.object(
            LauncherDetector, 'CONTEXT_FILE', tmp_path / "context.json"
        ):
            with patch.dict(os.environ, {"CLAUDE_CODE_SESSION": "test-session"}):
                # Step 1: Detect launcher
                info = LauncherDetector.detect()
                assert info.launcher_type == "claude"

                # Step 2: Write context
                context_file = LauncherDetector.write_context(
                    launcher_type=info.launcher_type,
                    command=info.command,
                    session_id="test-session-123"
                )
                assert context_file.exists()

                # Step 3: Read context back
                read_info = LauncherDetector.read_context()
                assert read_info is not None
                assert read_info.launcher_type == "claude"

                # Step 4: Check staleness
                assert not LauncherDetector.is_stale(read_info)

    def test_stale_context_detection_workflow(self, tmp_path):
        """Test workflow for detecting stale context."""
        with patch.object(
            LauncherDetector, 'CONTEXT_FILE', tmp_path / "context.json"
        ):
            # Write old context
            old_time = datetime.now() - timedelta(seconds=400)
            old_context = LauncherInfo(
                launcher_type="claude",
                command="old command",
                detected_at=old_time.isoformat(),
                environment={}
            )

            tmp_path.joinpath("context.json").write_text(
                json.dumps(old_context.to_dict(), indent=2)
            )

            # Read and check staleness
            context = LauncherDetector.read_context()
            assert context is not None
            assert LauncherDetector.is_stale(context)

            # Should trigger re-detection in real usage
            new_context = LauncherDetector.detect()
            assert not LauncherDetector.is_stale(new_context)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def tmp_path(tmp_path_factory):
    """Create temporary directory for test files."""
    return tmp_path_factory.mktemp("launcher_detector_tests")
