"""REST API client library for amplihack.

This package provides a robust REST API client with retry logic,
rate limiting, and proper error handling.

Philosophy:
- Simple, direct API design
- Built on requests library
- Thread-safe using thread-local sessions
- Comprehensive error handling

Public API:
    APIClient: Main client class for making HTTP requests
    APIRequest: Request data model
    APIResponse: Response data model
    APIError: Base exception class
    RateLimitError: Rate limit exception (HTTP 429)
    TimeoutError: Timeout exception
    AuthenticationError: Authentication exception (HTTP 401/403)
"""

from .client import APIClient
from .exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
)
from .models import APIRequest, APIResponse

__all__ = [
    # Client
    "APIClient",
    # Exceptions
    "APIError",
    "RateLimitError",
    "TimeoutError",
    "AuthenticationError",
    # Models
    "APIRequest",
    "APIResponse",
]

__version__ = "0.1.0"
