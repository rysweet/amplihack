"""Tests for Copilot CLI agent integration.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)

Philosophy:
- Test the contract, not implementation
- Zero-BS - all tests actually test functionality
- Fast execution with strategic mocking
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from amplihack.copilot.agent_wrapper import (
    AgentInfo,
    AgentInvocationResult,
    invoke_copilot_agent,
    discover_agents,
    list_agents,
    check_copilot,
)
from amplihack.copilot.errors import InvocationError, InstallationError


# ============================================================================
# UNIT TESTS (60%) - Fast, heavily mocked
# ============================================================================


class TestCheckCopilot:
    """Unit tests for Copilot CLI detection."""

    def test_copilot_installed(self):
        """Test detection when copilot is installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            assert check_copilot() is True
            mock_run.assert_called_once()

    def test_copilot_not_installed(self):
        """Test detection when copilot is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert check_copilot() is False

    def test_copilot_timeout(self):
        """Test detection when copilot command times out."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("copilot", 5)):
            assert check_copilot() is False


class TestDiscoverAgents:
    """Unit tests for agent discovery."""

    @pytest.fixture
    def mock_registry(self, tmp_path):
        """Create mock REGISTRY.json file."""
        registry = {
            "version": "1.0",
            "agents": {
                "architect": {
                    "path": "amplihack/core/architect.md",
                    "name": "architect",
                    "description": "General architecture agent",
                    "tags": ["design", "architecture"],
                    "invocable_by": [],
                },
                "builder": {
                    "path": "amplihack/core/builder.md",
                    "name": "builder",
                    "description": "Primary implementation agent",
                    "tags": ["implementation"],
                    "invocable_by": [],
                },
                "README": {
                    "path": "README.md",
                    "name": "Readme",
                    "description": "",
                    "tags": [],
                    "invocable_by": [],
                },
            },
        }

        registry_path = tmp_path / "REGISTRY.json"
        registry_path.write_text(json.dumps(registry))
        return registry_path

    def test_discover_agents_success(self, mock_registry):
        """Test successful agent discovery."""
        agents = discover_agents(mock_registry)

        assert "architect" in agents
        assert "builder" in agents
        assert "README" not in agents  # Should filter out non-invocable

        architect = agents["architect"]
        assert architect.name == "architect"
        assert architect.path == "amplihack/core/architect.md"
        assert "design" in architect.tags

    def test_discover_agents_registry_not_found(self):
        """Test error when REGISTRY.json doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Agent registry not found"):
            discover_agents(Path("/nonexistent/REGISTRY.json"))

    def test_discover_agents_invalid_json(self, tmp_path):
        """Test error when REGISTRY.json is invalid."""
        invalid_registry = tmp_path / "REGISTRY.json"
        invalid_registry.write_text("{ invalid json }")

        with pytest.raises(ValueError, match="Invalid REGISTRY.json"):
            discover_agents(invalid_registry)

    def test_discover_agents_empty(self, tmp_path):
        """Test handling of empty registry."""
        empty_registry = tmp_path / "REGISTRY.json"
        empty_registry.write_text(json.dumps({"version": "1.0", "agents": {}}))

        agents = discover_agents(empty_registry)
        assert len(agents) == 0


class TestListAgents:
    """Unit tests for agent listing."""

    def test_list_agents_sorted(self, tmp_path):
        """Test agents are returned sorted by name."""
        registry = {
            "version": "1.0",
            "agents": {
                "zebra": {
                    "path": "zebra.md",
                    "name": "zebra",
                    "description": "Zebra agent",
                    "tags": [],
                    "invocable_by": [],
                },
                "alpha": {
                    "path": "alpha.md",
                    "name": "alpha",
                    "description": "Alpha agent",
                    "tags": [],
                    "invocable_by": [],
                },
            },
        }

        registry_path = tmp_path / "REGISTRY.json"
        registry_path.write_text(json.dumps(registry))

        agents = list_agents(registry_path)
        assert len(agents) == 2
        assert agents[0].name == "alpha"
        assert agents[1].name == "zebra"


class TestInvokeCopilotAgent:
    """Unit tests for agent invocation."""

    @pytest.fixture
    def mock_environment(self, tmp_path):
        """Set up mock environment with registry and agent files."""
        # Create REGISTRY.json
        registry = {
            "version": "1.0",
            "agents": {
                "architect": {
                    "path": "amplihack/core/architect.md",
                    "name": "architect",
                    "description": "Architecture agent",
                    "tags": [],
                    "invocable_by": [],
                },
            },
        }

        registry_path = tmp_path / "REGISTRY.json"
        registry_path.write_text(json.dumps(registry))

        # Create agent file
        agent_dir = tmp_path / "amplihack" / "core"
        agent_dir.mkdir(parents=True)
        agent_file = agent_dir / "architect.md"
        agent_file.write_text("# Architect Agent\n\nTest agent content")

        return registry_path, agent_file

    def test_invoke_agent_success(self, mock_environment):
        """Test successful agent invocation."""
        registry_path, agent_file = mock_environment

        with patch("subprocess.run") as mock_run, \
             patch("amplihack.copilot.agent_wrapper.check_copilot", return_value=True), \
             patch("pathlib.Path.exists", return_value=True):

            mock_run.return_value = Mock(
                returncode=0,
                stdout="Agent output",
                stderr="",
            )

            result = invoke_copilot_agent(
                "architect",
                "Design authentication system",
                registry_path=registry_path,
            )

            assert result.success is True
            assert result.agent_name == "architect"
            assert result.output == "Agent output"
            assert result.exit_code == 0

            # Verify command structure
            call_args = mock_run.call_args[0][0]
            assert "copilot" in call_args
            assert "--allow-all-tools" in call_args
            assert "-p" in call_args
            assert "Design authentication system" in call_args

    def test_invoke_agent_copilot_not_installed(self, mock_environment):
        """Test error when Copilot CLI not installed."""
        registry_path, _ = mock_environment

        with patch("amplihack.copilot.agent_wrapper.check_copilot", return_value=False):
            with pytest.raises(InstallationError, match="Copilot CLI not installed"):
                invoke_copilot_agent(
                    "architect",
                    "Design system",
                    registry_path=registry_path,
                )

    def test_invoke_agent_not_found(self, mock_environment):
        """Test error when agent doesn't exist."""
        registry_path, _ = mock_environment

        with patch("amplihack.copilot.agent_wrapper.check_copilot", return_value=True):
            with pytest.raises(InvocationError, match="Agent 'nonexistent' not found"):
                invoke_copilot_agent(
                    "nonexistent",
                    "Do something",
                    registry_path=registry_path,
                )

    def test_invoke_agent_file_not_found(self, mock_environment):
        """Test error when agent file doesn't exist."""
        registry_path, _ = mock_environment

        with patch("amplihack.copilot.agent_wrapper.check_copilot", return_value=True), \
             patch("pathlib.Path.exists", return_value=False):

            with pytest.raises(InvocationError, match="Agent file not found"):
                invoke_copilot_agent(
                    "architect",
                    "Design system",
                    registry_path=registry_path,
                )

    def test_invoke_agent_with_additional_files(self, mock_environment):
        """Test invocation with additional file references."""
        registry_path, _ = mock_environment

        with patch("subprocess.run") as mock_run, \
             patch("amplihack.copilot.agent_wrapper.check_copilot", return_value=True), \
             patch("pathlib.Path.exists", return_value=True):

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            invoke_copilot_agent(
                "architect",
                "Design system",
                registry_path=registry_path,
                additional_files=["PHILOSOPHY.md", "PATTERNS.md"],
            )

            call_args = mock_run.call_args[0][0]
            assert "@PHILOSOPHY.md" in " ".join(call_args)
            assert "@PATTERNS.md" in " ".join(call_args)

    def test_invoke_agent_verbose_mode(self, mock_environment, capsys):
        """Test verbose mode prints command."""
        registry_path, _ = mock_environment

        with patch("subprocess.run") as mock_run, \
             patch("amplihack.copilot.agent_wrapper.check_copilot", return_value=True), \
             patch("pathlib.Path.exists", return_value=True):

            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            invoke_copilot_agent(
                "architect",
                "Design system",
                registry_path=registry_path,
                verbose=True,
            )

            captured = capsys.readouterr()
            assert "Executing:" in captured.out
            assert "copilot" in captured.out


