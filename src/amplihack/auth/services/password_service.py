"""
Password Service - handles password hashing and verification using bcrypt.
Following ruthless simplicity - direct bcrypt operations with proper error handling.
"""

import bcrypt
from typing import Optional


class PasswordService:
    """Service for password hashing and verification."""

    def __init__(self, rounds: int = 12):
        """
        Initialize password service.

        Args:
            rounds: Number of bcrypt rounds (default 12 for good security/performance balance)
        """
        self.rounds = rounds

    def hash_password(self, password: Optional[str]) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password to hash

        Returns:
            Bcrypt hashed password string

        Raises:
            ValueError: If password is None or empty
        """
        if password is None:
            raise ValueError("Password cannot be None")
        if not password or len(password) == 0:
            raise ValueError("Password cannot be empty")

        # Convert password to bytes and hash
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password_bytes, salt)

        return hashed.decode("utf-8")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password to verify
            hashed_password: Bcrypt hashed password

        Returns:
            True if password matches hash, False otherwise
        """
        if not password or not hashed_password:
            return False

        try:
            password_bytes = password.encode("utf-8")
            hashed_bytes = hashed_password.encode("utf-8")
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        except Exception:
            # Any error in verification means invalid password
            return False
