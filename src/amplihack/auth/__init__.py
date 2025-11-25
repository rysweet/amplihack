"""Authentication module for JWT-based API authentication."""

from .jwt_handler import jwt_handler
from .middleware import (
    get_current_active_user,
    get_current_admin_user,
    get_current_user,
    get_optional_current_user,
    jwt_bearer,
    optional_jwt_bearer,
)
from .models import (
    TokenData,
    TokenResponse,
    User,
    UserCreate,
    UserLogin,
    UserResponse,
)
from .routes import auth_router
from .user_store import user_store

__all__ = [
    "jwt_handler",
    "user_store",
    "auth_router",
    "get_current_user",
    "get_current_active_user",
    "get_current_admin_user",
    "get_optional_current_user",
    "jwt_bearer",
    "optional_jwt_bearer",
    "User",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "TokenData",
]
