"""
Data models for Goal Agent Generator.

Defines type-safe structures for goals, plans, skills, and agent bundles.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional


@dataclass
class GoalDefinition:
    """User's goal extracted from natural language prompt."""

    raw_prompt: str
    goal: str  # Primary objective
    domain: str  # e.g., "data-processing", "security-analysis", "automation"
    constraints: List[str] = field(default_factory=list)  # Technical constraints
    success_criteria: List[str] = field(default_factory=list)  # How to measure success
    context: Dict[str, Any] = field(default_factory=dict)  # Additional context
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
    required_capabilities: List[str]
    estimated_duration: str  # e.g., "5 minutes", "1 hour"
    dependencies: List[str] = field(default_factory=list)  # Names of prerequisite phases
    parallel_safe: bool = True  # Can execute in parallel with others
    success_indicators: List[str] = field(default_factory=list)

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
    phases: List[PlanPhase]
    total_estimated_duration: str
    required_skills: List[str] = field(default_factory=list)  # Skill names needed
    parallel_opportunities: List[List[str]] = field(
        default_factory=list
    )  # Groups of phases that can run in parallel
    risk_factors: List[str] = field(default_factory=list)
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
    capabilities: List[str]
    description: str
    content: str  # Full skill markdown content
    dependencies: List[str] = field(default_factory=list)  # Other skills needed
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
    goal_definition: Optional[GoalDefinition] = None
    execution_plan: Optional[ExecutionPlan] = None
    skills: List[SkillDefinition] = field(default_factory=list)
    auto_mode_config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
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


# Phase 2: AI-Powered Custom Skill Generation Models


@dataclass
class ValidationResult:
    """Result of skill validation."""

    passed: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    quality_score: float = 0.0  # 0-1

    def __post_init__(self):
        """Validate result."""
        if not 0 <= self.quality_score <= 1:
            raise ValueError(f"Quality score must be 0-1, got {self.quality_score}")


@dataclass
class GeneratedSkillDefinition(SkillDefinition):
    """Skill generated by AI."""

    generation_prompt: str = ""
    generation_model: str = ""
    validation_result: Optional[ValidationResult] = None
    provenance: Literal["ai_generated"] = "ai_generated"
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate generated skill definition."""
        # Call parent validation
        super().__post_init__()
        if not self.generation_model:
            raise ValueError("Generated skill must specify generation_model")


@dataclass
class SkillGapReport:
    """Analysis of missing capabilities."""

    execution_plan_id: uuid.UUID
    coverage_percentage: float  # 0-100
    missing_capabilities: List[str]
    gaps_by_phase: Dict[str, List[str]]
    criticality_ranking: List[tuple[str, float]]
    recommendation: Literal["use_existing", "generate_custom", "mixed"]

    def __post_init__(self):
        """Validate gap report."""
        if not 0 <= self.coverage_percentage <= 100:
            raise ValueError(f"Coverage must be 0-100, got {self.coverage_percentage}")
        if not self.recommendation:
            raise ValueError("Recommendation must be specified")


# Phase 3: Multi-Agent Coordination Models


@dataclass
class CoordinationStrategy:
    """Strategy for coordinating multiple agents to achieve a complex goal."""

    coordination_type: Literal["single", "multi_parallel", "multi_sequential", "hybrid"]
    agent_count: int
    agent_groupings: List[List[str]] = field(
        default_factory=list
    )  # Lists of phase names per agent
    coordination_overhead: float = 0.0  # 0-1, cost of coordination
    parallelization_benefit: float = 0.0  # 0-1, benefit from parallelization
    recommendation_reason: str = ""

    def __post_init__(self):
        """Validate coordination strategy."""
        if self.agent_count < 1:
            raise ValueError(f"Agent count must be >= 1, got {self.agent_count}")
        if not 0 <= self.coordination_overhead <= 1:
            raise ValueError(
                f"Coordination overhead must be 0-1, got {self.coordination_overhead}"
            )
        if not 0 <= self.parallelization_benefit <= 1:
            raise ValueError(
                f"Parallelization benefit must be 0-1, got {self.parallelization_benefit}"
            )
        if self.coordination_type != "single" and not self.recommendation_reason:
            raise ValueError("Multi-agent strategies must include recommendation reason")


@dataclass
class SubAgentDefinition:
    """Definition of a sub-agent in a multi-agent coordination."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    role: Literal["leader", "worker", "monitor"] = "worker"
    goal_definition: Optional[GoalDefinition] = None
    execution_plan: Optional[ExecutionPlan] = None
    skills: List[SkillDefinition] = field(default_factory=list)
    dependencies: List[uuid.UUID] = field(default_factory=list)  # Other agent IDs
    shared_state_keys: List[str] = field(default_factory=list)  # State keys to access
    coordination_protocol: str = "v1"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate sub-agent definition."""
        if not self.name:
            raise ValueError("Sub-agent must have a name")
        if not self.coordination_protocol:
            raise ValueError("Sub-agent must specify coordination protocol")


@dataclass
class CoordinationMessage:
    """Message passed between coordinated agents."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    from_agent: uuid.UUID = field(default_factory=uuid.uuid4)
    to_agent: Optional[uuid.UUID] = None  # None = broadcast
    message_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    protocol_version: str = "v1"

    def __post_init__(self):
        """Validate coordination message."""
        if not self.message_type:
            raise ValueError("Message must have a type")
        if not self.protocol_version:
            raise ValueError("Message must specify protocol version")


