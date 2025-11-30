"""Retry handler with exponential backoff and jitter.

Implements intelligent retry logic with circuit breaker pattern.
"""

import asyncio
import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

from .exceptions import NetworkError, RateLimitError, ServerError, TimeoutError
from .models import RetryConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryHandler:
    """Handles retry logic with exponential backoff."""

    def __init__(self, config: RetryConfig | None = None):
        """Initialize retry handler.

        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
        self.consecutive_failures = 0
        self.circuit_open = False
        self.circuit_open_until = 0.0

    def calculate_delay(self, attempt: int, retry_after: int | None = None) -> float:
        """Calculate delay before next retry.

        Args:
            attempt: Current retry attempt (0-based)
            retry_after: Server-provided retry delay (seconds)

        Returns:
            Delay in seconds before next attempt
        """
        if retry_after is not None:
            # Respect server's Retry-After header
            return float(retry_after)

        # Exponential backoff
        delay = self.config.initial_delay * (self.config.exponential_base**attempt)

        # Apply maximum delay cap
        delay = min(delay, self.config.max_delay)

        # Add jitter to prevent thundering herd
        if self.config.jitter:
            delay *= 0.5 + random.random()  # 50% to 150% of calculated delay

        return delay

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if request should be retried.

        Args:
            exception: The exception that occurred
            attempt: Current retry attempt (0-based)

        Returns:
            True if should retry, False otherwise
        """
        # Check if max retries reached
        if attempt >= self.config.max_retries:
            logger.debug(f"Max retries ({self.config.max_retries}) reached")
            return False

        # Check circuit breaker
        if self.circuit_open and time.time() < self.circuit_open_until:
            logger.debug("Circuit breaker is open, not retrying")
            return False

        # Check if exception is retryable
        retryable_exceptions = (
            NetworkError,
            TimeoutError,
            ServerError,
            RateLimitError,
        )

        if not isinstance(exception, retryable_exceptions):
            logger.debug(f"Exception {type(exception).__name__} is not retryable")
            return False

        # Check status code for HTTP errors
        if hasattr(exception, "status_code"):
            status_code = exception.status_code
            if status_code not in self.config.retry_on_statuses:
                logger.debug(f"Status code {status_code} is not in retry list")
                return False

        return True

    def record_success(self):
        """Record successful request."""
        self.consecutive_failures = 0
        if self.circuit_open:
            logger.info("Circuit breaker closed after successful request")
            self.circuit_open = False
            self.circuit_open_until = 0.0

    def record_failure(self):
        """Record failed request and update circuit breaker."""
        self.consecutive_failures += 1

        # Open circuit breaker after 5 consecutive failures
        if self.consecutive_failures >= 5 and not self.circuit_open:
            self.circuit_open = True
            # Keep circuit open for 30 seconds
            self.circuit_open_until = time.time() + 30
            logger.warning(f"Circuit breaker opened after {self.consecutive_failures} failures")

    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> T:
        """Execute function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function execution

        Raises:
            The last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                # Execute the function
                result = await func(*args, **kwargs)
                self.record_success()
                return result

            except Exception as e:
                last_exception = e
                logger.debug(f"Attempt {attempt + 1}/{self.config.max_retries + 1} failed: {e}")

                # Check if we should retry
                if not self.should_retry(e, attempt):
                    self.record_failure()
                    raise

                # Calculate delay
                retry_after = getattr(e, "retry_after", None)
                delay = self.calculate_delay(attempt, retry_after)

                logger.info(
                    f"Retrying after {delay:.2f}s (attempt {attempt + 1}/{self.config.max_retries})"
                )

                # Wait before retry
                await asyncio.sleep(delay)

        # All retries exhausted
        self.record_failure()
        if last_exception:
            raise last_exception
        raise RuntimeError("All retries failed with unknown error")
