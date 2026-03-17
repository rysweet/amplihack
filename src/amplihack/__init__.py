"""Amplihack package initialization.

Philosophy:
- Ruthless simplicity: Just constants and exports
- Modular design: All functionality in focused modules
- Clear public API: __all__ defines what's exported

Public API:
    - Constants: HOME, CLAUDE_DIR, etc.
    - Installation: _local_install, ensure_dirs, copytree_manifest
    - Settings: ensure_settings_json, update_hook_paths
    - Hooks: verify_hooks
    - Uninstall: uninstall
    - Main: main (CLI entry point)
"""

import json
import os
import sys
from pathlib import Path

# Read version from installed package metadata
try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    # Python < 3.8 (shouldn't happen, but graceful fallback)
    print("WARNING: importlib.metadata not available", file=sys.stderr)
    version = None  # type: ignore
    PackageNotFoundError = Exception  # type: ignore

if version:
    try:
        __version__ = version("amplihack")
    except PackageNotFoundError:
        # Fallback for development (not installed)
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            print("WARNING: tomllib not available, trying tomli", file=sys.stderr)
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                print(
                    "WARNING: tomli not available, version detection from pyproject.toml disabled",
                    file=sys.stderr,
                )
                tomllib = None  # type: ignore

        if tomllib:
            _pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
            if _pyproject_path.exists():
                with open(_pyproject_path, "rb") as f:
                    _pyproject = tomllib.load(f)
                    __version__ = _pyproject["project"]["version"]
            else:
                __version__ = "unknown"
        else:
            __version__ = "unknown"
else:
    __version__ = "unknown"

# Core constants
HOME = str(Path.home())
CLAUDE_DIR = os.path.join(HOME, ".claude")
CLI_NAME = "amplihack_cli.py"
CLI_SRC = os.path.abspath(__file__)

MANIFEST_JSON = os.path.join(CLAUDE_DIR, "install", "amplihack-manifest.json")

# Essential directories that must be copied during installation
ESSENTIAL_DIRS = [
    "bin",  # Staged Rust binaries (amplihack, amplihack-hooks)
    "agents/amplihack",  # Specialized agents
    "commands/amplihack",  # Slash commands
    "tools/amplihack",  # Hooks and utilities
    "tools/xpia",  # XPIA security hooks (Issue #458)
    "context",  # Philosophy, patterns, project info
    "workflow",  # DEFAULT_WORKFLOW.md
    "skills",  # Claude Code Skills (12 production skills)
    "templates",  # Investigation & architecture doc templates
    "scenarios",  # Production scenario tools
    "docs",  # Investigation examples and documentation
    "schemas",  # JSON/YAML schemas for validation
    "config",  # Configuration files for tools
]

# Essential files that must be copied (relative to .claude/)
ESSENTIAL_FILES = [
    "tools/statusline.sh",  # StatusLine script for Claude Code status bar
    "../CLAUDE.md",  # Root-level CLAUDE.md (Issue #1746)
    "AMPLIHACK.md",  # Framework instructions at .claude/AMPLIHACK.md (Issue #1948)
]

# Runtime directories that need to be created
RUNTIME_DIRS = [
    "runtime",
    "runtime/logs",
    "runtime/metrics",
    "runtime/security",
    "runtime/analysis",
]

# Hook configurations for amplihack and xpia systems
# MUST match hooks.json - hooks.json is the canonical source of truth
HOOK_CONFIGS = {
    "amplihack": [
        {"type": "SessionStart", "file": "session_start.py", "timeout": 10},
        {"type": "Stop", "file": "stop.py", "timeout": 120},
        {"type": "PreToolUse", "file": "pre_tool_use.py", "matcher": "*"},
        {"type": "PostToolUse", "file": "post_tool_use.py", "matcher": "*"},
        {"type": "UserPromptSubmit", "file": "user_prompt_submit.py", "timeout": 10},
        {"type": "UserPromptSubmit", "file": "workflow_classification_reminder.py", "timeout": 5},
        {"type": "PreCompact", "file": "pre_compact.py", "timeout": 30},
    ],
    "xpia": [
        {"type": "SessionStart", "file": "session_start.py", "timeout": 10},
        {"type": "PostToolUse", "file": "post_tool_use.py", "matcher": "*"},
        {"type": "PreToolUse", "file": "pre_tool_use.py", "matcher": "*"},
    ],
}

