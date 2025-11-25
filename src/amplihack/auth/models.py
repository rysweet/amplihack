"""User models and schemas for authentication."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base user schema."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema with password."""

    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        return v


class UserLogin(BaseModel):
    """User login schema."""

    username: str
    password: str


class User(UserBase):
    """User schema for database storage."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    is_admin: bool = False
    hashed_password: str


class UserResponse(UserBase):
    """User response schema (without sensitive data)."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    id: str
    created_at: datetime
    is_active: bool = True
    is_admin: bool = False


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data schema for token payload."""

    user_id: str
    username: str
    is_admin: bool = False
