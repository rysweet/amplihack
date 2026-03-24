"""Tests for Rust-first handoff in the top-level amplihack entrypoint."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from amplihack import _delegate_to_rust_cli_if_supported, main


def test_delegate_to_rust_cli_for_recipe_command():
    rust_cli = Path("/tmp/amplihack-rs")

    with (
        patch("amplihack.auto_update._find_rust_cli", return_value=rust_cli),
        patch("amplihack.subprocess.run", return_value=MagicMock(returncode=17)) as mock_run,
    ):
        result = _delegate_to_rust_cli_if_supported(["recipe", "list"])

    assert result == 17
    mock_run.assert_called_once_with([str(rust_cli), "recipe", "list"], check=False)


def test_delegate_to_rust_cli_for_install_command():
    rust_cli = Path("/tmp/amplihack-rs")

    with (
        patch("amplihack.auto_update._find_rust_cli", return_value=rust_cli),
        patch("amplihack.subprocess.run", return_value=MagicMock(returncode=5)) as mock_run,
    ):
        result = _delegate_to_rust_cli_if_supported(["install"])

    assert result == 5
    mock_run.assert_called_once_with([str(rust_cli), "install"], check=False)


def test_delegate_to_rust_cli_skips_unsupported_commands():
    with patch("amplihack.auto_update._find_rust_cli") as mock_find:
        result = _delegate_to_rust_cli_if_supported(["copilot", "--resume"])

    assert result is None
    mock_find.assert_not_called()


def test_main_skips_python_bootstrap_when_rust_cli_handles_command():
    with (
        patch("amplihack._delegate_to_rust_cli_if_supported", return_value=0) as mock_delegate,
        patch("amplihack.memory_auto_install.ensure_memory_lib_installed") as mock_memory,
        patch("amplihack.copilot_auto_install.ensure_copilot_sdk_installed") as mock_copilot,
        patch("amplihack.cli.main") as mock_cli,
    ):
        result = main()

    assert result == 0
    mock_delegate.assert_called_once_with()
    mock_memory.assert_not_called()
    mock_copilot.assert_not_called()
    mock_cli.assert_not_called()


def test_main_falls_back_to_python_cli_when_no_rust_handoff():
    with (
        patch("amplihack._delegate_to_rust_cli_if_supported", return_value=None),
        patch("amplihack.memory_auto_install.ensure_memory_lib_installed") as mock_memory,
        patch("amplihack.copilot_auto_install.ensure_copilot_sdk_installed") as mock_copilot,
        patch("amplihack.cli.main", return_value=23) as mock_cli,
    ):
        result = main()

    assert result == 23
    mock_memory.assert_called_once_with()
    mock_copilot.assert_called_once_with()
    mock_cli.assert_called_once_with()
