"""Tests for staging_safety module.

Tests all safety check branches with temporary directories.
"""

import importlib
import subprocess
import tempfile
from pathlib import Path

import pytest

from amplihack.staging_safety import DirectorySafetyCheck, is_safe_to_delete


class TestDirectorySafetyCheck:
    """Tests for DirectorySafetyCheck dataclass."""

    def test_safety_check_initialization(self):
        """Test DirectorySafetyCheck initialization."""
        check = DirectorySafetyCheck(status="safe", reason="Test reason", custom_skills=["skill1"])
        assert check.status == "safe"
        assert check.reason == "Test reason"
        assert check.custom_skills == ["skill1"]

    def test_safety_check_default_custom_skills(self):
        """Test that custom_skills defaults to empty list."""
        check = DirectorySafetyCheck(status="safe", reason="Test")
        assert check.custom_skills == []


class TestIsSafeToDeleteNonExistent:
    """Tests for is_safe_to_delete with non-existent directories."""

    def test_nonexistent_directory_returns_uncertain(self):
        """Test that non-existent directory returns uncertain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "does-not-exist"
            result = is_safe_to_delete(nonexistent)

            assert result.status == "uncertain"
            assert "does not exist" in result.reason.lower()
            assert result.custom_skills == []


class TestIsSafeToDeleteSymlinks:
    """Tests for is_safe_to_delete with symlinks."""

    def test_symlink_returns_unsafe(self):
        """Test that symlinked directory returns unsafe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            target = tmppath / "target"
            target.mkdir()
            symlink = tmppath / "symlink"
            symlink.symlink_to(target)

            result = is_safe_to_delete(symlink)

            assert result.status == "unsafe"
            assert "symlink" in result.reason.lower()
            assert result.custom_skills == []


class TestIsSafeToDeletePermissions:
    """Tests for is_safe_to_delete with permission issues."""

    @pytest.mark.skipif(not hasattr(Path, "chmod"), reason="chmod not available on this platform")
    def test_unreadable_directory_returns_uncertain(self):
        """Test that unreadable directory returns uncertain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            unreadable = tmppath / "unreadable"
            unreadable.mkdir()

            # Make directory unreadable (remove read permission)
            try:
                unreadable.chmod(0o000)
                result = is_safe_to_delete(unreadable)

                assert result.status == "uncertain"
                assert "cannot read" in result.reason.lower()
                assert result.custom_skills == []
            finally:
                # Restore permissions for cleanup
                unreadable.chmod(0o755)


class TestIsSafeToDeleteGitRepository:
    """Tests for is_safe_to_delete with git repositories."""

    def test_git_repository_returns_unsafe(self):
        """Test that directory with .git returns unsafe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            git_dir = tmppath / ".git"
            git_dir.mkdir()

            result = is_safe_to_delete(tmppath)

            assert result.status == "unsafe"
            assert "git repository" in result.reason.lower()
            assert result.custom_skills == []


class TestIsSafeToDeleteHiddenFiles:
    """Tests for is_safe_to_delete with hidden files."""

    def test_gitkeep_is_safe(self):
        """Test that .gitkeep file is considered safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            gitkeep = tmppath / ".gitkeep"
            gitkeep.touch()

            result = is_safe_to_delete(tmppath)

            # Empty directory with only .gitkeep should be safe
            assert result.status == "safe"
            assert "only amplihack-managed" in result.reason.lower()

    def test_other_hidden_file_returns_unsafe(self):
        """Test that other hidden files return unsafe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            hidden = tmppath / ".hidden"
            hidden.touch()

            result = is_safe_to_delete(tmppath)

            assert result.status == "unsafe"
            assert "hidden file" in result.reason.lower()
            assert ".hidden" in result.reason

    def test_multiple_hidden_files_returns_unsafe(self):
        """Test that multiple hidden files return unsafe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".hidden1").touch()
            (tmppath / ".hidden2").touch()

            result = is_safe_to_delete(tmppath)

            assert result.status == "unsafe"
            assert "hidden file" in result.reason.lower()


class TestIsSafeToDeleteNonDirectoryFiles:
    """Tests for is_safe_to_delete with non-directory files."""

    def test_regular_file_returns_unsafe(self):
        """Test that regular file in root returns unsafe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            regular_file = tmppath / "README.md"
            regular_file.touch()

            result = is_safe_to_delete(tmppath)

            assert result.status == "unsafe"
            assert "non-directory file" in result.reason.lower()
            assert "README.md" in result.reason


