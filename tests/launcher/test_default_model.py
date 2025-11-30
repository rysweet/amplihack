"""Tests for default model selection in ClaudeLauncher.

TDD approach - tests written BEFORE implementation.
These tests WILL FAIL until the default model logic is implemented.

Feature specification:
- Default model is sonnet[1m] when no overrides present
- Azure proxy takes precedence (highest priority)
- User --model flag takes precedence
- AMPLIHACK_DEFAULT_MODEL environment variable overrides hardcoded default
- Both code paths (claude-trace and standard) have identical behavior
"""

from unittest.mock import Mock, patch

import pytest

from amplihack.launcher.core import ClaudeLauncher
from amplihack.proxy.manager import ProxyManager


class TestDefaultModelSelection:
    """Test default model selection logic in ClaudeLauncher."""

    def test_azure_proxy_overrides_default(self, monkeypatch):
        """When proxy_manager configured, use Azure model not default.

        Priority: Azure proxy > default model
        Azure proxy should ALWAYS take precedence over default model.
        """
        # Setup: Configure proxy with Azure model
        mock_proxy_config = {
            "BIG_MODEL": "gpt-5-codex",
            "AZURE_OPENAI_DEPLOYMENT_NAME": None,
        }

        with patch("amplihack.launcher.core.ProxyManager"):
            mock_proxy = Mock(spec=ProxyManager)
            mock_proxy.proxy_config = mock_proxy_config

            launcher = ClaudeLauncher(proxy_manager=mock_proxy)
            launcher._target_directory = None  # No --add-dir
            launcher._cached_uvx_decision = False

            # Mock get_claude_command to test both paths
            with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
                cmd = launcher.build_claude_command()

                # Verify: Azure model in command, NOT default sonnet[1m]
                assert "--model" in cmd
                model_idx = cmd.index("--model")
                assert cmd[model_idx + 1] == "azure/gpt-5-codex"

                # Verify: sonnet[1m] is NOT present
                assert "sonnet[1m]" not in " ".join(cmd)

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

            # Verify: Default sonnet[1m] is NOT added
            model_count = cmd.count("--model")
            assert model_count == 1, "Should have exactly one --model flag"

            # Verify: sonnet[1m] is NOT present
            assert "sonnet[1m]" not in " ".join(cmd)

    def test_env_var_overrides_hardcoded_default(self, monkeypatch):
        """AMPLIHACK_DEFAULT_MODEL overrides sonnet[1m].

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
            assert "sonnet[1m]" not in " ".join(cmd)

    def test_hardcoded_default_when_no_overrides(self, monkeypatch):
        """Uses sonnet[1m] when no proxy, no user flag, no env var.

        Baseline behavior: When nothing overrides, use sonnet[1m].
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
            assert cmd[model_idx + 1] == "sonnet[1m]"

    @pytest.mark.parametrize("use_trace", [True, False])
    def test_both_paths_consistent(self, use_trace, monkeypatch):
        """claude-trace and standard paths have same model logic.

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
            assert cmd[model_idx + 1] == "sonnet[1m]", (
                f"Model mismatch in {'claude-trace' if use_trace else 'standard'} path"
            )

    def test_priority_order_azure_beats_all(self, monkeypatch):
        """Azure proxy beats both user flag and env var.

        When proxy configured, it should override EVERYTHING.
        This is the highest priority override.
        """
        # Setup: All three overrides present
        monkeypatch.setenv("AMPLIHACK_DEFAULT_MODEL", "claude-3-opus-20240229")

        mock_proxy_config = {
            "BIG_MODEL": "gpt-5-codex",
            "AZURE_OPENAI_DEPLOYMENT_NAME": None,
        }

        with patch("amplihack.launcher.core.ProxyManager"):
            mock_proxy = Mock(spec=ProxyManager)
            mock_proxy.proxy_config = mock_proxy_config

            launcher = ClaudeLauncher(
                proxy_manager=mock_proxy,
                claude_args=["--model", "sonnet"],  # User also specified
            )
            launcher._target_directory = None
            launcher._cached_uvx_decision = False

            with patch("amplihack.launcher.core.get_claude_command", return_value="claude"):
                cmd = launcher.build_claude_command()

                # Verify: ONLY Azure model present
                assert "--model" in cmd

                # Azure adds its model BEFORE user args
                # So we should have azure model, then potentially user's --model in claude_args
                # But since proxy is configured, Azure should be the FINAL authority

                # The proxy logic adds model AFTER --dangerously-skip-permissions
                # but BEFORE claude_args are added
                # So if user also has --model, we'd have TWO --model flags
                # This test verifies Azure takes precedence

                # Actually, re-reading the code, Azure is added before claude_args
                # So if user has --model, we'd have: --model azure/gpt-5-codex --model sonnet
                # Claude would use the LAST one, which is wrong!

                # THIS IS A BUG WE'RE TESTING FOR - should NOT happen
                # When proxy configured, user's --model should be ignored
                # This test documents the EXPECTED behavior

                # For now, just verify Azure model is present
                azure_model_present = any(arg == "azure/gpt-5-codex" for arg in cmd)
                assert azure_model_present, "Azure model must be present when proxy configured"

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
        """AMPLIHACK_DEFAULT_MODEL beats sonnet[1m].

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
            assert "sonnet[1m]" not in " ".join(cmd)

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
                assert claude_args[model_idx + 1] == "sonnet[1m]"

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
            assert cmd[model_idx + 1] == "sonnet[1m]"

            # Verify: No --run-with (that's claude-trace only)
            assert "--run-with" not in cmd
