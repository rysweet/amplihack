"""Retry logic with exponential backoff for REST API client.

Philosophy:
- Simple exponential backoff with configurable jitter
- Clear retry conditions (network errors, 5xx, 429)
- No magic - explicit control over retry behavior

Public API:
    RetryHandler: Main retry orchestrator

Formula:
    delay = min(backoff_base * 1.5^attempt + jitter, backoff_max)
    jitter = random(0, backoff_jitter * delay)
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

from .exceptions import (
    RateLimitError,
    RequestError,
    RetryExhaustedError,
    ServerError,
)

T = TypeVar("T")


class RetryHandler:
    """Handles retry logic with exponential backoff.

    Implements exponential backoff with jitter for transient failures.
    Respects Retry-After headers when available.

    Attributes:
        max_retries: Maximum number of retry attempts.
        backoff_base: Base delay in seconds.
        backoff_max: Maximum delay in seconds.
        backoff_jitter: Jitter factor (0.0-1.0).

    Example:
        >>> handler = RetryHandler(
        ...     max_retries=3,
        ...     backoff_base=0.5,
        ...     backoff_max=60.0,
        ...     backoff_jitter=0.25,
        ... )
        >>> result = handler.execute(
        ...     operation=lambda: api.get("/users"),
        ...     operation_name="get_users",
        ... )
    """

    # Multiplier for exponential growth (1.5^attempt)
    BACKOFF_MULTIPLIER: float = 1.5

    def __init__(
        self,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        backoff_max: float = 60.0,
        backoff_jitter: float = 0.25,
    ) -> None:
        """Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts.
            backoff_base: Base delay for exponential backoff in seconds.
            backoff_max: Maximum delay between retries in seconds.
            backoff_jitter: Jitter factor (0.0-1.0) to randomize delays.
        """
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.backoff_jitter = backoff_jitter

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if an operation should be retried.

        Retryable conditions:
        - RequestError (network failures)
        - ServerError (5xx responses)
        - RateLimitError (429 responses)

        Args:
            exception: The exception that occurred.
            attempt: Current attempt number (0-indexed).

        Returns:
            True if the operation should be retried.
        """
        if attempt >= self.max_retries:
            return False

        # Retry on network errors
        if isinstance(exception, RequestError):
            return True

        # Retry on server errors (5xx)
        if isinstance(exception, ServerError):
            return True

        # Retry on rate limits (429)
        if isinstance(exception, RateLimitError):
            return True

        # Don't retry other errors (4xx client errors, etc.)
        return False

    def get_delay(self, attempt: int, retry_after: float | None = None) -> float:
        """Calculate delay before next retry attempt.

        Formula: min(backoff_base * 1.5^attempt + jitter, backoff_max)
        Jitter: random 0-25% of base delay (configurable).

        If retry_after is provided (from Retry-After header), it takes
        precedence over the calculated delay.

        Args:
            attempt: Current attempt number (0-indexed).
            retry_after: Optional delay from Retry-After header.

        Returns:
            Delay in seconds before next retry.

        Example:
            >>> handler = RetryHandler(backoff_base=0.5, backoff_jitter=0.25)
            >>> handler.get_delay(0)  # ~0.5 + jitter
            0.55
            >>> handler.get_delay(1)  # ~0.75 + jitter
            0.85
            >>> handler.get_delay(2)  # ~1.125 + jitter
            1.20
        """
        # Use Retry-After if provided
        if retry_after is not None:
            return max(0.0, retry_after)

        # Calculate exponential delay: base * 1.5^attempt
        base_delay = self.backoff_base * (self.BACKOFF_MULTIPLIER**attempt)

        # Add jitter: random 0 to jitter_factor * base_delay
        jitter = random.uniform(0, self.backoff_jitter * base_delay)
        delay_with_jitter = base_delay + jitter

        # Cap at maximum delay
        return min(delay_with_jitter, self.backoff_max)

    def execute(
        self,
        operation: Callable[[], T],
        operation_name: str = "operation",
    ) -> T:
        """Execute an operation with retry logic.

        Retries the operation according to configured policy when
        retryable exceptions occur.

        Args:
            operation: Callable that performs the operation.
            operation_name: Name for logging/debugging.

        Returns:
            Result of the successful operation.

        Raises:
            RetryExhaustedError: If all retry attempts fail.
            APIClientError: If a non-retryable error occurs.

        Example:
            >>> handler = RetryHandler(max_retries=3)
            >>> result = handler.execute(
            ...     operation=lambda: risky_api_call(),
            ...     operation_name="risky_api_call",
            ... )
        """
        last_exception: Exception | None = None

        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            try:
                return operation()
            except Exception as e:
                last_exception = e

                # Check if we should retry
                if not self.should_retry(e, attempt):
                    # Re-raise non-retryable exceptions
                    raise

                # Get retry-after from rate limit errors
                retry_after: float | None = None
                if isinstance(e, RateLimitError):
                    retry_after = e.retry_after

                # Calculate and apply delay
                delay = self.get_delay(attempt, retry_after)
                time.sleep(delay)

        # All retries exhausted
        raise RetryExhaustedError(
            message=f"{operation_name} failed after {self.max_retries + 1} attempts",
            attempts=self.max_retries + 1,
            last_exception=last_exception,
        )


__all__ = ["RetryHandler"]