# Maps Python hook filenames to Rust multicall subcommands (amplihack-hooks <subcommand>).
# Hooks NOT in this map (e.g., workflow_classification_reminder.py) always use Python.
RUST_HOOK_MAP = {
    "session_start.py": "session-start",
    "stop.py": "stop",
    # session_stop.py is used only in Copilot launcher wrappers (stage_hooks),
    # not in Claude Code's HOOK_CONFIGS. Included here for Copilot rust engine path.
    "session_stop.py": "session-stop",
    "pre_tool_use.py": "pre-tool-use",
    "post_tool_use.py": "post-tool-use",
    "user_prompt_submit.py": "user-prompt-submit",
    "pre_compact.py": "pre-compact",
}

def _resolve_hooks_json_path():
    """Locate the canonical hooks.json file.

    Search order:
    1. Installed location: ~/.amplihack/.claude/tools/amplihack/hooks/hooks.json
    2. Source tree (development): relative to this file

    Returns:
        Path to hooks.json, or None if not found.
    """
    installed = Path(HOME) / ".amplihack" / ".claude" / "tools" / "amplihack" / "hooks" / "hooks.json"
    if installed.exists():
        return installed

    # Development: hooks.json lives in the source tree
    source = Path(__file__).resolve().parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks" / "hooks.json"
    if source.exists():
        return source

    return None


def validate_hook_configs_against_json(hooks_json_path=None):
    """Validate HOOK_CONFIGS and RUST_HOOK_MAP against hooks.json.

    hooks.json is the canonical source of truth for hook definitions.
    This function checks that HOOK_CONFIGS (used by the Python installer)
    and RUST_HOOK_MAP (used by the Rust hook engine) are consistent with it.

    Args:
        hooks_json_path: Path to hooks.json. If None, auto-discovered.

    Returns:
        Tuple of (is_valid: bool, errors: list[str]).
        When is_valid is False, errors contains human-readable descriptions
        of every divergence found.

    Raises:
        Nothing — returns errors instead of raising.
    """
    errors = []

    if hooks_json_path is None:
        hooks_json_path = _resolve_hooks_json_path()

    if hooks_json_path is None:
        errors.append("hooks.json not found — cannot validate HOOK_CONFIGS")
        return (False, errors)

    try:
        with open(hooks_json_path, encoding="utf-8") as f:
            hooks_json = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"Failed to read hooks.json at {hooks_json_path}: {exc}")
        return (False, errors)

    # --- Build a normalised view from hooks.json ---
    # hooks.json structure: { "EventType": [ { "hooks": [ { "command": "...file.py", ... } ] } ] }
    json_hooks_by_type = {}  # event_type -> list of basenames
    for event_type, event_configs in hooks_json.items():
        basenames = []
        for config in event_configs:
            for hook in config.get("hooks", []):
                command = hook.get("command", "")
                basename = os.path.basename(command)
                if basename:
                    basenames.append(basename)
        if basenames:
            json_hooks_by_type[event_type] = sorted(basenames)

    # --- Check 1: HOOK_CONFIGS["amplihack"] must match hooks.json ---
    config_hooks_by_type = {}  # event_type -> list of filenames
    for hook_info in HOOK_CONFIGS.get("amplihack", []):
        event_type = hook_info["type"]
        config_hooks_by_type.setdefault(event_type, []).append(hook_info["file"])
    for key in config_hooks_by_type:
        config_hooks_by_type[key] = sorted(config_hooks_by_type[key])

    # Compare event types present
    json_event_types = set(json_hooks_by_type.keys())
    config_event_types = set(config_hooks_by_type.keys())

    missing_in_config = json_event_types - config_event_types
    extra_in_config = config_event_types - json_event_types

    for event_type in sorted(missing_in_config):
        errors.append(
            f"HOOK_CONFIGS['amplihack'] is missing event type '{event_type}' "
            f"that exists in hooks.json"
        )

    for event_type in sorted(extra_in_config):
        errors.append(
            f"HOOK_CONFIGS['amplihack'] has event type '{event_type}' "
            f"not present in hooks.json"
        )

    # Compare hook files within shared event types
    for event_type in sorted(json_event_types & config_event_types):
        json_files = json_hooks_by_type[event_type]
        config_files = config_hooks_by_type[event_type]

        if json_files != config_files:
            errors.append(
                f"HOOK_CONFIGS['amplihack'] event '{event_type}' has files "
                f"{config_files} but hooks.json has {json_files}"
            )

    # --- Check 2: Every amplihack hook file (except workflow_classification_reminder.py)
    #     should have a RUST_HOOK_MAP entry ---
    # workflow_classification_reminder.py is documented as Python-only.
    PYTHON_ONLY_HOOKS = {"workflow_classification_reminder.py"}
    all_amplihack_files = {h["file"] for h in HOOK_CONFIGS.get("amplihack", [])}

    for hook_file in sorted(all_amplihack_files - PYTHON_ONLY_HOOKS):
        if hook_file not in RUST_HOOK_MAP:
            errors.append(
                f"RUST_HOOK_MAP is missing entry for '{hook_file}' "
                f"(present in HOOK_CONFIGS['amplihack'])"
            )

    # Check that RUST_HOOK_MAP doesn't reference files absent from
    # both HOOK_CONFIGS['amplihack'] and the known Copilot-only set.
    COPILOT_ONLY_HOOKS = {"session_stop.py"}  # documented in RUST_HOOK_MAP comment
    for rust_file in sorted(RUST_HOOK_MAP.keys()):
        if rust_file not in all_amplihack_files and rust_file not in COPILOT_ONLY_HOOKS:
            errors.append(
                f"RUST_HOOK_MAP has entry for '{rust_file}' which is not in "
                f"HOOK_CONFIGS['amplihack'] and not a known Copilot-only hook"
            )

    return (len(errors) == 0, errors)


