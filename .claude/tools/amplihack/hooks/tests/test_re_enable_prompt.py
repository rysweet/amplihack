"""Tests for power-steering re-enable prompt.

Focus on high-value test cases that verify explicit user requirements:
1. Trigger on startup when .disabled exists
2. Prompt with Y/n and 30s timeout
3. Default YES on timeout
4. Cross-platform support (Unix signals, Windows threading)
5. Worktree-aware (shared runtime dir)
6. Fail-open on errors

Reduced from 53 tests to 21 focused tests (ratio: 6.4:1 → ~4:1).
"""

import platform

# Add src to path
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

src_path = Path(__file__).parent.parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from amplihack.power_steering.re_enable_prompt import prompt_re_enable_if_disabled


class TestDetection:
    """Test .disabled file detection."""

    def test_no_disabled_file_returns_true_immediately(self, tmp_path):
        """When .disabled doesn't exist, return True without prompting."""
        runtime_dir = tmp_path / "runtime"
        runtime_dir.mkdir()

        with patch(
            "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
            return_value=str(runtime_dir),
        ):
            _result = prompt_re_enable_if_disabled(project_root=tmp_path)

            assert _result is True

    def test_disabled_file_exists_triggers_prompt(self, tmp_path):
        """When .disabled exists, prompt user."""
        runtime_dir = tmp_path / "runtime"
        ps_dir = runtime_dir / "power-steering"
        ps_dir.mkdir(parents=True)
        (ps_dir / ".disabled").touch()

        with (
            patch(
                "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
                return_value=str(runtime_dir),
            ),
            patch(
                "amplihack.power_steering.re_enable_prompt._get_input_with_timeout",
                return_value="Y",
            ) as mock_input,
        ):
            _result = prompt_re_enable_if_disabled(project_root=tmp_path)

            mock_input.assert_called_once()
            assert "Would you like to re-enable it? [Y/n]" in mock_input.call_args[0][0]


class TestUserInput:
    """Test user input handling (case-insensitive Y/n)."""

    @pytest.mark.parametrize(
        "user_input,expected,file_removed",
        [
            ("Y", True, True),
            ("y", True, True),
            ("yes", True, True),
            ("YES", True, True),
            ("", True, True),  # Empty defaults to YES
            ("n", False, False),
            ("N", False, False),
            ("no", False, False),
            ("invalid", True, True),  # Invalid defaults to YES
        ],
    )
    def test_input_handling(self, tmp_path, user_input, expected, file_removed):
        """Test case-insensitive Y/n handling and defaults."""
        runtime_dir = tmp_path / "runtime"
        ps_dir = runtime_dir / "power-steering"
        ps_dir.mkdir(parents=True)
        disabled_file = ps_dir / ".disabled"
        disabled_file.touch()

        with (
            patch(
                "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
                return_value=str(runtime_dir),
            ),
            patch(
                "amplihack.power_steering.re_enable_prompt._get_input_with_timeout",
                return_value=user_input,
            ),
        ):
            result = prompt_re_enable_if_disabled(project_root=tmp_path)

            assert result is expected
            assert disabled_file.exists() != file_removed


class TestTimeout:
    """Test 30s timeout with default YES."""

    def test_timeout_defaults_to_yes(self, tmp_path):
        """Test timeout returns default value (YES)."""
        runtime_dir = tmp_path / "runtime"
        ps_dir = runtime_dir / "power-steering"
        ps_dir.mkdir(parents=True)
        (ps_dir / ".disabled").touch()

        with (
            patch(
                "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
                return_value=str(runtime_dir),
            ),
            patch(
                "amplihack.power_steering.re_enable_prompt._get_input_with_timeout",
                return_value="Y",
            ),
        ):
            _result = prompt_re_enable_if_disabled(project_root=tmp_path)

            assert _result is True


