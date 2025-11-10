"""Formatting utilities - Batch 330"""

from typing import Any, Dict
import json

class DataFormatter:
    """Format data in various output formats."""

    @staticmethod
    def to_json(data: Any, indent: int = 2) -> str:
        """Convert data to JSON string."""
        return json.dumps(data, indent=indent, default=str)

    @staticmethod
    def to_table(data: list[Dict], headers: list[str]) -> str:
        """Convert list of dicts to simple text table."""
        if not data:
            return ""

        # Calculate column widths
        widths = {{h: len(h) for h in headers}}
        for row in data:
            for h in headers:
                widths[h] = max(widths[h], len(str(row.get(h, ""))))

        # Build table
        lines = []
        header_line = " | ".join(h.ljust(widths[h]) for h in headers)
        lines.append(header_line)
        lines.append("-" * len(header_line))

        for row in data:
            line = " | ".join(str(row.get(h, "")).ljust(widths[h]) for h in headers)
            lines.append(line)

        return "\n".join(lines)