class TestIsSafeToDeleteCustomSkills:
    """Tests for is_safe_to_delete with custom skills."""

    def test_single_custom_skill_returns_unsafe(self):
        """Test that single custom skill returns unsafe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            custom = tmppath / "my-custom-skill"
            custom.mkdir()

            result = is_safe_to_delete(tmppath)

            assert result.status == "unsafe"
            assert "custom skills" in result.reason.lower()
            assert result.custom_skills == ["my-custom-skill"]

    def test_multiple_custom_skills_returns_unsafe(self):
        """Test that multiple custom skills are all reported."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "custom1").mkdir()
            (tmppath / "custom2").mkdir()
            (tmppath / "custom3").mkdir()

            result = is_safe_to_delete(tmppath)

            assert result.status == "unsafe"
            assert "custom skills" in result.reason.lower()
            assert set(result.custom_skills) == {"custom1", "custom2", "custom3"}

    def test_mixed_custom_and_amplihack_returns_unsafe(self):
        """Test that mix of custom and amplihack skills returns unsafe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Amplihack skills
            (tmppath / "claude-agent-sdk").mkdir()
            (tmppath / "common").mkdir()
            # Custom skill
            (tmppath / "my-custom").mkdir()

            result = is_safe_to_delete(tmppath)

            assert result.status == "unsafe"
            assert "custom skills" in result.reason.lower()
            assert result.custom_skills == ["my-custom"]


class TestIsSafeToDeleteAmplihackSkills:
    """Tests for is_safe_to_delete with only amplihack skills."""

    def test_single_amplihack_skill_returns_safe(self):
        """Test that single amplihack skill returns safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "claude-agent-sdk").mkdir()

            result = is_safe_to_delete(tmppath)

            assert result.status == "safe"
            assert "only amplihack-managed" in result.reason.lower()
            assert result.custom_skills == []

    def test_multiple_amplihack_skills_returns_safe(self):
        """Test that multiple amplihack skills returns safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "claude-agent-sdk").mkdir()
            (tmppath / "common").mkdir()
            (tmppath / "default-workflow").mkdir()

            result = is_safe_to_delete(tmppath)

            assert result.status == "safe"
            assert "only amplihack-managed" in result.reason.lower()
            assert result.custom_skills == []

    def test_all_amplihack_skills_returns_safe(self):
        """Test that directory with many amplihack skills returns safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create subset of known skills
            known_skills = [
                "claude-agent-sdk",
                "common",
                "development",
                "collaboration",
                "quality",
                "default-workflow",
                "cascade-workflow",
            ]
            for skill in known_skills:
                (tmppath / skill).mkdir()

            result = is_safe_to_delete(tmppath)

            assert result.status == "safe"
            assert "only amplihack-managed" in result.reason.lower()
            assert result.custom_skills == []

    def test_empty_directory_returns_safe(self):
        """Test that empty directory returns safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            result = is_safe_to_delete(tmppath)

            assert result.status == "safe"
            assert "only amplihack-managed" in result.reason.lower()
            assert result.custom_skills == []

    def test_amplihack_skills_with_gitkeep_returns_safe(self):
        """Test that amplihack skills with .gitkeep returns safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "claude-agent-sdk").mkdir()
            (tmppath / "common").mkdir()
            (tmppath / ".gitkeep").touch()

            result = is_safe_to_delete(tmppath)

            assert result.status == "safe"
            assert "only amplihack-managed" in result.reason.lower()
            assert result.custom_skills == []


class TestIsSafeToDeleteEdgeCases:
    """Tests for edge cases in is_safe_to_delete."""

    def test_nested_directories_not_checked(self):
        """Test that safety check only looks at immediate children."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            skill_dir = tmppath / "claude-agent-sdk"
            skill_dir.mkdir()
            # Create nested custom directory (should not be checked)
            (skill_dir / "custom-nested").mkdir()

            result = is_safe_to_delete(tmppath)

            # Should be safe - we only check immediate children
            assert result.status == "safe"
            assert result.custom_skills == []

    def test_skill_names_with_special_chars(self):
        """Test that skill names with special characters are handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Names that should be considered custom (not in registry)
            (tmppath / "skill_with_underscores").mkdir()

            result = is_safe_to_delete(tmppath)

            assert result.status == "unsafe"
            assert "skill_with_underscores" in result.custom_skills

    def test_case_sensitive_skill_matching(self):
        """Test that skill matching is case-sensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Wrong case - should be considered custom
            (tmppath / "Agent-SDK").mkdir()

            result = is_safe_to_delete(tmppath)

            assert result.status == "unsafe"
            assert "Agent-SDK" in result.custom_skills


class TestIsSafeToDeleteSecurityChecks:
    """Tests for security-related checks in is_safe_to_delete."""

    def test_prevents_deletion_of_user_customized_directory(self):
        """Test that directories with user customizations are protected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Amplihack skills
            (tmppath / "claude-agent-sdk").mkdir()
            # User's custom skill
            (tmppath / "my-custom-agent").mkdir()

            result = is_safe_to_delete(tmppath)

            assert result.status == "unsafe"
            assert "my-custom-agent" in result.custom_skills

    def test_prevents_deletion_of_git_tracked_directory(self):
        """Test that git repositories are protected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / ".git").mkdir()
            (tmppath / "claude-agent-sdk").mkdir()

            result = is_safe_to_delete(tmppath)

            assert result.status == "unsafe"
            assert "git repository" in result.reason.lower()

    def test_prevents_deletion_through_symlink(self):
        """Test that symlinks are not followed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            target = tmppath / "target"
            target.mkdir()
            symlink = tmppath / "link"
            symlink.symlink_to(target)

            result = is_safe_to_delete(symlink)

            assert result.status == "unsafe"
            assert "symlink" in result.reason.lower()


