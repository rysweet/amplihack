"""Unit tests for recipe CLI command handlers.

Tests the command handler functions that implement:
- amplihack recipe run
- amplihack recipe list
- amplihack recipe validate
- amplihack recipe show

Following TDD: These tests are written BEFORE implementation.
Expected to fail until recipe_command.py is implemented.

Test Coverage:
- Command argument parsing
- Context merging (CLI args + user context + recipe defaults)
- Error handling and exit codes
- Integration with Recipe Runner API
- Output formatting delegation
- Edge cases and boundary conditions
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from amplihack.recipes.models import Recipe, RecipeResult

# Import the command handlers we're testing (will fail until implemented)
try:
    from amplihack.cli.recipe_command import (
        handle_list,
        handle_run,
        handle_show,
        handle_validate,
    )

    COMMANDS_EXIST = True
except ImportError:
    COMMANDS_EXIST = False
    # Create placeholder functions for test structure
    handle_run = None
    handle_list = None
    handle_validate = None
    handle_show = None


pytestmark = pytest.mark.skipif(not COMMANDS_EXIST, reason="recipe_command.py not yet implemented")


class TestHandleRun:
    """Tests for the 'recipe run' command handler."""

    def test_run_basic_execution(
        self,
        simple_recipe: Recipe,
        successful_result: RecipeResult,
        mock_recipe_runner: MagicMock,
    ) -> None:
        """Test basic recipe execution with default options."""
        mock_recipe_runner.execute.return_value = successful_result

        with (
            patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser,
            patch("amplihack.cli.recipe_command.RecipeRunner", return_value=mock_recipe_runner),
        ):
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_run(
                recipe_path="test.yaml",
                context={},
                dry_run=False,
                verbose=False,
                format="table",
            )

        assert exit_code == 0
        mock_recipe_runner.execute.assert_called_once()

    def test_run_with_user_context(
        self,
        simple_recipe: Recipe,
        successful_result: RecipeResult,
        mock_recipe_runner: MagicMock,
    ) -> None:
        """Test recipe execution with user-provided context."""
        user_context = {"env": "production", "debug": False}
        mock_recipe_runner.execute.return_value = successful_result

        with (
            patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser,
            patch("amplihack.cli.recipe_command.RecipeRunner", return_value=mock_recipe_runner),
        ):
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_run(
                recipe_path="test.yaml",
                context=user_context,
                dry_run=False,
                verbose=False,
                format="table",
            )

        # Verify context was passed to runner
        call_args = mock_recipe_runner.execute.call_args
        assert call_args[1]["user_context"] == user_context
        assert exit_code == 0

    def test_run_with_dry_run_mode(
        self,
        simple_recipe: Recipe,
        successful_result: RecipeResult,
        mock_recipe_runner: MagicMock,
    ) -> None:
        """Test recipe execution in dry-run mode (no actual execution)."""
        mock_recipe_runner.execute.return_value = successful_result

        with (
            patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser,
            patch("amplihack.cli.recipe_command.RecipeRunner", return_value=mock_recipe_runner),
        ):
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_run(
                recipe_path="test.yaml",
                context={},
                dry_run=True,
                verbose=False,
                format="table",
            )

        # Verify dry_run flag was passed
        call_args = mock_recipe_runner.execute.call_args
        assert call_args[1]["dry_run"] is True
        assert exit_code == 0

    def test_run_failure_returns_nonzero(
        self,
        simple_recipe: Recipe,
        failed_result: RecipeResult,
        mock_recipe_runner: MagicMock,
    ) -> None:
        """Test that failed recipe execution returns non-zero exit code."""
        mock_recipe_runner.execute.return_value = failed_result

        with (
            patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser,
            patch("amplihack.cli.recipe_command.RecipeRunner", return_value=mock_recipe_runner),
        ):
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_run(
                recipe_path="test.yaml",
                context={},
                dry_run=False,
                verbose=False,
                format="table",
            )

        assert exit_code == 1

    def test_run_file_not_found(self) -> None:
        """Test handling of non-existent recipe file."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.side_effect = FileNotFoundError("Recipe not found")

            exit_code = handle_run(
                recipe_path="nonexistent.yaml",
                context={},
                dry_run=False,
                verbose=False,
                format="table",
            )

        assert exit_code == 1

    def test_run_invalid_yaml(self) -> None:
        """Test handling of invalid YAML in recipe file."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.side_effect = ValueError("Invalid YAML")

            exit_code = handle_run(
                recipe_path="invalid.yaml",
                context={},
                dry_run=False,
                verbose=False,
                format="table",
            )

        assert exit_code == 1

    def test_run_verbose_mode(
        self,
        simple_recipe: Recipe,
        successful_result: RecipeResult,
        mock_recipe_runner: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test verbose output includes step details."""
        mock_recipe_runner.execute.return_value = successful_result

        with (
            patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser,
            patch("amplihack.cli.recipe_command.RecipeRunner", return_value=mock_recipe_runner),
        ):
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_run(
                recipe_path="test.yaml",
                context={},
                dry_run=False,
                verbose=True,
                format="table",
            )

        captured = capsys.readouterr()
        # Verbose mode should show step-by-step output
        assert "step1" in captured.out or "step1" in captured.err
        assert exit_code == 0

    def test_run_json_output_format(
        self,
        simple_recipe: Recipe,
        successful_result: RecipeResult,
        mock_recipe_runner: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test JSON output format."""
        mock_recipe_runner.execute.return_value = successful_result

        with (
            patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser,
            patch("amplihack.cli.recipe_command.RecipeRunner", return_value=mock_recipe_runner),
        ):
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_run(
                recipe_path="test.yaml",
                context={},
                dry_run=False,
                verbose=False,
                format="json",
            )

        captured = capsys.readouterr()
        # Should output valid JSON
        assert "{" in captured.out
        assert exit_code == 0

    def test_run_yaml_output_format(
        self,
        simple_recipe: Recipe,
        successful_result: RecipeResult,
        mock_recipe_runner: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test YAML output format."""
        mock_recipe_runner.execute.return_value = successful_result

        with (
            patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser,
            patch("amplihack.cli.recipe_command.RecipeRunner", return_value=mock_recipe_runner),
        ):
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_run(
                recipe_path="test.yaml",
                context={},
                dry_run=False,
                verbose=False,
                format="yaml",
            )

        captured = capsys.readouterr()
        # Should output valid YAML
        assert ":" in captured.out
        assert exit_code == 0

    def test_run_context_merging_priority(
        self,
        mock_recipe_runner: MagicMock,
    ) -> None:
        """Test context merging: CLI args > user context > recipe defaults."""
        recipe_with_context = Recipe(
            name="test",
            context={"key1": "recipe_default", "key2": "recipe_only"},
        )
        user_context = {"key1": "user_override", "key3": "user_only"}

        mock_recipe_runner.execute.return_value = RecipeResult(
            recipe_name="test",
            success=True,
            step_results=[],
        )

        with (
            patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser,
            patch("amplihack.cli.recipe_command.RecipeRunner", return_value=mock_recipe_runner),
        ):
            mock_parser.return_value.parse_file.return_value = recipe_with_context

            handle_run(
                recipe_path="test.yaml",
                context=user_context,
                dry_run=False,
                verbose=False,
                format="table",
            )

        # Verify merged context
        call_args = mock_recipe_runner.execute.call_args
        merged = call_args[1]["user_context"]
        assert merged["key1"] == "user_override"  # User overrides recipe
        assert merged["key3"] == "user_only"  # User adds new key

    def test_run_with_working_directory(
        self,
        simple_recipe: Recipe,
        successful_result: RecipeResult,
        mock_recipe_runner: MagicMock,
    ) -> None:
        """Test recipe execution with custom working directory."""
        mock_recipe_runner.execute.return_value = successful_result

        with (
            patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser,
            patch("amplihack.cli.recipe_command.RecipeRunner", return_value=mock_recipe_runner),
        ):
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_run(
                recipe_path="test.yaml",
                context={},
                dry_run=False,
                verbose=False,
                format="table",
                working_dir="/custom/dir",
            )

        # Runner should be initialized with custom working_dir
        assert exit_code == 0

    def test_run_exception_handling(
        self,
        simple_recipe: Recipe,
        mock_recipe_runner: MagicMock,
    ) -> None:
        """Test graceful handling of unexpected exceptions."""
        mock_recipe_runner.execute.side_effect = RuntimeError("Unexpected error")

        with (
            patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser,
            patch("amplihack.cli.recipe_command.RecipeRunner", return_value=mock_recipe_runner),
        ):
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_run(
                recipe_path="test.yaml",
                context={},
                dry_run=False,
                verbose=False,
                format="table",
            )

        assert exit_code == 1


class TestHandleList:
    """Tests for the 'recipe list' command handler."""

    def test_list_all_recipes(
        self,
        sample_recipes: list[Recipe],
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test listing all available recipes."""
        with patch("amplihack.cli.recipe_command.discover_recipes") as mock_discovery:
            mock_discovery.return_value = sample_recipes

            exit_code = handle_list(
                recipe_dir="./recipes",
                format="table",
                tags=None,
                verbose=False,
            )

        captured = capsys.readouterr()
        assert "recipe-1" in captured.out
        assert "recipe-2" in captured.out
        assert "recipe-3" in captured.out
        assert exit_code == 0

    def test_list_filter_by_tag(
        self,
        sample_recipes: list[Recipe],
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test filtering recipes by tag."""
        with patch("amplihack.cli.recipe_command.discover_recipes") as mock_discovery:
            mock_discovery.return_value = sample_recipes

            exit_code = handle_list(
                recipe_dir="./recipes",
                format="table",
                tags=["tag1"],
                verbose=False,
            )

        captured = capsys.readouterr()
        # Only recipes with tag1 should appear
        assert "recipe-1" in captured.out
        assert "recipe-3" in captured.out
        assert "recipe-2" not in captured.out
        assert exit_code == 0

    def test_list_filter_by_multiple_tags(
        self,
        sample_recipes: list[Recipe],
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test filtering recipes by multiple tags (AND logic)."""
        with patch("amplihack.cli.recipe_command.discover_recipes") as mock_discovery:
            mock_discovery.return_value = sample_recipes

            exit_code = handle_list(
                recipe_dir="./recipes",
                format="table",
                tags=["tag1", "tag2"],
                verbose=False,
            )

        captured = capsys.readouterr()
        # Only recipes with BOTH tags
        assert "recipe-1" in captured.out
        assert exit_code == 0

    def test_list_json_format(
        self,
        sample_recipes: list[Recipe],
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test JSON output format for list."""
        with patch("amplihack.cli.recipe_command.discover_recipes") as mock_discovery:
            mock_discovery.return_value = sample_recipes

            exit_code = handle_list(
                recipe_dir="./recipes",
                format="json",
                tags=None,
                verbose=False,
            )

        captured = capsys.readouterr()
        assert "{" in captured.out
        assert "recipe-1" in captured.out
        assert exit_code == 0

    def test_list_yaml_format(
        self,
        sample_recipes: list[Recipe],
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test YAML output format for list."""
        with patch("amplihack.cli.recipe_command.discover_recipes") as mock_discovery:
            mock_discovery.return_value = sample_recipes

            exit_code = handle_list(
                recipe_dir="./recipes",
                format="yaml",
                tags=None,
                verbose=False,
            )

        captured = capsys.readouterr()
        assert ":" in captured.out
        assert exit_code == 0

    def test_list_verbose_mode(
        self,
        sample_recipes: list[Recipe],
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test verbose listing includes full recipe details."""
        with patch("amplihack.cli.recipe_command.discover_recipes") as mock_discovery:
            mock_discovery.return_value = sample_recipes

            exit_code = handle_list(
                recipe_dir="./recipes",
                format="table",
                tags=None,
                verbose=True,
            )

        captured = capsys.readouterr()
        # Verbose should show descriptions and tags
        assert "First recipe" in captured.out or "description" in captured.out
        assert exit_code == 0

    def test_list_empty_directory(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test listing when no recipes are found."""
        with patch("amplihack.cli.recipe_command.discover_recipes") as mock_discovery:
            mock_discovery.return_value = []

            exit_code = handle_list(
                recipe_dir="./empty",
                format="table",
                tags=None,
                verbose=False,
            )

        captured = capsys.readouterr()
        assert "No recipes found" in captured.out or "0 recipes" in captured.out
        assert exit_code == 0

    def test_list_invalid_directory(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test error handling for invalid recipe directory."""
        with patch("amplihack.cli.recipe_command.discover_recipes") as mock_discovery:
            mock_discovery.side_effect = FileNotFoundError("Directory not found")

            exit_code = handle_list(
                recipe_dir="./nonexistent",
                format="table",
                tags=None,
                verbose=False,
            )

        assert exit_code == 1

    def test_list_no_matching_tags(
        self,
        sample_recipes: list[Recipe],
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test filtering with tags that match no recipes."""
        with patch("amplihack.cli.recipe_command.discover_recipes") as mock_discovery:
            mock_discovery.return_value = sample_recipes

            exit_code = handle_list(
                recipe_dir="./recipes",
                format="table",
                tags=["nonexistent_tag"],
                verbose=False,
            )

        captured = capsys.readouterr()
        assert "No recipes found" in captured.out or "0 recipes" in captured.out
        assert exit_code == 0


class TestHandleValidate:
    """Tests for the 'recipe validate' command handler."""

    def test_validate_valid_recipe(
        self,
        simple_recipe: Recipe,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test validation of a valid recipe file."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_validate(
                recipe_path="test.yaml",
                verbose=False,
                format="table",
            )

        captured = capsys.readouterr()
        assert "valid" in captured.out.lower() or "ok" in captured.out.lower()
        assert exit_code == 0

    def test_validate_invalid_yaml(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test validation of file with invalid YAML syntax."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.side_effect = ValueError("Invalid YAML syntax")

            exit_code = handle_validate(
                recipe_path="invalid.yaml",
                verbose=False,
                format="table",
            )

        captured = capsys.readouterr()
        assert "invalid" in captured.out.lower() or "error" in captured.out.lower()
        assert exit_code == 1

    def test_validate_missing_required_fields(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test validation of recipe missing required fields."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.side_effect = ValueError(
                "Missing required field: steps"
            )

            exit_code = handle_validate(
                recipe_path="incomplete.yaml",
                verbose=False,
                format="table",
            )

        captured = capsys.readouterr()
        assert "steps" in captured.out.lower() or "missing" in captured.out.lower()
        assert exit_code == 1

    def test_validate_file_not_found(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test validation of non-existent file."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.side_effect = FileNotFoundError("File not found")

            exit_code = handle_validate(
                recipe_path="nonexistent.yaml",
                verbose=False,
                format="table",
            )

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "error" in captured.out.lower()
        assert exit_code == 1

    def test_validate_verbose_mode(
        self,
        simple_recipe: Recipe,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test verbose validation includes detailed checks."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_validate(
                recipe_path="test.yaml",
                verbose=True,
                format="table",
            )

        captured = capsys.readouterr()
        # Verbose should show validation details
        assert "steps" in captured.out.lower() or "valid" in captured.out.lower()
        assert exit_code == 0

    def test_validate_json_output(
        self,
        simple_recipe: Recipe,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test JSON output format for validation."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_validate(
                recipe_path="test.yaml",
                verbose=False,
                format="json",
            )

        captured = capsys.readouterr()
        assert "{" in captured.out
        assert exit_code == 0

    def test_validate_multiple_errors(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test validation with multiple error messages."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.side_effect = ValueError(
                "Multiple errors: missing name, invalid step type"
            )

            exit_code = handle_validate(
                recipe_path="broken.yaml",
                verbose=True,
                format="table",
            )

        captured = capsys.readouterr()
        assert "name" in captured.out.lower()
        assert "step" in captured.out.lower()
        assert exit_code == 1


class TestHandleShow:
    """Tests for the 'recipe show' command handler."""

    def test_show_recipe_details(
        self,
        simple_recipe: Recipe,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test showing detailed recipe information."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_show(
                recipe_path="test.yaml",
                format="table",
                show_steps=True,
                show_context=True,
            )

        captured = capsys.readouterr()
        assert "simple-test" in captured.out
        assert "A simple test recipe" in captured.out
        assert exit_code == 0

    def test_show_with_steps(
        self,
        complex_recipe: Recipe,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test showing recipe with step details."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.return_value = complex_recipe

            exit_code = handle_show(
                recipe_path="test.yaml",
                format="table",
                show_steps=True,
                show_context=False,
            )

        captured = capsys.readouterr()
        assert "setup" in captured.out
        assert "analyze" in captured.out
        assert exit_code == 0

    def test_show_with_context(
        self,
        complex_recipe: Recipe,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test showing recipe with context variables."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.return_value = complex_recipe

            exit_code = handle_show(
                recipe_path="test.yaml",
                format="table",
                show_steps=False,
                show_context=True,
            )

        captured = capsys.readouterr()
        assert "output_dir" in captured.out or "context" in captured.out.lower()
        assert exit_code == 0

    def test_show_json_format(
        self,
        simple_recipe: Recipe,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test JSON output format for show."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_show(
                recipe_path="test.yaml",
                format="json",
                show_steps=True,
                show_context=True,
            )

        captured = capsys.readouterr()
        assert "{" in captured.out
        assert "simple-test" in captured.out
        assert exit_code == 0

    def test_show_yaml_format(
        self,
        simple_recipe: Recipe,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test YAML output format for show."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_show(
                recipe_path="test.yaml",
                format="yaml",
                show_steps=True,
                show_context=True,
            )

        captured = capsys.readouterr()
        assert "name:" in captured.out
        assert exit_code == 0

    def test_show_file_not_found(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test error handling for non-existent recipe."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.side_effect = FileNotFoundError("File not found")

            exit_code = handle_show(
                recipe_path="nonexistent.yaml",
                format="table",
                show_steps=True,
                show_context=True,
            )

        captured = capsys.readouterr()
        output = (captured.out + captured.err).lower()
        assert "not found" in output or "error" in output
        assert exit_code == 1

    def test_show_minimal_display(
        self,
        simple_recipe: Recipe,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test showing recipe with minimal details (no steps/context)."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.return_value = simple_recipe

            exit_code = handle_show(
                recipe_path="test.yaml",
                format="table",
                show_steps=False,
                show_context=False,
            )

        captured = capsys.readouterr()
        assert "simple-test" in captured.out
        assert "A simple test recipe" in captured.out
        assert exit_code == 0


class TestErrorHandling:
    """Tests for error handling across all commands."""

    def test_graceful_keyboard_interrupt(self) -> None:
        """Test graceful handling of Ctrl+C during execution."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.side_effect = KeyboardInterrupt()

            exit_code = handle_run(
                recipe_path="test.yaml",
                context={},
                dry_run=False,
                verbose=False,
                format="table",
            )

        assert exit_code == 130  # Standard exit code for SIGINT

    def test_permission_denied_error(self) -> None:
        """Test handling of permission denied errors."""
        with patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser:
            mock_parser.return_value.parse_file.side_effect = PermissionError("Permission denied")

            exit_code = handle_run(
                recipe_path="test.yaml",
                context={},
                dry_run=False,
                verbose=False,
                format="table",
            )

        assert exit_code == 1

    def test_invalid_format_argument(self) -> None:
        """Test handling of invalid output format."""
        with pytest.raises(ValueError, match="format"):
            handle_run(
                recipe_path="test.yaml",
                context={},
                dry_run=False,
                verbose=False,
                format="invalid_format",
            )


class TestContextMerging:
    """Tests specifically for context merging logic."""

    def test_empty_context_handling(
        self,
        mock_recipe_runner: MagicMock,
    ) -> None:
        """Test handling of empty context dictionaries."""
        recipe = Recipe(name="test", context={})
        mock_recipe_runner.execute.return_value = RecipeResult(
            recipe_name="test", success=True, step_results=[]
        )

        with (
            patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser,
            patch("amplihack.cli.recipe_command.RecipeRunner", return_value=mock_recipe_runner),
        ):
            mock_parser.return_value.parse_file.return_value = recipe

            exit_code = handle_run(
                recipe_path="test.yaml",
                context={},
                dry_run=False,
                verbose=False,
                format="table",
            )

        assert exit_code == 0

    def test_nested_context_values(
        self,
        mock_recipe_runner: MagicMock,
    ) -> None:
        """Test context merging with nested dictionary values."""
        recipe = Recipe(
            name="test",
            context={"config": {"db": "sqlite", "port": 5432}},
        )
        user_context = {"config": {"db": "postgres"}}  # Partial override

        mock_recipe_runner.execute.return_value = RecipeResult(
            recipe_name="test", success=True, step_results=[]
        )

        with (
            patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser,
            patch("amplihack.cli.recipe_command.RecipeRunner", return_value=mock_recipe_runner),
        ):
            mock_parser.return_value.parse_file.return_value = recipe

            exit_code = handle_run(
                recipe_path="test.yaml",
                context=user_context,
                dry_run=False,
                verbose=False,
                format="table",
            )

        assert exit_code == 0

    def test_context_with_none_values(
        self,
        mock_recipe_runner: MagicMock,
    ) -> None:
        """Test context merging when values are None."""
        recipe = Recipe(
            name="test",
            context={"key1": None, "key2": "value"},
        )
        user_context = {"key1": "override"}

        mock_recipe_runner.execute.return_value = RecipeResult(
            recipe_name="test", success=True, step_results=[]
        )

        with (
            patch("amplihack.cli.recipe_command.RecipeParser") as mock_parser,
            patch("amplihack.cli.recipe_command.RecipeRunner", return_value=mock_recipe_runner),
        ):
            mock_parser.return_value.parse_file.return_value = recipe

            exit_code = handle_run(
                recipe_path="test.yaml",
                context=user_context,
                dry_run=False,
                verbose=False,
                format="table",
            )

        assert exit_code == 0