def _validate_hooks_on_startup():
    """Run hook config validation at startup and warn on divergence.

    This is called at module import time. It logs warnings to stderr
    but does not raise — divergence is a configuration bug, not a
    runtime crash.
    """
    is_valid, errors = validate_hook_configs_against_json()
    if not is_valid:
        print(
            "WARNING: HOOK_CONFIGS/RUST_HOOK_MAP diverged from hooks.json:",
            file=sys.stderr,
        )
        for error in errors:
            print(f"  - {error}", file=sys.stderr)


# Validate at import time — catches divergence early.
_validate_hooks_on_startup()


# Import from focused modules
from .hook_verification import verify_hooks
from .install import (
    _local_install,
    copytree_manifest,
    create_runtime_dirs,
    ensure_dirs,
    get_all_files_and_dirs,
    write_manifest,
)
from .settings import SETTINGS_TEMPLATE, ensure_settings_json, update_hook_paths
from .uninstall import read_manifest, uninstall


def filecmp(f1, f2):
    """Compare two files byte-by-byte.

    Args:
        f1: Path to first file
        f2: Path to second file

    Returns:
        True if files are identical, False otherwise
    """
    try:
        if os.path.getsize(f1) != os.path.getsize(f2):
            return False
        with open(f1, "rb") as file1, open(f2, "rb") as file2:
            return file1.read() == file2.read()
    except Exception as e:
        import logging

        logging.getLogger(__name__).debug(f"File comparison failed for {f1}: {type(e).__name__}")
        return False


def main():
    """Main CLI entry point."""
    # Ensure dependencies are installed at CLI startup (not import time)
    from .copilot_auto_install import ensure_copilot_sdk_installed
    from .memory_auto_install import ensure_memory_lib_installed

    ensure_memory_lib_installed()
    ensure_copilot_sdk_installed()

    # Import and use the enhanced CLI
    from .cli import main as cli_main

    return cli_main()


# Public API
__all__ = [
    # Version
    "__version__",
    # Constants
    "HOME",
    "CLAUDE_DIR",
    "CLI_NAME",
    "CLI_SRC",
    "MANIFEST_JSON",
    "ESSENTIAL_DIRS",
    "ESSENTIAL_FILES",
    "RUNTIME_DIRS",
    "HOOK_CONFIGS",
    "validate_hook_configs_against_json",
    "SETTINGS_TEMPLATE",
    # Installation
    "_local_install",
    "ensure_dirs",
    "copytree_manifest",
    "create_runtime_dirs",
    "get_all_files_and_dirs",
    "write_manifest",
    # Settings
    "ensure_settings_json",
    "update_hook_paths",
    # Hooks
    "verify_hooks",
    # Uninstall
    "uninstall",
    "read_manifest",
    # Utilities
    "filecmp",
    # Main
    "main",
]
