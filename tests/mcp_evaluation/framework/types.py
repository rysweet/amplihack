"""Core type definitions for MCP evaluation framework.

This module defines all data structures used throughout the evaluation system.
Each type represents a clear concept with well-defined boundaries.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ScenarioCategory(Enum):
    """Categories of test scenarios."""

    NAVIGATION = "NAVIGATION"
    ANALYSIS = "ANALYSIS"
    MODIFICATION = "MODIFICATION"


class ExpectedImprovement(Enum):
    """Expected improvement types for tool capabilities."""

    FASTER = "faster"
    MORE_ACCURATE = "more_accurate"
    BOTH = "both"


class ComparisonMode(Enum):
    """Modes for comparing baseline vs enhanced execution."""

    WITH_VS_WITHOUT = "with_vs_without"
    BEFORE_VS_AFTER = "before_vs_after"


class FallbackBehavior(Enum):
    """Behavior when tool is unavailable."""

    FAIL = "fail"
    SKIP = "skip"
    BASELINE = "baseline"


@dataclass
class ToolCapability:
    """A single capability an MCP tool provides."""

    id: str
    name: str
    description: str
    relevant_scenarios: list[ScenarioCategory]
    expected_improvement: ExpectedImprovement
    mcp_commands: list[str]

    def __post_init__(self):
        """Convert string enums to enum types if needed."""
        self.relevant_scenarios = [
            ScenarioCategory(s) if isinstance(s, str) else s for s in self.relevant_scenarios
        ]
        if isinstance(self.expected_improvement, str):
            self.expected_improvement = ExpectedImprovement(self.expected_improvement)


@dataclass
class ToolConfiguration:
    """Configuration for a specific MCP tool."""

    # Required fields
    tool_id: str
    tool_name: str
    version: str
    description: str
    capabilities: list[ToolCapability]
    adapter_class: str
    setup_required: bool
    setup_instructions: str
    expected_advantages: dict[ScenarioCategory, list[str]]
    baseline_comparison_mode: ComparisonMode

    # Optional fields
    health_check_url: str | None = None
    environment_variables: dict[str, str] = field(default_factory=dict)
    max_concurrent_calls: int | None = None
    timeout_seconds: int = 30
    fallback_behavior: FallbackBehavior = FallbackBehavior.BASELINE

    def __post_init__(self):
        """Convert string values to proper types."""
        # Convert baseline_comparison_mode
        if isinstance(self.baseline_comparison_mode, str):
            self.baseline_comparison_mode = ComparisonMode(self.baseline_comparison_mode)

        # Convert fallback_behavior
        if isinstance(self.fallback_behavior, str):
            self.fallback_behavior = FallbackBehavior(self.fallback_behavior)

        # Convert expected_advantages keys to enums
        self.expected_advantages = {
            ScenarioCategory(k) if isinstance(k, str) else k: v
            for k, v in self.expected_advantages.items()
        }

        # Convert capabilities to ToolCapability objects
        self.capabilities = [
            ToolCapability(**cap) if isinstance(cap, dict) else cap for cap in self.capabilities
        ]

    def validate(self) -> list[str]:
        """Validate configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Tool ID validation
        if not self.tool_id.islower() or " " in self.tool_id:
            errors.append("tool_id must be lowercase with no spaces")

        # Version validation
        try:
            parts = self.version.split(".")
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                errors.append("version must be valid semver (X.Y.Z)")
        except Exception:
            errors.append("version must be valid semver (X.Y.Z)")

        # Capabilities validation
        if not self.capabilities:
            errors.append("capabilities list cannot be empty")

        # Setup instructions validation
        if self.setup_required and not self.setup_instructions.strip():
            errors.append("setup_instructions required when setup_required is true")

        # Consistency validation
        capability_scenarios = set()
        for cap in self.capabilities:
            capability_scenarios.update(cap.relevant_scenarios)

        advantage_scenarios = set(self.expected_advantages.keys())

        if capability_scenarios != advantage_scenarios:
            missing = capability_scenarios - advantage_scenarios
            extra = advantage_scenarios - capability_scenarios
            if missing:
                errors.append(f"expected_advantages missing scenarios: {missing}")
            if extra:
                errors.append(f"expected_advantages has extra scenarios: {extra}")

        # Constraint validation
        if self.max_concurrent_calls is not None and self.max_concurrent_calls <= 0:
            errors.append("max_concurrent_calls must be positive")

        if self.timeout_seconds <= 0:
            errors.append("timeout_seconds must be positive")

        return errors


