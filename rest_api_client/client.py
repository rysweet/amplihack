"""Consolidated REST API client with retry, rate limiting, and session management.

This module provides a robust HTTP client with automatic retry, rate limiting,
and comprehensive error handling all in a single file for simplicity.
"""

import random
import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

import requests
from requests.exceptions import ConnectionError, Timeout

from .models import (
    APIClientError,
    APIRequest,
    APIResponse,
    HTTPResponseError,
    NetworkError,
    RateLimitConfig,
    RateLimitError,
    RetryConfig,
    TimeoutError,
)
from .utils import APIClientLogger, close_session, create_session, get_logger

T = TypeVar("T")


# =============================================================================
# Token Bucket Rate Limiter (Inlined)
# =============================================================================


class TokenBucket:
    """Token bucket implementation for rate limiting.

    The bucket starts with initial_tokens and refills at refill_rate tokens per second,
    up to max_tokens capacity.
    """

    def __init__(self, config: RateLimitConfig) -> None:
        """Initialize the token bucket.

        Args:
            config: Rate limit configuration
        """
        self.config = config
        self.max_tokens = config.max_tokens
        self.refill_rate = config.refill_rate
        self.tokens = float(config.initial_tokens or config.max_tokens)
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()
        self._retry_after: float | None = None
        self._retry_after_expires: float = 0.0

    def _refill(self) -> None:
        """Refill tokens based on elapsed time since last refill."""
        now = time.monotonic()
        elapsed = now - self.last_refill

        # Add tokens based on refill rate
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.tokens + tokens_to_add, self.max_tokens)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume (default: 1)

        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        with self._lock:
            # Check if we're in a retry-after period
            if self._retry_after_expires > 0:
                if time.monotonic() < self._retry_after_expires:
                    return False
                # Retry-after period expired, clear it
                self._retry_after_expires = 0.0
                self._retry_after = None

            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait_time(self, tokens: int = 1) -> float:
        """Calculate how long to wait for tokens to be available.

        Args:
            tokens: Number of tokens needed (default: 1)

        Returns:
            Wait time in seconds
        """
        with self._lock:
            # Check if we're in a retry-after period
            if self._retry_after_expires > 0:
                remaining = self._retry_after_expires - time.monotonic()
                if remaining > 0:
                    return remaining

            self._refill()

            if self.tokens >= tokens:
                return 0.0

            # Calculate how long until we have enough tokens
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate
            return wait_time

    def set_retry_after(self, seconds: float) -> None:
        """Set a retry-after period during which no tokens are available.

        Args:
            seconds: How many seconds to wait
        """
        with self._lock:
            self._retry_after = seconds
            self._retry_after_expires = time.monotonic() + seconds

    def get_retry_after(self) -> float | None:
        """Get the current retry-after value if any.

        Returns:
            Retry-after seconds or None
        """
        return self._retry_after

    def reset(self) -> None:
        """Reset the bucket to initial state."""
        with self._lock:
            self.tokens = float(self.config.initial_tokens or self.config.max_tokens)
            self.last_refill = time.monotonic()
            self._retry_after = None
            self._retry_after_expires = 0.0

    def get_current_tokens(self) -> float:
        """Get the current number of tokens available.

        Returns:
            Number of tokens currently in the bucket
        """
        with self._lock:
            self._refill()
            return self.tokens


class RateLimiter:
    """Rate limiter using token bucket algorithm."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        """Initialize the rate limiter.

        Args:
            config: Rate limit configuration (uses defaults if None)
        """
        self.config = config or RateLimitConfig()
        self.bucket = TokenBucket(self.config)

    def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Raises:
            RateLimitError: If rate limit cannot be satisfied
        """
        # First try to acquire without waiting
        if self.bucket.consume(tokens):
            return

        # Calculate wait time
        wait_time = self.bucket.wait_time(tokens)

        if wait_time > 60:  # Don't wait more than a minute
            retry_after = self.bucket.get_retry_after()
            raise RateLimitError(
                f"Rate limit exceeded, would need to wait {wait_time:.1f}s",
                retry_after=int(retry_after) if retry_after else None,
            )

        # Wait and try again
        time.sleep(wait_time)
        if not self.bucket.consume(tokens):
            raise RateLimitError("Failed to acquire rate limit token after waiting")

    def handle_retry_after(self, seconds: int) -> None:
        """Handle a Retry-After header from the server.

        Args:
            seconds: Number of seconds to wait
        """
        if self.config.respect_retry_after:
            self.bucket.set_retry_after(float(seconds))

    def reset(self) -> None:
        """Reset the rate limiter to initial state."""
        self.bucket.reset()


