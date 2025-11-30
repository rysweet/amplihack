"""Authentication service."""

import hashlib
from typing import Optional

from .database_service import DatabaseService


class AuthService:
    """Service for authentication and authorization.

    Handles user authentication, token generation, and validation.
    """

    def __init__(self, db_service: DatabaseService):
        """Initialize auth service.

        Args:
            db_service: Database service for user lookup
        """
        self.db = db_service

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate user credentials.

        Args:
            username: Username
            password: Password (plaintext)

        Returns:
            Auth token if successful, None otherwise
        """
        user = self.db.query("users", {"username": username})
        if not user:
            return None

        password_hash = self._hash_password(password)
        if user.get("password_hash") == password_hash:
            return self._generate_token(user["id"])

        return None

    def validate_token(self, token: str) -> bool:
        """Validate authentication token.

        Args:
            token: Token to validate

        Returns:
            True if valid
        """
        # Simplified token validation
        return len(token) == 64

    def revoke_token(self, token: str) -> bool:
        """Revoke an authentication token.

        Args:
            token: Token to revoke

        Returns:
            True if successful
        """
        return self.db.insert("revoked_tokens", {"token": token})

    def _hash_password(self, password: str) -> str:
        """Hash a password.

        Args:
            password: Plaintext password

        Returns:
            Password hash
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def _generate_token(self, user_id: str) -> str:
        """Generate authentication token.

        Args:
            user_id: User identifier

        Returns:
            Authentication token
        """
        data = f"{user_id}:{hashlib.sha256(user_id.encode()).hexdigest()}"
        return hashlib.sha256(data.encode()).hexdigest()
