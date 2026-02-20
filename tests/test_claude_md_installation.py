"""Test that CLAUDE.md is properly installed and hooks can find project root.

These are integration tests that verify the installed state of ~/.amplihack/.
They require a prior `amplihack launch` or equivalent installation.
Run with: pytest tests/test_claude_md_installation.py -m integration
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


# --- Integration tests (require installation) ---


@pytest.mark.integration
def test_claude_md_exists_in_amplihack():
    """Verify CLAUDE.md is present in ~/.amplihack/ after installation."""
    claude_md_path = Path.home() / ".amplihack" / "CLAUDE.md"

    assert claude_md_path.exists(), (
        f"CLAUDE.md not found at {claude_md_path}. "
        "This file is required for hooks to detect project root. "
        "Check build_hooks.py to ensure CLAUDE.md is copied to the package."
    )

    assert claude_md_path.is_file(), f"{claude_md_path} exists but is not a file"

    content = claude_md_path.read_text(encoding="utf-8")
    assert len(content) > 0, f"CLAUDE.md at {claude_md_path} is empty"


@pytest.mark.integration
def test_claude_dir_exists_in_amplihack():
    """Verify .claude/ directory exists in ~/.amplihack/"""
    claude_dir = Path.home() / ".amplihack" / ".claude"

    assert claude_dir.exists(), f".claude directory not found at {claude_dir}"
    assert claude_dir.is_dir(), f"{claude_dir} exists but is not a directory"


@pytest.mark.integration
def test_hooks_can_find_project_root():
    """Verify hooks can find project root by checking for .claude and CLAUDE.md"""
    amplihack_root = Path.home() / ".amplihack"
    claude_dir = amplihack_root / ".claude"
    claude_md = amplihack_root / "CLAUDE.md"

    # This is the exact check hooks perform (from pre_tool_use.py line 20)
    has_claude_dir = claude_dir.exists()
    has_claude_md = claude_md.exists()

    assert has_claude_dir and has_claude_md, (
        f"Hooks require BOTH .claude/ and CLAUDE.md in {amplihack_root}. "
        f"Found: .claude/={has_claude_dir}, CLAUDE.md={has_claude_md}"
    )


# --- Unit tests (no installation required) ---


def test_build_hooks_copies_claude_md():
    """Verify build_hooks.py _CustomBuildBackend has CLAUDE.md paths configured."""
    import importlib
    import sys

    # Find build_hooks.py relative to this test
    repo_root = Path(__file__).parent.parent
    build_hooks_path = repo_root / "build_hooks.py"

    if not build_hooks_path.exists():
        pytest.skip("build_hooks.py not found (not running from repo root)")

    # Import build_hooks module
    spec = importlib.util.spec_from_file_location("build_hooks", build_hooks_path)
    mod = importlib.util.module_from_spec(spec)

    # The module imports setuptools which may not be available
    try:
        spec.loader.exec_module(mod)
    except ImportError:
        pytest.skip("setuptools not available")

    backend = mod._CustomBuildBackend()

    # Verify CLAUDE.md source and dest paths are configured
    assert hasattr(backend, "claude_md_src"), "Missing claude_md_src attribute"
    assert hasattr(backend, "claude_md_dest"), "Missing claude_md_dest attribute"
    assert backend.claude_md_src.name == "CLAUDE.md"
    assert backend.claude_md_dest.name == "CLAUDE.md"


def test_hook_project_root_detection_logic():
    """Verify the project root detection pattern works with .claude + CLAUDE.md."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_root = Path(tmpdir) / "fake_amplihack"
        fake_root.mkdir()

        # Without either marker: should not detect
        found = _find_project_root(fake_root)
        assert found is None

        # With only .claude: should not detect
        (fake_root / ".claude").mkdir()
        found = _find_project_root(fake_root)
        assert found is None

        # With both .claude + CLAUDE.md: should detect
        (fake_root / "CLAUDE.md").write_text("test")
        found = _find_project_root(fake_root)
        assert found == fake_root


def _find_project_root(start: Path) -> Path | None:
    """Replicate the hook project root detection logic."""
    current = start
    for _ in range(10):
        if (current / ".claude").exists() and (current / "CLAUDE.md").exists():
            return current
        if current == current.parent:
            break
        current = current.parent
    return None


if __name__ == "__main__":
    test_claude_md_exists_in_amplihack()
    test_claude_dir_exists_in_amplihack()
    test_hooks_can_find_project_root()
    print("✅ All CLAUDE.md installation tests passed")
