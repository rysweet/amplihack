"""
Retry handler with exponential backoff logic.

Philosophy:
- Simple exponential backoff algorithm
- Respects retry configuration bounds
- Comprehensive logging
- Standard library only
"""

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from .config import RetryConfig
from .exceptions import RetryExhaustedError

# Set up module logger
logger = logging.getLogger(__name__)

# Generic type for return value
T = TypeVar("T")


class RetryHandler:
    """Handles retry logic with exponential backoff.

    This handler wraps function calls with automatic retry logic,
    using exponential backoff to progressively increase delays
    between retry attempts.

    The backoff calculation:
        delay = min(base_delay * (exponential_base ** attempt), max_delay)

    Example:
        With base_delay=1.0, exponential_base=2.0, max_delay=60.0:
        - Attempt 1: 1s delay
        - Attempt 2: 2s delay
        - Attempt 3: 4s delay
        - Attempt 4: 8s delay
        - etc., capped at max_delay

    Attributes:
        config: RetryConfig instance controlling retry behavior
    """

    def __init__(self, config: RetryConfig | None = None):
        """Initialize retry handler with configuration.

        Args:
            config: Optional RetryConfig. Uses defaults if not provided.
        """
        self.config = config or RetryConfig()
        logger.debug(
            f"RetryHandler initialized: max_retries={self.config.max_retries}, "
            f"base_delay={self.config.base_delay}s, max_delay={self.config.max_delay}s"
        )

    def execute_with_retry(
        self,
        func: Callable[[], T],
        is_retryable: Callable[[Exception], bool],
        operation_name: str = "operation",
    ) -> T:
        """Execute a function with retry logic.

        Args:
            func: Function to execute (takes no arguments)
            is_retryable: Function that returns True if exception should trigger retry
            operation_name: Name of operation for logging

        Returns:
            Return value from successful function execution

        Raises:
            RetryExhaustedError: If all retry attempts are exhausted
            Exception: If a non-retryable exception occurs
        """
        attempt = 0
        last_error: Exception | None = None

        while attempt <= self.config.max_retries:
            try:
                # Attempt the operation
                if attempt > 0:
                    logger.info(
                        f"Retry attempt {attempt}/{self.config.max_retries} for {operation_name}"
                    )
                else:
                    logger.debug(f"Executing {operation_name}")

                result = func()

                # Success!
                if attempt > 0:
                    logger.info(f"{operation_name} succeeded on retry attempt {attempt}")

                return result

            except Exception as e:
                last_error = e

                # Check if this exception is retryable
                if not is_retryable(e):
                    logger.debug(f"{operation_name} failed with non-retryable error: {e!s}")
                    raise

                # Check if we have retries left
                if attempt >= self.config.max_retries:
                    # If max_retries is 0, just raise the original error
                    if self.config.max_retries == 0:
                        logger.debug(f"{operation_name} failed (retries disabled)")
                        raise

                    # Otherwise raise RetryExhaustedError
                    logger.error(f"{operation_name} failed after {attempt} retry attempts")
                    raise RetryExhaustedError(attempts=attempt, last_error=last_error)

                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt)

                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}/"
                    f"{self.config.max_retries + 1}): {e!s}. "
                    f"Retrying in {delay:.1f}s..."
                )

                # Wait before retrying
                time.sleep(delay)
                attempt += 1

        # Loop exit means all retries exhausted with an error
        # This should never happen (we should always hit an exception first)
        # but handle it gracefully for type safety
        if last_error is None:
            raise RetryExhaustedError(
                attempts=self.config.max_retries,
                last_error=Exception("Retry loop exited unexpectedly without error"),
            )
        raise RetryExhaustedError(attempts=self.config.max_retries, last_error=last_error)

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay for given attempt number.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds, capped at max_delay
        """
        # Calculate exponential delay: base * (exponential_base ^ attempt)
        delay = self.config.base_delay * (self.config.exponential_base**attempt)

        # Cap at max_delay
        delay = min(delay, self.config.max_delay)

        logger.debug(f"Calculated retry delay for attempt {attempt}: {delay:.2f}s")

        return delay


__all__ = ["RetryHandler"]
