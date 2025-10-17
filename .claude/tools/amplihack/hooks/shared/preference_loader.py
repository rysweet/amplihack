"""
Shared preference loading utilities for hooks.

This module provides functions to load and format user preferences
from USER_PREFERENCES.md for injection into Claude Code's system prompts.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def get_preferences_file() -> Optional[Path]:
    """Get path to USER_PREFERENCES.md file."""
    # Try FrameworkPathResolver first (if available)
    try:
        from ..shared.framework_path_resolver import FrameworkPathResolver

        return FrameworkPathResolver.resolve_preferences_file()
    except (ImportError, AttributeError):
        # Fallback to relative path from this file
        project_root = Path(__file__).parent.parent.parent.parent.parent
        prefs_file = project_root / ".claude" / "context" / "USER_PREFERENCES.md"
        return prefs_file if prefs_file.exists() else None


def load_preferences() -> Tuple[Optional[str], Dict[str, str]]:
    """
    Load user preferences from USER_PREFERENCES.md.

    Returns:
        Tuple of (full_content, parsed_preferences_dict)
    """
    prefs_file = get_preferences_file()
    if not prefs_file or not prefs_file.exists():
        return None, {}

    try:
        with open(prefs_file, encoding="utf-8") as f:
            content = f.read()

        # Parse key preferences
        preferences = {}
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

        for pref_name in key_prefs:
            pattern = f"### {pref_name}\\s*\\n\\s*([^\\n]+)"
            match = re.search(pattern, content)
            if match:
                value = match.group(1).strip()
                if value and value != "(not set)":
                    preferences[pref_name] = value

        # Extract learned patterns
        learned_pattern = r"## Learned Patterns\s*\n(.*?)(?=\n##|\n---|\Z)"
        learned_match = re.search(learned_pattern, content, re.DOTALL)
        if learned_match:
            learned_content = learned_match.group(1).strip()
            if learned_content and "<!--" not in learned_content:
                preferences["Learned Patterns"] = learned_content

        return content, preferences

    except Exception as e:
        print(f"Warning: Failed to load preferences: {e}")
        return None, {}


def format_preferences_for_injection(preferences: Dict[str, str]) -> str:
    """
    Format preferences for injection into CLAUDE.md or system prompts.

    Args:
        preferences: Dictionary of preference name -> value

    Returns:
        Formatted markdown string with MANDATORY enforcement markers
    """
    if not preferences:
        return ""

    lines = [
        "## MANDATORY User Preferences (MUST BE FOLLOWED)",
        "",
        "**CRITICAL**: These preferences are MANDATORY and take priority over default behaviors.",
        "They CANNOT be optimized away or ignored under any circumstances.",
        "",
    ]

    # Add each preference
    for pref_name, value in preferences.items():
        if pref_name == "Learned Patterns":
            lines.append("### Learned Patterns")
            lines.append(value)
        else:
            lines.append(f"### {pref_name}")
            lines.append(f"{value}")
        lines.append("")

    return "\n".join(lines)


def get_enforcement_rules(preferences: Dict[str, str]) -> List[str]:
    """
    Generate specific enforcement rules from preferences.

    Args:
        preferences: Dictionary of preference name -> value

    Returns:
        List of enforcement rule strings
    """
    rules = []

    for pref_name, value in preferences.items():
        if pref_name == "Communication Style":
            rules.append(f"MUST use {value} communication style in ALL responses")
        elif pref_name == "Verbosity":
            rules.append(f"MUST maintain {value} verbosity level")
        elif pref_name == "Collaboration Style":
            rules.append(f"MUST follow {value} collaboration approach")
        elif pref_name == "Update Frequency":
            rules.append(f"MUST provide {value} progress updates")
        elif pref_name == "Priority Type":
            rules.append(f"MUST prioritize {value} in decision-making")
        elif pref_name == "Learned Patterns":
            rules.append("MUST follow all learned behavioral patterns")

    return rules


def create_preference_reminder() -> str:
    """
    Create a concise preference reminder for periodic injection.

    Returns:
        Short reminder text for hooks
    """
    _, preferences = load_preferences()
    if not preferences:
        return ""

    rules = get_enforcement_rules(preferences)
    if not rules:
        return ""

    reminder = ["**USER PREFERENCE REMINDER (MANDATORY)**:", ""]

    for rule in rules:
        reminder.append(f"- {rule}")

    return "\n".join(reminder)
