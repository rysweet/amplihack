"""Unit tests for recipe CLI loader helpers."""

from __future__ import annotations

from amplihack.recipe_cli.loader import discover_recipe_definitions


def _write_recipe(path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class TestDiscoverRecipeDefinitions:
    def test_discovers_valid_recipes_from_directory(self, tmp_path) -> None:
        recipe_file = tmp_path / "valid.yaml"
        _write_recipe(
            recipe_file,
            "name: valid\nsteps:\n  - id: step-01\n    type: bash\n    command: echo hi\n",
        )

        recipes = discover_recipe_definitions(str(tmp_path))

        assert [recipe.name for recipe in recipes] == ["valid"]

    def test_warns_for_invalid_discovered_recipe_even_when_not_verbose(
        self, tmp_path, capsys
    ) -> None:
        _write_recipe(
            tmp_path / "valid.yaml",
            "name: valid\nsteps:\n  - id: step-01\n    type: bash\n    command: echo hi\n",
        )
        _write_recipe(tmp_path / "broken.yaml", "name: broken\n")

        recipes = discover_recipe_definitions(str(tmp_path))

        captured = capsys.readouterr()
        assert [recipe.name for recipe in recipes] == ["valid"]
        assert "Warning: Skipped invalid recipe definitions" in captured.err
        assert "broken.yaml" in captured.err
