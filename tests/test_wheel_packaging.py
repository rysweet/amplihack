"""Test that .claude/ directory is included in wheel builds.

This test verifies that the custom build backend (build_hooks.py) correctly
copies the .claude/ directory into the package before building the wheel,
ensuring it's available in UVX deployments.
"""

import subprocess
import tempfile
import zipfile
from pathlib import Path

import pytest


def test_wheel_includes_claude_directory():
    """Test that building a wheel includes the .claude/ directory."""
    # Build wheel in temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        wheel_dir = Path(tmpdir)

        # Build wheel using pyproject-build
        result = subprocess.run(
            ["python", "-m", "build", "--wheel", "--outdir", str(wheel_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        # Check build succeeded
        if result.returncode != 0:
            pytest.fail(f"Wheel build failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")

        # Find the built wheel
        wheels = list(wheel_dir.glob("*.whl"))
        assert len(wheels) == 1, f"Expected 1 wheel, found {len(wheels)}"
        wheel_path = wheels[0]

        # Inspect wheel contents
        with zipfile.ZipFile(wheel_path, "r") as zf:
            file_list = zf.namelist()

            # Verify .claude/ directory is included
            claude_files = [f for f in file_list if "amplihack/.claude/" in f]
            assert len(claude_files) > 100, (
                f"Expected > 100 .claude/ files, found {len(claude_files)}"
            )

            # Verify key files are present
            required_files = [
                "amplihack/.claude/.version",
                "amplihack/.claude/settings.json",
                "amplihack/.claude/__init__.py",
            ]

            for required_file in required_files:
                assert required_file in file_list, (
                    f"Required file {required_file} not found in wheel"
                )

            # Verify subdirectories are present
            required_dirs = [
                "amplihack/.claude/agents/",
                "amplihack/.claude/commands/",
                "amplihack/.claude/context/",
                "amplihack/.claude/skills/",
                "amplihack/.claude/workflows/",
            ]

            for required_dir in required_dirs:
                dir_files = [f for f in file_list if f.startswith(required_dir)]
                assert len(dir_files) > 0, (
                    f"No files found in {required_dir} (expected subdirectory)"
                )

            # Verify runtime directory is excluded (as per build_hooks.py ignore patterns)
            runtime_files = [f for f in file_list if "amplihack/.claude/runtime/" in f]
            assert len(runtime_files) == 0, (
                f"runtime/ should be excluded, but found {len(runtime_files)} files"
            )


def test_build_hooks_cleanup():
    """Test that build_hooks.py cleans up .claude/ from src/amplihack/ after build."""
    # Path to .claude/ inside package (should not exist after build)
    package_claude = Path(__file__).parent.parent / "src" / "amplihack" / ".claude"

    # Verify cleanup happened
    assert not package_claude.exists(), (
        f"{package_claude} should not exist after build (build_hooks.py should clean it up)"
    )


def test_claude_directory_exists_at_repo_root():
    """Test that .claude/ exists at repository root (source of truth)."""
    repo_root = Path(__file__).parent.parent
    claude_root = repo_root / ".claude"

    assert claude_root.exists(), f".claude/ not found at {claude_root}"
    assert claude_root.is_dir(), f"{claude_root} is not a directory"

    # Verify key subdirectories
    required_subdirs = ["agents", "commands", "context", "skills", "tools", "workflow"]
    for subdir in required_subdirs:
        subdir_path = claude_root / subdir
        assert subdir_path.exists(), f"Required subdirectory {subdir} not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
