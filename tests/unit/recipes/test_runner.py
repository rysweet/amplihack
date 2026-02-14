"""Tests for RecipeRunner.

These tests verify that RecipeRunner can:
- Execute steps sequentially through a mock adapter
- Accumulate context between steps (step 2 sees step 1 output)
- Skip steps when their condition evaluates to false
- Route bash and agent steps to the correct adapter methods
- Stop execution on first failure (fail-fast)
- Render template variables in prompts before execution
- Parse JSON output and store as dict in context
- Support dry-run mode (no actual execution)
- Produce correct RecipeResult success/failure status
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from amplihack.recipes.models import StepStatus
from amplihack.recipes.parser import RecipeParser
from amplihack.recipes.runner import RecipeRunner


class TestStepExecution:
    """Test that steps execute in sequence via the adapter."""

    def test_steps_execute_sequentially(
        self, simple_recipe_yaml: str, mock_adapter: MagicMock
    ) -> None:
        """All steps run in order: bash step first, agent step second."""
        parser = RecipeParser()
        recipe = parser.parse(simple_recipe_yaml)

        runner = RecipeRunner(adapter=mock_adapter)
        runner.execute(recipe)

        # Both adapter methods should have been called
        assert mock_adapter.execute_bash_step.call_count == 1
        assert mock_adapter.execute_agent_step.call_count == 1

        # Bash step should be called before agent step
        all_calls = mock_adapter.method_calls
        bash_call_idx = next(i for i, c in enumerate(all_calls) if c[0] == "execute_bash_step")
        agent_call_idx = next(i for i, c in enumerate(all_calls) if c[0] == "execute_agent_step")
        assert bash_call_idx < agent_call_idx

    def test_context_accumulates_between_steps(
        self, context_accumulation_yaml: str, mock_adapter: MagicMock
    ) -> None:
        """Step 2's prompt contains step 1's output from context."""
        mock_adapter.execute_bash_step.return_value = "Hello world"
        mock_adapter.execute_agent_step.return_value = "Elaborated greeting"

        parser = RecipeParser()
        recipe = parser.parse(context_accumulation_yaml)

        runner = RecipeRunner(adapter=mock_adapter)
        runner.execute(recipe)

        # The agent step prompt should contain the bash step output
        agent_call_args = mock_adapter.execute_agent_step.call_args
        # The prompt passed to the agent should contain "Hello world"
        prompt_arg = _extract_prompt_from_call(agent_call_args)
        assert "Hello world" in prompt_arg


class TestConditionalExecution:
    """Test conditional step skipping."""

    def test_condition_skips_step(
        self, conditional_recipe_yaml: str, mock_adapter: MagicMock
    ) -> None:
        """A step with a false condition gets StepStatus.SKIPPED."""
        parser = RecipeParser()
        recipe = parser.parse(conditional_recipe_yaml)

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Step 2 (conditional) should be skipped
        step_results = result.step_results
        conditional_step = next(sr for sr in step_results if sr.step_id == "step-02-conditional")
        assert conditional_step.status == StepStatus.SKIPPED

        # Steps 1 and 3 should have executed (2 bash calls, not 3)
        assert mock_adapter.execute_bash_step.call_count == 2


class TestStepRouting:
    """Test that step types route to the correct adapter method."""

    def test_bash_step_uses_execute_bash(
        self, simple_recipe_yaml: str, mock_adapter: MagicMock
    ) -> None:
        """Bash steps call adapter.execute_bash_step."""
        parser = RecipeParser()
        recipe = parser.parse(simple_recipe_yaml)

        runner = RecipeRunner(adapter=mock_adapter)
        runner.execute(recipe)

        mock_adapter.execute_bash_step.assert_called_once()

    def test_agent_step_uses_execute_agent(
        self, simple_recipe_yaml: str, mock_adapter: MagicMock
    ) -> None:
        """Agent steps call adapter.execute_agent_step."""
        parser = RecipeParser()
        recipe = parser.parse(simple_recipe_yaml)

        runner = RecipeRunner(adapter=mock_adapter)
        runner.execute(recipe)

        mock_adapter.execute_agent_step.assert_called_once()


class TestFailFast:
    """Test that execution stops after the first failed step."""

    def test_fail_fast_on_error(self, mock_adapter: MagicMock) -> None:
        """Execution stops after first failed step; subsequent steps do not run."""
        yaml_str = """\
name: "fail-fast-recipe"
description: "test"
version: "1.0.0"
steps:
  - id: "step-01"
    type: "bash"
    command: "echo first"
    output: "first_result"
  - id: "step-02"
    type: "bash"
    command: "failing command"
    output: "second_result"
  - id: "step-03"
    type: "bash"
    command: "echo third"
    output: "third_result"
"""
        # First call succeeds, second raises an error
        mock_adapter.execute_bash_step.side_effect = [
            "first ok",
            RuntimeError("command failed"),
        ]

        parser = RecipeParser()
        recipe = parser.parse(yaml_str)

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Only 2 bash calls (step 3 never executed)
        assert mock_adapter.execute_bash_step.call_count == 2
        assert result.success is False


class TestTemplateRendering:
    """Test that template variables are rendered before execution."""

    def test_template_variables_rendered_in_prompt(self, mock_adapter: MagicMock) -> None:
        """{{var}} placeholders in prompts are replaced before execution."""
        yaml_str = """\
