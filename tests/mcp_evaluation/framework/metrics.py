"""Metrics collection system for MCP evaluation framework.

This module provides the MetricsCollector class that tracks all measurements
during scenario execution, including quality, efficiency, and tool-specific metrics.
"""

import time

from .adapter import ToolAdapter
from .types import (
    EfficiencyMetrics,
    Metrics,
    QualityMetrics,
)


class MetricsCollector:
    """Collects universal and tool-specific metrics during execution.

    The collector tracks:
    - File operations (reads/writes)
    - Token usage
    - Wall clock time
    - Tool invocations
    - Quality assessments
    """

    def __init__(self, adapter: ToolAdapter | None = None):
        """Initialize metrics collector.

        Args:
            adapter: Optional tool adapter for collecting tool-specific metrics
        """
        self.adapter = adapter
        self._reset()

    def _reset(self) -> None:
        """Reset all metrics to initial state."""
        # Efficiency tracking
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.total_tokens: int = 0
        self.file_reads: set[str] = set()
        self.file_writes: set[str] = set()
        self.tool_invocations: int = 0
        self.unnecessary_ops: int = 0

        # Quality tracking
        self.correctness: float = 0.0
        self.test_failures: int = 0
        self.requirements_met: int = 0
        self.requirements_total: int = 0
        self.follows_best_practices: bool = True
        self.bugs_introduced: int = 0

        # Tool tracking
        self.tool_calls: list[dict] = []

    def start(self) -> None:
        """Start metrics collection."""
        self._reset()
        self.start_time = time.time()

    def stop(self) -> Metrics:
        """Stop collection and return metrics.

        Returns:
            Complete Metrics object with quality, efficiency, and tool data
        """
        self.end_time = time.time()

        quality = QualityMetrics(
            correctness_score=self.correctness,
            test_failures=self.test_failures,
            requirements_met=self.requirements_met,
            requirements_total=self.requirements_total,
            follows_best_practices=self.follows_best_practices,
            introduces_bugs=self.bugs_introduced,
        )

        efficiency = EfficiencyMetrics(
            total_tokens=self.total_tokens,
            wall_clock_seconds=self._elapsed_time(),
            file_reads=len(self.file_reads),
            file_writes=len(self.file_writes),
            tool_invocations=self.tool_invocations,
            unnecessary_operations=self.unnecessary_ops,
        )

        # Collect tool metrics if adapter provided
        tool_metrics = None
        if self.adapter and self.adapter.is_available():
            try:
                tool_metrics = self.adapter.collect_tool_metrics()
            except Exception as e:
                # Don't fail collection if tool metrics fail
                print(f"Warning: Failed to collect tool metrics: {e}")

        return Metrics(
            quality=quality,
            efficiency=efficiency,
            tool=tool_metrics,
        )

    def _elapsed_time(self) -> float:
        """Calculate elapsed time in seconds."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    # Recording methods for efficiency metrics

    def record_file_read(self, path: str) -> None:
        """Record a file read operation.

        Args:
            path: Path to file that was read
        """
        self.file_reads.add(path)

    def record_file_write(self, path: str) -> None:
        """Record a file write operation.

        Args:
            path: Path to file that was written
        """
        self.file_writes.add(path)

    def record_tool_call(self, command: str, latency: float, success: bool) -> None:
        """Record an MCP tool invocation.

        Args:
            command: MCP command that was invoked
            latency: Time taken for the call in seconds
            success: Whether the call succeeded
        """
        self.tool_invocations += 1
        self.tool_calls.append(
            {
                "command": command,
                "latency": latency,
                "success": success,
                "timestamp": time.time(),
            }
        )

    def record_tokens(self, count: int) -> None:
        """Record token usage.

        Args:
            count: Number of tokens consumed
        """
        self.total_tokens += count

    def record_unnecessary_operation(self) -> None:
        """Record an unnecessary or redundant operation."""
        self.unnecessary_ops += 1

    # Recording methods for quality metrics

    def set_correctness(self, score: float) -> None:
        """Set correctness score.

        Args:
            score: Correctness score between 0.0 and 1.0
        """
        self.correctness = max(0.0, min(1.0, score))

    def record_test_failure(self) -> None:
        """Record a test failure."""
        self.test_failures += 1

    def set_requirements(self, met: int, total: int) -> None:
        """Set requirement fulfillment counts.

        Args:
            met: Number of requirements met
            total: Total number of requirements
        """
        self.requirements_met = met
        self.requirements_total = total

    def set_best_practices(self, follows: bool) -> None:
        """Set whether code follows best practices.

        Args:
            follows: True if code follows best practices
        """
        self.follows_best_practices = follows

    def record_bug(self) -> None:
        """Record a bug introduced by the changes."""
        self.bugs_introduced += 1

    # Analysis helpers

    def get_file_operation_count(self) -> int:
        """Get total file operations (reads + writes)."""
        return len(self.file_reads) + len(self.file_writes)

    def get_average_tool_latency(self) -> float:
        """Get average tool call latency in seconds."""
        if not self.tool_calls:
            return 0.0
        return sum(call["latency"] for call in self.tool_calls) / len(self.tool_calls)

    def get_tool_success_rate(self) -> float:
        """Get tool call success rate (0.0 to 1.0)."""
        if not self.tool_calls:
            return 1.0
        successes = sum(1 for call in self.tool_calls if call["success"])
        return successes / len(self.tool_calls)

    def get_completeness_score(self) -> float:
        """Get requirement completeness score (0.0 to 1.0)."""
        if self.requirements_total == 0:
            return 1.0
        return self.requirements_met / self.requirements_total
