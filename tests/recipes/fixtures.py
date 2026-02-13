#!/usr/bin/env python3
"""
Test fixtures for Step 1 sync verification tests.

Provides functions to create git repositories in various sync states:
- Up-to-date
- Behind (remote has new commits)
- Ahead (local has unpushed commits)
- Diverged (both have unique commits)
- No upstream tracking branch
"""

import subprocess
import tempfile
from pathlib import Path


def create_git_repo_uptodate(tmp_path: Path) -> tuple[Path, Path]:
    """
    Create git repo that is up-to-date with remote.

    Args:
        tmp_path: Temporary directory for test files

    Returns:
        (repo_path, remote_path) tuple
    """
    repo_path = tmp_path / "repo"
    remote_path = tmp_path / "remote.git"

    # Create bare remote repository with main as default branch
    remote_path.mkdir()
    subprocess.run(
        ["git", "init", "--bare", "--initial-branch=main", str(remote_path)],
        check=True,
        capture_output=True,
    )

    # Clone remote to create local repo
    subprocess.run(
        ["git", "clone", str(remote_path), str(repo_path)],
        check=True,
        capture_output=True,
    )

    # Configure git user
    _configure_git_user(repo_path)

    # Create initial commit and push
    (repo_path / "README.md").write_text("# Test Repository\n")
    subprocess.run(
        ["git", "-C", str(repo_path), "add", "."],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_path), "commit", "-m", "Initial commit"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_path), "push", "origin", "main"],
        check=True,
        capture_output=True,
    )

    return repo_path, remote_path


def create_git_repo_behind(tmp_path: Path, commits_behind: int = 1) -> tuple[Path, Path]:
    """
    Create git repo that is behind remote by N commits.

    Args:
        tmp_path: Temporary directory for test files
        commits_behind: Number of commits remote is ahead by

    Returns:
        (repo_path, remote_path) tuple
    """
    repo_path, remote_path = create_git_repo_uptodate(tmp_path)

    # Add commits directly to remote (via temp clone)
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_clone = Path(tmpdir) / "temp"
        subprocess.run(
            ["git", "clone", str(remote_path), str(temp_clone)],
            check=True,
            capture_output=True,
        )
        _configure_git_user(temp_clone)

        for i in range(commits_behind):
            (temp_clone / f"remote_file_{i}.txt").write_text(f"Remote commit {i}\n")
            subprocess.run(
                ["git", "-C", str(temp_clone), "add", "."],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(temp_clone), "commit", "-m", f"Remote commit {i}"],
                check=True,
                capture_output=True,
            )

        subprocess.run(
            ["git", "-C", str(temp_clone), "push", "origin", "main"],
            check=True,
            capture_output=True,
        )

    return repo_path, remote_path


def create_git_repo_diverged(
    tmp_path: Path, commits_ahead: int = 1, commits_behind: int = 1
) -> tuple[Path, Path]:
    """
    Create git repo that has diverged (both local and remote have unique commits).

    Args:
        tmp_path: Temporary directory for test files
        commits_ahead: Number of local unpushed commits
        commits_behind: Number of remote commits not in local

    Returns:
        (repo_path, remote_path) tuple
    """
    repo_path, remote_path = create_git_repo_uptodate(tmp_path)

    # Add local commits (ahead)
    for i in range(commits_ahead):
        (repo_path / f"local_file_{i}.txt").write_text(f"Local commit {i}\n")
        subprocess.run(
            ["git", "-C", str(repo_path), "add", "."],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_path), "commit", "-m", f"Local commit {i}"],
            check=True,
            capture_output=True,
        )

    # Add remote commits (behind) via temp clone
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_clone = Path(tmpdir) / "temp"
        subprocess.run(
            ["git", "clone", str(remote_path), str(temp_clone)],
            check=True,
            capture_output=True,
        )
        _configure_git_user(temp_clone)

        for i in range(commits_behind):
            (temp_clone / f"remote_file_{i}.txt").write_text(f"Remote commit {i}\n")
            subprocess.run(
                ["git", "-C", str(temp_clone), "add", "."],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(temp_clone), "commit", "-m", f"Remote commit {i}"],
                check=True,
                capture_output=True,
            )

        subprocess.run(
            ["git", "-C", str(temp_clone), "push", "origin", "main"],
            check=True,
            capture_output=True,
        )

    # Fetch remote changes to update tracking branch
    subprocess.run(
        ["git", "-C", str(repo_path), "fetch", "origin"],
        check=True,
        capture_output=True,
    )

    return repo_path, remote_path


def create_git_repo_ahead(tmp_path: Path, commits_ahead: int = 2) -> tuple[Path, Path]:
    """
    Create git repo with local commits ahead of remote (unpushed commits).

    Args:
        tmp_path: Temporary directory for test files
        commits_ahead: Number of local unpushed commits

    Returns:
        (repo_path, remote_path) tuple
    """
    repo_path, remote_path = create_git_repo_uptodate(tmp_path)

    # Add local commits (ahead)
    for i in range(commits_ahead):
        (repo_path / f"local_ahead_{i}.txt").write_text(f"Local commit {i}\n")
        subprocess.run(
            ["git", "-C", str(repo_path), "add", "."],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_path), "commit", "-m", f"Local ahead commit {i}"],
            check=True,
            capture_output=True,
        )

    return repo_path, remote_path


def create_git_repo_no_upstream(tmp_path: Path) -> Path:
    """
    Create git repo with no upstream tracking branch.

    Args:
        tmp_path: Temporary directory for test files

    Returns:
        repo_path
    """
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    # Initialize local-only repository
    subprocess.run(
        ["git", "init", str(repo_path)],
        check=True,
        capture_output=True,
    )
    _configure_git_user(repo_path)

    # Create initial commit (but no remote)
    (repo_path / "README.md").write_text("# Test Repository\n")
    subprocess.run(
        ["git", "-C", str(repo_path), "add", "."],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_path), "commit", "-m", "Initial commit"],
        check=True,
        capture_output=True,
    )

    # Rename branch to main if needed
    subprocess.run(
        ["git", "-C", str(repo_path), "branch", "-M", "main"],
        check=True,
        capture_output=True,
    )

    return repo_path


def create_test_recipe_context(repo_path: Path) -> dict:
    """
    Create recipe context dictionary for testing.

    Args:
        repo_path: Path to git repository

    Returns:
        Context dictionary with repo_path variable
    """
    return {"repo_path": str(repo_path)}


def _configure_git_user(repo_path: Path) -> None:
    """Configure git user for test repository."""
    subprocess.run(
        ["git", "-C", str(repo_path), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_path), "config", "user.name", "Test User"],
        check=True,
        capture_output=True,
    )
