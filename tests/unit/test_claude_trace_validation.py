"""Unit tests for claude-trace validation logic."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from amplihack.utils.claude_trace import (
    _is_valid_claude_trace_binary,
    clear_status_cache,
    detect_claude_trace_status,
)


class TestClaudeTraceValidation:
    """Test suite for claude-trace binary validation."""

    def test_help_output_with_claude_and_trace(self):
        """Test that --help output with 'claude' and 'trace' passes validation."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Usage: claude-trace [options]\nTrace claude execution"
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result) as mock_run,
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            # Clear cache
            clear_status_cache()

            result = detect_claude_trace_status("/usr/bin/claude-trace")
            assert result == "working"
            mock_run.assert_called_once()
            # Verify --help was called with 2s timeout
            call_args = mock_run.call_args
            assert call_args[0][0] == ["/usr/bin/claude-trace", "--help"]
            assert call_args[1]["timeout"] == 2

    def test_help_output_with_claude_and_usage(self):
        """Test that --help output with 'claude' and 'usage' passes validation."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Usage: claude [options]\nRun claude with tracing"
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            # Clear cache
            clear_status_cache()

            result = detect_claude_trace_status("/usr/bin/claude-trace")
            assert result == "working"

    def test_help_output_case_insensitive(self):
        """Test that validation is case-insensitive."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "USAGE: CLAUDE-TRACE [OPTIONS]\nTrace CLAUDE execution"
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            # Clear cache
            clear_status_cache()

            result = detect_claude_trace_status("/usr/bin/claude-trace")
            assert result == "working"

    def test_help_output_missing_claude(self):
        """Test that output without 'claude' fails validation."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Usage: trace-tool [options]\nTrace execution"
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            clear_status_cache()
            result = detect_claude_trace_status("/usr/bin/wrong-tool")
            assert result == "broken"

    def test_help_output_missing_trace_and_usage(self):
        """Test that output without 'trace' or 'usage' fails validation."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "claude debugging tool\nSome other info"
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            clear_status_cache()
            result = detect_claude_trace_status("/usr/bin/wrong-tool")
            assert result == "broken"

    def test_help_output_empty(self):
        """Test that empty output fails validation."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            clear_status_cache()
            result = detect_claude_trace_status("/usr/bin/wrong-tool")
            assert result == "broken"

    def test_help_output_only_whitespace(self):
        """Test that whitespace-only output fails validation."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "   \n\t  \n"
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            clear_status_cache()
            result = detect_claude_trace_status("/usr/bin/wrong-tool")
            assert result == "broken"

    def test_non_zero_exit_code(self):
        """Test that non-zero exit code fails validation."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Usage: claude-trace [options]\nTrace claude execution"
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            # Clear cache
            clear_status_cache()

            result = detect_claude_trace_status("/usr/bin/claude-trace")
            assert result == "broken"

    def test_subprocess_timeout(self):
        """Test that timeout exceptions result in False."""
        with (
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 2)),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            # Clear cache
            clear_status_cache()

            result = detect_claude_trace_status("/usr/bin/claude-trace")
            assert result == "broken"

    def test_subprocess_error(self):
        """Test that subprocess errors result in False."""
        with (
            patch("subprocess.run", side_effect=subprocess.SubprocessError("error")),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            # Clear cache
            clear_status_cache()

            result = detect_claude_trace_status("/usr/bin/claude-trace")
            assert result == "broken"

    def test_os_error(self):
        """Test that OS errors result in False."""
        with (
            patch("subprocess.run", side_effect=OSError("error")),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            # Clear cache
            clear_status_cache()

            result = detect_claude_trace_status("/usr/bin/claude-trace")
            assert result == "broken"

    def test_homebrew_symlink_handling(self):
        """Test that homebrew symlinks are still validated."""
        # The special homebrew handling should still work
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Usage: claude-trace\nTrace claude"
        mock_result.stderr = ""

        # Create a mock Path object for homebrew location
        with (
            patch("pathlib.Path.is_symlink", return_value=True),
            patch(
                "pathlib.Path.resolve",
                return_value=Path("/opt/homebrew/lib/node_modules/claude-trace.js"),
            ),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
            patch("subprocess.run", return_value=mock_result),
        ):
            # Clear cache
            clear_status_cache()

            # The homebrew path should be validated via the standard logic
            result = detect_claude_trace_status("/opt/homebrew/bin/claude-trace")
            # Should return "working" after subprocess test passes
            assert result == "working"

    def test_is_valid_binary_integration(self):
        """Test that _is_valid_claude_trace_binary integrates correctly."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Usage: claude-trace [options]\nTrace claude execution"
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            # Clear cache
            clear_status_cache()

            result = _is_valid_claude_trace_binary("/usr/bin/claude-trace")
            assert result is True


def run_tests():
    """Run all tests."""

    test_class = TestClaudeTraceValidation()
    test_methods = [
        method
        for method in dir(test_class)
        if method.startswith("test_") and callable(getattr(test_class, method))
    ]

    print(f"Running {len(test_methods)} tests...\n")
    passed = 0
    failed = 0

    for method_name in test_methods:
        try:
            method = getattr(test_class, method_name)
            method()
            print(f"✓ {method_name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {method_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {method_name}: Unexpected error: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"Tests: {passed} passed, {failed} failed")
    if failed == 0:
        print("✅ All tests passed!")
        return 0
    print("❌ Some tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(run_tests())