@dataclass
class Criterion:
    """A single success criterion for a test scenario."""

    name: str
    check: Callable[[Any], bool]
    description: str = ""


@dataclass
class TestScenario:
    """A single evaluation test scenario."""

    # Identity
    id: str
    category: ScenarioCategory
    name: str
    description: str

    # Test Setup
    test_codebase: Path
    initial_state: dict[str, Any]

    # Test Execution
    task_prompt: str
    success_criteria: list[Criterion]

    # Measurement
    baseline_metrics: list[str]
    tool_metrics: list[str]

    def __post_init__(self):
        """Convert types if needed."""
        if isinstance(self.category, str):
            self.category = ScenarioCategory(self.category)
        if isinstance(self.test_codebase, str):
            self.test_codebase = Path(self.test_codebase)


@dataclass
class QualityMetrics:
    """Metrics that apply to ANY tool evaluation."""

    # Correctness
    correctness_score: float  # 0.0-1.0
    test_failures: int

    # Completeness
    requirements_met: int
    requirements_total: int

    # Code Quality
    follows_best_practices: bool
    introduces_bugs: int


@dataclass
class EfficiencyMetrics:
    """Performance measurements."""

    # Resource Usage
    total_tokens: int
    wall_clock_seconds: float

    # Operations
    file_reads: int
    file_writes: int
    tool_invocations: int

    # Optimization
    unnecessary_operations: int


@dataclass
class ToolMetrics:
    """Tool-specific measurements."""

    # Tool Usage
    features_used: list[str]
    feature_effectiveness: dict[str, float]

    # Tool Performance
    tool_call_latency: list[float]
    tool_failures: int
    fallback_count: int

    # Tool Value
    unique_insights: int
    time_saved_estimate: float


@dataclass
class Metrics:
    """Complete metrics for a scenario execution."""

    quality: QualityMetrics
    efficiency: EfficiencyMetrics
    tool: ToolMetrics | None = None


@dataclass
class ScenarioResult:
    """Result of executing a single test scenario."""

    scenario: TestScenario
    use_tool: bool
    output: Any
    metrics: Metrics
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ComparisonResult:
    """Comparison of baseline vs tool-enhanced execution."""

    scenario: TestScenario
    baseline_result: ScenarioResult
    enhanced_result: ScenarioResult
    quality_delta: dict[str, Any]
    efficiency_delta: dict[str, Any]
    tool_value: dict[str, Any]
    recommendation: str


@dataclass
class EvaluationReport:
    """Complete evaluation report."""

    tool_config: ToolConfiguration
    timestamp: datetime
    results: list[ComparisonResult]
    summary: dict[str, Any]
    recommendations: list[str]

    def save_json(self, path: Path) -> None:
        """Save report as JSON."""
        import json

        # Convert to JSON-serializable format
        data = {
            "tool": {
                "id": self.tool_config.tool_id,
                "name": self.tool_config.tool_name,
                "version": self.tool_config.version,
            },
            "timestamp": self.timestamp.isoformat(),
            "summary": self.summary,
            "recommendations": self.recommendations,
            "results": [
                {
                    "scenario_id": r.scenario.id,
                    "scenario_name": r.scenario.name,
                    "quality_delta": r.quality_delta,
                    "efficiency_delta": r.efficiency_delta,
                    "tool_value": r.tool_value,
                    "recommendation": r.recommendation,
                }
                for r in self.results
            ],
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)
