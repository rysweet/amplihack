"""Recipe execution context with template rendering and safe expression evaluation.

Provides variable storage, dot-notation access, Mustache-style template rendering,
and AST-based safe condition evaluation (whitelist-validated before eval).
"""

from __future__ import annotations

import ast
import builtins as _builtins_module
import copy
import json
import re
import shlex
from typing import Any

_TEMPLATE_RE = re.compile(r"\{\{([a-zA-Z0-9_.\-]+)\}\}")

# AST node types allowed in condition expressions
_SAFE_NODES = (
    ast.Expression,
    ast.Compare,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Name,
    ast.Attribute,
    ast.Constant,
    ast.Load,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Subscript,
    ast.Index,  # Still present in 3.11+ for backward compat, harmless to whitelist
    ast.Call,  # Allowed but restricted to safe functions (see _SAFE_CALL_NAMES)
    ast.keyword,  # Required for keyword arguments in calls
)

# Functions allowed in Call nodes. Only pure type-coercion and string helpers.
_SAFE_CALL_NAMES = frozenset({"int", "str", "len", "bool", "float", "min", "max"})

# Methods allowed on objects (e.g. value.strip()). Only side-effect-free string methods.
_SAFE_METHOD_NAMES = frozenset({
    "strip", "lstrip", "rstrip", "lower", "upper", "title",
    "startswith", "endswith", "replace", "split", "join", "count", "find",
})


