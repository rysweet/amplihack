"""
Token Sanitization Utility

Removes sensitive credentials from strings before logging to prevent credential exposure.

Philosophy:
- Single responsibility: Sanitize tokens and credentials
- Security-first: Default deny (redact anything that looks like a credential)
- Standard library only (no external dependencies)
- Self-contained and regeneratable

Public API:
    TokenSanitizer: Main sanitization class
    sanitize: Function to sanitize a string

Created to address Issue #1997: API Keys Logged in Plain Text
"""

import re
from typing import ClassVar


class TokenSanitizer:
    """
    Sanitizes sensitive tokens and credentials from strings before logging.

    Patterns detected:
    - OpenAI API keys (sk-...)
    - Bearer tokens
    - GitHub Personal Access Tokens (ghp_..., gho_..., ghs_...)
    - Azure AD tokens
    - AWS credentials
    - JWT tokens
    - API keys in JSON
    - Authorization headers
    """

    # Pattern definitions: (regex, replacement)
    # Order matters! More specific patterns first, then general patterns
    PATTERNS: ClassVar[list[tuple[str, str]]] = [
        # OpenAI API keys (6+ chars for flexibility in testing, real keys are 20+)
        (r"sk-[a-zA-Z0-9]{6,}", "sk-***"),
        (r"sk-proj-[a-zA-Z0-9_-]{6,}", "sk-proj-***"),
        # GitHub tokens (made more flexible with 20+ characters instead of exact 36)
        (r"ghp_[a-zA-Z0-9]{20,}", "ghp_***"),  # Personal access token
        (r"gho_[a-zA-Z0-9]{20,}", "gho_***"),  # OAuth token
        (r"ghs_[a-zA-Z0-9]{20,}", "ghs_***"),  # Server-to-server token
        (r"github_pat_[a-zA-Z0-9_]{22,255}", "github_pat_***"),  # Fine-grained PAT
        # Azure AD tokens (JWT format) - made more specific
        (r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+", "eyJ***.eyJ***.***"),
        # AWS credentials
        (r"AKIA[0-9A-Z]{16}", "AKIA***"),  # AWS Access Key ID
        (r"aws_secret_access_key[\'\":\s]*[\'\"]*[a-zA-Z0-9/+=]{40}", "aws_secret_access_key: ***"),
        # Authorization headers (specific pattern to avoid double sanitization)
        (r"Authorization:\s*Bearer\s+[^\s,;\'\"]+", "Authorization: Bearer ***"),
        (r'"Authorization"\s*:\s*"[^"]+"', '"Authorization": "***"'),
        # Generic Authorization header (only if not Bearer)
        (r"Authorization:\s*(?!Bearer)[^\s,;\'\"]+", "Authorization: ***"),
        # Bearer tokens (generic) - standalone, not after "Authorization:"
        (r"(?<!Authorization:\s)Bearer\s+[^\s\'\"]+", "Bearer ***"),
        # API keys in JSON
        (r'"api_key"\s*:\s*"[^"]+"', '"api_key": "***"'),
        (r'"apiKey"\s*:\s*"[^"]+"', '"apiKey": "***"'),
        (r'"api-key"\s*:\s*"[^"]+"', '"api-key": "***"'),
        (r'"access_token"\s*:\s*"[^"]+"', '"access_token": "***"'),
        (r'"accessToken"\s*:\s*"[^"]+"', '"accessToken": "***"'),
        (r'"token"\s*:\s*"[^"]+"', '"token": "***"'),
        (r'"secret"\s*:\s*"[^"]+"', '"secret": "***"'),
        (r'"password"\s*:\s*"[^"]+"', '"password": "***"'),
        # X-API-Key headers
        (r"X-API-Key:\s*[^\s,;]+", "X-API-Key: ***"),
        (r'"X-API-Key"\s*:\s*"[^"]+"', '"X-API-Key": "***"'),
    ]

    @classmethod
    def sanitize(cls, text: str | None) -> str:
        """
        Sanitize sensitive tokens from text.

        Args:
            text: String potentially containing sensitive tokens

        Returns:
            Sanitized string with tokens replaced by ***

        Examples:
            >>> TokenSanitizer.sanitize("Using key sk-1234567890abcdefghij")
            'Using key sk-***'

            >>> TokenSanitizer.sanitize("Authorization: Bearer eyJhbGc...")
            'Authorization: ***'
        """
        if text is None:
            return ""

        sanitized = str(text)

        # Apply all patterns
        for pattern, replacement in cls.PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized

    # Sensitive key names that should always be fully redacted (no pattern matching)
    FULLY_REDACT_KEYS: ClassVar[set[str]] = {
        "password",
        "secret",
        "credentials",
        "private_key",
        "privatekey",
        "private-key",
    }

    @classmethod
    def sanitize_dict(cls, data: dict | None) -> dict:
        """
        Recursively sanitize a dictionary.

        Args:
            data: Dictionary potentially containing sensitive values

        Returns:
            New dictionary with sensitive values sanitized
        """
        if data is None:
            return {}

        sanitized = {}
        for key, value in data.items():
            # Check if the key name indicates sensitive data that should be fully redacted
            key_lower = key.lower()
            should_fully_redact = key_lower in cls.FULLY_REDACT_KEYS

            if should_fully_redact and isinstance(value, str):
                # Fully redact these sensitive keys
                sanitized[key] = "***"
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized[key] = cls.sanitize_dict(value)
            elif isinstance(value, list):
                # Sanitize each item in the list
                sanitized[key] = [
                    cls.sanitize_dict(item)
                    if isinstance(item, dict)
                    else cls.sanitize(str(item))  # This correctly sanitizes
                    for item in value
                ]
            elif isinstance(value, str):
                # Sanitize string values (applies pattern matching)
                sanitized[key] = cls.sanitize(value)
            else:
                # For non-string types, leave as-is (don't convert to string unnecessarily)
                sanitized[key] = value

        return sanitized


# Convenience function for direct usage
def sanitize(text: str | None) -> str:
    """
    Convenience function to sanitize text.

    Args:
        text: String potentially containing sensitive tokens

    Returns:
        Sanitized string
    """
    return TokenSanitizer.sanitize(text)


__all__ = ["TokenSanitizer", "sanitize"]
