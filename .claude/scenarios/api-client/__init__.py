"""API Client - Simple, reliable HTTP client with automatic retry and rate limiting.

Philosophy:
- Single responsibility: HTTP requests with retry and rate limiting
- Standard library + requests only
- Self-contained and regeneratable

Public API (the "studs"):
    APIClient: Main HTTP client class with get, post, put, delete methods
    APIResponse: Immutable response container with status_code, body, headers, elapsed_ms
    APIClientError: Single exception class with error_type for specific handling
"""

from .client import APIClient, APIClientError, APIResponse

__all__ = ["APIClient", "APIResponse", "APIClientError"]
