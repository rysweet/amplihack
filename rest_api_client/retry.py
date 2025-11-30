"""Retry logic with exponential backoff for the REST API client.

Handles transient failures with configurable retry strategies.
"""

import random
import time
from collections.abc import Callable
from typing import TypeVar

from .config import RetryConfig
from .exceptions import APIClientError, RateLimitError, TimeoutError
from .models import APIResponse

T = TypeVar("T")


class RetryHandler:
    """Handles retry logic with exponential backoff."""

    def __init__(self, config: RetryConfig | None = None) -> None:
        """Initialize the retry handler.

        Args:
            config: Retry configuration (uses defaults if None)
        """
        self.config = config or RetryConfig()

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds with exponential backoff and jitter
        """
        if attempt <= 0:
            return 0.0

        # Exponential backoff: base_delay * (exponential_base ^ attempt)
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))

        # Cap at max_delay
        delay = min(delay, self.config.max_delay)

        # Add jitter (random value between -jitter and +jitter)
        if self.config.jitter > 0:
            jitter = random.uniform(-self.config.jitter, self.config.jitter)
            delay = max(0.0, delay + jitter)  # Ensure delay doesn't go negative

        return delay

    def should_retry(
        self,
        exception: Exception | None = None,
        response: APIResponse | None = None,
        attempt: int = 0,
    ) -> bool:
        """Determine if a request should be retried.

        Args:
            exception: Exception that occurred (if any)
            response: Response received (if any)
            attempt: Current attempt number (0-based)

        Returns:
            True if should retry, False otherwise
        """
        # Don't retry if we've exceeded max retries
        if attempt >= self.config.max_retries:
            return False

        # Check if we have an exception
        if exception is not None:
            # Always retry timeout errors
            if isinstance(exception, TimeoutError):
                return True

            # Always retry rate limit errors
            if isinstance(exception, RateLimitError):
                return True

            # Check if it's an API exception with a retryable status code
            if (
                isinstance(exception, APIClientError)
                and hasattr(exception, "status_code")
                and exception.status_code
            ):
                return exception.status_code in self.config.retry_on_status_codes

            # Don't retry other exceptions
            return False

        # Check if we have a response
        if response is not None:
            return response.status_code in self.config.retry_on_status_codes

        # No exception and no response - shouldn't happen, but don't retry
        return False

    def get_retry_after(
        self, exception: Exception | None = None, response: APIResponse | None = None
    ) -> int | None:
        """Extract retry-after value from exception or response.

        Args:
            exception: Exception that occurred (if any)
            response: Response received (if any)

        Returns:
            Retry-after value in seconds, or None if not found
        """
        # Check exception first
        if isinstance(exception, RateLimitError) and exception.retry_after:
            return exception.retry_after

        # Check response headers
        if response and "Retry-After" in response.headers:
            try:
                return int(response.headers["Retry-After"])
            except (ValueError, TypeError):
                pass

        return None

    def execute_with_retry(
        self, func: Callable[[], T], on_retry: Callable[[int, float, str], None] | None = None
    ) -> T:
        """Execute a function with retry logic.

        Args:
            func: Function to execute
            on_retry: Optional callback for retry events (attempt, delay, reason)

        Returns:
            Result from successful execution

        Raises:
            The last exception if all retries fail
        """
        last_exception: Exception | None = None
        last_response: APIResponse | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return func()

            except Exception as e:
                last_exception = e

                # Extract response if available
                if isinstance(e, APIClientError):
                    # Create a mock response for status code checking
                    if hasattr(e, "status_code") and e.status_code:
                        last_response = APIResponse(
                            status_code=e.status_code, headers={}, body=e.response_body or ""
                        )

                # Check if we should retry
                if not self.should_retry(e, last_response, attempt):
                    raise

                # Calculate delay
                delay = self.calculate_delay(attempt + 1)

                # Check for retry-after header
                retry_after = self.get_retry_after(e, last_response)
                if retry_after is not None:
                    delay = max(delay, float(retry_after))

                # Call the retry callback if provided
                if on_retry:
                    reason = f"{type(e).__name__}: {e!s}"
                    on_retry(attempt + 1, delay, reason)

                # Wait before retrying
                if delay > 0:
                    time.sleep(delay)

        # All retries exhausted
        if last_exception:
            raise last_exception

        # Shouldn't reach here, but just in case
        raise APIClientError("All retries exhausted without a successful response")


class ExponentialBackoff:
    """Simple exponential backoff implementation for direct use."""

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: int = 2,
        jitter: float = 0.1,
    ) -> None:
        """Initialize exponential backoff.

        Args:
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential calculation
            jitter: Random jitter range in seconds
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Get delay for the given attempt.

        Args:
            attempt: Attempt number (1-based)

        Returns:
            Delay in seconds
        """
        if attempt <= 0:
            return 0.0

        # Exponential backoff
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter
        if self.jitter > 0:
            jitter = random.uniform(-self.jitter, self.jitter)
            delay = max(0.0, delay + jitter)

        return delay

    def sleep(self, attempt: int) -> float:
        """Sleep for the calculated delay.

        Args:
            attempt: Attempt number (1-based)

        Returns:
            The actual delay that was used
        """
        delay = self.get_delay(attempt)
        if delay > 0:
            time.sleep(delay)
        return delay
