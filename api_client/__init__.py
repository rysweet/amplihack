"""REST API Client module.

A simple, robust HTTP client with retry logic and proper error handling.

Philosophy:
- Single responsibility: HTTP client with retry
- Standard library for core, requests for HTTP
- Self-contained and regeneratable

Public API (the "studs"):
    APIClient: Main HTTP client with retry and rate limiting
    Request: Request dataclass
    Response: Response dataclass
    RetryStrategy: Retry decision logic
    APIError, ConnectionError, TimeoutError, RateLimitError,
    ServerError, ClientError, RetryExhaustedError: Exception hierarchy

Example:
    >>> from api_client import APIClient
    >>> client = APIClient(base_url="https://api.example.com")
    >>> response = client.get("/users")
    >>> print(response.json_data)
"""

from .client import APIClient
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

__version__ = "0.1.0"

__all__ = [
    "APIClient",
    "Request",
    "Response",
    "RetryStrategy",
    "APIError",
    "ConnectionError",
    "TimeoutError",
    "RateLimitError",
    "ServerError",
    "ClientError",
    "RetryExhaustedError",
]
