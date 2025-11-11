"""GitHub repository creation for agent bundles."""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RepositoryResult:
    """Result of repository creation operation."""

    success: bool
    url: Optional[str] = None
    repository: Optional[str] = None
    error: Optional[str] = None


class RepositoryCreator:
    """
    Create and manage GitHub repositories for agent bundles.

    Uses GitHub CLI (gh) for all repository operations.
    """

    def __init__(self):
        """Initialize repository creator."""
        self._check_gh_cli()

    def _check_gh_cli(self) -> bool:
        """
        Check if GitHub CLI is available and authenticated.

        Returns:
            True if gh CLI is available

        Raises:
            RuntimeError: If gh CLI is not available or not authenticated
        """
        try:
            # Check if gh is installed
            result = subprocess.run(
                ["gh", "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                raise RuntimeError("GitHub CLI (gh) is not installed")

            # Check authentication status
            auth_result = subprocess.run(
                ["gh", "auth", "status"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if auth_result.returncode != 0:
                raise RuntimeError("GitHub CLI is not authenticated. Run: gh auth login")

            logger.debug("GitHub CLI is available and authenticated")
            return True

        except subprocess.TimeoutExpired:
            raise RuntimeError("GitHub CLI command timed out")
        except FileNotFoundError:
            raise RuntimeError(
                "GitHub CLI (gh) is not installed. Install from: https://cli.github.com"
            )

    def create_repository(
        self,
        bundle_path: Path,
        repo_name: Optional[str] = None,
        private: bool = True,
        push: bool = False,
        organization: Optional[str] = None,
    ) -> RepositoryResult:
        """
        Create GitHub repository for agent bundle.

        Creates a new repository, initializes git if needed, and optionally pushes.

        Args:
            bundle_path: Path to bundle directory
            repo_name: Repository name (defaults to bundle name)
            private: Whether to create private repository (default True)
            push: Whether to push to remote after creation (default False)
            organization: Organization to create repo under (optional)

        Returns:
            RepositoryResult with creation details

        Raises:
            ValueError: If bundle_path is invalid
            RuntimeError: If GitHub CLI is not available
        """
        if not bundle_path.exists():
            return RepositoryResult(
                success=False,
                error=f"Bundle path does not exist: {bundle_path}",
            )

        if not bundle_path.is_dir():
            return RepositoryResult(
                success=False,
                error=f"Bundle path is not a directory: {bundle_path}",
            )

        try:
            # Load bundle manifest to get name
            manifest_path = bundle_path / "manifest.json"
            if not manifest_path.exists():
                return RepositoryResult(
                    success=False,
                    error="No manifest.json found in bundle",
                )

            with open(manifest_path) as f:
                manifest = json.load(f)

            bundle_name = manifest.get("bundle", {}).get("name", "agent-bundle")
            bundle_version = manifest.get("bundle", {}).get("version", "1.0.0")
            bundle_description = manifest.get("bundle", {}).get("description", "Agent bundle")

            # Use provided repo name or default to bundle name
            final_repo_name = repo_name or bundle_name

            logger.info(f"Creating repository: {final_repo_name}")

            # Initialize git repository if not already initialized
            git_dir = bundle_path / ".git"
            if not git_dir.exists():
                logger.debug("Initializing git repository")
                self._run_git_command(
                    ["git", "init"],
                    cwd=bundle_path,
                )

                # Create initial commit
                self._run_git_command(
                    ["git", "add", "."],
                    cwd=bundle_path,
                )

                commit_message = f"Initial commit: {bundle_name} v{bundle_version}"
                self._run_git_command(
                    ["git", "commit", "-m", commit_message],
                    cwd=bundle_path,
                )

            # Build gh repo create command
            gh_command = [
                "gh",
                "repo",
                "create",
                final_repo_name,
                "--source",
                str(bundle_path),
                "--description",
                bundle_description,
            ]

            # Add visibility flag
            if private:
                gh_command.append("--private")
            else:
                gh_command.append("--public")

            # Add organization if specified
            if organization:
                # Remove repo name from command and add org/repo format
                gh_command[3] = f"{organization}/{final_repo_name}"

            # Add push flag if requested
            if push:
                gh_command.append("--push")

            logger.debug(f"Running: {' '.join(gh_command)}")

            # Create repository
            result = subprocess.run(
                gh_command,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                logger.error(
                    f"GitHub repository creation failed: repo='{final_repo_name}', "
                    f"returncode={result.returncode}, error='{error_msg}' "
                    f"(check GitHub CLI authentication and permissions)"
                )
                return RepositoryResult(
                    success=False,
                    error=error_msg,
                )

            # Extract repository URL from output
            repo_url = result.stdout.strip()
            if not repo_url.startswith("http"):
                # Try to get URL from git remote
                remote_result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    check=False,
                    cwd=bundle_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if remote_result.returncode == 0:
                    repo_url = remote_result.stdout.strip()

            # Determine full repository name
            if organization:
                full_repo_name = f"{organization}/{final_repo_name}"
            else:
                # Get current user
                user_result = subprocess.run(
                    ["gh", "api", "user", "--jq", ".login"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if user_result.returncode == 0:
                    username = user_result.stdout.strip()
                    full_repo_name = f"{username}/{final_repo_name}"
                else:
                    full_repo_name = final_repo_name

            logger.info(f"Successfully created repository: {repo_url}")

            return RepositoryResult(
                success=True,
                url=repo_url,
                repository=full_repo_name,
            )

        except subprocess.TimeoutExpired:
            return RepositoryResult(
                success=False,
                error="GitHub operation timed out",
            )
        except json.JSONDecodeError as e:
            return RepositoryResult(
                success=False,
                error=f"Invalid manifest.json: {e}",
            )
        except Exception as e:
            logger.exception("Repository creation failed")
            return RepositoryResult(
                success=False,
                error=str(e),
            )

    def _run_git_command(
        self,
        command: list,
        cwd: Path,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess:
        """
        Run git command with error handling.

        Args:
            command: Git command as list
            cwd: Working directory
            timeout: Command timeout in seconds

        Returns:
            CompletedProcess result

        Raises:
            RuntimeError: If git command fails
        """
        try:
            result = subprocess.run(
                command,
                check=False,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Git command failed: {' '.join(command)}\n{result.stderr}")

            return result

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Git command timed out: {' '.join(command)}")
        except FileNotFoundError:
            raise RuntimeError("Git is not installed")

    def delete_repository(
        self,
        repository: str,
        confirm: bool = False,
    ) -> RepositoryResult:
        """
        Delete a GitHub repository.

        Args:
            repository: Repository name in format "owner/repo"
            confirm: Must be True to actually delete

        Returns:
            RepositoryResult indicating success or failure
        """
        if not confirm:
            return RepositoryResult(
                success=False,
                error="Must set confirm=True to delete repository",
            )

        if "/" not in repository:
            return RepositoryResult(
                success=False,
                error="Repository must be in format 'owner/repo'",
            )

        try:
            logger.warning(f"Deleting repository: {repository}")

            result = subprocess.run(
                ["gh", "repo", "delete", repository, "--yes"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return RepositoryResult(
                    success=False,
                    error=result.stderr.strip(),
                )

            logger.info(f"Successfully deleted repository: {repository}")

            return RepositoryResult(
                success=True,
                repository=repository,
            )

        except subprocess.TimeoutExpired:
            return RepositoryResult(
                success=False,
                error="Delete operation timed out",
            )
        except Exception as e:
            return RepositoryResult(
                success=False,
                error=str(e),
            )

    def check_repository_exists(self, repository: str) -> bool:
        """
        Check if repository exists.

        Args:
            repository: Repository name in format "owner/repo"

        Returns:
            True if repository exists
        """
        try:
            result = subprocess.run(
                ["gh", "repo", "view", repository],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            return result.returncode == 0

        except Exception as e:
            logger.debug(f"Git verification failed for {directory}: {e}")
            return False
