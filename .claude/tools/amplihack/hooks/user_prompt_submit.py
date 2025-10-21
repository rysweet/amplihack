#!/usr/bin/env python3
"""
UserPromptSubmit hook - Inject user preferences on every message.
Ensures preferences persist across all conversation turns in REPL mode.
"""

import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

# Import path utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from amplihack.utils.paths import FrameworkPathResolver
except ImportError:
    FrameworkPathResolver = None


class UserPromptSubmitHook(HookProcessor):
    """Hook processor for user prompt submit events."""

    def __init__(self):
        super().__init__("user_prompt_submit")
        # Cache preferences to avoid repeated file reads
        self._preferences_cache: Optional[Dict[str, str]] = None
        self._cache_timestamp: Optional[float] = None

    def find_user_preferences(self) -> Optional[Path]:
        """Find USER_PREFERENCES.md file using FrameworkPathResolver or fallback."""
        # Try FrameworkPathResolver first (handles UVX and installed packages)
        if FrameworkPathResolver:
            pref_file = FrameworkPathResolver.resolve_preferences_file()
            if pref_file and pref_file.exists():
                return pref_file

        # Fallback: Check in project root
        pref_file = self.project_root / ".claude" / "context" / "USER_PREFERENCES.md"
        if pref_file.exists():
            return pref_file

        # Try src/amplihack location
        pref_file = (
            self.project_root / "src" / "amplihack" / ".claude" / "context" / "USER_PREFERENCES.md"
        )
        if pref_file.exists():
            return pref_file

        return None

    def extract_preferences(self, content: str) -> Dict[str, str]:
        """Extract preferences from USER_PREFERENCES.md content.

        Args:
            content: The raw content of USER_PREFERENCES.md

        Returns:
            Dictionary mapping preference names to values
        """
        preferences = {}

        # Key preferences to extract (aligned with session_start.py)
        key_prefs = [
            "Communication Style",
            "Verbosity",
            "Collaboration Style",
            "Update Frequency",
            "Priority Type",
            "Preferred Languages",
            "Coding Standards",
            "Workflow Preferences",
        ]

        # Extract each preference using regex pattern
        for pref_name in key_prefs:
            # Pattern: ### Preference Name\n\nvalue
            pattern = rf"### {re.escape(pref_name)}\s*\n\s*([^\n]+)"
            match = re.search(pattern, content)
            if match:
                value = match.group(1).strip()
                # Skip empty or placeholder values
                if value and value not in ["", "(not set)", "not set"]:
                    preferences[pref_name] = value

        # Extract learned patterns (brief mention only)
        if "## Learned Patterns" in content:
            learned_section = content.split("## Learned Patterns", 1)[1]
            # Check if there's content beyond just the comment
            if learned_section.strip() and "###" in learned_section:
                preferences["Has Learned Patterns"] = "Yes (see USER_PREFERENCES.md)"

        return preferences

    def build_preference_context(self, preferences: Dict[str, str]) -> str:
        """Build concise preference enforcement context for injection.

        This must be brief but clear enough to enforce preferences.

        Args:
            preferences: Dictionary of preference name -> value

        Returns:
            Formatted context string for injection
        """
        if not preferences:
            return ""

        lines = ["🎯 ACTIVE USER PREFERENCES (MANDATORY):"]

        # Priority order for displaying preferences (most impactful first)
        priority_order = [
            "Communication Style",
            "Verbosity",
            "Collaboration Style",
            "Update Frequency",
            "Priority Type",
            "Preferred Languages",
            "Coding Standards",
            "Workflow Preferences",
            "Has Learned Patterns",
        ]

        # Add preferences in priority order
        for pref_name in priority_order:
            if pref_name in preferences:
                value = preferences[pref_name]

                # Add specific enforcement instruction based on preference type
                if pref_name == "Communication Style":
                    lines.append(f"• {pref_name}: {value} - Use this style in your response")
                elif pref_name == "Verbosity":
                    lines.append(f"• {pref_name}: {value} - Match this detail level")
                elif pref_name == "Collaboration Style":
                    lines.append(f"• {pref_name}: {value} - Follow this approach")
                elif pref_name == "Update Frequency":
                    lines.append(f"• {pref_name}: {value} - Provide updates at this frequency")
                elif pref_name == "Priority Type":
                    lines.append(f"• {pref_name}: {value} - Consider this priority in decisions")
                elif pref_name == "Has Learned Patterns":
                    lines.append(f"• {value}")
                else:
                    lines.append(f"• {pref_name}: {value}")

        lines.append("")
        lines.append("These preferences MUST be applied to this response.")

        return "\n".join(lines)

    def get_cached_preferences(self, pref_file: Path) -> Dict[str, str]:
        """Get preferences with simple caching to improve performance.

        Args:
            pref_file: Path to preferences file

        Returns:
            Dictionary of preferences
        """
        try:
            # Check if cache is valid (file hasn't changed)
            current_mtime = pref_file.stat().st_mtime
            if (
                self._preferences_cache is not None
                and self._cache_timestamp is not None
                and current_mtime == self._cache_timestamp
            ):
                return self._preferences_cache

            # Read and parse preferences
            content = pref_file.read_text(encoding="utf-8")
            preferences = self.extract_preferences(content)

            # Update cache
            self._preferences_cache = preferences
            self._cache_timestamp = current_mtime

            return preferences

        except Exception as e:
            self.log(f"Error reading preferences: {e}", "WARNING")
            return {}

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process user prompt submit event.

        Args:
            input_data: Input from Claude Code

        Returns:
            Additional context to inject
        """
        # Find preferences file
        pref_file = self.find_user_preferences()
        if not pref_file:
            # No preferences file - return empty context
            self.log("No USER_PREFERENCES.md found - skipping injection")
            return {
                "additionalContext": "",
            }

        # Get preferences (with caching for performance)
        preferences = self.get_cached_preferences(pref_file)

        if not preferences:
            self.log("No active preferences found")
            return {
                "additionalContext": "",
            }

        # Build context
        context = self.build_preference_context(preferences)

        # Log activity (for debugging)
        self.log(f"Injected {len(preferences)} preferences on user prompt")
        self.save_metric("preferences_injected", len(preferences))
        self.save_metric("context_length", len(context))

        # Return output in correct format
        return {
            "additionalContext": context,
        }


def main():
    """Entry point for the user_prompt_submit hook."""
    hook = UserPromptSubmitHook()
    hook.run()


if __name__ == "__main__":
    main()
