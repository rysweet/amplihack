"""Rate limiting with Retry-After header support.

Philosophy:
- Track rate limit state per endpoint
- Respect server Retry-After headers
- Support both numeric seconds and HTTP-date formats
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime


@dataclass
class RateLimitState:
    """Track rate limit state for an endpoint."""

    is_limited: bool = False
    retry_after: int = 0
    blocked_until: float = 0
    consecutive_429s: int = 0


class RateLimiter:
    """Handle 429 responses and respect Retry-After headers."""

    def __init__(self, default_retry_after: int = 60):
        self.default_retry_after = default_retry_after
        self._state: dict[str, RateLimitState] = {}
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, endpoint: str) -> float | None:
        """Check if endpoint is rate limited. Returns seconds to wait or None."""
        async with self._lock:
            state = self._state.get(endpoint)
            if not state:
                return None
            now = time.time()
            if state.blocked_until > now:
                return state.blocked_until - now
            return None

    async def record_rate_limit(self, endpoint: str, retry_after: int | None = None) -> int:
        """Record a 429 response. Returns seconds to wait."""
        async with self._lock:
            if endpoint not in self._state:
                self._state[endpoint] = RateLimitState()
            state = self._state[endpoint]
            state.consecutive_429s += 1
            state.is_limited = True
            wait_time = retry_after if retry_after else self.default_retry_after
            if state.consecutive_429s > 1:
                wait_time = min(wait_time * state.consecutive_429s, 3600)
            state.retry_after = wait_time
            state.blocked_until = time.time() + wait_time
            return wait_time

    async def clear_rate_limit(self, endpoint: str) -> None:
        """Clear rate limit state after successful request."""
        async with self._lock:
            if endpoint in self._state:
                self._state[endpoint] = RateLimitState()

    def parse_retry_after(self, headers: dict[str, str]) -> int | None:
        """Parse Retry-After header (seconds or HTTP-date)."""
        retry_after = headers.get("Retry-After") or headers.get("retry-after")
        if not retry_after:
            return None
        try:
            return max(0, int(retry_after))
        except ValueError:
            pass
        try:
            dt = parsedate_to_datetime(retry_after)
            return max(0, int(dt.timestamp() - time.time()))
        except (ValueError, TypeError):
            return None


__all__ = ["RateLimitState", "RateLimiter"]
