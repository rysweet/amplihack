"""PM learning system for tracking outcomes and improving over time.

This module implements Phase 4 learning capabilities, tracking workstream
outcomes, improving estimation accuracy, identifying risk patterns, and
adapting prioritization based on actual results.

Public API:
    - WorkstreamOutcome: Record of completed workstream result
    - EstimationMetrics: Estimation accuracy tracking
    - RiskPattern: Identified risk pattern from history
    - OutcomeTracker: Learn from outcomes and improve

Philosophy:
    - Learn from results: Track actual vs. estimated
    - Pattern recognition: Identify what works and what doesn't
    - Continuous improvement: Adapt recommendations over time
    - Ruthless simplicity: Rule-based pattern matching
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import statistics

from .state import PMStateManager, WorkstreamState, BacklogItem

__all__ = [
    "WorkstreamOutcome",
    "EstimationMetrics",
    "RiskPattern",
    "OutcomeTracker",
]


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class WorkstreamOutcome:
    """Record of completed workstream and its outcome.

    Attributes:
        workstream_id: Workstream identifier
        backlog_id: Backlog item identifier
        title: Item title
        success: Whether workstream succeeded
        estimated_hours: Original estimate
        actual_hours: Actual time taken
        estimation_error: (actual - estimated) / estimated
        complexity: Assessed complexity (simple, medium, complex)
        blockers_encountered: List of blockers hit
        completed_at: ISO timestamp of completion
        notes: Additional notes about outcome
    """
    workstream_id: str
    backlog_id: str
    title: str
    success: bool
    estimated_hours: int
    actual_hours: float
    estimation_error: float
    complexity: str
    blockers_encountered: List[str] = field(default_factory=list)
    completed_at: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkstreamOutcome":
        """Create from dictionary loaded from YAML."""
        if data.get("blockers_encountered") is None:
            data["blockers_encountered"] = []
        return cls(**data)


@dataclass
class EstimationMetrics:
    """Estimation accuracy metrics over time.

    Attributes:
        total_items: Total items tracked
        mean_error: Mean estimation error (%)
        median_error: Median estimation error (%)
        std_error: Standard deviation of error
        overestimate_rate: % of items overestimated
        underestimate_rate: % of items underestimated
        by_complexity: Breakdown by complexity level
    """
    total_items: int
    mean_error: float
    median_error: float
    std_error: float
    overestimate_rate: float
    underestimate_rate: float
    by_complexity: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return asdict(self)


@dataclass
class RiskPattern:
    """Identified risk pattern from historical data.

    Attributes:
        pattern_id: Unique identifier
        pattern_type: Type of pattern (estimation, blocker, failure)
        description: What the pattern is
        occurrence_count: How many times seen
        severity: low, medium, high
        recommendation: What to do about it
        examples: Example workstreams showing pattern
    """
    pattern_id: str
    pattern_type: str
    description: str
    occurrence_count: int
    severity: str
    recommendation: str
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return asdict(self)


# =============================================================================
# Outcome Tracker
# =============================================================================


class OutcomeTracker:
    """Track outcomes and learn from results.

    Capabilities:
    - Record workstream outcomes (success/failure)
    - Track estimation accuracy over time
    - Identify common risk patterns
    - Provide adaptive recommendations
    - Generate learning insights

    Usage:
        tracker = OutcomeTracker(project_root)

        # Record a completed workstream
        outcome = tracker.record_outcome(workstream)

        # Get estimation metrics
        metrics = tracker.get_estimation_metrics()

        # Identify risk patterns
        patterns = tracker.identify_risk_patterns()

        # Get improvement suggestions
        suggestions = tracker.get_improvement_suggestions()
    """

    def __init__(self, project_root: Path):
        """Initialize outcome tracker.

        Args:
            project_root: Root directory of project (contains .pm/)
        """
        self.project_root = project_root
        self.state_mgr = PMStateManager(project_root)
        self.outcomes_file = project_root / ".pm" / "logs" / "outcomes.yaml"

    def record_outcome(
        self,
        workstream: WorkstreamState,
        success: bool,
        notes: str = ""
    ) -> WorkstreamOutcome:
        """Record outcome for completed workstream.

        Args:
            workstream: Completed workstream
            success: Whether it succeeded
            notes: Additional notes

        Returns:
            WorkstreamOutcome object
        """
        # Get backlog item for estimates
        backlog_item = self.state_mgr.get_backlog_item(workstream.backlog_id)
        if not backlog_item:
            raise ValueError(f"Backlog item {workstream.backlog_id} not found")

        # Calculate actual hours
        actual_hours = workstream.elapsed_minutes / 60.0

        # Calculate estimation error
        estimated_hours = float(backlog_item.estimated_hours)
        if estimated_hours > 0:
            estimation_error = (actual_hours - estimated_hours) / estimated_hours
        else:
            estimation_error = 0.0

        # Determine complexity from backlog or workstream
        complexity = "medium"  # Default
        # Note: In real implementation, could extract from backlog tags or AI analysis

        # Create outcome record
        outcome = WorkstreamOutcome(
            workstream_id=workstream.id,
            backlog_id=workstream.backlog_id,
            title=workstream.title,
            success=success,
            estimated_hours=backlog_item.estimated_hours,
            actual_hours=actual_hours,
            estimation_error=estimation_error,
            complexity=complexity,
            blockers_encountered=[],  # Could extract from progress notes
            completed_at=datetime.utcnow().isoformat() + "Z",
            notes=notes
        )

        # Save to outcomes log
        self._append_outcome(outcome)

        return outcome

    def get_estimation_metrics(
        self,
        window_days: int = 30
    ) -> EstimationMetrics:
        """Calculate estimation accuracy metrics.

        Args:
            window_days: How many days of history to analyze

        Returns:
            EstimationMetrics object
        """
        outcomes = self._load_outcomes()

        # Filter to time window
        cutoff = datetime.utcnow() - timedelta(days=window_days)
        recent = []
        for outcome in outcomes:
            try:
                ts = datetime.fromisoformat(outcome.completed_at.replace("Z", "+00:00"))
                if ts.replace(tzinfo=None) >= cutoff:
                    recent.append(outcome)
            except (ValueError, AttributeError):
                continue

        if not recent:
            # No data
            return EstimationMetrics(
                total_items=0,
                mean_error=0.0,
                median_error=0.0,
                std_error=0.0,
                overestimate_rate=0.0,
                underestimate_rate=0.0,
                by_complexity={}
            )

        # Calculate overall metrics
        errors = [o.estimation_error for o in recent]
        mean_error = statistics.mean(errors) * 100
        median_error = statistics.median(errors) * 100
        std_error = statistics.stdev(errors) * 100 if len(errors) > 1 else 0.0

        overestimates = [e for e in errors if e < 0]  # Actual < Estimated
        underestimates = [e for e in errors if e > 0]  # Actual > Estimated

        overestimate_rate = (len(overestimates) / len(errors)) * 100
        underestimate_rate = (len(underestimates) / len(errors)) * 100

        # Break down by complexity
        by_complexity = {}
        for complexity in ["simple", "medium", "complex"]:
            complex_outcomes = [o for o in recent if o.complexity == complexity]
            if complex_outcomes:
                complex_errors = [o.estimation_error for o in complex_outcomes]
                by_complexity[complexity] = {
                    "count": len(complex_outcomes),
                    "mean_error": statistics.mean(complex_errors) * 100,
                    "median_error": statistics.median(complex_errors) * 100,
                }

        return EstimationMetrics(
            total_items=len(recent),
            mean_error=mean_error,
            median_error=median_error,
            std_error=std_error,
            overestimate_rate=overestimate_rate,
            underestimate_rate=underestimate_rate,
            by_complexity=by_complexity
        )

    def identify_risk_patterns(
        self,
        min_occurrences: int = 3
    ) -> List[RiskPattern]:
        """Identify risk patterns from historical outcomes.

        Patterns detected:
        - Chronic underestimation (>50% underestimate)
        - Frequent blockers (>30% hit blockers)
        - High failure rate (>20% failures)
        - Complexity misestimation (consistent errors for complexity level)

        Args:
            min_occurrences: Minimum occurrences to flag pattern

        Returns:
            List of identified risk patterns
        """
        outcomes = self._load_outcomes()
        patterns = []

        if len(outcomes) < min_occurrences:
            return patterns

        # Pattern 1: Chronic underestimation
        underestimates = [o for o in outcomes if o.estimation_error > 0.2]  # >20% under
        if len(underestimates) >= min_occurrences:
            underestimate_rate = len(underestimates) / len(outcomes)
            if underestimate_rate > 0.5:
                patterns.append(RiskPattern(
                    pattern_id="chronic_underestimate",
                    pattern_type="estimation",
                    description=f"Chronic underestimation detected: {underestimate_rate*100:.0f}% of work takes longer than estimated",
                    occurrence_count=len(underestimates),
                    severity="high",
                    recommendation="Increase estimates by 30-50% or re-evaluate complexity assessment",
                    examples=[o.workstream_id for o in underestimates[:3]]
                ))

        # Pattern 2: Frequent blockers
        with_blockers = [o for o in outcomes if o.blockers_encountered]
        if len(with_blockers) >= min_occurrences:
            blocker_rate = len(with_blockers) / len(outcomes)
            if blocker_rate > 0.3:
                patterns.append(RiskPattern(
                    pattern_id="frequent_blockers",
                    pattern_type="blocker",
                    description=f"High blocker rate: {blocker_rate*100:.0f}% of work encounters blockers",
                    occurrence_count=len(with_blockers),
                    severity="medium",
                    recommendation="Improve dependency analysis and early risk identification",
                    examples=[o.workstream_id for o in with_blockers[:3]]
                ))

        # Pattern 3: High failure rate
        failures = [o for o in outcomes if not o.success]
        if len(failures) >= min_occurrences:
            failure_rate = len(failures) / len(outcomes)
            if failure_rate > 0.2:
                patterns.append(RiskPattern(
                    pattern_id="high_failure_rate",
                    pattern_type="failure",
                    description=f"High failure rate: {failure_rate*100:.0f}% of workstreams fail",
                    occurrence_count=len(failures),
                    severity="high",
                    recommendation="Review quality bar, improve scoping, or provide more support",
                    examples=[o.workstream_id for o in failures[:3]]
                ))

        # Pattern 4: Complexity-specific issues
        for complexity in ["simple", "medium", "complex"]:
            complex_outcomes = [o for o in outcomes if o.complexity == complexity]
            if len(complex_outcomes) >= min_occurrences:
                # Check for consistent underestimation
                underests = [o for o in complex_outcomes if o.estimation_error > 0.3]
                if len(underests) / len(complex_outcomes) > 0.6:
                    patterns.append(RiskPattern(
                        pattern_id=f"{complexity}_underestimate",
                        pattern_type="estimation",
                        description=f"{complexity.capitalize()} tasks consistently underestimated",
                        occurrence_count=len(underests),
                        severity="medium",
                        recommendation=f"Increase estimates for {complexity} tasks by 40-60%",
                        examples=[o.workstream_id for o in underests[:3]]
                    ))

        return patterns

    def get_improvement_suggestions(self) -> List[str]:
        """Get actionable improvement suggestions based on learning.

        Returns:
            List of suggestion strings
        """
        suggestions = []

        # Get recent metrics
        metrics = self.get_estimation_metrics(window_days=30)

        # Suggest based on estimation accuracy
        if metrics.total_items >= 5:
            if abs(metrics.mean_error) > 20:
                if metrics.mean_error > 0:
                    suggestions.append(
                        f"Estimates too low on average ({metrics.mean_error:.0f}% under). "
                        "Consider increasing estimates or breaking down work further."
                    )
                else:
                    suggestions.append(
                        f"Estimates too high on average ({-metrics.mean_error:.0f}% over). "
                        "Work is completing faster than expected - good sign!"
                    )

            if metrics.std_error > 50:
                suggestions.append(
                    "High variance in estimation accuracy. Consider using more "
                    "granular complexity classifications."
                )

        # Suggest based on risk patterns
        patterns = self.identify_risk_patterns()
        for pattern in patterns:
            if pattern.severity == "high":
                suggestions.append(f"🚨 {pattern.description} - {pattern.recommendation}")

        # Default suggestion if doing well
        if not suggestions and metrics.total_items >= 5:
            suggestions.append(
                "Estimation accuracy is good! Continue current approach."
            )

        return suggestions

    def get_adjusted_estimate(
        self,
        base_estimate: int,
        complexity: str = "medium"
    ) -> Tuple[int, float]:
        """Get learning-adjusted estimate for new work.

        Uses historical data to adjust estimates based on actual performance.

        Args:
            base_estimate: Original estimate in hours
            complexity: Complexity level (simple, medium, complex)

        Returns:
            (adjusted_estimate, confidence) tuple
        """
        metrics = self.get_estimation_metrics(window_days=60)

        if metrics.total_items < 3:
            # Not enough data, return base estimate
            return base_estimate, 0.5

        # Get complexity-specific adjustment
        adjustment_factor = 1.0
        confidence = 0.7

        if complexity in metrics.by_complexity:
            complexity_metrics = metrics.by_complexity[complexity]
            mean_error = complexity_metrics["mean_error"] / 100  # Convert from %

            # Adjust based on historical error
            # If we consistently underestimate by 30%, multiply by 1.3
            adjustment_factor = 1.0 + mean_error

            # Higher confidence if more data points
            if complexity_metrics["count"] >= 5:
                confidence = 0.9
            elif complexity_metrics["count"] >= 3:
                confidence = 0.8

        # Apply overall adjustment if no complexity-specific data
        elif metrics.total_items >= 5:
            mean_error = metrics.mean_error / 100
            adjustment_factor = 1.0 + (mean_error * 0.5)  # Apply 50% of overall error
            confidence = 0.6

        # Calculate adjusted estimate
        adjusted = int(base_estimate * adjustment_factor)

        # Clamp to reasonable range (50% to 300% of original)
        adjusted = max(
            int(base_estimate * 0.5),
            min(int(base_estimate * 3.0), adjusted)
        )

        return adjusted, confidence

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _load_outcomes(self) -> List[WorkstreamOutcome]:
        """Load outcomes from file."""
        if not self.outcomes_file.exists():
            return []

        import yaml
        with open(self.outcomes_file) as f:
            data = yaml.safe_load(f) or {}

        outcome_list = data.get("outcomes", [])
        return [WorkstreamOutcome.from_dict(o) for o in outcome_list]

    def _append_outcome(self, outcome: WorkstreamOutcome) -> None:
        """Append outcome to log."""
        outcomes = self._load_outcomes()
        outcomes.append(outcome)

        # Keep only last 500 outcomes
        if len(outcomes) > 500:
            outcomes = outcomes[-500:]

        # Save
        self.outcomes_file.parent.mkdir(parents=True, exist_ok=True)

        import yaml
        with open(self.outcomes_file, "w") as f:
            yaml.dump(
                {"outcomes": [o.to_dict() for o in outcomes]},
                f,
                default_flow_style=False
            )
