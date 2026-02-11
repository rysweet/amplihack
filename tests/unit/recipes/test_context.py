"""Tests for RecipeContext.

These tests verify that RecipeContext can:
- Store and retrieve values with simple and dot-notation keys
- Render Jinja2-style template strings with variable substitution
- Handle missing variables gracefully (render as empty string)
- Serialize dict values to JSON when rendering templates
- Evaluate safe conditional expressions for step conditions
- Reject dangerous expressions (function calls, imports)
"""

from __future__ import annotations

import pytest

from amplihack.recipes.context import RecipeContext


class TestContextGetSet:
    """Test basic key-value storage and retrieval."""

    def test_get_simple_key(self) -> None:
        """Get a top-level key returns the stored value."""
        ctx = RecipeContext({"greeting": "hello"})
        assert ctx.get("greeting") == "hello"

    def test_get_dot_notation(self) -> None:
        """Get a nested key using dot notation like 'a.b.c'."""
        ctx = RecipeContext({"a": {"b": {"c": "deep_value"}}})
        assert ctx.get("a.b.c") == "deep_value"

    def test_get_missing_returns_none(self) -> None:
        """Getting a key that does not exist returns None."""
        ctx = RecipeContext({"existing": "value"})
        assert ctx.get("nonexistent") is None

    def test_set_and_get(self) -> None:
        """Set a key then get it back."""
        ctx = RecipeContext({})
        ctx.set("new_key", "new_value")
        assert ctx.get("new_key") == "new_value"


class TestContextRender:
    """Test template rendering with variable substitution."""

    def test_render_simple_template(self) -> None:
        """Render '{{name}}' with name='hello' produces 'hello'."""
        ctx = RecipeContext({"name": "hello"})
        result = ctx.render("{{name}}")
        assert result == "hello"

    def test_render_dot_notation(self) -> None:
        """Render '{{obj.key}}' with nested dict resolves correctly."""
        ctx = RecipeContext({"obj": {"key": "nested_value"}})
        result = ctx.render("{{obj.key}}")
        assert result == "nested_value"

    def test_render_missing_variable_empty_string(self) -> None:
        """A template variable that does not exist renders as empty string."""
        ctx = RecipeContext({"existing": "value"})
        result = ctx.render("prefix-{{missing}}-suffix")
        assert result == "prefix--suffix"

    def test_render_dict_as_json(self) -> None:
        """When a variable holds a dict, it is serialized as JSON in the output."""
        ctx = RecipeContext({"data": {"key": "value", "num": 42}})
        result = ctx.render("{{data}}")
        # The rendered output should be valid JSON containing the dict
        assert '"key"' in result

    def test_render_list_as_json(self) -> None:
        """When a variable holds a list, it is serialized as JSON (not Python repr)."""
        ctx = RecipeContext({"items": ["one", "two", "three"]})
        result = ctx.render("{{items}}")
        assert result.startswith("[")  # JSON array
        assert '"one"' in result  # JSON uses double quotes
        assert "'" not in result  # Not Python repr with single quotes


class TestContextEvaluate:
    """Test safe expression evaluation for step conditions."""

    def test_evaluate_simple_equality(self) -> None:
        """'x == \"yes\"' returns True when x is 'yes'."""
        ctx = RecipeContext({"x": "yes"})
        assert ctx.evaluate('x == "yes"') is True

    def test_evaluate_simple_equality_false(self) -> None:
        """'x == \"yes\"' returns False when x is 'no'."""
        ctx = RecipeContext({"x": "no"})
        assert ctx.evaluate('x == "yes"') is False

    def test_evaluate_boolean_and(self) -> None:
        """'a and b' returns True when both are truthy."""
        ctx = RecipeContext({"a": "truthy", "b": "also_truthy"})
        assert ctx.evaluate("a and b") is True

    def test_evaluate_boolean_and_false(self) -> None:
        """'a and b' returns False when one is falsy (empty string)."""
        ctx = RecipeContext({"a": "truthy", "b": ""})
        assert ctx.evaluate("a and b") is False

    def test_evaluate_in_operator(self) -> None:
        """'\"hello\" in greeting' returns True when greeting contains 'hello'."""
        ctx = RecipeContext({"greeting": "hello world"})
        assert ctx.evaluate('"hello" in greeting') is True

    def test_evaluate_dot_notation(self) -> None:
        """'obj.flag == \"true\"' evaluates correctly with nested context."""
        ctx = RecipeContext({"obj": {"flag": "true"}})
        assert ctx.evaluate('obj.flag == "true"') is True


class TestContextRenderShell:
    """Test shell-safe template rendering."""

    def test_render_shell_quotes_metacharacters(self) -> None:
        """Shell metacharacters in values are quoted by shlex.quote."""
        ctx = RecipeContext({"cmd": "rm -rf /; echo pwned"})
        rendered = ctx.render_shell("echo {{cmd}}")
        # shlex.quote wraps dangerous values in single quotes
        assert ";" not in rendered or rendered.count("'") >= 2
        assert "rm -rf" in rendered  # value present but safely quoted

    def test_render_shell_safe_value_unchanged(self) -> None:
        """Simple safe values pass through without extra quoting."""
        ctx = RecipeContext({"name": "hello"})
        rendered = ctx.render_shell("echo {{name}}")
        assert "hello" in rendered


class TestContextEvaluateSecurity:
    """Test that dangerous expressions are rejected."""

    def test_evaluate_rejects_function_calls(self) -> None:
        """Expressions containing function calls like os.system() raise ValueError."""
        ctx = RecipeContext({})
        with pytest.raises(ValueError, match="(?i)(unsafe|forbidden|not allowed|invalid)"):
            ctx.evaluate('os.system("rm -rf /")')

    def test_evaluate_rejects_imports(self) -> None:
        """Expressions containing __import__ raise ValueError."""
        ctx = RecipeContext({})
        with pytest.raises(ValueError, match="(?i)(unsafe|forbidden|not allowed|invalid)"):
            ctx.evaluate('__import__("os")')

    def test_evaluate_rejects_dunder_access(self) -> None:
        """Expressions accessing dunder attributes are rejected."""
        ctx = RecipeContext({"x": "hello"})
        with pytest.raises(ValueError, match="(?i)(unsafe|forbidden|not allowed|invalid)"):
            ctx.evaluate("x.__class__.__bases__")
