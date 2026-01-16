"""Pytest fixtures for Copilot CLI integration tests."""

import json
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_project() -> Generator[Path, None, None]:
    """Create temporary project directory with basic structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Create .claude structure
        claude_dir = project_root / ".claude"
        (claude_dir / "agents" / "amplihack" / "core").mkdir(parents=True)
        (claude_dir / "agents" / "amplihack" / "specialized").mkdir(parents=True)
        (claude_dir / "context").mkdir(parents=True)
        (claude_dir / "workflow").mkdir(parents=True)
        (claude_dir / "tools" / "amplihack" / "hooks").mkdir(parents=True)
        (claude_dir / "runtime" / "logs").mkdir(parents=True)

        # Create .github structure
        github_dir = project_root / ".github"
        (github_dir / "agents").mkdir(parents=True)
        (github_dir / "hooks").mkdir(parents=True)

        yield project_root


@pytest.fixture
def sample_agent_markdown() -> str:
    """Sample agent markdown with frontmatter."""
    return """---
name: architect
version: 1.0.0
description: System design and problem decomposition specialist
category: core
tags:
  - design
  - architecture
  - planning
invocable_by:
  - cli
  - workflow
  - agent
triggers:
  - architect
  - design
  - architecture
---

# Architect Agent

You are the Architect agent, specializing in system design and problem decomposition.

## Role

Your role is to:
- Analyze requirements and break down problems
- Design system architecture
- Create module specifications
- Ensure philosophy compliance

## Process

1. Understand the requirements
2. Break down into modules
3. Design interfaces
4. Document architecture
"""


@pytest.fixture
def sample_copilot_env(temp_project: Path) -> dict[str, str]:
    """Environment variables for Copilot CLI environment."""
    return {
        "GITHUB_COPILOT_CLI": "1",
        "COPILOT_SESSION": "test-session-123",
        "PROJECT_ROOT": str(temp_project),
    }


@pytest.fixture
def mock_config_file(temp_project: Path) -> Path:
    """Create mock config file."""
    config_path = temp_project / ".claude" / "config.json"
    config = {
        "copilot_auto_sync_agents": "ask",
        "copilot_sync_on_startup": True,
    }
    config_path.write_text(json.dumps(config, indent=2))
    return config_path


@pytest.fixture
def mock_agent_files(temp_project: Path, sample_agent_markdown: str) -> list[Path]:
    """Create mock agent files in .claude/agents/."""
    agents_dir = temp_project / ".claude" / "agents" / "amplihack"

    agent_files = []

    # Core agents
    for agent_name in ["architect", "builder", "reviewer", "tester"]:
        agent_file = agents_dir / "core" / f"{agent_name}.md"
        content = sample_agent_markdown.replace("architect", agent_name)
        agent_file.write_text(content)
        agent_files.append(agent_file)

    # Specialized agents
    for agent_name in ["fix-agent", "ci-diagnostic"]:
        agent_file = agents_dir / "specialized" / f"{agent_name}.md"
        content = sample_agent_markdown.replace("architect", agent_name)
        agent_file.write_text(content)
        agent_files.append(agent_file)

    return agent_files


@pytest.fixture
def mock_registry_json(temp_project: Path) -> Path:
    """Create mock REGISTRY.json."""
    registry_path = temp_project / ".github" / "agents" / "REGISTRY.json"
    registry = {
        "version": "1.0",
        "generated": "auto",
        "agents": {
            "amplihack/core/architect": {
                "path": "amplihack/core/architect.md",
                "name": "Architect",
                "description": "System design specialist",
                "tags": ["design", "architecture"],
            }
        },
    }
    registry_path.write_text(json.dumps(registry, indent=2))
    return registry_path
