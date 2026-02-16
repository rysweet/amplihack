#!/usr/bin/env python3
"""Check for drift between local awesome-copilot integration and upstream releases.

Uses the GitHub API (via `gh api`) to check the latest commits on
github/awesome-copilot and compares against a stored timestamp.

Reports: CURRENT, DRIFT_DETECTED, or ERROR.

Usage:
    python check_drift.py
"""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = "github/awesome-copilot"
STATE_FILE = Path.home() / ".amplihack" / "awesome-copilot-sync-state.json"


def load_state() -> dict:
    """Load the last-checked state from disk.

    Returns:
        State dictionary with last_checked, latest_commit_sha, and
        latest_commit_date keys, or an empty dict if no state exists.
    """
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state: dict) -> None:
    """Persist sync state to disk.

    Args:
        state: Dictionary with last_checked, latest_commit_sha, and
               latest_commit_date fields.
    """
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def fetch_latest_commits(limit: int = 10) -> list[dict]:
    """Fetch the latest commits from the awesome-copilot repository.

    Uses `gh api` for authenticated access to avoid rate limiting.

    Args:
        limit: Maximum number of commits to fetch.

    Returns:
        List of commit dictionaries with sha and commit.committer.date fields.

    Raises:
        RuntimeError: If the gh CLI call fails.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{REPO}/commits",
                "-q",
                f".[:{limit}] | [.[] | {{sha: .sha, date: .commit.committer.date, message: .commit.message}}]",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except FileNotFoundError:
        raise RuntimeError("gh CLI not found. Install it from https://cli.github.com/")
    except subprocess.TimeoutExpired:
        raise RuntimeError("GitHub API request timed out after 15 seconds")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"gh api call failed: {stderr}")

    try:
        commits = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse GitHub API response: {result.stdout[:200]}")

    if not isinstance(commits, list):
        raise RuntimeError(
            f"Unexpected API response format: expected list, got {type(commits).__name__}"
        )

    return commits


def count_new_commits(commits: list[dict], since: str) -> int:
    """Count commits newer than the given ISO timestamp.

    Args:
        commits: List of commit dicts with a 'date' field (ISO 8601).
        since: ISO 8601 timestamp to compare against.

    Returns:
        Number of commits with a date strictly after `since`.
    """
    try:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        # If we cannot parse the stored date, treat all commits as new
        return len(commits)

    count = 0
    for commit in commits:
        commit_date_str = commit.get("date", "")
        try:
            commit_dt = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00"))
            if commit_dt > since_dt:
                count += 1
        except (ValueError, AttributeError):
            continue
    return count


def check_drift() -> dict:
    """Check for drift between local state and upstream awesome-copilot.

    Returns:
        Dictionary with keys:
            status: "CURRENT", "DRIFT_DETECTED", or "ERROR"
            last_checked: ISO timestamp of previous check (or None)
            latest_upstream_commit: ISO timestamp of newest upstream commit
            new_commit_count: Number of new commits since last check
            message: Human-readable summary
    """
    state = load_state()
    last_checked = state.get("last_checked")
    last_commit_date = state.get("latest_commit_date")

    try:
        commits = fetch_latest_commits(limit=10)
    except RuntimeError as e:
        return {
            "status": "ERROR",
            "last_checked": last_checked,
            "latest_upstream_commit": None,
            "new_commit_count": 0,
            "message": str(e),
        }

    if not commits:
        return {
            "status": "ERROR",
            "last_checked": last_checked,
            "latest_upstream_commit": None,
            "new_commit_count": 0,
            "message": f"No commits found in {REPO}",
        }

    latest = commits[0]
    latest_sha = latest.get("sha", "unknown")
    latest_date = latest.get("date", "")

    now = datetime.now(UTC).isoformat()

    # Determine drift
    if last_commit_date:
        new_count = count_new_commits(commits, last_commit_date)
    else:
        # First run: no baseline, report as current after recording state
        new_count = 0

    if new_count > 0:
        status = "DRIFT_DETECTED"
        message = (
            f"Found {new_count} new commit(s) in {REPO} since last check. "
            f"Latest: {latest_sha[:8]} ({latest_date})"
        )
    else:
        status = "CURRENT"
        message = f"No new commits in {REPO} since last check."

    # Update state
    new_state = {
        "last_checked": now,
        "latest_commit_sha": latest_sha,
        "latest_commit_date": latest_date,
    }
    save_state(new_state)

    return {
        "status": status,
        "last_checked": last_checked or now,
        "latest_upstream_commit": latest_date,
        "new_commit_count": new_count,
        "message": message,
    }


def main() -> int:
    """Run drift check and print results.

    Returns:
        Exit code: 0 for CURRENT, 1 for DRIFT_DETECTED, 2 for ERROR.
    """
    result = check_drift()

    status = result["status"]
    print(f"awesome-copilot sync status: {status}")
    print(f"Last checked: {result['last_checked'] or 'never'}")
    print(f"Latest upstream commit: {result['latest_upstream_commit'] or 'unknown'}")

    if status == "DRIFT_DETECTED":
        print(f"New commits since last check: {result['new_commit_count']}")

    if result["message"]:
        print(f"Details: {result['message']}")

    if status == "CURRENT":
        return 0
    if status == "DRIFT_DETECTED":
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
