"""API Client exceptions - all custom errors.

Philosophy: Simple exception hierarchy with clear purposes.
"""


class ApiClientError(Exception):
    """Base exception for API client."""


class RetryExhaustedError(ApiClientError):
    """All retry attempts failed."""

    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Failed after {attempts} attempts: {last_error}")


class ValidationError(ApiClientError):
    """Request validation failed."""


class SecurityError(ApiClientError):
    """Security check failed (SSRF, SSL, etc)."""


__all__ = ["ApiClientError", "RetryExhaustedError", "ValidationError", "SecurityError"]
