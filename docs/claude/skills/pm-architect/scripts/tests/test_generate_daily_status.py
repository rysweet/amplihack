"""Tests for generate_daily_status.py - Basic coverage."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from generate_daily_status import get_recent_git_activity, load_project_state


class TestLoadProjectState:
    """Tests for load_project_state function."""

    def test_no_pm_state_directory(self, project_root):
        """Test when PM state directory doesn't exist."""
        result = load_project_state(project_root)
        assert result is None

    def test_empty_pm_state_directory(self, tmp_path):
        """Test when PM state directory exists but is empty."""
        pm_state_dir = tmp_path / ".claude" / "pm_state"
        pm_state_dir.mkdir(parents=True)

        result = load_project_state(tmp_path)
        assert result is None

    def test_load_backlog_only(self, tmp_path):
        """Test loading only backlog file."""
        pm_state_dir = tmp_path / ".claude" / "pm_state"
        pm_state_dir.mkdir(parents=True)

        backlog_file = pm_state_dir / "backlog.yaml"
        backlog_file.write_text("items:\n  - id: 1\n    title: Task 1\n")

        result = load_project_state(tmp_path)
        assert result is not None
        assert "backlog" in result
        assert "items" in result["backlog"]

    def test_load_all_state_files(self, tmp_path):
        """Test loading all PM state files."""
        pm_state_dir = tmp_path / ".claude" / "pm_state"
        pm_state_dir.mkdir(parents=True)

        (pm_state_dir / "backlog.yaml").write_text("items: []\n")
        (pm_state_dir / "workstreams.yaml").write_text("workstreams: []\n")
        (pm_state_dir / "project_config.yaml").write_text("name: Test\n")

        result = load_project_state(tmp_path)
        assert result is not None
        assert "backlog" in result
        assert "workstreams" in result
        assert "config" in result


class TestGetRecentGitActivity:
    """Tests for get_recent_git_activity function."""

    def test_git_activity_with_commits(self, project_root):
        """Test with recent git commits."""
        from unittest.mock import MagicMock

        mock_output = "abc123 (HEAD -> main) Recent commit\ndef456 Another commit"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr="")

            result = get_recent_git_activity(project_root)

            assert "Recent Git Activity" in result
            assert "abc123" in result

    def test_git_activity_no_commits(self, project_root):
        """Test when no recent commits."""
        from unittest.mock import MagicMock

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = get_recent_git_activity(project_root)

            assert "No commits in the last 24 hours" in result or "No recent commits" in result

    def test_git_command_failure(self, project_root):
        """Test git command failure handling."""
        from unittest.mock import MagicMock

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Not a git repo")

            result = get_recent_git_activity(project_root)

            assert (
                "Unable to retrieve" in result
                or "No commits in the last 24 hours" in result
                or "No recent commits" in result
            )


class TestMainFunction:
    """Basic tests for main function."""

    def test_main_sdk_not_available(self, capsys):
        """Test main when SDK not available."""
        with patch("generate_daily_status.CLAUDE_SDK_AVAILABLE", False):
            with patch("sys.argv", ["generate_daily_status.py"]):
                from generate_daily_status import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "not installed" in captured.err
