"""API Client scenario module.

Simple HTTP client for JSON APIs following the Brick Philosophy.
"""

from .api_client import APIClient, APIError, AuthType

__all__ = ["APIClient", "APIError", "AuthType"]
