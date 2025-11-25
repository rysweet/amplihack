"""
Email validation utilities.
RFC 5322 compliant email validation.
"""

import re
from typing import Optional


class EmailValidator:
    """Email address validator."""

    # RFC 5322 simplified regex pattern
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    MAX_LENGTH = 255

    @classmethod
    def validate(cls, email: str) -> tuple[bool, Optional[str]]:
        """
        Validate email address format.

        Args:
            email: Email address to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email is required"

        # Check length
        if len(email) > cls.MAX_LENGTH:
            return False, f"Email must be {cls.MAX_LENGTH} characters or less"

        # Check format
        if not cls.EMAIL_PATTERN.match(email):
            return False, "Invalid email format"

        # Check for consecutive dots
        if '..' in email:
            return False, "Email cannot contain consecutive dots"

        # Check local part length (before @)
        local_part = email.split('@')[0]
        if len(local_part) > 64:
            return False, "Email local part too long"

        return True, None

    @classmethod
    def normalize(cls, email: str) -> str:
        """
        Normalize email for storage/comparison.

        Args:
            email: Email address to normalize

        Returns:
            Normalized email (lowercase)
        """
        return email.strip().lower()