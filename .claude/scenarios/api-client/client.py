"""APIClient implementation - Simple HTTP client with retry and rate limiting.

This module provides a robust HTTP client that handles:
- Automatic retry with exponential backoff for transient failures
- Rate limiting to avoid 429 errors
- Proper error classification for actionable error handling
- Secure logging with sanitized headers
"""

from __future__ import annotations

import logging
import time
import types
from dataclasses import dataclass
from typing import Any, Self

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout as RequestsTimeout

logger = logging.getLogger(__name__)

# Status codes that trigger retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Headers that should be masked in logs
SENSITIVE_HEADERS = {"authorization", "x-api-key", "api-key", "x-auth-token"}


@dataclass
class APIClientError(Exception):
    """Single exception class for all API client errors.

    Attributes:
        message: Human-readable error description
        error_type: Category of error - "connection", "timeout", "rate_limit", "http", "validation"
        status_code: HTTP status code if applicable
        response_body: Raw response body if available
        retry_after: Seconds to wait before retry (from Retry-After header)
    """

    message: str
    error_type: str
    status_code: int | None = None
    response_body: str | None = None
    retry_after: float | None = None

    def __str__(self) -> str:
        return f"[{self.error_type}] {self.message}"


@dataclass(frozen=True)
class APIResponse:
    """Immutable container for HTTP response data.

    Attributes:
        status_code: HTTP status code
        body: Parsed JSON (dict/list) or raw text
        headers: Response headers as dict
        elapsed_ms: Request duration in milliseconds
    """

    status_code: int
    body: dict[str, Any] | list[Any] | str | None
    headers: dict[str, str]
    elapsed_ms: float


