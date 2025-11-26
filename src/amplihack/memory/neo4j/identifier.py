"""Codebase identification from Git metadata.

This module provides functionality for extracting and normalizing codebase
identity from Git repository information.
"""

import hashlib
import logging
import re
import subprocess
from pathlib import Path

from .models import CodebaseIdentity

# SHA hash length constants
SHA1_HEX_LENGTH = 40  # Git commit SHAs (SHA-1)
SHA256_HEX_LENGTH = 64  # Unique keys (SHA-256)

logger = logging.getLogger(__name__)


class CodebaseIdentifier:
    """Extract and normalize codebase identity from Git metadata.

    This class provides methods to identify a codebase by examining its Git
    repository information, producing a stable unique key that can be used
    to track ingestions over time.
    """

    @staticmethod
    def from_git_repo(repo_path: Path) -> CodebaseIdentity:
        """Extract codebase identity from a Git repository.

        Args:
            repo_path: Path to the Git repository

        Returns:
            CodebaseIdentity with extracted information

        Raises:
            ValueError: If repo_path is not a valid Git repository
            RuntimeError: If Git commands fail
        """
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        # Check if it's a git repository
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            raise ValueError(f"Not a Git repository: {repo_path}")

        try:
            # Get remote URL
            remote_url = CodebaseIdentifier._get_remote_url(repo_path)

            # Get current branch
            branch = CodebaseIdentifier._get_current_branch(repo_path)

            # Get current commit SHA
            commit_sha = CodebaseIdentifier._get_commit_sha(repo_path)

            # Normalize remote URL and generate unique key
            normalized_url = CodebaseIdentifier._normalize_remote_url(remote_url)
            unique_key = CodebaseIdentifier._generate_unique_key(normalized_url, branch)

            # Gather additional metadata
            metadata = {
                "repo_path": str(repo_path.resolve()),
            }

            return CodebaseIdentity(
                remote_url=normalized_url,
                branch=branch,
                commit_sha=commit_sha,
                unique_key=unique_key,
                metadata=metadata,
            )

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e.stderr}") from e

    @staticmethod
    def _get_remote_url(repo_path: Path) -> str:
        """Get Git remote URL.

        Args:
            repo_path: Path to the Git repository

        Returns:
            Remote URL string

        Raises:
            RuntimeError: If no remote is configured
        """
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        url = result.stdout.strip()
        if not url:
            raise RuntimeError("No remote URL configured for origin")

        return url

    @staticmethod
    def _get_current_branch(repo_path: Path) -> str:
        """Get current Git branch.

        Args:
            repo_path: Path to the Git repository

        Returns:
            Branch name

        Raises:
            RuntimeError: If not on a branch (detached HEAD)
        """
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        branch = result.stdout.strip()
        if branch == "HEAD":
            raise RuntimeError("Repository is in detached HEAD state")

        return branch

    @staticmethod
    def _get_commit_sha(repo_path: Path) -> str:
        """Get current commit SHA.

        Args:
            repo_path: Path to the Git repository

        Returns:
            Full commit SHA
        """
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        return result.stdout.strip()

    @staticmethod
    def _normalize_remote_url(url: str) -> str:
        """Normalize Git remote URL by removing authentication.

        This ensures that URLs with different credentials are treated as the
        same repository. Supports both HTTPS and SSH URLs.

        Args:
            url: Raw remote URL

        Returns:
            Normalized URL without authentication

        Example:
            >>> CodebaseIdentifier._normalize_remote_url("https://user:pass@github.com/org/repo.git")
            'https://github.com/org/repo.git'
            >>> CodebaseIdentifier._normalize_remote_url("git@github.com:org/repo.git")
            'git@github.com:org/repo.git'
        """
        # Remove HTTPS authentication (https://user:pass@host/path -> https://host/path)
        url = re.sub(r"https://[^@]+@", "https://", url)

        # Normalize .git suffix
        if not url.endswith(".git"):
            url = url + ".git"

        return url

    @staticmethod
    def _generate_unique_key(remote_url: str, branch: str) -> str:
        """Generate stable unique key from remote URL and branch.

        The unique key is a hash of the normalized remote URL and branch name,
        ensuring that the same codebase/branch combination always produces the
        same key.

        Args:
            remote_url: Normalized remote URL
            branch: Branch name

        Returns:
            SHA-256 hash as hex string
        """
        key_input = f"{remote_url}#{branch}".encode()
        return hashlib.sha256(key_input).hexdigest()

    @staticmethod
    def validate_identity(identity: CodebaseIdentity) -> bool:
        """Validate that a CodebaseIdentity has all required fields.

        Args:
            identity: CodebaseIdentity to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            if not identity.remote_url:
                return False
            if not identity.branch:
                return False
            if not identity.commit_sha:
                return False
            if not identity.unique_key:
                return False

            # Validate commit SHA format (40-char hex from SHA-1)
            if not re.match(rf"^[0-9a-f]{{{SHA1_HEX_LENGTH}}}$", identity.commit_sha):
                return False

            # Validate unique key format (64-char hex from SHA-256)
            if not re.match(rf"^[0-9a-f]{{{SHA256_HEX_LENGTH}}}$", identity.unique_key):
                return False

            return True

        except Exception as e:
            logger.warning(f"Identity validation failed: {e}")
            return False

    @staticmethod
    def create_manual_identity(
        remote_url: str,
        branch: str,
        commit_sha: str,
        metadata: dict[str, str] | None = None,
    ) -> CodebaseIdentity:
        """Create a CodebaseIdentity manually without Git access.

        Useful for testing or when Git is not available.

        Args:
            remote_url: Git remote URL
            branch: Branch name
            commit_sha: Commit SHA
            metadata: Optional additional metadata

        Returns:
            CodebaseIdentity instance
        """
        normalized_url = CodebaseIdentifier._normalize_remote_url(remote_url)
        unique_key = CodebaseIdentifier._generate_unique_key(normalized_url, branch)

        return CodebaseIdentity(
            remote_url=normalized_url,
            branch=branch,
            commit_sha=commit_sha,
            unique_key=unique_key,
            metadata=metadata or {},
        )
