"""Hook synchronization validator for settings.json and UVX template.

Ensures hooks in .claude/settings.json match src/amplihack/utils/uvx_settings_template.json
with appropriate path normalization.
"""

import json
import re
from pathlib import Path
from typing import Any


def normalize_hook_path(path: str) -> str:
    """Normalize hook command path for comparison.

    Transforms:
    - "$CLAUDE_PROJECT_DIR/.claude/..." → ".claude/..."
    - ".claude/..." → ".claude/..."

    Args:
        path: Hook command path

    Returns:
        Normalized path string
    """
    # Remove $CLAUDE_PROJECT_DIR prefix if present
    normalized = re.sub(r"^\$CLAUDE_PROJECT_DIR/", "", path)
    return normalized


def normalize_hooks_dict(hooks: dict[str, Any]) -> dict[str, Any]:
    """Normalize hooks dictionary for comparison.

    Args:
        hooks: Hooks section from settings JSON

    Returns:
        Normalized hooks dictionary with consistent paths
    """
    normalized = {}

    for hook_name, hook_configs in hooks.items():
        normalized_configs = []

        for config in hook_configs:
            normalized_config = config.copy()

            if "hooks" in normalized_config:
                normalized_hooks = []
                for hook_def in normalized_config["hooks"]:
                    normalized_hook = hook_def.copy()
                    if "command" in normalized_hook:
                        normalized_hook["command"] = normalize_hook_path(normalized_hook["command"])
                    normalized_hooks.append(normalized_hook)
                normalized_config["hooks"] = normalized_hooks

            normalized_configs.append(normalized_config)

        normalized[hook_name] = normalized_configs

    return normalized


def compare_hooks(source_hooks: dict[str, Any], template_hooks: dict[str, Any]) -> list[str]:
    """Compare two hooks dictionaries and return differences.

    Args:
        source_hooks: Hooks from authoritative settings.json
        template_hooks: Hooks from UVX template

    Returns:
        List of error messages describing differences (empty if synced)
    """
    errors = []

    # Normalize both for comparison
    norm_source = normalize_hooks_dict(source_hooks)
    norm_template = normalize_hooks_dict(template_hooks)

    # Find hooks in source but not in template
    missing_hooks = set(norm_source.keys()) - set(norm_template.keys())
    if missing_hooks:
        errors.append(f"Missing in template: {', '.join(sorted(missing_hooks))}")

    # Find hooks in template but not in source (unexpected)
    extra_hooks = set(norm_template.keys()) - set(norm_source.keys())
    if extra_hooks:
        errors.append(f"Extra in template (not in source): {', '.join(sorted(extra_hooks))}")

    # Compare hooks that exist in both
    for hook_name in norm_source.keys() & norm_template.keys():
        if norm_source[hook_name] != norm_template[hook_name]:
            errors.append(f"Hook '{hook_name}' differs between source and template")

    return errors


def validate_hooks_sync(source_path: Path, template_path: Path) -> tuple[bool, list[str]]:
    """Validate hooks synchronization between settings files.

    Args:
        source_path: Path to authoritative .claude/settings.json
        template_path: Path to UVX template

    Returns:
        Tuple of (is_valid, error_messages)
    """
    try:
        # Load source settings
        with open(source_path, encoding="utf-8") as f:
            source_data = json.load(f)

        source_hooks = source_data.get("hooks", {})

        # Load template settings
        with open(template_path, encoding="utf-8") as f:
            template_data = json.load(f)

        template_hooks = template_data.get("hooks", {})

        # Compare
        errors = compare_hooks(source_hooks, template_hooks)

        return (len(errors) == 0, errors)

    except FileNotFoundError as e:
        return (False, [f"File not found: {e.filename}"])
    except json.JSONDecodeError as e:
        return (False, [f"Invalid JSON: {e}"])
    except Exception as e:
        return (False, [f"Validation error: {e}"])


def main() -> int:
    """Main entry point for CLI usage.

    Returns:
        0 if hooks are synced, 1 otherwise
    """
    # Determine paths relative to this script
    script_dir = Path(__file__).parent

    # Source: ../../.claude/settings.json (from src/amplihack/utils/)
    source_path = script_dir.parent.parent.parent / ".claude" / "settings.json"

    # Template: ./uvx_settings_template.json (same directory)
    template_path = script_dir / "uvx_settings_template.json"

    is_valid, errors = validate_hooks_sync(source_path, template_path)

    if is_valid:
        print("✅ Hooks are synchronized")
        return 0
    print("❌ Hooks are OUT OF SYNC")
    print()
    for error in errors:
        print(f"  • {error}")
    print()
    print("To fix, run:")
    print("  python scripts/sync_hooks.py")
    return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
