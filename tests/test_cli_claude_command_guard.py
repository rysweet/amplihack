"""Tests for the Claude plugin installation command guard.

Verifies that Claude Code plugin installation (marketplace config, CLI install)
only runs for Claude-specific commands (None, launch, claude, RustyClawd),
and is skipped for non-Claude commands (copilot, amplifier, codex, etc.).

Bug: https://github.com/rysweet/amplihack/issues/2236
"""

import argparse
import contextlib
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_args(command: str | None) -> argparse.Namespace:
    """Build a minimal Namespace that looks like parse_args_with_passthrough output."""
    return argparse.Namespace(
        command=command,
        verbose=False,
        quiet=False,
        skip_update_check=True,
        no_proxy=True,
    )


_NON_CLAUDE_COMMANDS = [
    "copilot",
    "amplifier",
    "codex",
    "install",
    "uninstall",
    "uvx-help",
    "plugin",
    "memory",
    "mode",
]

_CLAUDE_COMMAND_LIST = [None, "launch", "claude", "RustyClawd"]


def _apply_patches(extra_patches: dict | None = None):
    """Create an ExitStack with all the patches needed to run main() in UVX mode.

    Returns (stack, mocks_dict) where mocks_dict has named mocks for assertions.
    """
    mock_configure = MagicMock(return_value=True)
    mock_get_cli = MagicMock(return_value="/usr/bin/claude")
    mock_subprocess_run = MagicMock(return_value=MagicMock(returncode=0, stdout="ok", stderr=""))

    # Conflict detector mock
    mock_conflict_result = MagicMock(has_conflicts=False, conflicting_files=[])
    mock_detector = MagicMock()
    mock_detector.detect_conflicts.return_value = mock_conflict_result

    # Copy strategy mock
    mock_copy_strategy = MagicMock(
        should_proceed=True,
        target_dir="/tmp/fake_plugin_dir",
    )
    mock_strategy_manager = MagicMock()
    mock_strategy_manager.determine_target.return_value = mock_copy_strategy

    # These are local imports inside main(), so patch at their source modules
    patches = {
        "amplihack.cli.is_uvx_deployment": MagicMock(return_value=True),
        "amplihack.cli.cleanup_legacy_skills": MagicMock(),
        "amplihack.safety.GitConflictDetector": MagicMock(return_value=mock_detector),
        "amplihack.safety.SafeCopyStrategy": MagicMock(return_value=mock_strategy_manager),
        "amplihack.cli._configure_amplihack_marketplace": mock_configure,
        "amplihack.cli.get_claude_cli_path": mock_get_cli,
        "amplihack.cli.subprocess.run": mock_subprocess_run,
    }
    if extra_patches:
        patches.update(extra_patches)

    return patches, {
        "configure_marketplace": mock_configure,
        "get_cli_path": mock_get_cli,
        "subprocess_run": mock_subprocess_run,
    }


def _run_main_with_command(command: str | None):
    """Run main() with mocks, return the named mocks for assertions."""
    patches, mocks = _apply_patches(
        {
            "amplihack.cli.parse_args_with_passthrough": MagicMock(
                return_value=(_make_args(command), [])
            ),
        }
    )

    with contextlib.ExitStack() as stack:
        for target, mock_obj in patches.items():
            stack.enter_context(patch(target, mock_obj))
        try:
            from amplihack.cli import main

            main()
        except Exception:
            # main() will fail when dispatching to subcommand handlers
            # since we haven't mocked them. That's fine -- we only care
            # about whether plugin install was called.
            pass

    return mocks


# ---------------------------------------------------------------------------
# Tests: non-Claude commands must SKIP plugin installation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", _NON_CLAUDE_COMMANDS)
def test_non_claude_command_skips_plugin_install(command):
    """Plugin installation functions must NOT be called for non-Claude commands."""
    mocks = _run_main_with_command(command)

    (
        mocks["configure_marketplace"].assert_not_called(),
        (f"_configure_amplihack_marketplace should NOT be called for command={command!r}"),
    )
    (
        mocks["get_cli_path"].assert_not_called(),
        (f"get_claude_cli_path should NOT be called for command={command!r}"),
    )


# ---------------------------------------------------------------------------
# Tests: Claude commands MUST run plugin installation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", _CLAUDE_COMMAND_LIST)
def test_claude_command_runs_plugin_install(command):
    """Plugin installation functions MUST be called for Claude-specific commands."""
    mocks = _run_main_with_command(command)

    (
        mocks["configure_marketplace"].assert_called_once(),
        (f"_configure_amplihack_marketplace MUST be called for command={command!r}"),
    )


# ---------------------------------------------------------------------------
# Tests: _CLAUDE_COMMANDS constant
# ---------------------------------------------------------------------------


def test_claude_commands_constant_exists():
    """The _CLAUDE_COMMANDS set must be defined in cli module."""
    from amplihack.cli import _CLAUDE_COMMANDS

    assert isinstance(_CLAUDE_COMMANDS, (set, frozenset))
    assert None in _CLAUDE_COMMANDS
    assert "launch" in _CLAUDE_COMMANDS
    assert "claude" in _CLAUDE_COMMANDS
    assert "RustyClawd" in _CLAUDE_COMMANDS


def test_claude_commands_does_not_include_copilot():
    """The _CLAUDE_COMMANDS set must NOT include non-Claude commands."""
    from amplihack.cli import _CLAUDE_COMMANDS

    for cmd in _NON_CLAUDE_COMMANDS:
        assert cmd not in _CLAUDE_COMMANDS, f"{cmd!r} should not be in _CLAUDE_COMMANDS"
