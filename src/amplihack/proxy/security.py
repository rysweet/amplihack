"""Security utilities for token sanitization and data protection.

This module provides TokenSanitizer class for detecting and redacting
sensitive tokens (API keys, auth tokens) from logs, errors, and data structures.

Philosophy:
- Single responsibility: Token detection and sanitization
- Zero-BS: Fully functional with no stubs
- Performance-first: < 1ms for typical operations

Public API:
    TokenSanitizer: Main class for token sanitization
"""

import re
from typing import Any


class TokenSanitizer:
    """Sanitize sensitive tokens from strings and data structures.

    Detects and redacts:
    - GitHub tokens (gho_, ghp_, ghs_, ghu_, ghr_)
    - OpenAI API keys (sk-, sk-proj-)
    - Anthropic API keys (sk-ant-)
    - Generic Bearer tokens
    - JWT tokens
    - Azure tokens and connection strings
    """

    def __init__(self):
        """Initialize TokenSanitizer with compiled regex patterns."""
        # Token patterns with their replacement markers
        # Note: Patterns match tokens even when embedded in text.
        # Upper limits (100 chars) prevent matching entire files but allow real tokens.
        self._patterns = [
            # GitHub tokens (gho_, ghp_, ghs_, ghu_, ghr_) - 6-100 chars after prefix
            (re.compile(r"gh[opsuhr]_[A-Za-z0-9]{6,100}"), "[REDACTED-GITHUB-TOKEN]"),
            # OpenAI API keys (sk-, sk-proj-) - 6-100 chars after prefix
            (re.compile(r"sk-(?:proj-)?[A-Za-z0-9]{6,100}"), "[REDACTED-OPENAI-KEY]"),
            # Anthropic API keys (sk-ant-) - 6-100 chars after prefix
            (re.compile(r"sk-ant-[A-Za-z0-9]{6,100}"), "[REDACTED-ANTHROPIC-KEY]"),
            # Generic Bearer tokens (Bearer + base64-like string, 6-500 chars)
            (
                re.compile(r"Bearer\s+[A-Za-z0-9_\-]{6,500}(?:\.[A-Za-z0-9_\-]+)*"),
                "[REDACTED-BEARER-TOKEN]",
            ),
            # JWT tokens (header.payload.signature format)
            (
                re.compile(r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
                "[REDACTED-JWT-TOKEN]",
            ),
            # Azure subscription keys
            (re.compile(r"azure-key-[A-Za-z0-9]{6,100}"), "[REDACTED-AZURE-KEY]"),
            # Azure connection strings (matches to end of string or whitespace)
            (
                re.compile(
                    r"DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[^;]+;[^\s]+"
                ),
                "[REDACTED-AZURE-CONNECTION]",
            ),
        ]

    def contains_token(self, text: str) -> bool:
        """Check if text contains any sensitive tokens.

        Args:
            text: Text to check for tokens

        Returns:
            True if tokens are detected, False otherwise
        """
        if not text or not isinstance(text, str):
            return False

        for pattern, _ in self._patterns:
            if pattern.search(text):
                return True
        return False

    def sanitize(self, data: Any) -> Any:
        """Sanitize tokens from data structure.

        Recursively processes strings, dicts, and lists to redact tokens.
        Preserves non-sensitive data and structure.

        Args:
            data: Data to sanitize (str, dict, list, or other types)

        Returns:
            Sanitized copy of data with tokens redacted
        """
        if data is None:
            return None

        if isinstance(data, str):
            return self._sanitize_string(data)

        if isinstance(data, dict):
            return {key: self.sanitize(value) for key, value in data.items()}

        if isinstance(data, list):
            return [self.sanitize(item) for item in data]

        # For other types (int, bool, etc.), return as-is
        return data

    def _sanitize_string(self, text: str) -> str:
        """Sanitize tokens from a single string.

        Args:
            text: String to sanitize

        Returns:
            String with tokens replaced by redaction markers
        """
        if not text:
            return text

        result = text
        for pattern, replacement in self._patterns:
            result = pattern.sub(replacement, result)

        return result


__all__ = ["TokenSanitizer"]
