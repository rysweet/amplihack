"""Prompt transformation for directory change instructions."""

from pathlib import Path
from typing import Union
import re


class PromptTransformer:
    """Transform auto mode prompts to include directory change."""

    def transform_prompt(
        self,
        original_prompt: str,
        target_directory: Union[str, Path],
        used_temp: bool
    ) -> str:
        """Transform prompt to include directory change instruction."""
        if not used_temp:
            return original_prompt

        target_path = Path(target_directory).resolve()
        slash_commands, remaining_prompt = self._extract_slash_commands(original_prompt)
        dir_instruction = f"Change your working directory to {target_path}. "

        if slash_commands:
            return f"{slash_commands} {dir_instruction}{remaining_prompt}"
        return f"{dir_instruction}{remaining_prompt}"

    def _extract_slash_commands(self, prompt: str) -> tuple[str, str]:
        """Extract slash commands from the start of the prompt."""
        prompt_stripped = prompt.strip()
        slash_commands = []
        remaining = prompt_stripped

        while remaining:
            match = re.match(r'^(/[\w:-]+)(\s+|$)', remaining)
            if not match:
                break
            slash_commands.append(match.group(1))
            remaining = remaining[match.end():].strip()

        if slash_commands:
            return ' '.join(slash_commands), remaining
        return "", prompt_stripped
