"""REST API Client - A robust, zero-dependency REST API client library.

Philosophy:
- Zero external dependencies (standard library only)
- Modular brick architecture with clear boundaries
- Every function must work - no stubs or placeholders
- Thread-safe operations with comprehensive logging

Public API (the "studs"):
    APIClient: Main client class for making HTTP requests
    Request: Request dataclass
    Response: Response dataclass
    APIClientError: Base exception class
    RateLimitError: Rate limit exception
    RetryConfig: Retry configuration dataclass
    RateLimitConfig: Rate limit configuration dataclass
"""

from .client import APIClient
from .exceptions import (
    APIClientError,
    ConfigurationError,
    ConnectionError,
    HTTPError,
    InvalidResponseError,
    MaxRetriesExceeded,
    RateLimitError,
    RateLimitExceeded,
    TimeoutError,
    ValidationError,
)
from .models import Request, Response
from .rate_limiter import RateLimitConfig
from .retry import RetryConfig

__version__ = "1.0.0"

__all__ = [
    # Main client
    "APIClient",
    # Data models
    "Request",
    "Response",
    # Configuration
    "RetryConfig",
    "RateLimitConfig",
    # Core exceptions (most commonly used)
    "APIClientError",
    "ConfigurationError",
    "ValidationError",
    "ConnectionError",
    "TimeoutError",
    "HTTPError",
    "RateLimitError",
    "InvalidResponseError",
    "MaxRetriesExceeded",
    "RateLimitExceeded",
]