# ============================================================================
# INTEGRATION TESTS (30%) - Multiple components
# ============================================================================


class TestAgentDiscoveryIntegration:
    """Integration tests for agent discovery + validation."""

    def test_full_discovery_workflow(self, tmp_path):
        """Test complete discovery workflow."""
        # Create comprehensive registry
        registry = {
            "version": "1.0",
            "agents": {
                "architect": {
                    "path": "core/architect.md",
                    "name": "architect",
                    "description": "Architecture agent",
                    "tags": ["design"],
                    "invocable_by": [],
                },
                "builder": {
                    "path": "core/builder.md",
                    "name": "builder",
                    "description": "Implementation agent",
                    "tags": ["implementation"],
                    "invocable_by": [],
                },
                "tester": {
                    "path": "core/tester.md",
                    "name": "tester",
                    "description": "Testing agent",
                    "tags": ["testing", "qa"],
                    "invocable_by": [],
                },
            },
        }

        registry_path = tmp_path / "REGISTRY.json"
        registry_path.write_text(json.dumps(registry))

        # Discover agents
        agents_dict = discover_agents(registry_path)
        assert len(agents_dict) == 3

        # List agents (sorted)
        agents_list = list_agents(registry_path)
        assert len(agents_list) == 3
        assert [a.name for a in agents_list] == ["architect", "builder", "tester"]

        # Verify agent info is complete
        for agent in agents_list:
            assert agent.name
            assert agent.path
            assert isinstance(agent.tags, list)


