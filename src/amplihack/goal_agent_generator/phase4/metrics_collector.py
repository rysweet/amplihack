"""
MetricsCollector: Aggregates metrics from execution traces.

Calculates durations, success rates, tool usage, and statistical measures.
"""

import re
import uuid
from collections import Counter, defaultdict
from typing import Dict, List

from ..models import (
    ExecutionMetrics,
    ExecutionTrace,
    PhaseMetrics,
)


class MetricsCollector:
    """
    Collects and aggregates execution metrics.

    Analyzes execution traces to extract meaningful performance indicators.
    """

    @staticmethod
    def collect_metrics(trace: ExecutionTrace) -> ExecutionMetrics:
        """
        Collect metrics from execution trace.

        Args:
            trace: ExecutionTrace to analyze

        Returns:
            ExecutionMetrics with aggregated data

        Example:
            >>> metrics = MetricsCollector.collect_metrics(trace)
            >>> print(f"Success rate: {metrics.success_rate}")
        """
        # Calculate total duration
        total_duration = trace.duration_seconds or 0

        # Collect phase metrics
        phase_metrics = MetricsCollector._collect_phase_metrics(trace)

        # Count errors
        error_count = len([e for e in trace.events if e.event_type == "error"])

        # Calculate success rate
        if phase_metrics:
            successful_phases = sum(1 for m in phase_metrics.values() if m.success)
            success_rate = successful_phases / len(phase_metrics)
        else:
            success_rate = 1.0 if trace.status == "completed" else 0.0

        # Count tool usage
        tool_usage = MetricsCollector._count_tool_usage(trace)

        # Estimate API calls and tokens (from tool usage)
        api_calls = tool_usage.get("claude", 0) + tool_usage.get("llm", 0)
        tokens_used = MetricsCollector._estimate_tokens(trace)

        return ExecutionMetrics(
            execution_id=trace.execution_id,
            total_duration_seconds=total_duration,
            phase_metrics=phase_metrics,
            success_rate=success_rate,
            error_count=error_count,
            tool_usage=tool_usage,
            api_calls=api_calls,
            tokens_used=tokens_used,
        )

    @staticmethod
    def _collect_phase_metrics(trace: ExecutionTrace) -> Dict[str, PhaseMetrics]:
        """Collect metrics for each phase."""
        if not trace.execution_plan:
            return {}

        phase_metrics = {}
        phase_events = defaultdict(list)

        # Group events by phase
        for event in trace.events:
            if event.phase_name:
                phase_events[event.phase_name].append(event)

        # Calculate metrics for each phase
        for phase in trace.execution_plan.phases:
            events = phase_events.get(phase.name, [])
            if not events:
                continue

            # Find start and end events
            start_event = next((e for e in events if e.event_type == "phase_start"), None)
            end_event = next((e for e in events if e.event_type == "phase_end"), None)

            if not start_event or not end_event:
                continue

            # Calculate actual duration
            actual_duration = (end_event.timestamp - start_event.timestamp).total_seconds()

            # Parse estimated duration
            estimated_duration = MetricsCollector._parse_duration(phase.estimated_duration)

            # Check success
            success = end_event.data.get("success", True)
            error_message = end_event.data.get("error")

            # Count retries
            retry_count = len([e for e in events if e.event_type == "retry"])

            phase_metrics[phase.name] = PhaseMetrics(
                phase_name=phase.name,
                estimated_duration=estimated_duration,
                actual_duration=actual_duration,
                accuracy_ratio=actual_duration / estimated_duration if estimated_duration > 0 else 1.0,
                success=success,
                error_message=error_message,
                retry_count=retry_count,
            )

        return phase_metrics

    @staticmethod
    def _parse_duration(duration_str: str) -> float:
        """
        Parse duration string to seconds.

        Args:
            duration_str: Duration like "5 minutes", "2 hours", "30 seconds"

        Returns:
            Duration in seconds
        """
        duration_str = duration_str.lower().strip()

        # Try to extract number
        match = re.search(r"(\d+(?:\.\d+)?)", duration_str)
        if not match:
            return 60.0  # Default 1 minute

        value = float(match.group(1))

        # Determine unit
        if "hour" in duration_str:
            return value * 3600
        elif "min" in duration_str:
            return value * 60
        elif "sec" in duration_str:
            return value
        else:
            return value * 60  # Default to minutes

    @staticmethod
    def _count_tool_usage(trace: ExecutionTrace) -> Dict[str, int]:
        """Count tool usage from events."""
        tool_events = [e for e in trace.events if e.event_type == "tool_call"]
        tool_names = [e.data.get("tool") for e in tool_events if e.data.get("tool")]
        return dict(Counter(tool_names))

    @staticmethod
    def _estimate_tokens(trace: ExecutionTrace) -> int:
        """
        Estimate token usage from trace.

        Very rough estimate based on API calls and data size.
        """
        api_calls = len(
            [
                e
                for e in trace.events
                if e.event_type == "tool_call" and e.data.get("tool") in ["claude", "llm"]
            ]
        )

        # Estimate ~1000 tokens per API call (very rough)
        return api_calls * 1000

    @staticmethod
    def calculate_percentiles(values: List[float], percentiles: List[int]) -> Dict[str, float]:
        """
        Calculate percentiles for a list of values.

        Args:
            values: List of numeric values
            percentiles: List of percentile values (e.g., [50, 95, 99])

        Returns:
            Dictionary mapping percentile to value

        Example:
            >>> values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
            >>> MetricsCollector.calculate_percentiles(values, [50, 95])
            {'p50': 5.5, 'p95': 9.5}
        """
        if not values:
            return {f"p{p}": 0.0 for p in percentiles}

        sorted_values = sorted(values)
        result = {}

        for p in percentiles:
            if p < 0 or p > 100:
                raise ValueError(f"Percentile must be 0-100, got {p}")

            # Calculate index
            index = (len(sorted_values) - 1) * p / 100.0
            lower = int(index)
            upper = min(lower + 1, len(sorted_values) - 1)
            weight = index - lower

            # Interpolate
            value = sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
            result[f"p{p}"] = value

        return result

    @staticmethod
    def aggregate_metrics(metrics_list: List[ExecutionMetrics]) -> Dict[str, any]:
        """
        Aggregate multiple execution metrics.

        Args:
            metrics_list: List of ExecutionMetrics to aggregate

        Returns:
            Dictionary with aggregated statistics

        Example:
            >>> stats = MetricsCollector.aggregate_metrics([m1, m2, m3])
            >>> print(f"Average duration: {stats['avg_duration']}")
        """
        if not metrics_list:
            return {
                "count": 0,
                "avg_duration": 0,
                "avg_success_rate": 0,
                "total_errors": 0,
                "duration_percentiles": {},
            }

        durations = [m.total_duration_seconds for m in metrics_list]
        success_rates = [m.success_rate for m in metrics_list]
        error_counts = [m.error_count for m in metrics_list]

        # Aggregate tool usage
        all_tools = defaultdict(int)
        for m in metrics_list:
            for tool, count in m.tool_usage.items():
                all_tools[tool] += count

        return {
            "count": len(metrics_list),
            "avg_duration": sum(durations) / len(durations),
            "avg_success_rate": sum(success_rates) / len(success_rates),
            "total_errors": sum(error_counts),
            "duration_percentiles": MetricsCollector.calculate_percentiles(durations, [50, 95, 99]),
            "tool_usage": dict(all_tools),
            "total_api_calls": sum(m.api_calls for m in metrics_list),
            "total_tokens": sum(m.tokens_used for m in metrics_list),
        }

    @staticmethod
    def compare_metrics(
        baseline: ExecutionMetrics, current: ExecutionMetrics
    ) -> Dict[str, any]:
        """
        Compare two execution metrics.

        Args:
            baseline: Baseline metrics
            current: Current metrics to compare

        Returns:
            Dictionary with comparison results

        Example:
            >>> comparison = MetricsCollector.compare_metrics(old_metrics, new_metrics)
            >>> print(f"Duration change: {comparison['duration_change_pct']}%")
        """
        duration_change = current.total_duration_seconds - baseline.total_duration_seconds
        duration_change_pct = (
            (duration_change / baseline.total_duration_seconds * 100)
            if baseline.total_duration_seconds > 0
            else 0
        )

        success_rate_change = current.success_rate - baseline.success_rate

        return {
            "duration_change_seconds": duration_change,
            "duration_change_pct": duration_change_pct,
            "success_rate_change": success_rate_change,
            "error_count_change": current.error_count - baseline.error_count,
            "improved": duration_change < 0 and success_rate_change >= 0,
        }
