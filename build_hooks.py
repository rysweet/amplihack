"""Build hooks for setuptools to include .claude/ and amplifier-bundle/ in wheels.

This module provides custom build hooks that copy directories from the repository
root into src/amplihack/ before building the wheel. This ensures the framework
files are included in the wheel distribution for UVX deployment.

EXPECTED REPOSITORY STRUCTURE
=============================
The build expects this structure at the repository root:

    repo_root/
    ├── .claude/                    # REQUIRED - Claude Code framework files
    │   ├── skills/                 # REQUIRED - Skills directory (74+ skills)
    │   ├── recipes/                # Optional - Claude recipes
    │   ├── agents/                 # Agent definitions
    │   ├── commands/               # Slash commands
    │   ├── tools/                  # Hooks and utilities
    │   └── ...
    ├── amplifier-bundle/           # REQUIRED - Amplifier bundle definition
    │   ├── bundle.md               # REQUIRED - Bundle configuration
    │   ├── behaviors/              # Behavior definitions
    │   ├── modules/                # Module configurations
    │   └── recipes/                # Amplifier recipes
    ├── src/amplihack/              # REQUIRED - Python package
    └── build_hooks.py              # This file

Why this is needed:
- MANIFEST.in only controls sdist, not wheels
- Wheels only include files inside Python packages
- .claude/ and amplifier-bundle/ are at repo root (outside src/amplihack/)
- Solution: Copy them into package before build, cleanup after

NOTE: This file is only used during package building (not runtime),
so missing setuptools import at runtime is expected and not an error.
"""

import shutil
import sys
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


class BuildValidationError(Exception):
    """Raised when the repository structure doesn't match expectations."""

    pass


