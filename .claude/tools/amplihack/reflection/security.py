"""Security utilities for reflection system - sanitizes sensitive content."""

import re
from typing import Any, Dict, List


class ContentSanitizer:
    """Sanitizes content to prevent information disclosure."""

    def __init__(self):
        # Sensitive keyword patterns (case-insensitive)
        self.sensitive_patterns = [
            # Credentials and authentication
            r'\b(?:password|passwd|pwd)\s*[=:]\s*[^\s\'"]+',
            r'\b(?:token|auth|bearer)\s*[=:]\s*[^\s\'"]+',
            r'\b(?:key|secret|private)\s*[=:]\s*[^\s\'"]+',
            r'\b(?:credential|cred)\s*[=:]\s*[^\s\'"]+',
            r'\b(?:api_key|apikey)\s*[=:]\s*[^\s\'"]+',
            # Common credential formats
            r"\b[A-Za-z0-9]{20,}\b",  # Long alphanumeric strings (likely tokens)
            r"\b[A-Fa-f0-9]{32,}\b",  # Hex strings (likely hashes/tokens)
            # System paths
            r"/[^/\s]*(?:key|secret|token|password)[^/\s]*",
            r"C:\\[^\\s]*(?:key|secret|token|password)[^\\s]*",
            # Environment variables
            r"\$\{?[A-Z_]*(?:KEY|SECRET|TOKEN|PASSWORD|CRED)[A-Z_]*\}?",
            # Email patterns (potential usernames)
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            # URLs with credentials
            r"https?://[^/\s]*:[^@\s]*@[^\s]+",
        ]

        # Compile patterns for efficiency
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.sensitive_patterns
        ]

        # Sensitive keywords for basic filtering
        self.sensitive_keywords = {
            "password",
            "passwd",
            "pwd",
            "token",
            "auth",
            "bearer",
            "key",
            "secret",
            "private",
            "credential",
            "cred",
            "api_key",
            "apikey",
            "oauth",
        }

    def sanitize_content(self, content: str, max_length: int = 200) -> str:
        """Sanitize content by removing sensitive information and truncating.

        Args:
            content: Raw content to sanitize
            max_length: Maximum length of output

        Returns:
            Sanitized and truncated content
        """
        if not isinstance(content, str):
            content = str(content)

        # Remove sensitive patterns
        sanitized = content
        for pattern in self.compiled_patterns:
            sanitized = pattern.sub("[REDACTED]", sanitized)

        # Filter out lines containing sensitive keywords
        lines = sanitized.split("\n")
        safe_lines = []

        for line in lines:
            line_lower = line.lower()
            if not any(keyword in line_lower for keyword in self.sensitive_keywords):
                safe_lines.append(line)
            else:
                safe_lines.append("[LINE WITH SENSITIVE DATA REDACTED]")

        sanitized = "\n".join(safe_lines)

        # Truncate to max length
        if len(sanitized) > max_length:
            sanitized = sanitized[: max_length - 12] + "...[TRUNCATED]"

        return sanitized

    def sanitize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize a single message object.

        Args:
            message: Message dictionary to sanitize

        Returns:
            Sanitized message dictionary
        """
        if not isinstance(message, dict):
            return {"content": self.sanitize_content(str(message))}

        sanitized = {}
        for key, value in message.items():
            if key == "content":
                sanitized[key] = self.sanitize_content(str(value), max_length=500)
            elif isinstance(value, str):
                sanitized[key] = self.sanitize_content(value, max_length=100)
            elif isinstance(value, (list, dict)):
                # Don't process complex nested structures - too risky
                sanitized[key] = "[COMPLEX_DATA_REDACTED]"
            else:
                sanitized[key] = str(value)[:50]  # Limit length

        return sanitized

    def sanitize_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sanitize a list of messages.

        Args:
            messages: List of message dictionaries

        Returns:
            List of sanitized messages
        """
        if not isinstance(messages, list):
            return []

        sanitized_messages = []
        for msg in messages[:50]:  # Limit to first 50 messages
            sanitized_messages.append(self.sanitize_message(msg))

        return sanitized_messages

    def create_safe_preview(self, content: str, context: str = "") -> str:
        """Create a safe preview for pattern detection.

        Args:
            content: Raw content
            context: Context description

        Returns:
            Safe preview string
        """
        sanitized = self.sanitize_content(content, max_length=100)

        # Further limit for previews
        if len(sanitized) > 50:
            sanitized = sanitized[:47] + "..."

        if context:
            return f"{context}: {sanitized}"
        return sanitized

    def filter_pattern_suggestion(self, suggestion: str) -> str:
        """Filter and sanitize pattern suggestions for safe display.

        Args:
            suggestion: Raw pattern suggestion

        Returns:
            Safe suggestion text
        """
        # Sanitize the suggestion
        safe_suggestion = self.sanitize_content(suggestion, max_length=150)

        # Ensure suggestions are generic and don't expose specifics
        if any(keyword in safe_suggestion.lower() for keyword in self.sensitive_keywords):
            return "Improve security and data handling practices"

        return safe_suggestion


# Global sanitizer instance
_sanitizer = ContentSanitizer()


# Convenience functions
def sanitize_content(content: str, max_length: int = 200) -> str:
    """Sanitize content using global sanitizer."""
    return _sanitizer.sanitize_content(content, max_length)


def sanitize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitize messages using global sanitizer."""
    return _sanitizer.sanitize_messages(messages)


def create_safe_preview(content: str, context: str = "") -> str:
    """Create safe preview using global sanitizer."""
    return _sanitizer.create_safe_preview(content, context)


def filter_pattern_suggestion(suggestion: str) -> str:
    """Filter pattern suggestion using global sanitizer."""
    return _sanitizer.filter_pattern_suggestion(suggestion)
