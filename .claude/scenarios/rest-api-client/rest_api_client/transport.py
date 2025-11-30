"""HTTP transport layer using standard library.

This module provides HTTP communication functionality using only
Python's standard library (urllib).
"""

import json
import logging
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class HTTPTransport:
    """HTTP transport using urllib from standard library.

    Provides low-level HTTP communication with SSL support,
    timeout handling, and proper error mapping.
    """

    def __init__(
        self,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        ssl_context: ssl.SSLContext | None = None,
        logger: logging.Logger | None = None,
    ):
        """Initialize HTTP transport.

        Args:
            timeout: Default timeout for requests
            verify_ssl: Whether to verify SSL certificates
            ssl_context: Custom SSL context
            logger: Logger instance
        """
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.logger = logger or logging.getLogger(__name__)
        self.ssl_context = ssl_context or self._create_ssl_context()

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context based on verify_ssl setting.

        Returns:
            SSL context for HTTPS connections
        """
        if self.verify_ssl:
            # Use default secure context
            context = ssl.create_default_context()
        else:
            # Create context that doesn't verify certificates (dev only!)
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.logger.warning("SSL verification disabled - use only for development!")

        return context

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        data: bytes | str | dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> tuple[int, dict[str, str], bytes, float]:
        """Make HTTP request using urllib.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            params: Query parameters
            json_data: JSON data to send
            data: Raw data to send
            timeout: Request timeout

        Returns:
            Tuple of (status_code, headers, body, elapsed_time)

        Raises:
            ConnectionError: For connection issues
            TimeoutError: For timeout issues
            SSLError: For SSL issues
            DNSError: For DNS issues
        """
        start_time = time.time()
        headers = headers or {}
        timeout = timeout or self.timeout

        # Add query parameters to URL
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"

        # Prepare body
        body = self._prepare_body(json_data, data, headers)

        # Create request
        request = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            # Make request with proper SSL context
            response = urllib.request.urlopen(
                request,
                timeout=timeout,
                context=self.ssl_context if url.startswith("https") else None,
            )

            # Read response
            status_code = response.getcode()
            response_headers = dict(response.headers)
            response_body = response.read()

            elapsed_time = time.time() - start_time

            return status_code, response_headers, response_body, elapsed_time

        except urllib.error.HTTPError as e:
            # HTTP error (4xx, 5xx)
            elapsed_time = time.time() - start_time
            status_code = e.code
            response_headers = dict(e.headers) if hasattr(e, "headers") else {}

            try:
                response_body = e.read()
            except:
                response_body = b""

            return status_code, response_headers, response_body, elapsed_time

        except urllib.error.URLError as e:
            # Connection error
            elapsed_time = time.time() - start_time
            error_msg = str(e.reason)

            if isinstance(e.reason, ssl.SSLError):
                from .exceptions import SSLError

                raise SSLError(f"SSL error: {error_msg}", url=url, method=method)
            if "timed out" in error_msg.lower():
                from .exceptions import TimeoutError

                raise TimeoutError(
                    f"Request timed out after {timeout}s", url=url, method=method, timeout=timeout
                )
            if any(
                dns_err in error_msg.lower()
                for dns_err in [
                    "nodename nor servname",
                    "name or service not known",
                    "getaddrinfo failed",
                ]
            ):
                from .exceptions import DNSError

                raise DNSError(f"DNS resolution failed: {error_msg}", url=url, method=method)
            from .exceptions import ConnectionError

            raise ConnectionError(f"Connection failed: {error_msg}", url=url, method=method)

        except Exception as e:
            # Unexpected error
            from .exceptions import APIClientError

            raise APIClientError(f"Unexpected error during request: {e}", url=url, method=method)

    def _prepare_body(
        self,
        json_data: dict[str, Any] | None,
        data: bytes | str | dict[str, Any] | None,
        headers: dict[str, str],
    ) -> bytes | None:
        """Prepare request body and update headers.

        Args:
            json_data: JSON data to send
            data: Raw data to send
            headers: Headers dict to update

        Returns:
            Body as bytes or None
        """
        if json_data is not None:
            # JSON body
            body = json.dumps(json_data).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
            headers.setdefault("Content-Length", str(len(body)))
            return body

        if data is not None:
            if isinstance(data, dict):
                # Form-encoded data
                body = urllib.parse.urlencode(data).encode("utf-8")
                headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
            elif isinstance(data, str):
                body = data.encode("utf-8")
            else:
                # Assume bytes
                body = data

            headers.setdefault("Content-Length", str(len(body)))
            return body

        return None


class ConnectionPool:
    """Simple connection pooling for HTTP connections.

    Reuses connections when possible to improve performance.
    Note: This is a simplified implementation using urllib.
    """

    def __init__(self, max_connections: int = 10):
        """Initialize connection pool.

        Args:
            max_connections: Maximum number of pooled connections
        """
        self.max_connections = max_connections
        self._handlers = {}
        self.logger = logging.getLogger(__name__)

    def get_opener(
        self, url: str, ssl_context: ssl.SSLContext | None = None
    ) -> urllib.request.OpenerDirector:
        """Get or create an opener for the given URL.

        Args:
            url: Target URL
            ssl_context: SSL context for HTTPS

        Returns:
            URL opener
        """
        # Extract host from URL
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.netloc

        # Check if we have a cached opener
        if host in self._handlers:
            return self._handlers[host]

        # Create new opener
        if url.startswith("https") and ssl_context:
            https_handler = urllib.request.HTTPSHandler(context=ssl_context)
            opener = urllib.request.build_opener(https_handler)
        else:
            opener = urllib.request.build_opener()

        # Cache if under limit
        if len(self._handlers) < self.max_connections:
            self._handlers[host] = opener

        return opener

    def clear(self):
        """Clear all cached connections."""
        self._handlers.clear()


class MockTransport:
    """Mock transport for testing without network calls.

    Useful for unit tests and development.
    """

    def __init__(self):
        """Initialize mock transport."""
        self.requests = []
        self.responses = []
        self.default_response = (200, {}, b'{"success": true}', 0.1)

    def add_response(
        self,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        body: bytes | str | dict = b"",
        elapsed_time: float = 0.1,
    ):
        """Add a mock response.

        Args:
            status_code: HTTP status code
            headers: Response headers
            body: Response body
            elapsed_time: Simulated elapsed time
        """
        if isinstance(body, dict):
            body = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")

        self.responses.append((status_code, headers or {}, body, elapsed_time))

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        data: bytes | str | dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> tuple[int, dict[str, str], bytes, float]:
        """Mock HTTP request.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            params: Query parameters
            json_data: JSON data
            data: Raw data
            timeout: Timeout value

        Returns:
            Mock response tuple
        """
        # Record request
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params,
                "json": json_data,
                "data": data,
                "timeout": timeout,
            }
        )

        # Return response
        if self.responses:
            return self.responses.pop(0)
        return self.default_response

    def get_last_request(self) -> dict | None:
        """Get the last recorded request.

        Returns:
            Last request or None
        """
        return self.requests[-1] if self.requests else None

    def reset(self):
        """Reset mock transport."""
        self.requests.clear()
        self.responses.clear()
