"""Common session management utilities."""

import logging
import time
import uuid
from typing import Optional


def generate_session_id(prefix: str = "session") -> str:
    """Generate unique session ID.

    Args:
        prefix: Prefix for session ID

    Returns:
        Unique session ID string
    """
    timestamp = int(time.time())
    unique_id = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{unique_id}"


def setup_logger(
    name: str,
    level: str = "INFO",
    enable_logging: bool = True,
    formatter: Optional[logging.Formatter] = None,
) -> logging.Logger:
    """Setup logger with standard configuration.

    Args:
        name: Logger name
        level: Logging level (e.g., "INFO", "DEBUG")
        enable_logging: Whether to enable logging
        formatter: Optional custom formatter

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers and enable_logging:
        handler = logging.StreamHandler()

        if formatter is None:
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


class Statistics:
    """Simple statistics tracker."""

    def __init__(self):
        """Initialize statistics."""
        self.counts = {}
        self.totals = {}
        self.start_time = time.time()

    def increment(self, key: str, amount: int = 1) -> None:
        """Increment counter.

        Args:
            key: Counter key
            amount: Amount to increment
        """
        self.counts[key] = self.counts.get(key, 0) + amount

    def add(self, key: str, value: float) -> None:
        """Add value to total.

        Args:
            key: Total key
            value: Value to add
        """
        self.totals[key] = self.totals.get(key, 0) + value

    def get_count(self, key: str, default: int = 0) -> int:
        """Get counter value.

        Args:
            key: Counter key
            default: Default value if not found

        Returns:
            Counter value
        """
        return self.counts.get(key, default)

    def get_total(self, key: str, default: float = 0.0) -> float:
        """Get total value.

        Args:
            key: Total key
            default: Default value if not found

        Returns:
            Total value
        """
        return self.totals.get(key, default)

    def get_average(self, total_key: str, count_key: str, default: float = 0.0) -> float:
        """Calculate average value.

        Args:
            total_key: Key for total
            count_key: Key for count
            default: Default if count is 0

        Returns:
            Average value
        """
        count = self.get_count(count_key)
        if count == 0:
            return default
        return self.get_total(total_key) / count

    def get_elapsed(self) -> float:
        """Get elapsed time since creation in seconds.

        Returns:
            Elapsed time
        """
        return time.time() - self.start_time

    def to_dict(self) -> dict:
        """Convert statistics to dictionary.

        Returns:
            Dict with all statistics
        """
        return {
            "counts": self.counts,
            "totals": self.totals,
            "elapsed_seconds": self.get_elapsed(),
        }
