"""Build hooks for setuptools to include .claude/ and amplifier-bundle/ in wheels.

This module provides custom build hooks that copy directories from the repository
root into src/amplihack/ before building the wheel. This ensures the framework
files are included in the wheel distribution for UVX deployment.

Why this is needed:
- MANIFEST.in only controls sdist, not wheels
- Wheels only include files inside Python packages
- .claude/ and amplifier-bundle/ are at repo root (outside src/amplihack/)
- Solution: Copy them into package before build

NOTE: This file is only used during package building (not runtime),
so missing setuptools import at runtime is expected and not an error.
"""

import shutil
from pathlib import Path

from setuptools import build_meta as _orig
from setuptools.build_meta import (  # noqa: F401
    build_editable,
    get_requires_for_build_editable,
    get_requires_for_build_sdist,
    get_requires_for_build_wheel,
    prepare_metadata_for_build_editable,
    prepare_metadata_for_build_wheel,
)


class _CustomBuildBackend:
    """Custom build backend that copies .claude/ and amplifier-bundle/ before building."""

    def __init__(self):
        self.repo_root = Path(__file__).parent
        # Directories to copy into the package
        self.copy_dirs = [
            (".claude", ".claude"),
            ("amplifier-bundle", "amplifier-bundle"),
        ]
        # Additional copies: source -> destination (within pkg_dest)
        # These are copied AFTER the main directories
        self.extra_copies = [
            # Copy skills into amplifier-bundle so they're accessible via relative path
            (".claude/skills", "amplifier-bundle/skills"),
            (".claude/recipes", "amplifier-bundle/recipes-claude"),
        ]
        self.pkg_dest = self.repo_root / "src" / "amplihack"

    def _copy_directories(self):
        """Copy directories from repo root to src/amplihack/."""
        for src_name, dest_name in self.copy_dirs:
            src_path = self.repo_root / src_name
            dest_path = self.pkg_dest / dest_name

            if not src_path.exists():
                print(f"Warning: {src_name}/ not found at {src_path}")
                continue

            # Remove existing directory in package to ensure clean copy
            if dest_path.exists():
                print(f"Removing existing {dest_path}")
                shutil.rmtree(dest_path)

            # Copy directory into package
            print(f"Copying {src_path} -> {dest_path}")
            shutil.copytree(
                src_path,
                dest_path,
                ignore=shutil.ignore_patterns(
                    # Exclude runtime data (logs, metrics, analysis)
                    "runtime",
                    # Exclude Python cache
                    "__pycache__",
                    "*.pyc",
                    "*.pyo",
                    # Exclude temp files
                    "*~",
                    ".DS_Store",
                    "*.swp",
                    "*.swo",
                ),
            )
            print(f"Successfully copied {src_name}/ to package")

        # Handle extra copies (e.g., skills into amplifier-bundle)
        for src_name, dest_name in self.extra_copies:
            src_path = self.repo_root / src_name
            dest_path = self.pkg_dest / dest_name

            if not src_path.exists():
                print(f"Warning: {src_name}/ not found at {src_path}")
                continue

            # Remove existing directory to ensure clean copy
            if dest_path.exists():
                print(f"Removing existing {dest_path}")
                shutil.rmtree(dest_path)

            # Copy directory
            print(f"Copying {src_path} -> {dest_path}")
            shutil.copytree(
                src_path,
                dest_path,
                ignore=shutil.ignore_patterns(
                    "__pycache__",
                    "*.pyc",
                    "*.pyo",
                    "*~",
                    ".DS_Store",
                ),
            )
            print(f"Successfully copied {src_name}/ to {dest_name}")

    def _cleanup_directories(self):
        """Remove copied directories from package after build."""
        # Clean up main directories
        for _, dest_name in self.copy_dirs:
            dest_path = self.pkg_dest / dest_name
            if dest_path.exists():
                print(f"Cleaning up {dest_path}")
                shutil.rmtree(dest_path)
        # Clean up extra copies
        for _, dest_name in self.extra_copies:
            dest_path = self.pkg_dest / dest_name
            if dest_path.exists():
                print(f"Cleaning up {dest_path}")
                shutil.rmtree(dest_path)

    def build_wheel(self, wheel_directory, config_settings=None, metadata_directory=None):
        """Build wheel with .claude/ and amplifier-bundle/ directories included."""
        try:
            self._copy_directories()
            result = _orig.build_wheel(
                wheel_directory,
                config_settings=config_settings,
                metadata_directory=metadata_directory,
            )
            return result
        finally:
            # Always cleanup, even if build fails
            self._cleanup_directories()

    def build_sdist(self, sdist_directory, config_settings=None):
        """Build sdist (MANIFEST.in handles .claude/ for sdist)."""
        return _orig.build_sdist(sdist_directory, config_settings=config_settings)


# Create singleton instance
_backend = _CustomBuildBackend()

# Expose the build functions
build_wheel = _backend.build_wheel
build_sdist = _backend.build_sdist
