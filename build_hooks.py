"""Build hooks for setuptools to include .claude/ directory in wheels.

This module provides custom build hooks that copy the .claude/ directory
from the repository root into src/amplihack/.claude/ before building the wheel.
This ensures the framework files are included in the wheel distribution for
UVX deployment.

Why this is needed:
- MANIFEST.in only controls sdist, not wheels
- Wheels only include files inside Python packages
- .claude/ is at repo root (outside src/amplihack/)
- Solution: Copy .claude/ into package before build

Why symlinks=True is required:
- Enables support for symlinks within .claude/ directory structure
- shutil.copytree fails on symlinks without symlinks=True parameter
- Preserving symlinks maintains zero-duplication architecture
- Example: .github/agents/amplihack → .claude/agents/amplihack (source of truth)

NOTE: This file is only used during package building (not runtime),
so missing setuptools import at runtime is expected and not an error.
"""

import shutil
from pathlib import Path

from setuptools import build_meta as _orig
from setuptools.build_meta import *  # noqa: F403


class _CustomBuildBackend:
    """Custom build backend that copies .claude/ before building."""

    def __init__(self):
        self.repo_root = Path(__file__).parent
        self.claude_src = self.repo_root / ".claude"
        self.claude_dest = self.repo_root / "src" / "amplihack" / ".claude"

    def _copy_claude_directory(self):
        """Copy .claude/ from repo root to src/amplihack/ if needed."""
        if not self.claude_src.exists():
            print(f"Warning: .claude/ not found at {self.claude_src}")
            return

        # Remove existing .claude/ in package to ensure clean copy
        if self.claude_dest.exists():
            print(f"Removing existing {self.claude_dest}")
            shutil.rmtree(self.claude_dest)

        # Copy .claude/ into package
        print(f"Copying {self.claude_src} -> {self.claude_dest}")
        shutil.copytree(
            self.claude_src,
            self.claude_dest,
            symlinks=True,  # Preserve symlinks within .claude/ directory structure
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
        print("Successfully copied .claude/ to package")

    def _cleanup_claude_directory(self):
        """Remove .claude/ from package after build."""
        if self.claude_dest.exists():
            print(f"Cleaning up {self.claude_dest}")
            shutil.rmtree(self.claude_dest)

    def build_wheel(self, wheel_directory, config_settings=None, metadata_directory=None):
        """Build wheel with .claude/ directory included."""
        try:
            self._copy_claude_directory()
            result = _orig.build_wheel(
                wheel_directory,
                config_settings=config_settings,
                metadata_directory=metadata_directory,
            )
            return result
        finally:
            # Always cleanup, even if build fails
            self._cleanup_claude_directory()

    def build_sdist(self, sdist_directory, config_settings=None):
        """Build sdist (MANIFEST.in handles .claude/ for sdist)."""
        return _orig.build_sdist(sdist_directory, config_settings=config_settings)


# Create singleton instance
_backend = _CustomBuildBackend()

# Expose the build functions
build_wheel = _backend.build_wheel
build_sdist = _backend.build_sdist
