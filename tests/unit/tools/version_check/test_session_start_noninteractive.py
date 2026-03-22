"""Regression tests for non-interactive session_start version prompts."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "tools" / "amplihack" / "hooks"))
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "tools" / "amplihack"))

from session_start import SessionStartHook
from version_checker import VersionInfo


def _make_hook() -> SessionStartHook:
    hook = SessionStartHook.__new__(SessionStartHook)
    hook.project_root = PROJECT_ROOT
    hook.log = MagicMock()
    hook.save_metric = MagicMock()
    return hook


def test_check_version_mismatch_skips_prompt_for_noninteractive_stdin(capsys):
    """Headless sessions should not block on select() waiting for input."""
    hook = _make_hook()
    version_info = VersionInfo(
        package_commit="new123",
        project_commit="old456",
        is_mismatched=True,
        package_path=PROJECT_ROOT / ".claude" / "tools" / "amplihack",
        project_path=PROJECT_ROOT,
    )

    fake_stdin = MagicMock()
    fake_stdin.isatty.return_value = False

    with patch("version_checker.check_version_mismatch", return_value=version_info):
        with patch("update_prefs.load_update_preference", return_value=None):
            with patch("update_engine.perform_update") as mock_update:
                with patch("sys.stdin", fake_stdin):
                    with patch(
                        "select.select",
                        side_effect=AssertionError(
                            "select() should not run for non-interactive stdin"
                        ),
                    ):
                        hook._check_version_mismatch()

    stderr = capsys.readouterr().err
    assert "Non-interactive session detected - skipping update prompt" in stderr
    mock_update.assert_not_called()
    hook.save_metric.assert_any_call("version_prompt_skipped_non_interactive", True)
