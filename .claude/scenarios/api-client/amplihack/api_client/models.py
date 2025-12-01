"""Data models for REST API Client.

Philosophy:
- Immutable dataclasses (frozen=True) for thread safety
- Type hints throughout
- Default values for optional fields
- Helper methods for common operations (ok, json(), text)

Models:
    Request: Immutable HTTP request representation
    Response: Immutable HTTP response with helper methods
    ClientConfig: Client configuration with validation
    RetryPolicy: Retry logic configuration with backoff calculation
    RateLimiter: Rate limiting with wait time calculation
    BearerAuth: Bearer token authentication
    APIKeyAuth: API key authentication (header or query)
"""

import json as json_lib
import random
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class Request:
    """Immutable HTTP request model.

    Attributes:
        method: HTTP method (GET, POST, etc.)
        url: Full URL for the request
        headers: Request headers
        params: Query parameters
        body: Request body (dict, str, or bytes)
        timeout: Request timeout in seconds
    """

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    body: Any | None = None
    timeout: int = 30


@dataclass(frozen=True)
class Response:
    """Immutable HTTP response model.

    Attributes:
        status_code: HTTP status code
        headers: Response headers
        body: Response body as string
        request: Original request (optional)
        elapsed: Time taken for request in seconds
    """

    status_code: int
    headers: dict[str, str]
    body: str
    request: Request | None = None
    elapsed: float | None = None

    @property
    def ok(self) -> bool:
        """Check if response status indicates success (2xx).

        Returns:
            True if 200 <= status_code < 300, False otherwise
        """
        return 200 <= self.status_code < 300

    @property
    def text(self) -> str:
        """Get response body as text.

        Returns:
            Response body as string
        """
        return self.body

    def json(self) -> Any:
        """Parse response body as JSON.

        Returns:
            Parsed JSON data (dict, list, etc.)

        Raises:
            json.JSONDecodeError: If body is not valid JSON
        """
        return json_lib.loads(self.body)


