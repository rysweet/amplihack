"""REST API Client - A robust HTTP client with retry and rate limiting.

This module provides a comprehensive REST API client with:
- Automatic retry with exponential backoff
- Token bucket rate limiting
- Custom exception hierarchy
- Request/response logging
- Session management with connection pooling

Example:
    from rest_api_client import APIClient

    client = APIClient("https://api.example.com")
    response = client.get("/users")
    print(response.json_data)

Public API (the "studs"):
    APIClient: Main client class
    APIRequest: Request data model
    APIResponse: Response data model
    ClientConfig: Client configuration
    RetryConfig: Retry configuration
    RateLimitConfig: Rate limit configuration
    APIException: Base exception class
    ConnectionError: Connection failure exception
    TimeoutError: Timeout exception
    RateLimitError: Rate limit exception
    AuthenticationError: Auth failure exception
    ValidationError: Validation failure exception
    ServerError: Server error exception
    ClientError: Client error exception
"""

# Main client
from .client import APIClient

# Configuration
from .config import ClientConfig, RateLimitConfig, RetryConfig

# Exceptions
from .exceptions import (
    APIClientError,
    AuthenticationError,
    ClientError,
    HTTPResponseError,
    NetworkError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)

# Data models
from .models import APIRequest, APIResponse

# Define public API
__all__ = [
    # Client
    "APIClient",
    # Models
    "APIRequest",
    "APIResponse",
    # Configuration
    "ClientConfig",
    "RetryConfig",
    "RateLimitConfig",
    # Exceptions
    "APIClientError",
    "HTTPResponseError",
    "NetworkError",
    "TimeoutError",
    "RateLimitError",
    "AuthenticationError",
    "ValidationError",
    "ServerError",
    "ClientError",
]

# Version info
__version__ = "1.0.0"
