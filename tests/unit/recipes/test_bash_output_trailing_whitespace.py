"""Tests for issue #3058 — bash step output trailing whitespace.

Bash commands always append a trailing newline to stdout. Without stripping,
conditions like ``workstream_count != 1`` silently fail because the stored
value is ``"1\\n"`` which never equals ``"1"``.

Fixes:
1. RecipeRunner strips bash output via ``rstrip()`` before storing in context.
2. RecipeContext._build_namespace strips string values (defense-in-depth).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from amplihack.recipes.context import RecipeContext
from amplihack.recipes.models import Recipe, Step, StepStatus, StepType
from amplihack.recipes.parser import RecipeParser
from amplihack.recipes.runner import RecipeRunner


# ---------------------------------------------------------------------------
# RecipeContext tests — defense-in-depth stripping in _build_namespace
# ---------------------------------------------------------------------------


class TestContextStripsTrailingWhitespace:
    """RecipeContext._build_namespace must strip trailing whitespace from strings."""

    def test_build_namespace_strips_trailing_newline(self) -> None:
        """Values with trailing newline compare equal to the stripped variant."""
        ctx = RecipeContext({"workstream_count": "1\n"})
        assert ctx.evaluate("workstream_count == '1'")

    def test_build_namespace_strips_trailing_crlf(self) -> None:
        """Windows-style CRLF is also stripped."""
        ctx = RecipeContext({"val": "hello\r\n"})
        assert ctx.evaluate("val == 'hello'")

    def test_build_namespace_strips_multiple_newlines(self) -> None:
        """Multiple trailing newlines are all stripped."""
        ctx = RecipeContext({"count": "5\n\n\n"})
        assert ctx.evaluate("count == '5'")

    def test_build_namespace_preserves_internal_whitespace(self) -> None:
        """Internal whitespace (spaces/newlines in middle) must NOT be altered."""
        ctx = RecipeContext({"path": "hello world"})
        assert ctx.evaluate("path == 'hello world'")

    def test_condition_not_equal_with_trailing_newline(self) -> None:
        """workstream_count != '1' is False when value is '1\\n' (stripped to '1')."""
        ctx = RecipeContext({"workstream_count": "1\n"})
        # After stripping, '1' == '1', so != is False → condition returns False
        assert not ctx.evaluate("workstream_count != '1'")

    def test_condition_not_equal_when_truly_different(self) -> None:
        """workstream_count != '1' is True when value is genuinely different."""
        ctx = RecipeContext({"workstream_count": "3\n"})
        assert ctx.evaluate("workstream_count != '1'")


# ---------------------------------------------------------------------------
# RecipeRunner tests — bash output stripped before storing in context
# ---------------------------------------------------------------------------


class TestRunnerStripsBashOutput:
    """RecipeRunner must strip bash output before storing it in step_results."""

    @pytest.fixture()
    def mock_adapter(self) -> MagicMock:
        return MagicMock()

    def _make_runner(self, adapter: MagicMock) -> RecipeRunner:
        return RecipeRunner(adapter=adapter, working_dir="/tmp", auto_stage=False)

    def test_bash_output_stripped_in_context(self, mock_adapter: MagicMock) -> None:
        """Bash output stored in context must have trailing newline removed."""
        mock_adapter.execute_bash_step.return_value = "1\n"

        yaml = """
name: test-strip
steps:
  - id: count-step
    type: bash
    command: echo 1
    output: workstream_count
"""
        recipe = RecipeParser().parse(yaml)
        runner = self._make_runner(mock_adapter)
        result = runner.execute(recipe)

        assert result.success
        # Context must contain the stripped value
        assert result.context["workstream_count"] == "1"

    def test_bash_output_stripped_for_condition(self, mock_adapter: MagicMock) -> None:
        """A condition comparing bash output must work despite trailing newline."""
        mock_adapter.execute_bash_step.side_effect = ["1\n", "done"]

        yaml = """
name: test-condition
steps:
  - id: count-step
    type: bash
    command: echo 1
    output: workstream_count
  - id: conditional-step
    type: bash
    command: echo done
    condition: "workstream_count == '1'"
    output: result
"""
        recipe = RecipeParser().parse(yaml)
        runner = self._make_runner(mock_adapter)
        result = runner.execute(recipe)

        assert result.success
        step_statuses = {sr.step_id: sr.status for sr in result.step_results}
        # Conditional step must EXECUTE (condition is True after strip)
        assert step_statuses["conditional-step"] == StepStatus.COMPLETED

    def test_bash_output_not_equal_condition_with_newline(self, mock_adapter: MagicMock) -> None:
        """Condition ``!= 1`` evaluates correctly after stripping (issue #3058 scenario)."""
        # Simulate smart-orchestrator: count != 1 should be False when count=1
        mock_adapter.execute_bash_step.side_effect = ["1\n", "skipped"]

        yaml = """
name: test-not-equal
steps:
  - id: count-step
    type: bash
    command: echo 1
    output: workstream_count
  - id: force-single
    type: bash
    command: echo skipped
    condition: "workstream_count != '1'"
    output: result
"""
        recipe = RecipeParser().parse(yaml)
        runner = self._make_runner(mock_adapter)
        result = runner.execute(recipe)

        assert result.success
        step_statuses = {sr.step_id: sr.status for sr in result.step_results}
        # condition is False (1 == 1 after strip) → step must be SKIPPED
        assert step_statuses["force-single"] == StepStatus.SKIPPED

    def test_multiline_bash_output_trailing_stripped_only(self, mock_adapter: MagicMock) -> None:
        """Only trailing whitespace is stripped; leading/middle content is preserved."""
        # e.g. `wc -l` output is "      3\n" — spaces + number + newline
        mock_adapter.execute_bash_step.return_value = "      3\n"

        yaml = """
name: test-multiline
steps:
  - id: wc-step
    type: bash
    command: wc -l file.txt
    output: line_count
"""
        recipe = RecipeParser().parse(yaml)
        runner = self._make_runner(mock_adapter)
        result = runner.execute(recipe)

        assert result.success
        # Trailing newline stripped, but leading spaces preserved
        assert result.context["line_count"] == "      3"

    def test_empty_bash_output_passthrough(self, mock_adapter: MagicMock) -> None:
        """Empty string bash output (e.g. a command that produces no output) passes through."""
        mock_adapter.execute_bash_step.return_value = ""

        yaml = """
name: test-empty
steps:
  - id: empty-step
    type: bash
    command: "true"
    output: result
"""
        recipe = RecipeParser().parse(yaml)
        runner = self._make_runner(mock_adapter)
        result = runner.execute(recipe)

        assert result.success
        assert result.context.get("result") == ""
