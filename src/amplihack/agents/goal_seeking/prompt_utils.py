from __future__ import annotations

"""Shared prompt-loading utility for LearningAgent mixins."""

import sys
from collections.abc import Coroutine
from typing import Any, Callable

from .prompts import render_prompt

# Re-export the learning-agent completion binding so that mixins share the
# same module-level callable as learning_agent.py. Tests have patched both
# ``learning_agent._llm_completion`` and ``learning_agent.completion`` over
# time, so `_get_llm_completion()` must honor either name.
_MODULE_NAME = "amplihack.agents.goal_seeking.learning_agent"


def _get_llm_completion() -> "Callable[..., Coroutine[Any, Any, str]]":
    """Return the current completion callable from the learning_agent module.

    Using a function rather than a direct import ensures that test-time
    monkeypatching of ``learning_agent.completion`` or
    ``learning_agent._llm_completion`` is visible
    to all mixin modules.
    """
    mod = sys.modules[_MODULE_NAME]
    resolver = getattr(mod, "_get_completion_binding", None)
    if resolver is not None:
        return resolver()
    return getattr(mod, "completion", mod._llm_completion)  # type: ignore[attr-defined]


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
