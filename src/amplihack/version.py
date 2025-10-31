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
    """Get current amplihack version from pyproject.toml.

    Returns:
        Version string in semantic versioning format (MAJOR.MINOR.PATCH)

    Raises:
        FileNotFoundError: If pyproject.toml cannot be found
        KeyError: If version field is missing from pyproject.toml
    """
    # Navigate up from src/amplihack/version.py to project root
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    if not pyproject_path.exists():
        raise FileNotFoundError(
            f"pyproject.toml not found at {pyproject_path}. Cannot determine version."
        )

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    try:
        return data["project"]["version"]
    except KeyError as e:
        raise KeyError(
            "Version field not found in pyproject.toml. "
            'Expected format: [project] version = "X.Y.Z"'
        ) from e


# Module-level version variable for easy import
__version__ = get_version()
