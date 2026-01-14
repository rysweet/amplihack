"""
Data models for Goal Agent Generator.

Defines type-safe structures for goals, plans, skills, and agent bundles.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


@dataclass
class GoalDefinition:
    """User's goal extracted from natural language prompt."""

    raw_prompt: str
    goal: str  # Primary objective
    domain: str  # e.g., "data-processing", "security-analysis", "automation"
    constraints: list[str] = field(default_factory=list)  # Technical constraints
    success_criteria: list[str] = field(default_factory=list)  # How to measure success
    context: dict[str, Any] = field(default_factory=dict)  # Additional context
    complexity: Literal["simple", "moderate", "complex"] = "moderate"

    def __post_init__(self):
        """Validate goal definition."""
        if not self.raw_prompt.strip():
            raise ValueError("Raw prompt cannot be empty")
        if not self.goal.strip():
            raise ValueError("Goal must be specified")
        if not self.domain.strip():
            raise ValueError("Domain must be specified")


@dataclass
class PlanPhase:
    """Single phase in execution plan."""

    name: str
    description: str
    required_capabilities: list[str]
    estimated_duration: str  # e.g., "5 minutes", "1 hour"
    dependencies: list[str] = field(default_factory=list)  # Names of prerequisite phases
    parallel_safe: bool = True  # Can execute in parallel with others
    success_indicators: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate phase definition."""
        if not self.name:
            raise ValueError("Phase must have a name")
        if not self.required_capabilities:
            raise ValueError(f"Phase {self.name} must specify required capabilities")


@dataclass
class ExecutionPlan:
    """Multi-phase execution plan for achieving goal."""

    goal_id: uuid.UUID
    phases: list[PlanPhase]
    total_estimated_duration: str
    required_skills: list[str] = field(default_factory=list)  # Skill names needed
    parallel_opportunities: list[list[str]] = field(
        default_factory=list
    )  # Groups of phases that can run in parallel
    risk_factors: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate execution plan."""
        if not self.phases:
            raise ValueError("Plan must have at least one phase")
        if len(self.phases) > 10:
            raise ValueError("Plan should have 3-5 phases for MVP (max 10)")

    @property
    def phase_count(self) -> int:
        """Number of phases in plan."""
        return len(self.phases)


@dataclass
class SkillDefinition:
    """Definition of a skill (copied from existing skills for MVP)."""

    name: str
    source_path: Path  # Path to original skill file
    capabilities: list[str]
    description: str
    content: str  # Full skill markdown content
    dependencies: list[str] = field(default_factory=list)  # Other skills needed
    match_score: float = 0.0  # How well this matches the need (0-1)

    def __post_init__(self):
        """Validate skill definition."""
        if not self.name:
            raise ValueError("Skill must have a name")
        if not self.content:
            raise ValueError(f"Skill {self.name} must have content")
        if not 0 <= self.match_score <= 1:
            raise ValueError(f"Match score must be 0-1, got {self.match_score}")


@dataclass
class GoalAgentBundle:
    """Complete bundle for a goal-seeking agent."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    version: str = "1.0.0"
    goal_definition: GoalDefinition | None = None
    execution_plan: ExecutionPlan | None = None
    skills: list[SkillDefinition] = field(default_factory=list)
    auto_mode_config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    status: Literal["pending", "planning", "assembling", "ready", "failed"] = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate bundle."""
        if not self.name:
            raise ValueError("Bundle must have a name")
        if len(self.name) < 3 or len(self.name) > 50:
            raise ValueError("Bundle name must be 3-50 characters")

    @property
    def skill_count(self) -> int:
        """Number of skills in bundle."""
        return len(self.skills)

    @property
    def is_complete(self) -> bool:
        """Check if bundle has all required components."""
        return bool(
            self.goal_definition and self.execution_plan and self.skills and self.auto_mode_config
        )


@dataclass
class GenerationMetrics:
    """Metrics for goal agent generation."""

    total_time_seconds: float = 0.0
    analysis_time: float = 0.0
    planning_time: float = 0.0
    synthesis_time: float = 0.0
    assembly_time: float = 0.0
    skill_count: int = 0
    phase_count: int = 0
    bundle_size_kb: float = 0.0

    @property
    def average_phase_time(self) -> float:
        """Average time per phase."""
        if self.phase_count == 0:
            return 0.0
        return (self.planning_time + self.synthesis_time) / self.phase_count
