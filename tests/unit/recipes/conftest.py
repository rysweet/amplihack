"""Fixtures for Recipe Runner unit tests.

Provides recipe YAML strings, mock adapters, and paths to real recipe files
for testing the parser, context, runner, and agent resolver modules.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def simple_recipe_yaml() -> str:
    """Minimal 2-step recipe: one bash step and one agent step."""
    return """\
name: "simple-test-recipe"
description: "A minimal recipe for testing"
version: "1.0.0"

context:
  greeting: "hello"

steps:
  - id: "step-01-echo"
    type: "bash"
    command: "echo '{{greeting}}'"
    output: "echo_result"

  - id: "step-02-agent"
    agent: "amplihack:builder"
    prompt: |
      Process the echo result: {{echo_result}}
    output: "agent_result"
"""


@pytest.fixture
def conditional_recipe_yaml() -> str:
    """Recipe with a conditional step that should be skipped when condition is false."""
    return """\
name: "conditional-recipe"
description: "Recipe with conditional step"
version: "1.0.0"

context:
  run_optional: "no"

steps:
  - id: "step-01-always"
    type: "bash"
    command: "echo 'always runs'"
    output: "first_result"

  - id: "step-02-conditional"
    type: "bash"
    command: "echo 'conditional step'"
    condition: "run_optional == \\"yes\\""
    output: "conditional_result"

  - id: "step-03-final"
    type: "bash"
    command: "echo 'final step'"
    output: "final_result"
"""


@pytest.fixture
def context_accumulation_yaml() -> str:
    """Recipe where step 2 uses the output of step 1 via template variables."""
    return """\
name: "context-accumulation"
description: "Step 2 uses output of step 1"
version: "1.0.0"

context:
  base_name: "world"

steps:
  - id: "step-01-greet"
    type: "bash"
    command: "echo 'Hello {{base_name}}'"
    output: "greeting"

  - id: "step-02-use-greeting"
    agent: "amplihack:builder"
    prompt: |
      The greeting was: {{greeting}}
      Please elaborate on it.
    output: "elaboration"
"""


@pytest.fixture
def mock_adapter() -> MagicMock:
    """A mock SDKAdapter that records calls and returns configurable responses.

    The mock records all calls to execute_bash_step and execute_agent_step.
    By default, both return a successful result string. Override return values
    by setting mock_adapter.execute_bash_step.return_value or
    mock_adapter.execute_agent_step.return_value.
    """
    adapter = MagicMock()
    adapter.execute_bash_step.return_value = "bash step completed successfully"
    adapter.execute_agent_step.return_value = "agent step completed successfully"
    return adapter


@pytest.fixture
def sample_recipe_path() -> Path:
    """Path to the actual verification-workflow.yaml in amplifier-bundle/recipes/.

    This resolves relative to the project root so it works from any test
    working directory.
    """
    # Navigate from this test file up to the project root
    project_root = Path(__file__).resolve().parents[3]
    recipe_path = project_root / "amplifier-bundle" / "recipes" / "verification-workflow.yaml"
    if not recipe_path.exists():
        # Fallback: try src-embedded copy
        recipe_path = (
            project_root
            / "src"
            / "amplihack"
            / "amplifier-bundle"
            / "recipes"
            / "verification-workflow.yaml"
        )
    return recipe_path
