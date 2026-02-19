"""Prompt template loader for goal-seeking agents.

Loads prompt templates from markdown files in this directory.
Templates use Python format string syntax: {variable_name}

Philosophy:
- Prompts are content, not code - live in markdown files
- Easy to review, edit, and version independently
- Templates loaded once, formatted at runtime
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    """Load a prompt template from a markdown file.

    Args:
        name: Name of the prompt file (without .md extension)

    Returns:
        Template string with {variable} placeholders

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    path = _PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")

    text = path.read_text()

    # Strip the markdown header (lines starting with #) at the top
    lines = text.split("\n")
    content_lines = []
    past_header = False
    for line in lines:
        if not past_header and line.startswith("#"):
            continue
        if not past_header and line.strip() == "":
            continue
        past_header = True
        content_lines.append(line)

    return "\n".join(content_lines).strip()


def format_prompt(name: str, **kwargs: str) -> str:
    """Load and format a prompt template.

    Args:
        name: Name of the prompt file (without .md extension)
        **kwargs: Variables to substitute in the template

    Returns:
        Formatted prompt string
    """
    template = load_prompt(name)
    return template.format(**kwargs)


__all__ = ["load_prompt", "format_prompt"]