class TestAgentInvocationIntegration:
    """Integration tests for agent invocation with discovery."""

    def test_discover_and_invoke_workflow(self, tmp_path):
        """Test discovering agents then invoking one."""
        # Set up environment
        registry = {
            "version": "1.0",
            "agents": {
                "architect": {
                    "path": "core/architect.md",
                    "name": "architect",
                    "description": "Architecture agent",
                    "tags": [],
                    "invocable_by": [],
                },
            },
        }

        registry_path = tmp_path / "REGISTRY.json"
        registry_path.write_text(json.dumps(registry))

        # Discover agents first
        agents = discover_agents(registry_path)
        assert "architect" in agents

        # Then invoke discovered agent
        with patch("subprocess.run") as mock_run, \
             patch("amplihack.copilot.agent_wrapper.check_copilot", return_value=True), \
             patch("pathlib.Path.exists", return_value=True):

            mock_run.return_value = Mock(
                returncode=0,
                stdout="Design completed",
                stderr="",
            )

            result = invoke_copilot_agent(
                "architect",
                "Design API",
                registry_path=registry_path,
            )

            assert result.success is True
            assert result.agent_name == "architect"


# ============================================================================
# E2E TESTS (10%) - Complete workflows
# ============================================================================


class TestEndToEnd:
    """End-to-end tests for complete workflows."""

    def test_complete_agent_workflow_with_files(self, tmp_path):
        """Test complete workflow: discover, validate, invoke with files."""
        # Set up comprehensive environment
        registry = {
            "version": "1.0",
            "agents": {
                "architect": {
                    "path": "core/architect.md",
                    "name": "architect",
                    "description": "Architecture agent",
                    "tags": ["design"],
                    "invocable_by": [],
                },
            },
        }

        registry_path = tmp_path / "REGISTRY.json"
        registry_path.write_text(json.dumps(registry))

        # Create agent file
        agent_dir = tmp_path / "core"
        agent_dir.mkdir(parents=True)
        agent_file = agent_dir / "architect.md"
        agent_file.write_text("# Architect Agent")

        # Create additional context files
        philosophy = tmp_path / "PHILOSOPHY.md"
        philosophy.write_text("# Philosophy\nRuthless simplicity")

        # Step 1: Discover all agents
        agents = discover_agents(registry_path)
        assert len(agents) == 1

        # Step 2: List agents (sorted)
        agents_list = list_agents(registry_path)
        assert agents_list[0].name == "architect"

        # Step 3: Invoke with additional files
        with patch("subprocess.run") as mock_run, \
             patch("amplihack.copilot.agent_wrapper.check_copilot", return_value=True), \
             patch("pathlib.Path.exists", return_value=True):

            mock_run.return_value = Mock(
                returncode=0,
                stdout="Architecture designed",
                stderr="",
            )

            result = invoke_copilot_agent(
                "architect",
                "Design authentication system",
                registry_path=registry_path,
                additional_files=["PHILOSOPHY.md"],
            )

            # Verify command includes all pieces
            call_args = mock_run.call_args[0][0]
            assert "copilot" in call_args
            assert "--allow-all-tools" in call_args
            assert any("architect.md" in str(arg) for arg in call_args)
            assert any("PHILOSOPHY.md" in str(arg) for arg in call_args)
            assert "Design authentication system" in call_args

            # Verify result
            assert result.success is True
            assert "Architecture designed" in result.output

    def test_error_handling_workflow(self, tmp_path):
        """Test error handling across complete workflow."""
        registry_path = tmp_path / "REGISTRY.json"

        # Step 1: Missing registry
        with pytest.raises(FileNotFoundError):
            discover_agents(registry_path)

        # Create invalid registry
        registry_path.write_text("{ invalid }")

        # Step 2: Invalid JSON
        with pytest.raises(ValueError):
            discover_agents(registry_path)

        # Create valid registry
        registry = {
            "version": "1.0",
            "agents": {
                "architect": {
                    "path": "core/architect.md",
                    "name": "architect",
                    "description": "Test",
                    "tags": [],
                    "invocable_by": [],
                },
            },
        }
        registry_path.write_text(json.dumps(registry))

        # Step 3: Copilot not installed
        with patch("amplihack.copilot.agent_wrapper.check_copilot", return_value=False):
            with pytest.raises(InstallationError):
                invoke_copilot_agent("architect", "Task", registry_path=registry_path)

        # Step 4: Agent not found
        with patch("amplihack.copilot.agent_wrapper.check_copilot", return_value=True):
            with pytest.raises(InvocationError, match="not found"):
                invoke_copilot_agent("nonexistent", "Task", registry_path=registry_path)
