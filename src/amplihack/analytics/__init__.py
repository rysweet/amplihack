"""
Analytics module for subagent execution tracking and visualization.

This module provides tools to analyze subagent metrics, visualize execution
patterns, and detect performance issues.

Public API:
    - MetricsReader: Read and parse JSONL metrics files
    - SubagentEvent: Single subagent execution event
    - SubagentExecution: Complete execution record (start + stop)
    - ReportGenerator: Generate text and JSON reports
    - ExecutionTreeBuilder: Build agent execution trees
    - PatternDetector: Detect execution patterns
    - AsciiTreeRenderer: Render trees as ASCII art
    - main: CLI entry point

Example:
    >>> from amplihack.analytics import MetricsReader, ReportGenerator
    >>> reader = MetricsReader()
    >>> generator = ReportGenerator(reader)
    >>> report = generator.generate_text_report()
    >>> print(report)
"""

from .metrics_reader import (
    MetricsReader,
    SubagentEvent,
    SubagentExecution,
)

from .visualization import (
    ReportGenerator,
    ExecutionTreeBuilder,
    PatternDetector,
    AsciiTreeRenderer,
    AgentNode,
    Pattern,
)

from .subagent_mapper import main

__all__ = [
    # Core classes
    "MetricsReader",
    "SubagentEvent",
    "SubagentExecution",
    # Visualization
    "ReportGenerator",
    "ExecutionTreeBuilder",
    "PatternDetector",
    "AsciiTreeRenderer",
    "AgentNode",
    "Pattern",
    # CLI
    "main",
]

__version__ = "0.1.0"
