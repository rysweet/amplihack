"""
GitHub distributor for Agent Bundle Generator.

Distributes packaged bundles to GitHub repositories for sharing.
"""

import json
import logging
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import DistributionError, RateLimitError, TimeoutError
from .models import DistributionResult, PackagedBundle

logger = logging.getLogger(__name__)


class GitHubDistributor:
    """
    Distribute agent bundles to GitHub repositories.

    Handles repository creation, uploads, and releases.
    """

    def __init__(
        self,
        github_token: Optional[str] = None,
        organization: Optional[str] = None,
        default_branch: str = "main",
    ):
        """
        Initialize the GitHub distributor.

        Args:
            github_token: GitHub personal access token
            organization: GitHub organization (optional)
            default_branch: Default branch name
        """
        self.github_token = github_token
        self.organization = organization
        self.default_branch = default_branch
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = time.time() + 3600

    def distribute(
        self,
        package: PackagedBundle,
        repository: Optional[str] = None,
        create_release: bool = True,
        options: Optional[Dict[str, Any]] = None,
    ) -> DistributionResult:
        """
        Distribute a package to GitHub.

        Args:
            package: PackagedBundle to distribute
            repository: Target repository name (creates if not exists)
            create_release: Whether to create a GitHub release
            options: Optional distribution options

        Returns:
            DistributionResult with distribution information

        Raises:
            DistributionError: If distribution fails
            RateLimitError: If rate limited
        """
        options = options or {}
        start_time = time.time()

        try:
            # Check rate limits
            self._check_rate_limit()

            # Generate repository name if not provided
            if not repository:
                repository = f"agent-bundle-{package.bundle.name}"

            # Prepare repository
            repo_url = self._prepare_repository(repository, package, options)

            # Upload package
            commit_sha = self._upload_package(repo_url, package, options)

            # Create release if requested
            release_tag = None
            if create_release:
                release_tag = self._create_release(repository, package, commit_sha, options)

            distribution_time = time.time() - start_time

            return DistributionResult(
                success=True,
                platform="github",
                url=repo_url,
                repository=repository,
                branch=self.default_branch,
                commit_sha=commit_sha,
                release_tag=release_tag,
                distribution_time_seconds=distribution_time,
            )

        except (DistributionError, RateLimitError, TimeoutError) as e:
            logger.error(f"Distribution failed (expected): {e}", exc_info=True)
            return DistributionResult(
                success=False,
                platform="github",
                repository=repository,
                errors=[str(e)],
                distribution_time_seconds=time.time() - start_time,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {e.stderr}", exc_info=True)
            return DistributionResult(
                success=False,
                platform="github",
                repository=repository,
                errors=[f"Git command failed: {e.stderr or str(e)}"],
                distribution_time_seconds=time.time() - start_time,
            )
        except Exception as e:
            logger.error(f"Unexpected distribution error: {type(e).__name__}: {e}", exc_info=True)
            return DistributionResult(
                success=False,
                platform="github",
                repository=repository,
                errors=[f"{type(e).__name__}: {str(e)}"],
                distribution_time_seconds=time.time() - start_time,
            )

    def _check_rate_limit(self) -> None:
        """Check and enforce GitHub rate limits."""
        if self.rate_limit_remaining <= 0:
            wait_time = max(0, int(self.rate_limit_reset - time.time()))
            if wait_time > 0:
                raise RateLimitError(
                    f"GitHub rate limit exceeded. Retry after {wait_time} seconds.",
                    retry_after_seconds=wait_time,
                    endpoint="github.com",
                )

        # Decrement rate limit counter
        self.rate_limit_remaining -= 1

    def _prepare_repository(
        self, repository: str, package: PackagedBundle, options: Dict[str, Any]
    ) -> str:
        """Prepare GitHub repository for distribution."""
        # Check if using gh CLI (simplified implementation)
        if self._has_gh_cli():
            return self._prepare_with_gh(repository, package, options)
        return self._prepare_with_git(repository, package, options)

    def _has_gh_cli(self) -> bool:
        """Check if GitHub CLI is available."""
        try:
            result = subprocess.run(
                ["gh", "--version"], check=False, capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _prepare_with_gh(
        self, repository: str, package: PackagedBundle, options: Dict[str, Any]
    ) -> str:
        """Prepare repository using GitHub CLI."""
        try:
            # Check if repository exists
            check_cmd = ["gh", "repo", "view", repository]
            if self.organization:
                check_cmd.extend(["--json", "name"])

            result = subprocess.run(
                check_cmd, check=False, capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                # Create repository
                create_cmd = ["gh", "repo", "create", repository]
                if self.organization:
                    create_cmd.extend(["--org", self.organization])

                create_cmd.extend(
                    [
                        "--public" if options.get("public", True) else "--private",
                        "--description",
                        package.bundle.description[:100],
                        "--add-readme",
                    ]
                )

                result = subprocess.run(
                    create_cmd, check=False, capture_output=True, text=True, timeout=60
                )

                if result.returncode != 0:
                    raise DistributionError(
                        f"Failed to create repository: {result.stderr}",
                        platform="github",
                        repository=repository,
                    )

            # Get repository URL
            if self.organization:
                repo_url = f"https://github.com/{self.organization}/{repository}"
            else:
                # Get current user
                user_result = subprocess.run(
                    ["gh", "api", "user", "--jq", ".login"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                username = user_result.stdout.strip()
                repo_url = f"https://github.com/{username}/{repository}"

            return repo_url

        except subprocess.TimeoutExpired:
            raise TimeoutError(
                "GitHub CLI operation timed out",
                operation="repository_preparation",
                timeout_seconds=60,
            )

    def _prepare_with_git(
        self, repository: str, package: PackagedBundle, options: Dict[str, Any]
    ) -> str:
        """Prepare repository using git directly."""
        # Simplified implementation - would use git commands
        if self.organization:
            repo_url = f"https://github.com/{self.organization}/{repository}"
        else:
            repo_url = f"https://github.com/user/{repository}"

        logger.warning("Direct git implementation not complete, using placeholder URL")
        return repo_url

    def _upload_package(
        self, repo_url: str, package: PackagedBundle, options: Dict[str, Any]
    ) -> str:
        """Upload package contents to repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_path = None

            try:
                # Clone repository
                clone_cmd = ["git", "clone", repo_url, str(temp_path / "repo")]
                result = subprocess.run(
                    clone_cmd, check=False, capture_output=True, text=True, timeout=120
                )

                if result.returncode != 0:
                    # Try to initialize if clone failed
                    repo_path = temp_path / "repo"
                    try:
                        repo_path.mkdir()
                        subprocess.run(["git", "init"], cwd=repo_path, check=True, timeout=10)
                        subprocess.run(
                            ["git", "remote", "add", "origin", repo_url],
                            cwd=repo_path,
                            check=True,
                            timeout=10,
                        )
                    except subprocess.TimeoutExpired as te:
                        raise TimeoutError(
                            "Git initialization timed out", operation="repo_init", timeout_seconds=10
                        ) from te
                else:
                    repo_path = temp_path / "repo"

                # Copy package contents
                try:
                    if package.package_path.is_dir():
                        # Copy directory contents
                        for item in package.package_path.iterdir():
                            if item.is_dir():
                                shutil.copytree(item, repo_path / item.name, dirs_exist_ok=True)
                            else:
                                shutil.copy2(item, repo_path)
                    # Extract archive to repo
                    elif package.format == "zip":
                        import zipfile
                        with zipfile.ZipFile(package.package_path, "r") as zipf:
                            zipf.extractall(repo_path)
                    elif package.format in ["tar.gz", "uvx"]:
                        import tarfile
                        with tarfile.open(package.package_path, "r:*") as tar:
                            tar.extractall(repo_path)
                except Exception as e:
                    raise DistributionError(
                        f"Failed to copy package contents: {e}",
                        platform="github",
                        repository=repo_url,
                    ) from e

                # Create or update README
                try:
                    readme_path = repo_path / "README.md"
                    if not readme_path.exists():
                        readme_content = self._generate_repo_readme(package)
                        readme_path.write_text(readme_content)
                except OSError as e:
                    raise DistributionError(
                        f"Failed to write README: {e}", platform="github", repository=repo_url
                    ) from e

                # Git add, commit, and push with explicit error handling
                try:
                    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, timeout=30)

                    commit_message = f"Add {package.bundle.name} v{package.bundle.version}"
                    subprocess.run(
                        ["git", "commit", "-m", commit_message], cwd=repo_path, check=True, timeout=30
                    )

                    # Get commit SHA
                    result = subprocess.run(
                        ["git", "rev-parse", "HEAD"],
                        check=False,
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    commit_sha = result.stdout.strip()

                    # Push to remote
                    subprocess.run(
                        ["git", "push", "origin", self.default_branch],
                        cwd=repo_path,
                        check=True,
                        timeout=120,
                    )

                    return commit_sha

                except subprocess.TimeoutExpired as te:
                    operation = "package_upload"
                    if "push" in str(te):
                        operation = "git_push"
                    raise TimeoutError(
                        "Git operation timed out", operation=operation, timeout_seconds=120
                    ) from te

            except subprocess.CalledProcessError as e:
                error_msg = f"Git operation failed: {e.stderr if hasattr(e, 'stderr') else str(e)}"
                logger.error(error_msg, exc_info=True)
                raise DistributionError(
                    error_msg, platform="github", repository=repo_url
                ) from e
            except subprocess.TimeoutExpired as te:
                logger.error(f"Git command timed out: {te}", exc_info=True)
                raise TimeoutError(
                    "Git operation timed out", operation="package_upload", timeout_seconds=120
                ) from te
            except (DistributionError, TimeoutError):
                # Re-raise our custom exceptions
                raise
            except Exception as e:
                logger.error(f"Unexpected error during package upload: {type(e).__name__}: {e}", exc_info=True)
                raise DistributionError(
                    f"Unexpected error during upload: {type(e).__name__}: {e}",
                    platform="github",
                    repository=repo_url,
                ) from e

    def _create_release(
        self, repository: str, package: PackagedBundle, commit_sha: str, options: Dict[str, Any]
    ) -> str:
        """Create a GitHub release."""
        release_tag = f"v{package.bundle.version}"

        if self._has_gh_cli():
            try:
                # Create release using gh CLI
                release_cmd = [
                    "gh",
                    "release",
                    "create",
                    release_tag,
                    "--repo",
                    repository,
                    "--title",
                    f"{package.bundle.name} v{package.bundle.version}",
                    "--notes",
                    self._generate_release_notes(package),
                ]

                if options.get("draft", False):
                    release_cmd.append("--draft")

                if options.get("prerelease", False):
                    release_cmd.append("--prerelease")

                # Add package file if it's an archive
                if package.package_path.is_file():
                    release_cmd.append(str(package.package_path))

                result = subprocess.run(
                    release_cmd, check=False, capture_output=True, text=True, timeout=120
                )

                if result.returncode != 0:
                    logger.warning(f"Failed to create release: {result.stderr}")
                    return None

                return release_tag

            except subprocess.TimeoutExpired:
                logger.warning("Release creation timed out")
                return None

        return None

    def _generate_repo_readme(self, package: PackagedBundle) -> str:
        """Generate README for the repository."""
        agent_list = "\n".join(
            [f"- **{agent.name}**: {agent.role}" for agent in package.bundle.agents]
        )

        return f"""# {package.bundle.name}

{package.bundle.description}

## Installation

### Using UVX

```bash
uvx install {package.bundle.name}
```

### From Source

```bash
git clone {self.organization or "username"}/{package.bundle.name}
cd {package.bundle.name}
pip install -e .
```

## Agents

This bundle contains {len(package.bundle.agents)} agents:

{agent_list}

## Quick Start

```python
from {package.bundle.name} import load

bundle = load()
for agent in bundle["agents"]:
    result = agent.process("input data")
```

## Bundle Information

- **Version**: {package.bundle.version}
- **Format**: {package.format}
- **Size**: {package.size_bytes / 1024:.1f} KB
- **Created**: {package.created_at.isoformat()}

## Documentation

See the `docs/` directory for detailed documentation.

## License

MIT

---
Generated by Agent Bundle Generator
"""

    def _generate_release_notes(self, package: PackagedBundle) -> str:
        """Generate release notes for GitHub release."""
        return f"""## {package.bundle.name} v{package.bundle.version}

### Bundle Contents

- **Agents**: {len(package.bundle.agents)}
- **Package Format**: {package.format}
- **Package Size**: {package.size_bytes / 1024:.1f} KB

### Agents Included

{chr(10).join(f"- {agent.name}: {agent.role}" for agent in package.bundle.agents)}

### Installation

```bash
uvx install {package.bundle.name}
```

### Checksum

```
SHA256: {package.checksum}
```

---
Generated on {package.created_at.isoformat()}
"""

    def list_distributions(self, repository: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List existing distributions.

        Args:
            repository: Optional specific repository to check

        Returns:
            List of distribution information
        """
        distributions = []

        if self._has_gh_cli():
            try:
                # List repositories
                list_cmd = ["gh", "repo", "list"]
                if self.organization:
                    list_cmd.extend([self.organization])

                list_cmd.extend(["--json", "name,description,url,updatedAt"])

                result = subprocess.run(
                    list_cmd, check=False, capture_output=True, text=True, timeout=30
                )

                if result.returncode == 0:
                    repos = json.loads(result.stdout)
                    for repo in repos:
                        if repository and repo["name"] != repository:
                            continue

                        if "agent-bundle" in repo["name"].lower():
                            distributions.append(
                                {
                                    "name": repo["name"],
                                    "description": repo.get("description", ""),
                                    "url": repo["url"],
                                    "updated": repo.get("updatedAt", ""),
                                }
                            )

            except (subprocess.SubprocessError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to list distributions: {e}")

        return distributions

    def download_distribution(
        self, repository: str, target_path: Path, version: Optional[str] = None
    ) -> PackagedBundle:
        """
        Download a distributed bundle.

        Args:
            repository: Repository name
            target_path: Target directory for download
            version: Optional specific version (defaults to latest)

        Returns:
            Downloaded PackagedBundle

        Raises:
            DistributionError: If download fails
        """
        target_path.mkdir(parents=True, exist_ok=True)

        if self._has_gh_cli():
            try:
                # Download release
                download_cmd = ["gh", "release", "download"]
                if version:
                    download_cmd.append(version)
                else:
                    download_cmd.append("--latest")

                download_cmd.extend(["--repo", repository, "--dir", str(target_path)])

                result = subprocess.run(
                    download_cmd, check=False, capture_output=True, text=True, timeout=300
                )

                if result.returncode != 0:
                    raise DistributionError(
                        f"Failed to download distribution: {result.stderr}",
                        platform="github",
                        repository=repository,
                    )

                # Find downloaded package
                package_files = (
                    list(target_path.glob("*.uvx"))
                    + list(target_path.glob("*.tar.gz"))
                    + list(target_path.glob("*.zip"))
                )

                if not package_files:
                    raise DistributionError(
                        "No package file found in download",
                        platform="github",
                        repository=repository,
                    )

                # Return simplified PackagedBundle
                # Full implementation would extract and load bundle
                return PackagedBundle(
                    bundle=None,  # Would be loaded from package
                    package_path=package_files[0],
                    format="uvx"
                    if package_files[0].suffix == ".uvx"
                    else package_files[0].suffix[1:],
                )

            except subprocess.TimeoutExpired:
                raise TimeoutError(
                    "Download operation timed out",
                    operation="distribution_download",
                    timeout_seconds=300,
                )

        raise DistributionError("GitHub CLI not available", platform="github")
