"""Prompt template loader for goal-seeking agents.

Loads prompt templates from markdown files in this directory.
Two substitution styles are supported:
- {variable}: Python format string syntax (used by format_prompt)
- {{variable}}: Double-brace syntax (used by render_prompt), safe for
  JSON examples that contain literal single braces

Philosophy:
- Prompts are content, not code - live in markdown files
- Easy to review, edit, and version independently
- Templates loaded once, formatted at runtime
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent

# Regex to match {{variable_name}} placeholders (not {single_brace})
_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


@lru_cache(maxsize=64)
def load_prompt(name: str) -> str:
    """Load a prompt template from a markdown file.

    Args:
        name: Name of the prompt file (without .md extension)

    Returns:
        Raw template string (placeholders not yet substituted)

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
    """Load and format a prompt template using {variable} syntax.

    Args:
        name: Name of the prompt file (without .md extension)
        **kwargs: Variables to substitute in the template

    Returns:
        Formatted prompt string
    """
    template = load_prompt(name)
    return template.format(**kwargs)


def render_prompt(name: str, **kwargs: str) -> str:
    """Load and render a prompt template using {{variable}} syntax.

    Uses double-brace placeholders so that single braces (common in
    JSON examples inside prompts) are left untouched.

    Args:
        name: Name of the prompt file (without .md extension)
        **kwargs: Variables to substitute for {{variable}} placeholders

    Returns:
        Rendered prompt string with placeholders replaced
    """
    template = load_prompt(name)

    def _replace(match: re.Match) -> str:
        key = match.group(1)
        return kwargs.get(key, match.group(0))

    return _PLACEHOLDER_RE.sub(_replace, template)


__all__ = ["load_prompt", "format_prompt", "render_prompt"]