name: "template-recipe"
description: "test"
version: "1.0.0"
context:
  target_file: "main.py"
steps:
  - id: "step-01"
    agent: "amplihack:builder"
    prompt: "Edit the file {{target_file}} to add logging"
    output: "edit_result"
"""
        parser = RecipeParser()
        recipe = parser.parse(yaml_str)

        runner = RecipeRunner(adapter=mock_adapter)
        runner.execute(recipe)

        # The prompt sent to the agent should have "main.py" not "{{target_file}}"
        agent_call_args = mock_adapter.execute_agent_step.call_args
        prompt_arg = _extract_prompt_from_call(agent_call_args)
        assert "main.py" in prompt_arg
        assert "{{target_file}}" not in prompt_arg


class TestJsonParsing:
    """Test parse_json step option."""

    def test_parse_json_stores_dict(self, mock_adapter: MagicMock) -> None:
        """When parse_json=true, the step output is parsed and stored as a dict."""
        yaml_str = """\
name: "json-parse-recipe"
description: "test"
version: "1.0.0"
steps:
  - id: "step-01"
    type: "bash"
    command: "echo json"
    output: "json_data"
    parse_json: true
  - id: "step-02"
    agent: "amplihack:builder"
    prompt: "Use {{json_data}}"
    output: "final"
"""
        mock_adapter.execute_bash_step.return_value = '{"status": "ok", "count": 3}'
        mock_adapter.execute_agent_step.return_value = "done"

        parser = RecipeParser()
        recipe = parser.parse(yaml_str)

        runner = RecipeRunner(adapter=mock_adapter)
        runner.execute(recipe)

        # The context should contain the parsed dict, not the raw string
        # We verify by checking the agent prompt contains the JSON representation
        agent_call_args = mock_adapter.execute_agent_step.call_args
        prompt_arg = _extract_prompt_from_call(agent_call_args)
        assert "status" in prompt_arg
        assert "ok" in prompt_arg


class TestDryRun:
    """Test dry-run mode."""

    def test_dry_run_does_not_execute(
        self, simple_recipe_yaml: str, mock_adapter: MagicMock
    ) -> None:
        """With dry_run=True, no adapter calls are made."""
        parser = RecipeParser()
        recipe = parser.parse(simple_recipe_yaml)

        runner = RecipeRunner(adapter=mock_adapter)
        runner.execute(recipe, dry_run=True)

        mock_adapter.execute_bash_step.assert_not_called()
        mock_adapter.execute_agent_step.assert_not_called()


class TestRecipeResult:
    """Test RecipeResult success/failure status."""

    def test_recipe_result_success(self, simple_recipe_yaml: str, mock_adapter: MagicMock) -> None:
        """When all steps complete successfully, result.success is True."""
        parser = RecipeParser()
        recipe = parser.parse(simple_recipe_yaml)

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        assert result.success is True

    def test_recipe_result_failure(self, mock_adapter: MagicMock) -> None:
        """When any step fails, result.success is False."""
        yaml_str = """\
name: "failing-recipe"
description: "test"
version: "1.0.0"
steps:
  - id: "step-01"
    type: "bash"
    command: "exit 1"
    output: "result"
"""
        mock_adapter.execute_bash_step.side_effect = RuntimeError("exit code 1")

        parser = RecipeParser()
        recipe = parser.parse(yaml_str)

        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        assert result.success is False


class TestAdapterValidation:
    """Test that None adapter is rejected early."""

    def test_none_adapter_raises_on_execute(self, simple_recipe_yaml: str) -> None:
        """Executing with adapter=None gives a clear ValueError, not AttributeError."""
        parser = RecipeParser()
        recipe = parser.parse(simple_recipe_yaml)

        runner = RecipeRunner(adapter=None)
        with pytest.raises(ValueError, match="adapter is required"):
            runner.execute(recipe)

    def test_none_adapter_allowed_for_dry_run(self, simple_recipe_yaml: str) -> None:
        """Dry run works fine without an adapter."""
        parser = RecipeParser()
        recipe = parser.parse(simple_recipe_yaml)

        runner = RecipeRunner(adapter=None)
        result = runner.execute(recipe, dry_run=True)
        assert result.success is True


def _extract_prompt_from_call(call_args) -> str:
    """Extract the prompt string from a mock adapter call.

    Handles both positional and keyword argument patterns:
    - adapter.execute_agent_step(step, context) -> look for prompt in step or context
    - adapter.execute_agent_step(prompt="...") -> keyword arg
    - adapter.execute_agent_step("prompt text") -> positional arg

    Returns the prompt string or the string representation of all args for
    flexible assertion matching.
    """
    if call_args is None:
        return ""

    # Try keyword args first
    if call_args.kwargs:
        for key in ("prompt", "rendered_prompt", "text"):
            if key in call_args.kwargs:
                return str(call_args.kwargs[key])
        # Return string of all kwargs for flexible matching
        return str(call_args.kwargs)

    # Try positional args
    if call_args.args:
        # Return string representation of all positional args
        return " ".join(str(arg) for arg in call_args.args)

    return ""
