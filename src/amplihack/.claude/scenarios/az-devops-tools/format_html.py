#!/usr/bin/env python3
"""Convert markdown to Azure DevOps HTML format.

Azure DevOps work items use HTML formatting for descriptions and comments.
This tool converts common markdown elements to their HTML equivalents.

Philosophy:
- Single responsibility: markdown to HTML conversion
- Standard library only (no external markdown parsers)
- Support common markdown elements
- Utility functions for building HTML

Public API:
    markdown_to_html: Convert markdown string to HTML
    html_p: Create HTML paragraph
    html_list: Create HTML list (ul/ol)
    html_code: Create HTML code block
    html_heading: Create HTML heading
"""

import argparse
import re
import sys


def html_p(text: str) -> str:
    """Create HTML paragraph.

    Args:
        text: Paragraph text (may contain inline HTML)

    Returns:
        HTML paragraph string
    """
    return f"<p>{text}</p>"


def html_heading(text: str, level: int = 1) -> str:
    """Create HTML heading.

    Args:
        text: Heading text
        level: Heading level (1-6)

    Returns:
        HTML heading string
    """
    level = max(1, min(6, level))  # Clamp to 1-6
    return f"<h{level}>{text}</h{level}>"


def html_list(items: list[str], ordered: bool = False) -> str:
    """Create HTML list.

    Args:
        items: List items (may contain inline HTML)
        ordered: Whether to create ordered list (ol) vs unordered (ul)

    Returns:
        HTML list string
    """
    tag = "ol" if ordered else "ul"
    list_items = "".join(f"<li>{item}</li>" for item in items)
    return f"<{tag}>{list_items}</{tag}>"


def html_code(code: str, language: str | None = None) -> str:
    """Create HTML code block.

    Args:
        code: Code content
        language: Optional language identifier

    Returns:
        HTML code block string
    """
    if language:
        return f'<pre><code class="language-{language}">{code}</code></pre>'
    return f"<pre><code>{code}</code></pre>"


def html_link(text: str, url: str) -> str:
    """Create HTML link.

    Args:
        text: Link text
        url: Link URL

    Returns:
        HTML link string
    """
    return f'<a href="{url}">{text}</a>'


def process_inline_formatting(text: str) -> str:
    """Process inline markdown formatting (bold, italic, code, links).

    Args:
        text: Text with inline markdown

    Returns:
        Text with HTML inline formatting
    """
    # Bold: **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)

    # Italic: *text* or _text_ (but not inside words)
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", text)

    # Inline code: `code`
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)

    # Links: [text](url)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)

    return text


def markdown_to_html(markdown: str) -> str:
    """Convert markdown to Azure DevOps HTML.

    Supports:
    - Headings (# H1 through ###### H6)
    - Paragraphs (separated by blank lines)
    - Bold (**text** or __text__)
    - Italic (*text* or _text_)
    - Inline code (`code`)
    - Code blocks (```language or ``` or indented)
    - Unordered lists (- or * or +)
    - Ordered lists (1. 2. 3.)
    - Links ([text](url))

    Args:
        markdown: Markdown text

    Returns:
        HTML formatted text
    """
    lines = markdown.split("\n")
    html_parts = []
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Code blocks with ```
        if line.startswith("```"):
            language = line[3:].strip() or None
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # Skip closing ```
            code = "\n".join(code_lines)
            html_parts.append(html_code(code, language))
            continue

        # Indented code blocks (4 spaces or tab)
        if line.startswith("    ") or line.startswith("\t"):
            code_lines = []
            while i < len(lines) and (lines[i].startswith("    ") or lines[i].startswith("\t")):
                code_lines.append(lines[i][4:] if lines[i].startswith("    ") else lines[i][1:])
                i += 1
            code = "\n".join(code_lines)
            html_parts.append(html_code(code))
            continue

        # Headings
        if line.startswith("#"):
            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                level = len(match.group(1))
                text = process_inline_formatting(match.group(2))
                html_parts.append(html_heading(text, level))
                i += 1
                continue

        # Unordered lists
        if re.match(r"^[-*+]\s+", line):
            list_items = []
            while i < len(lines) and re.match(r"^[-*+]\s+", lines[i]):
                item_text = re.sub(r"^[-*+]\s+", "", lines[i])
                item_text = process_inline_formatting(item_text)
                list_items.append(item_text)
                i += 1
            html_parts.append(html_list(list_items, ordered=False))
            continue

        # Ordered lists
        if re.match(r"^\d+\.\s+", line):
            list_items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                item_text = re.sub(r"^\d+\.\s+", "", lines[i])
                item_text = process_inline_formatting(item_text)
                list_items.append(item_text)
                i += 1
            html_parts.append(html_list(list_items, ordered=True))
            continue

        # Regular paragraphs
        paragraph_lines = []
        while (
            i < len(lines)
            and lines[i].strip()
            and not lines[i].startswith(("#", "-", "*", "+", "```", "    ", "\t"))
            and not re.match(r"^\d+\.\s+", lines[i])
        ):
            paragraph_lines.append(lines[i].strip())
            i += 1

        if paragraph_lines:
            paragraph = " ".join(paragraph_lines)
            paragraph = process_inline_formatting(paragraph)
            html_parts.append(html_p(paragraph))

    return "\n".join(html_parts)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert markdown to Azure DevOps HTML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert file
  python -m .claude.scenarios.az-devops-tools.format_html input.md

  # Convert from stdin
  echo "# Title" | python -m .claude.scenarios.az-devops-tools.format_html

  # Convert and save to file
  python -m .claude.scenarios.az-devops-tools.format_html input.md -o output.html

Supported markdown:
  - Headings (# through ######)
  - Bold (**text** or __text__)
  - Italic (*text* or _text_)
  - Inline code (`code`)
  - Code blocks (``` or indented)
  - Unordered lists (- * +)
  - Ordered lists (1. 2. 3.)
  - Links ([text](url))
        """,
    )

    parser.add_argument(
        "input_file",
        nargs="?",
        help="Input markdown file (or read from stdin if not provided)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output HTML file (or write to stdout if not provided)",
    )

    args = parser.parse_args()

    # Read input
    try:
        if args.input_file:
            with open(args.input_file) as f:
                markdown = f.read()
        else:
            markdown = sys.stdin.read()
    except OSError as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert to HTML
    html = markdown_to_html(markdown)

    # Write output
    try:
        if args.output:
            with open(args.output, "w") as f:
                f.write(html)
            print(f"HTML written to {args.output}")
        else:
            print(html)
    except OSError as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


__all__ = [
    "markdown_to_html",
    "html_p",
    "html_heading",
    "html_list",
    "html_code",
    "html_link",
    "process_inline_formatting",
    "main",
]
