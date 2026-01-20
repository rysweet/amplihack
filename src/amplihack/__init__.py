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
from pathlib import Path

# Core constants
HOME = str(Path.home())
CLAUDE_DIR = os.path.join(HOME, ".claude")
CLI_NAME = "amplihack_cli.py"
CLI_SRC = os.path.abspath(__file__)

MANIFEST_JSON = os.path.join(CLAUDE_DIR, "install", "amplihack-manifest.json")

# Essential directories that must be copied during installation
ESSENTIAL_DIRS = [
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
HOOK_CONFIGS = {
    "amplihack": [
        {"type": "SessionStart", "file": "session_start.py", "timeout": 10000},
        {"type": "Stop", "file": "stop.py", "timeout": 30000},
        {"type": "PostToolUse", "file": "post_tool_use.py", "matcher": "*"},
        {"type": "PreCompact", "file": "pre_compact.py", "timeout": 30000},
    ],
    "xpia": [
        {"type": "SessionStart", "file": "session_start.py", "timeout": 10000},
        {"type": "PostToolUse", "file": "post_tool_use.py", "matcher": "*"},
        {"type": "PreToolUse", "file": "pre_tool_use.py", "matcher": "*"},
    ],
}

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
    except Exception:
        return False


def main():
    """Main CLI entry point."""
    # Import and use the enhanced CLI
    from .cli import main as cli_main

    return cli_main()


# Public API
__all__ = [
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
