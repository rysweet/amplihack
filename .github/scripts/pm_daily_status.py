#!/usr/bin/env python3
"""PM Daily Status Report Generator.

Generates daily project status by:
- Analyzing CI/CD health
- Tracking open issues and PRs
- Identifying failing tests or workflows
- Providing actionable insights

Uses GitHub API for data collection.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _run_gh_command(args: list[str], description: str) -> list[dict[str, Any]] | None:
    """Run a gh CLI command and return parsed JSON, or None on failure."""
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(
            f"ERROR: {description} failed (exit code {result.returncode}): {result.stderr.strip()}",
            file=sys.stderr,
        )
        # Also print to stdout for GitHub Actions visibility
        print(f"ERROR: {description} failed")
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(
            f"ERROR: {description} returned invalid JSON: {result.stdout[:200]}",
            file=sys.stderr,
        )
        print(f"ERROR: {description} returned invalid JSON")
        return None


def get_workflow_runs() -> list[dict[str, Any]] | None:
    """Fetch recent workflow runs. Returns None on failure."""
    return _run_gh_command(
        [
            "gh",
            "run",
            "list",
            "--limit",
            "10",
            "--json",
            "status,conclusion,name,createdAt,workflowName",
        ],
        "fetch workflow runs",
    )


def get_open_issues_count() -> int | None:
    """Get count of open issues. Returns None on failure."""
    issues = _run_gh_command(
        ["gh", "issue", "list", "--limit", "200", "--json", "number"],
        "fetch open issues",
    )
    if issues is None:
        return None
    return len(issues)


def get_open_prs_count() -> dict[str, int] | None:
    """Get count of open PRs by state. Returns None on failure."""
    prs = _run_gh_command(
        ["gh", "pr", "list", "--limit", "200", "--json", "number,isDraft"],
        "fetch open PRs",
    )
    if prs is None:
        return None
    return {
        "total": len(prs),
        "draft": len([pr for pr in prs if pr.get("isDraft")]),
        "ready": len([pr for pr in prs if not pr.get("isDraft")]),
    }


def analyze_ci_health(workflow_runs: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Analyze CI/CD health from recent workflow runs. Returns unknown status if workflow_runs is None."""
    if workflow_runs is None or not workflow_runs:
        return {
            "status": "unknown",
            "passing": 0,
            "failing": 0,
            "pending": 0,
            "total": 0,
            "fetch_failed": workflow_runs is None,
        }

    passing = failing = pending = 0
    for r in workflow_runs:
        conclusion = r.get("conclusion")
        if conclusion == "success":
            passing += 1
        elif conclusion == "failure":
            failing += 1
        elif r.get("status") == "in_progress":
            pending += 1

    # Determine overall health
    if failing == 0 and passing > 0:
        status = "healthy"
    elif failing > 0 and failing <= passing:
        status = "degraded"
    elif failing > passing:
        status = "unhealthy"
    else:
        status = "unknown"

    return {
        "status": status,
        "passing": passing,
        "failing": failing,
        "pending": pending,
        "total": len(workflow_runs),
        "fetch_failed": False,
    }


def get_failing_workflows(workflow_runs: list[dict[str, Any]] | None) -> list[str] | None:
    """Get list of failing workflow names. Returns None if workflow_runs is None."""
    if workflow_runs is None:
        return None

    failing = []
    seen = set()

    for run in workflow_runs:
        if run.get("conclusion") == "failure":
            name = run.get("workflowName", "Unknown")
            if name not in seen:
                failing.append(name)
                seen.add(name)

    return failing


