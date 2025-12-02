"""API Client module - REST API client with retry and rate limiting.

A self-contained HTTP client library following the brick philosophy:
- Single responsibility: HTTP API interactions
- Clear public API via __all__
- Regeneratable from specification

Public API:
    APIClient: Main HTTP client class
    Request: HTTP request dataclass
    Response: HTTP response dataclass
    APIClientError: Base exception class
    ConnectionError: Network connection failures
    TimeoutError: Request timeout errors
    RateLimitError: 429 rate limit errors
    ServerError: 5xx server errors
    ClientError: 4xx client errors
"""

from .client import APIClient
from .exceptions import (
    APIClientError,
    ClientError,
    ConnectionError,
    RateLimitError,
    ServerError,
    TimeoutError,
    create_exception_from_response,
)
from .models import Request, Response

__all__ = [
    # Main client
    "APIClient",
    # Models
    "Request",
    "Response",
    # Exceptions
    "APIClientError",
    "ConnectionError",
    "TimeoutError",
    "RateLimitError",
    "ServerError",
    "ClientError",
    "create_exception_from_response",
]

__version__ = "0.1.0"
