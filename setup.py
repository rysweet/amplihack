"""
Custom setup.py to handle .claude/ directory packaging.

This implements Option A: Dual-location strategy
- .claude/ lives at repo root for local Claude Code
- Custom build command copies .claude/ into package during wheel build
- Ensures both local and UVX scenarios work correctly
"""

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPyWithClaude(build_py):
    """Custom build command that copies .claude/ into the package."""

    def run(self):
        """Run the standard build, then copy .claude/ directory."""
        # Run standard build first
        super().run()

        # Copy .claude/ from repo root to built package
        repo_root = Path(__file__).parent
        claude_src = repo_root / ".claude"

        if not claude_src.exists():
            print(f"Warning: .claude/ directory not found at {claude_src}")
            return

        # Find the build directory for our package
        build_lib = Path(self.build_lib)
        claude_dest = build_lib / "amplihack" / ".claude"

        # Copy the entire .claude/ directory
        if claude_dest.exists():
            shutil.rmtree(claude_dest)

        print(f"Copying .claude/ from {claude_src} to {claude_dest}")
        shutil.copytree(claude_src, claude_dest, dirs_exist_ok=True)

        # Ensure Python recognizes it as package data
        # by creating __init__.py files where needed
        for dirpath in claude_dest.rglob("*"):
            if dirpath.is_dir() and not (dirpath / "__init__.py").exists():
                # Don't create __init__.py in every directory, only where it makes sense
                # for Python to traverse. Most .claude/ content is data, not code.
                pass


if __name__ == "__main__":
    setup(
        cmdclass={
            "build_py": BuildPyWithClaude,
        }
    )
