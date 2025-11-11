"""
PlanOptimizer: Optimizes execution plans using historical data.

Finds similar past executions and extracts best practices.
"""

import re
from typing import Dict, List, Optional, Tuple

from ..models import (
    ExecutionPlan,
    ExecutionTrace,
    GoalDefinition,
    PerformanceInsights,
)
from .execution_database import ExecutionDatabase
from .metrics_collector import MetricsCollector
from .performance_analyzer import PerformanceAnalyzer


class PlanOptimizer:
    """
    Optimizes execution plans using historical performance data.

    Finds similar goals and applies learned best practices.
    """

    def __init__(self, database: ExecutionDatabase):
        """
        Initialize plan optimizer.

        Args:
            database: ExecutionDatabase for querying history
        """
        self.database = database
        self.analyzer = PerformanceAnalyzer()

    def optimize_plan(
        self, goal: GoalDefinition, plan: ExecutionPlan
    ) -> Tuple[ExecutionPlan, Dict[str, any]]:
        """
        Optimize execution plan using historical data.

        Args:
            goal: Goal definition
            plan: Initial execution plan

        Returns:
            Tuple of (optimized_plan, optimization_info)

        Example:
            >>> optimized, info = optimizer.optimize_plan(goal, plan)
            >>> print(f"Confidence: {info['confidence']}")
        """
        # Find similar past executions
        similar_traces = self._find_similar_executions(goal)

        if not similar_traces:
            return plan, {
                "optimized": False,
                "reason": "No similar historical executions found",
                "confidence": 0.0,
                "similar_count": 0,
            }

        # Analyze performance of similar executions
        insights = self.analyzer.analyze_domain(similar_traces, goal.domain)

        if not insights.has_sufficient_data:
            return plan, {
                "optimized": False,
                "reason": f"Insufficient data ({insights.sample_size} executions)",
                "confidence": insights.confidence_score,
                "similar_count": len(similar_traces),
            }

        # Extract best practices
        best_practices = self._extract_best_practices(similar_traces, insights)

        # Apply optimizations
        optimized_plan = self._apply_optimizations(plan, best_practices, insights)

        return optimized_plan, {
            "optimized": True,
            "confidence": insights.confidence_score,
            "similar_count": len(similar_traces),
            "best_practices": best_practices,
            "expected_improvement": self._estimate_improvement(insights),
        }

    def _find_similar_executions(
        self, goal: GoalDefinition, limit: int = 50
    ) -> List[ExecutionTrace]:
        """
        Find executions with similar goals.

        Uses domain matching and keyword similarity.
        """
        # Query by domain
        executions = self.database.query_by_domain(
            goal.domain, limit=limit, status="completed"
        )

        if not executions:
            return []

        # Score similarity
        scored_executions = []
        for exec_dict in executions:
            similarity = self._calculate_similarity(goal, exec_dict)
            if similarity > 0.3:  # Minimum similarity threshold
                scored_executions.append((exec_dict, similarity))

        # Sort by similarity
        scored_executions.sort(key=lambda x: x[1], reverse=True)

        # Load top traces
        traces = []
        for exec_dict, _ in scored_executions[:20]:  # Top 20
            trace = self.database.get_trace(exec_dict["execution_id"])
            if trace:
                traces.append(trace)

        return traces

    def _calculate_similarity(
        self, goal: GoalDefinition, execution: Dict[str, any]
    ) -> float:
        """
        Calculate similarity between goal and historical execution.

        Returns score 0-1 where 1 is identical.
        """
        score = 0.0

        # Domain match (highest weight)
        if execution.get("goal_domain") == goal.domain:
            score += 0.5

        # Keyword overlap
        goal_keywords = self._extract_keywords(goal.goal)
        exec_keywords = self._extract_keywords(execution.get("goal_text", ""))
        overlap = len(goal_keywords & exec_keywords)
        if goal_keywords:
            score += 0.3 * (overlap / len(goal_keywords))

        # Complexity match
        if goal.complexity in execution.get("goal_text", "").lower():
            score += 0.2

        return min(score, 1.0)

    def _extract_keywords(self, text: str) -> set[str]:
        """Extract meaningful keywords from text."""
        # Simple keyword extraction (lowercase, remove common words)
        common_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }

        words = re.findall(r"\b\w+\b", text.lower())
        return {w for w in words if len(w) > 3 and w not in common_words}

    def _extract_best_practices(
        self, traces: List[ExecutionTrace], insights: PerformanceInsights
    ) -> List[str]:
        """
        Extract best practices from successful executions.

        Returns list of actionable best practices.
        """
        practices = []

        # Optimal phase order
        if insights.optimal_phase_order:
            practices.append(
                f"Use phase order: {' -> '.join(insights.optimal_phase_order)}"
            )

        # Duration estimates
        if insights.slow_phases:
            slowest_phase, duration = insights.slow_phases[0]
            practices.append(
                f"Allocate at least {int(duration)} seconds for '{slowest_phase}'"
            )

        # Error prevention
        if insights.common_errors:
            practices.append(
                "Add validation before phases prone to errors"
            )

        # Success patterns
        successful_traces = [t for t in traces if t.status == "completed"]
        if len(successful_traces) > len(traces) * 0.8:
            practices.append(
                "Current approach is reliable - minimal changes recommended"
            )

        # Tool usage patterns
        metrics_list = [MetricsCollector.collect_metrics(t) for t in traces]
        avg_stats = MetricsCollector.aggregate_metrics(metrics_list)
        if avg_stats["tool_usage"]:
            most_used_tool = max(avg_stats["tool_usage"].items(), key=lambda x: x[1])
            practices.append(
                f"'{most_used_tool[0]}' tool is commonly used - ensure availability"
            )

        return practices

    def _apply_optimizations(
        self,
        plan: ExecutionPlan,
        best_practices: List[str],
        insights: PerformanceInsights,
    ) -> ExecutionPlan:
        """
        Apply optimizations to execution plan.

        Modifies plan in place and returns it.
        """
        # Update phase estimates based on insights
        if insights.slow_phases:
            slow_phase_map = dict(insights.slow_phases)
            for phase in plan.phases:
                if phase.name in slow_phase_map:
                    actual_duration = slow_phase_map[phase.name]
                    phase.estimated_duration = f"{int(actual_duration * 1.2)} seconds"

        # Add risk factors based on common errors
        if insights.common_errors:
            for error_msg, count in insights.common_errors:
                risk = f"Common error pattern: {error_msg[:50]}"
                if risk not in plan.risk_factors:
                    plan.risk_factors.append(risk)

        # Update parallel opportunities
        if insights.optimal_phase_order:
            # Identify independent phases
            independent = [
                p.name
                for p in plan.phases
                if not p.dependencies and p.parallel_safe
            ]
            if len(independent) > 1:
                plan.parallel_opportunities = [independent]

        return plan

    def _estimate_improvement(self, insights: PerformanceInsights) -> float:
        """
        Estimate expected improvement percentage.

        Based on confidence and sample size.
        """
        base_improvement = 10.0  # Base 10% improvement from using history

        # Scale by confidence
        improvement = base_improvement * insights.confidence_score

        # Bonus for large sample size
        if insights.sample_size > 50:
            improvement += 5.0
        elif insights.sample_size > 100:
            improvement += 10.0

        return min(improvement, 30.0)  # Cap at 30%

    def get_recommendations(
        self, goal: GoalDefinition
    ) -> Optional[Dict[str, any]]:
        """
        Get recommendations for a goal without modifying a plan.

        Args:
            goal: Goal definition

        Returns:
            Dictionary with recommendations or None if no data

        Example:
            >>> recs = optimizer.get_recommendations(goal)
            >>> if recs:
            ...     for practice in recs['best_practices']:
            ...         print(practice)
        """
        similar_traces = self._find_similar_executions(goal)

        if not similar_traces:
            return None

        insights = self.analyzer.analyze_domain(similar_traces, goal.domain)

        if not insights.has_sufficient_data:
            return None

        best_practices = self._extract_best_practices(similar_traces, insights)

        return {
            "domain": goal.domain,
            "similar_executions": len(similar_traces),
            "confidence": insights.confidence_score,
            "best_practices": best_practices,
            "insights": insights.insights,
            "recommendations": insights.recommendations,
        }

    def compare_plans(
        self, plan_a: ExecutionPlan, plan_b: ExecutionPlan, goal: GoalDefinition
    ) -> Dict[str, any]:
        """
        Compare two execution plans using historical data.

        Args:
            plan_a: First plan
            plan_b: Second plan
            goal: Goal definition

        Returns:
            Comparison with predicted performance

        Example:
            >>> comparison = optimizer.compare_plans(original, optimized, goal)
            >>> print(f"Recommended: {comparison['recommended']}")
        """
        # Find similar executions
        similar_traces = self._find_similar_executions(goal)

        if not similar_traces:
            return {
                "compared": False,
                "reason": "No historical data for comparison",
            }

        # Simple heuristic comparison
        score_a = self._score_plan(plan_a, similar_traces)
        score_b = self._score_plan(plan_b, similar_traces)

        return {
            "compared": True,
            "plan_a_score": score_a,
            "plan_b_score": score_b,
            "recommended": "B" if score_b > score_a else "A",
            "confidence": min(len(similar_traces) / 20, 1.0),  # Max at 20 samples
        }

    def _score_plan(
        self, plan: ExecutionPlan, reference_traces: List[ExecutionTrace]
    ) -> float:
        """
        Score a plan based on alignment with successful patterns.

        Returns score 0-100.
        """
        score = 50.0  # Base score

        # Check phase count (prefer 3-5 phases)
        if 3 <= plan.phase_count <= 5:
            score += 10.0

        # Check for parallel opportunities
        if plan.parallel_opportunities:
            score += 10.0

        # Check for success indicators
        phases_with_indicators = sum(
            1 for p in plan.phases if p.success_indicators
        )
        score += (phases_with_indicators / len(plan.phases)) * 10

        # Check risk awareness
        if plan.risk_factors:
            score += 10.0

        # Compare with successful patterns
        successful_traces = [t for t in reference_traces if t.status == "completed"]
        if successful_traces:
            # Find most common phase count
            common_phase_count = max(
                set(
                    len(t.execution_plan.phases)
                    for t in successful_traces
                    if t.execution_plan
                ),
                key=lambda x: sum(
                    1
                    for t in successful_traces
                    if t.execution_plan and len(t.execution_plan.phases) == x
                ),
                default=4,
            )

            if plan.phase_count == common_phase_count:
                score += 10.0

        return min(score, 100.0)
