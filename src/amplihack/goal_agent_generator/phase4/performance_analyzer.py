"""
PerformanceAnalyzer: Analyzes execution history for patterns and insights.

Identifies slow phases, common failures, optimal ordering, and generates recommendations.
"""

from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from ..models import (
    ExecutionMetrics,
    ExecutionTrace,
    PerformanceInsights,
    PhaseMetrics,
)
from .metrics_collector import MetricsCollector


class PerformanceAnalyzer:
    """
    Analyzes execution history to extract performance insights.

    Uses statistical analysis to identify patterns and optimization opportunities.
    """

    def __init__(self, min_sample_size: int = 10):
        """
        Initialize performance analyzer.

        Args:
            min_sample_size: Minimum executions for reliable analysis
        """
        self.min_sample_size = min_sample_size

    def analyze_domain(
        self, traces: List[ExecutionTrace], domain: str
    ) -> PerformanceInsights:
        """
        Analyze execution history for a specific domain.

        Args:
            traces: List of execution traces for the domain
            domain: Goal domain being analyzed

        Returns:
            PerformanceInsights with recommendations

        Example:
            >>> insights = analyzer.analyze_domain(traces, "data-processing")
            >>> for rec in insights.recommendations:
            ...     print(rec)
        """
        if not traces:
            return self._empty_insights(domain)

        # Collect metrics for all traces
        metrics_list = [MetricsCollector.collect_metrics(t) for t in traces]

        # Identify slow phases
        slow_phases = self._identify_slow_phases(metrics_list)

        # Find common errors
        common_errors = self._identify_common_errors(traces)

        # Determine optimal phase order
        optimal_order = self._determine_optimal_order(traces)

        # Generate insights
        insights = self._generate_insights(
            traces, metrics_list, slow_phases, common_errors
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            slow_phases, common_errors, metrics_list
        )

        # Calculate confidence score
        confidence = self._calculate_confidence(len(traces))

        return PerformanceInsights(
            goal_domain=domain,
            sample_size=len(traces),
            insights=insights,
            recommendations=recommendations,
            confidence_score=confidence,
            slow_phases=slow_phases,
            common_errors=common_errors,
            optimal_phase_order=optimal_order,
        )

    def _empty_insights(self, domain: str) -> PerformanceInsights:
        """Return empty insights when no data available."""
        return PerformanceInsights(
            goal_domain=domain,
            sample_size=0,
            insights=["Insufficient data for analysis"],
            recommendations=["Execute more agents to gather performance data"],
            confidence_score=0.0,
            slow_phases=[],
            common_errors=[],
            optimal_phase_order=[],
        )

    def _identify_slow_phases(
        self, metrics_list: List[ExecutionMetrics]
    ) -> List[Tuple[str, float]]:
        """
        Identify phases that consistently take longer than estimated.

        Returns list of (phase_name, avg_duration) sorted by duration.
        """
        phase_durations = defaultdict(list)

        for metrics in metrics_list:
            for phase_name, phase_metrics in metrics.phase_metrics.items():
                phase_durations[phase_name].append(phase_metrics.actual_duration)

        # Calculate average durations
        avg_durations = {
            phase: sum(durations) / len(durations)
            for phase, durations in phase_durations.items()
        }

        # Sort by duration (descending)
        return sorted(avg_durations.items(), key=lambda x: x[1], reverse=True)[:5]

    def _identify_common_errors(
        self, traces: List[ExecutionTrace]
    ) -> List[Tuple[str, int]]:
        """
        Identify most common error messages.

        Returns list of (error_message, count) sorted by frequency.
        """
        error_messages = []

        for trace in traces:
            for event in trace.events:
                if event.event_type == "error":
                    error_msg = event.data.get("message", "Unknown error")
                    error_messages.append(error_msg)

        # Count occurrences
        error_counter = Counter(error_messages)
        return error_counter.most_common(5)

    def _determine_optimal_order(self, traces: List[ExecutionTrace]) -> List[str]:
        """
        Determine optimal phase execution order based on successful runs.

        Returns list of phase names in recommended order.
        """
        # Find most successful trace
        successful_traces = [
            t for t in traces if t.status == "completed" and t.execution_plan
        ]

        if not successful_traces:
            return []

        # Use most common phase order from successful runs
        phase_orders = []
        for trace in successful_traces:
            if trace.execution_plan:
                phase_names = [p.name for p in trace.execution_plan.phases]
                phase_orders.append(tuple(phase_names))

        if not phase_orders:
            return []

        # Find most common order
        order_counter = Counter(phase_orders)
        most_common_order = order_counter.most_common(1)[0][0]

        return list(most_common_order)

    def _generate_insights(
        self,
        traces: List[ExecutionTrace],
        metrics_list: List[ExecutionMetrics],
        slow_phases: List[Tuple[str, float]],
        common_errors: List[Tuple[str, int]],
    ) -> List[str]:
        """Generate human-readable insights."""
        insights = []

        # Success rate insight
        completed = sum(1 for t in traces if t.status == "completed")
        success_rate = completed / len(traces) * 100
        insights.append(
            f"Overall success rate: {success_rate:.1f}% ({completed}/{len(traces)} executions)"
        )

        # Duration insight
        avg_stats = MetricsCollector.aggregate_metrics(metrics_list)
        insights.append(
            f"Average execution time: {avg_stats['avg_duration']:.1f} seconds"
        )

        # Slow phase insight
        if slow_phases:
            slowest_phase, duration = slow_phases[0]
            insights.append(
                f"Slowest phase: '{slowest_phase}' averaging {duration:.1f} seconds"
            )

        # Error insight
        if common_errors:
            most_common_error, count = common_errors[0]
            error_pct = count / len(traces) * 100
            insights.append(
                f"Most common error occurs in {error_pct:.1f}% of executions"
            )

        # Estimation accuracy
        avg_accuracy = sum(m.average_accuracy_ratio for m in metrics_list) / len(
            metrics_list
        )
        if avg_accuracy > 1.5:
            insights.append(
                f"Phases take {avg_accuracy:.1f}x longer than estimated on average"
            )
        elif avg_accuracy < 0.7:
            insights.append(
                f"Phases complete faster than estimated ({avg_accuracy:.1f}x)"
            )

        return insights

    def _generate_recommendations(
        self,
        slow_phases: List[Tuple[str, float]],
        common_errors: List[Tuple[str, int]],
        metrics_list: List[ExecutionMetrics],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Slow phase recommendations
        if slow_phases:
            slowest_phase, duration = slow_phases[0]
            recommendations.append(
                f"Optimize '{slowest_phase}' phase - consider parallelization or caching"
            )

        # Error recommendations
        if common_errors:
            recommendations.append(
                "Add error handling and retry logic for common failure patterns"
            )

        # Estimation recommendations
        avg_accuracy = sum(m.average_accuracy_ratio for m in metrics_list) / len(
            metrics_list
        )
        if avg_accuracy > 1.5:
            recommendations.append(
                "Increase duration estimates by 50-100% for more realistic planning"
            )

        # Tool usage recommendations
        avg_stats = MetricsCollector.aggregate_metrics(metrics_list)
        if avg_stats["total_api_calls"] > 50 * len(metrics_list):
            recommendations.append(
                "High API usage detected - consider batching or caching strategies"
            )

        # Success rate recommendations
        if avg_stats["avg_success_rate"] < 0.7:
            recommendations.append(
                "Success rate below 70% - add validation checkpoints between phases"
            )

        if not recommendations:
            recommendations.append("Performance is within acceptable range")

        return recommendations

    def _calculate_confidence(self, sample_size: int) -> float:
        """
        Calculate confidence score based on sample size.

        Returns value 0-1 where 1 is high confidence.
        """
        if sample_size >= 100:
            return 1.0
        elif sample_size >= 50:
            return 0.9
        elif sample_size >= 20:
            return 0.7
        elif sample_size >= self.min_sample_size:
            return 0.5
        else:
            return max(0.1, sample_size / self.min_sample_size * 0.5)

    def compare_before_after(
        self,
        before_traces: List[ExecutionTrace],
        after_traces: List[ExecutionTrace],
        domain: str,
    ) -> Dict[str, any]:
        """
        Compare performance before and after an optimization.

        Args:
            before_traces: Traces before optimization
            after_traces: Traces after optimization
            domain: Goal domain

        Returns:
            Comparison results with improvement metrics

        Example:
            >>> results = analyzer.compare_before_after(old_traces, new_traces, "security")
            >>> print(f"Improvement: {results['improvement_pct']:.1f}%")
        """
        before_insights = self.analyze_domain(before_traces, domain)
        after_insights = self.analyze_domain(after_traces, domain)

        # Calculate improvements
        before_metrics = [
            MetricsCollector.collect_metrics(t) for t in before_traces
        ]
        after_metrics = [
            MetricsCollector.collect_metrics(t) for t in after_traces
        ]

        before_stats = MetricsCollector.aggregate_metrics(before_metrics)
        after_stats = MetricsCollector.aggregate_metrics(after_metrics)

        duration_improvement = (
            (before_stats["avg_duration"] - after_stats["avg_duration"])
            / before_stats["avg_duration"]
            * 100
            if before_stats["avg_duration"] > 0
            else 0
        )

        success_rate_improvement = (
            after_stats["avg_success_rate"] - before_stats["avg_success_rate"]
        ) * 100

        return {
            "domain": domain,
            "before_sample_size": before_insights.sample_size,
            "after_sample_size": after_insights.sample_size,
            "duration_improvement_pct": duration_improvement,
            "success_rate_improvement_pct": success_rate_improvement,
            "before_avg_duration": before_stats["avg_duration"],
            "after_avg_duration": after_stats["avg_duration"],
            "improved": duration_improvement > 0 or success_rate_improvement > 0,
            "confidence": min(
                before_insights.confidence_score, after_insights.confidence_score
            ),
        }
