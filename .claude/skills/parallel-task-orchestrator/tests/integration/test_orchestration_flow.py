"""Integration tests for complete orchestration flow.

Tests multiple components working together: issue parsing → worktrees → agents → PRs.

Philosophy: Test realistic workflows with some mocking but real component interaction.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestOrchestrationFlow:
    """Integration tests for end-to-end orchestration workflow."""

    @patch("subprocess.run")
    def test_parse_issue_to_config_flow(self, mock_run, sample_issue_body):
        """Test flow from issue parsing to config creation."""
        from parallel_task_orchestrator.core.issue_parser import GitHubIssueParser
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        # Mock gh issue view
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=f'{{"number": 1783, "body": "{sample_issue_body}"}}'
        )

        # Parse issue
        parser = GitHubIssueParser()
        body = parser.fetch_issue_body(1783)
        sub_issues = parser.parse_sub_issues(body)

        # Create config
        config = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=sub_issues
        )

        assert config.parent_issue == 1783
        assert len(config.sub_issues) == 5
        assert 101 in config.sub_issues

    @patch("subprocess.run")
    def test_deploy_agents_and_monitor_flow(self, mock_run, temp_dir):
        """Test flow from agent deployment to status monitoring."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor

        mock_run.return_value = MagicMock(returncode=0, stdout="")

        # Deploy agents
        deployer = AgentDeployer(worktree_base=temp_dir)
        deployments = deployer.deploy_batch(
            issues=[
                {"number": 101, "title": "Task A"},
                {"number": 102, "title": "Task B"},
            ],
            parent_issue=1783
        )

        assert len(deployments) == 2

        # Create status files
        for deployment in deployments:
            status_file = deployment["status_file"]
            status_file.write_text(json.dumps({
                "agent_id": deployment["agent_id"],
                "issue_number": deployment["issue_number"],
                "status": "in_progress"
            }))

        # Monitor status
        monitor = StatusMonitor(worktree_base=temp_dir)
        statuses = monitor.poll_all_agents()

        assert len(statuses) >= 2
        assert all(s["status"] == "in_progress" for s in statuses)

    @patch("subprocess.run")
    def test_agents_complete_and_create_prs_flow(self, mock_run, temp_dir):
        """Test flow from agent completion to PR creation."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        # Setup completed agent statuses
        worktree_base = temp_dir / "worktrees"
        worktree_base.mkdir()

        completed_agents = []
        for issue_num in [101, 102]:
            wt_path = worktree_base / f"feat-issue-{issue_num}"
            wt_path.mkdir()

            status_file = wt_path / ".agent_status.json"
            status_file.write_text(json.dumps({
                "agent_id": f"agent-{issue_num}",
                "issue_number": issue_num,
                "status": "completed",
                "branch_name": f"feat/issue-{issue_num}",
            }))

            completed_agents.append({
                "issue_number": issue_num,
                "branch_name": f"feat/issue-{issue_num}",
                "summary": f"Completed task {issue_num}",
            })

        # Monitor and detect completion
        monitor = StatusMonitor(worktree_base=worktree_base)
        statuses = monitor.poll_all_agents()
        completed = monitor.filter_by_status(statuses, "completed")

        assert len(completed) == 2

        # Create PRs
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 1801, "url": "https://github.com/owner/repo/pull/1801"}'
        )

        creator = PRCreator()
        pr_results = creator.create_batch(completed_agents, parent_issue=1783)

        assert len(pr_results) == 2

    def test_config_to_deployment_to_report_flow(self, temp_dir):
        """Test complete flow from config to final report."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer
        from parallel_task_orchestrator.models.completion import OrchestrationReport
        import time

        # Create config
        config = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=[101, 102, 103],
            parallel_degree=3
        )

        # Deploy (mocked)
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            deployer = AgentDeployer(worktree_base=temp_dir)
            deployments = deployer.deploy_batch(
                [{"number": n, "title": f"Task {n}"} for n in config.sub_issues],
                parent_issue=config.parent_issue
            )

        assert len(deployments) == 3

        # Simulate completion
        time.sleep(0.1)  # Small delay for duration

        # Generate report
        report = OrchestrationReport(
            parent_issue=1783,
            total_sub_issues=3,
            completed=3,
            failed=0,
            duration_seconds=1
        )

        assert report.calculate_success_rate() == 100.0

    @patch("subprocess.run")
    def test_partial_failure_recovery_flow(self, mock_run, temp_dir):
        """Test flow when some agents fail and recovery is needed."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor
        from parallel_task_orchestrator.models.completion import OrchestrationReport

        mock_run.return_value = MagicMock(returncode=0)

        # Deploy agents
        deployer = AgentDeployer(worktree_base=temp_dir)
        issues = [{"number": n, "title": f"Task {n}"} for n in [101, 102, 103]]
        deployments = deployer.deploy_batch(issues, parent_issue=1783)

        # Simulate mixed results
        for i, deployment in enumerate(deployments):
            status = "completed" if i < 2 else "failed"
            errors = [] if status == "completed" else ["Timeout error"]

            deployment["status_file"].write_text(json.dumps({
                "agent_id": deployment["agent_id"],
                "issue_number": deployment["issue_number"],
                "status": status,
                "errors": errors,
            }))

        # Monitor and detect failures
        monitor = StatusMonitor(worktree_base=temp_dir)
        statuses = monitor.poll_all_agents()

        completed = monitor.filter_by_status(statuses, "completed")
        failed = monitor.filter_by_status(statuses, "failed")

        assert len(completed) == 2
        assert len(failed) == 1

        # Generate report with failures
        report = OrchestrationReport(
            parent_issue=1783,
            total_sub_issues=3,
            completed=2,
            failed=1,
            failures=[{
                "issue_number": 103,
                "error": "Timeout",
                "status": "failed"
            }]
        )

        assert report.calculate_success_rate() == pytest.approx(66.67, rel=0.1)
        assert len(report.failures) == 1

    @patch("subprocess.run")
    def test_worktree_isolation_between_agents(self, mock_run, temp_dir):
        """Test that agents are properly isolated in separate worktrees."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        mock_run.return_value = MagicMock(returncode=0)

        deployer = AgentDeployer(worktree_base=temp_dir)
        deployments = deployer.deploy_batch(
            [{"number": n, "title": f"Task {n}"} for n in [101, 102, 103]],
            parent_issue=1783
        )

        # Verify each has unique worktree
        worktree_paths = [d["worktree_path"] for d in deployments]
        assert len(worktree_paths) == len(set(worktree_paths))  # All unique

        # Verify each has unique branch
        branches = [d.get("branch_name", "") for d in deployments]
        assert len(branches) == len(set(branches))

    @patch("subprocess.run")
    def test_status_updates_trigger_actions(self, mock_run, temp_dir):
        """Test that status changes trigger appropriate actions."""
        from parallel_task_orchestrator.core.status_monitor import StatusMonitor
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        # Setup worktree with agent
        worktree_base = temp_dir / "worktrees"
        worktree_base.mkdir()
        wt_path = worktree_base / "feat-issue-101"
        wt_path.mkdir()

        status_file = wt_path / ".agent_status.json"

        # Start as in_progress
        status_file.write_text(json.dumps({
            "agent_id": "agent-101",
            "issue_number": 101,
            "status": "in_progress",
        }))

        monitor = StatusMonitor(worktree_base=worktree_base)
        old_statuses = monitor.poll_all_agents()

        # Change to completed
        status_file.write_text(json.dumps({
            "agent_id": "agent-101",
            "issue_number": 101,
            "status": "completed",
            "branch_name": "feat/issue-101",
        }))

        new_statuses = monitor.poll_all_agents()
        changes = monitor.detect_changes(old_statuses, new_statuses)

        # Should detect completion
        assert len(changes) > 0
        assert changes[0]["new_status"] == "completed"

        # Should trigger PR creation
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 1801}'
        )

        creator = PRCreator()
        result = creator.create_pr(
            branch_name="feat/issue-101",
            title="feat: Task completed",
            body="Auto-generated"
        )

        assert result["number"] == 1801

    def test_error_propagation_through_flow(self, temp_dir):
        """Test that errors are properly propagated and reported."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer
        from parallel_task_orchestrator.models.completion import OrchestrationReport

        # Simulate deployment failure
        with patch("subprocess.run", side_effect=Exception("Git error")):
            deployer = AgentDeployer(worktree_base=temp_dir)

            with pytest.raises(RuntimeError, match="deployment failed"):
                deployer.deploy_agent(101, "Task", 1783)

        # Error should be capturable in report
        report = OrchestrationReport(
            parent_issue=1783,
            total_sub_issues=1,
            completed=0,
            failed=1,
            failures=[{
                "issue_number": 101,
                "error": "Git error during deployment",
                "status": "failed"
            }]
        )

        assert report.failed == 1
        assert len(report.failures) == 1
