"""Parsing utilities - Batch 357"""

import re
from typing import Dict, List, Optional

class TextParser:
    """Parse and extract information from text."""

    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract URLs from text."""
        url_pattern = r'https?://[^\s<>"{{}}|\\^`\[\]]+'
        return re.findall(url_pattern, text)

    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """Extract email addresses from text."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{{2,}}\b'
        return re.findall(email_pattern, text)

    @staticmethod
    def extract_key_value_pairs(text: str, separator: str = "=") -> Dict[str, str]:
        """Extract key=value pairs from text."""
        pairs = {{}}
        pattern = rf'([\w_]+){re.escape(separator)}([^\s,;]+)'
        for match in re.finditer(pattern, text):
            pairs[match.group(1)] = match.group(2)
        return pairs

    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        pattern = r'[.!?]+\s+'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]
