"""Tests for recipe runner parse_json fixes and CLAUDECODE handling.

Covers:
1. parse_json with non-JSON output → step FAILS (not silent degradation)
2. parse_json with markdown-wrapped JSON → extracts correctly
3. parse_json with direct JSON → works as before
4. Condition with unparsed string context → step FAILS with clear error
5. CLAUDECODE stripped from subprocess environment
6. All 15 recipe YAML files parse and dry-run without errors
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from amplihack.recipes.models import Step, StepType
from amplihack.recipes.runner import RecipeRunner, StepStatus


class TestParseJsonExtraction:
    """Test the _parse_json_output static method."""

    def test_direct_json(self):
        result = RecipeRunner._parse_json_output('{"key": "value"}', "test")
        assert result == {"key": "value"}

    def test_markdown_fenced_json(self):
        output = 'Here is the result:\n```json\n{"is_qa": true, "confidence": "high"}\n```\nDone.'
        result = RecipeRunner._parse_json_output(output, "test")
        assert result == {"is_qa": True, "confidence": "high"}

    def test_markdown_fenced_no_json_tag(self):
        output = 'Result:\n```\n{"status": "ok"}\n```'
        result = RecipeRunner._parse_json_output(output, "test")
        assert result == {"status": "ok"}

    def test_embedded_json_object(self):
        output = 'The classification is {"is_qa": false, "reason": "complex"} as shown.'
        result = RecipeRunner._parse_json_output(output, "test")
        assert result is not None
        assert result["is_qa"] is False

    def test_json_array(self):
        result = RecipeRunner._parse_json_output("[1, 2, 3]", "test")
        assert result == [1, 2, 3]

    def test_completely_invalid_returns_none(self):
        result = RecipeRunner._parse_json_output("This is just plain text", "test")
        assert result is None

    def test_empty_string_returns_none(self):
        result = RecipeRunner._parse_json_output("", "test")
        assert result is None

    def test_nested_json(self):
        output = '```json\n{"outer": {"inner": "value"}, "list": [1, 2]}\n```'
        result = RecipeRunner._parse_json_output(output, "test")
        assert result["outer"]["inner"] == "value"


class TestParseJsonStepFailure:
    """Test that parse_json=true steps FAIL when JSON can't be parsed."""

    def _make_runner(self):
        adapter = MagicMock()
        return RecipeRunner(adapter=adapter)

    def _make_step(self, step_id="test-step", parse_json=True, output_name="result"):
        return Step(
            id=step_id,
            step_type=StepType.AGENT,
            prompt="test prompt",
            output=output_name,
            parse_json=parse_json,
        )

    def test_parse_json_fails_on_non_json(self):
        """Step must FAIL, not silently store raw string."""
        runner = self._make_runner()
        runner._adapter.execute_agent_step = MagicMock(return_value="Not JSON at all")
        step = self._make_step()

        from amplihack.recipes.context import RecipeContext

        ctx = RecipeContext()
        result = runner._execute_step(step, ctx, dry_run=False)

        assert result.status == StepStatus.FAILED
        assert "parse_json failed" in result.error

    def test_parse_json_succeeds_on_valid_json(self):
        runner = self._make_runner()
        runner._adapter.execute_agent_step = MagicMock(return_value='{"key": "value"}')
        step = self._make_step()

        from amplihack.recipes.context import RecipeContext

        ctx = RecipeContext()
        result = runner._execute_step(step, ctx, dry_run=False)

        assert result.status == StepStatus.COMPLETED
        assert ctx.get("result") == {"key": "value"}

    def test_parse_json_succeeds_on_markdown_wrapped(self):
        runner = self._make_runner()
        runner._adapter.execute_agent_step = MagicMock(
            return_value='Here:\n```json\n{"is_qa": true}\n```'
        )
        step = self._make_step()

        from amplihack.recipes.context import RecipeContext

        ctx = RecipeContext()
        result = runner._execute_step(step, ctx, dry_run=False)

        assert result.status == StepStatus.COMPLETED
        stored = ctx.get("result")
        assert isinstance(stored, dict)
        assert stored["is_qa"] is True


