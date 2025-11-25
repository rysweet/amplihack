"""
Data models for authentication system.
Using Pydantic for validation and SQLAlchemy models integration.
"""

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
import re


# ============================================================================
# User Models
# ============================================================================

class User:
    """User model - matches database schema."""

    def __init__(
        self,
        id: str,
        email: str,
        username: str,
        password_hash: str,
        is_active: bool = True,
        is_verified: bool = False,
        is_locked: bool = False,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_login_at: Optional[datetime] = None,
        failed_login_attempts: int = 0,
        locked_until: Optional[datetime] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ):
        self.id = id
        self.email = email
        self.username = username
        self.password_hash = password_hash
        self.is_active = is_active
        self.is_verified = is_verified
        self.is_locked = is_locked
        self.roles = roles or ["user"]
        self.permissions = permissions or []
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.last_login_at = last_login_at
        self.failed_login_attempts = failed_login_attempts
        self.locked_until = locked_until
        self.first_name = first_name
        self.last_name = last_name


# ============================================================================
# Request Models
# ============================================================================

class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128)
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)

    @validator("password")
    def validate_password_strength(cls, v):
        """Validate password meets complexity requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[@$!%*?&]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class LoginRequest(BaseModel):
    """User login request."""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: str = Field(..., min_length=1)
    remember_me: bool = False

    @validator("email", always=True)
    def email_or_username_required(cls, v, values):
        """Ensure either email or username is provided."""
        if not v and not values.get("username"):
            raise ValueError("Either email or username must be provided")
        return v


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class RevokeTokenRequest(BaseModel):
    """Token revocation request (admin only)."""
    token_id: str
    reason: Optional[str] = None


# ============================================================================
# Response Models
# ============================================================================

class UserResponse(BaseModel):
    """User response model."""
    id: str
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    roles: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TokenPayload(BaseModel):
    """Token payload for validation."""
    user_id: str
    email: str
    username: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
    token_type: str = "access"
    jti: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None


class LoginResponse(BaseModel):
    """Login response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserResponse


class RefreshResponse(BaseModel):
    """Token refresh response."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class VerifyResponse(BaseModel):
    """Token verification response."""
    valid: bool
    user_id: str
    issued_at: datetime
    expires_at: datetime
    token_id: str


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


# ============================================================================
# Error Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Error detail structure."""
    code: str
    message: str
    details: Optional[dict] = None
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ErrorDetail
