"""REST API Client for amplihack.

A robust, async-first HTTP client with enterprise-grade features including
automatic retry logic, rate limiting, and comprehensive error handling.

Example:
    >>> from amplihack.api_client import APIClient
    >>> async with APIClient(base_url="https://api.example.com") as client:
    ...     response = await client.get("/users/123")
    ...     user = response.data
"""

from .client import APIClient
from .exceptions import (
    APIClientError,
    AuthenticationError,
    BadGatewayError,
    ClientError,
    ConfigurationError,
    ConnectionError,
    DNSError,
    HTTPError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    SSLError,
    TimeoutError,
    ValidationError,
    error_from_response,
    parse_error_response,
)
from .models import (
    APIConfig,
    ErrorDetail,
    RateLimitInfo,
    Request,
    Response,
    RetryConfig,
)
from .rate_limiter import RateLimitConfig, RateLimitHandler
from .retry import RetryHandler

__all__ = [
    # Main client
    "APIClient",
    # Configuration
    "APIConfig",
    "RetryConfig",
    "RateLimitConfig",
    # Models
    "Request",
    "Response",
    "RateLimitInfo",
    "ErrorDetail",
    # Exceptions
    "APIClientError",
    "NetworkError",
    "TimeoutError",
    "ConnectionError",
    "DNSError",
    "SSLError",
    "RateLimitError",
    "ValidationError",
    "HTTPError",
    "AuthenticationError",
    "ServerError",
    "ClientError",
    "NotFoundError",
    "ServiceUnavailableError",
    "BadGatewayError",
    "ConfigurationError",
    # Exception helpers
    "error_from_response",
    "parse_error_response",
    # Handlers
    "RetryHandler",
    "RateLimitHandler",
]

__version__ = "1.0.0"
