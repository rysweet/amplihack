"""
Authentication module for amplihack.
Provides JWT-based authentication with rate limiting, blacklisting, and audit logging.
"""

from typing import Optional
import redis

from .config import JWTConfig, AuthConfig, RedisConfig
from .services import (
    TokenService,
    PasswordService,
    BlacklistService,
    RateLimiter,
    AuditLogger,
    AuthenticationService,
)
from .repository import UserRepository
from .middleware import AuthMiddleware, require_auth, require_role, require_permission
from .routes import router, set_auth_service
from .models import (
    User,
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    RevokeTokenRequest,
    LoginResponse,
    RefreshResponse,
    VerifyResponse,
    MessageResponse,
    UserResponse,
    TokenPayload,
)
from .exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    AccountLockedError,
    AccountNotActiveError,
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


def create_auth_system(
    jwt_config: Optional[JWTConfig] = None,
    auth_config: Optional[AuthConfig] = None,
    redis_config: Optional[RedisConfig] = None,
    redis_client: Optional[redis.Redis] = None
) -> tuple[AuthenticationService, TokenService, AuthMiddleware]:
    """
    Factory function to create and wire up all authentication components.

    Args:
        jwt_config: JWT configuration (defaults to environment)
        auth_config: Auth configuration (defaults to environment)
        redis_config: Redis configuration (defaults to environment)
        redis_client: Optional pre-configured Redis client (for testing)

    Returns:
        Tuple of (auth_service, token_service, auth_middleware)

    Example:
        auth_service, token_service, middleware = create_auth_system()

        app = FastAPI()
        app.add_middleware(AuthMiddleware, token_service=token_service)
        app.include_router(router)
        set_auth_service(auth_service)
    """
    # Load configurations
    jwt_config = jwt_config or JWTConfig.from_env()
    auth_config = auth_config or AuthConfig.from_env()
    redis_config = redis_config or RedisConfig.from_env()

    # Create services
    password_service = PasswordService()
    blacklist_service = BlacklistService(redis_config, redis_client)
    rate_limiter = RateLimiter(auth_config, redis_config, redis_client)
    audit_logger = AuditLogger()
    token_service = TokenService(jwt_config, blacklist_service)

    # Create repository
    user_repository = UserRepository()

    # Create authentication service
    auth_service = AuthenticationService(
        user_repository=user_repository,
        password_service=password_service,
        token_service=token_service,
        rate_limiter=rate_limiter,
        audit_logger=audit_logger,
        config=auth_config
    )

    # Create middleware
    # Note: The app parameter is provided when adding middleware to FastAPI
    # This is just a class reference
    middleware_class = AuthMiddleware

    return auth_service, token_service, middleware_class


__all__ = [
    # Factory
    "create_auth_system",
    # Configuration
    "JWTConfig",
    "AuthConfig",
    "RedisConfig",
    # Services
    "TokenService",
    "PasswordService",
    "BlacklistService",
    "RateLimiter",
    "AuditLogger",
    "AuthenticationService",
    # Repository
    "UserRepository",
    # Middleware
    "AuthMiddleware",
    "require_auth",
    "require_role",
    "require_permission",
    # Routes
    "router",
    "set_auth_service",
    # Models
    "User",
    "RegisterRequest",
    "LoginRequest",
    "RefreshTokenRequest",
    "RevokeTokenRequest",
    "LoginResponse",
    "RefreshResponse",
    "VerifyResponse",
    "MessageResponse",
    "UserResponse",
    "TokenPayload",
    # Exceptions
    "AuthenticationError",
    "InvalidCredentialsError",
    "AccountLockedError",
    "AccountNotActiveError",
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
