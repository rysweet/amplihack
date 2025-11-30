"""REST API Client - A modular, robust HTTP client with retry and rate limiting.

This package provides a comprehensive REST API client with:
- Standard HTTP methods (GET, POST, PUT, DELETE, PATCH)
- Automatic retry logic with exponential backoff
- Rate limiting to handle 429 responses
- Custom exception hierarchy for precise error handling
- Request/Response dataclasses for type safety
- Configuration management with environment variable support

Basic Usage:
    from rest_api_client import APIClient

    # Simple usage
    client = APIClient(base_url="https://api.example.com")
    response = client.get("/users")

    # With authentication
    client = APIClient(
        base_url="https://api.example.com",
        api_key="<your-api-key>"
    )

    # With custom configuration
    from rest_api_client import APIConfig

    config = APIConfig(
        base_url="https://api.example.com",
        timeout=60,
        max_retries=5
    )
    client = APIClient(config=config)
"""

# Import main components for public API
from .client import APIClient
from .config import APIConfig, load_config, merge_configs, validate_config
from .exceptions import (
    APIClientError,
    AuthenticationError,
    ConnectionError,
    HTTPError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from .models import APIError, Request, RequestMethod, Response
from .rate_limiter import AdaptiveRateLimiter, RateLimiter, SlidingWindow, TokenBucket
from .retry import ExponentialBackoff, LinearBackoff, RetryManager, should_retry

__version__ = "1.0.0"

# Define public API
__all__ = [
    # Main client
    "APIClient",
    # Configuration
    "APIConfig",
    "load_config",
    "validate_config",
    "merge_configs",
    # Models
    "Request",
    "Response",
    "APIError",
    "RequestMethod",
    # Exceptions
    "APIClientError",
    "ConnectionError",
    "TimeoutError",
    "RateLimitError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "ServerError",
    "HTTPError",
    # Rate limiting
    "RateLimiter",
    "TokenBucket",
    "SlidingWindow",
    "AdaptiveRateLimiter",
    # Retry logic
    "ExponentialBackoff",
    "LinearBackoff",
    "RetryManager",
    "should_retry",
]
