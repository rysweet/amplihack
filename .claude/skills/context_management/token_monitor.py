"""Token monitoring brick for context management.

This module provides token usage monitoring and threshold detection,
helping users proactively manage their context window.
"""

from .models import UsageStats

# Default configuration
DEFAULT_MAX_TOKENS = 1_000_000

# Model-specific thresholds
# For large models (1M tokens): Be conservative (top threshold = 50%)
# For small models (200k tokens): Be aggressive (top threshold = 85%)
THRESHOLDS_1M = {
    "ok": 0.2,  # 0-20%: All good
    "consider": 0.3,  # 30%+: Consider snapshotting (auto-snapshot)
    "recommended": 0.4,  # 40%+: Snapshot recommended (auto-snapshot)
    "urgent": 0.5,  # 50%+: Snapshot urgent (auto-snapshot)
}

THRESHOLDS_SMALL = {
    "ok": 0.4,  # 0-40%: All good
    "consider": 0.55,  # 55%+: Consider snapshotting (auto-snapshot)
    "recommended": 0.7,  # 70%+: Snapshot recommended (auto-snapshot)
    "urgent": 0.85,  # 85%+: Snapshot urgent (auto-snapshot)
}


def get_thresholds_for_model(max_tokens: int) -> dict:
    """Get appropriate thresholds based on model size.

    Args:
        max_tokens: Maximum context window size

    Returns:
        Dict of thresholds appropriate for the model
    """
    # Large models (800k+): Use conservative thresholds (top = 50%)
    if max_tokens >= 800_000:
        return THRESHOLDS_1M
    # Small models (< 800k): Use aggressive thresholds (top = 85%)
    return THRESHOLDS_SMALL


class TokenMonitor:
    """Monitors token usage and calculates thresholds.

    This brick tracks current token usage against the maximum context window
    and provides recommendations based on configurable thresholds.

    Attributes:
        current_usage: Current token count (updated via check_usage)
        max_tokens: Maximum context window size
        thresholds: Named threshold percentages
    """

    def __init__(self, max_tokens: int = DEFAULT_MAX_TOKENS):
        """Initialize token monitor with context window size.

        Args:
            max_tokens: Maximum context window size (default: 1,000,000)
        """
        self.max_tokens = max_tokens
        # Use model-appropriate thresholds
        self.thresholds = get_thresholds_for_model(max_tokens)
        self.current_usage = 0

    def check_usage(self, current_tokens: int) -> UsageStats:
        """Check current usage against thresholds.

        Args:
            current_tokens: Current token count from system

        Returns:
            UsageStats with usage info, percentage, threshold status, and recommendation

        Example:
            >>> monitor = TokenMonitor()
            >>> stats = monitor.check_usage(750_000)
            >>> stats.threshold_status
            'consider'
            >>> stats.percentage
            75.0
        """
        self.current_usage = current_tokens
        percentage = (current_tokens / self.max_tokens) * 100
        threshold_status = self._get_threshold_status(percentage / 100)
        recommendation = self.get_recommendation(percentage)

        return UsageStats(
            current_tokens=current_tokens,
            max_tokens=self.max_tokens,
            percentage=round(percentage, 2),
            threshold_status=threshold_status,
            recommendation=recommendation,
        )

    def _get_threshold_status(self, percentage_decimal: float) -> str:
        """Determine threshold status from percentage.

        Args:
            percentage_decimal: Usage as decimal (0.0-1.0)

        Returns:
            One of: 'ok', 'consider', 'recommended', 'urgent'
        """
        if percentage_decimal >= self.thresholds["urgent"]:
            return "urgent"
        if percentage_decimal >= self.thresholds["recommended"]:
            return "recommended"
        if percentage_decimal >= self.thresholds["consider"]:
            return "consider"
        return "ok"

    def get_recommendation(self, percentage: float) -> str:
        """Get action recommendation based on usage percentage.

        Args:
            percentage: Usage percentage (0-100)

        Returns:
            Human-readable recommendation message

        Example:
            >>> monitor = TokenMonitor()
            >>> monitor.get_recommendation(45.0)
            'Context is healthy. No action needed.'
            >>> monitor.get_recommendation(87.0)
            'Snapshot recommended. Create a snapshot to preserve context before approaching limit.'
        """
        if percentage >= 95:
            return (
                "URGENT: Context window nearly full. Create snapshot immediately "
                "to preserve work before compaction."
            )
        if percentage >= 85:
            return (
                "Snapshot recommended. Create a snapshot to preserve context "
                "before approaching limit."
            )
        if percentage >= 70:
            return "Consider creating a snapshot soon. Context usage is rising."
        return "Context is healthy. No action needed."

    def get_tokens_until_threshold(self, threshold_name: str) -> int:
        """Calculate tokens remaining until a specific threshold.

        Args:
            threshold_name: One of 'consider', 'recommended', 'urgent'

        Returns:
            Number of tokens until threshold reached

        Raises:
            ValueError: If threshold_name is invalid
        """
        if threshold_name not in self.thresholds:
            raise ValueError(
                f"Invalid threshold '{threshold_name}'. "
                f"Must be one of: {list(self.thresholds.keys())}"
            )

        threshold_tokens = int(self.max_tokens * self.thresholds[threshold_name])
        return max(0, threshold_tokens - self.current_usage)
