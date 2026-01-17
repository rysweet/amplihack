"""Tests for copilot launcher integration with adaptive context."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.launcher.copilot import launch_copilot


@pytest.fixture
def mock_project_root(tmp_path):
    """Create a mock project root."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    runtime_dir = claude_dir / "runtime"
    runtime_dir.mkdir()
    return tmp_path


def test_launcher_writes_context_before_launch(mock_project_root):
    """Test that launcher writes context before launching copilot."""
    with (
        patch("amplihack.launcher.copilot.check_copilot", return_value=True),
        patch("amplihack.launcher.copilot.subprocess.run") as mock_run,
        patch("os.getcwd", return_value=str(mock_project_root)),
    ):
        mock_run.return_value.returncode = 0

        # Launch copilot
        result = launch_copilot(args=["test"])

        # Verify success
        assert result == 0

        # Verify context file was written
        context_file = mock_project_root / ".claude" / "runtime" / "launcher_context.json"
        assert context_file.exists()

        # Verify context contents
        context = json.loads(context_file.read_text())
        assert context["launcher_type"] == "copilot"
        assert "amplihack copilot test" in context["command"]
        assert context["environment"]["AMPLIHACK_LAUNCHER"] == "copilot"


def test_launcher_context_includes_timestamp(mock_project_root):
    """Test that launcher context includes timestamp."""
    with (
        patch("amplihack.launcher.copilot.check_copilot", return_value=True),
        patch("amplihack.launcher.copilot.subprocess.run") as mock_run,
        patch("os.getcwd", return_value=str(mock_project_root)),
    ):
        mock_run.return_value.returncode = 0

        # Launch copilot
        launch_copilot(args=[])

        # Verify context has timestamp
        context_file = mock_project_root / ".claude" / "runtime" / "launcher_context.json"
        context = json.loads(context_file.read_text())
        assert "timestamp" in context
        assert context["timestamp"]  # Non-empty


def test_launcher_handles_no_args(mock_project_root):
    """Test launcher handles no arguments gracefully."""
    with (
        patch("amplihack.launcher.copilot.check_copilot", return_value=True),
        patch("amplihack.launcher.copilot.subprocess.run") as mock_run,
        patch("os.getcwd", return_value=str(mock_project_root)),
    ):
        mock_run.return_value.returncode = 0

        # Launch without args
        result = launch_copilot()

        # Verify context file was written
        context_file = mock_project_root / ".claude" / "runtime" / "launcher_context.json"
        assert context_file.exists()

        context = json.loads(context_file.read_text())
        assert context["launcher_type"] == "copilot"
        assert result == 0


def test_launcher_context_survives_copilot_failure(mock_project_root):
    """Test that context is written even if copilot fails."""
    with (
        patch("amplihack.launcher.copilot.check_copilot", return_value=True),
        patch("amplihack.launcher.copilot.subprocess.run") as mock_run,
        patch("os.getcwd", return_value=str(mock_project_root)),
    ):
        mock_run.return_value.returncode = 1  # Copilot fails

        # Launch copilot
        result = launch_copilot(args=["test"])

        # Verify failure returned
        assert result == 1

        # But context was still written
        context_file = mock_project_root / ".claude" / "runtime" / "launcher_context.json"
        assert context_file.exists()


def test_launcher_creates_runtime_dir_if_missing(mock_project_root):
    """Test launcher creates runtime dir if it doesn't exist."""
    # Remove runtime directory
    runtime_dir = mock_project_root / ".claude" / "runtime"
    runtime_dir.rmdir()

    with (
        patch("amplihack.launcher.copilot.check_copilot", return_value=True),
        patch("amplihack.launcher.copilot.subprocess.run") as mock_run,
        patch("os.getcwd", return_value=str(mock_project_root)),
    ):
        mock_run.return_value.returncode = 0

        # Launch copilot
        launch_copilot(args=["test"])

        # Verify runtime dir was created
        assert runtime_dir.exists()

        # And context file exists
        context_file = runtime_dir / "launcher_context.json"
        assert context_file.exists()
