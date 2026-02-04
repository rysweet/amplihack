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
        pkg_root = self.repo_root / "src" / "amplihack"
        self.claude_src = self.repo_root / ".claude"
        self.claude_dest = pkg_root / ".claude"
        self.plugin_src = self.repo_root / ".claude-plugin"
        self.plugin_dest = pkg_root / ".claude-plugin"
        self.github_src = self.repo_root / ".github"
        self.github_dest = pkg_root / ".github"
        self.bundle_src = self.repo_root / "amplifier-bundle"
        self.bundle_dest = pkg_root / "amplifier-bundle"
        self.amplihack_md_src = self.repo_root / "AMPLIHACK.md"
        self.amplihack_md_dest = pkg_root / "AMPLIHACK.md"
        # Plugin discoverable directories (commands, skills, agents)
        self.commands_src = self.claude_src / "commands"
        self.commands_dest = pkg_root / "commands"
        self.skills_src = self.claude_src / "skills"
        self.skills_dest = pkg_root / "skills"
        self.agents_src = self.claude_src / "agents"
        self.agents_dest = pkg_root / "agents"

    def _get_ignore_patterns(self):
        """Return common ignore patterns for directory copying."""
        return shutil.ignore_patterns(
            "runtime",
            "__pycache__",
            "*.pyc",
            "*.pyo",
            "*~",
            ".DS_Store",
            "*.swp",
            "*.swo",
        )

    def _copy_plugin_directory(self, src, dest, name):
        """Copy a plugin directory from repo root to package, removing existing copy first.

        Args:
            src: Source directory path
            dest: Destination directory path
            name: Human-readable name for logging
        """
        if not src.exists():
            print(f"Warning: {name} not found at {src}")
            return

        if dest.exists():
            print(f"Removing existing {dest}")
            shutil.rmtree(dest)

        print(f"Copying {src} -> {dest}")
        shutil.copytree(src, dest, symlinks=True, ignore=self._get_ignore_patterns())
        print(f"Successfully copied {name} to package")

    def _copy_claude_directory(self):
        """Copy .claude/ from repo root to src/amplihack/ if needed."""
        self._copy_plugin_directory(self.claude_src, self.claude_dest, ".claude/")

    def _copy_plugin_manifest(self):
        """Copy .claude-plugin/ from repo root to src/amplihack/ for wheel inclusion."""
        self._copy_plugin_directory(self.plugin_src, self.plugin_dest, ".claude-plugin/")

    def _copy_github_directory(self):
        """Copy .github/ from repo root to src/amplihack/ for Copilot CLI integration."""
        if not self.github_src.exists():
            print(f"Info: .github/ not found at {self.github_src} (optional for Copilot CLI)")
            return

        if self.github_dest.exists():
            print(f"Removing existing {self.github_dest}")
            shutil.rmtree(self.github_dest)

        print(f"Copying {self.github_src} -> {self.github_dest}")
        ignore = shutil.ignore_patterns("workflows", "__pycache__", "*.pyc", "*.pyo", "*~", ".DS_Store")
        shutil.copytree(self.github_src, self.github_dest, symlinks=True, ignore=ignore)
        print("Successfully copied .github/ to package")

    def _is_tracked_by_git(self, path):
        """Check if a path is tracked by git."""
        import subprocess
        from pathlib import Path as PathLib

        # Resolve path to prevent traversal attacks
        try:
            resolved_path = PathLib(path).resolve()
            repo_root_resolved = self.repo_root.resolve()

            # Ensure path is within repository
            if not str(resolved_path).startswith(str(repo_root_resolved)):
                print(f"Warning: Path {path} is outside repository, treating as untracked")
                return False

            # Use relative path for git command
            relative_path = resolved_path.relative_to(repo_root_resolved)

            result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(relative_path)],
                cwd=self.repo_root,
                capture_output=True,
                check=False,
            )
            return result.returncode == 0
        except (ValueError, OSError) as e:
            print(f"Warning: Failed to validate path {path}: {e}")
            return False

    def _safe_cleanup(self, path, name):
        """Remove path if it exists and is not tracked by git."""
        if path.exists():
            if self._is_tracked_by_git(path):
                print(f"Skipping cleanup of {path} (tracked by git)")
            else:
                print(f"Cleaning up {path}")
                if path.is_file():
                    path.unlink()
                else:
                    shutil.rmtree(path)

    def _cleanup_claude_directory(self):
        """Remove .claude/ from package after build."""
        self._safe_cleanup(self.claude_dest, ".claude/")

    def _cleanup_plugin_manifest(self):
        """Remove .claude-plugin/ from package after build."""
        self._safe_cleanup(self.plugin_dest, ".claude-plugin/")

    def _cleanup_github_directory(self):
        """Remove .github/ from package after build."""
        self._safe_cleanup(self.github_dest, ".github/")

    def _copy_bundle_directory(self):
        """Copy amplifier-bundle/ from repo root to src/amplihack/ if needed."""
        self._copy_plugin_directory(self.bundle_src, self.bundle_dest, "amplifier-bundle/")

    def _cleanup_bundle_directory(self):
        """Remove amplifier-bundle/ from package after build."""
        self._safe_cleanup(self.bundle_dest, "amplifier-bundle/")

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
        self._safe_cleanup(self.amplihack_md_dest, "AMPLIHACK.md")

    def _copy_plugin_discoverable_directories(self):
        """Copy commands/, skills/, agents/ from .claude/ to package root for plugin discovery.

        Plugin systems discover these directories at package root for compatibility.
        This creates dual-location structure:
        - amplihack/.claude/commands/ (source of truth)
        - amplihack/commands/ (discovery location)
        """
        self._copy_plugin_directory(self.commands_src, self.commands_dest, "commands/")
        self._copy_plugin_directory(self.skills_src, self.skills_dest, "skills/")
        self._copy_plugin_directory(self.agents_src, self.agents_dest, "agents/")

    def _cleanup_plugin_discoverable_directories(self):
        """Remove commands/, skills/, agents/ from package root after build.

        These directories are temporary copies created during build.
        The source of truth remains in .claude/ subdirectory.
        """
        self._safe_cleanup(self.commands_dest, "commands/")
        self._safe_cleanup(self.skills_dest, "skills/")
        self._safe_cleanup(self.agents_dest, "agents/")

    def build_wheel(self, wheel_directory, config_settings=None, metadata_directory=None):
        """Build wheel with .claude/, .claude-plugin/, .github/, amplifier-bundle/, and CLAUDE.md included."""
        try:
            self._copy_claude_directory()
            self._copy_plugin_manifest()
            self._copy_github_directory()
            self._copy_bundle_directory()
            self._copy_amplihack_md()
            self._copy_plugin_discoverable_directories()
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
            self._cleanup_plugin_discoverable_directories()

    def build_sdist(self, sdist_directory, config_settings=None):
        """Build sdist (MANIFEST.in handles .claude/ for sdist)."""
        return _orig.build_sdist(sdist_directory, config_settings=config_settings)


# Create singleton instance
_backend = _CustomBuildBackend()

# Expose the build functions
build_wheel = _backend.build_wheel
build_sdist = _backend.build_sdist
