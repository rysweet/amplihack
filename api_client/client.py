"""HTTP client with retry logic and rate limit handling.

This module provides the main APIClient class for making HTTP requests
with automatic retry, rate limiting, and error handling.

Public API (the "studs"):
    APIClient: Main HTTP client class
"""

import logging
import time
import types
from typing import Any

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout as RequestsTimeout

from .exceptions import (
    APIError,
    ClientError,
    ConnectionError,
    RateLimitError,
    RetryExhaustedError,
    ServerError,
    TimeoutError,
)
from .models import Request, Response
from .retry import RetryStrategy

logger = logging.getLogger("api_client")


class APIClient:
    """HTTP client with retry logic and rate limit handling.

    Provides a simple interface for making HTTP requests with automatic
    retry on transient failures, rate limit handling, and proper error
    classification.

    Supports use as a context manager for connection pooling.

    Attributes:
        base_url: Base URL for all requests
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        retry_backoff_factor: Base delay multiplier for exponential backoff
        retry_on_status: Set of HTTP status codes that trigger retry
        default_headers: Headers included in all requests
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_backoff_factor: float = 0.5,
        retry_on_status: set[int] | None = None,
        default_headers: dict[str, str] | None = None,
    ):
        """Initialize API client.

        Args:
            base_url: Base URL for all requests (trailing slash stripped)
            timeout: Request timeout in seconds (default: 30.0)
            max_retries: Maximum retry attempts (default: 3)
            retry_backoff_factor: Backoff multiplier (default: 0.5)
            retry_on_status: Status codes to retry (default: {429, 500, 502, 503, 504})
            default_headers: Headers for all requests (default: {})
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.retry_on_status = retry_on_status or {429, 500, 502, 503, 504}
        self.default_headers = dict(default_headers) if default_headers else {}

        self._retry_strategy = RetryStrategy(
            max_retries=max_retries,
            backoff_factor=retry_backoff_factor,
            retry_on_status=self.retry_on_status,
        )
        self._session: requests.Session | None = None

    def __enter__(self) -> "APIClient":
        """Enter context manager, creating a session for connection pooling."""
        if self._session is None:
            self._session = requests.Session()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit context manager, closing the session."""
        self.close()

    def close(self) -> None:
        """Close the client session.

        Releases resources associated with the underlying HTTP session.
        Safe to call multiple times.
        """
        if self._session:
            self._session.close()
            self._session = None

    def _get_session(self) -> requests.Session:
        """Get or create the requests session."""
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _build_request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        data: bytes | None = None,
    ) -> Request:
        """Build a Request object from parameters."""
        url = f"{self.base_url}{path}"
        merged_headers = {**self.default_headers, **(headers or {})}
        return Request(
            method=method,
            url=url,
            headers=merged_headers,
            params=params,
            json_data=json_data,
            data=data,
        )

    def _make_response(self, req: Request, resp: requests.Response, elapsed_ms: float) -> Response:
        """Create a Response object from a requests.Response."""
        return Response(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            body=resp.content,
            elapsed_ms=elapsed_ms,
            request=req,
        )

    def _handle_error(self, req: Request, resp: requests.Response) -> None:
        """Handle HTTP error responses by raising appropriate exceptions."""
        status = resp.status_code
        message = f"HTTP {status}: {resp.reason}"
        response_obj = self._make_response(req, resp, 0)

        if status == 429:
            retry_after = None
            if "Retry-After" in resp.headers:
                retry_after = self._retry_strategy.parse_retry_after(resp.headers["Retry-After"])
            raise RateLimitError(
                message, retry_after=retry_after, request=req, response=response_obj
            )
        if 500 <= status < 600:
            raise ServerError(message, status_code=status, request=req, response=response_obj)
        if 400 <= status < 500:
            raise ClientError(message, status_code=status, request=req, response=response_obj)

    def request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        data: bytes | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: URL path (appended to base_url)
            headers: Request-specific headers (merged with defaults)
            params: Query parameters
            json_data: JSON body data
            data: Raw bytes body data
            timeout: Request-specific timeout (overrides default)

        Returns:
            Response object with status, headers, body, and timing info.

        Raises:
            ConnectionError: Network connectivity failure
            TimeoutError: Request timeout exceeded
            RateLimitError: HTTP 429 response
            ServerError: HTTP 5xx response
            ClientError: HTTP 4xx response (except 429)
            RetryExhaustedError: All retry attempts failed
        """
        req = self._build_request(method, path, headers, params, json_data, data)
        session = self._get_session()
        request_timeout = timeout if timeout is not None else self.timeout

        last_error: APIError | None = None
        total_attempts = self._retry_strategy.max_retries + 1

        for attempt in range(total_attempts):
            try:
                start_time = time.time()
                resp = session.request(
                    method=method,
                    url=req.url,
                    params=req.params,
                    json=req.json_data,
                    data=req.data,
                    headers=req.headers,
                    timeout=request_timeout,
                    verify=True,
                )
                elapsed_ms = (time.time() - start_time) * 1000

                if resp.status_code >= 400:
                    self._handle_error(req, resp)

                logger.info("Completed: %s %s -> %d", method, req.url, resp.status_code)
                return self._make_response(req, resp, elapsed_ms)

            except RateLimitError as e:
                last_error = e
                if self._retry_strategy.should_retry(attempt, 429):
                    delay = self._retry_strategy.get_delay(attempt, e.retry_after)
                    logger.warning("Rate limited: %s (retry after %.2fs)", req.url, delay)
                    time.sleep(delay)
                    continue
                # If we exhausted many retries (>1), raise RetryExhaustedError
                # Otherwise, raise the original error for simpler cases
                if self._retry_strategy.max_retries > 1 and attempt > 0:
                    break
                raise

            except ServerError as e:
                last_error = e
                if self._retry_strategy.should_retry(attempt, e.status_code):
                    delay = self._retry_strategy.get_delay(attempt)
                    logger.warning(
                        "Server error %d: %s (retry %d/%d after %.2fs)",
                        e.status_code,
                        req.url,
                        attempt + 1,
                        self._retry_strategy.max_retries,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                # If we exhausted many retries (>1), raise RetryExhaustedError
                # Otherwise, raise the original error for simpler cases
                if self._retry_strategy.max_retries > 1 and attempt > 0:
                    break
                raise

            except ClientError:
                # Client errors are not retried
                raise

            except RequestsTimeout as e:
                last_error = TimeoutError(f"Request timed out: {e}", request=req)
                raise last_error

            except RequestsConnectionError as e:
                last_error = ConnectionError(f"Connection failed: {e}", request=req)
                raise last_error

        # If we get here, all retries were exhausted
        raise RetryExhaustedError(
            f"All {total_attempts} attempts failed",
            attempts=total_attempts,
            last_error=last_error or APIError("Unknown error"),
            request=req,
        )

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Make GET request.

        Args:
            path: URL path
            params: Query parameters
            headers: Request-specific headers
            timeout: Request-specific timeout

        Returns:
            Response object
        """
        return self.request("GET", path, params=params, headers=headers, timeout=timeout)

    def post(
        self,
        path: str,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Make POST request.

        Args:
            path: URL path
            json_data: JSON body data
            headers: Request-specific headers
            data: Raw bytes body data
            timeout: Request-specific timeout

        Returns:
            Response object
        """
        return self.request(
            "POST", path, json_data=json_data, headers=headers, data=data, timeout=timeout
        )

    def put(
        self,
        path: str,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Make PUT request.

        Args:
            path: URL path
            json_data: JSON body data
            headers: Request-specific headers
            data: Raw bytes body data
            timeout: Request-specific timeout

        Returns:
            Response object
        """
        return self.request(
            "PUT", path, json_data=json_data, headers=headers, data=data, timeout=timeout
        )

    def patch(
        self,
        path: str,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Make PATCH request.

        Args:
            path: URL path
            json_data: JSON body data
            headers: Request-specific headers
            data: Raw bytes body data
            timeout: Request-specific timeout

        Returns:
            Response object
        """
        return self.request(
            "PATCH", path, json_data=json_data, headers=headers, data=data, timeout=timeout
        )

    def delete(
        self,
        path: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Response:
        """Make DELETE request.

        Args:
            path: URL path
            headers: Request-specific headers
            timeout: Request-specific timeout

        Returns:
            Response object
        """
        return self.request("DELETE", path, headers=headers, timeout=timeout)


__all__ = ["APIClient"]
