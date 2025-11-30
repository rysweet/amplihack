"""REST API Client - Simple HTTP client with rate limiting and retry logic.

A ruthlessly simple REST client using only Python standard library.
Built with the brick philosophy - self-contained, regeneratable, zero-BS.
"""

from .client import APIClient, RESTClient, StreamingResponse
from .exceptions import (
    APIClientError,
    APIConnectionError,
    APITimeoutError,
    ConfigurationError,
    HTTPError,
    RateLimitError,
)
from .models import Request, Response

__all__ = [
    # Primary client class
    "APIClient",
    # Backward compatibility alias
    "RESTClient",
    # Response types
    "Response",
    "StreamingResponse",
    "Request",
    # Exception hierarchy
    "APIClientError",
    "HTTPError",
    "RateLimitError",
    "APIConnectionError",
    "APITimeoutError",
    "ConfigurationError",
]

# Module metadata
__version__ = "2.1.0"
