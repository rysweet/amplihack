"""E2E test scenarios for Copilot CLI integration.

Testing pyramid: E2E (10%)
- Complete workflows from user perspective
- Real subprocess execution (mocked for safety)
- System integration validation
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


class TestScenario1SimpleAgentInvocation:
    """Scenario 1: Simple agent invocation via Copilot CLI."""

    @patch("subprocess.run")
    @patch("amplihack.launcher.copilot.check_copilot")
    def test_invoke_single_agent(
        self, mock_check, mock_run, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test invoking a single agent via Copilot CLI."""
        from amplihack.launcher.copilot import launch_copilot

        mock_check.return_value = True
        mock_run.return_value = subprocess.CompletedProcess(
            args=["copilot"], returncode=0, stdout="Success", stderr=""
        )

        # Launch with agent reference
        result = launch_copilot(
            args=["-p", "Design system", "-f", "@.github/agents/architect.md"]
        )

        assert result == 0
        mock_run.assert_called_once()

        # Verify correct command structure
        call_args = mock_run.call_args[0][0]
        assert "copilot" in call_args
        assert "-p" in call_args
        assert "-f" in call_args


class TestScenario2MultiStepWorkflow:
    """Scenario 2: Multi-step workflow with multiple agents."""

    def test_workflow_with_multiple_agents(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test workflow referencing multiple agents sequentially."""
        from amplihack.adapters.copilot_agent_converter import convert_agents

        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Sync agents first
        report = convert_agents(source_dir, target_dir)
        assert report.succeeded > 0

        # Verify all expected agents available
        expected_agents = ["architect", "builder", "reviewer", "tester"]
        for agent_name in expected_agents:
            agent_path = target_dir / "amplihack" / "core" / f"{agent_name}.md"
            assert agent_path.exists(), f"Missing agent: {agent_name}"

        # Workflow would reference these agents in sequence
        # (actual execution mocked)


class TestScenario3AutoModeSession:
    """Scenario 3: Auto mode session with Copilot CLI."""

    @patch("subprocess.run")
    @patch("amplihack.launcher.copilot.check_copilot")
    def test_auto_mode_workflow(self, mock_check, mock_run, temp_project: Path):
        """Test auto mode session workflow."""
        from amplihack.launcher.copilot import launch_copilot

        mock_check.return_value = True
        mock_run.return_value = subprocess.CompletedProcess(
            args=["copilot"], returncode=0
        )

        # Launch with workflow reference
        result = launch_copilot(
            args=[
                "-p",
                "Implement feature",
                "-f",
                "@.claude/workflow/DEFAULT_WORKFLOW.md",
            ]
        )

        assert result == 0


class TestScenario4HookLifecycle:
    """Scenario 4: Hook execution lifecycle."""

    def test_session_start_hook_lifecycle(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test complete session start hook lifecycle."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create config with "always" preference
        config_file = temp_project / ".claude" / "config.json"
        config = {"copilot_auto_sync_agents": "always", "copilot_sync_on_startup": True}
        config_file.write_text(json.dumps(config))

        # Simulate session start conditions
        # 1. Check if Copilot environment
        copilot_instructions = temp_project / ".github" / "copilot-instructions.md"
        copilot_instructions.write_text("# Copilot Instructions")
        assert copilot_instructions.exists()

        # 2. Check staleness
        from amplihack.adapters.copilot_agent_converter import is_agents_synced

        is_stale = not is_agents_synced(source_dir, target_dir)

        # 3. If stale, sync
        if is_stale:
            from amplihack.adapters.copilot_agent_converter import convert_agents

            report = convert_agents(source_dir, target_dir)
            assert report.succeeded > 0

        # 4. Verify post-sync state
        assert is_agents_synced(source_dir, target_dir) is True


class TestScenario5MCPServerUsage:
    """Scenario 5: MCP server integration."""

    def test_mcp_server_configuration(self, temp_project: Path):
        """Test MCP server configuration for Copilot CLI."""
        mcp_config_path = temp_project / ".github" / "mcp-servers.json"

        # Create sample MCP configuration
        mcp_config = {
            "mcpServers": {
                "github": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"},
                }
            }
        }

        mcp_config_path.write_text(json.dumps(mcp_config, indent=2))

        # Verify configuration
        assert mcp_config_path.exists()
        loaded = json.loads(mcp_config_path.read_text())
        assert "mcpServers" in loaded
        assert "github" in loaded["mcpServers"]


class TestScenario6CompleteSetupFlow:
    """Scenario 6: Complete setup flow from scratch."""

    def test_fresh_project_setup(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test complete setup flow for new project."""
        from amplihack.adapters.copilot_agent_converter import convert_agents

        # Step 1: Create agent files
        source_dir = temp_project / ".claude" / "agents" / "amplihack" / "core"
        source_dir.mkdir(parents=True)

        for agent_name in ["architect", "builder", "reviewer"]:
            agent_file = source_dir / f"{agent_name}.md"
            content = sample_agent_markdown.replace("architect", agent_name)
            agent_file.write_text(content)

        # Step 2: Create configuration
        config_file = temp_project / ".claude" / "config.json"
        config = {"copilot_auto_sync_agents": "always"}
        config_file.write_text(json.dumps(config))

        # Step 3: Create Copilot instructions
        copilot_instructions = temp_project / ".github" / "copilot-instructions.md"
        copilot_instructions.parent.mkdir(parents=True, exist_ok=True)
        copilot_instructions.write_text(
            """# Copilot Instructions

Use agents in .github/agents/ directory.
"""
        )

        # Step 4: Run initial sync
        target_dir = temp_project / ".github" / "agents"
        report = convert_agents(temp_project / ".claude" / "agents", target_dir)

        # Step 5: Verify setup complete
        assert report.succeeded == 3
        assert (target_dir / "REGISTRY.json").exists()
        assert copilot_instructions.exists()
        assert config_file.exists()

        # Step 6: Verify agents accessible
        for agent_name in ["architect", "builder", "reviewer"]:
            agent_path = target_dir / "amplihack" / "core" / f"{agent_name}.md"
            assert agent_path.exists()


class TestScenario7UpdateAndResync:
    """Scenario 7: Agent update and resync workflow."""

    def test_agent_update_workflow(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test complete workflow for updating and resyncing agents."""
        from amplihack.adapters.copilot_agent_converter import (
            convert_agents,
            is_agents_synced,
        )

        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Initial sync
        report1 = convert_agents(source_dir, target_dir)
        assert report1.succeeded > 0

        # Agents synced
        assert is_agents_synced(source_dir, target_dir) is True

        # Update agent
        import time

        time.sleep(0.1)
        architect = source_dir / "amplihack" / "core" / "architect.md"
        original_content = architect.read_text()
        architect.write_text(original_content.replace("architect", "ARCHITECT"))

        # Should be stale now
        assert is_agents_synced(source_dir, target_dir) is False

        # Resync
        report2 = convert_agents(source_dir, target_dir, force=True)
        assert report2.succeeded > 0

        # Verify update propagated
        target_architect = target_dir / "amplihack" / "core" / "architect.md"
        assert "ARCHITECT" in target_architect.read_text()

        # Should be synced again
        assert is_agents_synced(source_dir, target_dir) is True


class TestScenario8ErrorRecovery:
    """Scenario 8: Error recovery and retry."""

    def test_error_recovery_workflow(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test recovery from common errors."""
        from amplihack.adapters.copilot_agent_converter import convert_agents

        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create invalid agent
        invalid_agent = source_dir / "invalid.md"
        invalid_agent.write_text("invalid")

        # First attempt fails
        report1 = convert_agents(source_dir, target_dir)
        assert report1.failed > 0

        # Fix agent
        invalid_agent.write_text(sample_agent_markdown.replace("architect", "fixed"))

        # Retry succeeds
        report2 = convert_agents(source_dir, target_dir)
        assert report2.failed == 0
        assert (target_dir / "fixed.md").exists()


class TestScenario9PerformanceValidation:
    """Scenario 9: Performance validation for production use."""

    def test_production_scale_performance(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test performance at production scale (50+ agents)."""
        import time

        from amplihack.adapters.copilot_agent_converter import convert_agents

        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create 50 agents
        for i in range(50):
            agent_path = source_dir / f"agent{i}.md"
            content = sample_agent_markdown.replace("architect", f"agent{i}")
            agent_path.write_text(content)

        # Measure sync time
        start = time.time()
        report = convert_agents(source_dir, target_dir)
        elapsed = time.time() - start

        # Requirements: < 2s for full sync
        assert elapsed < 2.0
        assert report.succeeded == 50

        # Verify all agents synced
        for i in range(50):
            assert (target_dir / f"agent{i}.md").exists()


class TestScenario10BackwardCompatibility:
    """Scenario 10: Backward compatibility with Claude Code."""

    def test_claude_code_still_works(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test that Copilot integration doesn't break Claude Code."""
        from amplihack.adapters.copilot_agent_converter import convert_agents

        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Sync agents
        convert_agents(source_dir, target_dir)

        # Verify source agents still intact
        for agent_file in mock_agent_files:
            assert agent_file.exists()
            # Content should be unchanged
            content = agent_file.read_text()
            assert "---" in content  # Frontmatter preserved

        # Claude Code would still read from .claude/agents/
        # Copilot CLI would read from .github/agents/
        # Both should work independently
