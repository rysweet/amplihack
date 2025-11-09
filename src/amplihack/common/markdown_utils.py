"""Common markdown generation utilities."""

from pathlib import Path
from typing import Any, List, Optional


def write_markdown_file(file_path: Path, content: str, encoding: str = "utf-8") -> Path:
    """Write markdown content to file.

    Args:
        file_path: Path to write to
        content: Markdown content
        encoding: File encoding (default: utf-8)

    Returns:
        Path to written file
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding=encoding)
    return file_path


def create_markdown_header(title: str, level: int = 1) -> str:
    """Create markdown header.

    Args:
        title: Header text
        level: Header level (1-6)

    Returns:
        Markdown header string
    """
    return f"{'#' * level} {title}\n"


def create_markdown_table(headers: List[str], rows: List[List[Any]]) -> str:
    """Create markdown table from headers and rows.

    Args:
        headers: Column headers
        rows: List of rows (each row is list of values)

    Returns:
        Markdown table string
    """
    table = "| " + " | ".join(str(h) for h in headers) + " |\n"
    table += "|" + "|".join("---" for _ in headers) + "|\n"

    for row in rows:
        table += "| " + " | ".join(str(v)[:100] for v in row) + " |\n"

    return table


def truncate_text(text: str, max_length: int) -> str:
    """Truncate text with ellipsis if needed.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text
    """
    if len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text


def create_code_block(code: str, language: str = "python") -> str:
    """Create markdown code block.

    Args:
        code: Code content
        language: Language for syntax highlighting

    Returns:
        Markdown code block
    """
    return f"```{language}\n{code}\n```\n"


class MarkdownBuilder:
    """Builder for constructing markdown documents."""

    def __init__(self):
        """Initialize markdown builder."""
        self.content = ""

    def add_header(self, title: str, level: int = 1) -> "MarkdownBuilder":
        """Add header to document.

        Args:
            title: Header text
            level: Header level

        Returns:
            Self for chaining
        """
        self.content += create_markdown_header(title, level)
        self.content += "\n"
        return self

    def add_paragraph(self, text: str) -> "MarkdownBuilder":
        """Add paragraph to document.

        Args:
            text: Paragraph text

        Returns:
            Self for chaining
        """
        self.content += text + "\n\n"
        return self

    def add_list(self, items: List[str], ordered: bool = False) -> "MarkdownBuilder":
        """Add list to document.

        Args:
            items: List items
            ordered: True for ordered list, False for unordered

        Returns:
            Self for chaining
        """
        for i, item in enumerate(items):
            if ordered:
                self.content += f"{i + 1}. {item}\n"
            else:
                self.content += f"- {item}\n"

        self.content += "\n"
        return self

    def add_table(self, headers: List[str], rows: List[List[Any]]) -> "MarkdownBuilder":
        """Add table to document.

        Args:
            headers: Column headers
            rows: Table rows

        Returns:
            Self for chaining
        """
        self.content += create_markdown_table(headers, rows)
        self.content += "\n"
        return self

    def add_code_block(self, code: str, language: str = "python") -> "MarkdownBuilder":
        """Add code block to document.

        Args:
            code: Code content
            language: Language for syntax highlighting

        Returns:
            Self for chaining
        """
        self.content += create_code_block(code, language)
        self.content += "\n"
        return self

    def add_raw(self, text: str) -> "MarkdownBuilder":
        """Add raw text to document.

        Args:
            text: Raw text to add

        Returns:
            Self for chaining
        """
        self.content += text + "\n"
        return self

    def add_horizontal_rule(self) -> "MarkdownBuilder":
        """Add horizontal rule.

        Returns:
            Self for chaining
        """
        self.content += "---\n\n"
        return self

    def build(self) -> str:
        """Get final markdown content.

        Returns:
            Complete markdown document
        """
        return self.content.strip() + "\n"

    def save(self, file_path: Path) -> Path:
        """Save markdown to file.

        Args:
            file_path: Path to write to

        Returns:
            Path to written file
        """
        return write_markdown_file(file_path, self.build())
