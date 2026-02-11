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
    timeout: int = 120


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


@dataclass
class RecipeResult:
    """Result of executing an entire recipe."""

    recipe_name: str
    success: bool
    step_results: list[StepResult] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


class StepExecutionError(Exception):
    """Raised when a step fails to execute."""

    def __init__(self, step_id: str, message: str) -> None:
        self.step_id = step_id
        super().__init__(f"Step '{step_id}' failed: {message}")
