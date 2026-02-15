"""Test fixtures for CLI recipe command tests.

Provides reusable fixtures for:
- Sample recipes with various configurations
- Mock adapters and contexts
- Mock file systems for recipe discovery
- Common test data and helpers
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from amplihack.recipes.models import Recipe, RecipeResult, Step, StepResult, StepStatus, StepType


@pytest.fixture
def simple_recipe() -> Recipe:
    """A basic recipe with two bash steps."""
    return Recipe(
        name="simple-test",
        description="A simple test recipe",
        version="1.0.0",
        author="test-author",
        tags=["test", "simple"],
        steps=[
            Step(
                id="step1",
                step_type=StepType.BASH,
                command="echo 'hello'",
            ),
            Step(
                id="step2",
                step_type=StepType.BASH,
                command="echo 'world'",
            ),
        ],
        context={"env": "test"},
    )


@pytest.fixture
def agent_recipe() -> Recipe:
    """A recipe with agent steps."""
    return Recipe(
        name="agent-test",
        description="Recipe with agent steps",
        version="1.0.0",
        steps=[
            Step(
                id="analyze",
                step_type=StepType.AGENT,
                agent="analyzer",
                prompt="Analyze the codebase",
                output="analysis_result",
            ),
            Step(
                id="implement",
                step_type=StepType.AGENT,
                agent="builder",
                prompt="Implement feature based on {analysis_result}",
            ),
        ],
    )


@pytest.fixture
def conditional_recipe() -> Recipe:
    """A recipe with conditional steps."""
    return Recipe(
        name="conditional-test",
        description="Recipe with conditions",
        steps=[
            Step(
                id="check",
                step_type=StepType.BASH,
                command="test -f config.json",
                output="has_config",
            ),
            Step(
                id="process",
                step_type=StepType.BASH,
                command="echo 'processing'",
                condition="has_config",
            ),
        ],
        context={"has_config": False},
    )


@pytest.fixture
def complex_recipe() -> Recipe:
    """A complex recipe with mixed step types, conditions, and context."""
    return Recipe(
        name="complex-workflow",
        description="Complex multi-step workflow",
        version="2.0.0",
        author="test-team",
        tags=["complex", "workflow", "integration"],
        steps=[
            Step(
                id="setup",
                step_type=StepType.BASH,
                command="mkdir -p {output_dir}",
                output="setup_result",
            ),
            Step(
                id="analyze",
                step_type=StepType.AGENT,
                agent="analyzer",
                prompt="Analyze project in {project_path}",
                output="analysis",
                parse_json=True,
                condition="setup_result",
            ),
            Step(
                id="validate",
                step_type=StepType.BASH,
                command="python validate.py --input {analysis.file}",
                condition="analysis",
                timeout=300,
            ),
            Step(
                id="report",
                step_type=StepType.AGENT,
                agent="reporter",
                prompt="Generate report from {analysis}",
                mode="auto",
            ),
        ],
        context={
            "output_dir": "/tmp/output",
            "project_path": "/workspace/project",
        },
    )


@pytest.fixture
def successful_result() -> RecipeResult:
    """A successful recipe execution result."""
    return RecipeResult(
        recipe_name="test-recipe",
        success=True,
        step_results=[
            StepResult(
                step_id="step1",
                status=StepStatus.COMPLETED,
                output="success",
            ),
            StepResult(
                step_id="step2",
                status=StepStatus.COMPLETED,
                output="done",
            ),
        ],
        context={"result": "success"},
    )


@pytest.fixture
def failed_result() -> RecipeResult:
    """A failed recipe execution result."""
    return RecipeResult(
        recipe_name="test-recipe",
        success=False,
        step_results=[
            StepResult(
                step_id="step1",
                status=StepStatus.COMPLETED,
                output="ok",
            ),
            StepResult(
                step_id="step2",
                status=StepStatus.FAILED,
                error="Command failed with exit code 1",
            ),
        ],
        context={"error": "failed"},
    )


@pytest.fixture
def skipped_result() -> RecipeResult:
    """A recipe result with skipped steps."""
    return RecipeResult(
        recipe_name="test-recipe",
        success=True,
        step_results=[
            StepResult(
                step_id="step1",
                status=StepStatus.COMPLETED,
                output="ok",
            ),
            StepResult(
                step_id="step2",
                status=StepStatus.SKIPPED,
            ),
            StepResult(
                step_id="step3",
                status=StepStatus.COMPLETED,
                output="done",
            ),
        ],
        context={},
    )


@pytest.fixture
def mock_recipe_runner() -> MagicMock:
    """Mock RecipeRunner for testing command handlers."""
    runner = MagicMock()
    runner.execute = MagicMock()
    return runner


@pytest.fixture
def mock_recipe_discovery() -> MagicMock:
    """Mock RecipeDiscovery for testing list command."""
    discovery = MagicMock()
    discovery.discover_all = MagicMock()
    return discovery


@pytest.fixture
def mock_recipe_parser() -> MagicMock:
    """Mock RecipeParser for testing validation."""
    parser = MagicMock()
    parser.parse_file = MagicMock()
    return parser


@pytest.fixture
def recipe_dir(tmp_path: Path) -> Path:
    """Temporary directory with sample recipe files."""
    recipe_path = tmp_path / "recipes"
    recipe_path.mkdir()

    # Create sample recipe files
    (recipe_path / "simple.yaml").write_text("""
name: simple-test
description: Simple test recipe
steps:
  - id: hello
    type: bash
    command: echo 'hello'
""")

    (recipe_path / "agent.yaml").write_text("""
name: agent-test
description: Agent test recipe
steps:
  - id: analyze
    type: agent
    agent: analyzer
    prompt: Analyze the code
""")

    (recipe_path / "invalid.yaml").write_text("""
name: invalid-test
# Missing required 'steps' field
description: Invalid recipe
""")

    return recipe_path


@pytest.fixture
def sample_recipes() -> list[Recipe]:
    """List of sample recipes for testing list command."""
    return [
        Recipe(
            name="recipe-1",
            description="First recipe",
            tags=["tag1", "tag2"],
        ),
        Recipe(
            name="recipe-2",
            description="Second recipe",
            tags=["tag2", "tag3"],
        ),
        Recipe(
            name="recipe-3",
            description="Third recipe",
            tags=["tag1"],
        ),
    ]


@pytest.fixture
def mock_context() -> dict[str, Any]:
    """Sample context for recipe execution."""
    return {
        "project_path": "/workspace/project",
        "output_dir": "/tmp/output",
        "env": "test",
        "debug": True,
    }


@pytest.fixture
def mock_cli_args() -> dict[str, Any]:
    """Sample CLI arguments."""
    return {
        "verbose": False,
        "dry_run": False,
        "format": "table",
        "working_dir": ".",
    }
