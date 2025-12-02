"""Retry logic with exponential backoff and jitter.

Philosophy: Exponential backoff prevents thundering herd, jitter prevents synchronized retries.
"""

import random
import time
from collections.abc import Callable
from typing import Any


class RetryHandler:
    """Handles retry logic with exponential backoff."""

    def __init__(self, max_retries: int = 3, backoff: float = 1.0):
        """Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            backoff: Base backoff time in seconds
        """
        self.max_retries = max_retries
        self.backoff = backoff

    def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        retry_on: tuple[type[Exception], ...] = (Exception,),
        **kwargs: Any,
    ) -> Any:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            retry_on: Tuple of exceptions to retry on
            **kwargs: Keyword arguments for func

        Returns:
            Result of successful function call

        Raises:
            RetryExhaustedError: If all retries exhausted
        """
        from .exceptions import RetryExhaustedError

        last_error = None
        attempts = 0

        for attempt in range(self.max_retries + 1):
            attempts = attempt + 1
            try:
                return func(*args, **kwargs)
            except retry_on as e:
                last_error = e
                if attempt < self.max_retries:
                    # Exponential backoff: 2^attempt * backoff + jitter
                    delay = self.backoff * (2**attempt) + random.uniform(0, 0.1)
                    time.sleep(delay)
                    continue
                break

        # Type safety: last_error is guaranteed to be set if we reach here
        assert last_error is not None, "Retry loop must have caught an exception"
        raise RetryExhaustedError(attempts, last_error)


__all__ = ["RetryHandler"]
