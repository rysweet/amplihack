"""REST API Client with retry, rate limiting, and comprehensive error handling.

Philosophy:
- Single responsibility: HTTP communication with resilience
- Zero-BS: Every function works, no stubs
- Regeneratable: Can be rebuilt from specification

Public API (the "studs"):
    APIClient: Main async HTTP client
    HTTPMethod: Enum of HTTP methods
    RetryConfig: Configuration for retry behavior
    APIRequest: Immutable request representation
    APIResponse: Immutable response representation
    APIClientError: Base exception for all client errors
    RateLimitError: Rate limit exceeded (includes retry_after)
    RetryExhaustedError: All retry attempts failed
    APIConnectionError: Network connectivity issues
    APITimeoutError: Request timed out
    RateLimiter: Rate limit state tracker
    sanitize_headers: Header sanitization for logging
"""

from .client import APIClient
from .exceptions import (
    APIClientError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    RetryExhaustedError,
)
from .logging import MASK_VALUE, SENSITIVE_HEADERS, sanitize_headers
from .models import APIRequest, APIResponse, HTTPMethod, RetryConfig
from .rate_limiter import RateLimiter, RateLimitState
from .retry import calculate_delay, retry_async

__all__ = [
    # Client
    "APIClient",
    # Models
    "HTTPMethod",
    "RetryConfig",
    "APIRequest",
    "APIResponse",
    # Exceptions
    "APIClientError",
    "RateLimitError",
    "RetryExhaustedError",
    "APIConnectionError",
    "APITimeoutError",
    # Rate limiting
    "RateLimiter",
    "RateLimitState",
    # Retry utilities
    "calculate_delay",
    "retry_async",
    # Logging utilities
    "sanitize_headers",
    "SENSITIVE_HEADERS",
    "MASK_VALUE",
]
