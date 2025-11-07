"""Fork manager for handling SDK session forking based on duration.

Monitors session duration and triggers SDK fork before hitting the
69-minute (4129 seconds) hard limit.
"""

import threading
import time
from typing import Any, Optional

# Try to import SDK, gracefully handle if unavailable
try:
    from claude_agent_sdk import ClaudeAgentOptions
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    ClaudeAgentOptions = None  # type: ignore


class ForkManager:
    """Manages session forking based on elapsed duration.

    Monitors session duration and triggers SDK fork at configurable threshold
    (default 60 minutes) to stay under the 69-minute hard limit.
    """

    def __init__(self, start_time: float = 0.0, fork_threshold: float = 3600.0) -> None:
        """Initialize fork manager.

        Args:
            start_time: Session start timestamp (use time.time())
            fork_threshold: Seconds before triggering fork (default 3600 = 60 min)
        """
        self.start_time = start_time
        self.fork_threshold = fork_threshold
        self._fork_count = 0
        self._lock = threading.RLock()  # Thread safety for concurrent access

        # Validate threshold is reasonable (between 5 min and 68 min)
        if fork_threshold < 300:  # 5 minutes minimum
            self.fork_threshold = 300
        elif fork_threshold > 4080:  # 68 minutes maximum
            self.fork_threshold = 4080

    def should_fork(self) -> bool:
        """Check if fork needed based on elapsed time.

        Returns:
            True if elapsed time >= fork_threshold, False otherwise

        Side Effects:
            None (read-only check)
        """
        if self.start_time == 0:
            return False  # Not started yet

        elapsed = time.time() - self.start_time
        return elapsed >= self.fork_threshold

    def trigger_fork(self, options: Optional[Any] = None) -> Any:
        """Trigger SDK fork by setting fork_session flag.

        Args:
            options: Current ClaudeAgentOptions instance (or None)

        Returns:
            Modified options with fork_session=True, or new options if None

        Side Effects:
            Increments internal fork counter
        """
        with self._lock:
            self._fork_count += 1

        # If SDK not available, return options unchanged
        if not CLAUDE_SDK_AVAILABLE:
            return options

        # If no options provided and SDK available, create new options
        if options is None and ClaudeAgentOptions is not None:
            options = ClaudeAgentOptions()

        # Set fork flag if options object supports it
        if options is not None and hasattr(options, "__dict__"):
            # Some SDK versions use fork_session, others use session_fork
            if hasattr(options, "fork_session"):
                options.fork_session = True
            elif "fork_session" not in options.__dict__:
                # Dynamically add attribute if needed
                options.fork_session = True

        return options

    def get_fork_count(self) -> int:
        """Get number of forks executed in this session.

        Returns:
            Fork count (0 = no forks, 1 = one fork, etc.)

        Side Effects:
            None (read-only)
        """
        with self._lock:
            return self._fork_count

    def reset(self) -> None:
        """Reset fork manager for new session.

        Side Effects:
            Resets start time and fork counter
        """
        with self._lock:
            self.start_time = time.time()
            self._fork_count = 0

    def get_elapsed_time(self) -> float:
        """Get elapsed time since session start.

        Returns:
            Elapsed seconds, or 0 if not started
        """
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time

    def get_time_until_fork(self) -> float:
        """Get remaining time until fork threshold.

        Returns:
            Seconds until fork (negative if already past threshold)
        """
        if self.start_time == 0:
            return self.fork_threshold

        elapsed = self.get_elapsed_time()
        return self.fork_threshold - elapsed
