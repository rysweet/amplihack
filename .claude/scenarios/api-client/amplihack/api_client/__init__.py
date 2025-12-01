"""REST API Client - Public Interface.

Production-ready HTTP client with intelligent retry logic, rate limiting,
and comprehensive error handling.

Philosophy:
- Ruthless simplicity - start simple, add complexity only when needed
- Zero-BS - every function works or doesn't exist
- Type hints throughout for clarity
- Modular design following the brick pattern

Public API exports via __all__ (the "studs" that others connect to).
"""

__version__ = "1.0.0"

from amplihack.api_client.client import RestClient
from amplihack.api_client.exceptions import (
    APIError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    RequestError,
    ResponseError,
    RetryExhaustedError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from amplihack.api_client.models import (
    APIKeyAuth,
    BearerAuth,
    ClientConfig,
    RateLimiter,
    Request,
    Response,
    RetryPolicy,
)

__all__ = [
    "__version__",
    "APIError",
    "RequestError",
    "ResponseError",
    "TimeoutError",
    "RateLimitError",
    "AuthenticationError",
    "NotFoundError",
    "ServerError",
    "ValidationError",
    "RetryExhaustedError",
    "Request",
    "Response",
    "ClientConfig",
    "RetryPolicy",
    "RateLimiter",
    "BearerAuth",
    "APIKeyAuth",
    "RestClient",
]
