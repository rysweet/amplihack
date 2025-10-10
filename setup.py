"""
Custom setup.py to handle framework files packaging.

This implements Option A: Dual-location strategy
- Framework files (.claude/, CLAUDE.md, docs, examples, Specs) live at repo root
- Custom build command copies framework files into package during wheel build
- Ensures both local and UVX scenarios work correctly with all framework files
"""

import shutil
from pathlib import Path

from setuptools import setup  # type: ignore
from setuptools.command.build_py import build_py  # type: ignore


class BuildPyWithClaude(build_py):
    """Custom build command that copies framework files into the package."""

    def run(self):
        """Run the standard build, then copy framework files."""
        # Run standard build first
        super().run()

        # Define framework files/directories to copy
        repo_root = Path(__file__).parent
        build_lib = Path(self.build_lib)
        package_dir = build_lib / "amplihack"

        framework_items = [
            (".claude", ".claude"),
            ("CLAUDE.md", "CLAUDE.md"),
            ("docs", "docs"),
            ("examples", "examples"),
            ("Specs", "Specs"),
        ]

        # Copy each framework item
        for src_name, dest_name in framework_items:
            src_path = repo_root / src_name
            dest_path = package_dir / dest_name

            if not src_path.exists():
                print(f"Warning: {src_name} not found at {src_path}")
                continue

            # Remove existing destination if present
            if dest_path.exists():
                if dest_path.is_dir():
                    shutil.rmtree(dest_path)
                else:
                    dest_path.unlink()

            # Copy file or directory
            if src_path.is_dir():
                print(f"Copying {src_name}/ from {src_path} to {dest_path}")
                shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
            else:
                print(f"Copying {src_name} from {src_path} to {dest_path}")
                shutil.copy2(src_path, dest_path)


if __name__ == "__main__":
    setup(
        cmdclass={
            "build_py": BuildPyWithClaude,
        }
    )
