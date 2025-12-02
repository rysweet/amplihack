"""REST API Client module.

A production-ready REST API client with:
- Automatic retry with exponential backoff
- Rate limit handling (429 responses)
- Sensitive header redaction in logs
- Context manager for proper resource cleanup

Philosophy:
- Single responsibility: Each component handles one thing
- Self-contained: Only depends on standard library and requests
- Regeneratable: Can be rebuilt from this specification

Example:
    >>> from amplihack.utils.api_client import APIClient, APIClientConfig
    >>> config = APIClientConfig(base_url="https://api.example.com")
    >>> with APIClient(config) as client:
    ...     response = client.get("/users/123")
    ...     print(response.json)

Public API:
    APIClient: Main client class
    APIClientConfig: Configuration dataclass
    APIRequest: Request data model
    APIResponse: Response data model
    Exception classes for error handling
"""

from .client import APIClient
from .config import APIClientConfig
from .exceptions import (
    APIClientError,
    ClientError,
    ConfigurationError,
    RateLimitError,
    RequestError,
    ResponseError,
    RetryExhaustedError,
    ServerError,
)
from .models import APIRequest, APIResponse
from .rate_limit import RateLimitHandler
from .retry import RetryHandler

__all__ = [
    # Main classes
    "APIClient",
    "APIClientConfig",
    # Models
    "APIRequest",
    "APIResponse",
    # Exceptions
    "APIClientError",
    "RequestError",
    "ResponseError",
    "RateLimitError",
    "ServerError",
    "ClientError",
    "RetryExhaustedError",
    "ConfigurationError",
    # Handlers
    "RetryHandler",
    "RateLimitHandler",
]
