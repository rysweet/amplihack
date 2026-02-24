"""Tests for auto-staging of git changes after agent steps.

Verifies that:
- RecipeRunner auto-stages changes after successful agent steps by default
- Auto-staging can be disabled at the runner level
- Individual steps can override the runner-level auto_stage setting
- Auto-staging does not run for bash steps
- Auto-staging does not run during dry runs
- Auto-staging failures are gracefully handled (non-fatal)
- The parser recognizes the auto_stage step field
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from amplihack.recipes.models import StepStatus
from amplihack.recipes.parser import RecipeParser
from amplihack.recipes.runner import RecipeRunner, _git_stage_all

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

AGENT_RECIPE_YAML = """\
name: "auto-stage-test"
description: "Test auto-staging"
version: "1.0.0"
steps:
  - id: "agent-step"
    agent: "amplihack:builder"
    prompt: "Build something"
    output: "build_result"
  - id: "bash-step"
    type: "bash"
    command: "echo done"
    output: "done_result"
"""

MULTI_AGENT_YAML = """\
name: "multi-agent-test"
description: "Multiple agent steps"
version: "1.0.0"
steps:
  - id: "step-01-design"
    agent: "amplihack:architect"
    prompt: "Design something"
    output: "design"
  - id: "step-02-build"
    agent: "amplihack:builder"
    prompt: "Build {{design}}"
    output: "implementation"
  - id: "step-03-test"
    agent: "amplihack:tester"
    prompt: "Test {{implementation}}"
    output: "test_result"
"""


def _make_adapter() -> MagicMock:
    """Create a mock SDKAdapter with default success responses."""
    adapter = MagicMock()
    adapter.execute_bash_step.return_value = "bash ok"
    adapter.execute_agent_step.return_value = "agent ok"
    return adapter


# ---------------------------------------------------------------------------
# Tests: _git_stage_all helper
# ---------------------------------------------------------------------------


class TestGitStageAll:
    """Test the _git_stage_all helper function."""

    @patch("amplihack.recipes.runner.subprocess.run")
    def test_stages_files_successfully(self, mock_run: MagicMock) -> None:
        """Returns staged file list when git add succeeds and files are staged."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add -A
            MagicMock(returncode=0, stdout="src/foo.py\nsrc/bar.py\n"),  # git diff --cached
        ]
        result = _git_stage_all("/some/dir")
        assert result == "src/foo.py\nsrc/bar.py"
        assert mock_run.call_count == 2

    @patch("amplihack.recipes.runner.subprocess.run")
    def test_returns_none_when_nothing_staged(self, mock_run: MagicMock) -> None:
        """Returns None when git add succeeds but no files are staged."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add -A
            MagicMock(returncode=0, stdout=""),  # git diff --cached (empty)
        ]
        result = _git_stage_all("/some/dir")
        assert result is None

    @patch("amplihack.recipes.runner.subprocess.run")
    def test_returns_none_on_git_error(self, mock_run: MagicMock) -> None:
        """Returns None when git add fails (e.g., not a git repo)."""
        mock_run.return_value = MagicMock(returncode=128)
        result = _git_stage_all("/some/dir")
        assert result is None

    @patch("amplihack.recipes.runner.subprocess.run")
    def test_returns_none_when_git_not_found(self, mock_run: MagicMock) -> None:
        """Returns None when git binary is not found."""
        mock_run.side_effect = FileNotFoundError("git not found")
        result = _git_stage_all("/some/dir")
        assert result is None

    @patch("amplihack.recipes.runner.subprocess.run")
    def test_returns_none_on_timeout(self, mock_run: MagicMock) -> None:
        """Returns None when git command times out."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)
        result = _git_stage_all("/some/dir")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: Auto-staging behavior in RecipeRunner
# ---------------------------------------------------------------------------


