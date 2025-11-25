"""JWT token generation and validation utilities."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from dotenv import load_dotenv

load_dotenv()


class JWTHandler:
    """Handle JWT token generation and validation."""

    def __init__(self):
        """Initialize JWT handler with secret key."""
        # Get secret from environment or generate a secure default
        self.secret_key = os.getenv("JWT_SECRET_KEY", self._generate_secret_key())
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


# Create a singleton instance
jwt_handler = JWTHandler()
