"""Abstract base class for platform operations.

Philosophy:
- Clear contracts: Define operations all platforms must support
- Modular design: Each platform implements this interface
- Self-contained: No external dependencies
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PRStatus(Enum):
    """Pull request status."""
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"
    DRAFT = "draft"


@dataclass
class PRInfo:
    """Pull request information."""
    number: int
    title: str
    status: PRStatus
    url: str
    source_branch: str
    target_branch: str
    author: str


class PlatformOperations(ABC):
    """Abstract interface for platform operations.

    All platform bridges must implement these 5 operations:
    1. create_pr - Create a new pull request
    2. get_pr - Get pull request information
    3. list_prs - List pull requests
    4. update_pr - Update pull request
    5. check_ci_status - Check CI status
    """

    @abstractmethod
    def create_pr(
        self,
        title: str,
        body: str,
        source_branch: str,
        target_branch: str = "main",
        draft: bool = False
    ) -> PRInfo:
        """Create a pull request.

        Args:
            title: PR title
            body: PR description
            source_branch: Source branch name
            target_branch: Target branch name (default: main)
            draft: Create as draft PR

        Returns:
            PRInfo with created PR details

        Raises:
            RuntimeError: If PR creation fails
            ValueError: If inputs are invalid
        """
        pass

    @abstractmethod
    def get_pr(self, pr_number: int) -> PRInfo:
        """Get pull request information.

        Args:
            pr_number: PR number/ID

        Returns:
            PRInfo with PR details

        Raises:
            RuntimeError: If PR retrieval fails
            ValueError: If PR not found
        """
        pass

    @abstractmethod
    def list_prs(
        self,
        status: Optional[PRStatus] = None,
        author: Optional[str] = None
    ) -> list[PRInfo]:
        """List pull requests.

        Args:
            status: Filter by status (default: all)
            author: Filter by author (default: all)

        Returns:
            List of PRInfo objects

        Raises:
            RuntimeError: If listing fails
        """
        pass

    @abstractmethod
    def update_pr(
        self,
        pr_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None
    ) -> PRInfo:
        """Update pull request.

        Args:
            pr_number: PR number/ID
            title: New title (optional)
            body: New description (optional)

        Returns:
            PRInfo with updated PR details

        Raises:
            RuntimeError: If update fails
            ValueError: If PR not found
        """
        pass

    @abstractmethod
    def check_ci_status(self, pr_number: int) -> dict:
        """Check CI status for pull request.

        Args:
            pr_number: PR number/ID

        Returns:
            Dict with CI status information:
            {
                "status": "success" | "failure" | "pending" | "skipped",
                "checks": [{"name": str, "status": str, "url": str}]
            }

        Raises:
            RuntimeError: If status check fails
            ValueError: If PR not found
        """
        pass