class TestConditionFailure:
    """Test that conditions on unparsed data FAIL steps instead of skipping."""

    def _make_runner(self):
        adapter = MagicMock()
        return RecipeRunner(adapter=adapter)

    def test_condition_on_missing_attribute_fails_step(self):
        """If condition references .is_qa on a string, step must FAIL."""
        from amplihack.recipes.context import RecipeContext

        ctx = RecipeContext()
        ctx.set("classification", "raw string not a dict")

        step = Step(
            id="test-condition",
            step_type=StepType.AGENT,
            prompt="test",
            condition="classification.is_qa == True",
        )

        runner = self._make_runner()
        result = runner._execute_step(step, ctx, dry_run=False)

        assert result.status == StepStatus.FAILED
        assert "Condition error" in result.error

    def test_condition_on_parsed_dict_works(self):
        from amplihack.recipes.context import RecipeContext

        ctx = RecipeContext()
        ctx.set("classification", {"is_qa": True, "confidence": "high"})

        step = Step(
            id="test-condition",
            step_type=StepType.AGENT,
            prompt="test",
            condition="classification.is_qa == True",
        )

        runner = self._make_runner()
        # Should not fail -- condition should evaluate to True
        # (it will try to execute the step, which will use the mock adapter)
        runner._adapter.execute_agent_step = MagicMock(return_value="answer")
        result = runner._execute_step(step, ctx, dry_run=False)

        # Step should complete (condition was True, step executed)
        assert result.status == StepStatus.COMPLETED


