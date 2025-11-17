"""Tests for AgentConfig module."""

import sys
from pathlib import Path

# Add .claude to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude"))

import pytest
from tools.benchmarking.agent_config import AgentConfig, TaskConfig


def test_load_valid_agent(tmp_path):
    """Should parse agent directory with all required files."""
    # Setup: Create temp directory with required files
    agent_dir = tmp_path / "test_agent"
    agent_dir.mkdir()

    (agent_dir / "agent.yaml").write_text("""
required_env_vars:
  - ANTHROPIC_API_KEY
optional_env_vars:
  - DEBUG_MODE
description: "Test agent"
""")

    (agent_dir / "install.dockerfile").write_text("RUN npm install -g test-cli\n")
    (agent_dir / "command_template.txt").write_text("test-cli '{{task_instructions}}'")

    # Test
    config = AgentConfig.from_directory(agent_dir)

    # Assert
    assert config.name == "test_agent"
    assert config.required_env_vars == ["ANTHROPIC_API_KEY"]
    assert config.optional_env_vars == ["DEBUG_MODE"]
    assert "npm install" in config.install_dockerfile
    assert "{{task_instructions}}" in config.command_template


def test_missing_agent_yaml(tmp_path):
    """Should raise FileNotFoundError when agent.yaml missing."""
    agent_dir = tmp_path / "incomplete_agent"
    agent_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="agent.yaml"):
        AgentConfig.from_directory(agent_dir)


def test_missing_install_dockerfile(tmp_path):
    """Should raise FileNotFoundError when install.dockerfile missing."""
    agent_dir = tmp_path / "incomplete_agent"
    agent_dir.mkdir()
    (agent_dir / "agent.yaml").write_text("required_env_vars: []")

    with pytest.raises(FileNotFoundError, match="install.dockerfile"):
        AgentConfig.from_directory(agent_dir)


def test_validate_empty_required_vars():
    """Should allow empty required_env_vars (some agents don't need secrets)."""
    config = AgentConfig(
        name="test",
        agent_dir=Path("."),
        required_env_vars=[],  # Empty is valid
        optional_env_vars=[],
        install_dockerfile="RUN echo test",
        command_template="test '{{task_instructions}}'",
        command_template_continue=None,
        local_source_path=None,
        description="Test"
    )

    assert config.validate() is True


def test_validate_missing_placeholder():
    """Should reject command_template without {{task_instructions}}."""
    config = AgentConfig(
        name="test",
        agent_dir=Path("."),
        required_env_vars=["KEY"],
        optional_env_vars=[],
        install_dockerfile="RUN echo test",
        command_template="test-cli --run",  # Missing placeholder
        command_template_continue=None,
        local_source_path=None,
        description="Test"
    )

    with pytest.raises(ValueError, match="task_instructions.*placeholder"):
        config.validate()


def test_render_command():
    """Should substitute {{task_instructions}} in template."""
    config = AgentConfig(
        name="test",
        agent_dir=Path("."),
        required_env_vars=[],
        optional_env_vars=[],
        install_dockerfile="",
        command_template="cli --task '{{task_instructions}}'",
        command_template_continue=None,
        local_source_path=None,
        description=""
    )

    rendered = config.render_command("Write a function to add two numbers")

    assert "Write a function to add two numbers" in rendered
    assert "{{task_instructions}}" not in rendered


def test_render_command_escapes_shell():
    """Should escape shell metacharacters in task instructions."""
    config = AgentConfig(
        name="test",
        agent_dir=Path("."),
        required_env_vars=[],
        optional_env_vars=[],
        install_dockerfile="",
        command_template="cli '{{task_instructions}}'",
        command_template_continue=None,
        local_source_path=None,
        description=""
    )

    malicious_input = "task'; rm -rf /; echo 'pwned"
    rendered = config.render_command(malicious_input)

    # Should escape the single quotes
    assert "rm -rf" in rendered  # Content is there
    assert rendered.count("'") >= 4  # But properly quoted/escaped


def test_get_all_required_vars_merge():
    """Should merge and deduplicate agent + task required vars."""
    config = AgentConfig(
        name="test",
        agent_dir=Path("."),
        required_env_vars=["ANTHROPIC_API_KEY", "SHARED_VAR"],
        optional_env_vars=[],
        install_dockerfile="",
        command_template="test '{{task_instructions}}'",
        command_template_continue=None,
        local_source_path=None,
        description=""
    )

    task_vars = ["OPENAI_API_KEY", "SHARED_VAR"]
    all_vars = config.get_all_required_vars(task_vars)

    assert set(all_vars) == {"ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SHARED_VAR"}
    assert len(all_vars) == 3  # Deduplicated


def test_local_source_path_validation(tmp_path):
    """Should validate local_source_path exists if specified."""
    config = AgentConfig(
        name="test",
        agent_dir=Path("."),
        required_env_vars=[],
        optional_env_vars=[],
        install_dockerfile="RUN echo test",  # Valid dockerfile
        command_template="test '{{task_instructions}}'",
        command_template_continue=None,
        local_source_path=Path("/nonexistent/path"),
        description=""
    )

    with pytest.raises(ValueError, match="local_source_path.*not exist"):
        config.validate()


def test_load_task_config(tmp_path):
    """Should load task.yaml and instructions.txt correctly."""
    task_dir = tmp_path / "test_task"
    task_dir.mkdir()

    (task_dir / "task.yaml").write_text("""
name: test_task
required_env_vars:
  - ANTHROPIC_API_KEY
timeout_seconds: 300
test_command: "uv run test.py"
task_info:
  difficulty: medium
  is_non_deterministic: true
description: "Test task"
""")

    (task_dir / "instructions.txt").write_text("Write a hello world program")

    config = TaskConfig.from_directory(task_dir)

    assert config.name == "test_task"
    assert config.timeout_seconds == 300
    assert config.difficulty == "medium"
    assert config.is_non_deterministic is True
    assert "hello world" in config.instructions
