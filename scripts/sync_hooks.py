#!/usr/bin/env python3
"""Sync hooks from .claude/settings.json to UVX template.

This script ensures the UVX settings template stays in sync with the authoritative
settings.json by copying hooks and transforming paths appropriately.
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict


def transform_hook_path(path: str) -> str:
    """Transform hook path from source to template format.

    Transforms:
    - "$CLAUDE_PROJECT_DIR/.claude/..." → ".claude/..."
    - ".claude/..." → ".claude/..." (unchanged)

    Args:
        path: Source hook command path

    Returns:
        Template-formatted path
    """
    # Remove $CLAUDE_PROJECT_DIR prefix
    return re.sub(r'^\$CLAUDE_PROJECT_DIR/', '', path)


def transform_hooks_dict(hooks: Dict[str, Any]) -> Dict[str, Any]:
    """Transform hooks dictionary for template format.

    Args:
        hooks: Hooks section from source settings.json

    Returns:
        Transformed hooks dictionary for template
    """
    transformed = {}

    for hook_name, hook_configs in hooks.items():
        transformed_configs = []

        for config in hook_configs:
            transformed_config = config.copy()

            if 'hooks' in transformed_config:
                transformed_hooks = []
                for hook_def in transformed_config['hooks']:
                    transformed_hook = hook_def.copy()
                    if 'command' in transformed_hook:
                        transformed_hook['command'] = transform_hook_path(
                            transformed_hook['command']
                        )
                    transformed_hooks.append(transformed_hook)
                transformed_config['hooks'] = transformed_hooks

            transformed_configs.append(transformed_config)

        transformed[hook_name] = transformed_configs

    return transformed


def sync_hooks(
    source_path: Path,
    template_path: Path,
    dry_run: bool = False
) -> bool:
    """Sync hooks from source to template.

    Args:
        source_path: Path to authoritative .claude/settings.json
        template_path: Path to UVX template
        dry_run: If True, only show what would be done

    Returns:
        True if sync succeeded, False otherwise
    """
    try:
        # Load source settings
        print(f"Reading source: {source_path}")
        with open(source_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)

        source_hooks = source_data.get('hooks', {})
        print(f"Found {len(source_hooks)} hook types in source")

        # Load template settings
        print(f"Reading template: {template_path}")
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)

        # Transform and update hooks
        transformed_hooks = transform_hooks_dict(source_hooks)
        template_data['hooks'] = transformed_hooks

        if dry_run:
            print("\n[DRY RUN] Would update template with:")
            print(json.dumps(transformed_hooks, indent=2))
            print("\n[DRY RUN] No files modified")
            return True

        # Write atomically (temp file + rename)
        print(f"Writing updated template...")
        temp_fd, temp_path = tempfile.mkstemp(
            suffix='.json',
            dir=template_path.parent,
            text=True
        )

        try:
            with open(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2, ensure_ascii=False)
                f.write('\n')  # Add trailing newline

            # Atomic replace
            shutil.move(temp_path, template_path)
            print(f"✅ Successfully synced {len(transformed_hooks)} hook types")
            return True

        except Exception:
            # Clean up temp file on error
            Path(temp_path).unlink(missing_ok=True)
            raise

    except FileNotFoundError as e:
        print(f"❌ File not found: {e.filename}", file=sys.stderr)
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Sync error: {e}", file=sys.stderr)
        return False


def check_sync(source_path: Path, template_path: Path) -> bool:
    """Check if hooks are currently in sync.

    Args:
        source_path: Path to authoritative settings.json
        template_path: Path to UVX template

    Returns:
        True if in sync, False otherwise
    """
    # Import the validator
    sys.path.insert(0, str(source_path.parent.parent / 'src'))
    from amplihack.utils.sync_validator import validate_hooks_sync

    is_valid, errors = validate_hooks_sync(source_path, template_path)

    if is_valid:
        print("✅ Hooks are synchronized")
        return True
    else:
        print("❌ Hooks are OUT OF SYNC")
        for error in errors:
            print(f"  • {error}")
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Sync hooks from settings.json to UVX template'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without modifying files'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check if hooks are in sync without modifying files'
    )

    args = parser.parse_args()

    # Determine paths (run from project root)
    script_dir = Path(__file__).parent.parent
    source_path = script_dir / '.claude' / 'settings.json'
    template_path = script_dir / 'src' / 'amplihack' / 'utils' / 'uvx_settings_template.json'

    if args.check:
        return 0 if check_sync(source_path, template_path) else 1

    print("=" * 60)
    print("Hook Synchronization Tool")
    print("=" * 60)
    print()

    success = sync_hooks(source_path, template_path, dry_run=args.dry_run)

    if success and not args.dry_run:
        print()
        print("Verifying sync...")
        check_sync(source_path, template_path)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
