"""Unit tests for claude-trace fallback functionality (Issue #2042)."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from amplihack.utils.claude_trace import (
    clear_status_cache,
    detect_claude_trace_status,
    get_claude_command,
)


class TestClaudeTraceFallback:
    """Test suite for claude-trace fallback functionality."""

    def test_detect_working_claude_trace(self):
        """Test detection of working claude-trace binary."""
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
            # Clear cache before test
            clear_status_cache()

            status = detect_claude_trace_status("/usr/bin/claude-trace")
            assert status == "working"

    def test_detect_broken_claude_trace_exec_format_error(self):
        """Test detection of broken claude-trace with Exec format error."""
        mock_result = MagicMock()
        mock_result.returncode = 8
        mock_result.stdout = ""
        mock_result.stderr = "/usr/bin/claude-trace: /usr/bin/claude-trace: cannot execute binary file: Exec format error"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            # Clear cache before test
            clear_status_cache()

            status = detect_claude_trace_status("/usr/bin/claude-trace")
            assert status == "broken"

    def test_detect_broken_claude_trace_syntax_error(self):
        """Test detection of broken claude-trace with syntax error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "SyntaxError: Unexpected token '>'"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            # Clear cache before test
            clear_status_cache()

            status = detect_claude_trace_status("/usr/bin/claude-trace")
            assert status == "broken"

    def test_detect_broken_claude_trace_bad_interpreter(self):
        """Test detection of broken claude-trace with bad interpreter."""
        mock_result = MagicMock()
        mock_result.returncode = 127
        mock_result.stdout = ""
        mock_result.stderr = "/usr/bin/claude-trace: bad interpreter: No such file or directory"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            # Clear cache before test
            clear_status_cache()

            status = detect_claude_trace_status("/usr/bin/claude-trace")
            assert status == "broken"

    def test_detect_missing_claude_trace_not_exists(self):
        """Test detection of missing claude-trace (file doesn't exist)."""
        with patch("pathlib.Path.exists", return_value=False):
            # Clear cache before test
            clear_status_cache()

            status = detect_claude_trace_status("/usr/bin/claude-trace")
            assert status == "missing"

    def test_detect_missing_claude_trace_not_executable(self):
        """Test detection of missing claude-trace (not executable)."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=False),
        ):
            # Clear cache before test
            clear_status_cache()

            status = detect_claude_trace_status("/usr/bin/claude-trace")
            assert status == "missing"

    def test_detect_broken_claude_trace_empty_output(self):
        """Test detection of broken claude-trace with empty output."""
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
            # Clear cache before test
            clear_status_cache()

            status = detect_claude_trace_status("/usr/bin/claude-trace")
            assert status == "broken"

    def test_detect_broken_claude_trace_invalid_output(self):
        """Test detection of broken claude-trace with invalid output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Some random output"
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
        ):
            # Clear cache before test
            clear_status_cache()

            status = detect_claude_trace_status("/usr/bin/claude-trace")
            assert status == "broken"

    def test_detect_status_caching(self):
        """Test that detection results are cached."""
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
            # Clear cache before test
            clear_status_cache()

            # First call - should execute subprocess
            status1 = detect_claude_trace_status("/usr/bin/claude-trace")
            assert status1 == "working"
            assert mock_run.call_count == 1

            # Second call - should use cache
            status2 = detect_claude_trace_status("/usr/bin/claude-trace")
            assert status2 == "working"
            assert mock_run.call_count == 1  # No additional call

    def test_get_claude_command_fallback_on_broken(self):
        """Test that get_claude_command falls back to 'claude' when claude-trace is broken."""
        # Mock broken claude-trace
        mock_result = MagicMock()
        mock_result.returncode = 8
        mock_result.stdout = ""
        mock_result.stderr = "Exec format error"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
            patch("shutil.which", return_value="/usr/bin/claude-trace"),
            # Mock rustyclawd detection module
            patch(
                "amplihack.utils.rustyclawd_detect.should_use_rustyclawd",
                return_value=False,
            ),
            patch("amplihack.utils.rustyclawd_detect.get_rustyclawd_path", return_value=None),
        ):
            # Clear caches
            clear_status_cache()

            command = get_claude_command()
            assert command == "claude"

    def test_get_claude_command_uses_working_claude_trace(self):
        """Test that get_claude_command uses claude-trace when it's working."""
        # Mock working claude-trace
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Usage: claude-trace [options]\nTrace claude execution"
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
            patch("shutil.which", return_value="/usr/bin/claude-trace"),
            # Mock rustyclawd detection module
            patch(
                "amplihack.utils.rustyclawd_detect.should_use_rustyclawd",
                return_value=False,
            ),
            patch("amplihack.utils.rustyclawd_detect.get_rustyclawd_path", return_value=None),
        ):
            # Clear cache
            clear_status_cache()

            command = get_claude_command()
            assert command == "claude-trace"

    def test_fallback_message_shown_once(self):
        """Test that fallback message is shown only once."""
        # Mock broken claude-trace
        mock_result = MagicMock()
        mock_result.returncode = 8
        mock_result.stdout = ""
        mock_result.stderr = "Exec format error"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("os.access", return_value=True),
            patch("shutil.which", return_value="/usr/bin/claude-trace"),
            # Mock rustyclawd detection module
            patch(
                "amplihack.utils.rustyclawd_detect.should_use_rustyclawd",
                return_value=False,
            ),
            patch("amplihack.utils.rustyclawd_detect.get_rustyclawd_path", return_value=None),
            # Mock _find_valid_claude_trace to simulate finding broken binary
            patch(
                "amplihack.utils.claude_trace._find_valid_claude_trace",
                return_value="/usr/bin/claude-trace",
            ),
            patch("builtins.print") as mock_print,
        ):
            # Clear caches
            clear_status_cache()

            # First call - should show message
            command1 = get_claude_command()
            assert command1 == "claude"

            # Count calls containing the fallback message
            fallback_calls = [
                call
                for call in mock_print.call_args_list
                if "Falling back" in str(call)
            ]
            assert len(fallback_calls) > 0

            # Second call - should NOT show message again
            initial_call_count = mock_print.call_count
            command2 = get_claude_command()
            assert command2 == "claude"

            # Should have fewer new calls (no fallback message)
            new_calls_count = mock_print.call_count - initial_call_count
            new_fallback_calls = [
                call
                for call in mock_print.call_args_list[initial_call_count:]
                if "Falling back" in str(call)
            ]
            assert len(new_fallback_calls) == 0


def run_tests():
    """Run all tests."""
    test_class = TestClaudeTraceFallback()
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
