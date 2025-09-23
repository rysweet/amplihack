"""
AmplifyHack Path Resolution

Centralized path management to eliminate sys.path manipulations across modules.
This module provides clean path resolution without conflicts with external packages.
"""

import sys
from pathlib import Path
from typing import Optional

# One-time path setup - executed only when package is imported
_PROJECT_ROOT: Optional[Path] = None
_PATHS_INITIALIZED = False


def _initialize_paths():
    """Initialize project paths once per session."""
    global _PROJECT_ROOT, _PATHS_INITIALIZED

    if _PATHS_INITIALIZED:
        return _PROJECT_ROOT

    # Find project root by looking for .claude marker
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".claude").exists() and (parent / "CLAUDE.md").exists():
            _PROJECT_ROOT = parent
            break

    if _PROJECT_ROOT is None:
        raise ImportError("Could not locate project root - missing .claude directory")

    # Add essential paths to sys.path if not already present
    essential_paths = [
        str(_PROJECT_ROOT / "src"),
        str(_PROJECT_ROOT / ".claude" / "tools" / "amplihack"),
    ]

    for path in essential_paths:
        if path not in sys.path:
            sys.path.insert(0, path)

    _PATHS_INITIALIZED = True
    return _PROJECT_ROOT


def get_project_root() -> Path:
    """Get the project root directory.

    Returns:
        Path to the project root

    Raises:
        ImportError: If project root cannot be determined
    """
    if _PROJECT_ROOT is None:
        _initialize_paths()

    # Type checker satisfaction - _initialize_paths() ensures _PROJECT_ROOT is not None
    assert _PROJECT_ROOT is not None, "Project root should be initialized"
    return _PROJECT_ROOT


def get_amplihack_tools_dir() -> Path:
    """Get the amplihack tools directory."""
    return get_project_root() / ".claude" / "tools" / "amplihack"


def get_amplihack_src_dir() -> Path:
    """Get the amplihack source directory."""
    return get_project_root() / "src" / "amplihack"


# Initialize paths when module is imported
_initialize_paths()
