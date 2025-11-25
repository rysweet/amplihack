"""
Password validation and hashing utilities.
Enforces strong password requirements and secure hashing.
"""

import re
import bcrypt
from typing import Optional


class PasswordValidator:
    """Password strength validator."""

    MIN_LENGTH = 8
    MAX_LENGTH = 128

    # Pattern requiring uppercase, lowercase, digit, and special character
    STRENGTH_PATTERN = re.compile(
        r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]+$'
    )

    @classmethod
    def validate(cls, password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password strength.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"

        # Check length
        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters"

        if len(password) > cls.MAX_LENGTH:
            return False, f"Password must be {cls.MAX_LENGTH} characters or less"

        # Check pattern requirements
        if not cls.STRENGTH_PATTERN.match(password):
            return False, "Password must contain uppercase, lowercase, number, and special character"

        return True, None

    @classmethod
    def hash(cls, password: str) -> str:
        """
        Hash password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @classmethod
    def verify(cls, password: str, hashed: str) -> bool:
        """
        Verify password against hash.

        Args:
            password: Plain text password
            hashed: Hashed password to compare

        Returns:
            True if password matches hash
        """
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed.encode('utf-8')
        )