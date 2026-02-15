"""Metrics tracking for Code Pattern Recognizer Agent.

Tracks learning progress and pattern recognition accuracy.
"""

from amplihack_memory import ExperienceType, MemoryConnector


class PatternRecognitionMetrics:
    """Track pattern recognition accuracy and learning metrics.

    Attributes:
        memory: MemoryConnector instance
    """

    def __init__(self, memory: MemoryConnector):
        """Initialize metrics tracker.

        Args:
            memory: MemoryConnector instance
        """
        self.memory = memory

    def get_accuracy_stats(self) -> dict:
        """Get pattern recognition accuracy statistics.

        Returns:
            Dictionary with accuracy metrics:
            - true_positives: Count of validated patterns
            - false_positives: Count of incorrect patterns
            - accuracy: Recognition accuracy ratio
        """
        # Count pattern experiences
        patterns = self.memory.retrieve_experiences(experience_type=ExperienceType.PATTERN)

        # Count success/failure experiences
        successes = self.memory.retrieve_experiences(experience_type=ExperienceType.SUCCESS)

        failures = self.memory.retrieve_experiences(experience_type=ExperienceType.FAILURE)

        # Calculate metrics
        true_positives = len([p for p in patterns if p.confidence >= 0.7])
        false_positives = len([p for p in patterns if p.confidence < 0.7])

        total = true_positives + false_positives
        accuracy = true_positives / total if total > 0 else 0.0

        return {
            "true_positives": true_positives,
            "false_positives": false_positives,
            "accuracy": accuracy,
            "total_patterns": len(patterns),
            "successes": len(successes),
            "failures": len(failures),
        }

    def get_suggestion_stats(self) -> dict:
        """Get refactoring suggestion statistics.

        Returns:
            Dictionary with suggestion metrics:
            - total_suggestions: Total suggestions made
            - accepted_suggestions: Count of accepted suggestions
            - acceptance_rate: Ratio of accepted/total
        """
        # Count suggestions from success experiences
        successes = self.memory.retrieve_experiences(experience_type=ExperienceType.SUCCESS)

        # Extract suggestion counts from metadata
        total_suggestions = 0
        accepted_suggestions = 0

        for exp in successes:
            if "suggestions" in exp.metadata:
                total_suggestions += exp.metadata.get("suggestions", 0)
                accepted_suggestions += exp.metadata.get("accepted", 0)

        acceptance_rate = accepted_suggestions / total_suggestions if total_suggestions > 0 else 0.0

        return {
            "total_suggestions": total_suggestions,
            "accepted_suggestions": accepted_suggestions,
            "acceptance_rate": acceptance_rate,
        }

    def get_runtime_improvement(self) -> dict:
        """Calculate runtime improvement over time.

        Returns:
            Dictionary with runtime metrics:
            - first_run_time: Runtime of first analysis
            - latest_run_time: Runtime of latest analysis
            - improvement_percentage: Percentage improvement
        """
        successes = self.memory.retrieve_experiences(
            experience_type=ExperienceType.SUCCESS,
            limit=100,
        )

        if len(successes) < 2:
            return {
                "first_run_time": 0.0,
                "latest_run_time": 0.0,
                "improvement_percentage": 0.0,
            }

        # Get runtimes from metadata
        runtimes = []
        for exp in reversed(successes):
            if "runtime" in exp.metadata:
                runtimes.append(exp.metadata["runtime"])

        if len(runtimes) < 2:
            return {
                "first_run_time": 0.0,
                "latest_run_time": 0.0,
                "improvement_percentage": 0.0,
            }

        first_time = runtimes[0]
        latest_time = runtimes[-1]

        improvement = ((first_time - latest_time) / first_time * 100) if first_time > 0 else 0.0

        return {
            "first_run_time": first_time,
            "latest_run_time": latest_time,
            "improvement_percentage": improvement,
            "total_runs": len(runtimes),
        }

    def get_confidence_progression(self) -> dict:
        """Get confidence progression over time.

        Returns:
            Dictionary with confidence metrics:
            - average_confidence: Average pattern confidence
            - confidence_trend: List of confidence values over time
            - high_confidence_count: Count of high-confidence patterns
        """
        patterns = self.memory.retrieve_experiences(
            experience_type=ExperienceType.PATTERN,
            limit=100,
        )

        if not patterns:
            return {
                "average_confidence": 0.0,
                "confidence_trend": [],
                "high_confidence_count": 0,
            }

        # Calculate average
        avg_confidence = sum(p.confidence for p in patterns) / len(patterns)

        # Get trend (chronological)
        sorted_patterns = sorted(patterns, key=lambda p: p.timestamp)
        trend = [p.confidence for p in sorted_patterns]

        # High confidence count (>= 0.8)
        high_conf = len([p for p in patterns if p.confidence >= 0.8])

        return {
            "average_confidence": avg_confidence,
            "confidence_trend": trend,
            "high_confidence_count": high_conf,
            "total_patterns": len(patterns),
        }
