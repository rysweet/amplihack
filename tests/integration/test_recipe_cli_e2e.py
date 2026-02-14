"""End-to-end integration tests for recipe CLI commands.

Tests the full CLI integration from command invocation through to output:
- Complete CLI command execution flow
- Integration with RecipeRunner, Parser, Discovery
- File system interactions
- Real recipe execution (with mock adapter)
- Cross-command workflows

Following TDD: These tests are written BEFORE implementation.
Expected to fail until recipe CLI is fully integrated.

Test Coverage:
- Full command execution paths
- CLI argument parsing integration
- File I/O operations
- Error propagation from components
- Real-world usage scenarios
- Performance and resource handling
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.recipes.models import RecipeResult, StepResult, StepStatus

# Check if CLI integration exists
try:
    from amplihack.cli import recipe_command  # noqa: F401

    CLI_INTEGRATED = True
except (ImportError, AttributeError):
    CLI_INTEGRATED = False


pytestmark = pytest.mark.skipif(
    not CLI_INTEGRATED, reason="Recipe CLI not yet integrated into main CLI"
)


class TestRecipeRunE2E:
    """End-to-end tests for 'amplihack recipe run' command."""

    def test_run_simple_recipe_from_file(
        self,
        recipe_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test running a simple recipe from file with bash steps."""
        recipe_file = recipe_dir / "simple.yaml"

        # Mock the adapter to avoid actual execution
        with patch("amplihack.recipes.runner.RecipeRunner") as mock_runner:
            mock_runner.return_value.execute.return_value = RecipeResult(
                recipe_name="simple-test",
                success=True,
                step_results=[
                    StepResult(
                        step_id="hello",
                        status=StepStatus.COMPLETED,
                        output="hello",
                    )
                ],
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "amplihack",
                    "recipe",
                    "run",
                    str(recipe_file),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

        assert result.returncode == 0
        assert "simple-test" in result.stdout or "success" in result.stdout.lower()

    def test_run_with_context_from_cli(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test passing context variables via CLI arguments."""
        recipe_file = recipe_dir / "simple.yaml"
        context_args = [
            "--context",
            "env=production",
            "--context",
            "debug=false",
        ]

        with patch("amplihack.recipes.runner.RecipeRunner") as mock_runner:
            mock_runner.return_value.execute.return_value = RecipeResult(
                recipe_name="test",
                success=True,
                step_results=[],
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "amplihack",
                    "recipe",
                    "run",
                    str(recipe_file),
                    *context_args,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

        assert result.returncode == 0

    def test_run_with_dry_run_flag(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test dry-run mode doesn't execute actual commands."""
        recipe_file = recipe_dir / "simple.yaml"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "run",
                str(recipe_file),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "dry" in result.stdout.lower() or "would execute" in result.stdout.lower()

    def test_run_with_json_output(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test JSON output format from CLI."""
        recipe_file = recipe_dir / "simple.yaml"

        with patch("amplihack.recipes.runner.RecipeRunner") as mock_runner:
            mock_runner.return_value.execute.return_value = RecipeResult(
                recipe_name="test",
                success=True,
                step_results=[],
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "amplihack",
                    "recipe",
                    "run",
                    str(recipe_file),
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

        assert result.returncode == 0
        # Output should be valid JSON
        json.loads(result.stdout)

    def test_run_nonexistent_file_error(self) -> None:
        """Test error handling for non-existent recipe file."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "run",
                "nonexistent.yaml",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_run_invalid_yaml_error(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test error handling for invalid YAML syntax."""
        invalid_file = recipe_dir / "invalid.yaml"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "run",
                str(invalid_file),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0

    def test_run_with_verbose_output(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test verbose mode provides detailed progress."""
        recipe_file = recipe_dir / "simple.yaml"

        with patch("amplihack.recipes.runner.RecipeRunner") as mock_runner:
            mock_runner.return_value.execute.return_value = RecipeResult(
                recipe_name="test",
                success=True,
                step_results=[
                    StepResult(step_id="step1", status=StepStatus.COMPLETED, output="done")
                ],
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "amplihack",
                    "recipe",
                    "run",
                    str(recipe_file),
                    "--verbose",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

        assert result.returncode == 0
        # Verbose should show more details
        assert len(result.stdout) > 50

    def test_run_with_working_directory(
        self,
        recipe_dir: Path,
        tmp_path: Path,
    ) -> None:
        """Test setting custom working directory."""
        recipe_file = recipe_dir / "simple.yaml"
        work_dir = tmp_path / "workdir"
        work_dir.mkdir()

        with patch("amplihack.recipes.runner.RecipeRunner") as mock_runner:
            mock_runner.return_value.execute.return_value = RecipeResult(
                recipe_name="test",
                success=True,
                step_results=[],
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "amplihack",
                    "recipe",
                    "run",
                    str(recipe_file),
                    "--working-dir",
                    str(work_dir),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

        assert result.returncode == 0


class TestRecipeListE2E:
    """End-to-end tests for 'amplihack recipe list' command."""

    def test_list_all_recipes_in_directory(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test listing all recipes in a directory."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "list",
                str(recipe_dir),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "simple-test" in result.stdout
        assert "agent-test" in result.stdout

    def test_list_with_tag_filter(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test filtering recipes by tag."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "list",
                str(recipe_dir),
                "--tag",
                "test",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0

    def test_list_json_format(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test JSON output format for list."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "list",
                str(recipe_dir),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        # Should be valid JSON
        recipes = json.loads(result.stdout)
        assert isinstance(recipes, list)

    def test_list_empty_directory(
        self,
        tmp_path: Path,
    ) -> None:
        """Test listing empty recipe directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "list",
                str(empty_dir),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "no recipes" in result.stdout.lower() or "0" in result.stdout

    def test_list_nonexistent_directory(self) -> None:
        """Test error for non-existent directory."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "list",
                "/nonexistent/path",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0


class TestRecipeValidateE2E:
    """End-to-end tests for 'amplihack recipe validate' command."""

    def test_validate_valid_recipe(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test validation of valid recipe file."""
        recipe_file = recipe_dir / "simple.yaml"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "validate",
                str(recipe_file),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "valid" in result.stdout.lower()

    def test_validate_invalid_recipe(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test validation of invalid recipe file."""
        invalid_file = recipe_dir / "invalid.yaml"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "validate",
                str(invalid_file),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0
        assert "invalid" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_validate_with_verbose_output(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test verbose validation shows details."""
        recipe_file = recipe_dir / "simple.yaml"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "validate",
                str(recipe_file),
                "--verbose",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        # Verbose should show validation details
        assert "step" in result.stdout.lower() or len(result.stdout) > 50

    def test_validate_json_output(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test JSON output for validation."""
        recipe_file = recipe_dir / "simple.yaml"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "validate",
                str(recipe_file),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        # Should be valid JSON
        validation_result = json.loads(result.stdout)
        assert "valid" in validation_result


class TestRecipeShowE2E:
    """End-to-end tests for 'amplihack recipe show' command."""

    def test_show_recipe_details(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test showing recipe details."""
        recipe_file = recipe_dir / "simple.yaml"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "show",
                str(recipe_file),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "simple-test" in result.stdout

    def test_show_with_steps(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test showing recipe with step details."""
        recipe_file = recipe_dir / "simple.yaml"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "show",
                str(recipe_file),
                "--steps",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "hello" in result.stdout  # step id from fixture

    def test_show_json_format(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test JSON output for show command."""
        recipe_file = recipe_dir / "simple.yaml"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "show",
                str(recipe_file),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        recipe_data = json.loads(result.stdout)
        assert recipe_data["name"] == "simple-test"

    def test_show_nonexistent_file(self) -> None:
        """Test error for non-existent recipe file."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "show",
                "nonexistent.yaml",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0


class TestCrossCommandWorkflows:
    """Tests for realistic multi-command workflows."""

    def test_list_then_show_workflow(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test workflow: list recipes, then show details of one."""
        # First, list recipes
        list_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "list",
                str(recipe_dir),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert list_result.returncode == 0
        recipes = json.loads(list_result.stdout)
        first_recipe_name = recipes[0]["name"]

        # Then show details of first recipe
        recipe_file = recipe_dir / f"{first_recipe_name}.yaml"
        if not recipe_file.exists():
            recipe_file = recipe_dir / "simple.yaml"  # fallback

        show_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "show",
                str(recipe_file),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert show_result.returncode == 0

    def test_validate_then_run_workflow(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test workflow: validate recipe, then run it."""
        recipe_file = recipe_dir / "simple.yaml"

        # First validate
        validate_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "validate",
                str(recipe_file),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert validate_result.returncode == 0

        # Then run
        with patch("amplihack.recipes.runner.RecipeRunner") as mock_runner:
            mock_runner.return_value.execute.return_value = RecipeResult(
                recipe_name="test",
                success=True,
                step_results=[],
            )

            run_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "amplihack",
                    "recipe",
                    "run",
                    str(recipe_file),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

        assert run_result.returncode == 0

    def test_dry_run_then_real_run_workflow(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test workflow: dry-run first, then real execution."""
        recipe_file = recipe_dir / "simple.yaml"

        # Dry run
        dry_run_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "run",
                str(recipe_file),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert dry_run_result.returncode == 0

        # Real run
        with patch("amplihack.recipes.runner.RecipeRunner") as mock_runner:
            mock_runner.return_value.execute.return_value = RecipeResult(
                recipe_name="test",
                success=True,
                step_results=[],
            )

            real_run_result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "amplihack",
                    "recipe",
                    "run",
                    str(recipe_file),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

        assert real_run_result.returncode == 0


class TestCLIHelp:
    """Tests for CLI help text and documentation."""

    def test_recipe_help(self) -> None:
        """Test main recipe command help."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "--help",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "run" in result.stdout
        assert "list" in result.stdout
        assert "validate" in result.stdout
        assert "show" in result.stdout

    def test_run_help(self) -> None:
        """Test 'run' subcommand help."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "run",
                "--help",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "context" in result.stdout or "dry-run" in result.stdout

    def test_list_help(self) -> None:
        """Test 'list' subcommand help."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "list",
                "--help",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert "tag" in result.stdout or "filter" in result.stdout


class TestPerformanceAndResources:
    """Tests for performance and resource handling."""

    def test_list_large_directory_performance(
        self,
        tmp_path: Path,
    ) -> None:
        """Test listing directory with many recipes completes in reasonable time."""
        large_dir = tmp_path / "large"
        large_dir.mkdir()

        # Create 50 recipe files
        for i in range(50):
            recipe_file = large_dir / f"recipe-{i}.yaml"
            recipe_file.write_text(
                f"""
name: recipe-{i}
description: Test recipe {i}
steps:
  - id: step1
    type: bash
    command: echo 'test'
"""
            )

        import time

        start = time.time()
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack",
                "recipe",
                "list",
                str(large_dir),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        elapsed = time.time() - start

        assert result.returncode == 0
        assert elapsed < 10.0  # Should complete in < 10 seconds

    def test_memory_handling_large_output(
        self,
        recipe_dir: Path,
    ) -> None:
        """Test handling of recipes with large output."""
        # This test verifies the CLI doesn't crash with large data
        recipe_file = recipe_dir / "simple.yaml"

        with patch("amplihack.recipes.runner.RecipeRunner") as mock_runner:
            large_output = "x" * 1_000_000  # 1MB output
            mock_runner.return_value.execute.return_value = RecipeResult(
                recipe_name="test",
                success=True,
                step_results=[
                    StepResult(
                        step_id="large",
                        status=StepStatus.COMPLETED,
                        output=large_output,
                    )
                ],
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "amplihack",
                    "recipe",
                    "run",
                    str(recipe_file),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

        assert result.returncode == 0