# =============================================================================
# Retry Handler (Inlined)
# =============================================================================


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
            True if the request should be retried, False otherwise
        """
        # Check if we've exceeded max retries
        if attempt >= self.config.max_retries:
            return False

        # Check exception types
        if exception:
            # Network errors are retryable
            if isinstance(exception, (TimeoutError, NetworkError)):
                return True

            # Check if the exception has a should_retry method
            if isinstance(exception, APIClientError):
                return exception.should_retry()

            # Connection errors from requests are retryable
            if isinstance(exception, (ConnectionError, Timeout)):
                return True

            # Other exceptions are not retryable
            return False

        # Check response status codes
        if response:
            return response.status_code in self.config.retry_on_status_codes

        return False

    def execute_with_retry(self, func: Callable[[], T], logger: APIClientLogger | None = None) -> T:
        """Execute a function with retry logic.

        Args:
            func: Function to execute
            logger: Optional logger for retry attempts

        Returns:
            Result from the function

        Raises:
            Last exception if all retries are exhausted
        """
        last_exception: Exception | None = None
        last_response: APIResponse | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return func()
            except Exception as e:
                last_exception = e

                # Extract response if available
                if isinstance(e, HTTPResponseError) and hasattr(e, "response"):
                    last_response = e.response  # type: ignore
                elif isinstance(e, RateLimitError):
                    # For rate limit errors, use retry_after if available
                    if e.retry_after:
                        delay = float(e.retry_after)
                    else:
                        delay = self.calculate_delay(attempt + 1)

                    if logger and attempt < self.config.max_retries:
                        logger.log_retry(attempt + 1, delay, "Rate limit exceeded")

                    if attempt < self.config.max_retries:
                        time.sleep(delay)
                        continue

                # Check if we should retry
                if not self.should_retry(exception=e, response=last_response, attempt=attempt):
                    raise

                # Calculate delay and wait if we're retrying
                if attempt < self.config.max_retries:
                    delay = self.calculate_delay(attempt + 1)
                    if logger:
                        logger.log_retry(attempt + 1, delay, str(e))
                    time.sleep(delay)
                else:
                    # Last attempt, re-raise the exception
                    raise

        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Retry logic failed unexpectedly")


# =============================================================================
# Main API Client
# =============================================================================


class APIClient:
    """REST API client with automatic retry, rate limiting, and comprehensive error handling."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limit: int = 10,
        verify_ssl: bool = True,
        enable_logging: bool = True,
        log_level: str = "INFO",
        retry_config: RetryConfig | None = None,
        rate_limit_config: RateLimitConfig | None = None,
    ) -> None:
        """Initialize the API client.

        Args:
            base_url: Base URL for all API requests
            api_key: Optional API key for authentication
            headers: Additional headers to include in requests
            timeout: Default timeout in seconds
            max_retries: Maximum number of retries for failed requests
            rate_limit: Maximum requests per second
            verify_ssl: Whether to verify SSL certificates
            enable_logging: Whether to enable request logging
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            retry_config: Custom retry configuration
            rate_limit_config: Custom rate limit configuration
        """
        # Validate and normalize base URL
        if not base_url:
            raise ValueError("base_url is required")
        self.base_url = base_url.rstrip("/")

        # Set up configuration
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl

        # Initialize retry configuration
        self.retry_config = retry_config or RetryConfig(max_retries=max_retries)
        self.retry_handler = RetryHandler(self.retry_config)

        # Initialize rate limit configuration
        if rate_limit_config is None:
            rate_limit_config = RateLimitConfig(max_tokens=rate_limit, refill_rate=rate_limit / 1.0)
        self.rate_limit_config = rate_limit_config
        self.rate_limiter = RateLimiter(self.rate_limit_config)

        # Set up headers
        self.headers = {
            "User-Agent": "rest-api-client/1.0.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        if headers:
            self.headers.update(headers)

        # Set up logging
        self.enable_logging = enable_logging
        self.logger: APIClientLogger | None = None
        if enable_logging:
            self.logger = get_logger("rest_api_client", log_level)

        # Create session with connection pooling
        self.session = create_session(
            max_retries=0,  # We handle retries ourselves
            verify_ssl=verify_ssl,
            pool_connections=10,
            pool_maxsize=10,
        )
        self.session.headers.update(self.headers)

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint.

        Args:
            endpoint: API endpoint

        Returns:
            Full URL
        """
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"

    def _log_request(self, request: APIRequest) -> None:
        """Log an outgoing request.

        Args:
            request: Request to log
        """
        if self.logger:
            self.logger.log_request(
                request.method,
                request.url,
                params=request.params,
                has_json=request.json_data is not None,
                has_data=request.data is not None,
                timeout=request.timeout,
            )

    def _log_response(self, response: APIResponse) -> None:
        """Log an incoming response.

        Args:
            response: Response to log
        """
        if self.logger:
            self.logger.log_response(
                response.status_code, response.elapsed_time or 0.0, body_size=len(response.body)
            )

    def _log_error(self, error: Exception, request: APIRequest | None = None) -> None:
        """Log an error.

        Args:
            error: Error that occurred
            request: Request that caused the error
        """
        if self.logger:
            context = {}
            if request:
                context["method"] = request.method
                context["url"] = request.url
            self.logger.log_error(error, **context)

    def _execute_request(self, request: APIRequest) -> APIResponse:
        """Execute a single HTTP request (no retry logic).

        Args:
            request: Request to execute

        Returns:
            API response

        Raises:
            Various API exceptions for different error scenarios
        """
        # Acquire rate limit token
        self.rate_limiter.acquire()

        # Log the request
        self._log_request(request)

        # Prepare request parameters
        kwargs: dict[str, Any] = {
            "method": request.method,
            "url": request.url,
            "timeout": request.timeout or self.timeout,
        }

        if request.headers:
            if self.session:
                kwargs["headers"] = {**self.session.headers, **request.headers}
            else:
                kwargs["headers"] = request.headers

        if request.params:
            kwargs["params"] = request.params

        if request.json_data is not None:
            kwargs["json"] = request.json_data
        elif request.data is not None:
            kwargs["data"] = request.data

        # Make the request
        start_time = time.time()
        try:
            if not self.session:
                raise RuntimeError("Session has been closed")
            response = self.session.request(**kwargs)
            elapsed_time = time.time() - start_time

            # Build API response
            api_response = APIResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.text,
                request=request,
                elapsed_time=elapsed_time,
            )

            # Log the response
            self._log_response(api_response)

            # Handle rate limit headers
            if response.status_code == 429 and "Retry-After" in response.headers:
                try:
                    retry_after = int(response.headers["Retry-After"])
                    self.rate_limiter.handle_retry_after(retry_after)
                except ValueError:
                    pass

            # Raise for non-2xx status codes
            api_response.raise_for_status()

            return api_response

        except Timeout as e:
            elapsed_time = time.time() - start_time
            error = TimeoutError(
                f"Request timed out after {elapsed_time:.2f}s",
                timeout=request.timeout or self.timeout,
            )
            self._log_error(error, request)
            raise error from e

        except ConnectionError as e:
            error = NetworkError(f"Connection failed: {e}")
            self._log_error(error, request)
            raise error from e

        except requests.RequestException as e:
            error = NetworkError(f"Request failed: {e}")
            self._log_error(error, request)
            raise error from e

    def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | bytes | str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        retry: bool = True,
    ) -> APIResponse:
        """Make an HTTP request with retry and rate limiting.

        Args:
            method: HTTP method
            endpoint: API endpoint (can be relative or absolute URL)
            params: Query parameters
            json: JSON body data
            data: Form data or raw body
            headers: Additional headers for this request
            timeout: Timeout for this request
            retry: Whether to enable retry logic

        Returns:
            API response

        Raises:
            Various API exceptions for different error scenarios
        """
        # Build request object
        request = APIRequest(
            method=method,
            url=self._build_url(endpoint),
            headers=headers or {},
            params=params,
            json_data=json,
            data=data,
            timeout=timeout,
        )

        # Execute with or without retry
        if retry:
            return self.retry_handler.execute_with_retry(
                lambda: self._execute_request(request), logger=self.logger
            )
        return self._execute_request(request)

    # Convenience methods for common HTTP verbs

    def get(self, endpoint: str, **kwargs: Any) -> APIResponse:
        """Make a GET request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            API response
        """
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> APIResponse:
        """Make a POST request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            API response
        """
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs: Any) -> APIResponse:
        """Make a PUT request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            API response
        """
        return self.request("PUT", endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs: Any) -> APIResponse:
        """Make a PATCH request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            API response
        """
        return self.request("PATCH", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> APIResponse:
        """Make a DELETE request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            API response
        """
        return self.request("DELETE", endpoint, **kwargs)

    def head(self, endpoint: str, **kwargs: Any) -> APIResponse:
        """Make a HEAD request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            API response
        """
        return self.request("HEAD", endpoint, **kwargs)

    def options(self, endpoint: str, **kwargs: Any) -> APIResponse:
        """Make an OPTIONS request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            API response
        """
        return self.request("OPTIONS", endpoint, **kwargs)

    def close(self) -> None:
        """Close the client and clean up resources."""
        if self.session:
            close_session(self.session)
            self.session = None  # type: ignore

    def __enter__(self) -> "APIClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()

    def __del__(self) -> None:
        """Destructor to ensure cleanup."""
        try:
            self.close()
        except Exception:
            pass
