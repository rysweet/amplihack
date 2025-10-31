"""Version information for amplihack.

This module provides version information by reading from pyproject.toml,
maintaining a single source of truth for the project version.
"""

import sys
from pathlib import Path

# Handle both Python 3.11+ (tomllib) and older versions (tomli)
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError("tomli is required for Python < 3.11. Install it with: pip install tomli")


def get_version() -> str:
    """Get current amplihack version from pyproject.toml or package metadata.

    First tries to read from pyproject.toml (development mode).
    Falls back to importlib.metadata (installed package mode).

    Returns:
        Version string in semantic versioning format (MAJOR.MINOR.PATCH)

    Raises:
        RuntimeError: If version cannot be determined from either source
    """
    # Try pyproject.toml first (development mode)
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            return data["project"]["version"]
        except (KeyError, Exception):
            # Fall through to importlib.metadata
            pass

    # Fall back to importlib.metadata (installed package mode)
    try:
        from importlib.metadata import version
        return version("microsofthackathon2025-agenticcoding")
    except Exception as e:
        raise RuntimeError(
            "Cannot determine version. Neither pyproject.toml nor package metadata available."
        ) from e


# Module-level version variable for easy import
__version__ = get_version()
