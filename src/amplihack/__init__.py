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
    """Locate hooks.json on disk.

    Search order:
    1. Installed location: ~/.amplihack/.claude/tools/amplihack/hooks/hooks.json
    2. Source repo location: <repo_root>/.claude/tools/amplihack/hooks/hooks.json

    Returns:
        Path to hooks.json, or None if not found.
    """
    installed = os.path.join(HOME, ".amplihack", ".claude", "tools", "amplihack", "hooks", "hooks.json")
    if os.path.isfile(installed):
        return installed

    # Try repo-relative (for development / CI)
    repo_candidate = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        ".claude", "tools", "amplihack", "hooks", "hooks.json",
    )
    if os.path.isfile(repo_candidate):
        return repo_candidate

    return None


def validate_hook_configs_against_json(hooks_json_path=None):
    """Validate HOOK_CONFIGS and RUST_HOOK_MAP against hooks.json.

    hooks.json is the canonical source of truth for which hooks exist and their
    event types, files, timeouts, and matchers.  This function detects divergence
    so that mismatches are caught at startup rather than silently ignored.

    Args:
        hooks_json_path: Explicit path to hooks.json (used by tests).
                         If None, auto-resolved via _resolve_hooks_json_path().

    Returns:
        Tuple of (valid: bool, errors: list[str]).
        When valid is False, errors describes each mismatch found.

    Raises:
        Nothing — callers decide whether to warn or abort.
    """
    import json as _json

    if hooks_json_path is None:
        hooks_json_path = _resolve_hooks_json_path()

    if hooks_json_path is None:
        return True, []  # hooks.json not available (e.g. pip-installed wheel) — skip

    try:
        with open(hooks_json_path, encoding="utf-8") as f:
            hooks_json = _json.load(f)
    except Exception as exc:
        return False, [f"Failed to read hooks.json at {hooks_json_path}: {exc}"]

    errors = []

    # --- 1. Validate HOOK_CONFIGS["amplihack"] against hooks.json ---
    # Build a normalised set of (event_type, filename) from hooks.json
    json_hooks = set()  # {(event_type, filename)}
    json_details = {}   # {(event_type, filename): {timeout, matcher}}
    for event_type, event_configs in hooks_json.items():
        for config in event_configs:
            for hook in config.get("hooks", []):
                cmd = hook.get("command", "")
                filename = os.path.basename(cmd)
                json_hooks.add((event_type, filename))
                json_details[(event_type, filename)] = {
                    "timeout": hook.get("timeout"),
                    "matcher": config.get("matcher"),
                }

    # Build the same set from HOOK_CONFIGS["amplihack"]
    py_hooks = set()
    py_details = {}
    for entry in HOOK_CONFIGS.get("amplihack", []):
        key = (entry["type"], entry["file"])
        py_hooks.add(key)
        py_details[key] = {
            "timeout": entry.get("timeout"),
            "matcher": entry.get("matcher"),
        }

    # Compare sets
    in_json_not_py = json_hooks - py_hooks
    in_py_not_json = py_hooks - json_hooks

    for event_type, filename in sorted(in_json_not_py):
        errors.append(
            f"Hook ({event_type}, {filename}) present in hooks.json but missing from HOOK_CONFIGS"
        )
    for event_type, filename in sorted(in_py_not_json):
        errors.append(
            f"Hook ({event_type}, {filename}) present in HOOK_CONFIGS but missing from hooks.json"
        )

    # Compare details (timeout, matcher) for hooks present in both
    for key in sorted(py_hooks & json_hooks):
        py_d = py_details[key]
        js_d = json_details[key]
        if py_d["timeout"] != js_d["timeout"]:
            errors.append(
                f"Hook {key} timeout mismatch: HOOK_CONFIGS={py_d['timeout']}, hooks.json={js_d['timeout']}"
            )
        if py_d["matcher"] != js_d["matcher"]:
            errors.append(
                f"Hook {key} matcher mismatch: HOOK_CONFIGS={py_d['matcher']}, hooks.json={js_d['matcher']}"
            )

    # --- 2. Validate RUST_HOOK_MAP covers all amplihack hooks (except known Python-only) ---
    # Every file in HOOK_CONFIGS["amplihack"] that has a Rust equivalent should be in RUST_HOOK_MAP.
    # workflow_classification_reminder.py is explicitly Python-only, so we just verify
    # that no file in HOOK_CONFIGS is completely absent from RUST_HOOK_MAP without explanation.
    # (We don't enforce that every hook MUST have a Rust equivalent — only that files
    #  listed in RUST_HOOK_MAP actually appear in HOOK_CONFIGS or hooks.json.)
    for rust_file in RUST_HOOK_MAP:
        # session_stop.py is Copilot-only, noted in the comment — skip it
        if rust_file == "session_stop.py":
            continue
        found_in_configs = any(
            entry["file"] == rust_file for entry in HOOK_CONFIGS.get("amplihack", [])
        )
        found_in_json = any(
            os.path.basename(hook.get("command", "")) == rust_file
            for configs in hooks_json.values()
            for config in configs
            for hook in config.get("hooks", [])
        )
        if not found_in_configs and not found_in_json:
            errors.append(
                f"RUST_HOOK_MAP contains '{rust_file}' which is absent from both HOOK_CONFIGS and hooks.json"
            )

    return len(errors) == 0, errors


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
    "RUST_HOOK_MAP",
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
    "validate_hook_configs_against_json",
    # Uninstall
    "uninstall",
    "read_manifest",
    # Utilities
    "filecmp",
    # Main
    "main",
]
