"""WorkSummaryGenerator - Generate work summaries from session state.

Generates WorkSummary from:
- TodoWrite state (from MessageCapture)
- Git repository state (via git commands)
- GitHub PR state (via gh CLI, optional)

Philosophy:
- Graceful degradation when tools unavailable
- No exceptions escape - return empty/None values
- Safe subprocess wrappers with timeouts
"""

import json
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass
class TodoState:
    """TodoWrite task state."""

    total: int
    completed: int
    in_progress: int
    pending: int

    def __post_init__(self):
        """Validate counts sum to total."""
        if self.completed + self.in_progress + self.pending != self.total:
            raise ValueError(
                f"Todo counts don't sum to total: {self.completed} + {self.in_progress} + {self.pending} != {self.total}"
            )


@dataclass
class GitState:
    """Git repository state."""

    current_branch: str | None
    has_uncommitted_changes: bool
    commits_ahead: int | None


@dataclass
class GitHubState:
    """GitHub PR state (optional, requires gh CLI)."""

    pr_number: int | None
    pr_state: str | None  # OPEN, CLOSED, MERGED
    ci_status: str | None  # SUCCESS, FAILURE, PENDING
    pr_mergeable: bool | None


@dataclass
class WorkSummary:
    """Complete work summary from all sources."""

    todo_state: TodoState
    git_state: GitState
    github_state: GitHubState


class WorkSummaryGenerator:
    """Generate WorkSummary from session state and external tools."""

    def __init__(self):
        self._cache: WorkSummary | None = None

    def generate(self, message_capture: Any) -> WorkSummary:
        """Generate complete WorkSummary.

        Args:
            message_capture: MessageCapture instance with TodoWrite history

        Returns:
            WorkSummary with all available information
        """
        if self._cache is not None:
            return self._cache

        todo_state = self._extract_todo_state(message_capture)
        git_state = self._extract_git_state()

        # Extract GitHub state using current branch
        branch = git_state.current_branch
        github_state = (
            self._extract_github_state(branch)
            if branch
            else GitHubState(pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None)
        )

        summary = WorkSummary(todo_state=todo_state, git_state=git_state, github_state=github_state)

        self._cache = summary
        return summary

    def _extract_todo_state(self, message_capture: Any) -> TodoState:
        """Extract TodoWrite state from MessageCapture.

        Args:
            message_capture: MessageCapture instance

        Returns:
            TodoState with counts
        """
        try:
            todo_calls = message_capture.find_tools("TodoWrite")
            if not todo_calls:
                return TodoState(total=0, completed=0, in_progress=0, pending=0)

            # Use latest TodoWrite call
            latest_call = todo_calls[-1]
            todos = latest_call.params.get("todos", [])

            # Count states
            completed = 0
            in_progress = 0
            pending = 0

            for todo in todos:
                if not isinstance(todo, dict):
                    continue
                status = todo.get("status")
                if status == "completed":
                    completed += 1
                elif status == "in_progress":
                    in_progress += 1
                elif status == "pending":
                    pending += 1

            total = completed + in_progress + pending
            return TodoState(
                total=total,
                completed=completed,
                in_progress=in_progress,
                pending=pending,
            )

        except Exception:
            # Graceful degradation
            return TodoState(total=0, completed=0, in_progress=0, pending=0)

    def _extract_git_state(self) -> GitState:
        """Extract Git repository state.

        Returns:
            GitState with current branch, uncommitted changes, commits ahead
        """
        try:
            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, "git")

            current_branch = result.stdout.strip()

            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, "git")

            has_uncommitted_changes = bool(result.stdout.strip())

            # Get commits ahead of upstream
            commits_ahead = None
            try:
                result = subprocess.run(
                    ["git", "rev-list", "--count", "@{u}..HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    commits_ahead = int(result.stdout.strip())
            except (subprocess.CalledProcessError, ValueError):
                # No upstream or error - leave as None
                pass

            return GitState(
                current_branch=current_branch,
                has_uncommitted_changes=has_uncommitted_changes,
                commits_ahead=commits_ahead,
            )

        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # Not in git repo or git not available
            return GitState(current_branch=None, has_uncommitted_changes=False, commits_ahead=None)

    def _extract_github_state(self, branch: str) -> GitHubState:
        """Extract GitHub PR state using gh CLI.

        Args:
            branch: Current git branch name

        Returns:
            GitHubState with PR information (or empty if unavailable)
        """
        try:
            # Query gh CLI for PR info
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--head",
                    branch,
                    "--json",
                    "number,state,statusCheckRollup,mergeable",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, "gh")

            prs = json.loads(result.stdout)
            if not prs:
                return GitHubState(pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None)

            # Use first PR (most recent)
            pr = prs[0]
            pr_number = pr.get("number")
            pr_state = pr.get("state")

            # Extract CI status from statusCheckRollup
            ci_status = None
            checks = pr.get("statusCheckRollup", [])
            if checks:
                # Look for overall status
                for check in checks:
                    status = check.get("status")
                    conclusion = check.get("conclusion")

                    if status == "IN_PROGRESS":
                        ci_status = "PENDING"
                        break
                    if status == "COMPLETED":
                        ci_status = conclusion  # SUCCESS, FAILURE, etc.
                        break

            # Extract mergeable state
            pr_mergeable = None
            mergeable = pr.get("mergeable")
            if mergeable == "MERGEABLE":
                pr_mergeable = True
            elif mergeable == "CONFLICTING":
                pr_mergeable = False

            return GitHubState(
                pr_number=pr_number,
                pr_state=pr_state,
                ci_status=ci_status,
                pr_mergeable=pr_mergeable,
            )

        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            json.JSONDecodeError,
            subprocess.TimeoutExpired,
        ):
            # gh CLI not available or error
            return GitHubState(pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None)

    def format_for_prompt(self, summary: WorkSummary) -> str:
        """Format WorkSummary for LLM prompt injection.

        Args:
            summary: WorkSummary to format

        Returns:
            Human-readable summary text
        """
        lines = ["Work Summary:"]

        # Todo state
        todo = summary.todo_state
        if todo.total > 0:
            lines.append(
                f"- Tasks: {todo.completed}/{todo.total} tasks completed, "
                f"{todo.in_progress} in progress, {todo.pending} pending"
            )
        else:
            lines.append("- Tasks: No TodoWrite entries")

        # Git state
        git = summary.git_state
        if git.current_branch:
            lines.append(f"- Branch: {git.current_branch}")
            if git.commits_ahead is not None:
                lines.append(f"- Commits ahead: {git.commits_ahead}")
            if git.has_uncommitted_changes:
                lines.append("- Uncommitted changes: Yes")
            else:
                lines.append("- Uncommitted changes: No")
        else:
            lines.append("- Git: Not in repository")

        # GitHub state
        gh = summary.github_state
        if gh.pr_number:
            lines.append(f"- PR: #{gh.pr_number} ({gh.pr_state})")
            if gh.ci_status:
                status_text = "passing" if gh.ci_status == "SUCCESS" else gh.ci_status
                lines.append(f"- CI Status: {status_text}")
            if gh.pr_mergeable is not None:
                mergeable_text = "yes" if gh.pr_mergeable else "no (conflicts)"
                lines.append(f"- Mergeable: {mergeable_text}")
        else:
            lines.append("- PR: not created")

        return "\n".join(lines)
