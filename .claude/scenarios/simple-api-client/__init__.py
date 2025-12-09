"""Simple HTTP API client for JSON APIs.

A minimal, zero-BS HTTP client for JSON APIs.

Example:
    >>> from simple_api_client import get, post, APIError
    >>> data = get("https://jsonplaceholder.typicode.com/posts/1")
    >>> print(data["title"])
"""

from .simple_api_client import DEFAULT_TIMEOUT, APIError, get, post

__all__ = ["get", "post", "APIError", "DEFAULT_TIMEOUT"]