class APIClient:
    """HTTP client with automatic retry, rate limiting, and secure logging.

    Example:
        >>> with APIClient(base_url="https://api.example.com") as client:
        ...     response = client.get("/users/1")
        ...     print(response.body)
    """

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        rate_limit_per_second: float = 10.0,
    ) -> None:
        """Initialize the API client.

        Args:
            base_url: Base URL for all requests (e.g., "https://api.example.com")
            timeout_seconds: Request timeout in seconds
            max_retries: Maximum retry attempts for transient failures
            rate_limit_per_second: Maximum requests per second

        Raises:
            APIClientError: With error_type="validation" for invalid parameters
        """
        # Validate parameters
        if not base_url or not base_url.strip():
            raise APIClientError(
                message="base_url cannot be empty",
                error_type="validation",
            )
        if timeout_seconds <= 0:
            raise APIClientError(
                message="timeout_seconds must be positive",
                error_type="validation",
            )
        if max_retries < 0:
            raise APIClientError(
                message="max_retries cannot be negative",
                error_type="validation",
            )
        if rate_limit_per_second <= 0:
            raise APIClientError(
                message="rate_limit_per_second must be positive",
                error_type="validation",
            )

        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.rate_limit_per_second = rate_limit_per_second
        self._session: requests.Session | None = None
        self._last_request_time: float = 0.0
        self._min_request_interval = 1.0 / rate_limit_per_second

    def __enter__(self) -> Self:
        """Enter context manager - create session."""
        self._session = requests.Session()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit context manager - close session."""
        if self._session:
            self._session.close()
            self._session = None

    def get(self, path: str, params: dict[str, Any] | None = None) -> APIResponse:
        """Send GET request.

        Args:
            path: URL path (appended to base_url)
            params: Query parameters

        Returns:
            APIResponse with status_code, body, headers, elapsed_ms

        Raises:
            APIClientError: On request failure
        """
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict[str, Any] | list[Any] | None = None) -> APIResponse:
        """Send POST request with JSON body.

        Args:
            path: URL path (appended to base_url)
            json: Request body (will be JSON-encoded)

        Returns:
            APIResponse with status_code, body, headers, elapsed_ms

        Raises:
            APIClientError: On request failure
        """
        return self._request("POST", path, json=json)

    def put(self, path: str, json: dict[str, Any] | list[Any] | None = None) -> APIResponse:
        """Send PUT request with JSON body.

        Args:
            path: URL path (appended to base_url)
            json: Request body (will be JSON-encoded)

        Returns:
            APIResponse with status_code, body, headers, elapsed_ms

        Raises:
            APIClientError: On request failure
        """
        return self._request("PUT", path, json=json)

    def delete(self, path: str) -> APIResponse:
        """Send DELETE request.

        Args:
            path: URL path (appended to base_url)

        Returns:
            APIResponse with status_code, body, headers, elapsed_ms

        Raises:
            APIClientError: On request failure
        """
        return self._request("DELETE", path)

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | list[Any] | None = None,
    ) -> APIResponse:
        """Core request method with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: URL path
            params: Query parameters
            json: Request body

        Returns:
            APIResponse on success

        Raises:
            APIClientError: On failure after retries exhausted
        """
        url = f"{self.base_url}{path}"
        session = self._session or requests.Session()
        last_error: APIClientError | None = None

        for attempt in range(self.max_retries + 1):
            try:
                self._apply_rate_limit()

                logger.debug(
                    "Request: %s %s (attempt %d/%d)",
                    method,
                    url,
                    attempt + 1,
                    self.max_retries + 1,
                )

                start_time = time.monotonic()
                response = session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    timeout=self.timeout_seconds,
                )
                elapsed_ms = (time.monotonic() - start_time) * 1000

                logger.debug(
                    "Response: %d in %.1fms (headers: %s)",
                    response.status_code,
                    elapsed_ms,
                    self._sanitize_headers(dict(response.headers)),
                )

                # Success - return response
                if response.ok:
                    return self._build_response(response, elapsed_ms)

                # Check if should retry
                if self._should_retry(response.status_code, attempt):
                    delay = self._get_backoff_delay(response, attempt)
                    logger.warning(
                        "Retrying after %s %d (waiting %.1fs)",
                        method,
                        response.status_code,
                        delay,
                    )
                    time.sleep(delay)
                    last_error = self._build_error(response)
                    continue

                # Non-retryable error
                raise self._build_error(response)

            except RequestsConnectionError as e:
                last_error = APIClientError(
                    message=f"Connection failed: {e}",
                    error_type="connection",
                )
                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt)
                    logger.warning("Connection error, retrying in %.1fs: %s", delay, e)
                    time.sleep(delay)
                    continue
                raise last_error from e

            except RequestsTimeout as e:
                last_error = APIClientError(
                    message=f"Request timed out after {self.timeout_seconds}s",
                    error_type="timeout",
                )
                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt)
                    logger.warning("Timeout, retrying in %.1fs: %s", delay, e)
                    time.sleep(delay)
                    continue
                raise last_error from e

        # All retries exhausted
        if last_error:
            logger.error("Request failed after %d attempts: %s", self.max_retries + 1, last_error)
            raise last_error

        # Should not reach here, but satisfy type checker
        raise APIClientError(
            message="Unexpected error: all retries exhausted",
            error_type="http",
        )

    def _should_retry(self, status_code: int, attempt: int) -> bool:
        """Determine if request should be retried.

        Args:
            status_code: HTTP status code
            attempt: Current attempt number (0-indexed)

        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_retries:
            return False
        return status_code in RETRYABLE_STATUS_CODES

    def _get_backoff_delay(self, response: requests.Response, attempt: int) -> float:
        """Calculate delay before next retry.

        Args:
            response: HTTP response (may contain Retry-After header)
            attempt: Current attempt number

        Returns:
            Delay in seconds
        """
        # Check Retry-After header for 429 responses
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    pass

        return self._calculate_backoff(attempt)

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Pattern: 0.5s, 1s, 2s (capped at 2s)

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = 0.5 * (2**attempt)
        return min(delay, 2.0)

    def _apply_rate_limit(self) -> None:
        """Apply rate limiting by sleeping if necessary."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            sleep_time = self._min_request_interval - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.monotonic()

    def _build_response(self, response: requests.Response, elapsed_ms: float) -> APIResponse:
        """Build APIResponse from requests Response.

        Args:
            response: Raw requests Response
            elapsed_ms: Request duration in milliseconds

        Returns:
            APIResponse with parsed body
        """
        # Parse body - try JSON first, fall back to text
        body: dict[str, Any] | list[Any] | str | None = None
        content_type = response.headers.get("Content-Type", "")

        if response.content:
            if "application/json" in content_type:
                try:
                    body = response.json()
                except ValueError:
                    body = response.text
            else:
                body = response.text if response.text else None

        return APIResponse(
            status_code=response.status_code,
            body=body,
            headers=dict(response.headers),
            elapsed_ms=elapsed_ms,
        )

    def _build_error(self, response: requests.Response) -> APIClientError:
        """Build APIClientError from failed response.

        Args:
            response: HTTP response with error status

        Returns:
            APIClientError with appropriate error_type
        """
        # Determine error type
        if response.status_code == 429:
            error_type = "rate_limit"
            retry_after = response.headers.get("Retry-After")
            retry_after_float = None
            if retry_after:
                try:
                    retry_after_float = float(retry_after)
                except ValueError:
                    pass  # HTTP-Date format not supported, fall back to None
        else:
            error_type = "http"
            retry_after_float = None

        return APIClientError(
            message=f"HTTP {response.status_code}: {response.reason}",
            error_type=error_type,
            status_code=response.status_code,
            response_body=response.text if response.text else None,
            retry_after=retry_after_float,
        )

    def _sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Sanitize sensitive headers for logging.

        Args:
            headers: Original headers dict

        Returns:
            Headers with sensitive values masked
        """
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in SENSITIVE_HEADERS:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized
