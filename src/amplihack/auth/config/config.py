"""
Authentication configuration module.
Centralized configuration for JWT and auth settings.
"""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class JWTConfig:
    """JWT token configuration."""
    secret_key: str
    algorithm: str = "RS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    issuer: str = "amplihack-auth"
    audience: str = "amplihack-api"
    private_key_path: Optional[str] = None
    public_key_path: Optional[str] = None

    @classmethod
    def from_env(cls) -> "JWTConfig":
        """Create configuration from environment variables."""
        # If no key paths provided, default to HS256 (symmetric) instead of RS256 (asymmetric)
        private_key_path = os.getenv("JWT_PRIVATE_KEY_PATH")
        public_key_path = os.getenv("JWT_PUBLIC_KEY_PATH")
        default_algorithm = "RS256" if (private_key_path or public_key_path) else "HS256"

        return cls(
            secret_key=os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production"),
            algorithm=os.getenv("JWT_ALGORITHM", default_algorithm),
            access_token_expire_minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
            refresh_token_expire_days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")),
            issuer=os.getenv("JWT_ISSUER", "amplihack-auth"),
            audience=os.getenv("JWT_AUDIENCE", "amplihack-api"),
            private_key_path=private_key_path,
            public_key_path=public_key_path,
        )


@dataclass
class AuthConfig:
    """Authentication configuration."""
    enable_registration: bool = True
    enable_social_login: bool = False
    require_email_verification: bool = False
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = True
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    rate_limit_requests: int = 5
    rate_limit_window_seconds: int = 60

    @classmethod
    def from_env(cls) -> "AuthConfig":
        """Create configuration from environment variables."""
        return cls(
            enable_registration=os.getenv("AUTH_ENABLE_REGISTRATION", "true").lower() == "true",
            require_email_verification=os.getenv("AUTH_REQUIRE_EMAIL_VERIFICATION", "false").lower() == "true",
            password_min_length=int(os.getenv("AUTH_PASSWORD_MIN_LENGTH", "8")),
            max_login_attempts=int(os.getenv("AUTH_MAX_LOGIN_ATTEMPTS", "5")),
            lockout_duration_minutes=int(os.getenv("AUTH_LOCKOUT_DURATION_MINUTES", "30")),
            rate_limit_requests=int(os.getenv("AUTH_RATE_LIMIT_REQUESTS", "5")),
            rate_limit_window_seconds=int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60")),
        )


@dataclass
class RedisConfig:
    """Redis configuration for blacklisting."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    decode_responses: bool = True

    @classmethod
    def from_env(cls) -> "RedisConfig":
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD"),
            ssl=os.getenv("REDIS_SSL", "false").lower() == "true",
        )
