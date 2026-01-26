"""GitHub bridge implementation using gh CLI.

Philosophy:
- Reuse existing tools: Uses gh CLI that's already used in project
- Zero-BS: All functions work, no stubs
- Error handling: Clear error messages with context
"""

import json
import re
import subprocess

from .operations import PlatformOperations, PRInfo, PRStatus


class GitHubBridge(PlatformOperations):
    """GitHub platform bridge using gh CLI."""

    def __init__(self, repo_path: str = ".", timeout: int = 30):
        """Initialize GitHub bridge.

        Args:
            repo_path: Path to git repository (default: current directory)
            timeout: Command timeout in seconds (default: 30)
        """
        if timeout <= 0 or timeout > 300:
            raise ValueError(
                "Timeout must be between 1 and 300 seconds (timeout too large or unreasonable)"
            )

        self.repo_path = repo_path
        self.timeout = timeout
        self._check_gh_cli()

    def _check_gh_cli(self) -> None:
        """Check if gh CLI is available."""
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("gh CLI not found. Install from https://cli.github.com/")

    def _sanitize_error(self, error_msg: str) -> str:
        """Sanitize error messages to remove sensitive data.

        Args:
            error_msg: Raw error message

        Returns:
            Sanitized error message
        """
        # Remove authentication tokens (ghp_, gho_, etc.)
        error_msg = re.sub(r"gh[ps]_\w+", "***TOKEN***", error_msg)

        # Remove passwords from URLs
        error_msg = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", error_msg)

        # Remove file paths that might contain sensitive info
        error_msg = re.sub(r"/home/[^/]+/\.", "/home/***/.", error_msg)
        error_msg = re.sub(r"C:\\Users\\[^\\]+\\\.", r"C:\Users\***\.", error_msg)

        # Remove Azure DevOps PAT tokens
        error_msg = re.sub(r"[A-Za-z0-9]{52}", "***PAT***", error_msg)

        # Generic credential sanitization
        if "credential" in error_msg.lower() or "auth" in error_msg.lower():
            error_msg = re.sub(r"token[:\s]+\w+", "token: ***", error_msg, flags=re.IGNORECASE)
            error_msg = re.sub(
                r"password[:\s]+\w+", "password: ***", error_msg, flags=re.IGNORECASE
            )

        return error_msg

    def _run_gh(self, args: list[str], context: str = "") -> str:
        """Run gh command safely.

        Args:
            args: Command arguments (excluding 'gh')
            context: Context for error messages

        Returns:
            Command stdout

        Raises:
            RuntimeError: If command fails
        """
        try:
            result = subprocess.run(
                ["gh"] + args,
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout,
                cwd=self.repo_path,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = "GitHub command failed"
            if context:
                error_msg += f" ({context})"
            error_msg += f": {e.stderr}"
            raise RuntimeError(error_msg)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"GitHub command timed out ({context})")

    def _parse_pr_status(self, gh_state: str, merged: bool = False) -> PRStatus:
        """Parse GitHub PR state to PRStatus.

        Args:
            gh_state: GitHub state (OPEN, CLOSED, MERGED, DRAFT)
            merged: Whether PR is merged

        Returns:
            PRStatus enum value
        """
        if merged or gh_state == "MERGED":
            return PRStatus.MERGED
        if gh_state == "DRAFT":
            return PRStatus.DRAFT
        if gh_state == "OPEN":
            return PRStatus.OPEN
        if gh_state == "CLOSED":
            return PRStatus.CLOSED
        return PRStatus.OPEN  # Default fallback

    def create_pr(
        self,
        title: str,
        body: str,
        source_branch: str,
        target_branch: str = "main",
        draft: bool = False,
    ) -> PRInfo:
        """Create GitHub pull request."""
        # Input validation
        if not title or not title.strip():
            raise ValueError("PR title cannot be empty")
        if len(title) > 4000:
            raise ValueError("PR title too long (max 4000 characters)")
        if "\n" in title or "\r" in title:
            raise ValueError("PR title cannot contain newlines")

        # Build command
        cmd = [
            "pr",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--base",
            target_branch,
            "--head",
            source_branch,
        ]
        if draft:
            cmd.append("--draft")

        # Create PR and get URL
        pr_url = self._run_gh(cmd, "creating PR")

        # Extract PR number from URL
        pr_number = int(pr_url.rstrip("/").split("/")[-1])

        # Get full PR info
        return self.get_pr(pr_number)

    def get_pr(self, pr_number: int) -> PRInfo:
        """Get GitHub pull request information."""
        if pr_number <= 0:
            raise ValueError(f"Invalid PR number: {pr_number}")

        # Get PR details in JSON format
        output = self._run_gh(
            [
                "pr",
                "view",
                str(pr_number),
                "--json",
                "number,title,state,url,headRefName,baseRefName,author,isDraft,merged",
            ],
            f"getting PR #{pr_number}",
        )

        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse PR data: {e}")

        # Determine status
        is_draft = data.get("isDraft", False)
        is_merged = data.get("merged", False)
        gh_state = "DRAFT" if is_draft else data.get("state", "OPEN")
        status = self._parse_pr_status(gh_state, is_merged)

        return PRInfo(
            number=data["number"],
            title=data["title"],
            status=status,
            url=data["url"],
            source_branch=data["headRefName"],
            target_branch=data["baseRefName"],
            author=data["author"]["login"] if isinstance(data["author"], dict) else data["author"],
        )

    def list_prs(self, status: PRStatus | None = None, author: str | None = None) -> list[PRInfo]:
        """List GitHub pull requests."""
        # Build command
        cmd = [
            "pr",
            "list",
            "--json",
            "number,title,state,url,headRefName,baseRefName,author,isDraft,merged",
        ]

        # Add filters
        if status:
            if status == PRStatus.OPEN:
                cmd.extend(["--state", "open"])
            elif status == PRStatus.CLOSED:
                cmd.extend(["--state", "closed"])
            elif status == PRStatus.MERGED:
                cmd.extend(["--state", "merged"])
            # DRAFT handled in post-processing

        if author:
            cmd.extend(["--author", author])

        output = self._run_gh(cmd, "listing PRs")

        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse PR list: {e}")

        prs = []
        for pr_data in data:
            is_draft = pr_data.get("isDraft", False)
            is_merged = pr_data.get("merged", False)
            gh_state = "DRAFT" if is_draft else pr_data.get("state", "OPEN")
            pr_status = self._parse_pr_status(gh_state, is_merged)

            # Filter by draft status if requested
            if status == PRStatus.DRAFT and not is_draft:
                continue

            prs.append(
                PRInfo(
                    number=pr_data["number"],
                    title=pr_data["title"],
                    status=pr_status,
                    url=pr_data["url"],
                    source_branch=pr_data["headRefName"],
                    target_branch=pr_data["baseRefName"],
                    author=pr_data["author"]["login"]
                    if isinstance(pr_data["author"], dict)
                    else pr_data["author"],
                )
            )

        return prs

    def update_pr(
        self, pr_number: int, title: str | None = None, body: str | None = None
    ) -> PRInfo:
        """Update GitHub pull request."""
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
            if "\n" in title or "\r" in title:
                raise ValueError("PR title cannot contain newlines")

        # Build command
        cmd = ["pr", "edit", str(pr_number)]
        if title:
            cmd.extend(["--title", title])
        if body:
            cmd.extend(["--body", body])

        self._run_gh(cmd, f"updating PR #{pr_number}")

        # Get updated PR info
        return self.get_pr(pr_number)

    def check_ci_status(self, pr_number: int) -> dict:
        """Check CI status for GitHub pull request."""
        if pr_number <= 0:
            raise ValueError(f"Invalid PR number: {pr_number}")

        # Get check runs
        output = self._run_gh(
            ["pr", "checks", str(pr_number), "--json", "name,status,conclusion,detailsUrl"],
            f"checking CI status for PR #{pr_number}",
        )

        try:
            checks_data = json.loads(output)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse CI status: {e}")

        checks = []
        overall_status = "success"

        for check in checks_data:
            # Map GitHub check conclusion to our status
            conclusion = check.get("conclusion", "").lower()
            check_status = check.get("status", "").lower()

            if check_status == "in_progress" or check_status == "queued":
                status = "pending"
                overall_status = "pending"
            elif conclusion == "success":
                status = "success"
            elif conclusion == "skipped" or conclusion == "neutral":
                status = "skipped"
            else:
                status = "failure"
                if overall_status != "pending":
                    overall_status = "failure"

            checks.append(
                {"name": check["name"], "status": status, "url": check.get("detailsUrl", "")}
            )

        return {"status": overall_status, "checks": checks}

    # Convenience methods for common operations

    def create_issue(self, title: str, body: str, labels: list[str] | None = None) -> dict:
        """Create GitHub issue with validation.

        Args:
            title: Issue title
            body: Issue description
            labels: Optional labels to add

        Returns:
            Dict with success, issue_number, url, error
        """
        try:
            # Input validation
            if not title or not title.strip():
                raise ValueError("Issue title cannot be empty")
            if len(title) > 4000:
                raise ValueError("Issue title too long (max 4000 characters)")
            if "\n" in title or "\r" in title:
                raise ValueError("Issue title cannot contain newlines")
            if "\x00" in title:
                raise ValueError("Issue title contains invalid null character")

            if not body or not body.strip():
                raise ValueError("Issue body cannot be empty")
            if len(body) > 65536:
                raise ValueError("Issue body too long (max 65536 characters)")
            if "\x00" in body:
                raise ValueError("Issue body contains invalid null character")

            # Build command
            cmd = ["issue", "create", "--title", title, "--body", body, "--json", "number,url"]

            if labels:
                cmd.extend(["--label", ",".join(labels)])

            # Create issue
            output = self._run_gh(cmd, "creating issue")

            try:
                data = json.loads(output)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Failed to parse issue response: {e}")

            return {
                "success": True,
                "issue_number": data.get("number", 0),
                "url": data.get("url", ""),
            }

        except (ValueError, RuntimeError) as e:
            return {
                "success": False,
                "error": self._sanitize_error(str(e)),
                "issue_number": 0,
                "url": "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": self._sanitize_error(f"Unexpected error: {e!s}"),
                "issue_number": 0,
                "url": "",
            }

    def create_draft_pr(self, title: str, body: str, branch: str, base: str = "main") -> dict:
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
            if "\n" in title or "\r" in title:
                raise ValueError("PR title cannot contain newlines")
            if "\x00" in title:
                raise ValueError("PR title contains invalid null character")

            if not branch or not branch.strip():
                raise ValueError("Branch name cannot be empty")
            if len(branch) > 255:
                raise ValueError("Branch name too long (max 255 characters)")
            if "\x00" in branch:
                raise ValueError("Branch name contains invalid null character")

            # Validate branch name against dangerous chars
            dangerous_chars = [";", "|", "&", ">", "<", "`", "$", "(", ")"]
            for char in dangerous_chars:
                if char in branch:
                    raise ValueError(f"Branch name contains invalid character: {char}")

            # Check for path traversal
            if ".." in branch:
                raise ValueError("Branch name contains path traversal attempt")

            if len(body) > 65536:
                raise ValueError("PR body too long (max 65536 characters)")
            if "\x00" in body:
                raise ValueError("PR body contains invalid null character")

            # Build command
            cmd = [
                "pr",
                "create",
                "--draft",
                "--title",
                title,
                "--body",
                body,
                "--head",
                branch,
                "--base",
                base,
                "--json",
                "number,url",
            ]

            # Create draft PR
            output = self._run_gh(cmd, "creating draft PR")

            try:
                data = json.loads(output)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Failed to parse PR response: {e}")

            return {"success": True, "pr_number": data.get("number", 0), "url": data.get("url", "")}

        except (ValueError, RuntimeError) as e:
            return {
                "success": False,
                "error": self._sanitize_error(str(e)),
                "pr_number": 0,
                "url": "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": self._sanitize_error(f"Unexpected error: {e!s}"),
                "pr_number": 0,
                "url": "",
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

            # Mark PR ready
            self._run_gh(["pr", "ready", str(pr_number)], f"marking PR #{pr_number} ready")

            # Get updated PR info
            pr_info = self.get_pr(pr_number)

            return {"success": True, "pr_number": pr_info.number, "url": pr_info.url}

        except (TypeError, ValueError, RuntimeError) as e:
            return {
                "success": False,
                "error": str(e),
                "pr_number": pr_number if isinstance(pr_number, int) else 0,
                "url": "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": self._sanitize_error(f"Unexpected error: {e!s}"),
                "pr_number": pr_number if isinstance(pr_number, int) else 0,
                "url": "",
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
            if "\x00" in comment:
                raise ValueError("Comment contains invalid null character")

            # Add comment
            output = self._run_gh(
                ["pr", "comment", str(pr_number), "--body", comment],
                f"adding comment to PR #{pr_number}",
            )

            # gh pr comment returns the comment URL
            comment_url = output.strip() if output else ""

            return {
                "success": True,
                "comment_id": comment_url.split("#")[-1] if "#" in comment_url else "",
                "url": comment_url,
            }

        except (ValueError, RuntimeError) as e:
            return {
                "success": False,
                "error": self._sanitize_error(str(e)),
                "comment_id": "",
                "url": "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": self._sanitize_error(f"Unexpected error: {e!s}"),
                "comment_id": "",
                "url": "",
            }
