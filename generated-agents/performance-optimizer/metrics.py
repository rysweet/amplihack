"""
Performance metrics and learning statistics for the Performance Optimizer agent.
"""

from dataclasses import dataclass


@dataclass
class LearningMetrics:
    """Metrics tracking the agent's learning progress."""

    # Experience counts
    total_analyses: int
    total_optimizations: int
    successful_optimizations: int

    # Performance metrics
    avg_speedup: float
    avg_confidence: float
    max_speedup: float

    # Learning progress
    trend: str  # "improving", "stable", "declining", "no_data"
    confidence_improvement: float  # Change in average confidence over time

    # Technique-specific metrics
    technique_metrics: dict[str, dict[str, float]]

    def get_learning_rate(self) -> float:
        """Calculate learning rate (how much confidence has improved)."""
        if self.total_analyses == 0:
            return 0.0
        return self.confidence_improvement / max(self.total_analyses, 1)

    def is_improving(self) -> bool:
        """Check if the agent is improving over time."""
        return self.trend == "improving" or self.confidence_improvement > 0.1

    def get_best_technique(self) -> str | None:
        """Get the most effective optimization technique."""
        if not self.technique_metrics:
            return None

        best_technique = None
        best_score = 0.0

        for technique, metrics in self.technique_metrics.items():
            # Score combines speedup and confidence
            score = metrics.get("avg_speedup", 1.0) * metrics.get("confidence", 0.5)
            if score > best_score:
                best_score = score
                best_technique = technique

        return best_technique

    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return {
            "total_analyses": self.total_analyses,
            "total_optimizations": self.total_optimizations,
            "successful_optimizations": self.successful_optimizations,
            "avg_speedup": self.avg_speedup,
            "avg_confidence": self.avg_confidence,
            "max_speedup": self.max_speedup,
            "trend": self.trend,
            "confidence_improvement": self.confidence_improvement,
            "technique_metrics": self.technique_metrics,
            "learning_rate": self.get_learning_rate(),
            "is_improving": self.is_improving(),
            "best_technique": self.get_best_technique(),
        }


def calculate_metrics_from_stats(stats: dict) -> LearningMetrics:
    """
    Calculate learning metrics from agent statistics.

    Args:
        stats: Statistics dictionary from agent.get_learning_stats()

    Returns:
        LearningMetrics instance
    """
    total_optimizations = stats.get("total_optimizations", 0)
    avg_speedup = stats.get("avg_speedup", 1.0)
    trend = stats.get("trend", "no_data")

    # Calculate confidence improvement
    technique_effectiveness = stats.get("technique_effectiveness", {})
    confidence_values = [t.get("confidence", 0.5) for t in technique_effectiveness.values()]
    avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.5

    # Estimate confidence improvement from trend
    first_half = stats.get("first_half_avg", 1.0)
    second_half = stats.get("second_half_avg", 1.0)
    confidence_improvement = (second_half - first_half) / max(first_half, 0.1)

    # Count successful optimizations (speedup > 1.1)
    successful = sum(1 for t in technique_effectiveness.values() if t.get("avg_speedup", 1.0) > 1.1)

    return LearningMetrics(
        total_analyses=total_optimizations,
        total_optimizations=total_optimizations,
        successful_optimizations=successful,
        avg_speedup=avg_speedup,
        avg_confidence=avg_confidence,
        max_speedup=stats.get("max_speedup", 1.0),
        trend=trend,
        confidence_improvement=confidence_improvement,
        technique_metrics=technique_effectiveness,
    )


def format_metrics_report(metrics: LearningMetrics) -> str:
    """
    Format metrics as human-readable report.

    Args:
        metrics: LearningMetrics instance

    Returns:
        Formatted report string
    """
    report = []
    report.append("=== Performance Optimizer Learning Metrics ===\n")

    report.append(f"Total Analyses: {metrics.total_analyses}")
    report.append(f"Total Optimizations: {metrics.total_optimizations}")
    report.append(f"Successful Optimizations: {metrics.successful_optimizations}")
    report.append(
        f"Success Rate: {metrics.successful_optimizations / max(metrics.total_optimizations, 1):.1%}\n"
    )

    report.append(f"Average Speedup: {metrics.avg_speedup:.2f}x")
    report.append(f"Maximum Speedup: {metrics.max_speedup:.2f}x")
    report.append(f"Average Confidence: {metrics.avg_confidence:.2%}\n")

    report.append(f"Learning Trend: {metrics.trend}")
    report.append(f"Confidence Improvement: {metrics.confidence_improvement:+.2%}")
    report.append(f"Learning Rate: {metrics.get_learning_rate():.3f}\n")

    report.append(f"Currently Improving: {'Yes' if metrics.is_improving() else 'No'}")
    best = metrics.get_best_technique()
    if best:
        report.append(f"Best Technique: {best}\n")

    if metrics.technique_metrics:
        report.append("=== Technique Effectiveness ===")
        for technique, data in sorted(
            metrics.technique_metrics.items(),
            key=lambda x: x[1].get("avg_speedup", 0),
            reverse=True,
        ):
            speedup = data.get("avg_speedup", 1.0)
            confidence = data.get("confidence", 0.5)
            uses = data.get("uses", 0)
            report.append(
                f"{technique:30s} {speedup:6.2f}x  confidence={confidence:.2%}  uses={uses}"
            )

    return "\n".join(report)
