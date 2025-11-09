"""Common parsing utilities for extracting structured data from text."""

import re
from typing import List, Optional, Tuple


def extract_numbered_items(text: str, max_items: Optional[int] = None) -> List[str]:
    """Extract numbered items from text output.

    Handles various numbering formats:
    - "1. item text" and "1) item text"
    - Removes numbering prefix
    - Filters out lines that don't match pattern

    Args:
        text: Text containing numbered items
        max_items: Maximum number of items to extract (None = no limit)

    Returns:
        List of extracted items without numbering
    """
    items = []

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or not any(c.isdigit() for c in line[:5]):
            continue

        # Try to extract numbering and remove it
        item_text = line
        for i in range(1, 11):  # Support up to 10 items
            patterns = [f"{i}. ", f"{i}) "]
            for pattern in patterns:
                if item_text.startswith(pattern):
                    item_text = item_text.split(" ", 1)[1] if " " in item_text else item_text
                    break

        if item_text and (not items or item_text not in items):
            items.append(item_text)

        if max_items and len(items) >= max_items:
            break

    return items[:max_items] if max_items else items


def extract_question_text(line: str, max_count: int = 10) -> Optional[str]:
    """Extract question text from potentially numbered line.

    Args:
        line: Line potentially containing "N. question?" format
        max_count: Expected max number prefix (for range validation)

    Returns:
        Extracted question text or None if parsing failed
    """
    line = line.strip()
    if not line:
        return None

    # Try to remove numbering
    for i in range(1, max_count + 1):
        for pattern in [f"{i}. ", f"{i}) "]:
            if line.startswith(pattern):
                return line.split(" ", 1)[1] if " " in line else None

    return line if "?" in line or line else None


def parse_markdown_table(text: str) -> List[dict]:
    """Parse markdown table into list of dictionaries.

    Args:
        text: Markdown text containing a table

    Returns:
        List of dicts with column names as keys
    """
    lines = text.strip().split("\n")
    if len(lines) < 3:
        return []

    # Extract header
    header_line = lines[0]
    separator_line = lines[1]

    # Validate it's a proper markdown table
    if not separator_line.strip().startswith("|"):
        return []

    # Parse header
    headers = [h.strip() for h in header_line.split("|")[1:-1]]

    # Parse rows
    rows = []
    for line in lines[2:]:
        if not line.strip().startswith("|"):
            break

        values = [v.strip() for v in line.split("|")[1:-1]]
        if len(values) == len(headers):
            rows.append(dict(zip(headers, values)))

    return rows


def extract_urls_from_text(text: str) -> List[str]:
    """Extract all HTTP(S) URLs from text.

    Args:
        text: Text containing URLs

    Returns:
        List of unique URLs
    """
    # Simple URL pattern for http/https
    pattern = r"https?://[^\s\n\)]+"
    urls = re.findall(pattern, text)
    return list(dict.fromkeys(urls))  # Remove duplicates while preserving order


def split_into_sections(text: str, delimiter: str = "\n\n") -> List[str]:
    """Split text into sections by delimiter, filtering empty sections.

    Args:
        text: Text to split
        delimiter: Section delimiter (default: double newline)

    Returns:
        List of non-empty sections
    """
    sections = text.split(delimiter)
    return [s.strip() for s in sections if s.strip()]
