#!/usr/bin/env python3
"""ClaudeProcess: delegate-aware command building — Failing Tests.

Tests that ClaudeProcess._build_command() uses the AMPLIHACK_DELEGATE env var
instead of hardcoding 'claude'. These tests FAIL until the implementation
replaces the hardcoded 'claude' binary with a DELEGATE_COMMANDS lookup.

Coverage:
  - DELEGATE_COMMANDS: module-level dict mapping delegate → command list
  - _build_command(): uses AMPLIHACK_DELEGATE env var when set
  - _build_command(): maps 'amplihack claude' → ['claude', ...] correctly
  - _build_command(): maps 'amplihack copilot' → appropriate command
  - _build_command(): maps 'amplihack amplifier' → appropriate command
  - _build_command(): emits warnings.warn() when AMPLIHACK_DELEGATE not set
  - _build_command(): emits warnings.warn() for unrecognised delegate value
  - _build_command(): falls back safely to 'claude' on unknown delegate
"""

import os
import sys
import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

# Add orchestration directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude_process import ClaudeProcess

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_process(tmp_path: Path) -> ClaudeProcess:
    """Create a minimal ClaudeProcess for testing."""
    return ClaudeProcess(
        prompt="test prompt",
        process_id="test-001",
        working_dir=tmp_path / "work",
        log_dir=tmp_path / "logs",
    )


# ---------------------------------------------------------------------------
# 1. DELEGATE_COMMANDS: module-level dict
# ---------------------------------------------------------------------------


class TestDelegateCommandsDict:
    """DELEGATE_COMMANDS must exist at module level as a safe command lookup table."""

    def test_delegate_commands_exists(self):
        """DELEGATE_COMMANDS dict must exist in claude_process module."""
        import claude_process as cp_module

        assert hasattr(cp_module, "DELEGATE_COMMANDS"), (
            "DELEGATE_COMMANDS dict is missing from claude_process.py. "
            "Add: DELEGATE_COMMANDS = {'amplihack claude': ['claude', ...], "
            "'amplihack copilot': ['amplihack', 'copilot', ...], "
            "'amplihack amplifier': ['amplihack', 'amplifier', ...]}"
        )

    def test_delegate_commands_is_dict(self):
        """DELEGATE_COMMANDS must be a dict."""
        import claude_process as cp_module

        assert isinstance(cp_module.DELEGATE_COMMANDS, dict), (
            f"DELEGATE_COMMANDS must be a dict, got {type(cp_module.DELEGATE_COMMANDS).__name__}"
        )

    def test_delegate_commands_contains_all_three_keys(self):
        """DELEGATE_COMMANDS must have entries for all three valid delegates."""
        import claude_process as cp_module

        dc = cp_module.DELEGATE_COMMANDS
        assert "amplihack claude" in dc, (
            f"DELEGATE_COMMANDS must include 'amplihack claude' key. Got keys: {list(dc.keys())}"
        )
        assert "amplihack copilot" in dc, (
            f"DELEGATE_COMMANDS must include 'amplihack copilot' key. Got keys: {list(dc.keys())}"
        )
        assert "amplihack amplifier" in dc, (
            f"DELEGATE_COMMANDS must include 'amplihack amplifier' key. Got keys: {list(dc.keys())}"
        )

    def test_delegate_commands_values_are_lists(self):
        """Each DELEGATE_COMMANDS value must be a list of strings (pre-split command)."""
        import claude_process as cp_module

        for key, value in cp_module.DELEGATE_COMMANDS.items():
            assert isinstance(value, list), (
                f"DELEGATE_COMMANDS[{key!r}] must be a list, got {type(value).__name__}. "
                "Use pre-split lists to prevent injection via .split() on untrusted input."
            )
            assert all(isinstance(s, str) for s in value), (
                f"All elements in DELEGATE_COMMANDS[{key!r}] must be strings"
            )
            assert len(value) >= 1, f"DELEGATE_COMMANDS[{key!r}] must have at least one element"

    def test_delegate_commands_no_shell_injection_strings(self):
        """DELEGATE_COMMANDS values must not contain shell metacharacters."""
        import claude_process as cp_module

        shell_chars = [";", "|", "&", "`", "$", ">", "<", "(", ")"]
        for key, value in cp_module.DELEGATE_COMMANDS.items():
            for part in value:
                for char in shell_chars:
                    assert char not in part, (
                        f"DELEGATE_COMMANDS[{key!r}] contains shell metachar '{char}' "
                        f"in part {part!r}. This could enable injection attacks."
                    )


# ---------------------------------------------------------------------------
# 2. _build_command(): uses AMPLIHACK_DELEGATE env var
# ---------------------------------------------------------------------------


