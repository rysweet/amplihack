"""
JWT token validation utilities.
Handles RSA-256 signed JWT tokens.
"""

import re
from typing import Optional
from datetime import datetime
import uuid


class TokenValidator:
    """JWT token format validator."""

    # JWT pattern: header.payload.signature
    JWT_PATTERN = re.compile(
        r'^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$'
    )

    @classmethod
    def validate_format(cls, token: str) -> tuple[bool, Optional[str]]:
        """
        Validate JWT token format.

        Args:
            token: JWT token string

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not token:
            return False, "Token is required"

        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        # Check JWT format
        if not cls.JWT_PATTERN.match(token):
            return False, "Invalid token format"

        # Check parts count
        parts = token.split('.')
        if len(parts) != 3:
            return False, "Token must have three parts"

        return True, None

    @classmethod
    def validate_uuid(cls, token_id: str) -> tuple[bool, Optional[str]]:
        """
        Validate token ID as UUID.

        Args:
            token_id: Token identifier

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            uuid.UUID(token_id)
            return True, None
        except (ValueError, AttributeError):
            return False, "Invalid token ID format"

    @classmethod
    def validate_expiry(cls, expires_at: datetime) -> tuple[bool, Optional[str]]:
        """
        Validate token expiration.

        Args:
            expires_at: Token expiration timestamp

        Returns:
            Tuple of (is_valid, error_message)
        """
        now = datetime.utcnow()

        if expires_at <= now:
            return False, "Token has expired"

        return True, None

    @classmethod
    def extract_bearer_token(cls, auth_header: str) -> Optional[str]:
        """
        Extract token from Authorization header.

        Args:
            auth_header: Authorization header value

        Returns:
            Token string or None if invalid
        """
        if not auth_header:
            return None

        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header[7:]  # Remove 'Bearer ' prefix

        # Validate format
        valid, _ = cls.validate_format(token)
        if not valid:
            return None

        return token