class TestAutoStageDefault:
    """Test that auto-staging is ON by default for agent steps."""

    @patch("amplihack.recipes.runner._git_stage_all")
    def test_auto_stage_runs_after_agent_step(self, mock_stage: MagicMock) -> None:
        """Auto-staging runs after agent steps but not bash steps."""
        mock_stage.return_value = "src/foo.py"
        adapter = _make_adapter()
        recipe = RecipeParser().parse(AGENT_RECIPE_YAML)

        runner = RecipeRunner(adapter=adapter)
        result = runner.execute(recipe)

        assert result.success is True
        # Called once: after the agent step, NOT after the bash step
        mock_stage.assert_called_once_with(".")

    @patch("amplihack.recipes.runner._git_stage_all")
    def test_auto_stage_runs_for_each_agent_step(self, mock_stage: MagicMock) -> None:
        """Auto-staging runs after every agent step in a multi-step recipe."""
        mock_stage.return_value = "src/foo.py"
        adapter = _make_adapter()
        recipe = RecipeParser().parse(MULTI_AGENT_YAML)

        runner = RecipeRunner(adapter=adapter)
        result = runner.execute(recipe)

        assert result.success is True
        assert mock_stage.call_count == 3  # Once per agent step


class TestAutoStageDisabled:
    """Test that auto-staging can be disabled at the runner level."""

    @patch("amplihack.recipes.runner._git_stage_all")
    def test_no_staging_when_disabled(self, mock_stage: MagicMock) -> None:
        """No git operations when auto_stage=False on the runner."""
        adapter = _make_adapter()
        recipe = RecipeParser().parse(AGENT_RECIPE_YAML)

        runner = RecipeRunner(adapter=adapter, auto_stage=False)
        result = runner.execute(recipe)

        assert result.success is True
        mock_stage.assert_not_called()


class TestAutoStageStepOverride:
    """Test per-step auto_stage override."""

    @patch("amplihack.recipes.runner._git_stage_all")
    def test_step_override_disables_staging(self, mock_stage: MagicMock) -> None:
        """A step with auto_stage: false skips staging even if runner default is True."""
        yaml_str = """\
name: "step-override-test"
description: "test"
version: "1.0.0"
steps:
  - id: "no-stage-step"
    agent: "amplihack:builder"
    prompt: "Build something"
    output: "result"
    auto_stage: false
"""
        adapter = _make_adapter()
        recipe = RecipeParser().parse(yaml_str)

        runner = RecipeRunner(adapter=adapter, auto_stage=True)
        result = runner.execute(recipe)

        assert result.success is True
        mock_stage.assert_not_called()

    @patch("amplihack.recipes.runner._git_stage_all")
    def test_step_override_enables_staging(self, mock_stage: MagicMock) -> None:
        """A step with auto_stage: true stages even if runner default is False."""
        yaml_str = """\
name: "step-override-enable-test"
description: "test"
version: "1.0.0"
steps:
  - id: "force-stage-step"
    agent: "amplihack:builder"
    prompt: "Build something"
    output: "result"
    auto_stage: true
"""
        mock_stage.return_value = "src/new.py"
        adapter = _make_adapter()
        recipe = RecipeParser().parse(yaml_str)

        runner = RecipeRunner(adapter=adapter, auto_stage=False)
        result = runner.execute(recipe)

        assert result.success is True
        mock_stage.assert_called_once()


class TestAutoStageDryRun:
    """Test that auto-staging does not run during dry runs."""

    @patch("amplihack.recipes.runner._git_stage_all")
    def test_no_staging_in_dry_run(self, mock_stage: MagicMock) -> None:
        """Dry run never triggers auto-staging."""
        recipe = RecipeParser().parse(AGENT_RECIPE_YAML)

        runner = RecipeRunner(adapter=None, auto_stage=True)
        result = runner.execute(recipe, dry_run=True)

        assert result.success is True
        mock_stage.assert_not_called()