class TestBuildCommandUsesDelegate:
    """_build_command() must respect AMPLIHACK_DELEGATE env var."""

    def test_build_command_uses_claude_by_default(self, tmp_path):
        """Without AMPLIHACK_DELEGATE, _build_command() must use the 'claude' binary."""
        proc = make_process(tmp_path)

        env_without_delegate = {k: v for k, v in os.environ.items() if k != "AMPLIHACK_DELEGATE"}
        with patch.dict(os.environ, env_without_delegate, clear=True):
            cmd = proc._build_command()

        assert isinstance(cmd, list), f"_build_command() must return a list, got {type(cmd)}"
        assert len(cmd) >= 1, "_build_command() must return a non-empty command list"
        # First element must be the binary
        assert cmd[0] in ("claude", "amplihack"), (
            f"Default command must start with 'claude' or 'amplihack', got {cmd[0]!r}"
        )

    def test_build_command_uses_amplihack_delegate_env_var(self, tmp_path):
        """_build_command() must change its base command when AMPLIHACK_DELEGATE is set."""
        proc = make_process(tmp_path)

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack copilot"}):
            cmd = proc._build_command()

        assert isinstance(cmd, list), "_build_command() must return a list"
        # The command must NOT start with just 'claude' when copilot is the delegate
        cmd_str = " ".join(cmd[:3])
        assert cmd[0] != "claude" or "copilot" in cmd_str, (
            f"When AMPLIHACK_DELEGATE='amplihack copilot', _build_command() must not "
            f"use hardcoded 'claude' as the binary. Got: {cmd}"
        )

    def test_build_command_does_not_hardcode_claude(self, tmp_path):
        """_build_command() must NOT hardcode ['claude', ...] regardless of env var."""
        proc = make_process(tmp_path)

        # When copilot is set, the first element must NOT be just 'claude'
        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack copilot"}):
            cmd = proc._build_command()

        assert cmd[0] != "claude", (
            f"_build_command() hardcodes 'claude' even when AMPLIHACK_DELEGATE='amplihack copilot'. "
            f"Got: {cmd}. "
            "Fix: replace ['claude', ...] with DELEGATE_COMMANDS lookup on env var."
        )

    def test_build_command_returns_list_not_string(self, tmp_path):
        """_build_command() must always return a list (never a shell string)."""
        proc = make_process(tmp_path)

        for delegate in ["amplihack claude", "amplihack copilot", "amplihack amplifier"]:
            with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": delegate}):
                cmd = proc._build_command()
            assert isinstance(cmd, list), (
                f"_build_command() must return a list for delegate={delegate!r}, "
                f"got {type(cmd).__name__}: {cmd!r}"
            )

    def test_build_command_includes_prompt(self, tmp_path):
        """_build_command() must include the prompt in the command list."""
        proc = make_process(tmp_path)

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack claude"}):
            cmd = proc._build_command()

        assert "test prompt" in cmd, (
            f"_build_command() must include the prompt in the command. Got: {cmd}"
        )

    def test_build_command_includes_permissions_flag(self, tmp_path):
        """_build_command() must include --dangerously-skip-permissions flag."""
        proc = make_process(tmp_path)

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack claude"}):
            cmd = proc._build_command()

        assert "--dangerously-skip-permissions" in cmd, (
            f"_build_command() must include --dangerously-skip-permissions. Got: {cmd}"
        )


# ---------------------------------------------------------------------------
# 3. _build_command(): command mapping for each delegate
# ---------------------------------------------------------------------------


class TestBuildCommandMapping:
    """_build_command() must map each delegate string to the correct binary."""

    def test_amplihack_claude_maps_to_claude_binary(self, tmp_path):
        """'amplihack claude' delegate must use 'claude' as the executable."""
        proc = make_process(tmp_path)

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack claude"}):
            cmd = proc._build_command()

        # 'amplihack claude' should resolve to the 'claude' CLI binary
        assert cmd[0] == "claude", (
            f"'amplihack claude' delegate must resolve to 'claude' binary. Got: {cmd[0]!r}"
        )

    def test_amplihack_copilot_does_not_use_bare_claude(self, tmp_path):
        """'amplihack copilot' delegate must NOT use 'claude' as the executable."""
        proc = make_process(tmp_path)

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack copilot"}):
            cmd = proc._build_command()

        assert cmd[0] != "claude", (
            f"'amplihack copilot' delegate must not use 'claude' binary. "
            f"Got cmd[0]={cmd[0]!r}. Expected something like 'amplihack' or 'gh'."
        )

    def test_amplihack_amplifier_does_not_use_bare_claude(self, tmp_path):
        """'amplihack amplifier' delegate must NOT use 'claude' as the executable."""
        proc = make_process(tmp_path)

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack amplifier"}):
            cmd = proc._build_command()

        assert cmd[0] != "claude", (
            f"'amplihack amplifier' delegate must not use 'claude' binary. Got cmd[0]={cmd[0]!r}."
        )

    def test_model_flag_included_when_model_set(self, tmp_path):
        """_build_command() must include --model flag when model is set."""
        proc = ClaudeProcess(
            prompt="test",
            process_id="test-model",
            working_dir=tmp_path / "work",
            log_dir=tmp_path / "logs",
            model="claude-opus-4-5",
        )

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack claude"}):
            cmd = proc._build_command()

        assert "--model" in cmd, f"Command must include --model flag when model is set: {cmd}"
        model_idx = cmd.index("--model")
        assert cmd[model_idx + 1] == "claude-opus-4-5", (
            f"--model must be followed by the model name. Got: {cmd[model_idx + 1]!r}"
        )


