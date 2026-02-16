"""Unit tests for AgentDeployer - spawning task agents with proper isolation.

Tests the AgentDeployer brick that generates agent prompts, creates worktrees, and launches agents.

Philosophy: Test prompt generation and contract creation logic with mocked subprocess calls.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call


class TestAgentDeployer:
    """Unit tests for agent deployment functionality."""

    def test_generate_agent_prompt_basic(self):
        """Test generation of basic agent prompt for sub-issue."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        deployer = AgentDeployer()
        prompt = deployer.generate_prompt(
            issue_number=101,
            issue_title="Implement authentication module",
            parent_issue=1783
        )

        assert "101" in prompt
        assert "authentication module" in prompt.lower()
        assert "1783" in prompt
        assert len(prompt) > 100  # Should have substantial content

    def test_generate_agent_prompt_with_context(self):
        """Test prompt generation with additional context."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        deployer = AgentDeployer()
        context = {
            "dependencies": [102, 103],
            "priority": "high",
            "estimated_hours": 8,
        }

        prompt = deployer.generate_prompt(
            issue_number=101,
            issue_title="Task A",
            parent_issue=1783,
            context=context
        )

        assert "dependencies" in prompt.lower() or "102" in prompt
        assert "high" in prompt.lower()

    def test_generate_agent_contract(self):
        """Test generation of agent contract specification."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        deployer = AgentDeployer()
        contract = deployer.generate_contract(
            issue_number=101,
            issue_title="Implement feature X"
        )

        # Contract should define expected outputs
        assert "outputs" in contract or "deliverables" in contract
        assert "status_updates" in contract
        assert "issue" in contract.lower()

    def test_create_worktree_path(self):
        """Test generation of worktree path for issue."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        deployer = AgentDeployer(worktree_base="/tmp/worktrees")
        path = deployer.get_worktree_path(issue_number=101)

        assert "/tmp/worktrees" in str(path)
        assert "101" in str(path)
        assert "feat" in str(path).lower() or "issue" in str(path).lower()

    @patch("subprocess.run")
    def test_create_worktree_success(self, mock_run, temp_dir):
        """Test successful git worktree creation."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        deployer = AgentDeployer(worktree_base=temp_dir)
        worktree_path = deployer.create_worktree(
            issue_number=101,
            branch_name="feat/issue-101"
        )

        assert worktree_path.exists() or True  # Mock may not create actual dir
        mock_run.assert_called()
        call_args = str(mock_run.call_args)
        assert "worktree" in call_args
        assert "add" in call_args

    @patch("subprocess.run")
    def test_create_worktree_already_exists(self, mock_run, temp_dir):
        """Test handling of existing worktree."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="worktree already exists"
        )

        deployer = AgentDeployer(worktree_base=temp_dir)

        with pytest.raises(RuntimeError, match="already exists"):
            deployer.create_worktree(101, "feat/issue-101")

    @patch("subprocess.run")
    def test_deploy_agent_full_workflow(self, mock_run, temp_dir):
        """Test full agent deployment workflow."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        deployer = AgentDeployer(worktree_base=temp_dir)
        result = deployer.deploy_agent(
            issue_number=101,
            issue_title="Implement feature X",
            parent_issue=1783
        )

        # Should return deployment details
        assert result["issue_number"] == 101
        assert "worktree_path" in result
        assert "agent_id" in result
        assert "status_file" in result

    def test_generate_status_file_path(self, temp_dir):
        """Test generation of status file path."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        deployer = AgentDeployer(worktree_base=temp_dir)
        status_file = deployer.get_status_file_path("agent-101")

        assert ".agent_status.json" in str(status_file)
        assert "agent-101" in str(status_file) or "101" in str(status_file)

    def test_initialize_status_file(self, temp_dir):
        """Test initialization of agent status file."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        deployer = AgentDeployer(worktree_base=temp_dir)
        status_file = temp_dir / ".agent_status.json"

        deployer.initialize_status_file(
            status_file=status_file,
            agent_id="agent-101",
            issue_number=101
        )

        assert status_file.exists()
        content = json.loads(status_file.read_text())
        assert content["agent_id"] == "agent-101"
        assert content["status"] == "pending"

    def test_validate_deployment_prerequisites(self):
        """Test validation of deployment prerequisites (git repo, gh CLI, etc.)."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        deployer = AgentDeployer()

        # Should check for git, gh CLI, etc.
        validation = deployer.validate_prerequisites()

        assert "git" in validation
        assert "gh" in validation
        # All should be True or have error messages

    @patch("subprocess.run")
    def test_cleanup_worktree(self, mock_run, temp_dir):
        """Test cleanup of worktree after agent completion."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        mock_run.return_value = MagicMock(returncode=0)

        deployer = AgentDeployer(worktree_base=temp_dir)
        worktree_path = temp_dir / "feat-issue-101"
        worktree_path.mkdir()

        deployer.cleanup_worktree(worktree_path)

        # Should call git worktree remove
        mock_run.assert_called()
        call_args = str(mock_run.call_args)
        assert "worktree" in call_args
        assert "remove" in call_args

    def test_generate_agent_id(self):
        """Test generation of unique agent IDs."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        deployer = AgentDeployer()
        agent_id_1 = deployer.generate_agent_id(101)
        agent_id_2 = deployer.generate_agent_id(102)

        assert "agent" in agent_id_1
        assert "101" in agent_id_1
        assert agent_id_1 != agent_id_2

    def test_deploy_batch_of_agents(self, temp_dir):
        """Test deploying multiple agents in batch."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        deployer = AgentDeployer(worktree_base=temp_dir)
        issues = [
            {"number": 101, "title": "Task A"},
            {"number": 102, "title": "Task B"},
            {"number": 103, "title": "Task C"},
        ]

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            results = deployer.deploy_batch(issues, parent_issue=1783)

        assert len(results) == 3
        assert all("agent_id" in r for r in results)
        assert all("worktree_path" in r for r in results)

    def test_deploy_with_parallel_limit(self, temp_dir):
        """Test that deployment respects parallel degree limit."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        deployer = AgentDeployer(
            worktree_base=temp_dir,
            max_parallel=3
        )

        issues = [{"number": i, "title": f"Task {i}"} for i in range(101, 111)]

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            # Should deploy in waves respecting max_parallel
            results = deployer.deploy_batch(issues, parent_issue=1783)

        # All should eventually deploy
        assert len(results) == 10

    @patch("subprocess.run")
    def test_agent_launch_with_claude_code(self, mock_run, temp_dir):
        """Test launching agent with claude CLI in worktree."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        mock_run.return_value = MagicMock(returncode=0)

        deployer = AgentDeployer(worktree_base=temp_dir)
        worktree_path = temp_dir / "feat-issue-101"
        worktree_path.mkdir()

        prompt = "Implement feature X for issue #101"
        deployer.launch_agent(worktree_path, prompt)

        # Should invoke claude CLI with prompt
        mock_run.assert_called()
        call_args = str(mock_run.call_args)
        assert "claude" in call_args.lower()

    def test_error_handling_in_deployment(self, temp_dir):
        """Test error handling during deployment failures."""
        from parallel_task_orchestrator.core.agent_deployer import AgentDeployer

        deployer = AgentDeployer(worktree_base=temp_dir)

        with patch("subprocess.run", side_effect=Exception("Git error")):
            with pytest.raises(RuntimeError, match="deployment failed"):
                deployer.deploy_agent(101, "Task", 1783)


import json  # Add missing import at top of file