def generate_status_report(
    ci_health: dict[str, Any],
    open_issues: int | None,
    open_prs: dict[str, int] | None,
    failing_workflows: list[str] | None,
) -> str:
    """Generate daily status report. Shows explicit warnings when data fetches fail."""

    status_emoji = {
        "healthy": "🟢",
        "degraded": "🟡",
        "unhealthy": "🔴",
        "unknown": "⚪",
    }

    # Track which data fetches failed
    fetch_failures = []
    if ci_health.get("fetch_failed"):
        fetch_failures.append("CI/CD status")
    if open_issues is None:
        fetch_failures.append("Issue count")
    if open_prs is None:
        fetch_failures.append("PR count")

    report_parts = [
        f"## PM Daily Status - {datetime.now().strftime('%Y-%m-%d')}",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
    ]

    # Add data quality warning banner if any fetches failed
    if fetch_failures:
        report_parts.extend(
            [
                "### ⚠️ INCOMPLETE DATA - SOME FETCHES FAILED",
                "",
                "This report contains partial data. The following information could not be fetched:",
            ]
        )
        for failure in fetch_failures:
            report_parts.append(f"- {failure}")
        report_parts.extend(
            [
                "",
                "**Action Required**: Check workflow logs for details: `gh run view --log`",
                "",
                "---",
                "",
            ]
        )

    report_parts.extend(
        [
            "### Project Health",
            "",
            f"**Overall Status**: {status_emoji.get(ci_health['status'], '⚪')} {ci_health['status'].title()}",
            "",
            "### CI/CD Status",
            "",
        ]
    )

    if ci_health.get("fetch_failed"):
        report_parts.append("⚠️ **Data fetch failed** - CI/CD status unavailable")
    else:
        report_parts.extend(
            [
                f"- **Recent Runs** ({ci_health['total']} analyzed):",
                f"  - Passing: {ci_health['passing']}",
                f"  - Failing: {ci_health['failing']}",
                f"  - In Progress: {ci_health['pending']}",
            ]
        )

    report_parts.append("")

    if failing_workflows is not None and failing_workflows:
        report_parts.extend(
            [
                "**Failing Workflows**:",
            ]
        )
        for workflow in failing_workflows:
            report_parts.append(f"- {workflow}")
        report_parts.append("")

    report_parts.extend(
        [
            "### Work In Progress",
            "",
        ]
    )

    # Show explicit failure indicators for missing data
    if open_issues is None:
        report_parts.append("**Open Issues**: ⚠️ Data fetch failed")
    else:
        report_parts.append(f"**Open Issues**: {open_issues}")

    if open_prs is None:
        report_parts.append("**Open PRs**: ⚠️ Data fetch failed")
    else:
        report_parts.append(
            f"**Open PRs**: {open_prs['total']} ({open_prs['ready']} ready, {open_prs['draft']} draft)"
        )

    report_parts.append("")

    # Generate recommendations
    report_parts.extend(
        [
            "### Daily Recommendations",
            "",
        ]
    )

    recommendations = []

    # Add warning if any data is missing
    if fetch_failures:
        recommendations.append("- ⚠️ Verify data manually - some metrics unavailable")

    if ci_health["status"] == "unhealthy":
        recommendations.append("- 🔴 CI/CD unhealthy - prioritize fixing failing workflows")
    elif ci_health["status"] == "degraded":
        recommendations.append("- 🟡 CI/CD degraded - review recent failures")

    if failing_workflows:
        recommendations.append(f"- Fix {len(failing_workflows)} failing workflow(s)")

    if open_prs is not None and open_prs["ready"] > 0:
        recommendations.append(f"- {open_prs['ready']} PR(s) ready for review")

    if open_prs is not None and open_prs["draft"] > 5:
        recommendations.append(
            f"- {open_prs['draft']} draft PRs - consider completing or closing stale drafts"
        )

    if not recommendations and not fetch_failures:
        recommendations.append("- All systems operational - maintain current trajectory")

    report_parts.extend(recommendations)

    report_parts.extend(
        [
            "",
            "### Quick Actions",
            "",
            "- [ ] Review and merge ready PRs",
            "- [ ] Address failing CI/CD workflows",
            "- [ ] Triage new issues",
            "",
            "---",
            "*Generated by PM Architect automation*",
        ]
    )

    return "\n".join(report_parts)


def main():
    """Main entry point for daily status generation."""
    try:
        print("Fetching project status data...")

        workflow_runs = get_workflow_runs()
        open_issues = get_open_issues_count()
        open_prs = get_open_prs_count()

        ci_health = analyze_ci_health(workflow_runs)
        failing_workflows = get_failing_workflows(workflow_runs)

        # Check if any critical fetches failed
        has_failures = workflow_runs is None or open_issues is None or open_prs is None

        print("Generating daily status report...")
        report = generate_status_report(
            ci_health,
            open_issues,
            open_prs,
            failing_workflows,
        )

        # Write to file
        output_file = Path("status_report.md")
        output_file.write_text(report)

        print(f"Status report written to {output_file}")

        # Also output to console for GitHub Actions summary
        print("\n" + report)

        # Exit with error code if any data fetches failed
        # This ensures workflow fails and issues are visible in GitHub Actions UI
        if has_failures:
            print(
                "\n⚠️ WARNING: Some data fetches failed. Check logs above for details.",
                file=sys.stderr,
            )
            sys.exit(1)

    except Exception as e:
        print(f"Error generating status report: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
