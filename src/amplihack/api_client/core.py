"""Core REST API client implementation.

Philosophy: Standard library only (urllib), simple and regeneratable.
"""

import logging
import ssl
import urllib.error
import urllib.request
from typing import Any

from .config import RestApiConfig
from .exceptions import ApiClientError
from .response import ApiResponse
from .retry import RetryHandler
from .security import SecurityValidator

logger = logging.getLogger(__name__)


class RestApiClient:
    """REST API client with security, retries, and configuration.

    Features:
    - SSRF protection (blocks private IPs)
    - HTTPS enforcement
    - Exponential backoff with jitter
    - Configurable timeouts
    - SSL verification
    - Log sanitization

    Example:
        >>> config = RestApiConfig(base_url="https://api.example.com")
        >>> client = RestApiClient(config)
        >>> response = client.get("/users")
        >>> print(response.json())
    """

    def __init__(self, config: RestApiConfig):
        """Initialize REST API client.

        Args:
            config: Client configuration
        """
        self.config = config
        self.security = SecurityValidator()
        self.retry = RetryHandler(
            max_retries=config.max_retries,
            backoff=config.retry_backoff,
        )

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        allow_private: bool = False,
    ) -> ApiResponse:
        """Make HTTP request with security and retry.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc)
            path: URL path (appended to base_url)
            body: Request body (bytes)
            headers: Additional headers
            allow_private: Allow private IPs (for testing only)

        Returns:
            ApiResponse object

        Raises:
            ApiClientError: On request failure after all retries
            SecurityError: On security validation failure
        """
        # Build full URL
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"

        # Security validation (SSRF protection)
        self.security.validate_url(url, allow_private=allow_private)

        # Prepare headers
        req_headers = self.config.headers.copy() if self.config.headers else {}
        if headers:
            req_headers.update(headers)

        # Log request with sanitized headers
        sanitized = self.security.sanitize_headers(req_headers)
        logger.info(
            f"Making {method} request to {url}",
            extra={"method": method, "url": url, "headers": sanitized}
        )

        # Create SSL context
        ssl_context = ssl.create_default_context()
        if not self.config.verify_ssl:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        # Execute with retry
        def _do_request() -> ApiResponse:
            request = urllib.request.Request(
                url,
                data=body,
                headers=req_headers,
                method=method,
            )

            try:
                with urllib.request.urlopen(
                    request,
                    timeout=self.config.timeout,
                    context=ssl_context,
                ) as response:
                    return ApiResponse(
                        status_code=response.status,
                        body=response.read(),
                        headers=dict(response.headers),
                    )
            except urllib.error.HTTPError as e:
                # HTTP errors return response with error status
                response = ApiResponse(
                    status_code=e.code,
                    body=e.read() if e.fp else b"",
                    headers=dict(e.headers) if e.headers else {},
                )

                # Raise error for 5xx status codes to trigger retry
                if 500 <= response.status_code < 600:
                    raise ApiClientError(f"Server error {response.status_code}: {url}") from e

                return response
            except urllib.error.URLError as e:
                raise ApiClientError(f"Request failed: {e.reason}") from e
            except Exception as e:
                raise ApiClientError(f"Unexpected error: {e}") from e

        # Execute request with retry
        response = self.retry.execute(_do_request, retry_on=(ApiClientError,))

        # Log successful completion
        logger.info(
            f"Request completed: {method} {url} -> {response.status_code}",
            extra={"status_code": response.status_code}
        )

        return response

    def get(self, path: str, **kwargs: Any) -> ApiResponse:
        """Make GET request.

        Args:
            path: URL path
            **kwargs: Additional arguments for request()

        Returns:
            ApiResponse object
        """
        return self.request("GET", path, **kwargs)

    def post(self, path: str, body: bytes, **kwargs: Any) -> ApiResponse:
        """Make POST request.

        Args:
            path: URL path
            body: Request body (bytes)
            **kwargs: Additional arguments for request()

        Returns:
            ApiResponse object
        """
        return self.request("POST", path, body=body, **kwargs)

    def put(self, path: str, body: bytes, **kwargs: Any) -> ApiResponse:
        """Make PUT request.

        Args:
            path: URL path
            body: Request body (bytes)
            **kwargs: Additional arguments for request()

        Returns:
            ApiResponse object
        """
        return self.request("PUT", path, body=body, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> ApiResponse:
        """Make DELETE request.

        Args:
            path: URL path
            **kwargs: Additional arguments for request()

        Returns:
            ApiResponse object
        """
        return self.request("DELETE", path, **kwargs)


__all__ = ["RestApiClient"]
