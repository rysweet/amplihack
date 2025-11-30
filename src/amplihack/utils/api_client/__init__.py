"""
REST API Client - Production-ready HTTP client with retry and rate limiting.

Philosophy:
- Ruthless simplicity with powerful features
- Security by default
- Clear public API via __all__
- Modular brick design (self-contained, regeneratable)

Public API (the "studs"):
    APIClient: Main client class
    APIRequest: Request dataclass
    APIResponse: Response dataclass
    RetryConfig: Retry configuration
    RateLimitConfig: Rate limit configuration
    APIClientError: Base exception
    RequestError: Network/connection errors
    HTTPError: HTTP status errors
    RateLimitError: Rate limit errors
    RetryExhaustedError: Retry exhaustion
    ResponseError: Response parsing errors

Example:
    >>> from amplihack.utils.api_client import APIClient
    >>> client = APIClient(base_url="https://api.example.com")
    >>> response = client.get("/users/123")
    >>> print(response.data)
"""

# Import all public components
from .client import APIClient
from .config import RateLimitConfig, RetryConfig
from .exceptions import (
    APIClientError,
    HTTPError,
    RateLimitError,
    RequestError,
    ResponseError,
    RetryExhaustedError,
)
from .models import APIRequest, APIResponse

# Define public API
__all__ = [
    # Main client
    "APIClient",
    # Request/response models
    "APIRequest",
    "APIResponse",
    # Configuration
    "RetryConfig",
    "RateLimitConfig",
    # Exceptions
    "APIClientError",
    "RequestError",
    "HTTPError",
    "RateLimitError",
    "RetryExhaustedError",
    "ResponseError",
]
