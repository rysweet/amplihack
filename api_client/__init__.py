"""REST API Client with zero dependencies.

A simple, robust REST API client using only Python's urllib standard library.
Provides automatic retries, rate limiting, and thread-safe operation.

Public API:
    APIClient: Main client class for making HTTP requests
    ClientConfig: Configuration dataclass for the client
    APIError: Base exception for API-related errors
    HTTPError: Exception for HTTP error responses (4xx, 5xx)
"""

from .client import APIClient
from .config import ClientConfig
from .exceptions import APIError, HTTPError

__all__ = ["APIClient", "ClientConfig", "APIError", "HTTPError"]

__version__ = "1.0.0"