class _CustomBuildBackend:
    """Custom build backend that copies .claude/ and amplifier-bundle/ before building.

    This backend validates the expected structure exists, copies required directories
    into the package, and cleans up after the build completes.
    """

    # Required directories that MUST exist for build to succeed
    REQUIRED_DIRS = [
        ".claude",
        ".claude/skills",
        "amplifier-bundle",
    ]

    # Required files that MUST exist
    REQUIRED_FILES = [
        "amplifier-bundle/bundle.md",
    ]

    # Patterns to exclude when copying (applied to all copies)
    EXCLUDE_PATTERNS = [
        "runtime",  # Runtime data (logs, metrics, analysis)
        "__pycache__",  # Python cache
        "*.pyc",
        "*.pyo",
        "*~",  # Temp files
        ".DS_Store",
        "*.swp",
        "*.swo",
    ]

    def __init__(self):
        self.repo_root = Path(__file__).parent
        self.pkg_dest = self.repo_root / "src" / "amplihack"

        # Main directories to copy: (source_relative, dest_relative)
        self.copy_dirs = [
            (".claude", ".claude"),
            ("amplifier-bundle", "amplifier-bundle"),
        ]

        # Extra copies for path resolution workarounds
        # These are copied AFTER main directories to overlay into amplifier-bundle
        self.extra_copies = [
            # Skills copied into bundle so tool-skills can find them via .claude/skills
            # (the launcher copies to cwd/.claude/skills at runtime)
            (".claude/skills", "amplifier-bundle/skills"),
            (".claude/recipes", "amplifier-bundle/recipes-claude"),
        ]

    def _validate_structure(self) -> None:
        """Validate that the expected repository structure exists.

        Raises:
            BuildValidationError: If required directories or files are missing.
        """
        errors = []

        # Check required directories
        for dir_path in self.REQUIRED_DIRS:
            full_path = self.repo_root / dir_path
            if not full_path.is_dir():
                errors.append(f"Required directory missing: {dir_path}/")

        # Check required files
        for file_path in self.REQUIRED_FILES:
            full_path = self.repo_root / file_path
            if not full_path.is_file():
                errors.append(f"Required file missing: {file_path}")

        # Check package destination exists
        if not self.pkg_dest.is_dir():
            errors.append(f"Package directory missing: {self.pkg_dest}")

        if errors:
            error_msg = "Build validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            error_msg += "\n\nSee build_hooks.py docstring for expected structure."
            raise BuildValidationError(error_msg)

        print("✓ Repository structure validated")

    def _verify_copy(self, dest_path: Path, min_files: int = 1) -> None:
        """Verify that a copy operation resulted in expected content.

        Args:
            dest_path: The destination directory to verify
            min_files: Minimum number of files expected (recursive)

        Raises:
            BuildValidationError: If verification fails
        """
        if not dest_path.exists():
            raise BuildValidationError(f"Copy verification failed: {dest_path} does not exist")

        file_count = sum(1 for _ in dest_path.rglob("*") if _.is_file())
        if file_count < min_files:
            raise BuildValidationError(
                f"Copy verification failed: {dest_path} has {file_count} files, expected >= {min_files}"
            )

    def _copy_directories(self) -> None:
        """Copy directories from repo root to src/amplihack/.

        Validates structure first, then copies with verification.
        """
        self._validate_structure()

        ignore_func = shutil.ignore_patterns(*self.EXCLUDE_PATTERNS)

        # Copy main directories
        for src_name, dest_name in self.copy_dirs:
            src_path = self.repo_root / src_name
            dest_path = self.pkg_dest / dest_name

            if not src_path.exists():
                print(f"⚠ Warning: {src_name}/ not found, skipping")
                continue

            # Remove existing to ensure clean copy
            if dest_path.exists():
                print(f"  Removing existing {dest_name}/")
                shutil.rmtree(dest_path)

            # Copy
            print(f"  Copying {src_name}/ -> {dest_name}/")
            shutil.copytree(src_path, dest_path, ignore=ignore_func)

            # Verify
            self._verify_copy(dest_path, min_files=5)
            print(f"  ✓ Verified {dest_name}/")

        # Handle extra copies (overlays)
        for src_name, dest_name in self.extra_copies:
            src_path = self.repo_root / src_name
            dest_path = self.pkg_dest / dest_name

            if not src_path.exists():
                print(f"⚠ Warning: {src_name}/ not found, skipping extra copy")
                continue

            if dest_path.exists():
                shutil.rmtree(dest_path)

            print(f"  Copying {src_name}/ -> {dest_name}/ (overlay)")
            shutil.copytree(src_path, dest_path, ignore=ignore_func)
            print(f"  ✓ Copied {src_name}/")

    def _cleanup_directories(self) -> None:
        """Remove copied directories from package after build."""
        for _, dest_name in self.copy_dirs:
            dest_path = self.pkg_dest / dest_name
            if dest_path.exists():
                print(f"  Cleaning up {dest_name}/")
                shutil.rmtree(dest_path)

        for _, dest_name in self.extra_copies:
            dest_path = self.pkg_dest / dest_name
            if dest_path.exists():
                print(f"  Cleaning up {dest_name}/")
                shutil.rmtree(dest_path)

    def build_wheel(self, wheel_directory, config_settings=None, metadata_directory=None):
        """Build wheel with .claude/ and amplifier-bundle/ directories included."""
        print("=" * 60)
        print("Amplihack Build: Preparing wheel with framework files")
        print("=" * 60)

        try:
            self._copy_directories()
            print("\n  Building wheel...")
            result = _orig.build_wheel(
                wheel_directory,
                config_settings=config_settings,
                metadata_directory=metadata_directory,
            )
            print(f"  ✓ Wheel built: {result}")
            return result
        except BuildValidationError as e:
            print(f"\n❌ BUILD FAILED: {e}", file=sys.stderr)
            raise
        finally:
            print("\n  Cleaning up temporary copies...")
            self._cleanup_directories()
            print("=" * 60)

    def build_sdist(self, sdist_directory, config_settings=None):
        """Build sdist (MANIFEST.in handles .claude/ for sdist)."""
        return _orig.build_sdist(sdist_directory, config_settings=config_settings)


# Create singleton instance
_backend = _CustomBuildBackend()

# Expose the build functions
build_wheel = _backend.build_wheel
build_sdist = _backend.build_sdist
