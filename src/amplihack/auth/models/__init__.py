"""
Data models for authentication.
"""

from .models import (
    User,
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    RevokeTokenRequest,
    UserResponse,
    TokenPayload,
    LoginResponse,
    RefreshResponse,
    VerifyResponse,
    MessageResponse,
    ErrorDetail,
    ErrorResponse,
)

# Aliases for compatibility
RefreshToken = TokenPayload
AccessToken = TokenPayload

__all__ = [
    "User",
    "RegisterRequest",
    "LoginRequest",
    "RefreshTokenRequest",
    "RevokeTokenRequest",
    "UserResponse",
    "TokenPayload",
    "LoginResponse",
    "RefreshResponse",
    "VerifyResponse",
    "MessageResponse",
    "ErrorDetail",
    "ErrorResponse",
    "RefreshToken",
    "AccessToken",
]
