"""Retry logic with configurable backoff strategies.

This module provides retry mechanisms with different backoff strategies
for handling transient failures in API requests.
"""

import asyncio
import logging
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ExponentialBackoff:
    """Exponential backoff retry strategy.

    Delays increase exponentially with each attempt, optionally with jitter.
    """

    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = False,
    ):
        """Initialize exponential backoff strategy.

        Args:
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Multiplier for each attempt
            jitter: Whether to add random jitter to delays
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: The retry attempt number (0-indexed)

        Returns:
            Delay in seconds, capped at max_delay
        """
        delay = self.initial_delay * (self.multiplier**attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add random jitter between 0 and full delay
            delay = random.uniform(0, delay)

        return delay

    def should_retry(self, status_code: int) -> bool:
        """Determine if status code is retryable.

        Retries on:
        - 5xx server errors
        - 429 Too Many Requests

        Args:
            status_code: HTTP status code

        Returns:
            True if retryable
        """
        return status_code >= 500 or status_code == 429


class LinearBackoff:
    """Linear backoff retry strategy.

    Delays increase linearly or remain constant.
    """

    def __init__(self, delay: float = 5.0, increment: float = 0.0, max_delay: float = 60.0):
        """Initialize linear backoff strategy.

        Args:
            delay: Base delay in seconds
            increment: Increment per attempt (0 for constant delay)
            max_delay: Maximum delay in seconds
        """
        self.delay = delay
        self.increment = increment
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        """Calculate linear backoff delay.

        Args:
            attempt: The retry attempt number (0-indexed)

        Returns:
            Delay in seconds, capped at max_delay
        """
        delay = self.delay + (self.increment * attempt)
        return min(delay, self.max_delay)

    def should_retry(self, status_code: int) -> bool:
        """Determine if status code is retryable.

        Uses same logic as ExponentialBackoff.

        Args:
            status_code: HTTP status code

        Returns:
            True if retryable
        """
        return status_code >= 500 or status_code == 429


class RetryManager:
    """Manages retry logic for function execution."""

    def __init__(
        self,
        max_retries: int = 3,
        strategy: Any | None = None,
        retry_predicate: Callable[[Exception], bool] | None = None,
    ):
        """Initialize retry manager.

        Args:
            max_retries: Maximum number of retry attempts
            strategy: Retry strategy to use (defaults to exponential backoff)
            retry_predicate: Custom function to determine if exception is retryable
        """
        self.max_retries = max_retries
        self.strategy = strategy or ExponentialBackoff()
        self.retry_predicate = retry_predicate

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function execution

        Raises:
            The last exception if all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if we should retry
                if attempt >= self.max_retries:
                    logger.error(f"All {self.max_retries} retries exhausted")
                    raise

                if not self._should_retry_exception(e):
                    logger.debug(f"Exception {type(e).__name__} is not retryable")
                    raise

                # Calculate delay and wait
                delay = self.strategy.get_delay(attempt)
                logger.info(
                    f"Retry attempt {attempt + 1}/{self.max_retries} after {delay:.1f}s delay"
                )
                time.sleep(delay)

        # Should never reach here, but for type safety
        if last_exception:
            raise last_exception

    async def execute_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute async function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function execution

        Raises:
            The last exception if all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if we should retry
                if attempt >= self.max_retries:
                    logger.error(f"All {self.max_retries} retries exhausted")
                    raise

                if not self._should_retry_exception(e):
                    logger.debug(f"Exception {type(e).__name__} is not retryable")
                    raise

                # Calculate delay and wait
                delay = self.strategy.get_delay(attempt)
                logger.info(
                    f"Retry attempt {attempt + 1}/{self.max_retries} after {delay:.1f}s delay"
                )
                await asyncio.sleep(delay)

        # Should never reach here, but for type safety
        if last_exception:
            raise last_exception

    def _should_retry_exception(self, exception: Exception) -> bool:
        """Determine if exception is retryable.

        Args:
            exception: Exception that occurred

        Returns:
            True if exception should trigger a retry
        """
        # Use custom predicate if provided
        if self.retry_predicate:
            return self.retry_predicate(exception)

        # Import our custom exceptions
        from .exceptions import ConnectionError, RateLimitError, ServerError, TimeoutError

        # Default retryable exceptions
        retryable_types = (ConnectionError, TimeoutError, RateLimitError, ServerError)
        return isinstance(exception, retryable_types)

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        return False


def should_retry(
    status_code: int | None = None,
    exception: Exception | None = None,
    custom_predicate: Callable | None = None,
) -> bool:
    """Helper function to determine if request should be retried.

    Args:
        status_code: HTTP status code
        exception: Exception that occurred
        custom_predicate: Custom logic for retry decision

    Returns:
        True if request should be retried
    """
    # Use custom predicate if provided
    if custom_predicate:
        return custom_predicate(status_code=status_code, exception=exception)

    # Check status code
    if status_code is not None:
        return status_code >= 500 or status_code == 429

    # Check exception type
    if exception is not None:
        from .exceptions import ConnectionError, RateLimitError, TimeoutError

        retryable_types = (ConnectionError, TimeoutError, RateLimitError)
        return isinstance(exception, retryable_types)

    return False


__all__ = ["ExponentialBackoff", "LinearBackoff", "RetryManager", "should_retry"]
