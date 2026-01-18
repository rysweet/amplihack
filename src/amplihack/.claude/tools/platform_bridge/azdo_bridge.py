"""Azure DevOps bridge implementation using az CLI.

Philosophy:
- Reuse existing tools: Uses az CLI infrastructure from .claude/scenarios/az-devops-tools
- Zero-BS: All functions work, no stubs
- Error handling: Clear error messages with context
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add az-devops-tools to path to import common utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scenarios" / "az-devops-tools"))

from common import AzCliWrapper, load_config

from .operations import PlatformOperations, PRInfo, PRStatus


class AzDoBridge(PlatformOperations):
    """Azure DevOps platform bridge using az CLI."""

    def __init__(self, repo_path: str = "."):
        """Initialize Azure DevOps bridge.

        Args:
            repo_path: Path to git repository (default: current directory)
        """
        self.repo_path = repo_path
        self._check_az_cli()

        # Load configuration
        config = load_config()
        self.org = config.get("org")
        self.project = config.get("project")

        if not self.org or not self.project:
            raise RuntimeError(
                "Azure DevOps organization and project must be configured. "
                "Use 'az devops configure' or set AZURE_DEVOPS_ORG_URL and AZURE_DEVOPS_PROJECT"
            )

        self.wrapper = AzCliWrapper(org=self.org, project=self.project)
        self.repository = self.project  # Use project name as default repo

    def _check_az_cli(self) -> None:
        """Check if az CLI is available."""
        try:
            subprocess.run(
                ["az", "--version"],
                capture_output=True,
                check=True,
                timeout=5
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "az CLI not found. Install from https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"
            )

    def _sanitize_error(self, error_msg: str) -> str:
        """Sanitize error messages to remove sensitive data.

        Args:
            error_msg: Raw error message

        Returns:
            Sanitized error message
        """
        # Remove authentication tokens (ghp_, gho_, etc.)
        error_msg = re.sub(r'gh[ps]_\w+', '***TOKEN***', error_msg)

        # Remove passwords from URLs
        error_msg = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', error_msg)

        # Remove file paths that might contain sensitive info
        error_msg = re.sub(r'/home/[^/]+/\.', '/home/***/.',  error_msg)
        error_msg = re.sub(r'C:\\Users\\[^\\]+\\\.', r'C:\Users\***\.', error_msg)

        # Remove Azure DevOps PAT tokens (52 character base64 strings)
        error_msg = re.sub(r'PAT token \w+', 'PAT token ***', error_msg)
        error_msg = re.sub(r'\b[A-Za-z0-9]{52}\b', '***PAT***', error_msg)

        # Generic credential sanitization
        if 'credential' in error_msg.lower() or 'auth' in error_msg.lower():
            error_msg = re.sub(r'token[:\s]+\w+', 'token: ***', error_msg, flags=re.IGNORECASE)
            error_msg = re.sub(r'password[:\s]+\w+', 'password: ***', error_msg, flags=re.IGNORECASE)

        return error_msg

    def _parse_pr_status(self, azdo_status: str) -> PRStatus:
        """Parse Azure DevOps PR status to PRStatus.

        Args:
            azdo_status: Azure DevOps status (active, completed, abandoned, draft)

        Returns:
            PRStatus enum value
        """
        status_lower = azdo_status.lower()
        if status_lower == "active" or status_lower == "draft":
            return PRStatus.OPEN
        elif status_lower == "completed":
            return PRStatus.MERGED
        elif status_lower == "abandoned":
            return PRStatus.CLOSED
        else:
            return PRStatus.OPEN  # Default fallback

    def create_pr(
        self,
        title: str,
        body: str,
        source_branch: str,
        target_branch: str = "main",
        draft: bool = False
    ) -> PRInfo:
        """Create Azure DevOps pull request."""
        # Input validation
        if not title or not title.strip():
            raise ValueError("PR title cannot be empty")
        if len(title) > 4000:
            raise ValueError("PR title too long (max 4000 characters)")
        if '\n' in title or '\r' in title:
            raise ValueError("PR title cannot contain newlines")

        # Build command
        cmd = [
            "repos", "pr", "create",
            "--repository", self.repository,
            "--source-branch", source_branch,
            "--target-branch", target_branch,
            "--title", title,
            "--output", "json"
        ]

        if body:
            cmd.extend(["--description", body])

        if draft:
            cmd.append("--draft")

        # Create PR
        result = self.wrapper.devops_command(cmd, timeout=60)

        if not result.success:
            raise RuntimeError(f"Failed to create PR: {result.stderr}")

        try:
            pr_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse PR response: {e}")

        # Parse response
        pr_id = pr_data.get("pullRequestId", 0)
        is_draft = pr_data.get("isDraft", False)

        # Build PR URL
        pr_url = (
            pr_data.get("url", "")
            .replace("_apis/git/repositories", "_git")
            .replace("/pullRequests/", "/pullrequest/")
        )

        return PRInfo(
            number=pr_id,
            title=pr_data.get("title", title),
            status=PRStatus.DRAFT if is_draft else PRStatus.OPEN,
            url=pr_url,
            source_branch=source_branch,
            target_branch=target_branch,
            author=pr_data.get("createdBy", {}).get("displayName", "unknown")
        )

    def get_pr(self, pr_number: int) -> PRInfo:
        """Get Azure DevOps pull request information."""
        if pr_number <= 0:
            raise ValueError(f"Invalid PR number: {pr_number}")

        # Get PR details
        cmd = [
            "repos", "pr", "show",
            "--id", str(pr_number),
            "--output", "json"
        ]

        result = self.wrapper.devops_command(cmd, timeout=30)

        if not result.success:
            if "does not exist" in result.stderr.lower():
                raise ValueError(f"PR #{pr_number} not found")
            raise RuntimeError(f"Failed to get PR: {result.stderr}")

        try:
            pr_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse PR data: {e}")

        # Parse status
        azdo_status = pr_data.get("status", "active")
        is_draft = pr_data.get("isDraft", False)
        status = PRStatus.DRAFT if is_draft else self._parse_pr_status(azdo_status)

        # Build PR URL
        pr_url = (
            pr_data.get("url", "")
            .replace("_apis/git/repositories", "_git")
            .replace("/pullRequests/", "/pullrequest/")
        )

        return PRInfo(
            number=pr_data.get("pullRequestId", pr_number),
            title=pr_data.get("title", ""),
            status=status,
            url=pr_url,
            source_branch=pr_data.get("sourceRefName", "").replace("refs/heads/", ""),
            target_branch=pr_data.get("targetRefName", "").replace("refs/heads/", ""),
            author=pr_data.get("createdBy", {}).get("displayName", "unknown")
        )

    def list_prs(
        self,
        status: Optional[PRStatus] = None,
        author: Optional[str] = None
    ) -> list[PRInfo]:
        """List Azure DevOps pull requests."""
        # Build command
        cmd = [
            "repos", "pr", "list",
            "--repository", self.repository,
            "--output", "json"
        ]

        # Add status filter
        if status:
            if status == PRStatus.OPEN:
                cmd.extend(["--status", "active"])
            elif status == PRStatus.CLOSED:
                cmd.extend(["--status", "abandoned"])
            elif status == PRStatus.MERGED:
                cmd.extend(["--status", "completed"])
            # DRAFT handled in post-processing

        # Add author filter
        if author:
            cmd.extend(["--creator", author])

        result = self.wrapper.devops_command(cmd, timeout=30)

        if not result.success:
            raise RuntimeError(f"Failed to list PRs: {result.stderr}")

        try:
            prs_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse PR list: {e}")

        prs = []
        for pr_data in prs_data:
            is_draft = pr_data.get("isDraft", False)
            azdo_status = pr_data.get("status", "active")
            pr_status = PRStatus.DRAFT if is_draft else self._parse_pr_status(azdo_status)

            # Filter by draft status if requested
            if status == PRStatus.DRAFT and not is_draft:
                continue

            # Build PR URL
            pr_url = (
                pr_data.get("url", "")
                .replace("_apis/git/repositories", "_git")
                .replace("/pullRequests/", "/pullrequest/")
            )

            prs.append(PRInfo(
                number=pr_data.get("pullRequestId", 0),
                title=pr_data.get("title", ""),
                status=pr_status,
                url=pr_url,
                source_branch=pr_data.get("sourceRefName", "").replace("refs/heads/", ""),
                target_branch=pr_data.get("targetRefName", "").replace("refs/heads/", ""),
                author=pr_data.get("createdBy", {}).get("displayName", "unknown")
            ))

        return prs

    def update_pr(
        self,
        pr_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None
    ) -> PRInfo:
        """Update Azure DevOps pull request."""
        if pr_number <= 0:
            raise ValueError(f"Invalid PR number: {pr_number}")

        if not title and not body:
            raise ValueError("Must provide title or body to update")

        # Validate title if provided
        if title:
            if not title.strip():
                raise ValueError("PR title cannot be empty")
            if len(title) > 4000:
                raise ValueError("PR title too long (max 4000 characters)")
            if '\n' in title or '\r' in title:
                raise ValueError("PR title cannot contain newlines")

        # Build command
        cmd = [
            "repos", "pr", "update",
            "--id", str(pr_number),
            "--output", "json"
        ]

        if title:
            cmd.extend(["--title", title])
        if body:
            cmd.extend(["--description", body])

        result = self.wrapper.devops_command(cmd, timeout=30)

        if not result.success:
            raise RuntimeError(f"Failed to update PR: {result.stderr}")

        # Get updated PR info
        return self.get_pr(pr_number)

    def check_ci_status(self, pr_number: int) -> dict:
        """Check CI status for Azure DevOps pull request."""
        if pr_number <= 0:
            raise ValueError(f"Invalid PR number: {pr_number}")

        # Get PR details first to get the last merge commit
        pr_info = self.get_pr(pr_number)

        # Get PR details with commits
        cmd = [
            "repos", "pr", "show",
            "--id", str(pr_number),
            "--output", "json"
        ]

        result = self.wrapper.devops_command(cmd, timeout=30)

        if not result.success:
            raise RuntimeError(f"Failed to get PR details: {result.stderr}")

        try:
            pr_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse PR data: {e}")

        # Get merge status (represents overall CI/policy status)
        merge_status = pr_data.get("mergeStatus", "")

        # Map merge status to our CI status
        if merge_status == "succeeded":
            overall_status = "success"
        elif merge_status == "conflicts" or merge_status == "failure":
            overall_status = "failure"
        elif merge_status == "queued":
            overall_status = "pending"
        else:
            overall_status = "pending"

        # For more detailed checks, we would need to query build/policy APIs
        # For now, return basic status based on merge status
        checks = [{
            "name": "Azure DevOps Policies",
            "status": overall_status,
            "url": pr_info.url
        }]

        return {
            "status": overall_status,
            "checks": checks
        }

    # Convenience methods for common operations

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[list[str]] = None
    ) -> dict:
        """Create Azure DevOps work item (issue) with validation.

        Args:
            title: Work item title
            body: Work item description
            labels: Optional tags/labels (Azure DevOps calls these tags)

        Returns:
            Dict with success, issue_number, url, error
        """
        try:
            # Input validation
            if not title or not title.strip():
                raise ValueError("Issue title cannot be empty")
            if len(title) > 4000:
                raise ValueError("Issue title too long (max 4000 characters)")
            if '\n' in title or '\r' in title:
                raise ValueError("Issue title cannot contain newlines")
            if '\x00' in title:
                raise ValueError("Issue title contains invalid null character")

            if not body or not body.strip():
                raise ValueError("Issue body cannot be empty")
            if len(body) > 65536:
                raise ValueError("Issue body too long (max 65536 characters)")
            if '\x00' in body:
                raise ValueError("Issue body contains invalid null character")

            # Build command
            cmd = [
                "boards", "work-item", "create",
                "--type", "Issue",
                "--title", title,
                "--description", body,
                "--output", "json"
            ]

            if labels:
                cmd.extend(["--fields", f"System.Tags={';'.join(labels)}"])

            # Create work item
            result = self.wrapper.devops_command(cmd, timeout=60)

            if not result.success:
                raise RuntimeError(f"Failed to create issue: {result.stderr}")

            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Failed to parse issue response: {e}")

            # Build work item URL
            work_item_id = data.get("id", 0)
            work_item_url = (
                f"https://dev.azure.com/{self.org}/{self.project}/"
                f"_workitems/edit/{work_item_id}"
            )

            return {
                "success": True,
                "issue_number": work_item_id,
                "url": work_item_url
            }

        except (ValueError, RuntimeError) as e:
            return {
                "success": False,
                "error": self._sanitize_error(str(e)),
                "issue_number": 0,
                "url": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": self._sanitize_error(f"Unexpected error: {str(e)}"),
                "issue_number": 0,
                "url": ""
            }

    def create_draft_pr(
        self,
        title: str,
        body: str,
        branch: str,
        base: str = "main"
    ) -> dict:
        """Create draft pull request with validation.

        Args:
            title: PR title
            body: PR description
            branch: Source branch name
            base: Target branch name (default: main)

        Returns:
            Dict with success, pr_number, url, error
        """
        try:
            # Input validation
            if not title or not title.strip():
                raise ValueError("PR title cannot be empty")
            if len(title) > 4000:
                raise ValueError("PR title too long (max 4000 characters)")
            if '\n' in title or '\r' in title:
                raise ValueError("PR title cannot contain newlines")
            if '\x00' in title:
                raise ValueError("PR title contains invalid null character")

            if not branch or not branch.strip():
                raise ValueError("Branch name cannot be empty")
            if len(branch) > 255:
                raise ValueError("Branch name too long (max 255 characters)")
            if '\x00' in branch:
                raise ValueError("Branch name contains invalid null character")

            # Validate branch name against dangerous chars
            dangerous_chars = [';', '|', '&', '>', '<', '`', '$', '(', ')']
            for char in dangerous_chars:
                if char in branch:
                    raise ValueError(f"Branch name contains invalid character: {char}")

            # Check for path traversal
            if '..' in branch:
                raise ValueError("Branch name contains path traversal attempt")

            if len(body) > 65536:
                raise ValueError("PR body too long (max 65536 characters)")
            if '\x00' in body:
                raise ValueError("PR body contains invalid null character")

            # Build command
            cmd = [
                "repos", "pr", "create",
                "--repository", self.repository,
                "--source-branch", branch,
                "--target-branch", base,
                "--title", title,
                "--description", body,
                "--draft", "true",
                "--output", "json"
            ]

            # Create draft PR
            result = self.wrapper.devops_command(cmd, timeout=60)

            if not result.success:
                raise RuntimeError(f"Failed to create PR: {result.stderr}")

            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Failed to parse PR response: {e}")

            # Build PR URL
            pr_id = data.get("pullRequestId", 0)
            pr_url = (
                data.get("url", "")
                .replace("_apis/git/repositories", "_git")
                .replace("/pullRequests/", "/pullrequest/")
            )

            return {
                "success": True,
                "pr_number": pr_id,
                "url": pr_url
            }

        except (ValueError, RuntimeError) as e:
            return {
                "success": False,
                "error": self._sanitize_error(str(e)),
                "pr_number": 0,
                "url": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": self._sanitize_error(f"Unexpected error: {str(e)}"),
                "pr_number": 0,
                "url": ""
            }

    def mark_pr_ready(self, pr_number: int) -> dict:
        """Mark draft PR as ready for review.

        Args:
            pr_number: PR number to mark ready

        Returns:
            Dict with success, pr_number, url, error
        """
        try:
            # Input validation
            if not isinstance(pr_number, int):
                raise TypeError("PR number must be an integer")
            if pr_number <= 0:
                raise ValueError("PR number must be a positive integer")

            # Mark PR ready (remove draft status)
            cmd = [
                "repos", "pr", "update",
                "--id", str(pr_number),
                "--draft", "false",
                "--output", "json"
            ]

            result = self.wrapper.devops_command(cmd, timeout=30)

            if not result.success:
                raise RuntimeError(f"Failed to mark PR ready: {result.stderr}")

            # Get updated PR info
            pr_info = self.get_pr(pr_number)

            return {
                "success": True,
                "pr_number": pr_info.number,
                "url": pr_info.url
            }

        except (TypeError, ValueError, RuntimeError) as e:
            return {
                "success": False,
                "error": str(e),
                "pr_number": pr_number if isinstance(pr_number, int) else 0,
                "url": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": self._sanitize_error(f"Unexpected error: {str(e)}"),
                "pr_number": pr_number if isinstance(pr_number, int) else 0,
                "url": ""
            }

    def add_pr_comment(self, pr_number: int, comment: str) -> dict:
        """Add comment to pull request.

        Args:
            pr_number: PR number to comment on
            comment: Comment text

        Returns:
            Dict with success, comment_id, url, error
        """
        try:
            # Input validation
            if pr_number <= 0:
                raise ValueError("PR number must be a positive integer")

            if not comment or not comment.strip():
                raise ValueError("Comment cannot be empty")
            if len(comment) > 65536:
                raise ValueError("Comment too long (max 65536 characters)")
            if '\x00' in comment:
                raise ValueError("Comment contains invalid null character")

            # Add comment (create a thread with the comment)
            cmd = [
                "repos", "pr", "create-thread",
                "--id", str(pr_number),
                "--comment-text", comment,
                "--output", "json"
            ]

            result = self.wrapper.devops_command(cmd, timeout=30)

            if not result.success:
                raise RuntimeError(f"Failed to add comment: {result.stderr}")

            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Failed to parse comment response: {e}")

            # Extract comment ID and URL
            thread_id = data.get("id", "")
            pr_info = self.get_pr(pr_number)
            comment_url = f"{pr_info.url}?_a=files&discussionId={thread_id}"

            return {
                "success": True,
                "comment_id": str(thread_id),
                "url": comment_url
            }

        except (ValueError, RuntimeError) as e:
            return {
                "success": False,
                "error": self._sanitize_error(str(e)),
                "comment_id": "",
                "url": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": self._sanitize_error(f"Unexpected error: {str(e)}"),
                "comment_id": "",
                "url": ""
            }


# Alias for test compatibility
AzureDevOpsBridge = AzDoBridge
