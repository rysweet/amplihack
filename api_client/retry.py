"""Retry logic with exponential backoff.

Philosophy:
- Exponential backoff for transient failures
- Configurable retry parameters
- Clear logging of retry attempts
- Standard library only

Public API:
    RetryHandler: Manages retry logic with exponential backoff
"""

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from .exceptions import RetryExhaustedError

T = TypeVar("T")

logger = logging.getLogger(__name__)


class RetryHandler:
    """Retry handler with exponential backoff.

    Retries operations with increasing delays between attempts.
    Delay = base_delay * (multiplier ** attempt)

    Example:
        >>> handler = RetryHandler(max_retries=3, base_delay=1.0)
        >>> result = handler.execute(lambda: api_call())
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        multiplier: float = 2.0,
        max_delay: float = 60.0,
    ) -> None:
        """Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            multiplier: Delay multiplier for each retry
            max_delay: Maximum delay in seconds

        Raises:
            ValueError: If parameters are invalid
        """
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if multiplier <= 0:
            raise ValueError("multiplier must be positive")
        if max_delay <= 0:
            raise ValueError("max_delay must be positive")

        self._max_retries = max_retries
        self._base_delay = base_delay
        self._multiplier = multiplier
        self._max_delay = max_delay

    def execute(
        self,
        operation: Callable[[], T],
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> T:
        """Execute operation with retries.

        Args:
            operation: Callable to execute
            retryable_exceptions: Tuple of exception types to retry

        Returns:
            Result from successful operation

        Raises:
            RetryExhaustedError: If all retries fail
        """
        last_error: Exception | None = None
        attempts = 0

        for attempt in range(self._max_retries + 1):
            attempts = attempt + 1

            try:
                result = operation()
                if attempt > 0:
                    logger.info(f"Operation succeeded after {attempts} attempts")
                return result

            except retryable_exceptions as e:
                last_error = e

                if attempt < self._max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"Attempt {attempts} failed: {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {attempts} retry attempts failed. Last error: {e}")

        # All retries exhausted
        raise RetryExhaustedError(
            message=f"Operation failed after {attempts} attempts",
            attempts=attempts,
            last_error=last_error,
        )

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt.

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self._base_delay * (self._multiplier**attempt)
        return min(delay, self._max_delay)


__all__ = ["RetryHandler"]
