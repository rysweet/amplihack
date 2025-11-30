"""Rate limiter for controlling API request frequency."""

import threading
import time


class RateLimiter:
    """Thread-safe rate limiter using token bucket algorithm.

    Limits requests to a specified rate (requests per second).
    """

    def __init__(self, requests_per_second: float = 10.0):
        """Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second (default: 10)
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second  # Time between requests
        self._last_request_time = 0.0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a request can be made within rate limits.

        This method is thread-safe and will block the calling thread
        until it's safe to make a request without exceeding the rate limit.
        """
        with self._lock:
            now = time.time()

            # Calculate how long we need to wait based on the last request
            time_since_last = now - self._last_request_time
            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                time.sleep(wait_time)
                now = time.time()

            # Update last request time
            self._last_request_time = now

    def reset(self) -> None:
        """Reset the rate limiter, clearing all timestamps."""
        with self._lock:
            self._last_request_time = 0.0
