"""Outside-in tests: Python recipe runner removal — real recipe execution.

Verifies from a USER's perspective that recipes actually work after
the Python runner was removed. These tests execute real recipes via
the Rust runner and verify the results.

Test categories:
1. Real recipe dry-run execution (default-workflow, smart-orchestrator)
2. Recipe discovery and parsing still works
3. Python runner is fully gone (no fallback path)
4. Backward-compatible callers work (adapter kwarg ignored)
5. Error behavior when Rust binary missing
6. Source files physically removed
7. CLI module is clean
"""

import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("Cannot find repo root")


REPO_ROOT = _repo_root()


# ============================================================================
# Scenario 1: Real recipe dry-run execution via Rust
# ============================================================================


class TestRecipeDryRunExecution:
    """Execute REAL recipes via Rust runner with dry_run=True."""

    def test_default_workflow_dry_run(self):
        """The main development workflow recipe should execute via Rust."""
        from amplihack.recipes import run_recipe_by_name

        result = run_recipe_by_name(
            "default-workflow",
            user_context={"task_description": "test task", "repo_path": "."},
            dry_run=True,
        )
        assert result.success, f"default-workflow dry-run failed: {result}"
        assert result.recipe_name == "default-workflow"
        assert len(result.step_results) > 10, (
            f"default-workflow should have many steps, got {len(result.step_results)}"
        )

    def test_smart_orchestrator_dry_run(self):
        """The smart-orchestrator recipe should execute via Rust."""
        from amplihack.recipes import run_recipe_by_name

        result = run_recipe_by_name(
            "smart-orchestrator",
            user_context={"task_description": "test orchestration", "repo_path": "."},
            dry_run=True,
        )
        assert result.success, "smart-orchestrator dry-run failed"
        assert result.recipe_name == "smart-orchestrator"
        assert len(result.step_results) > 0

    def test_investigation_workflow_dry_run(self):
        """Investigation workflow recipe should execute via Rust."""
        from amplihack.recipes import find_recipe, run_recipe_by_name

        # Only run if investigation-workflow recipe exists
        if find_recipe("investigation-workflow") is None:
            pytest.skip("investigation-workflow recipe not found")

        result = run_recipe_by_name(
            "investigation-workflow",
            user_context={"task_description": "test investigation", "repo_path": "."},
            dry_run=True,
        )
        assert result.success


# ============================================================================
# Scenario 2: Recipe discovery and parsing
# ============================================================================


class TestRecipeDiscoveryAndParsing:
    """Recipes should be discoverable and parseable (these feed into Rust runner)."""

    def test_list_recipes_finds_multiple(self):
        from amplihack.recipes import list_recipes

        recipes = list_recipes()
        assert len(recipes) >= 3, f"Expected at least 3 recipes, found {len(recipes)}"

    def test_find_default_workflow(self):
        from amplihack.recipes import find_recipe

        path = find_recipe("default-workflow")
        assert path is not None, "default-workflow recipe not found"
        assert Path(path).exists()

    def test_find_smart_orchestrator(self):
        from amplihack.recipes import find_recipe

        path = find_recipe("smart-orchestrator")
        assert path is not None, "smart-orchestrator recipe not found"

    def test_parse_recipe_from_yaml(self):
        """parse_recipe should work (uses parser, not runner)."""
        from amplihack.recipes import parse_recipe

        yaml_content = """
name: test-parse-recipe
description: Verify parsing works
steps:
  - id: step1
    type: agent
    agent: architect
    prompt: Design something
"""
        recipe = parse_recipe(yaml_content)
        assert recipe.name == "test-parse-recipe"
        assert len(recipe.steps) == 1
        assert recipe.steps[0].id == "step1"

    def test_parse_real_recipe_file(self):
        """Parse a real recipe file from disk."""
        from amplihack.recipes import RecipeParser, find_recipe

        path = find_recipe("default-workflow")
        assert path is not None
        parser = RecipeParser()
        recipe = parser.parse_file(str(path))
        assert recipe.name == "default-workflow"
        assert len(recipe.steps) > 10


# ============================================================================
# Scenario 3: Python runner completely gone
# ============================================================================


