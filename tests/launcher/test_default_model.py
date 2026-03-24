"""Tests for default model selection in ClaudeLauncher.

TDD approach - tests written BEFORE implementation.
These tests WILL FAIL until the default model logic is implemented.

Feature specification:
- Default model is opus[1m] when no overrides present
- User --model flag takes precedence
- AMPLIHACK_DEFAULT_MODEL environment variable overrides hardcoded default
- Both code paths (native binary and standard) have identical behavior
"""

from unittest.mock import patch

import pytest

from amplihack.launcher.core import ClaudeLauncher


class TestDefaultModelSelection:
    """Test default model selection logic in ClaudeLauncher."""

    def test_user_model_flag_overrides_default(self, monkeypatch):
        """When user specifies --model, don't add default.

        Priority: User flag > default model
        User's explicit model choice should be respected.
        """
        # Setup: User specifies their own model
        launcher = ClaudeLauncher(claude_args=["--model", "opus"])
        launcher._target_directory = None
        launcher._cached_uvx_decision = False

        with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
            cmd = launcher.build_claude_command()

            # Verify: User's model is present
            assert "--model" in cmd
            assert "opus" in cmd

            # Verify: Default opus[1m] is NOT added
            model_count = cmd.count("--model")
            assert model_count == 1, "Should have exactly one --model flag"

            # Verify: opus[1m] is NOT present
            assert "opus[1m]" not in " ".join(cmd)

    def test_env_var_overrides_hardcoded_default(self, monkeypatch):
        """AMPLIHACK_DEFAULT_MODEL overrides opus[1m].

        Priority: Environment variable > hardcoded default
        Allows users to customize their default without code changes.
        """
        # Setup: Set environment variable for custom default
        monkeypatch.setenv("AMPLIHACK_DEFAULT_MODEL", "claude-3-opus-20240229")

        launcher = ClaudeLauncher()
        launcher._target_directory = None
        launcher._cached_uvx_decision = False

        with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
            cmd = launcher.build_claude_command()

            # Verify: Custom default from env var is used
            assert "--model" in cmd
            model_idx = cmd.index("--model")
            assert cmd[model_idx + 1] == "claude-3-opus-20240229"

            # Verify: Hardcoded default NOT present
            assert "opus[1m]" not in " ".join(cmd)

    def test_hardcoded_default_when_no_overrides(self, monkeypatch):
        """Uses opus[1m] when no user flag, no env var.

        Baseline behavior: When nothing overrides, use opus[1m].
        """
        # Setup: Clean environment - no overrides
        monkeypatch.delenv("AMPLIHACK_DEFAULT_MODEL", raising=False)

        launcher = ClaudeLauncher()
        launcher._target_directory = None
        launcher._cached_uvx_decision = False

        with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
            cmd = launcher.build_claude_command()

            # Verify: Default model is present
            assert "--model" in cmd
            model_idx = cmd.index("--model")
            assert cmd[model_idx + 1] == "opus[1m]"

    @pytest.mark.parametrize("use_trace", [True, False])
    def test_both_paths_consistent(self, use_trace, monkeypatch):
        """Native binary and standard paths have same model logic.

        CRITICAL: Both code paths must produce identical model selection.
        DRY principle - model logic should not be duplicated.
        """
        # Setup: Clean environment
        monkeypatch.delenv("AMPLIHACK_DEFAULT_MODEL", raising=False)

        launcher = ClaudeLauncher()
        launcher._target_directory = None
        launcher._cached_uvx_decision = False

        # Test both code paths
        claude_binary = "claude-trace" if use_trace else "claude"

        with patch("amplihack.launcher.core.get_claude_command", return_value=claude_binary):
            if use_trace:
                # Mock get_claude_cli_path for claude-trace path
                with patch(
                    "amplihack.launcher.core.get_claude_cli_path",
                    return_value="/usr/local/bin/claude",
                ):
                    cmd = launcher.build_claude_command()
            else:
                cmd = launcher.build_claude_command()

            # Verify: Default model is present in BOTH paths
            assert "--model" in cmd
            model_idx = cmd.index("--model")
            assert cmd[model_idx + 1] == "opus[1m]", (
                f"Model mismatch in {'claude-trace' if use_trace else 'standard'} path"
            )

    def test_user_flag_beats_env_var(self, monkeypatch):
        """User --model flag beats AMPLIHACK_DEFAULT_MODEL.

        Explicit user choice always beats environment defaults.
        """
        # Setup: Both user flag and env var present
        monkeypatch.setenv("AMPLIHACK_DEFAULT_MODEL", "claude-3-opus-20240229")

        launcher = ClaudeLauncher(claude_args=["--model", "sonnet"])
        launcher._target_directory = None
        launcher._cached_uvx_decision = False

        with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
            cmd = launcher.build_claude_command()

            # Verify: User's model is present
            assert "sonnet" in cmd

            # Verify: Env var model is NOT present
            assert "claude-3-opus-20240229" not in " ".join(cmd)

            # Verify: Only ONE --model flag
            model_count = cmd.count("--model")
            assert model_count == 1

    def test_env_var_beats_hardcoded_default(self, monkeypatch):
        """AMPLIHACK_DEFAULT_MODEL beats opus[1m].

        Environment configuration beats hardcoded defaults.
        Lowest priority override, but still an override.
        """
        # Setup: Only env var set
        monkeypatch.setenv("AMPLIHACK_DEFAULT_MODEL", "claude-3-haiku-20240307")

        launcher = ClaudeLauncher()
        launcher._target_directory = None
        launcher._cached_uvx_decision = False

        with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
            cmd = launcher.build_claude_command()

            # Verify: Env var model is used
            assert "--model" in cmd
            model_idx = cmd.index("--model")
            assert cmd[model_idx + 1] == "claude-3-haiku-20240307"

            # Verify: Hardcoded default NOT used
            assert "opus[1m]" not in " ".join(cmd)

    def test_has_model_arg_detects_user_flag(self):
        """_has_model_arg() correctly detects user's --model flag.

        Helper method test - ensures we can detect if user specified --model.
        """
        # Test with --model present
        launcher = ClaudeLauncher(claude_args=["--model", "opus", "--verbose"])
        assert launcher._has_model_arg() is True

        # Test without --model
        launcher = ClaudeLauncher(claude_args=["--verbose", "--some-other-flag"])
        assert launcher._has_model_arg() is False

        # Test with None claude_args
        launcher = ClaudeLauncher(claude_args=None)
        assert launcher._has_model_arg() is False

        # Test with empty list
        launcher = ClaudeLauncher(claude_args=[])
        assert launcher._has_model_arg() is False

    def test_claude_trace_path_model_logic(self, monkeypatch):
        """claude-trace path includes default model correctly.

        When using claude-trace, model should be in --run-with args.
        """
        monkeypatch.delenv("AMPLIHACK_DEFAULT_MODEL", raising=False)

        launcher = ClaudeLauncher()
        launcher._target_directory = None
        launcher._cached_uvx_decision = False

        with patch("amplihack.launcher.core.get_claude_command", return_value="claude-trace"):
            with patch(
                "amplihack.launcher.core.get_claude_cli_path", return_value="/usr/local/bin/claude"
            ):
                cmd = launcher.build_claude_command()

                # Verify: --run-with is present
                assert "--run-with" in cmd

                # Everything after --run-with are Claude arguments
                run_with_idx = cmd.index("--run-with")
                claude_args = cmd[run_with_idx + 1 :]

                # Verify: --model is in claude args
                assert "--model" in claude_args
                model_idx = claude_args.index("--model")
                assert claude_args[model_idx + 1] == "opus[1m]"

    def test_standard_path_model_logic(self, monkeypatch):
        """Standard claude path includes default model correctly.

        When using standard claude, model should be in main args.
        """
        monkeypatch.delenv("AMPLIHACK_DEFAULT_MODEL", raising=False)

        launcher = ClaudeLauncher()
        launcher._target_directory = None
        launcher._cached_uvx_decision = False

        with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
            cmd = launcher.build_claude_command()

            # Verify: --model is in command
            assert "--model" in cmd
            model_idx = cmd.index("--model")
            assert cmd[model_idx + 1] == "opus[1m]"

            # Verify: No --run-with (that's claude-trace only)
            assert "--run-with" not in cmd
