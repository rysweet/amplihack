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
    """
    path = _PROMPTS_DIR / name
    return path.read_text(encoding="utf-8").strip()