class TestAutoStageGracefulFailure:
    """Test that auto-staging failures do not break the recipe."""

    @patch("amplihack.recipes.runner._git_stage_all")
    def test_stage_failure_does_not_fail_step(self, mock_stage: MagicMock) -> None:
        """If _git_stage_all returns None, the step still succeeds."""
        mock_stage.return_value = None  # No files staged / not a git repo
        adapter = _make_adapter()
        recipe = RecipeParser().parse(AGENT_RECIPE_YAML)

        runner = RecipeRunner(adapter=adapter)
        result = runner.execute(recipe)

        assert result.success is True
        # All steps should complete
        assert len(result.step_results) == 2
        assert all(sr.status == StepStatus.COMPLETED for sr in result.step_results)


class TestAutoStageWorkingDir:
    """Test that auto-staging uses the correct working directory."""

    @patch("amplihack.recipes.runner._git_stage_all")
    def test_uses_step_working_dir(self, mock_stage: MagicMock) -> None:
        """Auto-staging uses the step's working_dir if specified."""
        yaml_str = """\
name: "working-dir-test"
description: "test"
version: "1.0.0"
steps:
  - id: "custom-dir-step"
    agent: "amplihack:builder"
    prompt: "Build in custom dir"
    output: "result"
    working_dir: "/custom/worktree"
"""
        mock_stage.return_value = "file.py"
        adapter = _make_adapter()
        recipe = RecipeParser().parse(yaml_str)

        runner = RecipeRunner(adapter=adapter, working_dir="/default/dir")
        runner.execute(recipe)

        mock_stage.assert_called_once_with("/custom/worktree")

    @patch("amplihack.recipes.runner._git_stage_all")
    def test_falls_back_to_runner_working_dir(self, mock_stage: MagicMock) -> None:
        """Auto-staging falls back to runner working_dir when step has none."""
        yaml_str = """\
name: "fallback-dir-test"
description: "test"
version: "1.0.0"
steps:
  - id: "no-dir-step"
    agent: "amplihack:builder"
    prompt: "Build"
    output: "result"
"""
        mock_stage.return_value = "file.py"
        adapter = _make_adapter()
        recipe = RecipeParser().parse(yaml_str)

        runner = RecipeRunner(adapter=adapter, working_dir="/runner/dir")
        runner.execute(recipe)

        mock_stage.assert_called_once_with("/runner/dir")


# ---------------------------------------------------------------------------
# Tests: Parser recognizes auto_stage field
# ---------------------------------------------------------------------------


class TestParserAutoStage:
    """Test that the parser correctly handles the auto_stage field."""

    def test_parses_auto_stage_true(self) -> None:
        """Parser sets auto_stage=True when specified in YAML."""
        yaml_str = """\
name: "parser-test"
version: "1.0.0"
steps:
  - id: "step-01"
    agent: "amplihack:builder"
    prompt: "Build"
    auto_stage: true
"""
        recipe = RecipeParser().parse(yaml_str)
        assert recipe.steps[0].auto_stage is True

    def test_parses_auto_stage_false(self) -> None:
        """Parser sets auto_stage=False when specified in YAML."""
        yaml_str = """\
name: "parser-test"
version: "1.0.0"
steps:
  - id: "step-01"
    agent: "amplihack:builder"
    prompt: "Build"
    auto_stage: false
"""
        recipe = RecipeParser().parse(yaml_str)
        assert recipe.steps[0].auto_stage is False

    def test_auto_stage_defaults_to_none(self) -> None:
        """Parser sets auto_stage=None when not specified (inherit runner default)."""
        yaml_str = """\
name: "parser-test"
version: "1.0.0"
steps:
  - id: "step-01"
    agent: "amplihack:builder"
    prompt: "Build"
"""
        recipe = RecipeParser().parse(yaml_str)
        assert recipe.steps[0].auto_stage is None

    def test_auto_stage_not_flagged_as_unrecognized(self) -> None:
        """Validator does not warn about auto_stage field."""
        yaml_str = """\
name: "parser-test"
version: "1.0.0"
steps:
  - id: "step-01"
    agent: "amplihack:builder"
    prompt: "Build"
    auto_stage: true
"""
        parser = RecipeParser()
        recipe = parser.parse(yaml_str)
        warnings = parser.validate(recipe, raw_yaml=yaml_str)
        assert not any("auto_stage" in w for w in warnings)