class TestCLAUDECODEStripped:
    """Test that CLAUDECODE is removed from subprocess environment."""

    def test_claudecode_not_in_agent_step_env(self):
        from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter

        adapter = CLISubprocessAdapter(cli="echo", working_dir="/tmp")

        with patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.wait = MagicMock()
            mock_popen.return_value = mock_proc

            # Mock the output file operations
            with patch("builtins.open", MagicMock()):
                with patch.object(Path, "mkdir"):
                    with patch.object(Path, "read_text", return_value="test output"):
                        with patch.object(Path, "unlink"):
                            with patch.dict(os.environ, {"CLAUDECODE": "1"}):
                                adapter.execute_agent_step("test prompt")

            # Popen MUST have been called
            assert mock_popen.called, "Popen should have been called"
            child_env = mock_popen.call_args.kwargs.get("env")
            assert child_env is not None, "env must be passed to Popen"
            assert "CLAUDECODE" not in child_env, (
                "CLAUDECODE must be stripped from agent step subprocess environment"
            )

    def test_claudecode_not_in_bash_step_env(self):
        from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter

        adapter = CLISubprocessAdapter(cli="echo", working_dir="/tmp")

        with patch("amplihack.recipes.adapters.cli_subprocess.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

            with patch.dict(os.environ, {"CLAUDECODE": "1"}):
                adapter.execute_bash_step("echo hello")

            assert mock_run.called, "subprocess.run should have been called"
            child_env = mock_run.call_args.kwargs.get("env")
            assert child_env is not None, "env must be passed to subprocess.run"
            assert "CLAUDECODE" not in child_env, (
                "CLAUDECODE must be stripped from bash step subprocess environment"
            )


class TestRecipeYAMLValidation:
    """Test that all recipe YAML files parse and dry-run without errors."""

    def _get_recipe_files(self):
        import glob

        return sorted(glob.glob("amplifier-bundle/recipes/*.yaml"))

    def test_all_recipes_exist(self):
        recipes = self._get_recipe_files()
        assert len(recipes) >= 10, f"Expected 10+ recipes, found {len(recipes)}"

    def test_all_recipes_parse(self):
        from amplihack.recipes.parser import RecipeParser

        parser = RecipeParser()
        for path in self._get_recipe_files():
            recipe = parser.parse_file(path)
            assert recipe.name, f"Recipe at {path} has no name"
            assert len(recipe.steps) > 0, f"Recipe {recipe.name} has no steps"

    def test_all_recipes_dry_run(self):
        from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter
        from amplihack.recipes.parser import RecipeParser

        parser = RecipeParser()
        adapter = CLISubprocessAdapter(working_dir=".")

        # Recipes with conditions on step outputs can fail dry-run because
        # dry-run stores "[dry run]" strings, not real parsed objects.
        # These are known limitations of dry-run mode, not recipe bugs.
        for path in self._get_recipe_files():
            recipe = parser.parse_file(path)
            runner = RecipeRunner(adapter=adapter)

            # Dry-run now skips condition evaluation entirely, so all recipes
            # should succeed in dry-run mode
            result = runner.execute(recipe, user_context={}, dry_run=True)
            assert result.success, f"Recipe '{recipe.name}' failed dry-run: " + "; ".join(
                f"{sr.step_id}: {sr.error}"
                for sr in result.step_results
                if sr.status == StepStatus.FAILED
            )

    def test_conditions_reference_valid_outputs(self):
        """Every condition must reference a variable defined by a prior step or context default."""
        import re

        from amplihack.recipes.parser import RecipeParser

        parser = RecipeParser()
        errors = []
        for path in self._get_recipe_files():
            recipe = parser.parse_file(path)
            defined_outputs = set()
            # Context defaults are also valid variable sources
            context_keys = set(recipe.context.keys()) if recipe.context else set()

            for step in recipe.steps:
                if step.condition:
                    # Extract ROOT variable names from condition
                    # "strategy.parallel_deployment.specialist_agent" → "strategy"
                    # "'CONTINUE' in iteration_1" → "iteration_1"
                    # "num_versions >= 4" → "num_versions"
                    vars_used = set()
                    # Match the first identifier in a dotted chain
                    for match in re.findall(r"\b([a-zA-Z_]\w*)(?:\.\w+)+", step.condition):
                        vars_used.add(match)
                    # Match standalone identifiers in 'X in Y' patterns
                    for match in re.findall(r"'[^']+'\s+in\s+(\w+)", step.condition):
                        vars_used.add(match)
                    # Match standalone identifiers NOT preceded by a dot
                    # (to avoid extracting nested attrs like .requires_debate)
                    for match in re.findall(r"(?<![.\w])([a-zA-Z_]\w+)\s*[=!><]+", step.condition):
                        vars_used.add(match)

                    builtins = {
                        "true", "false", "True", "False", "None",
                        "not", "and", "or", "in", "is", "CONTINUE",
                    }
                    for var in vars_used - builtins:
                        if var not in defined_outputs and var not in context_keys:
                            errors.append(
                                f"{recipe.name}/{step.id}: condition references "
                                f"'{var}' but it is not defined by a prior step "
                                f"or context default"
                            )

                if step.output:
                    defined_outputs.add(step.output)

        assert not errors, "Condition-output mismatches found:\n" + "\n".join(errors)


class TestRecipeRunnerEndToEnd:
    """End-to-end test running qa-workflow with a mock adapter."""

    def test_qa_workflow_with_json_response(self):
        from amplihack.recipes.parser import RecipeParser

        parser = RecipeParser()
        recipe = parser.parse_file("amplifier-bundle/recipes/qa-workflow.yaml")

        # Create adapter that returns proper JSON for classification step
        adapter = MagicMock()
        adapter.execute_agent_step = MagicMock(
            side_effect=[
                # Step 1: classification - return valid JSON
                '{"is_qa": true, "confidence": "high", "reasoning": "simple question", "suggested_workflow": "qa", "can_answer_directly": true}',
                # Step 2: answer
                "The answer is 42.",
                # Step 3: escalation check - return valid JSON
                '{"answer_complete": true, "escalation_needed": false, "escalation_reason": null, "suggested_workflow": "none", "follow_up_hint": null}',
            ]
        )
        # compile-output is a bash step
        adapter.execute_bash_step = MagicMock(
            return_value='{"workflow": "qa-workflow", "status": "complete"}'
        )

        runner = RecipeRunner(adapter=adapter)
        result = runner.execute(
            recipe,
            user_context={"question": "What is the meaning of life?"},
        )

        classification_step = next(
            (sr for sr in result.step_results if sr.step_id == "classification-confirmation"),
            None,
        )
        assert classification_step is not None
        assert classification_step.status == StepStatus.COMPLETED

    def test_qa_workflow_with_markdown_wrapped_json(self):
        from amplihack.recipes.parser import RecipeParser

        parser = RecipeParser()
        recipe = parser.parse_file("amplifier-bundle/recipes/qa-workflow.yaml")

        adapter = MagicMock()
        adapter.execute_agent_step = MagicMock(
            side_effect=[
                # Step 1: classification wrapped in markdown
                'Here is my classification:\n```json\n{"is_qa": true, "confidence": "high", "reasoning": "simple", "suggested_workflow": "qa", "can_answer_directly": true}\n```',
                # Step 2: answer
                "42",
                # Step 3: escalation
                '```json\n{"answer_complete": true, "escalation_needed": false, "escalation_reason": null, "suggested_workflow": "none", "follow_up_hint": null}\n```',
            ]
        )
        adapter.execute_bash_step = MagicMock(
            return_value='{"workflow": "qa-workflow", "status": "complete"}'
        )

        runner = RecipeRunner(adapter=adapter)
        result = runner.execute(
            recipe,
            user_context={"question": "What is 2+2?"},
        )

        classification_step = next(
            (sr for sr in result.step_results if sr.step_id == "classification-confirmation"),
            None,
        )
        assert classification_step is not None
        assert classification_step.status == StepStatus.COMPLETED


class TestParseJsonRetry:
    """Test that parse_json retries once before failing."""

    def _make_runner(self):
        adapter = MagicMock()
        return RecipeRunner(adapter=adapter)

    def _make_step(self, step_id="test-step", parse_json=True, output_name="result"):
        return Step(
            id=step_id,
            step_type=StepType.AGENT,
            prompt="test prompt",
            output=output_name,
            parse_json=parse_json,
        )

    def test_retry_succeeds_on_second_attempt(self):
        """First attempt returns non-JSON, retry returns valid JSON."""
        runner = self._make_runner()
        runner._adapter.execute_agent_step = MagicMock(
            side_effect=[
                "Not JSON at all",  # First call (original)
                '{"key": "value"}',  # Second call (retry)
            ]
        )
        step = self._make_step()

        from amplihack.recipes.context import RecipeContext

        ctx = RecipeContext()
        result = runner._execute_step(step, ctx, dry_run=False)

        assert result.status == StepStatus.COMPLETED
        assert ctx.get("result") == {"key": "value"}
        assert runner._adapter.execute_agent_step.call_count == 2

    def test_retry_fails_after_both_attempts(self):
        """Both attempts return non-JSON -> step fails."""
        runner = self._make_runner()
        runner._adapter.execute_agent_step = MagicMock(
            side_effect=["Not JSON", "Still not JSON"]
        )
        step = self._make_step()

        from amplihack.recipes.context import RecipeContext

        ctx = RecipeContext()
        result = runner._execute_step(step, ctx, dry_run=False)

        assert result.status == StepStatus.FAILED
        assert "retry" in result.error.lower()

    def test_no_retry_for_bash_steps(self):
        """Bash steps cannot be retried."""
        runner = self._make_runner()
        runner._adapter.execute_bash_step = MagicMock(return_value="Not JSON")
        step = Step(
            id="bash-step",
            step_type=StepType.BASH,
            command="echo hello",
            output="result",
            parse_json=True,
        )

        from amplihack.recipes.context import RecipeContext

        ctx = RecipeContext()
        result = runner._execute_step(step, ctx, dry_run=False)

        assert result.status == StepStatus.FAILED
        assert runner._adapter.execute_bash_step.call_count == 1

    def test_retry_prompt_includes_json_reminder(self):
        """Retry prompt should tell LLM to return only JSON."""
        runner = self._make_runner()
        call_prompts = []

        def capture_prompt(prompt, **kwargs):
            call_prompts.append(prompt)
            if len(call_prompts) == 1:
                return "Not JSON"
            return '{"ok": true}'

        runner._adapter.execute_agent_step = MagicMock(side_effect=capture_prompt)
        step = self._make_step()

        from amplihack.recipes.context import RecipeContext

        ctx = RecipeContext()
        runner._execute_step(step, ctx, dry_run=False)

        assert len(call_prompts) == 2
        assert "valid JSON" in call_prompts[1]


class TestQaWorkflowConditionGuard:
    """Test that qa-workflow compile-output steps have condition guards."""

    def test_compile_output_has_condition(self):
        from amplihack.recipes.parser import RecipeParser

        parser = RecipeParser()
        recipe = parser.parse_file("amplifier-bundle/recipes/qa-workflow.yaml")

        compile_steps = [s for s in recipe.steps if s.id.startswith("compile-output")]
        assert len(compile_steps) >= 1, "Should have at least one compile-output step"

        for step in compile_steps:
            assert step.condition is not None, (
                f"Step {step.id} must have a condition guard"
            )
