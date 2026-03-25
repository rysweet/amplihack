# File: src/amplihack/tools/supply_chain_audit/github_client.py
"""Thin wrapper around gh CLI for GitHub API access.

Uses subprocess.run with shell=False, explicit timeouts, and
input validation to prevent injection attacks.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time

logger = logging.getLogger(__name__)

_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]+(/[a-zA-Z0-9._-]+)?$")
_BLOCKLIST_CHARS = set(";|&$'\"\\`\x00")
_DEFAULT_TIMEOUT = 30
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0


class GitHubClient:
    """GitHub API client via gh CLI subprocess calls."""

    def validate_repo_name(self, name: str) -> None:
        """Validate a repo name (owner/repo format) against injection."""
        if any(c in name for c in _BLOCKLIST_CHARS):
            raise ValueError(f"Invalid character in repo name: {name!r}")
        if not _SAFE_NAME_RE.match(name):
            raise ValueError(f"Invalid repo name format: {name!r}")

    def validate_org_name(self, name: str) -> None:
        """Validate an org name against injection."""
        if any(c in name for c in _BLOCKLIST_CHARS):
            raise ValueError(f"Invalid character in org name: {name!r}")
        if not re.match(r"^[a-zA-Z0-9._-]+$", name):
            raise ValueError(f"Invalid org name format: {name!r}")

    def _run_gh(
        self,
        args: list[str],
        *,
        timeout: int = _DEFAULT_TIMEOUT,
        parse_json: bool = True,
    ) -> str | list | dict:
        """Execute a gh CLI command safely with retry on rate limit.

        Args:
            args: Command arguments (gh is prepended).
            timeout: Subprocess timeout in seconds.
            parse_json: If True, parse stdout as JSON.

        Returns:
            Parsed JSON (dict/list) or raw stdout string.

        Raises:
            RuntimeError: On gh errors, timeouts, or invalid output.
        """
        cmd = ["gh"] + args
        last_error = None

        for attempt in range(_MAX_RETRIES):
            try:
                result = subprocess.run(
                    cmd,
                    shell=False,
                    timeout=timeout,
                    capture_output=True,
                    text=True,
                )
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"gh command timed out after {timeout}s: {' '.join(cmd)}")
            except FileNotFoundError:
                raise RuntimeError("gh CLI not found. Install from https://cli.github.com/")

            if result.returncode == 0:
                if parse_json:
                    try:
                        return json.loads(result.stdout)
                    except json.JSONDecodeError as e:
                        raise RuntimeError(f"Invalid JSON from gh: {e}")
                return result.stdout

            stderr = result.stderr.lower()
            if "rate limit" in stderr and attempt < _MAX_RETRIES - 1:
                delay = _RETRY_BASE_DELAY * (2**attempt)
                logger.warning(
                    "Rate limited, retrying in %.1fs (attempt %d/%d)",
                    delay,
                    attempt + 1,
                    _MAX_RETRIES,
                )
                time.sleep(delay)
                last_error = result.stderr
                continue

            # Log expiry (410) for run logs — return empty
            if "410" in stderr or "expired" in stderr:
                return "" if not parse_json else []

            # Sanitize stderr to avoid leaking tokens or internal paths
            safe_stderr = result.stderr[:200] if result.stderr else ""
            safe_stderr = re.sub(r"(ghp_|gho_|github_pat_)[A-Za-z0-9_]+", "[REDACTED]", safe_stderr)
            raise RuntimeError(f"gh command failed (exit {result.returncode}): {safe_stderr}")

        raise RuntimeError(f"gh command failed after {_MAX_RETRIES} retries: {last_error}")

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def list_org_repos(self, org: str) -> list[str]:
        """List all repository full names in an organization."""
        self.validate_org_name(org)
        data = self._run_gh(
            [
                "api",
                "--paginate",
                f"/orgs/{org}/repos",
                "--jq",
                ".[].full_name",
            ]
        )

        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                return [r["nameWithOwner"] for r in data]
            return [str(r) for r in data]
        if isinstance(data, str):
            stripped = data.strip()
            return [line.strip() for line in stripped.split("\n") if line.strip()]
        return []

    def get_workflow_runs(
        self,
        repo: str,
        created_after: str,
        created_before: str,
        max_runs: int = 100,
    ) -> list[dict]:
        """Get workflow runs for a repo within a date range."""
        self.validate_repo_name(repo)
        data = self._run_gh(
            [
                "run",
                "list",
                "--repo",
                repo,
                "--json",
                "databaseId,name,createdAt,headSha,status,conclusion",
                "--limit",
                str(max_runs),
                "--created",
                f"{created_after}..{created_before}",
            ]
        )
        if isinstance(data, list):
            return data[:max_runs]
        return []

    def get_run_logs(self, repo: str, run_id: int) -> str:
        """Get logs for a specific workflow run."""
        self.validate_repo_name(repo)
        result = self._run_gh(
            ["run", "view", str(run_id), "--repo", repo, "--log"],
            parse_json=False,
            timeout=60,
        )
        return result if isinstance(result, str) else ""

    def get_workflow_files(self, repo: str) -> list[dict]:
        """List workflow files in a repo's .github/workflows/ directory."""
        self.validate_repo_name(repo)
        try:
            data = self._run_gh(
                [
                    "api",
                    f"/repos/{repo}/contents/.github/workflows",
                    "--jq",
                    ".",
                ]
            )
            if isinstance(data, list):
                return data
            return []
        except RuntimeError as e:
            logger.warning("Failed to list workflow files for %s: %s", repo, e)
            return []

    def get_workflow_file_content(self, repo: str, path: str) -> str:
        """Get raw content of a workflow file from a repo."""
        self.validate_repo_name(repo)
        # Validate path: must be under .github/workflows, no traversal
        if ".." in path or any(c in path for c in _BLOCKLIST_CHARS):
            raise ValueError(f"Invalid workflow path: {path!r}")
        if not path.startswith(".github/workflows/"):
            raise ValueError(f"Workflow path must be under .github/workflows/: {path!r}")
        result = self._run_gh(
            [
                "api",
                f"/repos/{repo}/contents/{path}",
                "--jq",
                ".content",
                "-H",
                "Accept: application/vnd.github.raw+json",
            ],
            parse_json=False,
        )
        return result if isinstance(result, str) else ""

    def list_workflows(self, repo: str) -> list[dict]:
        """List workflows configured in a repository."""
        self.validate_repo_name(repo)
        try:
            data = self._run_gh(
                [
                    "api",
                    f"/repos/{repo}/actions/workflows",
                    "--jq",
                    ".workflows",
                ]
            )
            if isinstance(data, list):
                return data
            return []
        except RuntimeError as e:
            logger.warning("Failed to list workflows for %s: %s", repo, e)
            return []
