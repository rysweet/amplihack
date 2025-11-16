"""MCP Evaluation Framework - Public API.

This module provides a generic, reusable framework for evaluating ANY MCP
server integration with amplihack. The framework measures real value through
controlled comparisons of baseline vs tool-enhanced coding workflows.

Core Philosophy:
- Ruthless Simplicity: Core framework < 500 lines
- Brick Design: Each component is self-contained and regeneratable
- Zero-BS: No stubs or placeholders, only working code
- Measurement-Driven: Real execution data, not synthetic benchmarks

Example Usage:
    >>> from tests.mcp_evaluation.framework import (
    ...     MCPEvaluationFramework,
    ...     ToolConfiguration,
    ...     TestScenario
    ... )
    >>>
    >>> # Load tool configuration
    >>> config = ToolConfiguration.from_yaml("tools/serena_config.yaml")
    >>>
    >>> # Create framework
    >>> framework = MCPEvaluationFramework(config)
    >>>
    >>> # Run evaluation
    >>> report = framework.run_evaluation(scenarios)
    >>>
    >>> # Save results
    >>> report.save_json(Path("results/report.json"))
"""

from .adapter import ToolAdapter, MockToolAdapter
from .evaluator import MCPEvaluationFramework
from .metrics import MetricsCollector
from .reporter import ReportGenerator, generate_comparison_report
from .types import (
    ComparisonMode,
    ComparisonResult,
    Criterion,
    EfficiencyMetrics,
    EvaluationReport,
    ExpectedImprovement,
    FallbackBehavior,
    Metrics,
    QualityMetrics,
    ScenarioCategory,
    ScenarioResult,
    TestScenario,
    ToolCapability,
    ToolConfiguration,
    ToolMetrics,
)

__all__ = [
    # Main Framework
    "MCPEvaluationFramework",

    # Adapters
    "ToolAdapter",
    "MockToolAdapter",

    # Metrics
    "MetricsCollector",
    "Metrics",
    "QualityMetrics",
    "EfficiencyMetrics",
    "ToolMetrics",

    # Reporting
    "ReportGenerator",
    "generate_comparison_report",

    # Configuration
    "ToolConfiguration",
    "ToolCapability",

    # Scenarios
    "TestScenario",
    "Criterion",

    # Results
    "ScenarioResult",
    "ComparisonResult",
    "EvaluationReport",

    # Enums
    "ScenarioCategory",
    "ExpectedImprovement",
    "ComparisonMode",
    "FallbackBehavior",
]

__version__ = "1.0.0"
