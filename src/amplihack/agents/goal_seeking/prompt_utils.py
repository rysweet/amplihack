from __future__ import annotations

"""Shared prompt-loading utility for LearningAgent mixins."""

import sys
from collections.abc import Coroutine
from typing import Any, Callable

from .prompts import render_prompt

# Re-export _llm_completion so that mixins share the same module-level
# binding as learning_agent.py.  When tests patch
# ``amplihack.agents.goal_seeking.learning_agent._llm_completion``,
# the replacement propagates to the learning_agent module namespace.
# Mixin files must call ``_get_llm_completion()`` instead of using a
# cached local binding so the patched reference is always resolved.
_MODULE_NAME = "amplihack.agents.goal_seeking.learning_agent"


def _get_llm_completion() -> "Callable[..., Coroutine[Any, Any, str]]":
    """Return the current ``_llm_completion`` from the learning_agent module.

    Using a function rather than a direct import ensures that test-time
    monkeypatching of ``learning_agent._llm_completion`` is visible
    to all mixin modules.
    """
    mod = sys.modules[_MODULE_NAME]
    return mod._llm_completion  # type: ignore[attr-defined]


def _load_prompt(name: str, **kwargs: str) -> str:
    """Load a prompt template from prompts/{name}.md and substitute placeholders.

    Uses {{variable}} double-brace syntax so that literal JSON braces in
    the prompt templates are preserved.

    Args:
        name: Prompt file name without .md extension
        **kwargs: Values to substitute for {{variable}} placeholders

    Returns:
        Rendered prompt string
    """
    return render_prompt(name, **kwargs)

__all__ = ["_load_prompt", "_get_llm_completion"]
