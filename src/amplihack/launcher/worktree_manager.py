"""Git worktree manager for isolated automode execution.

This module provides automatic worktree creation and cleanup for automode sessions,
ensuring complete isolation from the active development directory.
"""

import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple


class WorktreeError(Exception):
    """Exception raised for worktree-related errors."""

    pass


class WorktreeManager:
    """Manages git worktrees for isolated automode execution.

    This class handles:
    - Automatic worktree creation with timestamp-based names
    - Branch creation for each worktree
    - Cleanup of worktrees after session completion
    - Detection of git repository state
    """

    def __init__(self, base_dir: Path, prefix: str = "automode"):
        """Initialize worktree manager.

        Args:
            base_dir: Base directory containing the git repository
            prefix: Prefix for worktree directory names (default: "automode")
        """
        self.base_dir = Path(base_dir).resolve()
        self.prefix = prefix
        self.worktree_path: Optional[Path] = None
        self.branch_name: Optional[str] = None

    def is_git_repo(self) -> bool:
        """Check if base_dir is within a git repository.

        Returns:
            True if in a git repository, False otherwise
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def get_repo_root(self) -> Path:
        """Get the root directory of the git repository.

        Returns:
            Path to repository root

        Raises:
            WorktreeError: If not in a git repository
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            return Path(result.stdout.strip()).resolve()
        except subprocess.CalledProcessError as e:
            raise WorktreeError(f"Not in a git repository: {e}") from e

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes in the repository.

        Returns:
            True if there are uncommitted changes, False otherwise
        """
        try:
            # Check both staged and unstaged changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            return bool(result.stdout.strip())
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def create_worktree(self, task_hint: Optional[str] = None) -> Tuple[Path, str]:
        """Create a new git worktree for automode execution.

        Args:
            task_hint: Optional hint for task name (sanitized for branch name)

        Returns:
            Tuple of (worktree_path, branch_name)

        Raises:
            WorktreeError: If worktree creation fails
        """
        if not self.is_git_repo():
            raise WorktreeError(f"Not in a git repository: {self.base_dir}")

        # Generate unique worktree name with timestamp
        timestamp = int(time.time())
        if task_hint:
            # Sanitize task hint for branch name (alphanumeric, dashes, underscores only)
            sanitized_hint = "".join(c if c.isalnum() or c in "-_" else "-" for c in task_hint)
            sanitized_hint = sanitized_hint.strip("-")[:30]  # Limit length
            worktree_name = f"{self.prefix}-{sanitized_hint}-{timestamp}"
        else:
            worktree_name = f"{self.prefix}-{timestamp}"

        # Create worktree directory path
        repo_root = self.get_repo_root()
        worktree_path = repo_root / "worktrees" / worktree_name

        # Create branch name (use full worktree name)
        branch_name = worktree_name

        try:
            # Ensure worktrees directory exists
            worktree_path.parent.mkdir(parents=True, exist_ok=True)

            # Create worktree with new branch
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), "-b", branch_name],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            self.worktree_path = worktree_path
            self.branch_name = branch_name

            return worktree_path, branch_name

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to create worktree: {e.stderr if e.stderr else str(e)}"
            raise WorktreeError(error_msg) from e

    def cleanup_worktree(self, force: bool = False) -> None:
        """Remove the worktree and its branch.

        Args:
            force: If True, force removal even with uncommitted changes

        Raises:
            WorktreeError: If cleanup fails
        """
        if not self.worktree_path or not self.branch_name:
            return

        try:
            # Remove worktree
            cmd = ["git", "worktree", "remove", str(self.worktree_path)]
            if force:
                cmd.append("--force")

            subprocess.run(
                cmd,
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            # Delete the branch (if it exists and is not checked out elsewhere)
            try:
                subprocess.run(
                    ["git", "branch", "-D", self.branch_name],
                    cwd=self.base_dir,
                    capture_output=True,
                    text=True,
                    check=False,  # Don't fail if branch already deleted
                )
            except subprocess.SubprocessError:
                # Branch deletion is best-effort
                pass

            # Clean up empty directories
            try:
                if self.worktree_path.parent.exists() and not any(
                    self.worktree_path.parent.iterdir()
                ):
                    self.worktree_path.parent.rmdir()
            except (OSError, PermissionError):
                # Directory cleanup is best-effort
                pass

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to remove worktree: {e.stderr if e.stderr else str(e)}"
            raise WorktreeError(error_msg) from e
        finally:
            self.worktree_path = None
            self.branch_name = None

    def list_worktrees(self) -> list[dict[str, str]]:
        """List all worktrees in the repository.

        Returns:
            List of worktree info dicts with keys: path, branch, commit
        """
        if not self.is_git_repo():
            return []

        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                check=True,
            )

            worktrees = []
            current = {}
            for line in result.stdout.strip().split("\n"):
                if not line:
                    if current:
                        worktrees.append(current)
                        current = {}
                    continue

                if line.startswith("worktree "):
                    current["path"] = line.split(" ", 1)[1]
                elif line.startswith("branch "):
                    current["branch"] = line.split(" ", 1)[1]
                elif line.startswith("HEAD "):
                    current["commit"] = line.split(" ", 1)[1]

            # Add last worktree if exists
            if current:
                worktrees.append(current)

            return worktrees

        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def cleanup_old_worktrees(self, prefix: Optional[str] = None, max_age_hours: int = 24) -> int:
        """Clean up old automode worktrees based on age.

        Args:
            prefix: Worktree prefix to match (defaults to self.prefix)
            max_age_hours: Maximum age in hours before cleanup (default: 24)

        Returns:
            Number of worktrees cleaned up
        """
        if prefix is None:
            prefix = self.prefix

        worktrees = self.list_worktrees()
        cleaned = 0
        current_time = time.time()

        for wt in worktrees:
            path = Path(wt.get("path", ""))
            branch = wt.get("branch", "")

            # Check if this is an automode worktree
            if not branch.startswith(f"refs/heads/{prefix}-"):
                continue

            # Extract timestamp from branch name (last component after final dash)
            try:
                timestamp_str = branch.split("-")[-1]
                timestamp = int(timestamp_str)
                age_hours = (current_time - timestamp) / 3600

                if age_hours > max_age_hours:
                    # Create temporary manager for this worktree
                    temp_manager = WorktreeManager(self.base_dir, prefix)
                    temp_manager.worktree_path = path
                    temp_manager.branch_name = branch.replace("refs/heads/", "")
                    try:
                        temp_manager.cleanup_worktree(force=True)
                        cleaned += 1
                    except WorktreeError:
                        # Continue cleaning others even if one fails
                        pass

            except (ValueError, IndexError):
                # Not a valid timestamp, skip
                continue

        return cleaned

    def __enter__(self):
        """Context manager entry - does not auto-create worktree.

        Call create_worktree() explicitly after entering context.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup worktree if created."""
        if self.worktree_path:
            try:
                # Force cleanup if exception occurred
                self.cleanup_worktree(force=exc_type is not None)
            except WorktreeError:
                # Suppress cleanup errors during exception handling
                pass
        return False
