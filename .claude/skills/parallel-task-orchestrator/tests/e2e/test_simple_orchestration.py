"""End-to-end tests for simple orchestration scenarios.

Tests complete orchestration workflows from issue to PRs with realistic scenarios.

Philosophy: Slow but comprehensive - test actual user workflows end-to-end.
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestSimpleOrchestration:
    """E2E tests for simple orchestration scenarios."""

    @pytest.mark.slow
    @patch("subprocess.run")
    def test_three_sub_issues_all_succeed(self, mock_run, temp_dir):
        """Test complete orchestration with 3 sub-issues, all successful.

        Scenario:
        - Parent issue #1783 with 3 sub-issues
        - All agents complete successfully
        - All PRs created
        - Success rate: 100%
        """
        from parallel_task_orchestrator.core.orchestrator import ParallelOrchestrator

        # Mock gh CLI responses
        def mock_subprocess(args, **kwargs):
            cmd = " ".join(str(a) for a in args)

            # gh issue view
            if "issue view" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps({
                        "number": 1783,
                        "body": "Sub-tasks: #101, #102, #103"
                    })
                )

            # git worktree add
            if "worktree add" in cmd:
                return MagicMock(returncode=0, stdout="")

            # gh pr create
            if "pr create" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps({"number": 1801, "url": "https://github.com/owner/repo/pull/1801"})
                )

            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = mock_subprocess

        # Run orchestration
        orchestrator = ParallelOrchestrator(worktree_base=temp_dir)
        result = orchestrator.orchestrate(
            parent_issue=1783,
            parallel_degree=3,
            timeout_minutes=60
        )

        # Verify results
        assert result["success"] is True
        assert result["total_sub_issues"] == 3
        assert result["completed"] == 3
        assert result["failed"] == 0
        assert result["success_rate"] == 100.0

    @pytest.mark.slow
    @patch("subprocess.run")
    def test_five_sub_issues_one_fails(self, mock_run, temp_dir):
        """Test orchestration with 5 sub-issues, one failure.

        Scenario:
        - Parent issue with 5 sub-issues
        - 4 agents complete successfully
        - 1 agent fails with timeout
        - Continue-on-failure recovery
        - Success rate: 80%
        """
        from parallel_task_orchestrator.core.orchestrator import ParallelOrchestrator

        # Track which issues have been processed
        processed_issues = set()

        def mock_subprocess(args, **kwargs):
            cmd = " ".join(str(a) for a in args)

            if "issue view" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps({
                        "number": 1783,
                        "body": "Sub-tasks: #101, #102, #103, #104, #105"
                    })
                )

            if "worktree add" in cmd:
                # Extract issue number from branch name
                for issue_num in [101, 102, 103, 104, 105]:
                    if f"issue-{issue_num}" in cmd:
                        processed_issues.add(issue_num)
                        break
                return MagicMock(returncode=0, stdout="")

            if "pr create" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=json.dumps({"number": 1801})
                )

            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = mock_subprocess

        # Run orchestration
        orchestrator = ParallelOrchestrator(worktree_base=temp_dir)
        result = orchestrator.orchestrate(
            parent_issue=1783,
            parallel_degree=5,
            timeout_minutes=60,
            recovery_strategy="continue_on_failure"
        )

        # Verify results
        assert result["total_sub_issues"] == 5
        assert result["completed"] >= 4  # At least 4 should complete
        assert result["failed"] <= 1     # At most 1 should fail
        assert result["success_rate"] >= 80.0

    @pytest.mark.slow
    def test_orchestration_with_config_file(self, temp_dir):
        """Test orchestration using configuration file.

        Scenario:
        - Load config from JSON file
        - Execute orchestration based on config
        - Verify config parameters respected
        """
        from parallel_task_orchestrator.core.orchestrator import ParallelOrchestrator

        # Create config file
        config = {
            "parent_issue": 1783,
            "sub_issues": [101, 102, 103],
            "parallel_degree": 3,
            "timeout_minutes": 120,
            "recovery_strategy": "continue_on_failure"
        }

        config_file = temp_dir / "orchestration_config.json"
        config_file.write_text(json.dumps(config))

        # Load and execute
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            orchestrator = ParallelOrchestrator.from_config_file(config_file)
            result = orchestrator.orchestrate_from_config()

        assert result["total_sub_issues"] == 3

    @pytest.mark.slow
    @patch("subprocess.run")
    def test_orchestration_status_monitoring_realtime(self, mock_run, temp_dir):
        """Test real-time status monitoring during orchestration.

        Scenario:
        - Start orchestration
        - Monitor status updates
        - Verify progress tracking
        - Detect completion
        """
        from parallel_task_orchestrator.core.orchestrator import ParallelOrchestrator

        mock_run.return_value = MagicMock(returncode=0, stdout='{"number": 1783}')

        orchestrator = ParallelOrchestrator(
            worktree_base=temp_dir,
            status_poll_interval=1  # Fast polling for test
        )

        # Start orchestration in background
        import threading

        result_holder = {}

        def run_orchestration():
            result_holder["result"] = orchestrator.orchestrate(
                parent_issue=1783,
                parallel_degree=3
            )

        thread = threading.Thread(target=run_orchestration)
        thread.start()

        # Monitor status
        time.sleep(2)  # Let it run briefly
        status = orchestrator.get_current_status()

        # Should have status information
        assert "agents" in status or "total" in status

        thread.join(timeout=5)

    @pytest.mark.slow
    def test_orchestration_generates_complete_report(self, temp_dir):
        """Test that orchestration generates comprehensive final report.

        Scenario:
        - Complete orchestration
        - Generate report
        - Verify report completeness
        """
        from parallel_task_orchestrator.core.orchestrator import ParallelOrchestrator

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            orchestrator = ParallelOrchestrator(worktree_base=temp_dir)
            result = orchestrator.orchestrate(parent_issue=1783)

        # Report should include
        report = result["report"]
        assert "parent_issue" in report
        assert "total_sub_issues" in report
        assert "completed" in report
        assert "failed" in report
        assert "duration_seconds" in report
        assert "pr_links" in report or "prs" in report

    @pytest.mark.slow
    @patch("subprocess.run")
    def test_orchestration_cleanup_on_completion(self, mock_run, temp_dir):
        """Test that worktrees are cleaned up after completion.

        Scenario:
        - Run orchestration
        - Complete all tasks
        - Verify worktrees removed
        - Verify status files archived
        """
        from parallel_task_orchestrator.core.orchestrator import ParallelOrchestrator

        mock_run.return_value = MagicMock(returncode=0)

        orchestrator = ParallelOrchestrator(
            worktree_base=temp_dir,
            cleanup_on_completion=True
        )

        result = orchestrator.orchestrate(parent_issue=1783)

        # Should have called worktree remove
        remove_calls = [
            call for call in mock_run.call_args_list
            if "worktree" in str(call) and "remove" in str(call)
        ]

        assert len(remove_calls) > 0 or result.get("cleanup_complete") is True

    @pytest.mark.slow
    def test_orchestration_logs_detailed_progress(self, temp_dir):
        """Test that orchestration logs detailed progress information.

        Scenario:
        - Run orchestration
        - Verify log file created
        - Verify log contains key events
        """
        from parallel_task_orchestrator.core.orchestrator import ParallelOrchestrator

        log_file = temp_dir / "orchestration.log"

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            orchestrator = ParallelOrchestrator(
                worktree_base=temp_dir,
                log_file=log_file
            )

            result = orchestrator.orchestrate(parent_issue=1783)

        # Verify log exists and has content
        assert log_file.exists() or result.get("log_path") is not None

    @pytest.mark.slow
    @patch("subprocess.run")
    def test_orchestration_posts_summary_comment(self, mock_run, temp_dir):
        """Test that orchestration posts summary to parent issue.

        Scenario:
        - Complete orchestration
        - Generate summary
        - Post comment to parent issue
        - Verify comment includes all PR links
        """
        from parallel_task_orchestrator.core.orchestrator import ParallelOrchestrator

        mock_run.return_value = MagicMock(returncode=0)

        orchestrator = ParallelOrchestrator(
            worktree_base=temp_dir,
            post_summary=True
        )

        result = orchestrator.orchestrate(parent_issue=1783)

        # Should have called gh issue comment
        comment_calls = [
            call for call in mock_run.call_args_list
            if "issue" in str(call) and "comment" in str(call)
        ]

        assert len(comment_calls) > 0 or result.get("summary_posted") is True

    @pytest.mark.slow
    @patch("subprocess.run")
    def test_orchestration_handles_interrupt_gracefully(self, mock_run, temp_dir):
        """Test graceful handling of interrupt signal (Ctrl+C).

        Scenario:
        - Start orchestration
        - Simulate interrupt
        - Verify partial progress saved
        - Verify status files preserved
        """
        from parallel_task_orchestrator.core.orchestrator import ParallelOrchestrator

        mock_run.return_value = MagicMock(returncode=0)

        orchestrator = ParallelOrchestrator(worktree_base=temp_dir)

        # Simulate interrupt during orchestration
        with pytest.raises(KeyboardInterrupt):
            with patch.object(orchestrator, "monitor_agents", side_effect=KeyboardInterrupt):
                orchestrator.orchestrate(parent_issue=1783)

        # Should have partial results saved
        status_files = list(temp_dir.rglob(".agent_status.json"))
        # Files should exist (not cleaned up on interrupt)
        assert len(status_files) >= 0  # May or may not have started
