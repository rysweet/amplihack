"""Test that CLAUDE.md is properly installed to ~/.amplihack/"""

import os
from pathlib import Path


def test_claude_md_exists_in_amplihack():
    """Verify CLAUDE.md is present in ~/.amplihack/ after installation."""
    claude_md_path = Path.home() / ".amplihack" / "CLAUDE.md"
    
    assert claude_md_path.exists(), (
        f"CLAUDE.md not found at {claude_md_path}. "
        "This file is required for hooks to detect project root. "
        "Check build_hooks.py to ensure CLAUDE.md is copied to the package."
    )
    
    # Verify it's readable and not empty
    assert claude_md_path.is_file(), f"{claude_md_path} exists but is not a file"
    
    content = claude_md_path.read_text(encoding="utf-8")
    assert len(content) > 0, f"CLAUDE.md at {claude_md_path} is empty"
    assert "amplihack" in content.lower(), "CLAUDE.md should contain amplihack documentation"


def test_claude_dir_exists_in_amplihack():
    """Verify .claude/ directory exists in ~/.amplihack/"""
    claude_dir = Path.home() / ".amplihack" / ".claude"
    
    assert claude_dir.exists(), f".claude directory not found at {claude_dir}"
    assert claude_dir.is_dir(), f"{claude_dir} exists but is not a directory"


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


if __name__ == "__main__":
    # Allow running directly for quick checks
    test_claude_md_exists_in_amplihack()
    test_claude_dir_exists_in_amplihack()
    test_hooks_can_find_project_root()
    print("✅ All CLAUDE.md installation tests passed")
