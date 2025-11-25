"""Simple in-memory rate limiter for authentication endpoints.

Philosophy:
- Ruthless simplicity: In-memory implementation (use Redis in production)
- Working implementation: Fully functional rate limiting
- Self-contained: No external dependencies
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Deque, Tuple


class RateLimiter:
    """Simple sliding window rate limiter."""

    def __init__(self, requests_per_minute: int = 10):
        """
        Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute per IP
        """
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, Deque[datetime]] = defaultdict(deque)
        self.window_size = timedelta(minutes=1)

    def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if a request is allowed for the given identifier.

        Args:
            identifier: Unique identifier (e.g., IP address)

        Returns:
            Tuple of (allowed, remaining_requests)
        """
        now = datetime.now()
        request_times = self.requests[identifier]

        # Remove old requests outside the window
        while request_times and request_times[0] < now - self.window_size:
            request_times.popleft()

        # Check if limit exceeded
        if len(request_times) >= self.requests_per_minute:
            remaining = 0
            return False, remaining

        # Allow the request and record it
        request_times.append(now)
        remaining = self.requests_per_minute - len(request_times)
        return True, remaining

    def reset(self, identifier: str) -> None:
        """
        Reset the rate limit for a specific identifier.

        Args:
            identifier: The identifier to reset
        """
        if identifier in self.requests:
            del self.requests[identifier]

    def get_reset_time(self, identifier: str) -> datetime:
        """
        Get the time when the rate limit will reset.

        Args:
            identifier: The identifier to check

        Returns:
            The reset time
        """
        request_times = self.requests.get(identifier, deque())
        if request_times:
            return request_times[0] + self.window_size
        return datetime.now()


# Global rate limiters for different endpoint groups
login_rate_limiter = RateLimiter(requests_per_minute=5)  # Strict for login
register_rate_limiter = RateLimiter(requests_per_minute=3)  # Very strict for registration
general_rate_limiter = RateLimiter(requests_per_minute=60)  # More lenient for general endpoints