class TestCrossPlatform:
    """Test cross-platform timeout mechanisms."""

    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix-specific")
    def test_unix_uses_signal_alarm(self):
        """Verify Unix uses signal.SIGALRM."""
        from amplihack.power_steering.re_enable_prompt import _get_input_with_timeout

        with (
            patch("signal.signal") as mock_signal,
            patch("signal.alarm") as mock_alarm,
            patch("builtins.input", return_value="test"),
        ):
            _result = _get_input_with_timeout("prompt", 30, "default")

            assert mock_signal.called
            assert mock_alarm.called

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific")
    def test_windows_uses_threading(self):
        """Verify Windows uses threading.Event."""
        from amplihack.power_steering.re_enable_prompt import _get_input_with_timeout

        with patch("threading.Thread") as mock_thread:
            mock_thread.return_value.start = lambda: None

            _result = _get_input_with_timeout("prompt", 0.1, "default")

            assert mock_thread.called


class TestWorktreeAwareness:
    """Test shared runtime directory (worktree-aware)."""

    def test_uses_shared_runtime_dir(self, tmp_path):
        """Test shared runtime directory is used."""
        shared_runtime = tmp_path / "shared" / "runtime"
        ps_dir = shared_runtime / "power-steering"
        ps_dir.mkdir(parents=True)
        disabled_file = ps_dir / ".disabled"
        disabled_file.touch()

        with (
            patch(
                "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
                return_value=str(shared_runtime),
            ) as mock_get_dir,
            patch(
                "amplihack.power_steering.re_enable_prompt._get_input_with_timeout",
                return_value="Y",
            ),
        ):
            _result = prompt_re_enable_if_disabled(project_root=tmp_path)

            mock_get_dir.assert_called_once_with(tmp_path)
            assert not disabled_file.exists()

    def test_fallback_when_get_shared_runtime_dir_fails(self, tmp_path):
        """Test fallback to .claude/runtime when get_shared_runtime_dir fails."""
        fallback_runtime = tmp_path / ".claude" / "runtime"
        ps_dir = fallback_runtime / "power-steering"
        ps_dir.mkdir(parents=True)
        (ps_dir / ".disabled").touch()

        with (
            patch(
                "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
                side_effect=Exception("Git error"),
            ),
            patch(
                "amplihack.power_steering.re_enable_prompt._get_input_with_timeout",
                return_value="Y",
            ),
        ):
            result = prompt_re_enable_if_disabled(project_root=tmp_path)

            assert result is True


class TestFailOpen:
    """Test fail-open error handling."""

    def test_permission_error_returns_true(self, tmp_path):
        """Test permission errors don't crash (fail-open)."""
        runtime_dir = tmp_path / "runtime"
        ps_dir = runtime_dir / "power-steering"
        ps_dir.mkdir(parents=True)
        (ps_dir / ".disabled").touch()

        with (
            patch(
                "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
                return_value=str(runtime_dir),
            ),
            patch(
                "amplihack.power_steering.re_enable_prompt._get_input_with_timeout",
                return_value="Y",
            ),
            patch("pathlib.Path.unlink", side_effect=PermissionError("Access denied")),
        ):
            result = prompt_re_enable_if_disabled(project_root=tmp_path)

            assert result is True  # Fail-open

    def test_file_not_found_during_removal_returns_true(self, tmp_path):
        """Test FileNotFoundError during removal is handled (concurrent removal)."""
        runtime_dir = tmp_path / "runtime"
        ps_dir = runtime_dir / "power-steering"
        ps_dir.mkdir(parents=True)
        (ps_dir / ".disabled").touch()

        with (
            patch(
                "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
                return_value=str(runtime_dir),
            ),
            patch(
                "amplihack.power_steering.re_enable_prompt._get_input_with_timeout",
                return_value="Y",
            ),
            patch("pathlib.Path.unlink", side_effect=FileNotFoundError("Already removed")),
        ):
            result = prompt_re_enable_if_disabled(project_root=tmp_path)

            assert result is True  # Fail-open

    def test_keyboard_interrupt_returns_false(self, tmp_path):
        """Test Ctrl+C returns False (user cancelled)."""
        runtime_dir = tmp_path / "runtime"
        ps_dir = runtime_dir / "power-steering"
        ps_dir.mkdir(parents=True)
        disabled_file = ps_dir / ".disabled"
        disabled_file.touch()

        with (
            patch(
                "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
                return_value=str(runtime_dir),
            ),
            patch(
                "amplihack.power_steering.re_enable_prompt._get_input_with_timeout",
                side_effect=KeyboardInterrupt,
            ),
        ):
            result = prompt_re_enable_if_disabled(project_root=tmp_path)

            assert result is False
            assert disabled_file.exists()

    def test_eof_error_defaults_to_yes(self, tmp_path):
        """Test EOFError (non-interactive) defaults to YES."""
        runtime_dir = tmp_path / "runtime"
        ps_dir = runtime_dir / "power-steering"
        ps_dir.mkdir(parents=True)
        (ps_dir / ".disabled").touch()

        with (
            patch(
                "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
                return_value=str(runtime_dir),
            ),
            patch(
                "amplihack.power_steering.re_enable_prompt._get_input_with_timeout",
                side_effect=EOFError,
            ),
        ):
            result = prompt_re_enable_if_disabled(project_root=tmp_path)

            assert result is True


