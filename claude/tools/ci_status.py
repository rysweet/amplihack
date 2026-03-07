#!/usr/bin/env python3
"""
CI Status Checker Tool

A simple Python wrapper around GitHub CLI (gh) for checking CI status.
Returns structured data about CI checks for branches, PRs, or commits.
"""

import json
import re
import subprocess
import sys


def run_gh_command(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """
    Run a gh CLI command with timeout.

    Args:
        args: List of arguments for gh command
        timeout: Command timeout in seconds

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            ["gh"] + args, check=False, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out after 30 seconds"
    except FileNotFoundError:
        return 1, "", "gh CLI not found. Please install GitHub CLI."
    except Exception as e:
        return 1, "", f"Error running command: {e}"


def get_current_branch() -> str | None:
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_pr_for_branch(branch: str) -> int | None:
    """Get PR number for the given branch if it exists."""
    code, stdout, stderr = run_gh_command(
        ["pr", "list", "--head", branch, "--json", "number", "--limit", "1"]
    )

    if code == 0 and stdout:
        try:
            data = json.loads(stdout)
            if data and len(data) > 0:
                return data[0].get("number")
        except json.JSONDecodeError:
            pass
    return None


def check_pr_checks(pr_number: int) -> dict:
    """Check CI status for a specific PR."""
    code, stdout, stderr = run_gh_command(
        [
            "pr",
            "checks",
            str(pr_number),
            "--json",
            "name,state,bucket,startedAt,completedAt,link,description",
        ]
    )

    if code != 0:
        return {"success": False, "error": f"Failed to get PR checks: {stderr}"}

    try:
        checks = json.loads(stdout) if stdout else []
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse PR checks output"}

    # Analyze check statuses using bucket field
    # bucket field categorizes state into: pass, fail, pending, skipping, or cancel
    total = len(checks)
    passed = sum(1 for c in checks if c.get("bucket") == "pass")
    failed = sum(1 for c in checks if c.get("bucket") == "fail")
    pending = sum(1 for c in checks if c.get("bucket") == "pending")
    skipped = sum(1 for c in checks if c.get("bucket") == "skipping")
    cancelled = sum(1 for c in checks if c.get("bucket") == "cancel")

    # Determine overall status
    if total == 0:
        status = "NO_CHECKS"
    elif failed > 0:
        status = "FAILING"
    elif pending > 0:
        status = "PENDING"
    elif passed == total:
        status = "PASSING"
    elif passed + skipped == total:
        status = "PASSING"  # Consider skipped as OK
    else:
        status = "MIXED"

    return {
        "success": True,
        "status": status,
        "checks": checks,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pending": pending,
            "skipped": skipped,
            "cancelled": cancelled,
        },
    }


def check_workflow_runs(branch: str | None = None, limit: int = 10) -> dict:
    """Check recent workflow runs for a branch or repo."""
    args = [
        "run",
        "list",
        "--json",
        "status,conclusion,name,headBranch,createdAt,url",
        "--limit",
        str(limit),
    ]

    if branch:
        args.extend(["--branch", branch])

    code, stdout, stderr = run_gh_command(args)

    if code != 0:
        return {"success": False, "error": f"Failed to get workflow runs: {stderr}"}

    try:
        runs = json.loads(stdout) if stdout else []
    except json.JSONDecodeError:
        return {"success": False, "error": "Failed to parse workflow runs output"}

    # Analyze run statuses
    total = len(runs)
    completed = sum(1 for r in runs if r.get("status") == "completed")
    successful = sum(1 for r in runs if r.get("conclusion") == "success")
    failed = sum(1 for r in runs if r.get("conclusion") == "failure")
    in_progress = sum(1 for r in runs if r.get("status") == "in_progress")

    # Determine overall status from recent runs
    if total == 0:
        status = "NO_RUNS"
    elif in_progress > 0:
        status = "RUNNING"
    elif failed > 0:
        status = "FAILING"
    elif successful == completed and completed > 0:
        status = "PASSING"
    else:
        status = "MIXED"

    return {
        "success": True,
        "status": status,
        "runs": runs,
        "summary": {
            "total": total,
            "completed": completed,
            "successful": successful,
            "failed": failed,
            "in_progress": in_progress,
        },
    }


def check_ci_status(reference: str | None = None) -> dict:
    """
    Check CI status for a given reference (PR number, branch, or current).

    Args:
        reference: Can be:
            - PR number (e.g., "123" or "#123")
            - Branch name (e.g., "main", "feature/xyz")
            - None (uses current branch)

    Returns:
        Dictionary with:
            - success: Whether the check completed successfully
            - status: Overall status (PASSING, FAILING, PENDING, etc.)
            - checks: List of individual checks (for PRs)
            - runs: List of workflow runs (for branches)
            - summary: Summary statistics
            - error: Error message if success is False
    """

    # Parse reference type
    pr_number = None
    branch = None

    if reference:
        # Check if it's a PR number
        pr_match = re.match(r"#?(\d+)$", reference)
        if pr_match:
            pr_number = int(pr_match.group(1))
        else:
            # Treat as branch name
            branch = reference
    else:
        # Use current branch
        branch = get_current_branch()
        if not branch:
            return {"success": False, "error": "Could not determine current git branch"}

    # If we have a branch, check if there's an associated PR
    if branch and not pr_number:
        pr_number = get_pr_for_branch(branch)

    # Check CI status
    if pr_number:
        result = check_pr_checks(pr_number)
        result["reference_type"] = "pr"
        result["pr_number"] = pr_number
        if branch:
            result["branch"] = branch
    else:
        result = check_workflow_runs(branch)
        result["reference_type"] = "branch"
        result["branch"] = branch

    return result


def format_summary(result: dict) -> str:
    """Format a human-readable summary of CI status."""
    if not result.get("success"):
        return f"Error: {result.get('error', 'Unknown error')}"

    lines = []
    status = result.get("status", "UNKNOWN")
    ref_type = result.get("reference_type", "unknown")

    # Header
    if ref_type == "pr":
        lines.append(f"CI Status for PR #{result.get('pr_number', '?')}: {status}")
    else:
        lines.append(f"CI Status for branch '{result.get('branch', '?')}': {status}")

    # Summary stats
    summary = result.get("summary", {})
    if summary:
        lines.append("")
        lines.append("Summary:")
        lines.append(f"  Total: {summary.get('total', 0)}")

        if ref_type == "pr":
            lines.append(f"  Passed: {summary.get('passed', 0)}")
            lines.append(f"  Failed: {summary.get('failed', 0)}")
            lines.append(f"  Pending: {summary.get('pending', 0)}")
            if summary.get("skipped", 0) > 0:
                lines.append(f"  Skipped: {summary.get('skipped', 0)}")
            if summary.get("cancelled", 0) > 0:
                lines.append(f"  Cancelled: {summary.get('cancelled', 0)}")
        else:
            lines.append(f"  Successful: {summary.get('successful', 0)}")
            lines.append(f"  Failed: {summary.get('failed', 0)}")
            lines.append(f"  In Progress: {summary.get('in_progress', 0)}")

    # Failed checks/runs details
    if status == "FAILING":
        lines.append("")
        if ref_type == "pr" and result.get("checks"):
            failed_checks = [c for c in result["checks"] if c.get("bucket") == "fail"]
            if failed_checks:
                lines.append("Failed checks:")
                for check in failed_checks[:5]:  # Show max 5
                    lines.append(f"  - {check.get('name', 'Unknown')}")
        elif result.get("runs"):
            failed_runs = [r for r in result["runs"] if r.get("conclusion") == "failure"]
            if failed_runs:
                lines.append("Failed runs:")
                for run in failed_runs[:5]:  # Show max 5
                    lines.append(f"  - {run.get('name', 'Unknown')}")

    return "\n".join(lines)


def main():
    """CLI interface for the CI status checker."""
    import argparse

    parser = argparse.ArgumentParser(description="Check CI status for GitHub branches and PRs")
    parser.add_argument(
        "reference",
        nargs="?",
        help="PR number (e.g., 123), branch name, or empty for current branch",
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of summary")

    args = parser.parse_args()

    # Check CI status
    result = check_ci_status(args.reference)

    # Output results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_summary(result))

    # Exit code based on status
    if not result.get("success") or result.get("status") == "FAILING":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