# ---------------------------------------------------------------------------
# 4. Warning behavior: unset or unrecognised AMPLIHACK_DELEGATE
# ---------------------------------------------------------------------------


class TestBuildCommandWarnings:
    """_build_command() must emit warnings.warn() for unset/unrecognised delegate."""

    def test_emits_warning_when_amplihack_delegate_not_set(self, tmp_path):
        """_build_command() must warn when AMPLIHACK_DELEGATE is not in environment."""
        proc = make_process(tmp_path)

        env_without_delegate = {k: v for k, v in os.environ.items() if k != "AMPLIHACK_DELEGATE"}

        with patch.dict(os.environ, env_without_delegate, clear=True):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                cmd = proc._build_command()

        assert len(w) > 0, (
            "_build_command() must emit warnings.warn() when AMPLIHACK_DELEGATE "
            "is not set, so operators know the subprocess is using the default delegate. "
            f"Got {len(w)} warnings, cmd={cmd}"
        )
        # Warning message should mention AMPLIHACK_DELEGATE or the fallback
        warning_texts = " ".join(str(warning.message) for warning in w)
        assert "AMPLIHACK_DELEGATE" in warning_texts or "claude" in warning_texts.lower(), (
            f"Warning must mention 'AMPLIHACK_DELEGATE'. Got: {warning_texts!r}"
        )

    def test_emits_warning_for_unrecognised_delegate(self, tmp_path):
        """_build_command() must warn when AMPLIHACK_DELEGATE has an unrecognised value."""
        proc = make_process(tmp_path)

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "unknown-delegate-xyz"}):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                cmd = proc._build_command()

        assert len(w) > 0, (
            "_build_command() must emit a warning when AMPLIHACK_DELEGATE='unknown-delegate-xyz' "
            "is not in DELEGATE_COMMANDS. "
            f"Got {len(w)} warnings, cmd={cmd}"
        )

    def test_does_not_warn_for_valid_delegate(self, tmp_path):
        """_build_command() must NOT warn when AMPLIHACK_DELEGATE is a valid known delegate."""
        proc = make_process(tmp_path)

        for delegate in ["amplihack claude", "amplihack copilot", "amplihack amplifier"]:
            with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": delegate}):
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    proc._build_command()

            # Filter for our warnings (UserWarning or similar)
            relevant_warnings = [
                wn
                for wn in w
                if "AMPLIHACK_DELEGATE" in str(wn.message) or "delegate" in str(wn.message).lower()
            ]
            assert not relevant_warnings, (
                f"_build_command() must not warn for valid delegate {delegate!r}. "
                f"Got warnings: {[str(wn.message) for wn in relevant_warnings]}"
            )

    def test_falls_back_to_claude_for_unrecognised_delegate(self, tmp_path):
        """_build_command() must fall back to 'claude' for unrecognised delegate."""
        proc = make_process(tmp_path)

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "completely-unknown"}):
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                cmd = proc._build_command()

        assert isinstance(cmd, list), (
            "_build_command() must return a list even for unknown delegate"
        )
        assert len(cmd) >= 1, (
            "_build_command() must return non-empty command even for unknown delegate"
        )
        # Should fall back to 'claude' (the safe default)
        assert cmd[0] in ("claude",), (
            f"_build_command() must fall back to 'claude' for unknown delegate, "
            f"got cmd[0]={cmd[0]!r}"
        )


# ---------------------------------------------------------------------------
# 5. No shell=True in subprocess calls
# ---------------------------------------------------------------------------


class TestNoShellTrue:
    """ClaudeProcess must never use shell=True in subprocess calls."""

    def test_spawn_process_does_not_use_shell_true(self, tmp_path):
        """_spawn_process() must use list-form command (not shell=True)."""

        proc = make_process(tmp_path)
        (tmp_path / "work").mkdir(parents=True, exist_ok=True)
        (tmp_path / "logs").mkdir(parents=True, exist_ok=True)

        popen_calls = []

        def mock_popen(*args, **kwargs):
            popen_calls.append((args, kwargs))
            # Raise immediately so we don't actually execute
            raise RuntimeError("Mock Popen called")

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack claude"}):
            with patch("pty.openpty", return_value=(99, 100)):
                with patch("os.close"):
                    with patch("subprocess.Popen", side_effect=mock_popen):
                        try:
                            proc._spawn_process(["claude", "-p", "test"], slave_fd=100)
                        except RuntimeError:
                            pass

        for args, kwargs in popen_calls:
            assert not kwargs.get("shell", False), (
                "_spawn_process() must NOT use shell=True. "
                f"Got Popen call with shell={kwargs.get('shell')!r}. "
                "shell=True enables command injection vulnerabilities."
            )
            if args:
                cmd_arg = args[0]
                assert isinstance(cmd_arg, list), (
                    f"_spawn_process() must pass command as a list, got {type(cmd_arg).__name__}: "
                    f"{cmd_arg!r}. String commands with shell=False are still a risk."
                )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
