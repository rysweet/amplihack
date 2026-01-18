"""Build hooks for setuptools to include .claude/, .claude-plugin/, .github/, and amplifier-bundle/ in wheels.

This module provides custom build hooks that copy directories from the repository
root into src/amplihack/ before building the wheel. This ensures the framework
files, plugin manifest, and bundle files are included in the wheel distribution
for UVX deployment.

Why this is needed:
- MANIFEST.in only controls sdist, not wheels
- Wheels only include files inside Python packages
- .claude/, .claude-plugin/, .github/, and amplifier-bundle/ are at repo root (outside src/amplihack/)
- Solution: Copy them into package before build, cleanup after

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
    """Custom build backend that copies .claude/, .claude-plugin/, .github/, and amplifier-bundle/ before building."""

    def __init__(self):
        self.repo_root = Path(__file__).parent
        self.claude_src = self.repo_root / ".claude"
        self.claude_dest = self.repo_root / "src" / "amplihack" / ".claude"
        self.plugin_src = self.repo_root / ".claude-plugin"
        self.plugin_dest = self.repo_root / "src" / "amplihack" / ".claude-plugin"
        self.github_src = self.repo_root / ".github"
        self.github_dest = self.repo_root / "src" / "amplihack" / ".github"
        self.bundle_src = self.repo_root / "amplifier-bundle"
        self.bundle_dest = self.repo_root / "src" / "amplihack" / "amplifier-bundle"
        self.amplihack_md_src = self.repo_root / "AMPLIHACK.md"
        self.amplihack_md_dest = self.repo_root / "src" / "amplihack" / "AMPLIHACK.md"

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

    def _copy_plugin_manifest(self):
        """Copy .claude-plugin/ from repo root to src/amplihack/ for wheel inclusion."""
        if not self.plugin_src.exists():
            print(f"Warning: .claude-plugin/ not found at {self.plugin_src}")
            return

        # Remove existing .claude-plugin/ in package to ensure clean copy
        if self.plugin_dest.exists():
            print(f"Removing existing {self.plugin_dest}")
            shutil.rmtree(self.plugin_dest)

        # Copy .claude-plugin/ into package
        print(f"Copying {self.plugin_src} -> {self.plugin_dest}")
        shutil.copytree(self.plugin_src, self.plugin_dest)
        print("Successfully copied .claude-plugin/ to package")

    def _copy_github_directory(self):
        """Copy .github/ from repo root to src/amplihack/ for Copilot CLI integration."""
        if not self.github_src.exists():
            print(f"Info: .github/ not found at {self.github_src} (optional for Copilot CLI)")
            return

        # Remove existing .github/ in package to ensure clean copy
        if self.github_dest.exists():
            print(f"Removing existing {self.github_dest}")
            shutil.rmtree(self.github_dest)

        # Copy .github/ into package
        print(f"Copying {self.github_src} -> {self.github_dest}")
        shutil.copytree(
            self.github_src,
            self.github_dest,
            symlinks=True,  # Preserve symlinks (agents, skills point to .claude/)
            ignore=shutil.ignore_patterns(
                # Exclude CI/CD workflows (not needed in package)
                "workflows",
                # Exclude Python cache
                "__pycache__",
                "*.pyc",
                "*.pyo",
                # Exclude temp files
                "*~",
                ".DS_Store",
            ),
        )
        print("Successfully copied .github/ to package")

    def _cleanup_claude_directory(self):
        """Remove .claude/ from package after build."""
        if self.claude_dest.exists():
            print(f"Cleaning up {self.claude_dest}")
            shutil.rmtree(self.claude_dest)

    def _cleanup_plugin_manifest(self):
        """Remove .claude-plugin/ from package after build."""
        if self.plugin_dest.exists():
            print(f"Cleaning up {self.plugin_dest}")
            shutil.rmtree(self.plugin_dest)

    def _cleanup_github_directory(self):
        """Remove .github/ from package after build."""
        if self.github_dest.exists():
            print(f"Cleaning up {self.github_dest}")
            shutil.rmtree(self.github_dest)

    def _copy_bundle_directory(self):
        """Copy amplifier-bundle/ from repo root to src/amplihack/ if needed."""
        if not self.bundle_src.exists():
            print(f"Warning: amplifier-bundle/ not found at {self.bundle_src}")
            return

        # Remove existing amplifier-bundle/ in package to ensure clean copy
        if self.bundle_dest.exists():
            print(f"Removing existing {self.bundle_dest}")
            shutil.rmtree(self.bundle_dest)

        # Copy amplifier-bundle/ into package
        print(f"Copying {self.bundle_src} -> {self.bundle_dest}")
        shutil.copytree(
            self.bundle_src,
            self.bundle_dest,
            symlinks=True,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "*.pyo",
                "*~",
                ".DS_Store",
            ),
        )
        print("Successfully copied amplifier-bundle/ to package")

    def _cleanup_bundle_directory(self):
        """Remove amplifier-bundle/ from package after build."""
        if self.bundle_dest.exists():
            print(f"Cleaning up {self.bundle_dest}")
            shutil.rmtree(self.bundle_dest)

    def _copy_amplihack_md(self):
        """Copy AMPLIHACK.md from repo root to src/amplihack/ for wheel inclusion."""
        if not self.amplihack_md_src.exists():
            print(f"Warning: AMPLIHACK.md not found at {self.amplihack_md_src}")
            return

        # Copy AMPLIHACK.md into package
        print(f"Copying {self.amplihack_md_src} -> {self.amplihack_md_dest}")
        shutil.copy2(self.amplihack_md_src, self.amplihack_md_dest)
        print("Successfully copied AMPLIHACK.md to package")

    def _cleanup_amplihack_md(self):
        """Remove AMPLIHACK.md from package after build."""
        if self.amplihack_md_dest.exists():
            print(f"Cleaning up {self.amplihack_md_dest}")
            self.amplihack_md_dest.unlink()

    def build_wheel(self, wheel_directory, config_settings=None, metadata_directory=None):
        """Build wheel with .claude/, .claude-plugin/, .github/, amplifier-bundle/, and CLAUDE.md included."""
        try:
            self._copy_claude_directory()
            self._copy_plugin_manifest()
            self._copy_github_directory()
            self._copy_bundle_directory()
            self._copy_amplihack_md()
            result = _orig.build_wheel(
                wheel_directory,
                config_settings=config_settings,
                metadata_directory=metadata_directory,
            )
            return result
        finally:
            # Always cleanup, even if build fails
            self._cleanup_claude_directory()
            self._cleanup_plugin_manifest()
            self._cleanup_github_directory()
            self._cleanup_bundle_directory()
            self._cleanup_amplihack_md()

    def build_sdist(self, sdist_directory, config_settings=None):
        """Build sdist (MANIFEST.in handles .claude/ for sdist)."""
        return _orig.build_sdist(sdist_directory, config_settings=config_settings)


# Create singleton instance
_backend = _CustomBuildBackend()

# Expose the build functions
build_wheel = _backend.build_wheel
build_sdist = _backend.build_sdist
