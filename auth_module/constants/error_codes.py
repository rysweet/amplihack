"""
Standardized error codes for JWT authentication API.
Single source of truth for all error responses.
"""

from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes matching OpenAPI specification."""

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_FIELD = "MISSING_FIELD"

    # Authentication errors
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_BLACKLISTED = "TOKEN_BLACKLISTED"

    # Authorization errors
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # Resource errors
    USER_EXISTS = "USER_EXISTS"
    TOKEN_NOT_FOUND = "TOKEN_NOT_FOUND"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Error messages mapped to codes
ERROR_MESSAGES = {
    ErrorCode.VALIDATION_ERROR: "Invalid request parameters",
    ErrorCode.MISSING_FIELD: "Required field missing",
    ErrorCode.INVALID_CREDENTIALS: "Invalid email or password",
    ErrorCode.TOKEN_EXPIRED: "Access token has expired",
    ErrorCode.TOKEN_INVALID: "Invalid or malformed token",
    ErrorCode.TOKEN_BLACKLISTED: "Token has been revoked",
    ErrorCode.INSUFFICIENT_PERMISSIONS: "Admin access required",
    ErrorCode.USER_EXISTS: "User with this email already exists",
    ErrorCode.TOKEN_NOT_FOUND: "Token not found",
    ErrorCode.RATE_LIMIT_EXCEEDED: "Too many requests, please try again later",
    ErrorCode.INTERNAL_ERROR: "An unexpected error occurred"
}


def get_error_message(code: ErrorCode) -> str:
    """Get standard error message for code."""
    return ERROR_MESSAGES.get(code, "An error occurred")