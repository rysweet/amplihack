"""Outside-in tests for canonical hooks location (fix #2881).

Tests verify from a user's perspective that:
1. amplifier-bundle/tools/amplihack/hooks/ is a symlink (not a copy)
2. The symlink resolves to .claude/tools/amplihack/hooks/
3. Hook files are accessible via both paths
4. .claude/ is the single source of truth — editing one file affects both paths
"""

from pathlib import Path

import pytest


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("Cannot find repo root")


REPO_ROOT = _repo_root()
CANONICAL_HOOKS = REPO_ROOT / ".claude" / "tools" / "amplihack" / "hooks"
BUNDLE_HOOKS = REPO_ROOT / "amplifier-bundle" / "tools" / "amplihack" / "hooks"


class TestSymlinkStructure:
    """Verify the symlink structure is correct."""

    def test_canonical_hooks_dir_exists(self):
        assert CANONICAL_HOOKS.is_dir(), f"Canonical hooks directory missing: {CANONICAL_HOOKS}"

    def test_bundle_hooks_is_symlink(self):
        assert BUNDLE_HOOKS.is_symlink(), (
            f"{BUNDLE_HOOKS} must be a symlink, not a regular directory. "
            "amplifier-bundle/tools/amplihack/hooks/ should point to "
            ".claude/tools/amplihack/hooks/ as the canonical source."
        )

    def test_bundle_hooks_resolves_to_canonical(self):
        assert BUNDLE_HOOKS.resolve() == CANONICAL_HOOKS.resolve(), (
            f"Symlink {BUNDLE_HOOKS} must resolve to {CANONICAL_HOOKS}, "
            f"but resolved to {BUNDLE_HOOKS.resolve()}"
        )


class TestFileAccessibility:
    """Verify hook files are accessible via both canonical and bundle paths."""

    CORE_HOOKS = [
        "pre_tool_use.py",
        "session_start.py",
        "stop.py",
        "post_tool_use.py",
        "user_prompt_submit.py",
    ]

    @pytest.mark.parametrize("hook_file", CORE_HOOKS)
    def test_core_hook_accessible_via_canonical_path(self, hook_file):
        assert (CANONICAL_HOOKS / hook_file).exists(), (
            f"Core hook {hook_file} missing from canonical path {CANONICAL_HOOKS}"
        )

    @pytest.mark.parametrize("hook_file", CORE_HOOKS)
    def test_core_hook_accessible_via_bundle_path(self, hook_file):
        assert (BUNDLE_HOOKS / hook_file).exists(), (
            f"Core hook {hook_file} not accessible via bundle path {BUNDLE_HOOKS}"
        )

    def test_same_file_count_via_both_paths(self):
        canonical_files = set(f.name for f in CANONICAL_HOOKS.iterdir())
        bundle_files = set(f.name for f in BUNDLE_HOOKS.iterdir())
        assert canonical_files == bundle_files, (
            "File listings differ between canonical and bundle paths. "
            "This should not happen with a symlink."
        )


class TestSingleSourceOfTruth:
    """Verify .claude/ is the single source of truth."""

    def test_canonical_and_bundle_pre_tool_use_are_same_content(self):
        """Files accessible via both paths must have identical content (same inode via symlink)."""
        canonical = CANONICAL_HOOKS / "pre_tool_use.py"
        bundle = BUNDLE_HOOKS / "pre_tool_use.py"
        assert canonical.read_text() == bundle.read_text()

    def test_no_separate_copy_in_bundle(self):
        """amplifier-bundle/hooks must NOT be a regular directory (that would mean a copy exists)."""
        assert not (BUNDLE_HOOKS.exists() and not BUNDLE_HOOKS.is_symlink()), (
            "amplifier-bundle/tools/amplihack/hooks is a regular directory, not a symlink. "
            "It must be converted to a symlink pointing to .claude/tools/amplihack/hooks."
        )
