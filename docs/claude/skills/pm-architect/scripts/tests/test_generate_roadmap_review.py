"""Tests for generate_roadmap_review.py - Basic coverage."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest  # pyright: ignore[reportMissingImports]

sys.path.insert(0, str(Path(__file__).parent.parent))
from agent_query import AgentQueryError
from generate_roadmap_review import get_git_velocity_metrics, load_project_state


class TestLoadProjectState:
    """Tests for load_project_state function."""

    def test_no_pm_state_directory(self, project_root):
        """Test when PM state directory doesn't exist."""
        result = load_project_state(project_root)
        assert result is None

    def test_load_state_files(self, tmp_path):
        """Test loading PM state files."""
        pm_state_dir = tmp_path / ".claude" / "pm_state"
        pm_state_dir.mkdir(parents=True)

        (pm_state_dir / "backlog.yaml").write_text("items: []\n")

        result = load_project_state(tmp_path)
        assert result is not None
        assert "backlog" in result


class TestGetGitVelocityMetrics:
    """Tests for get_git_velocity_metrics function."""

    def test_velocity_metrics_with_commits(self, project_root):
        """Test velocity metrics with commits."""
        from unittest.mock import MagicMock

        mock_commits = "abc123 Commit 1\ndef456 Commit 2\nghi789 Commit 3"

        with patch("subprocess.run") as mock_run:
            # Mock git log call
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_commits, stderr="")

            result = get_git_velocity_metrics(project_root)

            assert "Velocity Metrics" in result or "commits" in result.lower()

    def test_velocity_metrics_no_activity(self, project_root):
        """Test when no git activity."""
        from unittest.mock import MagicMock

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = get_git_velocity_metrics(project_root)

            # Should still return valid metrics structure
            assert isinstance(result, str)


class TestMainFunction:
    """Basic tests for main function."""

    def test_main_sdk_not_available(self, capsys):
        """Test main when SDK not available."""
        with patch("generate_roadmap_review.SDK_AVAILABLE", False):
            with patch("sys.argv", ["generate_roadmap_review.py"]):
                from generate_roadmap_review import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "No agent SDK installed" in captured.err


class TestGenerateRoadmapReview:
    """Tests for generate_roadmap_review error handling."""

    @pytest.mark.asyncio
    async def test_generate_roadmap_review_handles_agent_query_error(self, project_root, capsys):
        """Agent query failures should be surfaced explicitly."""
        from generate_roadmap_review import generate_roadmap_review

        with patch("generate_roadmap_review.SDK_AVAILABLE", True):
            with patch(
                "generate_roadmap_review.get_git_velocity_metrics", return_value="## Velocity"
            ):
                with patch(
                    "generate_roadmap_review.get_milestone_progress",
                    return_value="## Milestones",
                ):
                    with patch(
                        "generate_roadmap_review.query_agent",
                        side_effect=AgentQueryError("SDK error"),
                    ):
                        result = await generate_roadmap_review(project_root)

        assert result is None
        captured = capsys.readouterr()
        assert "Error generating roadmap review: SDK error" in captured.err
