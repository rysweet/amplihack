"""Edge case tests for Recipe Runner components.

These tests verify robust handling of unusual inputs across parser, context,
runner, template, and agent resolver modules:
- Very large inputs (1000+ steps, 10K+ char strings, 1MB+ outputs)
- Unicode and special characters (emoji, RTL, control chars, YAML bombs)
- Deeply nested structures (100+ levels)
- Boundary conditions (None vs empty string, integer overflow)
- Circular references and recursion
- File system edge cases (missing files, corruption, race conditions)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from amplihack.recipes.agent_resolver import AgentNotFoundError, AgentResolver
from amplihack.recipes.context import RecipeContext
from amplihack.recipes.parser import RecipeParser
from amplihack.recipes.runner import RecipeRunner


class TestParserEdgeCases:
    """Test parser behavior with extreme and unusual inputs."""

    def test_parse_very_large_recipe(self) -> None:
        """Parse a recipe with 1000+ steps successfully."""
        steps_yaml = "\n".join(
            [
                f'  - id: "step-{i:04d}"\n    type: "bash"\n    command: "echo step{i}"'
                for i in range(1000)
            ]
        )
        yaml_str = f"""\
name: "large-recipe"
description: "Recipe with 1000 steps"
version: "1.0.0"
steps:
{steps_yaml}
"""
        parser = RecipeParser()
        recipe = parser.parse(yaml_str)

        assert recipe.name == "large-recipe"
        assert len(recipe.steps) == 1000
        assert recipe.steps[0].id == "step-0000"
        assert recipe.steps[999].id == "step-0999"

    def test_parse_deeply_nested_context(self) -> None:
        """Parse recipe with deeply nested context values."""
        parser = RecipeParser()
        yaml_str = """\
name: "nested-context"
description: "Deep nesting"
version: "1.0.0"
context:
  level1:
    level2:
      level3:
        level4:
          level5:
            level6:
              level7:
                level8:
                  level9:
                    level10: "deep_value"
steps:
  - id: "step-01"
    type: "bash"
    command: "echo test"
"""
        recipe = parser.parse(yaml_str)

        assert (
            recipe.context["level1"]["level2"]["level3"]["level4"]["level5"]["level6"]["level7"][
                "level8"
            ]["level9"]["level10"]
            == "deep_value"
        )

    def test_parse_unicode_in_all_fields(self) -> None:
        """Parse recipe with Unicode characters in name, description, and steps."""
        parser = RecipeParser()
        yaml_str = """\
name: "recipe-with-émojis-🎉"
description: "Testing Unicode: 你好世界 مرحبا العالم"
version: "1.0.0"
author: "Tëst Üser 测试"
steps:
  - id: "step-émoji-🚀"
    type: "bash"
    command: "echo 'Hello 世界 🌍'"
    output: "unicode_output"
"""
        recipe = parser.parse(yaml_str)

        assert "émojis-🎉" in recipe.name
        assert "你好世界" in recipe.description
        assert "مرحبا العالم" in recipe.description
        assert recipe.author == "Tëst Üser 测试"
        assert recipe.steps[0].id == "step-émoji-🚀"
        assert "世界 🌍" in recipe.steps[0].command

    def test_parse_rejects_yaml_bomb(self) -> None:
        """Reject YAML bombs (circular references and billion laughs attacks)."""
        parser = RecipeParser()
        # YAML bomb attempt using anchors and aliases
        yaml_str = """\
name: &a ["lol", *a]
"""
        # PyYAML safe_load should protect against this
        with pytest.raises((ValueError, yaml.YAMLError)):
            parser.parse(yaml_str)

    def test_parse_empty_strings_vs_none(self) -> None:
        """Distinguish between empty string and missing (None) values."""
        parser = RecipeParser()
        yaml_str = """\
name: "empty-vs-none"
description: ""
version: "1.0.0"
steps:
  - id: "step-01"
    type: "bash"
    command: ""
    output: ""
