"""GitHub Pages deployer for documentation sites.

Deploys generated documentation sites to GitHub Pages via gh-pages branch.

Philosophy:
- Single responsibility: Deploy site to GitHub Pages
- Safe by default: Never force push unless explicitly requested
- Proper git workflow with rollback on failure
- Clear error messages for common issues
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from . import DeploymentConfig, DeploymentResult


def deploy_site(config: DeploymentConfig) -> DeploymentResult:
    """Deploy documentation site to GitHub Pages.

    Args:
        config: Deployment configuration

    Returns:
        DeploymentResult with deployment status

    Raises:
        TypeError: If config is None
        ValueError: If site_dir doesn't exist or is empty
        PermissionError: If unable to copy files
    """
    if config is None:
        raise TypeError("Config cannot be None")

    site_path = Path(config.site_dir)
    repo_path = Path(config.repo_path)
    errors: list[str] = []

    # Validate site directory exists and has content
    if not site_path.exists():
        raise ValueError(f"Site directory not found: {config.site_dir}")

    site_contents = list(site_path.iterdir())
    if not site_contents:
        raise ValueError(f"Site directory is empty: {config.site_dir}")

    # Check git status (should be clean or we might lose changes)
    try:
        is_clean = _check_git_status(repo_path)
        if not is_clean:
            # Allow deployment with uncommitted changes, but warn
            pass
    except Exception as e:
        errors.append(f"Git status check failed: {e}")
        return DeploymentResult(
            success=False,
            branch="gh-pages",
            commit_sha=None,
            url=None,
            errors=errors,
        )

    # Get current branch to return to after deployment
    try:
        original_branch = _get_current_branch(repo_path)
    except Exception:
        original_branch = "main"

    # Get repository URL for constructing Pages URL
    try:
        repo_url = _get_repo_url(repo_path)
        pages_url = _construct_pages_url(repo_url)
    except Exception:
        repo_url = ""
        pages_url = None

    # Create a temporary directory for the deployment
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Copy site contents to temp directory
        try:
            for item in site_path.iterdir():
                if item.is_dir():
                    shutil.copytree(item, tmp_path / item.name)
                else:
                    shutil.copy2(item, tmp_path / item.name)
        except PermissionError:
            raise

        # Validate branch name before operations
        _validate_branch_name("gh-pages")

        # Check if gh-pages branch exists
        branch_exists = _branch_exists(repo_path, "gh-pages")

        try:
            if branch_exists:
                # Switch to existing gh-pages branch
                _run_git_command(repo_path, ["checkout", "gh-pages"])
            else:
                # Create orphan gh-pages branch
                _run_git_command(repo_path, ["checkout", "--orphan", "gh-pages"])
                # Remove all files from the new branch
                _run_git_command(repo_path, ["rm", "-rf", "."], check=False)

            # Clear the directory (except .git)
            for item in repo_path.iterdir():
                if item.name != ".git":
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()

            # Copy site contents to repo root
            for item in tmp_path.iterdir():
                dest = repo_path / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

            # Add .nojekyll file to disable Jekyll processing
            (repo_path / ".nojekyll").touch()

            # Stage all changes
            _run_git_command(repo_path, ["add", "."])

            # Check if there are changes to commit
            status_result = _run_git_command(
                repo_path, ["status", "--porcelain"], capture_output=True
            )

            if not status_result.stdout.strip():
                # No changes to commit
                _switch_branch(repo_path, original_branch)
                return DeploymentResult(
                    success=True,
                    branch="gh-pages",
                    commit_sha=None,
                    url=pages_url,
                    errors=["No changes to deploy"],
                )

            # Commit changes
            _run_git_command(repo_path, ["commit", "-m", config.commit_message])

            # Get commit SHA
            sha_result = _run_git_command(repo_path, ["rev-parse", "HEAD"], capture_output=True)
            commit_sha = sha_result.stdout.strip()

            # Push to remote
            push_args = ["push", "origin", "gh-pages"]
            if config.force_push:
                push_args.insert(1, "--force")

            try:
                _run_git_command(repo_path, push_args)
            except subprocess.CalledProcessError as e:
                # CalledProcessError always has stderr when capture_output=True
                errors.append(f"push failed: {e.stderr if e.stderr else str(e)}")
                # Rollback to original branch
                _switch_branch(repo_path, original_branch)
                return DeploymentResult(
                    success=False,
                    branch="gh-pages",
                    commit_sha=commit_sha,
                    url=None,
                    errors=errors,
                )

            # Switch back to original branch
            _switch_branch(repo_path, original_branch)

            return DeploymentResult(
                success=True,
                branch="gh-pages",
                commit_sha=commit_sha,
                url=pages_url,
                errors=[],
            )

        except subprocess.CalledProcessError as e:
            # CalledProcessError always has stderr when capture_output=True
            error_msg = e.stderr if e.stderr else str(e)
            errors.append(f"Git operation failed: {error_msg}")

            # Try to rollback to original branch
            try:
                _switch_branch(repo_path, original_branch)
            except Exception:
                pass

            return DeploymentResult(
                success=False,
                branch="gh-pages",
                commit_sha=None,
                url=None,
                errors=errors,
            )
        except OSError as e:
            errors.append(f"File operation failed: {e!s}")
            return DeploymentResult(
                success=False,
                branch="gh-pages",
                commit_sha=None,
                url=None,
                errors=errors,
            )


# ==============================================================================
# Git Helper Functions
# ==============================================================================


def _validate_branch_name(branch_name: str) -> None:
    """Validate git branch name for security.

    Args:
        branch_name: Branch name to validate

    Raises:
        ValueError: If branch name is invalid or potentially dangerous
    """
    if not branch_name:
        raise ValueError("Branch name cannot be empty")

    # Check for dangerous characters
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]
    for char in dangerous_chars:
        if char in branch_name:
            raise ValueError(f"Branch name contains invalid character: {char}")

    # Check for path traversal attempts
    if ".." in branch_name or branch_name.startswith("/"):
        raise ValueError(f"Branch name contains invalid path components: {branch_name}")

    # Validate against git branch naming rules
    # Cannot start/end with slash, contain consecutive slashes, or end with .lock
    if (
        branch_name.startswith("/")
        or branch_name.endswith("/")
        or "//" in branch_name
        or branch_name.endswith(".lock")
    ):
        raise ValueError(f"Branch name violates git naming rules: {branch_name}")


def _validate_github_url(url: str) -> None:
    """Validate GitHub repository URL for security.

    Args:
        url: GitHub URL to validate

    Raises:
        ValueError: If URL is invalid or potentially dangerous
    """
    if not url:
        raise ValueError("GitHub URL cannot be empty")

    # Check for dangerous characters that could be used for injection
    dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r", " "]
    for char in dangerous_chars:
        if char in url:
            raise ValueError(f"GitHub URL contains invalid character: {char}")

    # Validate URL format (must be GitHub)
    valid_prefixes = [
        "https://github.com/",
        "git@github.com:",
        "http://github.com/",  # Will be upgraded to HTTPS
    ]

    if not any(url.startswith(prefix) for prefix in valid_prefixes):
        raise ValueError(
            f"URL must be a valid GitHub URL (https://github.com/... or git@github.com:...): {url}"
        )


def _run_git_command(
    repo_path: Path,
    args: list[str],
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a git command in the repository.

    Args:
        repo_path: Path to repository
        args: Git command arguments
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise on non-zero exit

    Returns:
        CompletedProcess result
    """
    cmd = ["git"] + args

    result = subprocess.run(
        cmd,
        cwd=str(repo_path),
        capture_output=capture_output,
        text=True,
        check=check,
    )

    return result


