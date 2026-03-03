"""Fleet prompt templates — loaded from .prompt files at runtime.

Keeps prompts separate from code so they can be edited without touching Python.
"""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory.

    Args:
        name: Filename (e.g. "copilot_system.prompt")

    Returns:
        Prompt text content.

    Raises:
        FileNotFoundError: If the prompt file doesn't exist.
        ValueError: If the name contains path traversal or is absolute.
    """
    if ".." in name or name.startswith("/"):
        raise ValueError(f"Invalid prompt name (path traversal rejected): {name!r}")
    path = (_PROMPTS_DIR / name).resolve()
    if not path.is_relative_to(_PROMPTS_DIR.resolve()):
        raise ValueError(f"Invalid prompt name (escapes prompts directory): {name!r}")
    return path.read_text(encoding="utf-8").strip()
