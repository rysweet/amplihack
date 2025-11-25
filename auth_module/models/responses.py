"""
Response models for JWT authentication API.
Pydantic models that match OpenAPI schemas exactly.
"""

from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, UUID4
from enum import Enum


class TokenType(str, Enum):
    """Token type enumeration."""
    BEARER = "Bearer"


class UserResponse(BaseModel):
    """User information response."""
    id: UUID4 = Field(
        ...,
        description="User unique identifier"
    )
    email: str = Field(
        ...,
        description="User email address"
    )
    username: str = Field(
        ...,
        description="User display name"
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp"
    )

    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "username": "john_doe",
                "created_at": "2024-01-15T09:30:00Z"
            }
        }


class LoginResponse(BaseModel):
    """Successful login response."""
    access_token: str = Field(
        ...,
        description="JWT access token for API requests"
    )
    token_type: TokenType = Field(
        TokenType.BEARER,
        description="Token type (always Bearer)"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds"
    )
    user: UserResponse = Field(
        ...,
        description="Authenticated user information"
    )

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 900,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "username": "john_doe",
                    "created_at": "2024-01-15T09:30:00Z"
                }
            }
        }


class RefreshResponse(BaseModel):
    """Token refresh response."""
    access_token: str = Field(
        ...,
        description="New JWT access token"
    )
    token_type: TokenType = Field(
        TokenType.BEARER,
        description="Token type (always Bearer)"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds"
    )

    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 900
            }
        }


class VerifyResponse(BaseModel):
    """Token verification response."""
    valid: bool = Field(
        ...,
        description="Token validity status"
    )
    user_id: UUID4 = Field(
        ...,
        description="ID of the token owner"
    )
    issued_at: datetime = Field(
        ...,
        description="Token issue timestamp"
    )
    expires_at: datetime = Field(
        ...,
        description="Token expiration timestamp"
    )
    token_id: Optional[UUID4] = Field(
        None,
        description="Unique identifier of the token"
    )

    class Config:
        schema_extra = {
            "example": {
                "valid": True,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "issued_at": "2024-01-15T09:30:00Z",
                "expires_at": "2024-01-15T09:45:00Z",
                "token_id": "660e8400-e29b-41d4-a716-446655440000"
            }
        }


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str = Field(
        ...,
        description="Response message"
    )

    class Config:
        schema_extra = {
            "example": {
                "message": "Operation completed successfully"
            }
        }


class ErrorDetail(BaseModel):
    """Error response details."""
    code: str = Field(
        ...,
        description="Error code for programmatic handling"
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error context"
    )
    request_id: Optional[UUID4] = Field(
        None,
        description="Unique request identifier for debugging"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ErrorDetail = Field(
        ...,
        description="Error information"
    )

    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters",
                    "details": {
                        "field": "email",
                        "reason": "Invalid email format"
                    },
                    "request_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            }
        }