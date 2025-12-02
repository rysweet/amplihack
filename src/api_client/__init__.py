"""REST API Client with retry handling and rate limiting.

This package provides a production-ready HTTP client with:
- Automatic retries with exponential backoff and jitter
- Thread-safe token bucket rate limiting
- Structured logging with credential sanitization
- Timeout enforcement on all requests

Public API (the "studs"):
    APIClient: Main HTTP client class
    RetryPolicy: Configures retry behavior
    RateLimiter: Thread-safe rate limiting
    APIClientError: Base exception
    NetworkError: Connection/timeout errors (always retryable)
    HTTPError: HTTP response errors (conditionally retryable)

Example:
    >>> from api_client import APIClient, RetryPolicy
    >>> policy = RetryPolicy(max_retries=5)
    >>> client = APIClient(
    ...     base_url="https://api.example.com",
    ...     retry_policy=policy
    ... )
    >>> response = client.get("/users/123")
    >>> print(response.json())
"""

from .client import APIClient
from .rate_limiter import RateLimiter
from .retry import RetryPolicy
from .types import APIClientError, HTTPError, NetworkError

__all__ = [
    "APIClient",
    "RetryPolicy",
    "RateLimiter",
    "APIClientError",
    "NetworkError",
    "HTTPError",
]

__version__ = "1.0.0"
