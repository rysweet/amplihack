"""Retry logic with exponential backoff for REST API Client.

This module provides configurable retry mechanisms for handling
transient failures in API requests.
"""

import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum number of attempts (including initial)
        backoff_factor: Multiplier for exponential backoff
        max_backoff: Maximum wait time between retries in seconds
        retry_on_status: HTTP status codes to retry
        retry_on_exception: Exception types to retry
        jitter: Whether to add random jitter to wait times
    """

    max_attempts: int = 3
    backoff_factor: float = 2.0
    max_backoff: float = 60.0
    retry_on_status: set[int] = field(default_factory=lambda: {408, 429, 500, 502, 503, 504})
    retry_on_exception: set[type] = field(default_factory=lambda: {ConnectionError, TimeoutError})
    jitter: bool = True


class RetryManager:
    """Manages retry logic for API requests.

    Implements exponential backoff with optional jitter for
    handling transient failures.
    """

    def __init__(self, config: RetryConfig | None = None, logger: logging.Logger | None = None):
        """Initialize retry manager.

        Args:
            config: Retry configuration
            logger: Logger for retry events
        """
        self.config = config or RetryConfig()
        self.logger = logger or logging.getLogger(__name__)

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff time for given attempt.

        Args:
            attempt: Attempt number (0-based)

        Returns:
            Wait time in seconds
        """
        if attempt == 0:
            return 0

        # Calculate exponential backoff
        wait_time = self.config.backoff_factor ** (attempt - 1)

        # Add jitter if enabled
        if self.config.jitter:
            # Add 0-25% random jitter
            jitter = random.uniform(0, wait_time * 0.25)
            wait_time += jitter

        # Cap at maximum backoff
        return min(wait_time, self.config.max_backoff)

    def should_retry(
        self, attempt: int, status_code: int | None = None, exception: Exception | None = None
    ) -> bool:
        """Determine if request should be retried.

        Args:
            attempt: Current attempt number (0-based)
            status_code: HTTP status code (if applicable)
            exception: Exception that occurred (if applicable)

        Returns:
            True if request should be retried
        """
        # Check if we've exceeded max attempts
        if attempt >= self.config.max_attempts - 1:
            return False

        # Check status code
        if status_code is not None:
            return status_code in self.config.retry_on_status

        # Check exception type
        if exception is not None:
            for exc_type in self.config.retry_on_exception:
                if isinstance(exception, exc_type):
                    return True

        return False

    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of successful function execution

        Raises:
            MaxRetriesExceeded: If all retry attempts fail
            Exception: Original exception if not retryable
        """
        last_exception = None
        last_response = None

        for attempt in range(self.config.max_attempts):
            try:
                # Log attempt
                if attempt > 0:
                    self.logger.info(f"Retry attempt {attempt + 1}/{self.config.max_attempts}")

                # Execute function
                result = func(*args, **kwargs)

                # Check if result has status_code (Response object)
                if hasattr(result, "status_code"):
                    if self.should_retry(attempt, status_code=result.status_code):
                        last_response = result
                        wait_time = self._get_wait_time(attempt, result)
                        self.logger.warning(
                            f"Received status {result.status_code}, retrying in {wait_time:.1f}s"
                        )
                        time.sleep(wait_time)
                        continue

                # Success!
                return result

            except Exception as e:
                last_exception = e

                # Check if we should retry this exception
                if self.should_retry(attempt, exception=e):
                    wait_time = self.calculate_backoff(attempt + 1)
                    self.logger.warning(
                        f"Request failed with {type(e).__name__}: {e}, retrying in {wait_time:.1f}s"
                    )
                    time.sleep(wait_time)
                    continue
                # Not retryable, raise immediately
                raise

        # All retries exhausted
        from .exceptions import MaxRetriesExceeded

        error_msg = f"Maximum retries ({self.config.max_attempts}) exceeded"

        if last_exception:
            error_msg += f". Last error: {last_exception}"

        raise MaxRetriesExceeded(
            error_msg,
            attempts=self.config.max_attempts,
            last_error=last_exception,
            response=last_response,
        )

    def _get_wait_time(self, attempt: int, response: Any) -> float:
        """Get wait time, respecting Retry-After header if present.

        Args:
            attempt: Current attempt number
            response: Response object

        Returns:
            Wait time in seconds
        """
        # Check for Retry-After header
        if hasattr(response, "headers"):
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    # Retry-After can be seconds or HTTP-date
                    return float(retry_after)
                except ValueError:
                    # Might be HTTP-date, ignore for now
                    pass

        # Use exponential backoff
        return self.calculate_backoff(attempt + 1)


def retry(max_attempts: int = 3, backoff_factor: float = 2.0, retry_on: list[type] | None = None):
    """Decorator for adding retry logic to functions.

    Args:
        max_attempts: Maximum number of attempts
        backoff_factor: Multiplier for exponential backoff
        retry_on: List of exception types to retry

    Returns:
        Decorated function with retry logic

    Example:
        @retry(max_attempts=3, retry_on=[ConnectionError])
        def make_request():
            # Request logic here
            pass
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                backoff_factor=backoff_factor,
                retry_on_exception=set(retry_on or []),
            )
            manager = RetryManager(config)
            return manager.execute_with_retry(func, *args, **kwargs)

        return wrapper

    return decorator


class ExponentialBackoff:
    """Iterator for exponential backoff values.

    Useful for custom retry implementations.

    Example:
        backoff = ExponentialBackoff(base=2, max_value=60)
        for wait_time in backoff:
            try:
                # Attempt operation
                break
            except Exception:
                time.sleep(wait_time)
    """

    def __init__(
        self,
        base: float = 2.0,
        max_value: float = 60.0,
        max_attempts: int = 10,
        jitter: bool = True,
    ):
        """Initialize exponential backoff iterator.

        Args:
            base: Base for exponential calculation
            max_value: Maximum backoff value
            max_attempts: Maximum number of iterations
            jitter: Whether to add random jitter
        """
        self.base = base
        self.max_value = max_value
        self.max_attempts = max_attempts
        self.jitter = jitter
        self.attempt = 0

    def __iter__(self):
        """Return iterator."""
        return self

    def __next__(self) -> float:
        """Get next backoff value.

        Returns:
            Next backoff time in seconds

        Raises:
            StopIteration: When max_attempts reached
        """
        if self.attempt >= self.max_attempts:
            raise StopIteration

        if self.attempt == 0:
            wait_time = 0
        else:
            wait_time = self.base ** (self.attempt - 1)

            if self.jitter:
                jitter = random.uniform(0, wait_time * 0.25)
                wait_time += jitter

            wait_time = min(wait_time, self.max_value)

        self.attempt += 1
        return wait_time

    def reset(self):
        """Reset iterator to beginning."""
        self.attempt = 0


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures.

    Monitors failure rate and temporarily blocks requests when
    threshold is exceeded.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening
            recovery_timeout: Time before attempting recovery
            expected_exception: Exception type to monitor
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Original exception if circuit is closed
        """
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                from .exceptions import APIClientError

                raise APIClientError("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset circuit."""
        return (
            self.last_failure_time and time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def reset(self):
        """Manually reset circuit breaker."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"

    def get_state(self) -> dict:
        """Get current circuit breaker state.

        Returns:
            Dictionary with state information
        """
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "threshold": self.failure_threshold,
        }


# Aliases for test compatibility
RetryHandler = RetryManager
RetryPolicy = RetryConfig
RetryableError = ConnectionError  # Map to a retryable error
