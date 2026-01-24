"""
Base classes for prompt templates.

This module provides the core PromptTemplate class and related utilities.
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Base class for prompt templates with separated system and input prompts."""

    name: str
    description: str
    system_prompt: str
    input_prompt: str
    variables: list[str] = None

    def __post_init__(self):
        if self.variables is None:
            self.variables = []

    def get_prompts(self) -> tuple[str, str]:
        """Get system prompt and input prompt as raw templates."""
        return self.system_prompt, self.input_prompt

    def validate_variables(self, variables: dict[str, Any]) -> bool:
        """Validate that all required variables are provided."""
        missing = [var for var in self.variables if var not in variables]
        if missing:
            logger.exception(f"Missing required variables for template {self.name}: {missing}")
            return False
        return True