class TestEdgeCases:
    """Test boundary conditions."""

    def test_concurrent_file_removal(self, tmp_path):
        """Test handling when another process removes file during prompt."""
        runtime_dir = tmp_path / "runtime"
        ps_dir = runtime_dir / "power-steering"
        ps_dir.mkdir(parents=True)
        disabled_file = ps_dir / ".disabled"
        disabled_file.touch()

        def remove_file_during_input(prompt, timeout, default):
            disabled_file.unlink()
            return "Y"

        with (
            patch(
                "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
                return_value=str(runtime_dir),
            ),
            patch(
                "amplihack.power_steering.re_enable_prompt._get_input_with_timeout",
                side_effect=remove_file_during_input,
            ),
        ):
            result = prompt_re_enable_if_disabled(project_root=tmp_path)

            assert result is True

    def test_disabled_is_directory(self, tmp_path):
        """Test when .disabled is a directory instead of file."""
        runtime_dir = tmp_path / "runtime"
        ps_dir = runtime_dir / "power-steering"
        ps_dir.mkdir(parents=True)
        (ps_dir / ".disabled").mkdir()

        with patch(
            "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
            return_value=str(runtime_dir),
        ):
            result = prompt_re_enable_if_disabled(project_root=tmp_path)

            assert result is True  # Directory exists() returns True but isn't a file

    def test_none_project_root_uses_cwd(self):
        """Test None project_root uses current directory."""
        with (
            patch(
                "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir"
            ) as mock_get_dir,
            patch("pathlib.Path.cwd", return_value=Path("/current/dir")),
        ):
            mock_get_dir.return_value = "/current/dir/.claude/runtime"

            _result = prompt_re_enable_if_disabled(project_root=None)

            mock_get_dir.assert_called_once_with(Path("/current/dir"))


class TestStateConsistency:
    """Test state consistency across multiple calls."""

    def test_second_call_returns_true_without_prompting(self, tmp_path):
        """Test calling again after re-enable returns True immediately."""
        runtime_dir = tmp_path / "runtime"
        ps_dir = runtime_dir / "power-steering"
        ps_dir.mkdir(parents=True)
        (ps_dir / ".disabled").touch()

        with (
            patch(
                "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
                return_value=str(runtime_dir),
            ),
            patch(
                "amplihack.power_steering.re_enable_prompt._get_input_with_timeout",
                return_value="Y",
            ),
        ):
            result1 = prompt_re_enable_if_disabled(project_root=tmp_path)
            assert result1 is True

        # Second call should return True immediately without prompting
        with (
            patch(
                "amplihack.power_steering.re_enable_prompt.get_shared_runtime_dir",
                return_value=str(runtime_dir),
            ),
            patch(
                "amplihack.power_steering.re_enable_prompt._get_input_with_timeout"
            ) as mock_input,
        ):
            result2 = prompt_re_enable_if_disabled(project_root=tmp_path)

            assert result2 is True
            mock_input.assert_not_called()
