"""JWT token generation and validation utilities."""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from dotenv import load_dotenv

load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)


class JWTHandler:
    """Handle JWT token generation and validation."""

    def __init__(self):
        """Initialize JWT handler with secret key."""
        # Simple in-memory blacklist (use Redis in production)
        self._blacklisted_tokens = set()

        # Get secret from environment - REQUIRED in production
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        if not self.secret_key:
            import warnings
            warnings.warn(
                "JWT_SECRET_KEY not set! Using generated key for development only. "
                "Set JWT_SECRET_KEY environment variable in production.",
                RuntimeWarning,
                stacklevel=2
            )
            self.secret_key = self._generate_secret_key()

        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    @staticmethod
    def _generate_secret_key() -> str:
        """Generate a secure secret key if none is configured."""
        import secrets

        return secrets.token_urlsafe(32)

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            data: The data to encode in the token
            expires_delta: Optional expiration time delta

        Returns:
            The encoded JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.access_token_expire_minutes
            )

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return encoded_jwt

    def create_refresh_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT refresh token.

        Args:
            data: The data to encode in the token
            expires_delta: Optional expiration time delta

        Returns:
            The encoded JWT refresh token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)

        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return encoded_jwt

    def verify_token(self, token: str, expected_type: str = "access") -> Dict[str, Any]:
        """
        Verify and decode a JWT token.

        Args:
            token: The JWT token to verify
            expected_type: The expected token type ('access' or 'refresh')

        Returns:
            The decoded token payload

        Raises:
            jwt.ExpiredSignatureError: If the token has expired
            jwt.InvalidTokenError: If the token is invalid
        """
        # Check if token is blacklisted
        if token in self._blacklisted_tokens:
            raise jwt.InvalidTokenError("Token has been revoked")

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Verify token type
            if payload.get("type") != expected_type:
                raise jwt.InvalidTokenError(f"Invalid token type. Expected {expected_type}")

            return payload

        except jwt.ExpiredSignatureError:
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {e!s}")

    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify an access token."""
        return self.verify_token(token, "access")

    def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """Verify a refresh token."""
        return self.verify_token(token, "refresh")

    def blacklist_token(self, token: str) -> None:
        """
        Add a token to the blacklist.

        Args:
            token: The JWT token to blacklist
        """
        self._blacklisted_tokens.add(token)
        # Log token blacklist (don't log full token for security)
        token_preview = f"{token[:10]}..." if len(token) > 10 else token
        logger.debug(f"Token blacklisted: {token_preview}")

    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token: The JWT token to check

        Returns:
            True if the token is blacklisted, False otherwise
        """
        return token in self._blacklisted_tokens


# Create a singleton instance
jwt_handler = JWTHandler()
