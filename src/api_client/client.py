"""HTTP API client with retry handling and rate limiting.

This module implements the APIClient class that provides:
- HTTP methods (GET, POST, PUT, PATCH, DELETE)
- Automatic retry with exponential backoff
- Rate limiting integration
- Structured logging with credential sanitization
- Context manager support

Philosophy:
- Returns requests.Response directly (no wrapper)
- Thread safety optional via thread_safe parameter
- SSL verification always enabled (security first)
- Credentials never logged in plaintext
"""

import logging
import threading
import time
from types import TracebackType
from typing import Any

import requests

from .rate_limiter import RateLimiter
from .retry import RetryPolicy
from .types import APIClientError, HTTPError, NetworkError

# Logger for the module
logger = logging.getLogger("api_client")

# Headers that should be redacted in logs
SENSITIVE_HEADERS = {
    "authorization",
    "x-api-key",
    "api-key",
    "x-auth-token",
    "cookie",
    "x-csrf-token",
    "x-session-id",
}


def _sanitize_headers(headers: dict[str, str] | None) -> dict[str, str]:
    """Sanitize headers for logging by redacting sensitive values.

    Args:
        headers: Dictionary of headers to sanitize

    Returns:
        Copy of headers with sensitive values replaced with [REDACTED]
    """
    if not headers:
        return {}

    sanitized = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value

    return sanitized


