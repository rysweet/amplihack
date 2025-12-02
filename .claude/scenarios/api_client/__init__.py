"""APIClient module - async HTTP client with retry logic.

Public API:
    APIClient: Async HTTP client with automatic retry
    Request: HTTP request dataclass
    Response: HTTP response dataclass
    APIClientError: Base exception
    NetworkError: Connection/timeout errors (retriable)
    HTTPError: Non-2xx responses
"""

from api_client.client import (
    APIClient,
    APIClientError,
    HTTPError,
    NetworkError,
    Request,
    Response,
)

__all__ = [
    "APIClient",
    "Request",
    "Response",
    "APIClientError",
    "NetworkError",
    "HTTPError",
]
