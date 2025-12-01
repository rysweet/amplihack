"""REST API Client library.

A simple, type-safe HTTP client with built-in retry logic, rate limiting,
and comprehensive error handling.

Philosophy:
- Type-safe dataclasses for requests and responses
- Zero-BS implementation (no stubs or placeholders)
- Ruthless simplicity (minimal abstractions)
- Standard library only (beyond requests)

Public API:
    HTTPClient: Main HTTP client
    Request: Immutable request dataclass
    Response: Immutable response dataclass
    APIError: Base exception
    ClientError: 4xx errors
    ServerError: 5xx errors
    RateLimiter: Token bucket rate limiter
    RetryPolicy: Exponential backoff retry policy

Example:
    >>> from api_client import HTTPClient, Request
    >>> client = HTTPClient()
    >>> response = client.send(Request(
    ...     url="https://api.example.com/users",
    ...     method="GET"
    ... ))
    >>> response.status_code
    200
"""

# Import and export all public classes
from api_client.client import HTTPClient
from api_client.exceptions import APIError, ClientError, ServerError
from api_client.models import Request, Response
from api_client.rate_limiter import RateLimiter
from api_client.retry import RetryPolicy

__all__ = [
    "HTTPClient",
    "Request",
    "Response",
    "APIError",
    "ClientError",
    "ServerError",
    "RateLimiter",
    "RetryPolicy",
]

__version__ = "1.0.0"
