"""Caching utilities - Batch 313"""

import time
from typing import Any, Optional, Dict

class SimpleCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, ttl_seconds: float = 300):
        self.ttl = ttl_seconds
        self._cache: Dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache with current timestamp."""
        self._cache[key] = (value, time.time())

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def cleanup(self) -> int:
        """Remove expired entries and return count removed."""
        now = time.time()
        expired = [k for k, (_, ts) in self._cache.items() if now - ts >= self.ttl]
        for key in expired:
            del self._cache[key]
        return len(expired)
