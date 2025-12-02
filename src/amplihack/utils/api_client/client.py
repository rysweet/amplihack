"""REST API Client implementation.

Philosophy:
- Simple, synchronous HTTP client built on requests library
- Automatic retry with exponential backoff
- Sensitive header redaction in logs
- Context manager for proper resource cleanup

Public API:
    APIClient: Main client class
"""

from __future__ import annotations

import logging
import time
import types
import uuid
from collections.abc import Mapping
from typing import Any, Self

import requests
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
)
from requests.exceptions import (
    Timeout as RequestsTimeout,
)

from .config import APIClientConfig
from .exceptions import (
    ClientError,
    RequestError,
    ResponseError,
    ServerError,
)
from .models import APIRequest, APIResponse
from .rate_limit import RateLimitHandler
from .retry import RetryHandler

# Headers to redact from logs
SENSITIVE_HEADERS = frozenset(
    {
        "authorization",
        "x-api-key",
        "api-key",
        "x-auth-token",
        "x-access-token",
        "cookie",
        "set-cookie",
        "proxy-authorization",
    }
)


class APIClient:
    """REST API client with retry logic and rate limit handling.

    Uses the requests library for HTTP operations. Supports automatic
    retry on transient failures and rate limit handling.

    Attributes:
        config: Client configuration.

    Example:
        >>> config = APIClientConfig(base_url="https://api.example.com")
        >>> with APIClient(config) as client:
        ...     response = client.get("/users/123")
        ...     print(response.json)
    """

    def __init__(
        self,
        config: APIClientConfig,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize API client.

        Args:
            config: Client configuration.
            logger: Optional logger for request/response logging.
        """
        self.config = config
        self._logger = logger or logging.getLogger(__name__)
        self._session: requests.Session | None = None
        self._retry_handler = RetryHandler(
            max_retries=config.max_retries,
            backoff_base=config.backoff_base,
            backoff_max=config.backoff_max,
            backoff_jitter=config.backoff_jitter,
        )
        self._rate_limit_handler = RateLimitHandler()

    @property
    def _active_session(self) -> requests.Session:
        """Get or create the requests session (lazy initialization)."""
        if self._session is None:
            self._session = requests.Session()
            # Apply default headers
            for key, value in self.config.default_headers.items():
                self._session.headers[key] = value
        return self._session

    def _redact_headers(self, headers: Mapping[str, str]) -> dict[str, str]:
        """Redact sensitive values from headers for logging.

        Args:
            headers: Headers to redact.

        Returns:
            Headers with sensitive values replaced with "[REDACTED]".
        """
        result = {}
        for key, value in headers.items():
            if key.lower() in SENSITIVE_HEADERS:
                result[key] = "[REDACTED]"
            else:
                result[key] = value
        return result

    def _build_url(self, path: str) -> str:
        """Build full URL from base URL and path.

        Args:
            path: Request path (may or may not start with /).

        Returns:
            Full URL.
        """
        base = self.config.base_url.rstrip("/")
        if not path.startswith("/"):
            path = "/" + path
        return base + path

    def request(self, request: APIRequest) -> APIResponse:
        """Execute an HTTP request.

        Args:
            request: Request to execute.

        Returns:
            Response from the server.

        Raises:
            RequestError: For network-level failures.
            ClientError: For 4xx responses (except 429).
            ServerError: For 5xx responses.
            RateLimitError: For 429 responses.
        """
        url = self._build_url(request.path)
        timeout = request.timeout or self.config.timeout
        request_id = str(uuid.uuid4())

        # Build headers
        headers = dict(self.config.default_headers)
        for key, value in request.headers.items():
            headers[key] = value
        headers["X-Request-ID"] = request_id

        # Log request (with redacted headers)
        self._logger.debug(
            "Request: %s %s headers=%s params=%s",
            request.method,
            url,
            self._redact_headers(headers),
            request.params,
        )

        def do_request() -> APIResponse:
            start_time = time.time()

            # SSL verification settings
            verify = self.config.ca_bundle if self.config.ca_bundle else self.config.verify_ssl

            try:
                response = self._active_session.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    params=request.params or None,
                    json=request.json_body,
                    timeout=timeout,
                    verify=verify,
                )
            except RequestsTimeout as e:
                raise RequestError(f"Request timed out after {timeout}s", cause=e)
            except RequestsConnectionError as e:
                raise RequestError(f"Connection failed: {e}", cause=e)
            except Exception as e:
                raise RequestError(f"Request failed: {e}", cause=e)

            elapsed_ms = (time.time() - start_time) * 1000

            # Log response
            self._logger.debug(
                "Response: %s %s status=%d elapsed=%.2fms",
                request.method,
                url,
                response.status_code,
                elapsed_ms,
            )

            # Build response object
            response_headers = dict(response.headers)
            api_response = APIResponse(
                status_code=response.status_code,
                headers=response_headers,
                body=response.text,
                elapsed_ms=elapsed_ms,
                request_id=request_id,
            )

            # Handle errors
            if api_response.is_success:
                return api_response

            # Rate limit (429)
            if response.status_code == 429:
                raise self._rate_limit_handler.handle_429(
                    headers=response_headers,
                    response_body=response.text,
                    request_id=request_id,
                )

            # Server errors (5xx)
            if api_response.is_server_error:
                raise ServerError(
                    message=f"Server error: {response.status_code}",
                    status_code=response.status_code,
                    response_body=response.text,
                    request_id=request_id,
                )

            # Client errors (4xx)
            if api_response.is_client_error:
                raise ClientError(
                    message=f"Client error: {response.status_code}",
                    status_code=response.status_code,
                    response_body=response.text,
                    request_id=request_id,
                )

            # Unexpected status code
            raise ResponseError(
                message=f"Unexpected status code: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
                request_id=request_id,
            )

        # Execute with retry
        return self._retry_handler.execute(
            operation=do_request,
            operation_name=f"{request.method} {url}",
        )

    def get(
        self,
        path: str,
        params: Mapping[str, str | int | float | bool | None] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """Execute a GET request.

        Args:
            path: Request path.
            params: Query parameters.
            headers: Additional headers.
            timeout: Request timeout override.

        Returns:
            Response from the server.
        """
        return self.request(
            APIRequest(
                method="GET",
                path=path,
                params=params or {},
                headers=headers or {},
                timeout=timeout,
            )
        )

    def post(
        self,
        path: str,
        json_body: dict[str, Any] | list[Any] | None = None,
        params: Mapping[str, str | int | float | bool | None] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """Execute a POST request.

        Args:
            path: Request path.
            json_body: JSON request body.
            params: Query parameters.
            headers: Additional headers.
            timeout: Request timeout override.

        Returns:
            Response from the server.
        """
        return self.request(
            APIRequest(
                method="POST",
                path=path,
                json_body=json_body,
                params=params or {},
                headers=headers or {},
                timeout=timeout,
            )
        )

    def put(
        self,
        path: str,
        json_body: dict[str, Any] | list[Any] | None = None,
        params: Mapping[str, str | int | float | bool | None] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """Execute a PUT request.

        Args:
            path: Request path.
            json_body: JSON request body.
            params: Query parameters.
            headers: Additional headers.
            timeout: Request timeout override.

        Returns:
            Response from the server.
        """
        return self.request(
            APIRequest(
                method="PUT",
                path=path,
                json_body=json_body,
                params=params or {},
                headers=headers or {},
                timeout=timeout,
            )
        )

    def delete(
        self,
        path: str,
        params: Mapping[str, str | int | float | bool | None] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """Execute a DELETE request.

        Args:
            path: Request path.
            params: Query parameters.
            headers: Additional headers.
            timeout: Request timeout override.

        Returns:
            Response from the server.
        """
        return self.request(
            APIRequest(
                method="DELETE",
                path=path,
                params=params or {},
                headers=headers or {},
                timeout=timeout,
            )
        )

    def patch(
        self,
        path: str,
        json_body: dict[str, Any] | list[Any] | None = None,
        params: Mapping[str, str | int | float | bool | None] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """Execute a PATCH request.

        Args:
            path: Request path.
            json_body: JSON request body.
            params: Query parameters.
            headers: Additional headers.
            timeout: Request timeout override.

        Returns:
            Response from the server.
        """
        return self.request(
            APIRequest(
                method="PATCH",
                path=path,
                json_body=json_body,
                params=params or {},
                headers=headers or {},
                timeout=timeout,
            )
        )

    def close(self) -> None:
        """Close the underlying session and release resources."""
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
        """Exit context manager, closing session."""
        self.close()


__all__ = ["APIClient"]