@dataclass
class AgentDependencyGraph:
    """Dependency graph for multi-agent execution."""

    nodes: Dict[uuid.UUID, SubAgentDefinition] = field(default_factory=dict)
    edges: Dict[uuid.UUID, List[uuid.UUID]] = field(
        default_factory=dict
    )  # agent_id -> list of dependency agent_ids
    execution_order: List[List[uuid.UUID]] = field(
        default_factory=list
    )  # Topologically sorted layers

    def __post_init__(self):
        """Validate dependency graph."""
        # Ensure all edges reference valid nodes
        for agent_id, deps in self.edges.items():
            if agent_id not in self.nodes:
                raise ValueError(f"Edge references non-existent agent: {agent_id}")
            for dep_id in deps:
                if dep_id not in self.nodes:
                    raise ValueError(f"Dependency references non-existent agent: {dep_id}")


@dataclass
class SharedState:
    """Shared state between coordinated agents."""

    key: str = ""
    value: Any = None
    owner_agent_id: Optional[uuid.UUID] = None
    readers: List[uuid.UUID] = field(default_factory=list)
    writers: List[uuid.UUID] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1

    def __post_init__(self):
        """Validate shared state."""
        if not self.key:
            raise ValueError("Shared state must have a key")
        if self.version < 1:
            raise ValueError(f"Version must be >= 1, got {self.version}")


# Phase 4: Learning and Adaptation from Execution History Models


@dataclass
class ExecutionEvent:
    """Single event during agent execution."""

    timestamp: datetime
    event_type: str
    phase_name: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None

    def __post_init__(self):
        """Validate event."""
        if not self.event_type:
            raise ValueError("Event must have a type")


@dataclass
class ExecutionTrace:
    """Complete execution trace for an agent."""

    execution_id: uuid.UUID = field(default_factory=uuid.uuid4)
    agent_bundle_id: uuid.UUID = field(default_factory=uuid.uuid4)
    goal_definition: Optional[GoalDefinition] = None
    execution_plan: Optional[ExecutionPlan] = None
    events: List[ExecutionEvent] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    status: Literal["running", "completed", "failed", "recovered"] = "running"
    final_result: Optional[str] = None

    def __post_init__(self):
        """Validate trace."""
        if self.end_time and self.end_time < self.start_time:
            raise ValueError("End time cannot be before start time")

    @property
    def duration_seconds(self) -> Optional[float]:
        """Total execution duration in seconds."""
        if not self.end_time:
            return None
        return (self.end_time - self.start_time).total_seconds()

    @property
    def is_complete(self) -> bool:
        """Check if execution is complete."""
        return self.status in ["completed", "failed", "recovered"]


@dataclass
class PhaseMetrics:
    """Metrics for a single phase execution."""

    phase_name: str
    estimated_duration: float  # seconds
    actual_duration: float  # seconds
    accuracy_ratio: float  # actual/estimated
    success: bool
    error_message: Optional[str] = None
    retry_count: int = 0

    def __post_init__(self):
        """Validate phase metrics."""
        if not self.phase_name:
            raise ValueError("Phase name required")
        if self.actual_duration < 0:
            raise ValueError("Duration cannot be negative")

    @property
    def duration_delta(self) -> float:
        """Difference between actual and estimated."""
        return self.actual_duration - self.estimated_duration


@dataclass
class ExecutionMetrics:
    """Aggregated metrics for an execution."""

    execution_id: uuid.UUID
    total_duration_seconds: float
    phase_metrics: Dict[str, PhaseMetrics]
    success_rate: float  # 0-1
    error_count: int
    tool_usage: Dict[str, int] = field(default_factory=dict)
    api_calls: int = 0
    tokens_used: int = 0

    def __post_init__(self):
        """Validate execution metrics."""
        if not 0 <= self.success_rate <= 1:
            raise ValueError(f"Success rate must be 0-1, got {self.success_rate}")
        if self.error_count < 0:
            raise ValueError("Error count cannot be negative")

    @property
    def average_accuracy_ratio(self) -> float:
        """Average estimation accuracy across phases."""
        if not self.phase_metrics:
            return 1.0
        return sum(m.accuracy_ratio for m in self.phase_metrics.values()) / len(self.phase_metrics)