class TestPythonRunnerRemoved:
    """No path should exist to invoke the Python recipe runner."""

    def test_runner_module_gone(self):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("amplihack.recipes.runner")

    def test_context_module_gone(self):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("amplihack.recipes.context")

    def test_adapters_package_gone(self):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("amplihack.recipes.adapters")

    def test_no_recipe_runner_class(self):
        import amplihack.recipes as mod

        assert not hasattr(mod, "RecipeRunner")

    def test_no_recipe_context_class(self):
        import amplihack.recipes as mod

        assert not hasattr(mod, "RecipeContext")

    def test_no_run_recipe_shortcut(self):
        """The old run_recipe() that used Python runner is gone."""
        import amplihack.recipes as mod

        assert not hasattr(mod, "run_recipe")

    def test_source_files_deleted(self):
        assert not (REPO_ROOT / "src/amplihack/recipes/runner.py").exists()
        assert not (REPO_ROOT / "src/amplihack/recipes/context.py").exists()
        assert not (REPO_ROOT / "src/amplihack/recipes/adapters").exists()


# ============================================================================
# Scenario 4: Backward compatibility
# ============================================================================


class TestBackwardCompatibility:
    """Old callers passing adapter= must not crash."""

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_adapter_kwarg_accepted(self, mock_rust):
        from amplihack.recipes import run_recipe_by_name

        mock_rust.return_value = MagicMock()
        # Old code: run_recipe_by_name("x", adapter=CLISubprocessAdapter())
        run_recipe_by_name("test", adapter=MagicMock())
        mock_rust.assert_called_once()

    @patch("amplihack.recipes.run_recipe_via_rust")
    def test_adapter_not_forwarded_to_rust(self, mock_rust):
        from amplihack.recipes import run_recipe_by_name

        mock_rust.return_value = MagicMock()
        run_recipe_by_name("test", adapter="should-be-ignored")
        call_kwargs = mock_rust.call_args[1]
        assert "adapter" not in call_kwargs


# ============================================================================
# Scenario 5: Error behavior
# ============================================================================


class TestErrorBehavior:
    """Clear errors when Rust binary is missing."""

    def test_clear_error_when_rust_missing(self):
        from amplihack.recipes import RustRunnerNotFoundError, run_recipe_by_name

        with patch("amplihack.recipes.rust_runner.find_rust_binary", return_value=None):
            with pytest.raises(RustRunnerNotFoundError, match="recipe-runner-rs"):
                run_recipe_by_name("default-workflow")

    def test_recipe_not_found_error(self):
        """Non-existent recipe should raise clear error from Rust runner."""
        from amplihack.recipes import run_recipe_by_name

        with pytest.raises((FileNotFoundError, RuntimeError)):
            run_recipe_by_name("nonexistent-recipe-xyz-12345")


# ============================================================================
# Scenario 6: Rust runner produces valid results
# ============================================================================


class TestRustRunnerResultStructure:
    """Verify the Rust runner returns properly structured RecipeResult."""

    def test_result_has_recipe_name(self):
        from amplihack.recipes import run_recipe_by_name

        result = run_recipe_by_name(
            "default-workflow",
            user_context={"task_description": "test", "repo_path": "."},
            dry_run=True,
        )
        assert isinstance(result.recipe_name, str)
        assert result.recipe_name == "default-workflow"

    def test_result_has_step_results(self):
        from amplihack.recipes import run_recipe_by_name

        result = run_recipe_by_name(
            "default-workflow",
            user_context={"task_description": "test", "repo_path": "."},
            dry_run=True,
        )
        assert len(result.step_results) > 0
        for sr in result.step_results:
            assert hasattr(sr, "step_id")
            assert hasattr(sr, "status")

    def test_result_has_success_flag(self):
        from amplihack.recipes import run_recipe_by_name

        result = run_recipe_by_name(
            "default-workflow",
            user_context={"task_description": "test", "repo_path": "."},
            dry_run=True,
        )
        assert isinstance(result.success, bool)


# ============================================================================
# Scenario 7: CLI module clean
# ============================================================================


class TestCLIModuleClean:
    """The recipe CLI command must not reference Python runner."""

    def test_recipe_command_imports_clean(self):
        mod = importlib.import_module("amplihack.recipe_cli.recipe_command")
        assert hasattr(mod, "handle_run")
        assert hasattr(mod, "handle_list")

    def test_recipe_command_source_no_python_runner(self):
        source = (REPO_ROOT / "src/amplihack/recipe_cli/recipe_command.py").read_text()
        assert "RecipeRunner" not in source
        assert "CLISubprocessAdapter" not in source
        assert "from amplihack.recipes.adapters" not in source
