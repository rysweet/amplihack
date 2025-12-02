"""Main API Client facade.

Philosophy:
- Simple interface for HTTP requests
- Integrated retry and error handling
- Context manager support for session management
- Comprehensive logging at appropriate levels

Public API (the "studs"):
    APIClient: Main HTTP client class
"""

from __future__ import annotations

import logging
import time
import types
from typing import Any, Self

import requests
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
)
from requests.exceptions import (
    Timeout as RequestsTimeout,
)

from .exceptions import (
    ConnectionError,
    TimeoutError,
    create_exception_from_response,
)
from .models import Request, Response
from .resilience import RetryConfig, RetryExecutor

__all__ = ["APIClient"]

logger = logging.getLogger(__name__)

# Headers that should not be logged for security
SENSITIVE_HEADERS = {
    "authorization",
    "x-api-key",
    "api-key",
    "x-token",
    "x-auth-token",
    "api-token",
    "bearer",
    "cookie",
}


class APIClient:
    """HTTP API client with retry and error handling.

    Features:
        - Automatic retry with exponential backoff
        - Rate limit handling with Retry-After
        - Context manager support
        - Comprehensive logging
        - SSL/TLS certificate verification enabled by default

    Security:
        SSL/TLS certificate verification is enabled by default for all HTTPS
        requests, protecting against man-in-the-middle attacks. API keys and
        sensitive headers are redacted from logs.

    Example:
        >>> import os
        >>> api_key = os.getenv("API_KEY")
        >>> client = APIClient(base_url="https://api.example.com", api_key=api_key)
        >>> response = client.get("/users/1")
        >>> print(response.body)
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize API client.

        Args:
            base_url: Base URL for all requests
            api_key: Optional API key for authentication
            timeout: Default timeout for requests in seconds
            headers: Optional default headers for all requests
            max_retries: Maximum retry attempts (0 to disable)
            retry_delay: Initial delay between retries in seconds
        """
        if not base_url:
            raise ValueError("base_url is required")

        # Strip trailing slash
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

        # Default headers
        self.default_headers = headers.copy() if headers else {}

        # Retry configuration
        self._retry_config = RetryConfig(
            max_retries=max_retries,
            initial_delay=retry_delay,
        )

        # Session management
        self._session: requests.Session | None = None

    def _get_session(self) -> requests.Session:
        """Get or create HTTP session."""
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _build_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        """Build request headers with defaults and auth."""
        headers = {
            "Accept": "application/json",
            **self.default_headers,
        }

        # Add API key if provided
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Add extra headers
        if extra_headers:
            headers.update(extra_headers)

        return headers

    def _make_request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Make HTTP request and return Response.

        This is the core method that handles the actual HTTP call.
        """
        request_headers = self._build_headers(headers)
        request_timeout = timeout or self.timeout

        # Log request at DEBUG level (sanitized)
        sanitized = {
            k: "[REDACTED]" if k.lower() in SENSITIVE_HEADERS else v
            for k, v in request_headers.items()
        }
        logger.debug(
            "Request: %s %s headers=%s",
            method,
            url,
            sanitized,
        )

        start_time = time.time()

        try:
            session = self._get_session()
            http_response = session.request(
                method=method,
                url=url,
                headers=request_headers,
                json=json,
                params=params,
                timeout=request_timeout,
            )

            elapsed_ms = (time.time() - start_time) * 1000

            # Parse response body
            try:
                body = http_response.json()
            except ValueError:
                body = http_response.text or None

            # Extract request ID from response headers
            request_id = http_response.headers.get("X-Request-ID")

            # Build Response object
            response = Response(
                status_code=http_response.status_code,
                body=body,
                headers=dict(http_response.headers),
                elapsed_ms=elapsed_ms,
                request_id=request_id,
            )

            # Log response at DEBUG level
            logger.debug("Response: %s (%.2fms)", response.status_code, elapsed_ms)

            return response

        except RequestsTimeout as e:
            logger.warning("Request timeout: %s %s", method, url)
            raise TimeoutError(
                f"Request timed out: {method} {url}",
                timeout_seconds=request_timeout,
                url=url,
            ) from e

        except RequestsConnectionError as e:
            logger.warning("Connection error: %s %s", method, url)
            raise ConnectionError(
                f"Connection failed: {method} {url}",
                url=url,
                original_error=e,
            ) from e

    def _on_retry(self, attempt: int, error: Exception) -> None:
        """Callback for retry events."""
        logger.warning(
            "Retry attempt %s after error: %s",
            attempt,
            str(error)[:100],
        )

    def request(self, request: Request) -> Response:
        """Execute a Request object.

        Args:
            request: Request to execute

        Returns:
            Response from server

        Raises:
            APIClientError: On request failure
        """
        return self._request_with_retry(
            method=request.method,
            path=request.url,  # Request.url may be full URL or path
            headers=request.headers,
            json=request.body,
            params=request.params,
            timeout=request.timeout,
        )

    def _handle_response(self, response: Response) -> Response:
        """Handle response, raising exceptions for errors."""
        if response.is_success:
            return response

        # Log error with truncated body for safety
        body_str = str(response.body)
        max_body_length = 200
        truncated_body = (
            f"{body_str[:max_body_length]}..." if len(body_str) > max_body_length else body_str
        )
        logger.error(
            "Request failed: %s - %s",
            response.status_code,
            truncated_body,
        )

        # Raise appropriate exception
        raise create_exception_from_response(response)

    def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Make request with retry logic."""
        # Build full URL
        url = path if path.startswith("http") else f"{self.base_url}{path}"

        def operation() -> Response:
            response = self._make_request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                params=params,
                timeout=timeout,
            )
            return self._handle_response(response)

        executor = RetryExecutor(
            config=self._retry_config,
            on_retry=self._on_retry,
        )
        return executor.execute(operation)

    def get(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Make GET request.

        Args:
            path: URL path (appended to base_url)
            headers: Optional additional headers
            params: Optional query parameters
            timeout: Optional timeout override

        Returns:
            Response from server
        """
        return self._request_with_retry(
            method="GET",
            path=path,
            headers=headers,
            params=params,
            timeout=timeout,
        )

    def post(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Make POST request.

        Args:
            path: URL path
            headers: Optional additional headers
            json: Optional JSON body
            params: Optional query parameters
            timeout: Optional timeout override

        Returns:
            Response from server
        """
        return self._request_with_retry(
            method="POST",
            path=path,
            headers=headers,
            json=json,
            params=params,
            timeout=timeout,
        )

    def put(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Make PUT request.

        Args:
            path: URL path
            headers: Optional additional headers
            json: Optional JSON body
            params: Optional query parameters
            timeout: Optional timeout override

        Returns:
            Response from server
        """
        return self._request_with_retry(
            method="PUT",
            path=path,
            headers=headers,
            json=json,
            params=params,
            timeout=timeout,
        )

    def delete(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Make DELETE request.

        Args:
            path: URL path
            headers: Optional additional headers
            params: Optional query parameters
            timeout: Optional timeout override

        Returns:
            Response from server
        """
        return self._request_with_retry(
            method="DELETE",
            path=path,
            headers=headers,
            params=params,
            timeout=timeout,
        )

    def patch(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Make PATCH request.

        Args:
            path: URL path
            headers: Optional additional headers
            json: Optional JSON body
            params: Optional query parameters
            timeout: Optional timeout override

        Returns:
            Response from server
        """
        return self._request_with_retry(
            method="PATCH",
            path=path,
            headers=headers,
            json=json,
            params=params,
            timeout=timeout,
        )

    def close(self) -> None:
        """Close HTTP session."""
        if self._session is not None:
            self._session.close()
            self._session = None

    def __enter__(self) -> Self:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit context manager and close session."""
        self.close()
