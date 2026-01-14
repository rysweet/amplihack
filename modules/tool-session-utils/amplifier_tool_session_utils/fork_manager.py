"""
Fork manager for handling session forking based on duration.

Monitors session duration and triggers fork before hitting time limits.
"""

import threading
import time
from typing import Any


class ForkManager:
    """Manages session forking based on elapsed duration.

    Monitors session duration and provides fork control at configurable
    threshold to stay under hard time limits.
    """

    # Default fork threshold (60 minutes)
    DEFAULT_THRESHOLD = 3600.0

    # Minimum threshold (5 minutes)
    MIN_THRESHOLD = 300.0

    # Maximum threshold (68 minutes - under typical 69-min hard limit)
    MAX_THRESHOLD = 4080.0

    def __init__(
        self,
        start_time: float = 0.0,
        fork_threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        """Initialize fork manager.

        Args:
            start_time: Session start timestamp (use time.time())
            fork_threshold: Seconds before triggering fork (default 3600 = 60 min)
        """
        self.start_time = start_time
        self._fork_count = 0
        self._lock = threading.RLock()

        # Validate threshold is reasonable
        if fork_threshold < self.MIN_THRESHOLD:
            self.fork_threshold = self.MIN_THRESHOLD
        elif fork_threshold > self.MAX_THRESHOLD:
            self.fork_threshold = self.MAX_THRESHOLD
        else:
            self.fork_threshold = fork_threshold

    def should_fork(self) -> bool:
        """Check if fork needed based on elapsed time.

        Returns:
            True if elapsed time >= fork_threshold, False otherwise
        """
        if self.start_time == 0:
            return False

        elapsed = time.time() - self.start_time
        return elapsed >= self.fork_threshold

    def trigger_fork(self, options: Any | None = None) -> Any:
        """Trigger fork by setting fork flag on options.

        Args:
            options: Session options object (or None)

        Returns:
            Modified options with fork flag set
        """
        with self._lock:
            self._fork_count += 1

        if options is not None and hasattr(options, "__dict__"):
            if hasattr(options, "fork_session"):
                options.fork_session = True
            else:
                options.fork_session = True

        return options

    def get_fork_count(self) -> int:
        """Get number of forks executed in this session."""
        with self._lock:
            return self._fork_count

    def reset(self) -> None:
        """Reset fork manager for new session."""
        with self._lock:
            self.start_time = time.time()
            self._fork_count = 0

    def get_elapsed_time(self) -> float:
        """Get elapsed time since session start."""
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time

    def get_time_until_fork(self) -> float:
        """Get remaining time until fork threshold."""
        if self.start_time == 0:
            return self.fork_threshold
        elapsed = self.get_elapsed_time()
        return self.fork_threshold - elapsed

    def get_status(self) -> dict[str, Any]:
        """Get current fork manager status."""
        elapsed = self.get_elapsed_time()
        remaining = self.get_time_until_fork()

        return {
            "started": self.start_time > 0,
            "elapsed_seconds": round(elapsed, 1),
            "elapsed_minutes": round(elapsed / 60, 1),
            "remaining_seconds": round(remaining, 1),
            "remaining_minutes": round(remaining / 60, 1),
            "threshold_minutes": round(self.fork_threshold / 60, 1),
            "fork_count": self._fork_count,
            "should_fork": self.should_fork(),
        }