class APIClient:
    """HTTP client with retry handling and rate limiting.

    Provides a reliable foundation for making HTTP requests with built-in
    resilience patterns:
    - Automatic retries with exponential backoff and jitter
    - Optional rate limiting with thread-safe token bucket
    - Structured logging with credential sanitization
    - Timeout enforcement on all requests

    Returns requests.Response objects directly for full compatibility
    with the requests library.

    Thread Safety Note:
        APIClient instances are effectively immutable after construction.
        All configuration (base_url, timeout, headers, retry_policy, rate_limiter)
        cannot be modified after __init__. When thread_safe=True, the underlying
        requests.Session is protected by a lock during HTTP operations.

    Attributes:
        base_url: Base URL for all requests
        timeout: Request timeout in seconds
        retry_policy: Retry configuration
        rate_limiter: Rate limiting configuration
        thread_safe: Whether thread-safe operations are enabled
        headers: Default headers for all requests

    Example:
        >>> client = APIClient(base_url="https://api.example.com")
        >>> response = client.get("/users/123")
        >>> print(response.json())

        >>> with APIClient(base_url="https://api.example.com") as client:
        ...     response = client.post("/users", json={"name": "Alice"})
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retry_policy: RetryPolicy | None = None,
        rate_limiter: RateLimiter | None = None,
        thread_safe: bool = False,
        headers: dict[str, str] | None = None,
    ):
        """Initialize APIClient.

        Args:
            base_url: Base URL for all requests (e.g., "https://api.example.com")
            timeout: Request timeout in seconds (default: 30.0)
            retry_policy: Custom retry configuration (default: 3 retries)
            rate_limiter: Custom rate limiter (default: None)
            thread_safe: Enable thread-safe operations (default: False)
            headers: Default headers for all requests
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retry_policy = retry_policy or RetryPolicy()
        self._rate_limiter = rate_limiter
        self._thread_safe = thread_safe
        self._headers = dict(headers) if headers else {}

        # Create session for connection pooling
        self._session = requests.Session()

        # Thread safety lock (used if thread_safe=True)
        self._lock = threading.Lock() if thread_safe else None

    @property
    def base_url(self) -> str:
        """Base URL for all requests."""
        return self._base_url

    @property
    def timeout(self) -> float:
        """Request timeout in seconds."""
        return self._timeout

    @property
    def retry_policy(self) -> RetryPolicy:
        """Retry configuration."""
        return self._retry_policy

    @property
    def rate_limiter(self) -> RateLimiter | None:
        """Rate limiting configuration."""
        return self._rate_limiter

    @property
    def thread_safe(self) -> bool:
        """Whether thread-safe operations are enabled."""
        return self._thread_safe

    @property
    def headers(self) -> dict[str, str]:
        """Default headers for all requests."""
        return dict(self._headers)

    def _build_url(self, path: str) -> str:
        """Build full URL from base URL and path.

        Args:
            path: API path (e.g., "/users/123" or "users/123")

        Returns:
            Full URL combining base_url and path
        """
        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path

        return self._base_url + path

    def _merge_headers(self, request_headers: dict[str, str] | None) -> dict[str, str]:
        """Merge default headers with request-specific headers.

        Request headers override default headers for the same key.

        Args:
            request_headers: Headers for this specific request

        Returns:
            Merged headers dictionary
        """
        merged = dict(self._headers)
        if request_headers:
            merged.update(request_headers)
        return merged

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Make an HTTP request with retry handling.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: API path
            **kwargs: Additional arguments passed to requests

        Returns:
            requests.Response object

        Raises:
            NetworkError: On connection/timeout errors after all retries
            HTTPError: On non-retryable HTTP errors or after all retries
        """
        url = self._build_url(path)

        # Merge headers
        request_headers = kwargs.pop("headers", None)
        merged_headers = self._merge_headers(request_headers)

        # Log the request (with sanitized headers)
        sanitized = _sanitize_headers(merged_headers)
        logger.debug(f"{method} {url} headers={sanitized}")

        # Security: Remove verify from kwargs to prevent SSL bypass
        # SSL verification is always enforced (security first)
        kwargs.pop("verify", None)

        # Apply rate limiting if configured
        if self._rate_limiter:
            wait_time = self._rate_limiter.acquire()
            if wait_time > 0:
                logger.debug(f"Rate limited, waited {wait_time:.3f}s")

        # Retry loop
        last_exception: Exception | None = None
        max_attempts = 1 + self._retry_policy.max_retries

        for attempt in range(max_attempts):
            try:
                # Make the request
                if self._lock:
                    with self._lock:
                        response = self._session.request(
                            method=method,
                            url=url,
                            headers=merged_headers,
                            timeout=self._timeout,
                            **kwargs,
                        )
                else:
                    response = self._session.request(
                        method=method,
                        url=url,
                        headers=merged_headers,
                        timeout=self._timeout,
                        **kwargs,
                    )

                # Log response
                logger.debug(f"Response: {response.status_code}")

                # Check for HTTP errors
                if response.status_code >= 400:
                    # Check if retryable
                    if self._retry_policy.is_retryable(response.status_code):
                        if attempt < max_attempts - 1:
                            # Calculate delay
                            delay = self._get_retry_delay(response, attempt)
                            logger.warning(
                                f"Request failed (attempt {attempt + 1}/{max_attempts}): "
                                f"HTTP {response.status_code}. Retrying after {delay:.2f}s"
                            )
                            time.sleep(delay)
                            continue

                    # Not retryable or retries exhausted
                    raise HTTPError(
                        f"HTTP {response.status_code}",
                        response=response,
                    )

                return response

            except requests.ConnectionError as e:
                last_exception = NetworkError(f"Connection error: {e}")
                if attempt < max_attempts - 1:
                    delay = self._retry_policy.calculate_backoff(attempt)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{max_attempts}): "
                        f"Connection error. Retrying after {delay:.2f}s"
                    )
                    time.sleep(delay)
                    continue
                raise last_exception

            except requests.Timeout as e:
                last_exception = NetworkError(f"Request timeout: {e}")
                if attempt < max_attempts - 1:
                    delay = self._retry_policy.calculate_backoff(attempt)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{max_attempts}): "
                        f"Timeout. Retrying after {delay:.2f}s"
                    )
                    time.sleep(delay)
                    continue
                raise last_exception

            except requests.RequestException as e:
                last_exception = NetworkError(f"Request failed: {e}")
                if attempt < max_attempts - 1:
                    delay = self._retry_policy.calculate_backoff(attempt)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{max_attempts}): "
                        f"{e}. Retrying after {delay:.2f}s"
                    )
                    time.sleep(delay)
                    continue
                raise last_exception

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise APIClientError("Request failed after all retries")

    def _get_retry_delay(self, response: requests.Response, attempt: int) -> float:
        """Get delay before next retry.

        Checks for Retry-After header first, falls back to exponential backoff.

        Args:
            response: The HTTP response
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        # Check for Retry-After header
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            parsed_delay = self._retry_policy.parse_retry_after(retry_after)
            if parsed_delay is not None:
                return parsed_delay

        # Fall back to exponential backoff
        return self._retry_policy.calculate_backoff(attempt)

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        """Make a GET request.

        Args:
            path: API path
            **kwargs: Additional arguments (params, headers, etc.)

        Returns:
            requests.Response object

        Example:
            >>> response = client.get("/users", params={"page": 1})
            >>> users = response.json()
        """
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        """Make a POST request.

        Args:
            path: API path
            **kwargs: Additional arguments (json, data, headers, etc.)

        Returns:
            requests.Response object

        Example:
            >>> response = client.post("/users", json={"name": "Alice"})
            >>> new_user = response.json()
        """
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        """Make a PUT request.

        Args:
            path: API path
            **kwargs: Additional arguments (json, data, headers, etc.)

        Returns:
            requests.Response object

        Example:
            >>> response = client.put("/users/123", json={"name": "Bob"})
        """
        return self._request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> requests.Response:
        """Make a PATCH request.

        Args:
            path: API path
            **kwargs: Additional arguments (json, data, headers, etc.)

        Returns:
            requests.Response object

        Example:
            >>> response = client.patch("/users/123", json={"email": "new@example.com"})
        """
        return self._request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        """Make a DELETE request.

        Args:
            path: API path
            **kwargs: Additional arguments (headers, etc.)

        Returns:
            requests.Response object

        Example:
            >>> response = client.delete("/users/123")
            >>> assert response.status_code == 204
        """
        return self._request("DELETE", path, **kwargs)

    def __enter__(self) -> "APIClient":
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, close session."""
        self._session.close()

    def close(self) -> None:
        """Close the underlying session."""
        self._session.close()


__all__ = ["APIClient"]
