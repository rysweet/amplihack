"""
Exception classes for authentication.
"""

from .exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    AccountLockedError,
    AccountNotActiveError,
    TooManyFailedAttemptsError,
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    TokenBlacklistedError,
    UserError,
    UserAlreadyExistsError,
    UserNotFoundError,
    RateLimitExceededError,
    InsufficientPermissionsError,
)

__all__ = [
    "AuthenticationError",
    "InvalidCredentialsError",
    "AccountLockedError",
    "AccountNotActiveError",
    "TooManyFailedAttemptsError",
    "TokenError",
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenBlacklistedError",
    "UserError",
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "RateLimitExceededError",
    "InsufficientPermissionsError",
]
