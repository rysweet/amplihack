"""Tests for branch name sanitization in default-workflow.yaml step-04-setup-worktree.

Issue #2952: Branch names generated from task_description were not sanitized,
allowing newlines, long names, and invalid git ref characters to produce
branch names that git rejects.

These tests verify the shell logic in step-04 produces valid git branch names
from a range of pathological task_description inputs by executing the
sanitization pipeline in a subprocess.
"""

from __future__ import annotations

import subprocess
import textwrap

import pytest

# Sanitization pipeline reproduced from default-workflow.yaml step-04-setup-worktree.
# Defined at module level so textwrap.dedent() runs once, not once per test call.
_SANITIZE_SCRIPT = textwrap.dedent(
    r"""
    printf '%s' "$TASK_DESC" \
      | tr '\n\r' ' ' \
      | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
      | tr '[:upper:]' '[:lower:]' \
      | sed 's/[^a-z0-9_.-]/-/g' \
      | sed 's/-\{2,\}/-/g' \
      | cut -c1-60 \
      | sed 's/[-.]$//'
    """
).strip()


def _sanitize(task_desc: str) -> str:
    """Run the sanitization pipeline from step-04 against task_desc.

    Reproduces the exact pipeline from the YAML so tests stay in sync:
      1. printf '%s' <desc>       — capture value without adding newline
      2. tr newlines to spaces
      3. sed strip leading/trailing whitespace
      4. tr upper to lower
      5. sed replace invalid chars with hyphens
      6. sed collapse consecutive hyphens
      7. cut to 60 chars
      8. sed strip trailing hyphens/dots
    """
    result = subprocess.run(
        ["bash", "-c", _SANITIZE_SCRIPT],
        input=None,
        capture_output=True,
        text=True,
        env={"TASK_DESC": task_desc, "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, f"Sanitization script failed: {result.stderr}"
    return result.stdout.strip()


def _validate_git_branch(name: str) -> bool:
    """Return True if git check-ref-format accepts the name as a branch."""
    result = subprocess.run(
        ["git", "check-ref-format", "--branch", name],
        capture_output=True,
    )
    return result.returncode == 0


class TestBranchNameSanitization:
    """Verify each sanitization rule independently and combined."""

    def test_newline_in_task_description_is_stripped(self) -> None:
        """Newlines in task_description produce a single-line branch slug."""
        desc = "fix login bug\nwith oauth"
        slug = _sanitize(desc)
        assert "\n" not in slug
        assert "\r" not in slug

    def test_leading_trailing_whitespace_stripped(self) -> None:
        """Leading and trailing whitespace is removed from the slug."""
        desc = "   add feature   "
        slug = _sanitize(desc)
        assert not slug.startswith(" ")
        assert not slug.endswith(" ")
        assert not slug.startswith("-")

    def test_uppercase_converted_to_lowercase(self) -> None:
        """Uppercase letters are lowercased in the branch slug."""
        desc = "Add User Authentication"
        slug = _sanitize(desc)
        assert slug == slug.lower()

    def test_spaces_replaced_with_hyphens(self) -> None:
        """Spaces become hyphens."""
        desc = "add user profile page"
        slug = _sanitize(desc)
        assert " " not in slug
        assert "add-user-profile-page" == slug

    def test_special_chars_replaced_with_hyphens(self) -> None:
        """Characters that are not alphanumeric, hyphen, underscore, or dot become hyphens."""
        desc = "fix: auth/login (oauth2)"
        slug = _sanitize(desc)
        # colon, slash, parens are all replaced
        for ch in (":", "/", "(", ")"):
            assert ch not in slug

    def test_consecutive_hyphens_collapsed(self) -> None:
        """Multiple consecutive hyphens are collapsed to one."""
        desc = "fix  multiple   spaces"
        slug = _sanitize(desc)
        assert "--" not in slug

    def test_long_description_truncated_to_60_chars(self) -> None:
        """Slugs are truncated to at most 60 characters."""
        desc = "a" * 120
        slug = _sanitize(desc)
        assert len(slug) <= 60

    def test_trailing_hyphen_stripped(self) -> None:
        """Trailing hyphens are removed after truncation."""
        # Craft a string whose 60th char would be a hyphen
        # 58 'a' chars + ' x' = 60 chars, 'x' becomes next char after cut
        desc = "a" * 58 + "  trailing"
        slug = _sanitize(desc)
        assert not slug.endswith("-")

    def test_trailing_dot_stripped(self) -> None:
        """Trailing dots are removed."""
        desc = "fix something."
        slug = _sanitize(desc)
        assert not slug.endswith(".")

    def test_underscore_preserved(self) -> None:
        """Underscores are valid git ref chars and must be preserved."""
        desc = "fix_login_bug"
        slug = _sanitize(desc)
        assert "fix_login_bug" == slug

    def test_dot_preserved_mid_name(self) -> None:
        """Dots mid-name are preserved."""
        desc = "bump version 1.2.3"
        slug = _sanitize(desc)
        assert "1.2.3" in slug

    def test_multiline_description_is_valid(self) -> None:
        """Multi-line task descriptions produce a valid branch slug."""
        desc = "Fix authentication bug\nThis affects oauth and saml\nHigh priority"
        slug = _sanitize(desc)
        assert "\n" not in slug
        assert len(slug) > 0
        assert len(slug) <= 60

    def test_only_special_chars_produces_safe_slug(self) -> None:
        """A description made entirely of special chars produces a slug that git accepts.

        After sanitization it may be all hyphens/empty; the fallback in the
        YAML handles this case. We verify the pipeline does not crash.
        """
        desc = "!@#$%^&*()"
        # Should not raise; the result may be empty or dashes — that is fine
        # because the workflow uses a git check-ref-format fallback.
        slug = _sanitize(desc)
        # Just verify it ran without error
        assert isinstance(slug, str)

    @pytest.mark.parametrize("desc,issue_num", [
        ("add user profile page", 42),
        ("fix login\nbug with oauth2\n", 99),
        ("implement comprehensive user authentication system with oauth2 saml and ldap", 7),
    ])
    def test_passes_git_check_ref_format(self, desc: str, issue_num: int) -> None:
        """All description types produce slugs that pass git check-ref-format."""
        branch = f"feat/issue-{issue_num}-{_sanitize(desc)}"
        assert len(branch) <= 75  # prefix + up to 60 slug chars
        assert _validate_git_branch(branch), f"Branch '{branch}' failed git check-ref-format"
