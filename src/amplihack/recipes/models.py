"""Data models for the Recipe Runner module.

Defines the core data structures used throughout the recipe execution pipeline:
steps, recipes, results, and error types.
"""

from __future__ import annotations

import ast
import enum
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


class _ConditionEvaluationError(ValueError):
    """Raised when a recipe condition uses unsupported syntax or unknown values."""


def _resolve_attribute(value: Any, attribute: str) -> Any:
    """Resolve dotted access against dict-like or attribute-based objects."""
    if isinstance(value, Mapping):
        if attribute in value:
            return value[attribute]
        raise _ConditionEvaluationError(f"Unknown key '{attribute}' in condition")

    if hasattr(value, attribute):
        return getattr(value, attribute)

    raise _ConditionEvaluationError(f"Unknown attribute '{attribute}' in condition")


def _coerce_bool_string_compare(left: Any, right: Any) -> tuple[Any, Any]:
    """Allow bools to compare cleanly with workflow-style 'true'/'false' strings."""
    if isinstance(left, bool) and isinstance(right, str):
        return str(left).lower(), right.lower()
    if isinstance(right, bool) and isinstance(left, str):
        return left.lower(), str(right).lower()
    return left, right


def _evaluate_compare(operator: ast.cmpop, left: Any, right: Any) -> bool:
    """Evaluate a supported comparison operator."""
    if isinstance(operator, (ast.Eq, ast.NotEq)):
        left, right = _coerce_bool_string_compare(left, right)

    if isinstance(operator, ast.Eq):
        return left == right
    if isinstance(operator, ast.NotEq):
        return left != right
    if isinstance(operator, ast.Gt):
        return left > right
    if isinstance(operator, ast.GtE):
        return left >= right
    if isinstance(operator, ast.Lt):
        return left < right
    if isinstance(operator, ast.LtE):
        return left <= right
    if isinstance(operator, ast.In):
        return left in right
    if isinstance(operator, ast.NotIn):
        return left not in right
    if isinstance(operator, ast.Is):
        return left is right
    if isinstance(operator, ast.IsNot):
        return left is not right

    raise _ConditionEvaluationError(f"Unsupported comparison operator: {type(operator).__name__}")


def _evaluate_condition_ast(node: ast.AST, context: dict[str, Any]) -> Any:
    """Evaluate a restricted condition AST with fail-closed semantics."""
    if isinstance(node, ast.Expression):
        return _evaluate_condition_ast(node.body, context)

    if isinstance(node, ast.Name):
        if node.id in {"True", "False", "None"}:
            return {"True": True, "False": False, "None": None}[node.id]
        if node.id not in context:
            raise _ConditionEvaluationError(f"Unknown name '{node.id}' in condition")
        return context[node.id]

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Attribute):
        value = _evaluate_condition_ast(node.value, context)
        return _resolve_attribute(value, node.attr)

    if isinstance(node, ast.List):
        return [_evaluate_condition_ast(element, context) for element in node.elts]

    if isinstance(node, ast.Tuple):
        return tuple(_evaluate_condition_ast(element, context) for element in node.elts)

    if isinstance(node, ast.Set):
        return {_evaluate_condition_ast(element, context) for element in node.elts}

    if isinstance(node, ast.BoolOp):
        values = [_evaluate_condition_ast(value, context) for value in node.values]
        if isinstance(node.op, ast.And):
            return all(bool(value) for value in values)
        if isinstance(node.op, ast.Or):
            return any(bool(value) for value in values)
        raise _ConditionEvaluationError(f"Unsupported boolean operator: {type(node.op).__name__}")

    if isinstance(node, ast.UnaryOp):
        operand = _evaluate_condition_ast(node.operand, context)
        if isinstance(node.op, ast.Not):
            return not bool(operand)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        raise _ConditionEvaluationError(f"Unsupported unary operator: {type(node.op).__name__}")

    if isinstance(node, ast.Compare):
        left = _evaluate_condition_ast(node.left, context)
        for operator, comparator_node in zip(node.ops, node.comparators, strict=True):
            right = _evaluate_condition_ast(comparator_node, context)
            if not _evaluate_compare(operator, left, right):
                return False
            left = right
        return True

    raise _ConditionEvaluationError(f"Unsupported condition syntax: {type(node).__name__}")


class StepType(enum.Enum):
    """Type of recipe step."""

    BASH = "bash"
    AGENT = "agent"
    RECIPE = "recipe"


class StepStatus(enum.Enum):
    """Execution status of a recipe step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class Step:
    """A single step in a recipe."""

    id: str
    step_type: StepType
    command: str | None = None
    agent: str | None = None
    prompt: str | None = None
    output: str | None = None
    condition: str | None = None
    parse_json: bool = False
    mode: str | None = None
    working_dir: str | None = None
    timeout: int | None = None
    auto_stage: bool | None = None  # None = inherit from runner default
    recipe: str | None = None  # Sub-recipe name (for StepType.RECIPE)
    sub_context: dict[str, Any] | None = None  # Context to merge into sub-recipe

    def evaluate_condition(self, context: dict[str, Any]) -> bool:
        """Evaluate the step condition against a context dict.

        Returns True if the step should execute (condition is met or absent).
        Conditions use a strict, fail-closed expression subset:
        names, dotted attribute access, boolean operators, membership, and
        comparisons. Anything unsafe or malformed evaluates to False.
        """
        if not self.condition:
            return True

        try:
            parsed = ast.parse(self.condition.strip(), mode="eval")
            return bool(_evaluate_condition_ast(parsed, context))
        except (
            SyntaxError,
            TypeError,
            ValueError,
            AttributeError,
            KeyError,
            IndexError,
        ):
            return False


@dataclass
class Recipe:
    """A parsed recipe definition."""

    name: str
    steps: list[Step] = field(default_factory=list)
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    tags: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    """Result of executing a single step."""

    step_id: str
    status: StepStatus
    output: str = ""
    error: str = ""

    def __str__(self) -> str:
        """Return a human-readable summary of the step result."""
        line = f"[{self.status.value:>9}] {self.step_id}"
        if self.error:
            line += f" -- error: {self.error}"
        return line


@dataclass
class RecipeResult:
    """Result of executing an entire recipe.

    Use attribute access for structured data:
        result.success, result.step_results, result.context

    Use str(result) for a human-readable summary (also enables safe
    string slicing like ``str(result)[:500]``).
    """

    recipe_name: str
    success: bool
    step_results: list[StepResult] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    log_path: str | None = None

    @property
    def output(self) -> str:
        """Aggregate output from all completed steps as a single string.

        Useful for callers that need a string summary of the recipe execution
        (e.g. for logging, truncation with ``result.output[:500]``, etc.).
        """
        parts = []
        for sr in self.step_results:
            if sr.output:
                parts.append(sr.output)
            elif sr.error:
                parts.append(f"[{sr.step_id} error] {sr.error}")
        return "\n".join(parts)

    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        step_count = len(self.step_results)
        base = f"RecipeResult({self.recipe_name}: {status}, {step_count} steps)"
        if self.step_results:
            step_lines = "\n  ".join(str(sr) for sr in self.step_results)
            return f"{base}\n  {step_lines}"
        return base

    def __getitem__(self, key: int | slice) -> str:
        """Support subscripting (e.g. ``result[:500]``) by delegating to ``.output``."""
        return self.output[key]


class StepExecutionError(Exception):
    """Raised when a step fails to execute."""

    def __init__(self, step_id: str, message: str) -> None:
        self.step_id = step_id
        super().__init__(f"Step '{step_id}' failed: {message}")
