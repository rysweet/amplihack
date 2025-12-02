"""REST API Client Module.

Philosophy:
- Self-contained module following brick philosophy
- Clear public API via __all__
- Standard library + requests only
- Zero-BS implementation (no stubs or placeholders)

Public API:
    APIClient: Main HTTP client
    Request: Request data model
    Response: Response data model
    RateLimiter: Rate limiting
    RetryHandler: Retry logic

    Exceptions:
        APIError: Base exception
        RequestError: Request failed
        ResponseError: Response error
        RateLimitError: Rate limit exceeded
        RetryExhaustedError: Retries exhausted

Example:
    >>> from api_client import APIClient, Request, RateLimiter
    >>>
    >>> # Create client with rate limiting
    >>> limiter = RateLimiter(max_requests=10, time_window=60.0)
    >>> client = APIClient(
    ...     base_url="https://api.example.com",
    ...     rate_limiter=limiter
    ... )
    >>>
    >>> # Make request
    >>> request = Request(method="GET", endpoint="/users")
    >>> response = client.send(request)
    >>> print(response.data)
"""

from .client import APIClient
from .exceptions import (
    APIError,
    RateLimitError,
    RequestError,
    ResponseError,
    RetryExhaustedError,
)
from .models import Request, Response
from .rate_limiter import RateLimiter
from .retry import RetryHandler

__version__ = "1.0.0"

__all__ = [
    # Main client
    "APIClient",
    # Data models
    "Request",
    "Response",
    # Utilities
    "RateLimiter",
    "RetryHandler",
    # Exceptions
    "APIError",
    "RequestError",
    "ResponseError",
    "RateLimitError",
    "RetryExhaustedError",
]
