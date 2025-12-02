"""Retry and rate limiting logic.

Philosophy:
- Exponential backoff with configurable jitter
- Rate limit handling via Retry-After header
- Circuit breaker for cascading failure prevention
- Clean separation of concerns

Public API (the "studs"):
    RetryConfig: Configuration for retry behavior
    RetryExecutor: Execute operations with retry logic
    RetryContext: Context tracking for retry operations
    RateLimitHandler: Handle rate limit responses
    CircuitBreaker: Circuit breaker pattern
    calculate_backoff: Calculate backoff delay
    should_retry: Determine if error is retryable
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from .exceptions import (
    APIClientError,
    ClientError,
    ConnectionError,
    RateLimitError,
    ServerError,
    TimeoutError,
)

__all__ = [
    "RetryConfig",
    "RetryExecutor",
    "RetryContext",
    "RateLimitHandler",
    "CircuitBreaker",
    "calculate_backoff",
    "should_retry",
]

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retries)
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delays
    """

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = False

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.initial_delay <= 0:
            raise ValueError("initial_delay must be positive")
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay must be >= initial_delay")


def calculate_backoff(attempt: int, config: RetryConfig) -> float:
    """Calculate exponential backoff delay.

    Formula: initial_delay * (exponential_base ^ (attempt - 1))

    Args:
        attempt: Current attempt number (1-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    # Calculate base delay using exponential backoff
    delay = config.initial_delay * (config.exponential_base ** (attempt - 1))

    # Cap at max_delay
    delay = min(delay, config.max_delay)

    # Add jitter if enabled (up to 25% variance)
    if config.jitter:
        jitter_factor = 1.0 + (random.random() - 0.5) * 0.5  # 0.75 to 1.25
        delay *= jitter_factor

    return delay


def should_retry(error: Exception, attempt: int, max_retries: int) -> bool:
    """Determine if an error should trigger a retry.

    Args:
        error: Exception that occurred
        attempt: Current attempt number (1 = first attempt, 2 = first retry, etc.)
        max_retries: Maximum number of retries allowed (0 = no retries)

    Returns:
        True if retry should be attempted
    """
    # Don't retry if retries disabled
    if max_retries == 0:
        return False

    # Don't retry if max retries exceeded
    # attempt=N means we've already made N calls
    # max_retries=3 means we allow up to 3 retries after initial
    # So we stop when attempt >= max_retries (at which point we've retried enough)
    if attempt >= max_retries:
        return False

    # Retry on connection errors
    if isinstance(error, ConnectionError):
        return True

    # Retry on timeout errors
    if isinstance(error, TimeoutError):
        return True

    # Retry on rate limit errors
    if isinstance(error, RateLimitError):
        return True

    # Retry on server errors (except non-retryable ones like 501)
    if isinstance(error, ServerError):
        return error.is_retryable

    # Don't retry on client errors (4xx)
    if isinstance(error, ClientError):
        return False

    # Don't retry on base API errors
    if isinstance(error, APIClientError):
        return False

    # Default: don't retry unknown errors
    return False


@dataclass
class RetryContext:
    """Context tracking for retry operations."""

    current_attempt: int = 1
    total_elapsed_ms: float = 0.0
    last_error: Exception | None = None


class RateLimitHandler:
    """Handle rate limit responses.

    Attributes:
        default_delay: Default delay when Retry-After not provided
        max_delay: Maximum delay to respect
        rate_limit_count: Number of rate limits encountered
    """

    def __init__(
        self,
        default_delay: float = 60.0,
        max_delay: float = 300.0,
    ) -> None:
        self.default_delay = default_delay
        self.max_delay = max_delay
        self.rate_limit_count = 0

    def get_retry_delay(self, error: RateLimitError) -> float:
        """Get delay before retrying after rate limit.

        Args:
            error: Rate limit error with optional retry_after

        Returns:
            Delay in seconds
        """
        if error.retry_after is not None:
            delay = float(error.retry_after)
        else:
            delay = self.default_delay

        # Cap at max_delay
        return min(delay, self.max_delay)

    def record_rate_limit(self, error: RateLimitError) -> None:
        """Record a rate limit hit for tracking.

        Args:
            error: Rate limit error
        """
        self.rate_limit_count += 1


class RetryExecutor:
    """Execute operations with retry logic.

    Handles exponential backoff and rate limit delays.
    """

    def __init__(
        self,
        config: RetryConfig,
        on_retry: Callable[[int, Exception], None] | None = None,
    ) -> None:
        """Initialize retry executor.

        Args:
            config: Retry configuration
            on_retry: Optional callback for retry events
        """
        self.config = config
        self.on_retry = on_retry
        self.rate_limit_handler = RateLimitHandler()

        # Context tracking
        self.current_attempt = 1
        self._start_time: float | None = None

    def execute(self, operation: Callable[[], T]) -> T:
        """Execute operation with retry logic.

        Args:
            operation: Callable to execute

        Returns:
            Result of operation

        Raises:
            Exception: Last exception if all retries exhausted
        """
        self._start_time = time.time()
        self.current_attempt = 1

        while True:
            try:
                result = operation()
                return result

            except Exception as error:
                # Check if we should retry
                # Pass (current_attempt - 1) as retry count since should_retry
                # expects "number of retries done" not "attempt number"
                retry_count = self.current_attempt - 1
                if not should_retry(error, retry_count, self.config.max_retries):
                    # Set attempts_made on exception
                    if isinstance(error, APIClientError):
                        error.attempts_made = self.current_attempt
                    raise

                # Calculate delay
                if isinstance(error, RateLimitError):
                    delay = self.rate_limit_handler.get_retry_delay(error)
                    self.rate_limit_handler.record_rate_limit(error)
                else:
                    delay = calculate_backoff(self.current_attempt, self.config)

                # Call retry callback if provided
                if self.on_retry:
                    self.on_retry(self.current_attempt, error)

                # Wait before retry
                time.sleep(delay)

                # Increment attempt counter
                self.current_attempt += 1

    @property
    def total_elapsed_ms(self) -> float:
        """Get total elapsed time in milliseconds."""
        if self._start_time is None:
            return 0.0
        return (time.time() - self._start_time) * 1000


class CircuitBreaker:
    """Circuit breaker pattern for failure prevention.

    States:
        - closed: Normal operation, requests allowed
        - open: Failures exceeded threshold, requests blocked
        - half-open: Testing if service recovered

    Attributes:
        failure_threshold: Number of failures to trigger open state
        reset_timeout: Seconds to wait before attempting recovery
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 30.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout

        self._state = "closed"
        self._consecutive_failures = 0
        self._last_failure_time: float | None = None

    @property
    def state(self) -> str:
        """Get current circuit state."""
        if self._state == "open":
            # Check if reset timeout has elapsed
            if self._last_failure_time is not None:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.reset_timeout:
                    return "half-open"
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == "closed"

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self.state == "open"

    @property
    def consecutive_failures(self) -> int:
        """Get current consecutive failure count."""
        return self._consecutive_failures

    def should_allow_request(self) -> bool:
        """Check if request should be allowed.

        Returns:
            True if request should proceed
        """
        state = self.state
        if state == "closed":
            return True
        if state == "half-open":
            return True  # Allow test request
        return False  # Open - block requests

    def record_failure(self, error: Exception) -> None:
        """Record a failure.

        Args:
            error: Exception that occurred
        """
        self._consecutive_failures += 1
        self._last_failure_time = time.time()

        if self._consecutive_failures >= self.failure_threshold:
            self._state = "open"

    def record_success(self) -> None:
        """Record a successful request."""
        self._consecutive_failures = 0
        self._state = "closed"
