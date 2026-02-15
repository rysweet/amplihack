"""
Learning Metrics Tracker

Tracks and analyzes learning progress for the Documentation Analyzer agent.
"""

import json
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class AnalysisMetrics:
    """Metrics for a single documentation analysis."""

    timestamp: str
    url: str
    structure_score: float
    completeness_score: float
    clarity_score: float
    overall_score: float
    pattern_matches: int
    runtime_ms: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class LearningProgress:
    """Aggregate learning progress metrics."""

    total_analyses: int
    avg_overall_score: float
    avg_structure_score: float
    avg_completeness_score: float
    avg_clarity_score: float
    score_std_dev: float
    improvement_rate: float  # Percentage improvement from baseline
    trend: str  # 'improving', 'stable', 'declining'
    first_analysis_score: float
    latest_analysis_score: float
    score_improvement: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MetricsTracker:
    """
    Tracks learning metrics across multiple documentation analyses.

    Measures:
    - Quality score trends over time
    - Pattern recognition improvements
    - Runtime performance
    - Learning rate (how quickly the agent improves)
    """

    def __init__(self):
        """Initialize metrics tracker."""
        self.metrics_history: list[AnalysisMetrics] = []

    def record_analysis(
        self,
        url: str,
        structure_score: float,
        completeness_score: float,
        clarity_score: float,
        overall_score: float,
        pattern_matches: int,
        runtime_ms: float,
    ):
        """Record metrics from a single analysis."""
        metrics = AnalysisMetrics(
            timestamp=datetime.utcnow().isoformat(),
            url=url,
            structure_score=structure_score,
            completeness_score=completeness_score,
            clarity_score=clarity_score,
            overall_score=overall_score,
            pattern_matches=pattern_matches,
            runtime_ms=runtime_ms,
        )
        self.metrics_history.append(metrics)

    def get_learning_progress(self) -> LearningProgress | None:
        """Calculate learning progress from metrics history."""
        if not self.metrics_history:
            return None

        if len(self.metrics_history) == 1:
            m = self.metrics_history[0]
            return LearningProgress(
                total_analyses=1,
                avg_overall_score=m.overall_score,
                avg_structure_score=m.structure_score,
                avg_completeness_score=m.completeness_score,
                avg_clarity_score=m.clarity_score,
                score_std_dev=0.0,
                improvement_rate=0.0,
                trend="baseline",
                first_analysis_score=m.overall_score,
                latest_analysis_score=m.overall_score,
                score_improvement=0.0,
            )

        # Calculate averages
        overall_scores = [m.overall_score for m in self.metrics_history]
        structure_scores = [m.structure_score for m in self.metrics_history]
        completeness_scores = [m.completeness_score for m in self.metrics_history]
        clarity_scores = [m.clarity_score for m in self.metrics_history]

        avg_overall = statistics.mean(overall_scores)
        avg_structure = statistics.mean(structure_scores)
        avg_completeness = statistics.mean(completeness_scores)
        avg_clarity = statistics.mean(clarity_scores)

        # Calculate standard deviation
        score_std_dev = statistics.stdev(overall_scores) if len(overall_scores) > 1 else 0.0

        # Calculate improvement rate
        first_score = overall_scores[0]
        latest_score = overall_scores[-1]
        score_improvement = latest_score - first_score

        if first_score > 0:
            improvement_rate = (score_improvement / first_score) * 100
        else:
            improvement_rate = 0.0

        # Determine trend
        if len(overall_scores) >= 4:
            # Compare first half vs second half
            mid = len(overall_scores) // 2
            first_half_avg = statistics.mean(overall_scores[:mid])
            second_half_avg = statistics.mean(overall_scores[mid:])

            if second_half_avg > first_half_avg + 5:
                trend = "improving"
            elif second_half_avg < first_half_avg - 5:
                trend = "declining"
            else:
                trend = "stable"
        elif score_improvement > 5:
            trend = "improving"
        elif score_improvement < -5:
            trend = "declining"
        else:
            trend = "stable"

        return LearningProgress(
            total_analyses=len(self.metrics_history),
            avg_overall_score=avg_overall,
            avg_structure_score=avg_structure,
            avg_completeness_score=avg_completeness,
            avg_clarity_score=avg_clarity,
            score_std_dev=score_std_dev,
            improvement_rate=improvement_rate,
            trend=trend,
            first_analysis_score=first_score,
            latest_analysis_score=latest_score,
            score_improvement=score_improvement,
        )

    def export_metrics(self, filepath: str):
        """Export metrics to JSON file."""
        data = {
            "metrics_history": [m.to_dict() for m in self.metrics_history],
            "summary": self.get_learning_progress().to_dict() if self.metrics_history else None,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def import_metrics(self, filepath: str):
        """Import metrics from JSON file."""
        with open(filepath) as f:
            data = json.load(f)

        self.metrics_history = [AnalysisMetrics(**m) for m in data.get("metrics_history", [])]

    def clear_metrics(self):
        """Clear all metrics history."""
        self.metrics_history = []

    def get_improvement_summary(self) -> str:
        """Get human-readable improvement summary."""
        progress = self.get_learning_progress()
        if not progress:
            return "No analyses recorded yet."

        if progress.total_analyses == 1:
            return f"Baseline established: {progress.avg_overall_score:.1f}/100"

        improvement_desc = (
            "significant improvement"
            if progress.improvement_rate > 15
            else "moderate improvement"
            if progress.improvement_rate > 5
            else "slight improvement"
            if progress.improvement_rate > 0
            else "slight decline"
            if progress.improvement_rate > -5
            else "moderate decline"
            if progress.improvement_rate > -15
            else "significant decline"
        )

        return f"""Learning Progress Summary:
- Total Analyses: {progress.total_analyses}
- Average Quality: {progress.avg_overall_score:.1f}/100
- Trend: {progress.trend}
- Improvement: {progress.score_improvement:+.1f} points ({improvement_desc})
- First Score: {progress.first_analysis_score:.1f}
- Latest Score: {progress.latest_analysis_score:.1f}
- Improvement Rate: {progress.improvement_rate:+.1f}%
"""

    def demonstrate_learning(self) -> bool:
        """
        Check if the agent demonstrates measurable learning.

        Returns True if:
        - At least 3 analyses recorded
        - Latest score is >= 15% better than first score
        """
        progress = self.get_learning_progress()
        if not progress or progress.total_analyses < 3:
            return False

        return progress.improvement_rate >= 15.0