def _require_staging_safety_attr(attr_name: str):
    module = importlib.import_module("amplihack.staging_safety")
    assert hasattr(module, attr_name), f"amplihack.staging_safety must define {attr_name}"
    return getattr(module, attr_name)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "tests@example.com")
    _git(tmp_path, "config", "user.name", "Recovery Tests")
    return tmp_path


class TestRecoveryStageGuards:
    """Tests for the Stage 1/2 staging guardrails added to staging_safety.py."""

    def test_capture_protected_staged_files_returns_relative_paths(self, git_repo: Path):
        """Stage 1 must snapshot the unrelated staged set before any mutation."""
        capture_protected_staged_files = _require_staging_safety_attr(
            "capture_protected_staged_files"
        )

        (git_repo / "docs").mkdir()
        (git_repo / "src" / "amplihack" / "launcher").mkdir(parents=True)
        (git_repo / "docs" / "index.md").write_text("docs")
        (git_repo / "src" / "amplihack" / "launcher" / "core.py").write_text("print('x')\n")
        (git_repo / "notes.txt").write_text("unstaged\n")

        _git(git_repo, "add", "docs/index.md", "src/amplihack/launcher/core.py")

        protected = capture_protected_staged_files(git_repo)

        assert protected == [
            "docs/index.md",
            "src/amplihack/launcher/core.py",
        ]

    def test_validate_fix_batch_rejects_repo_wide_staging_on_dirty_tree(self, git_repo: Path):
        """Recovery must ban repo-wide staging in a dirty main worktree."""
        validate_fix_batch = _require_staging_safety_attr("validate_fix_batch")

        (git_repo / "docs").mkdir()
        (git_repo / "docs" / "index.md").write_text("protected\n")
        (git_repo / "scratch.py").write_text("print('dirty tree')\n")
        _git(git_repo, "add", "docs/index.md")

        with pytest.raises(ValueError, match="repo-wide staging"):
            validate_fix_batch(
                repo_path=git_repo,
                candidate_paths=["."],
                protected_staged_files=["docs/index.md"],
            )

    def test_validate_fix_batch_rejects_overlap_with_protected_staged_files(self, git_repo: Path):
        """Stage 2 fixes must stay outside the protected staged set."""
        validate_fix_batch = _require_staging_safety_attr("validate_fix_batch")

        (git_repo / "docs").mkdir()
        (git_repo / "docs" / "index.md").write_text("protected\n")
        _git(git_repo, "add", "docs/index.md")

        with pytest.raises(ValueError, match="protected staged"):
            validate_fix_batch(
                repo_path=git_repo,
                candidate_paths=["docs/index.md"],
                protected_staged_files=["docs/index.md"],
            )

    def test_require_isolated_worktree_for_commit_capable_steps(self, git_repo: Path):
        """Stage 3 FIX+VERIFY must refuse to mutate the dirty main worktree."""
        require_isolated_worktree = _require_staging_safety_attr("require_isolated_worktree")

        with pytest.raises(ValueError, match="isolated worktree"):
            require_isolated_worktree(
                stage_name="FIX+VERIFY", repo_path=git_repo, worktree_path=None
            )

    def test_require_isolated_worktree_accepts_registered_git_worktree(self, git_repo: Path):
        """Registered git worktrees are valid mutation targets."""
        require_isolated_worktree = _require_staging_safety_attr("require_isolated_worktree")
        (git_repo / "README.md").write_text("hello\n")
        _git(git_repo, "add", "README.md")
        _git(git_repo, "commit", "-m", "init")
        worktree_path = git_repo.parent / "worktree"
        _git(git_repo, "worktree", "add", str(worktree_path), "HEAD")

        resolved = require_isolated_worktree(
            stage_name="FIX+VERIFY",
            repo_path=git_repo,
            worktree_path=worktree_path,
        )

        assert resolved == worktree_path.resolve()
