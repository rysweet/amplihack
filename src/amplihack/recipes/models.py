"""Data models for the Recipe Runner module.

Defines the core data structures used throughout the recipe execution pipeline:
steps, recipes, results, and error types.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


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
        return f"RecipeResult({self.recipe_name}: {status}, {step_count} steps)"

    def __getitem__(self, key: int | slice) -> str:
        """Support subscripting (e.g. ``result[:500]``) by delegating to ``.output``."""
        return self.output[key]


class StepExecutionError(Exception):
    """Raised when a step fails to execute."""

    def __init__(self, step_id: str, message: str) -> None:
        self.step_id = step_id
        super().__init__(f"Step '{step_id}' failed: {message}")
