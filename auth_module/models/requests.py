"""
Request models for JWT authentication API.
Pydantic models that match OpenAPI schemas exactly.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, constr, UUID4
import re


# Password regex pattern
PASSWORD_PATTERN = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr = Field(
        ...,
        max_length=255,
        description="User email address"
    )
    password: constr(
        min_length=8,
        max_length=128,
        regex=PASSWORD_PATTERN
    ) = Field(
        ...,
        description="Password must contain uppercase, lowercase, number, and special character"
    )
    username: constr(
        min_length=3,
        max_length=30,
        regex=r'^[a-zA-Z0-9_-]+$'
    ) = Field(
        ...,
        description="Username for display"
    )

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecureP@ss123",
                "username": "john_doe"
            }
        }


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr = Field(
        ...,
        description="User email address"
    )
    password: str = Field(
        ...,
        description="User password"
    )

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecureP@ss123"
            }
        }


class RevokeRequest(BaseModel):
    """Token revocation request (admin only)."""
    token_id: UUID4 = Field(
        ...,
        description="Unique identifier of the token to revoke"
    )
    reason: Optional[constr(max_length=255)] = Field(
        None,
        description="Optional reason for revocation"
    )

    class Config:
        schema_extra = {
            "example": {
                "token_id": "550e8400-e29b-41d4-a716-446655440000",
                "reason": "Security breach detected"
            }
        }