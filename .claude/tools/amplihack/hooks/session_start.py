#!/usr/bin/env python3
"""
Claude Code hook for session start.
Uses unified HookProcessor for common functionality.
"""

# Import the base processor
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class SessionStartHook(HookProcessor):
    """Hook processor for session start events."""

    def __init__(self):
        super().__init__("session_start")

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process session start event.

        Args:
            input_data: Input from Claude Code

        Returns:
            Additional context to add to the session
        """
        # Extract prompt
        prompt = input_data.get("prompt", "")
        self.log(f"Prompt length: {len(prompt)}")

        # Save metric
        self.save_metric("prompt_length", len(prompt))

        # Build context if needed
        context_parts = []

        # Add project context
        context_parts.append("## Project Context")
        context_parts.append("This is the Microsoft Hackathon 2025 Agentic Coding project.")
        context_parts.append("Focus on building AI-powered development tools.")

        # Check for recent discoveries
        discoveries_file = self.project_root / "DISCOVERIES.md"
        if discoveries_file.exists():
            context_parts.append("\n## Recent Learnings")
            context_parts.append("Check DISCOVERIES.md for recent insights.")

        # Simple preference notification
        preferences_file = self.project_root / ".claude" / "context" / "USER_PREFERENCES.md"
        if preferences_file.exists():
            try:
                with open(preferences_file, "r") as f:
                    prefs_content = f.read()

                # Simple extraction of communication style
                if "### Communication Style" in prefs_content:
                    import re

                    style_match = re.search(
                        r"### Communication Style\s*\n\s*([^\n]+)", prefs_content
                    )
                    if style_match and "pirate" in style_match.group(1).lower():
                        context_parts.append("\n## Active User Preferences")
                        context_parts.append(
                            "Communication Style: Pirate - Agents should use pirate language"
                        )
                        self.log("Pirate communication style detected in preferences")
                    elif style_match:
                        context_parts.append("\n## Active User Preferences")
                        context_parts.append(f"Communication Style: {style_match.group(1).strip()}")
                        self.log(f"Communication style: {style_match.group(1).strip()}")
            except Exception as e:
                self.log(f"Could not read preferences: {e}")
                # Fail silently - don't break session start

        # Build response
        output = {}
        if context_parts:
            context = "\n".join(context_parts)
            output = {
                "additionalContext": context,
                "metadata": {
                    "source": "project_context",
                    "timestamp": datetime.now().isoformat(),
                },
            }
            self.log(f"Returned context with {len(context_parts)} parts")

        return output


def main():
    """Entry point for the session start hook."""
    hook = SessionStartHook()
    hook.run()


if __name__ == "__main__":
    main()
