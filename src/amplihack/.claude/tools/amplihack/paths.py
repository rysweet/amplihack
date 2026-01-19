"""
AmplifyHack Path Resolution

Centralized path management to eliminate sys.path manipulations across modules.
This module provides clean path resolution without conflicts with external packages.
"""

import os
import sys
from pathlib import Path

# One-time path setup - executed only when package is imported
_PROJECT_ROOT: Path | None = None
_PATHS_INITIALIZED = False


def _initialize_paths():
    """Initialize project paths once per session using multi-strategy detection.

    Tries multiple strategies to find project root:
    1. Walk up from current working directory (FIRST - most reliable for hooks)
    2. Check AMPLIHACK_ROOT environment variable
    3. Check inside amplihack package (UVX/pip installs - fallback)
    4. Walk up from __file__ as last resort

    CRITICAL: CWD strategy must come BEFORE package check to avoid finding
    bundled .claude directory in uv cache instead of actual project directory.

    This ensures the function works from:
    - Project directory (dev mode)
    - Hooks (Claude Code sets CWD correctly)
    - Installed package (pip install)
    - UVX cache (uvx amplihack)
    """
    global _PROJECT_ROOT, _PATHS_INITIALIZED

    if _PATHS_INITIALIZED:
        return _PROJECT_ROOT

    errors = []

    # Strategy 1: Walk up from current working directory (HIGHEST PRIORITY)
    # Claude Code sets CWD to project root when running hooks
    current = Path.cwd()
    while current != current.parent:
        if (current / ".claude").exists():
            _PROJECT_ROOT = current
            _PATHS_INITIALIZED = True
            _add_essential_paths(_PROJECT_ROOT)
            return _PROJECT_ROOT
        current = current.parent
    errors.append("Strategy 1 (cwd walk): .claude not found in any parent directory")

    # Strategy 2: Check AMPLIHACK_ROOT environment variable
    if "AMPLIHACK_ROOT" in os.environ:
        env_path = Path(os.environ["AMPLIHACK_ROOT"])
        if env_path.exists() and (env_path / ".claude").exists():
            _PROJECT_ROOT = env_path
            _PATHS_INITIALIZED = True
            _add_essential_paths(_PROJECT_ROOT)
            return _PROJECT_ROOT
        errors.append(f"Strategy 2 (AMPLIHACK_ROOT): Path {env_path} invalid or missing .claude")
    else:
        errors.append("Strategy 2 (AMPLIHACK_ROOT): Environment variable not set")

    # Strategy 3: Check inside amplihack package (FALLBACK for non-hook contexts)
    # Only used when CWD doesn't have .claude (e.g., running from Python REPL)
    try:
        import amplihack

        package_root = Path(amplihack.__file__).parent
        # Check package root first (for installations where .claude is bundled)
        if (package_root / ".claude").exists():
            _PROJECT_ROOT = package_root
            _PATHS_INITIALIZED = True
            _add_essential_paths(_PROJECT_ROOT)
            return _PROJECT_ROOT
        # Also check parent of package root (for editable installs with src/ layout)
        project_root = package_root.parent.parent  # src/amplihack -> src -> project
        if (project_root / ".claude").exists():
            _PROJECT_ROOT = project_root
            _PATHS_INITIALIZED = True
            _add_essential_paths(_PROJECT_ROOT)
            return _PROJECT_ROOT
    except (ImportError, AttributeError) as e:
        errors.append(f"Strategy 3 (amplihack package): {e}")

    # Strategy 4: Last resort - walk up from __file__ looking for .claude marker
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".claude").exists():
            _PROJECT_ROOT = current
            _PATHS_INITIALIZED = True
            _add_essential_paths(_PROJECT_ROOT)
            return _PROJECT_ROOT
        current = current.parent
    errors.append("Strategy 4 (__file__ walk): .claude not found in any parent directory")

    # All strategies failed
    error_msg = (
        "Could not locate project root (looking for .claude directory).\n"
        "Tried the following strategies:\n" + "\n".join(f"  - {err}" for err in errors) + "\n\n"
        "Solutions:\n"
        "  - Set AMPLIHACK_ROOT environment variable to project root\n"
        "  - Run from within the project directory\n"
        "  - Ensure .claude directory exists in project root"
    )
    raise ImportError(error_msg)


def _add_essential_paths(project_root: Path) -> None:
    """Add essential paths to sys.path if not already present.

    Args:
        project_root: The project root directory
    """
    essential_paths = [
        str(project_root / "src"),
        str(project_root / ".claude" / "tools" / "amplihack"),
    ]

    for path in essential_paths:
        if path not in sys.path:
            sys.path.insert(0, path)


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
