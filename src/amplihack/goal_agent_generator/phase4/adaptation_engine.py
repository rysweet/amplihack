"""
AdaptationEngine: Modifies execution plans based on learned patterns.

Reorders phases, adjusts estimates, adds checkpoints based on historical performance.
"""

import uuid
from copy import deepcopy
from datetime import datetime
from typing import List, Optional

from ..models import (
    AdaptedExecutionPlan,
    ExecutionPlan,
    PerformanceInsights,
    PlanPhase,
)


class AdaptationEngine:
    """
    Adapts execution plans based on performance insights.

    Modifies plans to improve success rate and reduce execution time.
    """

    def __init__(self, min_confidence: float = 0.5):
        """
        Initialize adaptation engine.

        Args:
            min_confidence: Minimum confidence score to apply adaptations
        """
        self.min_confidence = min_confidence

    def adapt_plan(
        self,
        original_plan: ExecutionPlan,
        insights: PerformanceInsights,
        aggressive: bool = False,
    ) -> AdaptedExecutionPlan:
        """
        Adapt execution plan based on performance insights.

        Args:
            original_plan: Original execution plan
            insights: Performance insights from historical data
            aggressive: If True, apply more aggressive optimizations

        Returns:
            AdaptedExecutionPlan with modifications

        Example:
            >>> adapted = engine.adapt_plan(plan, insights)
            >>> print(f"Applied {len(adapted.adaptations)} adaptations")
        """
        if insights.confidence_score < self.min_confidence:
            return self._no_adaptation(original_plan, "Insufficient confidence")

        # Start with copy of original
        adapted_phases = deepcopy(original_plan.phases)
        adaptations = []
        expected_improvement = 0.0

        # Apply adaptations based on insights
        if insights.optimal_phase_order:
            adapted_phases, reorder_improvement = self._reorder_phases(
                adapted_phases, insights.optimal_phase_order
            )
            if reorder_improvement > 0:
                adaptations.append(
                    f"Reordered phases based on {insights.sample_size} successful executions"
                )
                expected_improvement += reorder_improvement

        if insights.slow_phases:
            adapted_phases, duration_improvement = self._adjust_durations(
                adapted_phases, insights.slow_phases
            )
            if duration_improvement > 0:
                adaptations.append(
                    f"Adjusted duration estimates for {len(insights.slow_phases)} slow phases"
                )
                expected_improvement += duration_improvement

        if insights.common_errors:
            adapted_phases, error_improvement = self._add_error_handling(
                adapted_phases, insights.common_errors, aggressive
            )
            if error_improvement > 0:
                adaptations.append(
                    f"Added error handling for {len(insights.common_errors)} common failures"
                )
                expected_improvement += error_improvement

        # Add validation checkpoints if success rate is low
        if insights.sample_size > 0:
            avg_success_rate = sum(
                1 for i in insights.insights if "success rate" in i.lower()
            )
            if avg_success_rate < 0.7 or aggressive:
                adapted_phases, checkpoint_improvement = self._add_checkpoints(
                    adapted_phases
                )
                if checkpoint_improvement > 0:
                    adaptations.append("Added validation checkpoints between phases")
                    expected_improvement += checkpoint_improvement

        if not adaptations:
            return self._no_adaptation(original_plan, "No beneficial adaptations found")

        # Create adapted plan
        adapted_plan = AdaptedExecutionPlan(
            goal_id=original_plan.goal_id,
            phases=adapted_phases,
            total_estimated_duration=self._recalculate_total_duration(adapted_phases),
            required_skills=original_plan.required_skills,
            parallel_opportunities=self._recalculate_parallel_opportunities(
                adapted_phases
            ),
            risk_factors=original_plan.risk_factors,
            original_plan_id=uuid.uuid4(),  # Would be original_plan.id if it had one
            adaptations=adaptations,
            expected_improvement=min(expected_improvement, 50.0),  # Cap at 50%
            confidence=insights.confidence_score,
            adapted_at=datetime.utcnow(),
        )

        return adapted_plan

    def _no_adaptation(
        self, original_plan: ExecutionPlan, reason: str
    ) -> AdaptedExecutionPlan:
        """Create an adapted plan with no changes."""
        return AdaptedExecutionPlan(
            goal_id=original_plan.goal_id,
            phases=original_plan.phases,
            total_estimated_duration=original_plan.total_estimated_duration,
            required_skills=original_plan.required_skills,
            parallel_opportunities=original_plan.parallel_opportunities,
            risk_factors=original_plan.risk_factors,
            original_plan_id=uuid.uuid4(),
            adaptations=[f"No adaptations applied: {reason}"],
            expected_improvement=0.0,
            confidence=0.0,
        )

    def _reorder_phases(
        self, phases: List[PlanPhase], optimal_order: List[str]
    ) -> tuple[List[PlanPhase], float]:
        """
        Reorder phases based on optimal order from successful executions.

        Returns (reordered_phases, improvement_percentage).
        """
        if not optimal_order or len(optimal_order) != len(phases):
            return phases, 0.0

        # Create phase lookup
        phase_map = {p.name: p for p in phases}

        # Check if all phases exist
        if not all(name in phase_map for name in optimal_order):
            return phases, 0.0

        # Respect dependencies
        reordered = []
        for name in optimal_order:
            phase = phase_map[name]
            # Check if dependencies are satisfied
            if all(dep in [p.name for p in reordered] for dep in phase.dependencies):
                reordered.append(phase)

        # Add any remaining phases
        for phase in phases:
            if phase not in reordered:
                reordered.append(phase)

        # Estimate improvement (reordering can save ~5-10%)
        improvement = 5.0 if reordered != phases else 0.0

        return reordered, improvement

    def _adjust_durations(
        self, phases: List[PlanPhase], slow_phases: List[tuple[str, float]]
    ) -> tuple[List[PlanPhase], float]:
        """
        Adjust duration estimates for slow phases.

        Returns (adjusted_phases, improvement_percentage).
        """
        slow_phase_map = dict(slow_phases)
        adjusted_count = 0

        for phase in phases:
            if phase.name in slow_phase_map:
                actual_duration = slow_phase_map[phase.name]
                # Update estimate to be closer to actual (add 20% buffer)
                new_estimate = f"{int(actual_duration * 1.2)} seconds"
                phase.estimated_duration = new_estimate
                adjusted_count += 1

        # Better estimates improve planning accuracy ~10%
        improvement = 10.0 if adjusted_count > 0 else 0.0

        return phases, improvement

    def _add_error_handling(
        self,
        phases: List[PlanPhase],
        common_errors: List[tuple[str, int]],
        aggressive: bool,
    ) -> tuple[List[PlanPhase], float]:
        """
        Add error handling capabilities to phases.

        Returns (modified_phases, improvement_percentage).
        """
        if not common_errors:
            return phases, 0.0

        modified_count = 0
        for phase in phases:
            # Add error handling capability if not present
            if "error_handling" not in phase.required_capabilities:
                phase.required_capabilities.append("error_handling")
                modified_count += 1

            # Add retry capability for aggressive mode
            if aggressive and "retry_logic" not in phase.required_capabilities:
                phase.required_capabilities.append("retry_logic")

        # Error handling can improve success rate ~15-20%
        improvement = 15.0 if modified_count > 0 else 0.0

        return phases, improvement

    def _add_checkpoints(
        self, phases: List[PlanPhase]
    ) -> tuple[List[PlanPhase], float]:
        """
        Add validation checkpoints between phases.

        Returns (modified_phases, improvement_percentage).
        """
        for phase in phases:
            # Add validation success indicators
            if not phase.success_indicators:
                phase.success_indicators = [
                    f"Phase '{phase.name}' completes without errors",
                    f"Output from '{phase.name}' is validated",
                ]

        # Checkpoints improve reliability ~10%
        return phases, 10.0

    def _recalculate_total_duration(self, phases: List[PlanPhase]) -> str:
        """Recalculate total estimated duration from phases."""
        # Simple sum for now (doesn't account for parallelization)
        total_seconds = 0
        for phase in phases:
            duration = phase.estimated_duration.lower()
            if "hour" in duration:
                total_seconds += int(duration.split()[0]) * 3600
            elif "minute" in duration:
                total_seconds += int(duration.split()[0]) * 60
            elif "second" in duration:
                total_seconds += int(duration.split()[0])

        if total_seconds >= 3600:
            return f"{total_seconds // 3600} hours"
        elif total_seconds >= 60:
            return f"{total_seconds // 60} minutes"
        else:
            return f"{total_seconds} seconds"

    def _recalculate_parallel_opportunities(
        self, phases: List[PlanPhase]
    ) -> List[List[str]]:
        """Identify phases that can run in parallel."""
        parallel_groups = []

        # Find phases with no dependencies
        independent_phases = [p for p in phases if not p.dependencies and p.parallel_safe]

        if len(independent_phases) > 1:
            parallel_groups.append([p.name for p in independent_phases])

        return parallel_groups

    def create_ab_test(
        self, original_plan: ExecutionPlan, adapted_plan: AdaptedExecutionPlan
    ) -> dict[str, ExecutionPlan]:
        """
        Create A/B test variants.

        Args:
            original_plan: Original plan (variant A)
            adapted_plan: Adapted plan (variant B)

        Returns:
            Dictionary with "A" and "B" variants

        Example:
            >>> variants = engine.create_ab_test(original, adapted)
            >>> # Route 50% of traffic to each variant
        """
        return {"A": original_plan, "B": adapted_plan}

    def should_use_adapted_plan(
        self, insights: PerformanceInsights, risk_tolerance: float = 0.5
    ) -> bool:
        """
        Decide whether to use adapted plan.

        Args:
            insights: Performance insights
            risk_tolerance: Risk tolerance (0=conservative, 1=aggressive)

        Returns:
            True if adapted plan should be used

        Example:
            >>> if engine.should_use_adapted_plan(insights, risk_tolerance=0.7):
            ...     plan = adapted_plan
        """
        # Need sufficient confidence
        if insights.confidence_score < self.min_confidence:
            return False

        # Need sufficient sample size
        if not insights.has_sufficient_data:
            return False

        # Consider risk tolerance
        confidence_threshold = 0.9 - (risk_tolerance * 0.4)  # 0.9 to 0.5 range
        return insights.confidence_score >= confidence_threshold