class _SafeNodeVisitor(ast.NodeVisitor):
    """Visits every node in an AST and rejects anything outside the whitelist."""

    def generic_visit(self, node: ast.AST) -> None:
        if not isinstance(node, _SAFE_NODES):
            raise ValueError(f"Unsafe expression: node type '{type(node).__name__}' is not allowed")
        super().generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Validate that Call nodes only invoke safe functions."""
        if isinstance(node.func, ast.Name):
            # Direct call: int(...), str(...), len(...)
            if node.func.id not in _SAFE_CALL_NAMES:
                raise ValueError(
                    f"Unsafe function call: '{node.func.id}' is not allowed. "
                    f"Safe functions: {sorted(_SAFE_CALL_NAMES)}"
                )
        elif isinstance(node.func, ast.Attribute):
            # Method call: value.strip(), s.lower()
            if node.func.attr not in _SAFE_METHOD_NAMES:
                raise ValueError(
                    f"Unsafe method call: '.{node.func.attr}()' is not allowed. "
                    f"Safe methods: {sorted(_SAFE_METHOD_NAMES)}"
                )
        else:
            raise ValueError("Unsafe expression: only named function/method calls are allowed")
        # Continue visiting child nodes
        self.generic_visit(node)


class RecipeContext:
    """Mutable context that accumulates step outputs and renders templates.

    Supports:
    - Dot-notation key access for nested dicts (e.g. ``a.b.c``)
    - ``{{var}}`` template rendering with JSON serialization for dicts
    - AST-based safe condition evaluation (whitelist-validated before eval)
    """

    def __init__(self, initial_context: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = copy.deepcopy(initial_context or {})

    def get(self, key: str) -> Any:
        """Retrieve a value by key, supporting dot notation for nested access.

        Args:
            key: Simple key or dot-separated path (e.g. ``"a.b.c"``).

        Returns:
            The value, or ``None`` if any segment is missing.
        """
        parts = key.split(".")
        current: Any = self._data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def set(self, key: str, value: Any) -> None:
        """Store a value at the top level of the context."""
        self._data[key] = value

    def render(self, template: str) -> str:
        """Replace ``{{var}}`` placeholders with context values.

        - Dict values are serialized to JSON.
        - Missing variables are replaced with empty string.

        Args:
            template: String containing ``{{variable}}`` placeholders.

        Returns:
            The rendered string.
        """

        def _replacer(match: re.Match) -> str:
            var_name = match.group(1)
            value = self.get(var_name)
            if value is None:
                return ""
            if isinstance(value, (dict, list)):
                return json.dumps(value)
            return str(value)

        return _TEMPLATE_RE.sub(_replacer, template)

    def render_shell(self, template: str) -> str:
        """Replace ``{{var}}`` placeholders with shell-escaped context values.

        Identical to :meth:`render` except every substituted value is passed
        through ``shlex.quote()`` to prevent shell injection when the rendered
        string is executed as a shell command.

        Args:
            template: String containing ``{{variable}}`` placeholders.

        Returns:
            The rendered string with all values shell-escaped.
        """

        def _shell_replacer(match: re.Match) -> str:
            var_name = match.group(1)
            value = self.get(var_name)
            if value is None:
                return shlex.quote("")
            if isinstance(value, (dict, list)):
                return shlex.quote(json.dumps(value))
            return shlex.quote(str(value))

        return _TEMPLATE_RE.sub(_shell_replacer, template)

    def evaluate(self, condition: str) -> bool:
        """Safely evaluate a boolean condition against the current context.

        Uses ``ast.parse`` with a strict node whitelist. Never calls ``eval()``
        on untrusted input directly -- instead compiles a validated AST.

        Args:
            condition: A Python-like boolean expression string.

        Returns:
            The boolean result of the expression.

        Raises:
            ValueError: If the expression contains unsafe nodes (function calls,
                imports, dunder access, etc.).
        """
        # Reject dunder access early -- check both the raw source and ALL
        # escape-sequence evasions that could resolve to underscores.
        if "__" in condition:
            raise ValueError("Unsafe expression: dunder attribute access is not allowed")

        # Block ALL backslash escape sequences except safe whitespace chars.
        # This catches \x5f, \u005f, \U0000005f, \137 (octal), and any other
        # encoding of underscore or dangerous characters.
        # Safe escapes: \n \r \t \f \b \v (whitespace only)
        if re.search(r"\\[^nrtfbv\s]", condition):
            raise ValueError("Unsafe expression: escape sequences not allowed (except whitespace)")

        try:
            tree = ast.parse(condition, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Invalid expression syntax: {exc}") from exc

        _SafeNodeVisitor().visit(tree)

        # Build a flattened namespace from the context for evaluation
        namespace = self._build_namespace()

        # Provide safe builtins that condition expressions may call
        safe_builtins = {
            name: getattr(_builtins_module, name)
            for name in _SAFE_CALL_NAMES
            if hasattr(_builtins_module, name)
        }

        # Prevent context variables from shadowing safe builtins
        for name in _SAFE_CALL_NAMES:
            namespace.pop(name, None)

        code = compile(tree, "<condition>", "eval")
        return bool(eval(code, {"__builtins__": safe_builtins}, namespace))

    def to_dict(self) -> dict[str, Any]:
        """Return a deep copy of the context data."""
        return copy.deepcopy(self._data)

    def _build_namespace(self) -> dict[str, Any]:
        """Build a flattened namespace from context for condition evaluation.

        Top-level keys are included directly. Nested dicts are also exposed
        as dot-separated keys using a simple namespace object so that
        ``obj.flag`` works in expressions.

        String values are stripped of trailing whitespace as defense-in-depth
        against bash step outputs that include a trailing newline (issue #3058).
        Bash commands always append a newline; without stripping, comparisons
        like ``count != 1`` silently fail because the value is ``"1\\n"``.
        """
        namespace: dict[str, Any] = {}
        for key, value in self._data.items():
            if isinstance(value, dict):
                namespace[key] = _DotDict(value)
            elif isinstance(value, str):
                # Strip trailing whitespace: bash stdout always ends with "\n"
                namespace[key] = value.rstrip()
            else:
                namespace[key] = value
        return namespace


class _DotDict:
    """Minimal wrapper that allows attribute-style access on a dict.

    Used so that conditions like ``obj.flag == "true"`` work naturally.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        for k, v in data.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict):
                setattr(self, k, _DotDict(v))
            else:
                setattr(self, k, v)

    def __contains__(self, item: Any) -> bool:
        return item in self.__dict__

    def __repr__(self) -> str:
        return repr(self.__dict__)
