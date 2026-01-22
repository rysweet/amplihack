#!/usr/bin/env python3
"""Test that memory-manager agent is properly removed from codebase.

This test ensures the memory-manager agent (specification document) is
completely removed while memory functionality remains intact.
"""

import subprocess
from pathlib import Path


def test_memory_manager_files_deleted():
    """Verify all 5 memory-manager.md files are deleted."""
    repo_root = Path(__file__).parent.parent

    expected_removed = [
        ".claude/agents/amplihack/specialized/memory-manager.md",
        "amplifier-bundle/agents/specialized/memory-manager.md",
        "docs/claude/agents/amplihack/specialized/memory-manager.md",
        "src/amplihack/.claude/agents/amplihack/specialized/memory-manager.md",
        "src/amplihack/amplifier-bundle/agents/specialized/memory-manager.md",
    ]

    for file_path in expected_removed:
        full_path = repo_root / file_path
        assert not full_path.exists(), f"File should be deleted: {file_path}"


def test_bundle_registration_removed():
    """Verify bundle.md no longer references memory-manager."""
    repo_root = Path(__file__).parent.parent
    bundle_file = repo_root / "amplifier-bundle/bundle.md"

    assert bundle_file.exists(), "bundle.md should exist"
    content = bundle_file.read_text()

    # Should NOT contain memory-manager registration
    assert "amplihack:memory-manager:" not in content, \
        "bundle.md should not contain memory-manager registration"
    assert "agents/specialized/memory-manager.md" not in content, \
        "bundle.md should not reference memory-manager.md"


def test_agent_performance_skill_updated():
    """Verify agent-performance skill shows correct count (24 not 25)."""
    repo_root = Path(__file__).parent.parent
    skill_file = repo_root / ".claude/skills/agent-performance/SKILL.md"

    assert skill_file.exists(), "agent-performance SKILL.md should exist"
    content = skill_file.read_text()

    # Should NOT contain memory-manager in agent list
    assert "memory-manager" not in content.lower(), \
        "SKILL.md should not list memory-manager"

    # Should show 24 specialized agents (was 25)
    assert "24" in content or "twenty-four" in content.lower(), \
        "SKILL.md should show 24 specialized agents (not 25)"


def test_readme_agent_table_updated():
    """Verify README.md agent table doesn't include memory-manager."""
    repo_root = Path(__file__).parent.parent
    readme_file = repo_root / "README.md"

    assert readme_file.exists(), "README.md should exist"
    content = readme_file.read_text()

    # Should NOT contain memory-manager row in agent table
    # Looking for the pattern: | [**memory-manager**]
    assert "[**memory-manager**]" not in content, \
        "README.md should not have memory-manager in agent table"


def test_memory_hook_still_exists():
    """Verify memory hook implementation is intact (critical path)."""
    repo_root = Path(__file__).parent.parent
    memory_hook = repo_root / ".claude/tools/amplihack/hooks/agent_memory_hook.py"

    # File should exist
    assert memory_hook.exists(), \
        "agent_memory_hook.py should still exist (actual memory implementation)"

    # Should contain core memory functionality
    content = memory_hook.read_text()
    assert "def detect_agent_references" in content, \
        "Memory hook should contain detect_agent_references function"
    assert "def inject_memory_for_agents" in content or "MemoryCoordinator" in content, \
        "Memory hook should contain memory injection functionality"


def test_no_code_references_memory_manager():
    """Verify no code invokes amplihack:memory-manager agent."""
    repo_root = Path(__file__).parent.parent

    # Search for any code references (excluding test files and archives)
    result = subprocess.run(
        ["git", "grep", "-l", "amplihack:memory-manager",
         "--", "*.py", "*.yaml", "*.json", "*.md",
         ":!tests/test_memory_manager_removed.py",
         ":!*.backup.*"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )

    # Should find no matches (exit code 1 means no matches in git grep)
    assert result.returncode == 1, \
        f"Found code references to amplihack:memory-manager:\n{result.stdout}"


if __name__ == "__main__":
    # Run tests standalone for quick verification
    import sys

    tests = [
        test_memory_manager_files_deleted,
        test_bundle_registration_removed,
        test_agent_performance_skill_updated,
        test_readme_agent_table_updated,
        test_memory_hook_still_exists,
        test_no_code_references_memory_manager,
    ]

    failed = []
    for test_func in tests:
        try:
            test_func()
            print(f"✓ {test_func.__name__}")
        except AssertionError as e:
            print(f"✗ {test_func.__name__}: {e}")
            failed.append(test_func.__name__)

    if failed:
        print(f"\n{len(failed)} test(s) failed")
        sys.exit(1)
    else:
        print(f"\nAll {len(tests)} tests passed!")
        sys.exit(0)
