"""User preference manager for auto-ultrathink feature.

Reads and interprets the auto_ultrathink user preference from USER_PREFERENCES.md.
Manages configuration for auto-invocation behavior.
"""

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AutoUltraThinkPreference:
    """User preference for auto-ultrathink behavior."""

    mode: str  # "enabled" | "disabled" | "ask"
    confidence_threshold: float  # 0.0 to 1.0
    excluded_patterns: list[str]  # Patterns to never trigger on


# Default preference (safe fallback)
DEFAULT_PREFERENCE = AutoUltraThinkPreference(
    mode="ask",  # Safest default - user maintains control
    confidence_threshold=0.80,  # Reasonable default
    excluded_patterns=[],  # No exclusions
)


def get_auto_ultrathink_preference() -> AutoUltraThinkPreference:
    """
    Read auto_ultrathink preference from USER_PREFERENCES.md.

    Returns:
        AutoUltraThinkPreference with mode and configuration

    Raises:
        Never raises - returns safe default on errors
    """
    try:
        # Find preferences file
        prefs_file = _find_preferences_file()
        if not prefs_file:
            return DEFAULT_PREFERENCE

        # Read content
        with open(prefs_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse YAML block
        data = _parse_yaml_simple(content)

        # Validate and construct preference
        return _validate_preference(data)

    except FileNotFoundError:
        # File doesn't exist - use default
        return DEFAULT_PREFERENCE

    except PermissionError:
        # Can't read file - use default
        print("Permission denied reading USER_PREFERENCES.md", file=sys.stderr)
        return DEFAULT_PREFERENCE

    except Exception as e:
        # Any other error - use default
        print(f"Error reading auto_ultrathink preference: {e}", file=sys.stderr)
        return DEFAULT_PREFERENCE


def is_excluded(prompt: str, excluded_patterns: list[str]) -> bool:
    """
    Check if prompt matches any excluded patterns.

    Args:
        prompt: User input string
        excluded_patterns: List of regex patterns to exclude

    Returns:
        True if prompt should be excluded from auto-ultrathink
    """
    if not excluded_patterns:
        return False

    if not prompt:
        return False

    for pattern in excluded_patterns:
        try:
            if re.search(pattern, prompt, re.IGNORECASE):
                return True
        except re.error:
            # Invalid regex pattern, skip
            continue

    return False


def _find_preferences_file() -> Optional[Path]:
    """Find USER_PREFERENCES.md in project root."""
    # Check environment variable first (for testing)
    env_path = os.getenv("AMPLIHACK_PREFERENCES_PATH")
    if env_path:
        env_file = Path(env_path)
        if env_file.exists():
            return env_file
        else:
            # Environment variable set but file doesn't exist
            return None

    # Start from current working directory
    cwd = Path.cwd()

    # Look for .claude/context/USER_PREFERENCES.md
    prefs_path = cwd / ".claude" / "context" / "USER_PREFERENCES.md"

    if prefs_path.exists():
        return prefs_path

    # Fallback: search upwards (for subdirectories)
    current = cwd
    while current != current.parent:
        prefs_path = current / ".claude" / "context" / "USER_PREFERENCES.md"
        if prefs_path.exists():
            return prefs_path
        current = current.parent

    # Not found
    return None


def _parse_yaml_simple(content: str) -> dict:
    """
    Parse simple YAML without external library.

    This is a simplified parser for our specific auto_ultrathink format.
    """
    result = {
        "mode": "ask",
        "confidence_threshold": 0.80,
        "excluded_patterns": [],
    }

    # Find the auto_ultrathink section in YAML block
    # Look for ```yaml ... ``` block
    yaml_pattern = r"```yaml\s+(.*?)\s+```"
    yaml_match = re.search(yaml_pattern, content, re.DOTALL)

    if not yaml_match:
        # No YAML block found, return default
        return result

    yaml_content = yaml_match.group(1)

    # Check if this YAML contains auto_ultrathink section
    if "auto_ultrathink:" not in yaml_content:
        return result

    # Extract the auto_ultrathink section
    # This is a simplified parser that looks for specific patterns
    lines = yaml_content.split('\n')
    in_auto_ultrathink = False
    in_excluded_patterns = False

    for line in lines:
        stripped = line.strip()

        # Check if we're entering auto_ultrathink section
        if stripped.startswith('auto_ultrathink:'):
            in_auto_ultrathink = True
            continue

        # Check if we're leaving auto_ultrathink section (dedent)
        if in_auto_ultrathink and not line.startswith(' ') and stripped:
            break

        if not in_auto_ultrathink:
            continue

        # Parse mode
        mode_match = re.match(r'mode:\s*["\']?(\w+)["\']?', stripped)
        if mode_match:
            result["mode"] = mode_match.group(1)
            continue

        # Parse confidence_threshold
        threshold_match = re.match(r'confidence_threshold:\s*([\d.]+)', stripped)
        if threshold_match:
            try:
                result["confidence_threshold"] = float(threshold_match.group(1))
            except ValueError:
                pass  # Keep default
            continue

        # Parse excluded_patterns
        if stripped.startswith('excluded_patterns:'):
            in_excluded_patterns = True
            # Check if it's inline: excluded_patterns: ["pattern1", "pattern2"]
            inline_match = re.search(r'excluded_patterns:\s*\[(.*?)\]', stripped)
            if inline_match:
                patterns_str = inline_match.group(1)
                # Extract patterns from the list
                pattern_matches = re.findall(r'["\']([^"\']+)["\']', patterns_str)
                result["excluded_patterns"] = pattern_matches
                in_excluded_patterns = False
            continue

        # Parse list items for excluded_patterns
        if in_excluded_patterns:
            # Check for list items (- "pattern" or - pattern)
            list_match = re.match(r'-\s*["\']?([^"\']+)["\']?', stripped)
            if list_match:
                result["excluded_patterns"].append(list_match.group(1))
            elif not stripped or not stripped.startswith('-'):
                in_excluded_patterns = False

    return result


def _validate_preference(data: dict) -> AutoUltraThinkPreference:
    """Validate and construct preference object."""
    # Validate mode
    mode = data.get("mode", "ask")
    if mode not in ["enabled", "disabled", "ask"]:
        mode = "ask"  # Safe default

    # Validate confidence threshold
    threshold = data.get("confidence_threshold", 0.80)
    try:
        threshold = float(threshold)
        if not (0.0 <= threshold <= 1.0):
            threshold = 0.80
    except (ValueError, TypeError):
        threshold = 0.80

    # Validate excluded patterns
    excluded = data.get("excluded_patterns", [])
    if not isinstance(excluded, list):
        excluded = []

    return AutoUltraThinkPreference(
        mode=mode,
        confidence_threshold=threshold,
        excluded_patterns=excluded,
    )
