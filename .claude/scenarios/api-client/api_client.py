"""API Client Module - A simple, reusable HTTP client.

Philosophy:
- Single responsibility: HTTP API communication
- Standard library + requests only
- Self-contained and regeneratable
- Zero-BS: No stubs, no TODOs, all code works

Public API (the "studs"):
    APIClient: Main client class for making HTTP requests
    APIError: Exception for HTTP and connection errors
    AuthType: Enum for authentication methods (NONE, BEARER, API_KEY)
"""

from enum import Enum
from typing import Any

import requests


class AuthType(Enum):
    """Authentication types supported by the API client."""

    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"  # pragma: allowlist secret


class APIError(Exception):
    """Exception raised for API errors.

    Attributes:
        status_code: HTTP status code (0 for connection errors)
        message: Human-readable error message
        response_body: Raw response body for debugging (optional)
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.response_body = response_body


class APIClient:
    """HTTP API client with configurable authentication and timeout.

    Supports:
    - Bearer token authentication
    - API key authentication (custom header)
    - No authentication
    - Configurable timeout
    - GET, POST, PUT, DELETE methods

    Example:
        >>> client = APIClient(
        ...     base_url="https://api.example.com",
        ...     auth_type=AuthType.BEARER,
        ...     auth_token="my-token",
        ...     timeout=30
        ... )
        >>> result = client.get("/users/1")
        >>> print(result)
        {'id': 1, 'name': 'Example User'}
    """

    def __init__(
        self,
        base_url: str,
        auth_type: AuthType = AuthType.NONE,
        auth_token: str | None = None,
        api_key_header: str = "X-API-Key",
        timeout: int = 30,
    ) -> None:
        """Initialize the API client.

        Args:
            base_url: Base URL for all API requests (e.g., "https://api.example.com")
            auth_type: Authentication method to use (default: AuthType.NONE)
            auth_token: Token for Bearer auth or API key value (default: None)
            api_key_header: Header name for API key auth (default: "X-API-Key")
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url
        self.auth_type = auth_type
        self.auth_token = auth_token
        self.api_key_header = api_key_header
        self.timeout = timeout

    def _build_headers(self) -> dict[str, str]:
        """Build request headers including authentication if configured."""
        headers: dict[str, str] = {}

        if self.auth_type == AuthType.BEARER and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        elif self.auth_type == AuthType.API_KEY and self.auth_token:
            headers[self.api_key_header] = self.auth_token

        return headers

    def _build_url(self, path: str) -> str:
        """Build full URL from base URL and path."""
        # Handle trailing slash on base_url and leading slash on path
        base = self.base_url.rstrip("/")
        path = "/" + path.lstrip("/") if path else ""
        return f"{base}{path}"

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        """Handle HTTP response, raising APIError for non-2xx status codes.

        Args:
            response: Response object from requests library

        Returns:
            Parsed JSON response as dict

        Raises:
            APIError: For 4xx/5xx status codes or invalid JSON
        """
        # Check for error status codes
        if response.status_code >= 400:
            raise APIError(
                status_code=response.status_code,
                message=f"HTTP {response.status_code} error",
                response_body=response.text,
            )

        # Parse JSON response
        try:
            return response.json()
        except (ValueError, TypeError) as e:
            raise APIError(
                status_code=response.status_code,
                message=f"Invalid JSON in response: {e}",
                response_body=response.text,
            )

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API endpoint path
            params: Query parameters for GET requests
            data: JSON body for POST/PUT requests

        Returns:
            Parsed JSON response as dict

        Raises:
            APIError: For connection errors, timeouts, HTTP errors, or invalid JSON
        """
        url = self._build_url(path)
        headers = self._build_headers()

        try:
            if method == "GET":
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout,
                )
            elif method == "POST":
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=self.timeout,
                )
            elif method == "PUT":
                response = requests.put(
                    url,
                    headers=headers,
                    json=data,
                    timeout=self.timeout,
                )
            elif method == "DELETE":
                response = requests.delete(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                )
            else:
                raise APIError(
                    status_code=0,
                    message=f"Unsupported HTTP method: {method}",
                )

            return self._handle_response(response)

        except APIError:
            # Re-raise APIError from _handle_response without wrapping
            raise
        except Exception as e:
            # Handle requests library exceptions
            # Check exception type by name to handle mocked requests in tests
            exc_type = type(e).__name__
            if exc_type == "Timeout" or "timeout" in str(e).lower():
                raise APIError(
                    status_code=0,
                    message=f"Request timeout after {self.timeout}s: {e}",
                )
            if exc_type == "ConnectionError" or "connection" in str(e).lower():
                raise APIError(
                    status_code=0,
                    message=f"Connection error: {e}",
                )
            raise APIError(
                status_code=0,
                message=f"Request failed: {e}",
            )

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request.

        Args:
            path: API endpoint path
            params: Optional query parameters

        Returns:
            Parsed JSON response as dict

        Raises:
            APIError: For any request errors
        """
        return self._request("GET", path, params=params)

    def post(self, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a POST request.

        Args:
            path: API endpoint path
            data: Optional JSON body data

        Returns:
            Parsed JSON response as dict

        Raises:
            APIError: For any request errors
        """
        return self._request("POST", path, data=data)

    def put(self, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a PUT request.

        Args:
            path: API endpoint path
            data: Optional JSON body data

        Returns:
            Parsed JSON response as dict

        Raises:
            APIError: For any request errors
        """
        return self._request("PUT", path, data=data)

    def delete(self, path: str) -> dict[str, Any]:
        """Make a DELETE request.

        Args:
            path: API endpoint path

        Returns:
            Parsed JSON response as dict

        Raises:
            APIError: For any request errors
        """
        return self._request("DELETE", path)


__all__ = ["APIClient", "APIError", "AuthType"]
