"""Integration tests specifically for ParallelOrchestrator.

Tests the main orchestrator class end-to-end with mocked components.
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestParallelOrchestrator:
    """Integration tests for ParallelOrchestrator class."""

    @patch("subprocess.run")
    def test_orchestrator_initialization(self, mock_run, temp_dir):
        """Test orchestrator initializes all components correctly."""
        from parallel_task_orchestrator.core import ParallelOrchestrator

        orchestrator = ParallelOrchestrator(worktree_base=temp_dir)

        assert orchestrator.worktree_base == temp_dir
        assert orchestrator.issue_parser is not None
        assert orchestrator.agent_deployer is not None
        assert orchestrator.status_monitor is not None
        assert orchestrator.pr_creator is not None

    def test_orchestrator_from_config_file(self, temp_dir):
        """Test creating orchestrator from config file."""
        from parallel_task_orchestrator.core import ParallelOrchestrator

        # Create config file
        config = {
            "parent_issue": 1783,
            "sub_issues": [101, 102],
            "parallel_degree": 2,
            "timeout_minutes": 60,
            "recovery_strategy": "continue_on_failure",
            "worktree_base": str(temp_dir),
            "status_poll_interval": 10
        }

        config_file = temp_dir / "test_config.json"
        config_file.write_text(json.dumps(config))

        # Load from file
        orchestrator = ParallelOrchestrator.from_config_file(config_file)

        assert orchestrator.worktree_base == temp_dir
        assert orchestrator.timeout_minutes == 60
        assert orchestrator.status_poll_interval == 10

    def test_get_current_status_not_started(self, temp_dir):
        """Test get_current_status when orchestration not started."""
        from parallel_task_orchestrator.core import ParallelOrchestrator

        orchestrator = ParallelOrchestrator(worktree_base=temp_dir)
        status = orchestrator.get_current_status()

        assert status["status"] == "not_started"

    @patch("subprocess.run")
    def test_orchestrate_with_no_sub_issues(self, mock_run, temp_dir):
        """Test orchestration fails gracefully when no sub-issues found."""
        from parallel_task_orchestrator.core import ParallelOrchestrator

        # Mock gh issue view returning empty body
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"number": 1783, "body": "No sub-issues here"})
        )

        orchestrator = ParallelOrchestrator(worktree_base=temp_dir)

        with pytest.raises(RuntimeError, match="No sub-issues found"):
            orchestrator.orchestrate(parent_issue=1783)

    @patch("subprocess.run")
    def test_orchestrate_successful_flow(self, mock_run, temp_dir):
        """Test successful end-to-end orchestration."""
        from parallel_task_orchestrator.core import ParallelOrchestrator

        def mock_subprocess(args, **kwargs):
            cmd = " ".join(str(a) for a in args)

            # gh issue view
            if "issue view" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps({
                        "number": 1783,
                        "body": "Sub-issues: #101, #102"
                    })
                )

            # git worktree add
            if "worktree add" in cmd:
                return MagicMock(returncode=0, stdout="")

            # git branch (for PR validation)
            if "git branch" in cmd:
                return MagicMock(returncode=0, stdout="")

            # gh pr create
            if "pr create" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps({"number": 1801, "url": "https://github.com/test/repo/pull/1801"})
                )

            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = mock_subprocess

        orchestrator = ParallelOrchestrator(
            worktree_base=temp_dir,
            timeout_minutes=1,
            status_poll_interval=10  # Minimum allowed
        )

        # Create mock status files showing completion
        for issue_num in [101, 102]:
            wt_path = temp_dir / f"feat-issue-{issue_num}"
            wt_path.mkdir(parents=True, exist_ok=True)
            status_file = wt_path / ".agent_status.json"
            status_file.write_text(json.dumps({
                "agent_id": f"agent-{issue_num}",
                "issue_number": issue_num,
                "status": "completed",
                "branch_name": f"feat/issue-{issue_num}",
                "completion_percentage": 100,
                "last_update": "2025-12-01T00:00:00"
            }))

        # Run orchestration
        result = orchestrator.orchestrate(parent_issue=1783, parallel_degree=2)

        # Verify results
        assert result["total_sub_issues"] == 2
        assert result["completed"] == 2
        assert result["failed"] == 0
        assert result["success_rate"] == 100.0
        assert result["success"] is True

    def test_orchestrate_keyboard_interrupt_handling(self, temp_dir):
        """Test orchestration handles KeyboardInterrupt gracefully."""
        from parallel_task_orchestrator.core import ParallelOrchestrator

        orchestrator = ParallelOrchestrator(worktree_base=temp_dir)

        # Mock _monitor_agents to raise KeyboardInterrupt
        with patch.object(orchestrator, "_monitor_agents", side_effect=KeyboardInterrupt):
            with patch.object(orchestrator.issue_parser, "fetch_issue_body", return_value="Test #101"):
                with pytest.raises(KeyboardInterrupt):
                    orchestrator.orchestrate(parent_issue=1783)

    @patch("subprocess.run")
    def test_orchestrate_partial_failures(self, mock_run, temp_dir):
        """Test orchestration with some agents failing."""
        from parallel_task_orchestrator.core import ParallelOrchestrator

        def mock_subprocess(args, **kwargs):
            cmd = " ".join(str(a) for a in args)

            if "issue view" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps({
                        "number": 1783,
                        "body": "Sub-issues: #101, #102, #103"
                    })
                )

            if "worktree add" in cmd:
                return MagicMock(returncode=0, stdout="")

            if "pr create" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps({"number": 1801, "url": "https://test.com/pr/1801"})
                )

            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = mock_subprocess

        orchestrator = ParallelOrchestrator(
            worktree_base=temp_dir,
            timeout_minutes=1,
            status_poll_interval=10  # Minimum allowed
        )

        # Create status files: 2 completed, 1 failed
        for issue_num, status in [(101, "completed"), (102, "completed"), (103, "failed")]:
            wt_path = temp_dir / f"feat-issue-{issue_num}"
            wt_path.mkdir(parents=True, exist_ok=True)
            status_file = wt_path / ".agent_status.json"

            status_data = {
                "agent_id": f"agent-{issue_num}",
                "issue_number": issue_num,
                "status": status,
                "branch_name": f"feat/issue-{issue_num}",
                "completion_percentage": 100 if status == "completed" else 0,
                "last_update": "2025-12-01T00:00:00"
            }

            if status == "failed":
                status_data["errors"] = ["Test error"]

            status_file.write_text(json.dumps(status_data))

        # Run orchestration
        result = orchestrator.orchestrate(
            parent_issue=1783,
            parallel_degree=3,
            recovery_strategy="continue_on_failure"
        )

        # Verify partial success
        assert result["total_sub_issues"] == 3
        assert result["completed"] == 2
        assert result["failed"] == 1
        assert result["success_rate"] == pytest.approx(66.67, rel=0.1)
        assert result["success"] is False  # Not all succeeded

    def test_orchestrate_config_preserved(self, temp_dir):
        """Test that orchestration config is preserved during run."""
        from parallel_task_orchestrator.core import ParallelOrchestrator

        orchestrator = ParallelOrchestrator(worktree_base=temp_dir)

        # Initially no config
        assert orchestrator.current_config is None

        # After setting config manually
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        config = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=[101, 102],
            parallel_degree=2
        )

        orchestrator.current_config = config

        # Config should be accessible
        status = orchestrator.get_current_status()
        assert status["total"] == 2
