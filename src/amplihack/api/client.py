"""REST API client with retry logic and rate limiting.

This module provides a robust HTTP client built on the requests library
with automatic retry, rate limiting, and proper error handling.

Philosophy:
- Thread-safe using thread-local sessions
- Automatic retry with exponential backoff
- Rate limit handling with Retry-After support
- Comprehensive logging with header sanitization
- Clean exception handling
"""

import json
import logging
import threading
import time
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urljoin

import requests
from requests.exceptions import ConnectTimeout, ReadTimeout

from .exceptions import APIError, AuthenticationError, RateLimitError, TimeoutError
from .models import APIResponse

# Maximum Retry-After sleep time (5 minutes) to prevent DoS
MAX_RETRY_AFTER = 300


class APIClient:
    """REST API client with retry logic and rate limiting.

    Provides HTTP methods (GET, POST, PUT, DELETE) with automatic retry
    on server errors (5xx), rate limit handling (429), and proper
    exception handling.

    Attributes:
        base_url: Base URL for API requests (must start with http:// or https://)
        timeout: Timeout tuple (connect_timeout, read_timeout) in seconds
        headers: Default headers to include in all requests
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Multiplier for exponential backoff delays (default: 1.0)
        max_response_size: Maximum allowed response size in bytes (default: 10MB)
        max_request_size: Maximum allowed request size in bytes (default: 10MB)
    """

    # Sensitive header names that should be redacted in logs
    _SENSITIVE_HEADERS = {
        "authorization",
        "api-key",
        "x-api-key",
        "cookie",
        "set-cookie",
    }

    def __init__(
        self,
        base_url: str,
        timeout: tuple[int, int] = (5, 30),
        headers: dict[str, str] | None = None,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        max_response_size: int = 10 * 1024 * 1024,  # 10MB
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        logger: logging.Logger | None = None,
    ):
        """Initialize APIClient.

        Args:
            base_url: Base URL for API (must start with http:// or https://)
            timeout: Timeout tuple (connect_timeout, read_timeout) in seconds
            headers: Default headers for all requests
            max_retries: Maximum retry attempts (default: 3)
            backoff_factor: Multiplier for backoff delays (default: 1.0)
            max_response_size: Maximum allowed response size in bytes (default: 10MB)
            max_request_size: Maximum allowed request size in bytes (default: 10MB)
            logger: Optional custom logger instance

        Raises:
            ValueError: If base_url doesn't start with http:// or https://
        """
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")

        self.base_url = base_url
        self.timeout = timeout
        self.headers = headers or {}
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_response_size = max_response_size
        self.max_request_size = max_request_size
        self._logger = logger or logging.getLogger(__name__)

        # Thread-local storage for sessions (one session per thread)
        self._local = threading.local()

    def _get_session(self) -> requests.Session:
        """Get thread-local session, creating if needed.

        Returns:
            Thread-local requests.Session instance
        """
        if not hasattr(self._local, "session"):
            self._local.session = requests.Session()
        return self._local.session

    def _sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Sanitize sensitive headers for logging.

        Args:
            headers: Headers dictionary to sanitize

        Returns:
            Sanitized headers with sensitive values redacted
        """
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self._SENSITIVE_HEADERS:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized

    def _validate_header_value(self, value: str) -> None:
        """Validate header value doesn't contain CRLF characters.

        Args:
            value: Header value to validate

        Raises:
            ValueError: If header value contains CRLF characters
        """
        if "\r" in value or "\n" in value:
            raise ValueError(f"Header value contains CRLF characters: {value!r}")

    def _merge_headers(self, request_headers: dict[str, str] | None) -> dict[str, str]:
        """Merge client default headers with request-specific headers.

        Request headers override client headers for the same key.

        Args:
            request_headers: Request-specific headers

        Returns:
            Merged headers dictionary

        Raises:
            ValueError: If any header value contains CRLF characters
        """
        merged = self.headers.copy()
        if request_headers:
            merged.update(request_headers)

        # Validate all header values for CRLF injection
        for key, value in merged.items():
            self._validate_header_value(value)

        return merged

    def _should_retry(self, status_code: int) -> bool:
        """Determine if request should be retried based on status code.

        Retry on:
        - 500 Internal Server Error
        - 502 Bad Gateway
        - 503 Service Unavailable
        - 504 Gateway Timeout
        - 429 Too Many Requests (rate limit)

        Do NOT retry on:
        - 4xx errors (except 429)
        - Successful responses (2xx, 3xx)

        Args:
            status_code: HTTP status code

        Returns:
            True if should retry, False otherwise
        """
        return status_code in {500, 502, 503, 504, 429}

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay for retry attempt.

        Base delays: 1s, 2s, 4s (exponential: 2^0, 2^1, 2^2)
        Multiplied by backoff_factor.

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        base_delay = 2**attempt
        return base_delay * self.backoff_factor

    def _parse_retry_after(self, retry_after: str | None) -> int | None:
        """Parse Retry-After header value.

        Supports both integer seconds and HTTP date format.

        Args:
            retry_after: Retry-After header value

        Returns:
            Seconds to wait, or None if parsing fails
        """
        if not retry_after:
            return None

        # Try parsing as integer (seconds)
        try:
            return int(retry_after)
        except ValueError:
            pass

        # Try parsing as HTTP date
        try:
            retry_datetime = parsedate_to_datetime(retry_after)
            delay = retry_datetime.timestamp() - time.time()
            return max(0, int(delay))
        except (ValueError, TypeError):
            return None

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body
            headers: Request-specific headers

        Returns:
            APIResponse object

        Raises:
            APIError: On non-retryable errors or after max retries
            RateLimitError: On rate limit after max retries
            TimeoutError: On request timeout
            AuthenticationError: On 401/403 errors
        """
        # Validate request size
        if json_data:
            serialized = json.dumps(json_data)
            if len(serialized) > self.max_request_size:
                raise ValueError(
                    f"Request body too large: {len(serialized)} bytes (max {self.max_request_size})"
                )

        # Construct URL - handle leading slash in endpoint
        # urljoin treats paths starting with / as absolute, which replaces base path
        # So we strip leading slash and ensure base_url ends with /
        base = self.base_url if self.base_url.endswith("/") else self.base_url + "/"
        endpoint_clean = endpoint.lstrip("/")
        url = urljoin(base, endpoint_clean)
        merged_headers = self._merge_headers(headers)
        session = self._get_session()

        # Log request
        self._logger.info(f"Request: {method} {url}")
        self._logger.debug(
            f"Request details: params={params} headers={self._sanitize_headers(merged_headers)}"
        )

        attempt = 0

        while attempt <= self.max_retries:
            try:
                # Make request using specific HTTP method
                # (explicit methods required for proper test mocking)
                method_lower = method.lower()
                if method_lower == "get":
                    response = session.get(
                        url, params=params, headers=merged_headers, timeout=self.timeout
                    )
                elif method_lower == "post":
                    response = session.post(
                        url,
                        params=params,
                        json=json_data,
                        headers=merged_headers,
                        timeout=self.timeout,
                    )
                elif method_lower == "put":
                    response = session.put(
                        url,
                        params=params,
                        json=json_data,
                        headers=merged_headers,
                        timeout=self.timeout,
                    )
                elif method_lower == "delete":
                    response = session.delete(
                        url, params=params, headers=merged_headers, timeout=self.timeout
                    )
                else:
                    response = session.request(
                        method,
                        url,
                        params=params,
                        json=json_data,
                        headers=merged_headers,
                        timeout=self.timeout,
                    )

                # Validate response size (if Content-Length header present)
                try:
                    if hasattr(response, "headers") and response.headers:
                        content_length_str = response.headers.get(
                            "content-length"
                        ) or response.headers.get("Content-Length")
                        if content_length_str:
                            size = int(content_length_str)
                            if size > self.max_response_size:
                                raise APIError(
                                    f"Response too large: {size} bytes (max {self.max_response_size})",
                                    status_code=response.status_code,
                                    response=response,
                                )
                except (TypeError, AttributeError, ValueError):
                    # Ignore if headers is not iterable (e.g., Mock object) or conversion fails
                    pass

                # Log response (handle missing elapsed for mocks)
                try:
                    elapsed_sec = (
                        response.elapsed.total_seconds() if hasattr(response, "elapsed") else 0
                    )
                    self._logger.info(f"Response: {response.status_code}")
                    self._logger.debug(f"Response elapsed: {elapsed_sec:.3f}s")
                except (AttributeError, TypeError):
                    self._logger.info(f"Response: {response.status_code}")

                # Handle authentication errors (401, 403) - do NOT retry
                if response.status_code in {401, 403}:
                    raise AuthenticationError(
                        f"Authentication failed: {response.status_code}",
                        response=response,
                    )

                # Handle rate limiting (429)
                if response.status_code == 429:
                    retry_after = self._parse_retry_after(response.headers.get("Retry-After"))

                    # If we have retries left, wait and retry
                    if attempt < self.max_retries:
                        if retry_after:
                            # Cap retry_after to prevent DoS
                            if retry_after > MAX_RETRY_AFTER:
                                self._logger.warning(
                                    f"Retry-After {retry_after}s exceeds max "
                                    f"{MAX_RETRY_AFTER}s, capping"
                                )
                                retry_after = MAX_RETRY_AFTER

                            self._logger.info(f"Rate limited. Waiting {retry_after}s before retry.")
                            time.sleep(retry_after)
                        else:
                            # No Retry-After header, use exponential backoff
                            delay = self._calculate_backoff_delay(attempt)
                            self._logger.info(f"Rate limited. Waiting {delay}s before retry.")
                            time.sleep(delay)
                        attempt += 1
                        continue
                    # Out of retries
                    raise RateLimitError(
                        "Rate limit exceeded",
                        response=response,
                        retry_after=retry_after,
                    )

                # Handle other client errors (4xx) - do NOT retry
                if 400 <= response.status_code < 500:
                    raise APIError(
                        f"Client error: {response.status_code}",
                        response=response,
                    )

                # Handle server errors (5xx) - retry with backoff
                if response.status_code >= 500:
                    if attempt < self.max_retries:
                        delay = self._calculate_backoff_delay(attempt)
                        self._logger.warning(
                            f"Server error {response.status_code}. "
                            f"Retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(delay)
                        attempt += 1
                        continue
                    # Out of retries
                    raise APIError(
                        f"Server error after {self.max_retries} retries: {response.status_code}",
                        response=response,
                    )

                # Success or redirect - return response
                return APIResponse.from_requests_response(response)

            except (ConnectTimeout, ReadTimeout) as e:
                timeout_type = "connect" if isinstance(e, ConnectTimeout) else "read"
                raise TimeoutError(
                    f"Request timed out: {e!s}",
                    timeout_type=timeout_type,
                    timeout_value=self.timeout[0] if timeout_type == "connect" else self.timeout[1],
                )

            except requests.exceptions.RequestException as e:
                # Other requests exceptions
                raise APIError(f"Request failed: {e!s}")

        # This should never be reached (all code paths return or raise)
        raise APIError("Request failed: maximum retries exceeded without response")

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """Make GET request.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            headers: Request-specific headers

        Returns:
            APIResponse object
        """
        return self._make_request("GET", endpoint, params=params, headers=headers)

    def post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """Make POST request.

        Args:
            endpoint: API endpoint path
            json_data: JSON request body
            params: Query parameters
            headers: Request-specific headers

        Returns:
            APIResponse object
        """
        return self._make_request(
            "POST", endpoint, params=params, json_data=json_data, headers=headers
        )

    def put(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """Make PUT request.

        Args:
            endpoint: API endpoint path
            json_data: JSON request body
            params: Query parameters
            headers: Request-specific headers

        Returns:
            APIResponse object
        """
        return self._make_request(
            "PUT", endpoint, params=params, json_data=json_data, headers=headers
        )

    def delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """Make DELETE request.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            headers: Request-specific headers

        Returns:
            APIResponse object
        """
        return self._make_request("DELETE", endpoint, params=params, headers=headers)

    def close(self) -> None:
        """Close the thread-local session if it exists.

        Should be called when done using the client to clean up resources.
        """
        if hasattr(self._local, "session"):
            self._local.session.close()
            del self._local.session

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()
        return False


__all__ = ["APIClient"]