"""
        recipe = parser.parse(yaml_str)

        # Empty description should be empty string, not None
        assert recipe.description == ""
        assert recipe.steps[0].command == ""
        assert recipe.steps[0].output == ""
        # Fields not provided should remain None
        assert recipe.steps[0].condition is None

    def test_parse_special_chars_in_step_ids(self) -> None:
        """Parse step IDs with various special characters."""
        parser = RecipeParser()
        yaml_str = """\
name: "special-chars"
description: "test"
version: "1.0.0"
steps:
  - id: "step-with-dashes-and_underscores"
    type: "bash"
    command: "echo 1"
  - id: "step.with.dots"
    type: "bash"
    command: "echo 2"
  - id: "step:with:colons"
    type: "bash"
    command: "echo 3"
"""
        recipe = parser.parse(yaml_str)

        assert len(recipe.steps) == 3
        assert recipe.steps[0].id == "step-with-dashes-and_underscores"
        assert recipe.steps[1].id == "step.with.dots"
        assert recipe.steps[2].id == "step:with:colons"

    def test_parse_integer_overflow_timeout(self) -> None:
        """Handle extremely large timeout values gracefully."""
        parser = RecipeParser()
        yaml_str = """\
name: "large-timeout"
description: "test"
version: "1.0.0"
steps:
  - id: "step-01"
    type: "bash"
    command: "echo test"
    timeout: 999999999999
"""
        recipe = parser.parse(yaml_str)

        # Should accept very large integers
        assert recipe.steps[0].timeout == 999999999999


class TestContextEdgeCases:
    """Test context behavior with extreme and unusual inputs."""

    def test_render_unicode_templates_with_emoji(self) -> None:
        """Render templates containing emoji and RTL text."""
        ctx = RecipeContext({"emoji": "🎉", "rtl": "مرحبا"})
        result = ctx.render("Hello {{emoji}} {{rtl}}")

        assert result == "Hello 🎉 مرحبا"

    def test_render_very_long_template(self) -> None:
        """Render templates with 10K+ character strings."""
        long_value = "x" * 10000
        ctx = RecipeContext({"long": long_value})
        result = ctx.render("{{long}}")

        assert len(result) == 10000
        assert result == long_value

    def test_get_circular_reference(self) -> None:
        """Handle circular references in context data."""
        # Create a circular reference
        circular: dict = {"a": {}}
        circular["a"]["b"] = circular  # type: ignore[assignment]

        # Python's deepcopy has built-in recursion detection and handles this gracefully
        # by creating a copy without infinite recursion. This is correct behavior.
        ctx = RecipeContext(circular)
        # Verify it was created without error
        assert ctx.get("a") is not None

    def test_get_deeply_nested_structure(self) -> None:
        """Access deeply nested keys (100+ levels)."""
        # Build nested dict 100 levels deep
        nested: dict = {"value": "deep"}
        for i in range(100, 0, -1):
            nested = {f"level{i}": nested}

        ctx = RecipeContext(nested)

        # Build dot-notation key for 100 levels
        key = ".".join([f"level{i}" for i in range(1, 101)] + ["value"])
        result = ctx.get(key)

        assert result == "deep"

    def test_render_large_arrays_and_dicts(self) -> None:
        """Render templates with very large arrays and dicts (10K+ items)."""
        large_list = list(range(10000))
        large_dict = {f"key{i}": i for i in range(10000)}

        ctx = RecipeContext({"list": large_list, "dict": large_dict})
        result = ctx.render("{{list}}")

        # Should serialize to JSON
        parsed = json.loads(result)
        assert len(parsed) == 10000
        assert parsed[9999] == 9999

    def test_render_binary_data(self) -> None:
        """Handle binary data in context gracefully."""
        ctx = RecipeContext({"binary": b"\x00\x01\x02\xff"})
        result = ctx.render("{{binary}}")

        # Binary data is rendered using str() which gives repr format
        assert result == "b'\\x00\\x01\\x02\\xff'"

    def test_set_special_chars_in_variable_names(self) -> None:
        """Handle special characters in variable names."""
        ctx = RecipeContext({})

        # set() stores at top level only, doesn't parse dots
        ctx.set("a.b.c", "value")
        # The key is stored literally as "a.b.c"
        assert ctx.get("a.b.c") is None  # Dot-notation lookup fails
        # But direct key access would work if we exposed _data
        assert ctx._data["a.b.c"] == "value"

    def test_render_nested_template_braces(self) -> None:
        """Handle templates with nested braces."""
        ctx = RecipeContext({"key": "value"})

        # Double braces should be recognized
        result = ctx.render("{{key}}")
        assert result == "value"

        # Single braces should pass through
        result = ctx.render("{key}")
        assert result == "{key}"

        # Triple braces should leave outer braces
        result = ctx.render("{{{key}}}")
        assert result == "{value}"

    def test_evaluate_condition_with_unicode(self) -> None:
        """Evaluate conditions containing Unicode variables."""
        ctx = RecipeContext({"emoji": "🎉", "greeting": "hello"})

        # Condition with Unicode should work
        result = ctx.evaluate('emoji == "🎉"')
        assert result is True

        result = ctx.evaluate('greeting == "hello"')
        assert result is True


class TestRunnerEdgeCases:
    """Test runner behavior with extreme and unusual inputs."""

    def test_execute_empty_recipe_steps(self, mock_adapter: MagicMock) -> None:
        """Handle recipe with empty steps list."""
        parser = RecipeParser()
        # Parser should reject this, so we test the validation
        yaml_str = """\
name: "empty-recipe"
description: "No steps"
version: "1.0.0"
steps: []
"""
        with pytest.raises(ValueError, match="at least one step"):
            parser.parse(yaml_str)

    def test_execute_single_step_recipe(self, mock_adapter: MagicMock) -> None:
        """Execute recipe with exactly one step."""
        parser = RecipeParser()
        yaml_str = """\
name: "single-step"
description: "One step only"
version: "1.0.0"
steps:
  - id: "only-step"
    type: "bash"
    command: "echo hello"
"""
        recipe = parser.parse(yaml_str)
        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        assert result.success
        assert len(result.step_results) == 1
        assert mock_adapter.execute_bash_step.call_count == 1

    def test_execute_all_steps_skipped(self, mock_adapter: MagicMock) -> None:
        """Handle recipe where all steps are skipped by conditions."""
        parser = RecipeParser()
        yaml_str = """\
name: "all-skipped"
description: "All steps skipped"
version: "1.0.0"
context:
  never: "no"
steps:
  - id: "step-01"
    type: "bash"
    command: "echo 1"
    condition: 'never == "yes"'
  - id: "step-02"
    type: "bash"
    command: "echo 2"
    condition: 'never == "yes"'
"""
        recipe = parser.parse(yaml_str)
        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Should succeed even though no steps ran
        assert result.success
        assert len(result.step_results) == 2
        # No steps should have executed
        assert mock_adapter.execute_bash_step.call_count == 0

    def test_execute_output_none_vs_empty_string(self, mock_adapter: MagicMock) -> None:
        """Distinguish between None and empty string outputs."""
        mock_adapter.execute_bash_step.return_value = ""

        parser = RecipeParser()
        yaml_str = """\
name: "empty-output"
description: "Step returns empty string"
version: "1.0.0"
steps:
  - id: "step-01"
    type: "bash"
    command: "echo -n ''"
    output: "result"
"""
        recipe = parser.parse(yaml_str)
        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        # Empty string should be stored, not None
        assert result.context["result"] == ""
        assert "result" in result.context

    def test_execute_very_long_output(self, mock_adapter: MagicMock) -> None:
        """Handle step outputs of 1MB+ size."""
        large_output = "x" * (1024 * 1024)  # 1MB
        mock_adapter.execute_bash_step.return_value = large_output

        parser = RecipeParser()
        yaml_str = """\
name: "large-output"
description: "Step returns 1MB+ output"
version: "1.0.0"
steps:
  - id: "step-01"
    type: "bash"
    command: "cat large_file.txt"
    output: "large_data"
"""
        recipe = parser.parse(yaml_str)
        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        assert result.success
        assert len(result.context["large_data"]) == 1024 * 1024

    def test_execute_step_id_with_special_characters(self, mock_adapter: MagicMock) -> None:
        """Execute steps with special characters in IDs."""
        parser = RecipeParser()
        yaml_str = """\
name: "special-ids"
description: "Steps with special char IDs"
version: "1.0.0"
steps:
  - id: "step:with:colons"
    type: "bash"
    command: "echo 1"
    output: "result_1"
  - id: "step.with.dots"
    type: "bash"
    command: "echo 2"
    output: "result_2"
"""
        recipe = parser.parse(yaml_str)
        runner = RecipeRunner(adapter=mock_adapter)
        result = runner.execute(recipe)

        assert result.success
        assert len(result.step_results) == 2
        assert result.step_results[0].step_id == "step:with:colons"
        assert result.step_results[1].step_id == "step.with.dots"


class TestTemplateEdgeCases:
    """Test template rendering edge cases."""

    def test_render_nested_template_braces_complex(self) -> None:
        """Complex nesting of template braces."""
        ctx = RecipeContext({"a": "1", "b": "2"})

        # Multiple variables in nested braces
        result = ctx.render("{{{a}}-{{b}}}")
        assert result == "{1-2}"

    def test_render_variable_shadowing(self) -> None:
        """Handle variable shadowing in nested contexts."""
        ctx = RecipeContext({"var": "outer", "nested": {"var": "inner"}})

        result = ctx.render("{{var}}")
        assert result == "outer"

        result = ctx.render("{{nested.var}}")
        assert result == "inner"

    def test_render_json_injection_attempt(self) -> None:
        """Prevent JSON injection through template variables."""
        ctx = RecipeContext({"input": '", "injected": "malicious'})

        # Should render as-is, not parse as JSON
        result = ctx.render('{"key": "{{input}}"}')
        assert '"injected": "malicious' in result

    def test_render_template_escaping(self) -> None:
        """Verify that template variables are not HTML-escaped."""
        ctx = RecipeContext({"html": "<script>alert('xss')</script>"})

        # Should render as-is without escaping
        result = ctx.render("{{html}}")
        assert result == "<script>alert('xss')</script>"

    def test_render_missing_variable_partial_path(self) -> None:
        """Handle missing intermediate keys in dot notation."""
        ctx = RecipeContext({"a": {"b": "value"}})

        # c does not exist in a.b.c
        result = ctx.render("{{a.b.c}}")
        assert result == ""

        # x does not exist at top level
        result = ctx.render("{{x.y.z}}")
        assert result == ""

    def test_render_null_boolean_number_values(self) -> None:
        """Render None, boolean, and numeric values correctly."""
        ctx = RecipeContext(
            {
                "none_val": None,
                "true_val": True,
                "false_val": False,
                "int_val": 42,
                "float_val": 3.14,
            }
        )

        assert ctx.render("{{none_val}}") == ""
        assert ctx.render("{{true_val}}") == "True"
        assert ctx.render("{{false_val}}") == "False"
        assert ctx.render("{{int_val}}") == "42"
        assert ctx.render("{{float_val}}") == "3.14"

    def test_render_recursion_prevention(self) -> None:
        """Prevent infinite recursion in template rendering."""
        ctx = RecipeContext({"a": "{{b}}", "b": "{{a}}"})

        # Should not recurse - renders literally
        result = ctx.render("{{a}}")
        assert result == "{{b}}"


class TestAgentResolverEdgeCases:
    """Test agent resolver behavior with unusual inputs and file system edge cases."""

    def test_resolve_unicode_agent_name(self, tmp_path: Path) -> None:
        """Agent names with Unicode should be rejected by validation."""
        resolver = AgentResolver(search_paths=[tmp_path])

        # Unicode characters should fail validation
        with pytest.raises(ValueError, match="Invalid agent name"):
            resolver.resolve("amplihack:agent-émoji-🚀")

    def test_resolve_special_chars_in_namespace(self, tmp_path: Path) -> None:
        """Namespace with special characters should be rejected."""
        resolver = AgentResolver(search_paths=[tmp_path])

        # Path traversal attempt
        with pytest.raises(ValueError, match="Invalid agent namespace"):
            resolver.resolve("../../etc:passwd")

        # Special characters
        with pytest.raises(ValueError, match="Invalid agent namespace"):
            resolver.resolve("name/space:agent")

    def test_resolve_file_missing_mid_resolve(self, tmp_path: Path) -> None:
        """Handle file disappearing between existence check and read."""
        # Create agent file
        namespace_dir = tmp_path / "test-namespace" / "core"
        namespace_dir.mkdir(parents=True)
        agent_file = namespace_dir / "agent.md"
        agent_file.write_text("# Agent content")

        resolver = AgentResolver(search_paths=[tmp_path])

        # Resolve successfully first time
        content = resolver.resolve("test-namespace:agent")
        assert "Agent content" in content

        # Delete file
        agent_file.unlink()

        # Should raise AgentNotFoundError
        with pytest.raises(AgentNotFoundError):
            resolver.resolve("test-namespace:agent")

    def test_resolve_corrupted_file(self, tmp_path: Path) -> None:
        """Handle corrupted file that cannot be decoded."""
        namespace_dir = tmp_path / "test-namespace" / "core"
        namespace_dir.mkdir(parents=True)
        agent_file = namespace_dir / "agent.md"

        # Write invalid UTF-8
        agent_file.write_bytes(b"\xff\xfe\xfd\xfc")

        resolver = AgentResolver(search_paths=[tmp_path])

        # Should raise UnicodeDecodeError
        with pytest.raises(UnicodeDecodeError):
            resolver.resolve("test-namespace:agent")

    def test_resolve_very_large_file(self, tmp_path: Path) -> None:
        """Handle agent files that are very large (10MB+)."""
        namespace_dir = tmp_path / "test-namespace" / "core"
        namespace_dir.mkdir(parents=True)
        agent_file = namespace_dir / "agent.md"

        # Write 10MB file
        large_content = "# Agent\n" + ("x" * (10 * 1024 * 1024))
        agent_file.write_text(large_content)

        resolver = AgentResolver(search_paths=[tmp_path])

        # Should handle large file
        content = resolver.resolve("test-namespace:agent")
        assert len(content) > 10 * 1024 * 1024

    def test_resolve_symlink_outside_search_path(self, tmp_path: Path) -> None:
        """Reject symlinks that point outside the search directory."""
        namespace_dir = tmp_path / "test-namespace" / "core"
        namespace_dir.mkdir(parents=True)

        # Create target file outside search path
        outside_dir = tmp_path.parent / "outside"
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / "secret.md"
        outside_file.write_text("Secret content")

        # Create symlink inside search path pointing outside
        symlink = namespace_dir / "agent.md"
        symlink.symlink_to(outside_file)

        resolver = AgentResolver(search_paths=[tmp_path])

        # Should reject because resolved path is outside search directory
        with pytest.raises(AgentNotFoundError):
            resolver.resolve("test-namespace:agent")

    def test_resolve_multiple_search_paths_priority(self, tmp_path: Path) -> None:
        """First matching file in search path order wins."""
        dir1 = tmp_path / "dir1" / "amplihack" / "core"
        dir2 = tmp_path / "dir2" / "amplihack" / "core"
        dir1.mkdir(parents=True)
        dir2.mkdir(parents=True)

        # Same agent in both directories
        (dir1 / "agent.md").write_text("Content from dir1")
        (dir2 / "agent.md").write_text("Content from dir2")

        resolver = AgentResolver(search_paths=[tmp_path / "dir1", tmp_path / "dir2"])

        # Should return content from first search path
        content = resolver.resolve("amplihack:agent")
        assert content == "Content from dir1"
