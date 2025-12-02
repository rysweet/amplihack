"""REST API Client - Standard library HTTP client with security and retries.

Philosophy:
- Standard library only (urllib)
- SSRF protection built-in
- Exponential backoff with jitter
- Simple and regeneratable
- Zero-BS implementation (no stubs, every function works)

Public API:
    RestApiClient: Main client class
    RestApiConfig: Configuration dataclass
    ApiResponse: Response wrapper
    SecurityValidator: Security validation utilities
    RetryHandler: Retry logic handler
    Exceptions: ApiClientError, RetryExhaustedError, SecurityError, ValidationError

Example:
    >>> from amplihack.api_client import RestApiClient, RestApiConfig
    >>> config = RestApiConfig(base_url="https://api.example.com")
    >>> client = RestApiClient(config)
    >>> response = client.get("/users")
    >>> users = response.json()
"""

from .config import RestApiConfig
from .core import RestApiClient
from .exceptions import (
    ApiClientError,
    RetryExhaustedError,
    SecurityError,
    ValidationError,
)
from .response import ApiResponse
from .retry import RetryHandler
from .security import SecurityValidator

__version__ = "0.1.0"

__all__ = [
    "RestApiClient",
    "RestApiConfig",
    "ApiResponse",
    "SecurityValidator",
    "RetryHandler",
    "ApiClientError",
    "RetryExhaustedError",
    "SecurityError",
    "ValidationError",
]
