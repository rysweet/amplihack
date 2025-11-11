"""Tests for codebase identification."""

import subprocess
from pathlib import Path

import pytest

from amplihack.memory.neo4j.identifier import CodebaseIdentifier
from amplihack.memory.neo4j.models import CodebaseIdentity


class TestCodebaseIdentifier:
    """Test CodebaseIdentifier functionality."""

    def test_from_git_repo(self, temp_git_repo: Path):
        """Test extracting identity from Git repository."""
        identity = CodebaseIdentifier.from_git_repo(temp_git_repo)

        assert identity.remote_url == "https://github.com/test/repo.git"
        assert identity.branch == "master" or identity.branch == "main"  # Depends on git config
        assert len(identity.commit_sha) == 40
        assert len(identity.unique_key) == 64
        assert identity.metadata["repo_path"] == str(temp_git_repo.resolve())

    def test_from_git_repo_nonexistent_path(self):
        """Test error when path doesn't exist."""
        with pytest.raises(ValueError, match="does not exist"):
            CodebaseIdentifier.from_git_repo(Path("/nonexistent/path"))

    def test_from_git_repo_not_git_directory(self, tmp_path: Path):
        """Test error when path is not a Git repository."""
        with pytest.raises(ValueError, match="Not a Git repository"):
            CodebaseIdentifier.from_git_repo(tmp_path)

    def test_normalize_remote_url_with_auth(self):
        """Test normalizing URL with authentication."""
        url = "https://user:pass@github.com/test/repo.git"
        normalized = CodebaseIdentifier._normalize_remote_url(url)

        assert normalized == "https://github.com/test/repo.git"
        assert "user" not in normalized
        assert "pass" not in normalized

    def test_normalize_remote_url_without_auth(self):
        """Test normalizing URL without authentication."""
        url = "https://github.com/test/repo.git"
        normalized = CodebaseIdentifier._normalize_remote_url(url)

        assert normalized == "https://github.com/test/repo.git"

    def test_normalize_remote_url_ssh(self):
        """Test normalizing SSH URL."""
        url = "git@github.com:test/repo.git"
        normalized = CodebaseIdentifier._normalize_remote_url(url)

        assert normalized == "git@github.com:test/repo.git"

    def test_normalize_remote_url_adds_git_suffix(self):
        """Test that .git suffix is added if missing."""
        url = "https://github.com/test/repo"
        normalized = CodebaseIdentifier._normalize_remote_url(url)

        assert normalized == "https://github.com/test/repo.git"

    def test_generate_unique_key_deterministic(self):
        """Test that unique key generation is deterministic."""
        url = "https://github.com/test/repo.git"
        branch = "main"

        key1 = CodebaseIdentifier._generate_unique_key(url, branch)
        key2 = CodebaseIdentifier._generate_unique_key(url, branch)

        assert key1 == key2
        assert len(key1) == 64  # SHA-256 in hex

    def test_generate_unique_key_different_branches(self):
        """Test that different branches produce different keys."""
        url = "https://github.com/test/repo.git"

        key_main = CodebaseIdentifier._generate_unique_key(url, "main")
        key_dev = CodebaseIdentifier._generate_unique_key(url, "dev")

        assert key_main != key_dev

    def test_generate_unique_key_different_repos(self):
        """Test that different repos produce different keys."""
        branch = "main"

        key_repo1 = CodebaseIdentifier._generate_unique_key(
            "https://github.com/test/repo1.git", branch
        )
        key_repo2 = CodebaseIdentifier._generate_unique_key(
            "https://github.com/test/repo2.git", branch
        )

        assert key_repo1 != key_repo2

    def test_validate_identity_valid(self):
        """Test validating a valid identity."""
        identity = CodebaseIdentity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
            unique_key="b" * 64,
        )

        assert CodebaseIdentifier.validate_identity(identity)

    def test_validate_identity_invalid_commit_sha(self):
        """Test validating identity with invalid commit SHA."""
        identity = CodebaseIdentity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="invalid",
            unique_key="b" * 64,
        )

        assert not CodebaseIdentifier.validate_identity(identity)

    def test_validate_identity_invalid_unique_key(self):
        """Test validating identity with invalid unique key."""
        identity = CodebaseIdentity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
            unique_key="invalid",
        )

        assert not CodebaseIdentifier.validate_identity(identity)

    def test_validate_identity_missing_fields(self):
        """Test validating identity with missing fields."""
        # Create valid identity first
        identity = CodebaseIdentity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
            unique_key="b" * 64,
        )

        # Then modify to be invalid (bypassing __post_init__)
        identity.remote_url = ""
        assert not CodebaseIdentifier.validate_identity(identity)

    def test_create_manual_identity(self):
        """Test creating identity manually."""
        identity = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
        )

        assert identity.remote_url == "https://github.com/test/repo.git"
        assert identity.branch == "main"
        assert identity.commit_sha == "a" * 40
        assert len(identity.unique_key) == 64
        assert CodebaseIdentifier.validate_identity(identity)

    def test_create_manual_identity_with_metadata(self):
        """Test creating manual identity with metadata."""
        metadata = {"source": "test"}
        identity = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
            metadata=metadata,
        )

        assert identity.metadata == metadata

    def test_create_manual_identity_normalizes_url(self):
        """Test that manual identity creation normalizes URL."""
        identity = CodebaseIdentifier.create_manual_identity(
            remote_url="https://user:pass@github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
        )

        assert identity.remote_url == "https://github.com/test/repo.git"
        assert "user" not in identity.remote_url
        assert "pass" not in identity.remote_url

    def test_different_checkouts_same_repo_different_branches(self):
        """Test that different branches of same repo have different unique keys."""
        identity_main = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
        )

        identity_dev = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="dev",
            commit_sha="b" * 40,
        )

        assert identity_main.unique_key != identity_dev.unique_key

    def test_same_codebase_different_commits(self):
        """Test that same codebase with different commits has same unique key."""
        identity1 = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
        )

        identity2 = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="b" * 40,
        )

        # Same unique_key because same repo + branch
        assert identity1.unique_key == identity2.unique_key
        # But different commit SHAs
        assert identity1.commit_sha != identity2.commit_sha

    def test_get_remote_url_no_remote(self, tmp_path: Path):
        """Test error when repository has no remote."""
        repo_path = tmp_path / "no_remote"
        repo_path.mkdir()

        # Initialize repo without remote
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=repo_path, check=True, capture_output=True
        )

        # Create commit
        (repo_path / "file.txt").write_text("test")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "test"], cwd=repo_path, check=True, capture_output=True
        )

        with pytest.raises(RuntimeError):
            CodebaseIdentifier.from_git_repo(repo_path)

    def test_detached_head_state(self, temp_git_repo: Path):
        """Test error when repository is in detached HEAD state."""
        # Get current commit
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=temp_git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        commit = result.stdout.strip()

        # Detach HEAD
        subprocess.run(
            ["git", "checkout", commit], cwd=temp_git_repo, check=True, capture_output=True
        )

        with pytest.raises(RuntimeError, match="detached HEAD"):
            CodebaseIdentifier.from_git_repo(temp_git_repo)