@dataclass
class PerformanceInsights:
    """Insights from analyzing execution history."""

    goal_domain: str
    sample_size: int
    insights: List[str]
    recommendations: List[str]
    confidence_score: float  # 0-1
    slow_phases: List[tuple[str, float]]  # (phase_name, avg_duration)
    common_errors: List[tuple[str, int]]  # (error_message, count)
    optimal_phase_order: List[str]

    def __post_init__(self):
        """Validate insights."""
        if not 0 <= self.confidence_score <= 1:
            raise ValueError(f"Confidence must be 0-1, got {self.confidence_score}")
        if self.sample_size < 0:
            raise ValueError("Sample size cannot be negative")

    @property
    def has_sufficient_data(self) -> bool:
        """Check if sample size is sufficient for reliable insights."""
        return self.sample_size >= 10


@dataclass
class AdaptedExecutionPlan(ExecutionPlan):
    """Execution plan modified based on learning."""

    original_plan_id: uuid.UUID = field(default_factory=uuid.uuid4)
    adaptations: List[str] = field(default_factory=list)
    expected_improvement: float = 0.0  # percentage
    confidence: float = 0.0  # 0-1
    adapted_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate adapted plan."""
        # Call parent validation
        super().__post_init__()
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be 0-1, got {self.confidence}")

    @property
    def adaptation_count(self) -> int:
        """Number of adaptations made."""
        return len(self.adaptations)


@dataclass
class RecoveryStrategy:
    """Strategy for recovering from execution failure."""

    strategy_type: Literal["retry", "skip", "simplify", "escalate"]
    phase_name: str
    reason: str
    actions: List[str]
    confidence: float  # 0-1
    estimated_cost: float  # seconds

    def __post_init__(self):
        """Validate recovery strategy."""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be 0-1, got {self.confidence}")
        if self.estimated_cost < 0:
            raise ValueError("Cost cannot be negative")


# Update Agent Models


@dataclass
class AgentVersionInfo:
    """Information about an installed agent version."""

    agent_dir: Path
    agent_name: str
    version: str
    infrastructure_phase: Literal["phase1", "phase2", "phase3", "phase4"]
    installed_skills: List[str]
    custom_files: List[Path]
    last_updated: Optional[datetime] = None

    def __post_init__(self):
        """Validate version info."""
        if not self.agent_dir.exists():
            raise ValueError(f"Agent directory does not exist: {self.agent_dir}")
        if not self.agent_name:
            raise ValueError("Agent name required")
        if not self.version:
            raise ValueError("Version required")


@dataclass
class FileChange:
    """A file change in an update."""

    file_path: Path
    change_type: Literal["add", "modify", "delete"]
    category: Literal["infrastructure", "custom", "skill"]
    diff: Optional[str] = None
    safety: Literal["safe", "review", "breaking"] = "safe"

    def __post_init__(self):
        """Validate file change."""
        if not str(self.file_path):
            raise ValueError("File path required")


@dataclass
class SkillUpdate:
    """Update information for a skill."""

    skill_name: str
    current_version: Optional[str] = None
    new_version: str = ""
    change_type: Literal["new", "update", "deprecated"] = "new"
    changes: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate skill update."""
        if not self.skill_name:
            raise ValueError("Skill name required")
        if not self.new_version:
            raise ValueError("New version required")


@dataclass
class UpdateChangeset:
    """Set of changes for updating an agent."""

    current_version: str
    target_version: str
    infrastructure_updates: List[FileChange]
    skill_updates: List[SkillUpdate]
    breaking_changes: List[str]
    bug_fixes: List[str]
    enhancements: List[str]
    total_changes: int
    estimated_time: str

    def __post_init__(self):
        """Validate changeset."""
        if not self.current_version:
            raise ValueError("Current version required")
        if not self.target_version:
            raise ValueError("Target version required")
        if self.total_changes < 0:
            raise ValueError("Total changes cannot be negative")

    @property
    def has_breaking_changes(self) -> bool:
        """Check if changeset contains breaking changes."""
        return len(self.breaking_changes) > 0

    @property
    def safe_auto_apply(self) -> bool:
        """Check if changeset is safe for automatic application."""
        return not self.has_breaking_changes and all(
            fc.safety == "safe" for fc in self.infrastructure_updates
        )
