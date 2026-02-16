"""
Bug Predictor Metrics

Tracks learning metrics and prediction accuracy for the bug predictor agent.
"""

from typing import Any

try:
    from amplihack_memory import ExperienceType, MemoryConnector
except ImportError:
    raise ImportError(
        "amplihack-memory-lib is required. Install with: pip install amplihack-memory-lib"
    )


class BugPredictorMetrics:
    """Track bug prediction accuracy and learning metrics."""

    def __init__(self, memory: MemoryConnector):
        """Initialize metrics tracker."""
        self.memory = memory

    def get_accuracy_stats(self) -> dict[str, Any]:
        """
        Get bug prediction accuracy statistics.

        Returns:
            Dictionary with accuracy metrics:
            - true_positives: Count of correctly predicted bugs
            - false_positives: Count of incorrect predictions
            - accuracy: Prediction accuracy ratio
            - precision: True positives / (true positives + false positives)
        """
        # Retrieve all bug patterns
        patterns = self.memory.retrieve_experiences(
            experience_type=ExperienceType.PATTERN, limit=200
        )

        # Count by confidence
        high_confidence = [p for p in patterns if p.outcome.get("confidence", 0) >= 0.7]
        medium_confidence = [p for p in patterns if 0.4 <= p.outcome.get("confidence", 0) < 0.7]
        low_confidence = [p for p in patterns if p.outcome.get("confidence", 0) < 0.4]

        # Estimate true positives (high confidence patterns are more likely correct)
        true_positives = len(high_confidence)
        false_positives = len(low_confidence)

        total = true_positives + false_positives
        accuracy = true_positives / total if total > 0 else 0.0
        precision = (
            true_positives / (true_positives + len(medium_confidence))
            if (true_positives + len(medium_confidence)) > 0
            else 0.0
        )

        return {
            "true_positives": true_positives,
            "false_positives": false_positives,
            "accuracy": accuracy,
            "precision": precision,
            "total_patterns": len(patterns),
            "high_confidence": len(high_confidence),
            "medium_confidence": len(medium_confidence),
            "low_confidence": len(low_confidence),
        }

    def get_detection_rate_stats(self) -> dict[str, Any]:
        """
        Get bug detection rate statistics.

        Returns:
            Dictionary with detection metrics:
            - total_analyses: Total code analyses performed
            - total_bugs_found: Total bugs detected
            - avg_bugs_per_file: Average bugs per analyzed file
            - critical_bugs: Count of critical severity bugs
        """
        # Retrieve all predictions
        predictions = self.memory.retrieve_experiences(
            experience_type=ExperienceType.SUCCESS, limit=200
        )
        predictions.extend(
            self.memory.retrieve_experiences(experience_type=ExperienceType.FAILURE, limit=200)
        )

        if not predictions:
            return {
                "total_analyses": 0,
                "total_bugs_found": 0,
                "avg_bugs_per_file": 0.0,
                "critical_bugs": 0,
            }

        total_bugs = 0
        critical_bugs = 0

        for pred in predictions:
            outcome = pred.outcome
            if isinstance(outcome, dict):
                total_bugs += outcome.get("total_issues", 0)
                critical_bugs += outcome.get("critical_issues", 0)

        avg_bugs = total_bugs / len(predictions) if predictions else 0.0

        return {
            "total_analyses": len(predictions),
            "total_bugs_found": total_bugs,
            "avg_bugs_per_file": avg_bugs,
            "critical_bugs": critical_bugs,
            "detection_rate": total_bugs / len(predictions) if predictions else 0.0,
        }

    def get_confidence_progression(self) -> dict[str, Any]:
        """
        Get confidence score progression over time.

        Returns:
            Dictionary with confidence metrics:
            - average_confidence: Average confidence across all predictions
            - confidence_trend: List of confidence values chronologically
            - high_confidence_percentage: Percentage of high-confidence predictions
        """
        # Retrieve bug patterns
        patterns = self.memory.retrieve_experiences(
            experience_type=ExperienceType.PATTERN, limit=100
        )

        if not patterns:
            return {
                "average_confidence": 0.0,
                "confidence_trend": [],
                "high_confidence_percentage": 0.0,
            }

        # Extract confidence scores
        confidences = [
            p.outcome.get("confidence", 0.0) for p in patterns if isinstance(p.outcome, dict)
        ]

        if not confidences:
            return {
                "average_confidence": 0.0,
                "confidence_trend": [],
                "high_confidence_percentage": 0.0,
            }

        avg_confidence = sum(confidences) / len(confidences)
        high_conf_count = sum(1 for c in confidences if c >= 0.7)
        high_conf_pct = high_conf_count / len(confidences) * 100

        # Sort chronologically for trend
        sorted_patterns = sorted(patterns, key=lambda p: p.timestamp)
        trend = [
            p.outcome.get("confidence", 0.0) for p in sorted_patterns if isinstance(p.outcome, dict)
        ]

        return {
            "average_confidence": avg_confidence,
            "confidence_trend": trend,
            "high_confidence_percentage": high_conf_pct,
            "total_patterns": len(patterns),
        }

    def get_learning_improvement(self) -> dict[str, Any]:
        """
        Calculate learning improvement over time.

        Measures:
        - Accuracy improvement (first half vs second half)
        - Runtime improvement (faster analysis over time)
        - Pattern usage increase (more learned patterns applied)

        Returns:
            Dictionary with improvement metrics showing >10% improvement target
        """
        # Get all predictions chronologically
        predictions = self.memory.retrieve_experiences(
            experience_type=ExperienceType.SUCCESS, limit=100
        )
        predictions.extend(
            self.memory.retrieve_experiences(experience_type=ExperienceType.FAILURE, limit=100)
        )

        # Sort by timestamp
        predictions = sorted(predictions, key=lambda p: p.timestamp)

        if len(predictions) < 4:
            return {
                "accuracy_improvement": 0.0,
                "runtime_improvement": 0.0,
                "pattern_usage_improvement": 0.0,
                "overall_improvement": 0.0,
                "meets_target": False,
            }

        # Split into first half and second half
        mid = len(predictions) // 2
        first_half = predictions[:mid]
        second_half = predictions[mid:]

        # Calculate accuracy improvement (using confidence as proxy)
        first_half_accuracy = self._calculate_avg_confidence(first_half)
        second_half_accuracy = self._calculate_avg_confidence(second_half)
        accuracy_improvement = (
            (second_half_accuracy - first_half_accuracy) / max(first_half_accuracy, 0.01)
        ) * 100

        # Calculate runtime improvement
        first_half_runtime = self._calculate_avg_runtime(first_half)
        second_half_runtime = self._calculate_avg_runtime(second_half)
        runtime_improvement = (
            (first_half_runtime - second_half_runtime) / max(first_half_runtime, 0.01)
        ) * 100

        # Calculate pattern usage improvement
        first_half_patterns = self._calculate_avg_patterns(first_half)
        second_half_patterns = self._calculate_avg_patterns(second_half)
        pattern_improvement = (
            (second_half_patterns - first_half_patterns) / max(first_half_patterns, 0.01)
        ) * 100

        # Overall improvement (weighted average)
        overall_improvement = (
            accuracy_improvement * 0.5 + runtime_improvement * 0.2 + pattern_improvement * 0.3
        )

        meets_target = overall_improvement >= 10.0

        return {
            "accuracy_improvement": accuracy_improvement,
            "runtime_improvement": runtime_improvement,
            "pattern_usage_improvement": pattern_improvement,
            "overall_improvement": overall_improvement,
            "meets_target": meets_target,
            "first_half_analyses": len(first_half),
            "second_half_analyses": len(second_half),
            "first_half_accuracy": first_half_accuracy,
            "second_half_accuracy": second_half_accuracy,
        }

    def _calculate_avg_confidence(self, experiences: list[Any]) -> float:
        """Calculate average confidence from experiences."""
        confidences = []
        for exp in experiences:
            outcome = exp.outcome
            if isinstance(outcome, dict):
                # For predictions, calculate average confidence
                high_count = outcome.get("high_confidence_count", 0)
                total = outcome.get("total_issues", 0)
                if total > 0:
                    confidences.append(high_count / total)

        return sum(confidences) / len(confidences) if confidences else 0.0

    def _calculate_avg_runtime(self, experiences: list[Any]) -> float:
        """Calculate average runtime from experiences."""
        runtimes = []
        for exp in experiences:
            metadata = exp.metadata
            if isinstance(metadata, dict):
                runtime = metadata.get("runtime", 0)
                if runtime > 0:
                    runtimes.append(runtime)

        return sum(runtimes) / len(runtimes) if runtimes else 0.0

    def _calculate_avg_patterns(self, experiences: list[Any]) -> float:
        """Calculate average pattern usage from experiences."""
        patterns = []
        for exp in experiences:
            outcome = exp.outcome
            if isinstance(outcome, dict):
                used = outcome.get("used_learned_patterns", 0)
                patterns.append(used)

        return sum(patterns) / len(patterns) if patterns else 0.0

    def get_bug_type_distribution(self) -> dict[str, int]:
        """
        Get distribution of detected bug types.

        Returns:
            Dictionary mapping bug type to count
        """
        patterns = self.memory.retrieve_experiences(
            experience_type=ExperienceType.PATTERN, limit=500
        )

        distribution = {}
        for pattern in patterns:
            outcome = pattern.outcome
            if isinstance(outcome, dict):
                bug_type = outcome.get("bug_type", "unknown")
                distribution[bug_type] = distribution.get(bug_type, 0) + 1

        return distribution

    def get_severity_distribution(self) -> dict[str, int]:
        """
        Get distribution of bug severities.

        Returns:
            Dictionary mapping severity to count
        """
        patterns = self.memory.retrieve_experiences(
            experience_type=ExperienceType.PATTERN, limit=500
        )

        distribution = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for pattern in patterns:
            outcome = pattern.outcome
            if isinstance(outcome, dict):
                severity = outcome.get("severity", "low")
                if severity in distribution:
                    distribution[severity] += 1

        return distribution
