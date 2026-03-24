"""Tests for default model selection in ClaudeLauncher.

Feature specification:
- Default model is opus[1m] when no overrides present
- User --model flag takes precedence
- AMPLIHACK_DEFAULT_MODEL environment variable overrides hardcoded default
"""

from unittest.mock import Mock, patch

from amplihack.launcher.core import ClaudeLauncher


def _make_launcher(**kwargs):
    """Create a ClaudeLauncher with binary manager mocked to use standard path."""
    launcher = ClaudeLauncher(**kwargs)
    launcher._target_directory = None
    launcher._cached_uvx_decision = False
    # Mock binary manager to skip native binary detection (use standard claude path)
    launcher.binary_manager = Mock()
    launcher.binary_manager.detect_native_binary.return_value = None
    return launcher


class TestDefaultModelSelection:
    """Test default model selection logic in ClaudeLauncher."""

    def test_user_model_flag_overrides_default(self, monkeypatch):
        """When user specifies --model, don't add default."""
        launcher = _make_launcher(claude_args=["--model", "opus"])

        with patch("amplihack.launcher.core.get_claude_cli_path", return_value="/usr/bin/claude"):
            cmd = launcher.build_claude_command()

            assert "--model" in cmd
            assert "opus" in cmd
            assert cmd.count("--model") == 1, "Should have exactly one --model flag"
            assert "opus[1m]" not in " ".join(cmd)

    def test_env_var_overrides_hardcoded_default(self, monkeypatch):
        """AMPLIHACK_DEFAULT_MODEL overrides opus[1m]."""
        monkeypatch.setenv("AMPLIHACK_DEFAULT_MODEL", "claude-3-opus-20240229")
        launcher = _make_launcher()

        with patch("amplihack.launcher.core.get_claude_cli_path", return_value="/usr/bin/claude"):
            cmd = launcher.build_claude_command()

            assert "--model" in cmd
            model_idx = cmd.index("--model")
            assert cmd[model_idx + 1] == "claude-3-opus-20240229"
            assert "opus[1m]" not in " ".join(cmd)

    def test_hardcoded_default_when_no_overrides(self, monkeypatch):
        """Uses opus[1m] when no user flag, no env var."""
        monkeypatch.delenv("AMPLIHACK_DEFAULT_MODEL", raising=False)
        launcher = _make_launcher()

        with patch("amplihack.launcher.core.get_claude_cli_path", return_value="/usr/bin/claude"):
            cmd = launcher.build_claude_command()

            assert "--model" in cmd
            model_idx = cmd.index("--model")
            assert cmd[model_idx + 1] == "opus[1m]"

    def test_user_flag_beats_env_var(self, monkeypatch):
        """User --model flag beats AMPLIHACK_DEFAULT_MODEL."""
        monkeypatch.setenv("AMPLIHACK_DEFAULT_MODEL", "claude-3-opus-20240229")
        launcher = _make_launcher(claude_args=["--model", "sonnet"])

        with patch("amplihack.launcher.core.get_claude_cli_path", return_value="/usr/bin/claude"):
            cmd = launcher.build_claude_command()

            assert "sonnet" in cmd
            assert "claude-3-opus-20240229" not in " ".join(cmd)
            assert cmd.count("--model") == 1

    def test_env_var_beats_hardcoded_default(self, monkeypatch):
        """AMPLIHACK_DEFAULT_MODEL beats opus[1m]."""
        monkeypatch.setenv("AMPLIHACK_DEFAULT_MODEL", "claude-3-haiku-20240307")
        launcher = _make_launcher()

        with patch("amplihack.launcher.core.get_claude_cli_path", return_value="/usr/bin/claude"):
            cmd = launcher.build_claude_command()

            assert "--model" in cmd
            model_idx = cmd.index("--model")
            assert cmd[model_idx + 1] == "claude-3-haiku-20240307"
            assert "opus[1m]" not in " ".join(cmd)

    def test_has_model_arg_detects_user_flag(self):
        """_has_model_arg() correctly detects user's --model flag."""
        launcher = ClaudeLauncher(claude_args=["--model", "opus", "--verbose"])
        assert launcher._has_model_arg() is True

        launcher = ClaudeLauncher(claude_args=["--verbose", "--some-other-flag"])
        assert launcher._has_model_arg() is False

        launcher = ClaudeLauncher(claude_args=None)
        assert launcher._has_model_arg() is False

        launcher = ClaudeLauncher(claude_args=[])
        assert launcher._has_model_arg() is False
