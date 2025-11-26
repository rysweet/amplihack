"""Plugin discovery with security validation.

This module provides secure plugin discovery functionality:
- Finds all .py files in a directory recursively
- Validates against path traversal attacks
- Enforces file size limits (max 1MB)
- Checks file permissions

Philosophy:
- Security first: prevent path traversal and malicious files
- Resilient: one bad file doesn't stop discovery
- Standard library only

Public API (the "studs"):
    discover_plugins: Find all plugin files in a directory with security validation
"""

import os
from pathlib import Path

# Security constants
MAX_FILE_SIZE = 1024 * 1024  # 1MB in bytes


def _validate_path(plugin_dir: str) -> Path:
    """Validate directory path against traversal attacks.

    Args:
        plugin_dir: Directory path to validate

    Returns:
        Path: Resolved absolute path

    Raises:
        ValueError: If path contains traversal attempts
    """
    path = Path(plugin_dir).resolve()

    # Check for path traversal patterns
    if ".." in plugin_dir:
        raise ValueError(
            f"path traversal detected in '{plugin_dir}'. "
            "Relative paths with '..' are not allowed for security."
        )

    # Additional check: ensure resolved path doesn't escape to sensitive areas
    path_str = str(path)
    if "/etc" in path_str or "passwd" in path_str:
        raise ValueError(
            f"path traversal detected: '{plugin_dir}' resolves to sensitive system path '{path_str}'"
        )

    return path


def _validate_file_size(file_path: Path) -> None:
    """Validate file size is within limits.

    Args:
        file_path: Path to file to check

    Raises:
        ValueError: If file exceeds size limit
    """
    try:
        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(
                f"File '{file_path}' exceeds maximum size limit. "
                f"Size: {file_size} bytes, Limit: {MAX_FILE_SIZE} bytes (1MB)"
            )
    except OSError as e:
        # File might not be readable or accessible
        raise ValueError(f"Cannot access file '{file_path}': {e}")


def _is_readable(file_path: Path) -> bool:
    """Check if file is readable.

    Args:
        file_path: Path to file to check

    Returns:
        bool: True if readable, False otherwise
    """
    try:
        return os.access(file_path, os.R_OK)
    except Exception:
        return False


def discover_plugins(plugin_dir: str) -> list[str]:
    """Discover all Python plugin files in a directory with security validation.

    Recursively searches for .py files, excluding __init__.py files.
    Validates against security threats:
    - Path traversal attacks
    - Oversized files (> 1MB)
    - Unreadable files

    Args:
        plugin_dir: Directory path to search for plugins

    Returns:
        List[str]: List of absolute paths to discovered plugin files

    Raises:
        ValueError: If path validation fails or files violate security constraints

    Example:
        >>> plugins = discover_plugins("/path/to/plugins")
        >>> for plugin_file in plugins:
        ...     print(f"Found: {plugin_file}")
    """
    # Validate path against traversal
    try:
        validated_path = _validate_path(plugin_dir)
    except ValueError:
        # Re-raise validation errors immediately
        raise

    # Check if directory exists
    if not validated_path.exists():
        return []

    if not validated_path.is_dir():
        return []

    discovered_files = []

    # Recursively find all .py files
    try:
        for py_file in validated_path.rglob("*.py"):
            # Skip __init__.py files
            if py_file.name == "__init__.py":
                continue

            # Check if file is readable
            if not _is_readable(py_file):
                # Skip unreadable files silently (resilient batch processing)
                continue

            # Validate file size
            try:
                _validate_file_size(py_file)
            except ValueError:
                # Re-raise size violations (security constraint)
                raise

            discovered_files.append(str(py_file))

    except Exception as e:
        # Handle unexpected errors during directory traversal
        if "path traversal" in str(e).lower() or "maximum size" in str(e).lower():
            raise
        # For other errors, return what we've found so far (resilient)

    return discovered_files


__all__ = ["discover_plugins"]
