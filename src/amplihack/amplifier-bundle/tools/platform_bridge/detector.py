"""Platform detection from git remote URLs.

Philosophy:
- Ruthless simplicity: regex patterns, standard library only
- Zero-BS: No stubs, fully functional
- Self-contained: <50 lines core logic (excluding docs/tests)
"""

import re
import subprocess
from enum import Enum
from pathlib import Path


class Platform(Enum):
    """Supported platforms."""

    GITHUB = "github"
    AZDO = "azdo"
    UNKNOWN = "unknown"


class PlatformDetector:
    """Detect platform from git remote URL."""

    def __init__(self, repo_path: str | Path | None = None, timeout: int = 30):
        """Initialize detector.

        Args:
            repo_path: Path to git repository (default: current directory)
            timeout: Timeout for git commands in seconds (default: 30)
        """
        if repo_path is None:
            self.repo_path = Path.cwd()
        else:
            self.repo_path = Path(repo_path)
        self.timeout = timeout
        self._cache: Platform | None = None

    def get_remote_url(self, remote: str = "origin") -> str:
        """Get remote URL for repository.

        Args:
            remote: Remote name (default: origin)

        Returns:
            Remote URL string

        Raises:
            RuntimeError: If git command fails, git not found, or no remote configured
        """
        try:
            result = subprocess.run(
                ["git", "remote", "-v"],
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout,
                cwd=self.repo_path,
            )

            # Check for error conditions even if check=True didn't raise
            # (needed for test mocks that return result instead of raising)
            if result.returncode != 0:
                if result.stderr and "not a git repository" in result.stderr.lower():
                    raise RuntimeError(f"not a git repository: {self.repo_path}")
                raise RuntimeError(
                    f"Git command failed: {result.stderr if result.stderr else 'unknown error'}"
                )

            # Parse git remote -v output
            # Format: "remotename\turl (fetch|push)"
            lines = result.stdout.strip().split("\n")
            if not lines or not lines[0]:
                raise RuntimeError("no remote configured")

            # Priority: origin > upstream > first available
            for priority_remote in ["origin", "upstream"]:
                for line in lines:
                    if line.startswith(priority_remote):
                        parts = line.split()
                        if len(parts) >= 2:
                            url = parts[1]
                            # Strip .git suffix if present
                            if url.endswith(".git"):
                                url = url[:-4]
                            return url

            # Use first available remote
            if lines[0]:
                parts = lines[0].split()
                if len(parts) >= 2:
                    url = parts[1]
                    # Strip .git suffix if present
                    if url.endswith(".git"):
                        url = url[:-4]
                    return url

            raise RuntimeError("no remote URL found")

        except FileNotFoundError:
            raise RuntimeError("git command not found - ensure git is installed")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Git command timed out after {self.timeout} seconds")
        except subprocess.CalledProcessError as e:
            # Check if it's because we're not in a git repository
            if e.stderr and "not a git repository" in e.stderr.lower():
                raise RuntimeError(f"not a git repository: {self.repo_path}")
            raise RuntimeError(
                f"Failed to get git remote: {e.stderr if e.stderr else 'unknown error'}"
            )

    def detect(self, force_refresh: bool = False) -> Platform:
        """Detect platform from git remote URL.

        Args:
            force_refresh: Force cache refresh (default: False)

        Returns:
            Platform enum value

        Raises:
            RuntimeError: If git command fails or no remote configured
        """
        # Return cached result if available
        if not force_refresh and self._cache is not None:
            return self._cache

        remote_url = self.get_remote_url()

        # GitHub patterns
        if re.search(r"github\.com[:/]", remote_url, re.IGNORECASE):
            platform = Platform.GITHUB
        # Azure DevOps patterns
        elif re.search(r"dev\.azure\.com|visualstudio\.com", remote_url, re.IGNORECASE):
            platform = Platform.AZDO
        else:
            platform = Platform.UNKNOWN

        # Cache result
        self._cache = platform
        return platform


def detect_platform(repo_path: str = ".") -> Platform:
    """Convenience function to detect platform.

    Args:
        repo_path: Path to git repository (default: current directory)

    Returns:
        Platform enum value
    """
    detector = PlatformDetector(repo_path)
    return detector.detect()