@dataclass
class ClientConfig:
    """Client configuration with defaults and validation.

    Attributes:
        base_url: Base URL for all requests
        timeout: Total request timeout in seconds
        connect_timeout: Connection timeout in seconds
        max_retries: Maximum number of retry attempts
        retry_backoff_factor: Exponential backoff multiplier
        retry_statuses: HTTP status codes to retry
        rate_limit_per_second: Max requests per second (None = no limit)
        rate_limit_per_minute: Max requests per minute (None = no limit)
        default_headers: Headers added to every request
        verify_ssl: Verify SSL certificates
        allow_redirects: Follow HTTP redirects
        max_redirects: Maximum number of redirect hops
        debug: Enable debug logging for requests and responses
    """

    base_url: str
    timeout: int = 30
    connect_timeout: int = 10
    max_retries: int = 3
    retry_backoff_factor: float = 0.5
    retry_statuses: list[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    rate_limit_per_second: int | None = None
    rate_limit_per_minute: int | None = None
    default_headers: dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True
    allow_redirects: bool = True
    max_redirects: int = 5
    debug: bool = False

    def __post_init__(self) -> None:
        """Validate configuration values.

        Raises:
            ValueError: If any configuration value is invalid
        """
        if self.timeout < 0:
            raise ValueError(f"timeout must be non-negative, got {self.timeout}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative, got {self.max_retries}")
        if self.connect_timeout < 0:
            raise ValueError(f"connect_timeout must be non-negative, got {self.connect_timeout}")
        if self.max_redirects < 0:
            raise ValueError(f"max_redirects must be non-negative, got {self.max_redirects}")


@dataclass
class RetryPolicy:
    """Retry policy with exponential backoff.

    Attributes:
        max_attempts: Maximum number of attempts (including initial request)
        backoff_factor: Exponential backoff multiplier
        backoff_max: Maximum backoff time in seconds
        jitter: Add random jitter to backoff time
        retry_on_statuses: HTTP status codes to retry
        retry_on_exceptions: Exception types to retry
    """

    max_attempts: int = 3
    backoff_factor: float = 0.5
    backoff_max: int = 60
    jitter: bool = True
    retry_on_statuses: list[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    retry_on_exceptions: list[type[Exception]] = field(
        default_factory=lambda: [ConnectionError, TimeoutError]
    )

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff time for given attempt.

        Uses exponential backoff: backoff_factor * (2 ** (attempt - 1))
        Respects backoff_max ceiling.
        Adds random jitter if enabled.

        Args:
            attempt: Retry attempt number (1-indexed)

        Returns:
            Backoff time in seconds
        """
        # Exponential backoff: 0.5, 1.0, 2.0, 4.0, 8.0, ...
        backoff = self.backoff_factor * (2 ** (attempt - 1))

        # Apply maximum backoff ceiling
        backoff = min(backoff, self.backoff_max)

        # Add jitter if enabled (random variation between 50% and 150%)
        if self.jitter:
            jitter_factor = 0.5 + random.random()  # Random between 0.5 and 1.5
            backoff = backoff * jitter_factor

        return backoff


@dataclass
class RateLimiter:
    """Rate limiter with per-second and per-minute limits.

    Thread-safe rate limiting implementation with metrics tracking
    and context manager support.

    Attributes:
        requests_per_second: Maximum requests per second (None = no limit)
        requests_per_minute: Maximum requests per minute (None = no limit)
    """

    requests_per_second: int | None = None
    requests_per_minute: int | None = None

    def __post_init__(self) -> None:
        """Initialize rate limiter state."""
        self._lock = Lock()
        self._second_requests: list[float] = []
        self._minute_requests: list[float] = []
        self._last_request_time: float | None = None
        self._total_requests = 0
        self._rate_limit_hits_count = 0

    def record_request(self) -> None:
        """Record that a request was made (for testing/manual tracking)."""
        with self._lock:
            now = time.time()
            self._second_requests.append(now)
            self._minute_requests.append(now)
            self._last_request_time = now
            self._total_requests += 1

    def allows_request(self) -> bool:
        """Check if a request can be made without exceeding rate limits.

        Returns:
            True if request is allowed, False otherwise
        """
        with self._lock:
            now = time.time()

            # Clean up old requests
            if self.requests_per_second is not None:
                self._second_requests = [t for t in self._second_requests if now - t < 1.0]
            if self.requests_per_minute is not None:
                self._minute_requests = [t for t in self._minute_requests if now - t < 60.0]

            # Check per-second limit
            if self.requests_per_second is not None:
                if len(self._second_requests) >= self.requests_per_second:
                    return False

            # Check per-minute limit
            if self.requests_per_minute is not None:
                if len(self._minute_requests) >= self.requests_per_minute:
                    return False

            return True

    def wait_time(self) -> float:
        """Calculate time to wait before next request is allowed.

        Returns:
            Wait time in seconds (0 if request can be made immediately)
        """
        with self._lock:
            now = time.time()
            wait_times = []

            # Calculate wait time for per-second limit
            if self.requests_per_second is not None and self._second_requests:
                # Clean up old requests
                self._second_requests = [t for t in self._second_requests if now - t < 1.0]
                if len(self._second_requests) >= self.requests_per_second:
                    oldest = self._second_requests[0]
                    wait_times.append(1.0 - (now - oldest))

            # Calculate wait time for per-minute limit
            if self.requests_per_minute is not None and self._minute_requests:
                # Clean up old requests
                self._minute_requests = [t for t in self._minute_requests if now - t < 60.0]
                if len(self._minute_requests) >= self.requests_per_minute:
                    oldest = self._minute_requests[0]
                    wait_times.append(60.0 - (now - oldest))

            # Return maximum wait time (most restrictive limit)
            return max(wait_times) if wait_times else 0.0

    @property
    def total_requests(self) -> int:
        """Get total number of requests tracked.

        Returns:
            Total number of requests recorded
        """
        with self._lock:
            return self._total_requests

    @property
    def rate_limit_hits(self) -> int:
        """Get number of times rate limit was hit.

        Returns:
            Count of rate limit violations
        """
        with self._lock:
            return self._rate_limit_hits_count

    def record_rate_limit_hit(self) -> None:
        """Record that rate limit was hit (blocked a request)."""
        with self._lock:
            self._rate_limit_hits_count += 1

    def current_rate(self) -> float:
        """Calculate current request rate (requests per second).

        Returns:
            Current request rate as requests/second
        """
        with self._lock:
            now = time.time()
            # Clean up old requests (last second)
            recent_requests = [t for t in self._second_requests if now - t < 1.0]
            return float(len(recent_requests))

    def __enter__(self) -> "RateLimiter":
        """Enter context manager - wait for rate limit if needed.

        Returns:
            Self for context manager protocol
        """
        wait = self.wait_time()
        if wait > 0:
            time.sleep(wait)
        self.record_request()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        # Nothing to clean up on exit


@dataclass
class BearerAuth:
    """Bearer token authentication.

    Attributes:
        token: Bearer token string
    """

    token: str


@dataclass
class APIKeyAuth:
    """API key authentication (header or query parameter).

    Attributes:
        key: API key string
        location: Where to place the key ("header" or "query")
        name: Header name or query parameter name
    """

    key: str
    location: str = "header"
    name: str = "X-API-Key"


__all__ = [
    "Request",
    "Response",
    "ClientConfig",
    "RetryPolicy",
    "RateLimiter",
    "BearerAuth",
    "APIKeyAuth",
]
