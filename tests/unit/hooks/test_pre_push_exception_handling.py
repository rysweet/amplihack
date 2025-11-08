#!/usr/bin/env python3
"""
Unit tests for pre-push hook exception handling (fail-closed behavior).
"""

import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add .claude to path
claude_dir = Path(__file__).parent.parent.parent.parent / ".claude"
sys.path.insert(0, str(claude_dir))

from tools.amplihack.hooks.pre_push import PrePushHook  # noqa: E402


class TestPrePushExceptionHandling:
    """Test exception handling behavior in pre-push hook."""

    @pytest.fixture
    def hook(self):
        """Create a PrePushHook instance."""
        return PrePushHook()

    def test_timeout_error_allows_push(self, hook):
        """Test that TimeoutExpired allows push with warning (non-blocking)."""
        with patch.object(hook, "read_push_refs", return_value=[("refs/heads/test", "abc123", "refs/heads/test", "def456")]):
            with patch.object(hook.quality_checker, "check_commits", side_effect=subprocess.TimeoutExpired("test", 30)):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    # Should return empty dict (allow push)
                    result = hook.process({})
                    assert result == {}

                    # Check warning message
                    stderr_output = mock_stderr.getvalue()
                    assert "⚠️" in stderr_output
                    assert "Pre-push hook warning" in stderr_output
                    assert "non-critical checker error" in stderr_output

    def test_file_not_found_error_allows_push(self, hook):
        """Test that FileNotFoundError allows push with warning (non-blocking)."""
        with patch.object(hook, "read_push_refs", return_value=[("refs/heads/test", "abc123", "refs/heads/test", "def456")]):
            with patch.object(hook.quality_checker, "check_commits", side_effect=FileNotFoundError("checker not found")):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    # Should return empty dict (allow push)
                    result = hook.process({})
                    assert result == {}

                    # Check warning message
                    stderr_output = mock_stderr.getvalue()
                    assert "⚠️" in stderr_output
                    assert "Pre-push hook warning" in stderr_output
                    assert "checker not found" in stderr_output

    def test_unexpected_error_blocks_push(self, hook):
        """Test that unexpected errors block push (fail-closed)."""
        with patch.object(hook, "read_push_refs", return_value=[("refs/heads/test", "abc123", "refs/heads/test", "def456")]):
            with patch.object(hook.quality_checker, "check_commits", side_effect=ValueError("unexpected error")):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    # Should call sys.exit(1)
                    with pytest.raises(SystemExit) as exc_info:
                        hook.process({})

                    # Check exit code
                    assert exc_info.value.code == 1

                    # Check error message
                    stderr_output = mock_stderr.getvalue()
                    assert "❌" in stderr_output
                    assert "Pre-push hook failed" in stderr_output
                    assert "Blocking push for safety" in stderr_output
                    assert "FORCE_PUSH_UNVERIFIED=1" in stderr_output

    def test_runtime_error_blocks_push(self, hook):
        """Test that RuntimeError blocks push (fail-closed)."""
        with patch.object(hook, "read_push_refs", return_value=[("refs/heads/test", "abc123", "refs/heads/test", "def456")]):
            with patch.object(hook.quality_checker, "check_commits", side_effect=RuntimeError("logic bug")):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    # Should call sys.exit(1)
                    with pytest.raises(SystemExit) as exc_info:
                        hook.process({})

                    # Check exit code
                    assert exc_info.value.code == 1

                    # Check error message
                    stderr_output = mock_stderr.getvalue()
                    assert "Pre-push hook failed" in stderr_output
                    assert "logic bug" in stderr_output

    @pytest.mark.skip(reason="KeyboardInterrupt propagates through pytest - tested in integration tests")
    def test_keyboard_interrupt_blocks_push(self, hook):
        """Test that KeyboardInterrupt blocks push (fail-closed)."""
        # Note: KeyboardInterrupt is a BaseException, not Exception
        # It will be caught by our generic Exception handler
        # This test is skipped because it interferes with pytest itself
        pass

    def test_attribute_error_blocks_push(self, hook):
        """Test that AttributeError blocks push (fail-closed)."""
        with patch.object(hook, "read_push_refs", return_value=[("refs/heads/test", "abc123", "refs/heads/test", "def456")]):
            with patch.object(hook.quality_checker, "check_commits", side_effect=AttributeError("missing attribute")):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    # Should call sys.exit(1)
                    with pytest.raises(SystemExit) as exc_info:
                        hook.process({})

                    # Check exit code
                    assert exc_info.value.code == 1

                    # Check error message
                    stderr_output = mock_stderr.getvalue()
                    assert "missing attribute" in stderr_output

    def test_emergency_override_bypasses_exception_handling(self, hook):
        """Test that FORCE_PUSH_UNVERIFIED=1 bypasses all checks."""
        with patch.object(hook, "check_emergency_override", return_value=True):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                # Should return empty dict (allow push)
                result = hook.process({})
                assert result == {}

                # Check warning about override
                stderr_output = mock_stderr.getvalue()
                assert "Quality checks bypassed" in stderr_output
                assert "FORCE_PUSH_UNVERIFIED" in stderr_output

    def test_successful_checks_allow_push(self, hook):
        """Test that successful quality checks allow push."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.checker_name = "test_checker"
        mock_result.violations = []
        mock_result.execution_time = 0.5

        with patch.object(hook, "read_push_refs", return_value=[("refs/heads/test", "abc123", "refs/heads/test", "def456")]):
            with patch.object(hook.quality_checker, "check_commits", return_value=[mock_result]):
                with patch.object(hook.quality_checker, "aggregate_violations", return_value=[]):
                    with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                        # Should return empty dict (allow push)
                        result = hook.process({})
                        assert result == {}

                        # Check success message
                        stderr_output = mock_stderr.getvalue()
                        assert "✅" in stderr_output
                        assert "Quality checks passed" in stderr_output

    def test_violations_block_push(self, hook):
        """Test that quality violations block push."""
        from tools.amplihack.hooks.violations import Violation, ViolationType

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.checker_name = "test_checker"
        mock_result.violations = [
            Violation(
                file="test.py",
                type=ViolationType.WHITESPACE,
                message="Trailing whitespace",
                remediation="Remove trailing whitespace",
                checker="test_checker",
                line=1,
            )
        ]
        mock_result.execution_time = 0.5

        with patch.object(hook, "read_push_refs", return_value=[("refs/heads/test", "abc123", "refs/heads/test", "def456")]):
            with patch.object(hook.quality_checker, "check_commits", return_value=[mock_result]):
                with patch.object(hook.quality_checker, "aggregate_violations", return_value=mock_result.violations):
                    with patch.object(hook.quality_checker, "format_violations_report", return_value="Test Report"):
                        with patch("sys.stderr", new_callable=StringIO):
                            # Should call sys.exit(1)
                            with pytest.raises(SystemExit) as exc_info:
                                hook.process({})

                            # Check exit code
                            assert exc_info.value.code == 1