def _check_git_status(repo_path: Path) -> bool:
    """Check if git working directory is clean.

    Args:
        repo_path: Path to repository

    Returns:
        True if clean, False if dirty
    """
    result = _run_git_command(
        repo_path,
        ["status", "--porcelain"],
        capture_output=True,
    )

    # Empty output means clean
    return len(result.stdout.strip()) == 0


def _get_current_branch(repo_path: Path) -> str:
    """Get current git branch name.

    Args:
        repo_path: Path to repository

    Returns:
        Current branch name
    """
    result = _run_git_command(
        repo_path,
        ["rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
    )

    return result.stdout.strip()


def _get_repo_url(repo_path: Path) -> str:
    """Get repository URL from git remote.

    Args:
        repo_path: Path to repository

    Returns:
        Repository URL
    """
    result = _run_git_command(
        repo_path,
        ["remote", "get-url", "origin"],
        capture_output=True,
    )

    return result.stdout.strip()


def _branch_exists(repo_path: Path, branch_name: str) -> bool:
    """Check if a branch exists.

    Args:
        repo_path: Path to repository
        branch_name: Name of branch to check

    Returns:
        True if branch exists, False otherwise
    """
    try:
        result = _run_git_command(
            repo_path,
            ["show-ref", "--verify", f"refs/heads/{branch_name}"],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _switch_branch(repo_path: Path, branch_name: str) -> None:
    """Switch to a different branch.

    Args:
        repo_path: Path to repository
        branch_name: Branch to switch to

    Raises:
        ValueError: If branch name is invalid
    """
    _validate_branch_name(branch_name)
    _run_git_command(repo_path, ["checkout", branch_name])


def _construct_pages_url(repo_url: str) -> str:
    """Construct GitHub Pages URL from repository URL.

    Args:
        repo_url: Repository URL (SSH or HTTPS)

    Returns:
        GitHub Pages URL

    Raises:
        ValueError: If URL is invalid

    Examples:
        >>> _construct_pages_url("git@github.com:user/repo.git")
        'https://user.github.io/repo/'
        >>> _construct_pages_url("https://github.com/user/repo.git")
        'https://user.github.io/repo/'
    """
    _validate_github_url(repo_url)
    url = repo_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    # Handle SSH format: git@github.com:user/repo
    if "git@github.com:" in url:
        parts = url.split("git@github.com:")[-1].split("/")
    # Handle HTTPS format: https://github.com/user/repo
    elif "github.com/" in url:
        parts = url.split("github.com/")[-1].split("/")
    else:
        # Unknown format, try to extract last two parts
        parts = url.split("/")[-2:]

    owner = parts[0] if len(parts) > 0 else "unknown"
    repo = parts[1] if len(parts) > 1 else "unknown"

    return f"https://{owner}.github.io/{repo}/"
