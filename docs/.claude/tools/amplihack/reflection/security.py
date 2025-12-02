"""Security utilities for reflection system - sanitizes sensitive content."""

import re
from functools import lru_cache
from typing import Any, Dict, List


class ContentSanitizer:
    """Sanitizes content to prevent information disclosure with performance optimizations."""

    def __init__(self):
        # Sensitive keyword patterns (case-insensitive) - optimized order
        self.sensitive_patterns = [
            # Most common patterns first for early exit
            r'\b(?:password|passwd|pwd|token|auth|bearer|key|secret|private)\s*[=:]\s*[^\s\'"]+',
            r'\b(?:credential|cred|api_key|apikey)\s*[=:]\s*[^\s\'"]+',
            # Common credential formats - combined for efficiency
            r"\b(?:[A-Za-z0-9]{20,}|[A-Fa-f0-9]{32,})\b",
            # System paths - combined patterns
            r"(?:/[^/\s]*|C:\\[^\\s]*)(?:key|secret|token|password)[^/\\s]*",
            # Environment variables
            r"\$\{?[A-Z_]*(?:KEY|SECRET|TOKEN|PASSWORD|CRED)[A-Z_]*\}?",
            # Email patterns (potential usernames)
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            # URLs with credentials
            r"https?://[^/\s]*:[^@\s]*@[^\s]+",
        ]

        # Single compiled pattern for maximum efficiency
        combined_pattern = "|".join(f"({pattern})" for pattern in self.sensitive_patterns)
        self.compiled_pattern = re.compile(combined_pattern, re.IGNORECASE)

        # Sensitive keywords as frozenset for O(1) lookup
        self.sensitive_keywords = frozenset(
            {
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
        )

    @lru_cache(maxsize=256)
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

        # Early truncation for very long content before processing
        if len(content) > max_length * 3:
            content = content[: max_length * 3]

        # Single pattern substitution pass
        sanitized = self.compiled_pattern.sub("[REDACTED]", content)

        # Optimized line filtering with early break
        if "\n" in sanitized:
            lines = sanitized.split("\n")
            safe_lines = []

            for line in lines:
                # Quick check: if line is short and no sensitive words, keep it
                if len(line) < 50 and not any(kw in line.lower() for kw in self.sensitive_keywords):
                    safe_lines.append(line)
                elif any(kw in line.lower() for kw in self.sensitive_keywords):
                    safe_lines.append("[LINE WITH SENSITIVE DATA REDACTED]")
                else:
                    safe_lines.append(line)

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

    def sanitize_messages(
        self, messages: List[Dict[str, Any]], max_messages: int = 50
    ) -> List[Dict[str, Any]]:
        """Sanitize a list of messages with batch optimization.

        Args:
            messages: List of message dictionaries
            max_messages: Maximum messages to process

        Returns:
            List of sanitized messages
        """
        if not isinstance(messages, list):
            return []

        # Early exit for empty lists
        if not messages:
            return []

        # Process in batches for better memory efficiency
        limited_messages = messages[:max_messages]

        # Use list comprehension for better performance
        return [self.sanitize_message(msg) for msg in limited_messages]

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

    @lru_cache(maxsize=128)
    def filter_pattern_suggestion(self, suggestion: str) -> str:
        """Filter and sanitize pattern suggestions for safe display.

        Args:
            suggestion: Raw pattern suggestion

        Returns:
            Safe suggestion text
        """
        # Sanitize the suggestion
        safe_suggestion = self.sanitize_content(suggestion, max_length=150)

        # Quick check for sensitive content using frozenset
        suggestion_lower = safe_suggestion.lower()
        if any(keyword in suggestion_lower for keyword in self.sensitive_keywords):
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
