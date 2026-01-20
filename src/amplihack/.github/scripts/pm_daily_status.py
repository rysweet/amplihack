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

REPO_ROOT = Path(__file__).parent.parent.parent


def get_workflow_runs() -> list[dict[str, Any]]:
    """Fetch recent workflow runs."""
    result = subprocess.run(
        [
            "gh",
            "run",
            "list",
            "--limit",
            "10",
            "--json",
            "status,conclusion,name,createdAt,workflowName",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return json.loads(result.stdout)


def get_open_issues_count() -> int:
    """Get count of open issues."""
    result = subprocess.run(
        ["gh", "issue", "list", "--json", "number"],
        capture_output=True,
        text=True,
        check=True,
    )

    return len(json.loads(result.stdout))


def get_open_prs_count() -> dict[str, int]:
    """Get count of open PRs by state."""
    result = subprocess.run(
        ["gh", "pr", "list", "--json", "number,isDraft"],
        capture_output=True,
        text=True,
        check=True,
    )

    prs = json.loads(result.stdout)
    return {
        "total": len(prs),
        "draft": len([pr for pr in prs if pr.get("isDraft")]),
        "ready": len([pr for pr in prs if not pr.get("isDraft")]),
    }


def analyze_ci_health(workflow_runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze CI/CD health from recent workflow runs."""
    if not workflow_runs:
        return {
            "status": "unknown",
            "passing": 0,
            "failing": 0,
            "pending": 0,
        }

    passing = len([r for r in workflow_runs if r.get("conclusion") == "success"])
    failing = len([r for r in workflow_runs if r.get("conclusion") == "failure"])
    pending = len([r for r in workflow_runs if r.get("status") == "in_progress"])

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
    }


def get_failing_workflows(workflow_runs: list[dict[str, Any]]) -> list[str]:
    """Get list of failing workflow names."""
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
    open_issues: int,
    open_prs: dict[str, int],
    failing_workflows: list[str],
) -> str:
    """Generate daily status report."""

    status_emoji = {
        "healthy": "🟢",
        "degraded": "🟡",
        "unhealthy": "🔴",
        "unknown": "⚪",
    }

    report_parts = [
        f"## PM Daily Status - {datetime.now().strftime('%Y-%m-%d')}",
        "",
        f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "### Project Health",
        "",
        f"**Overall Status**: {status_emoji.get(ci_health['status'], '⚪')} {ci_health['status'].title()}",
        "",
        "### CI/CD Status",
        "",
        f"- **Recent Runs** ({ci_health['total']} analyzed):",
        f"  - Passing: {ci_health['passing']}",
        f"  - Failing: {ci_health['failing']}",
        f"  - In Progress: {ci_health['pending']}",
        "",
    ]

    if failing_workflows:
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
            f"**Open Issues**: {open_issues}",
            f"**Open PRs**: {open_prs['total']} ({open_prs['ready']} ready, {open_prs['draft']} draft)",
            "",
        ]
    )

    # Generate recommendations
    report_parts.extend(
        [
            "### Daily Recommendations",
            "",
        ]
    )

    recommendations = []

    if ci_health["status"] == "unhealthy":
        recommendations.append("- 🔴 CI/CD unhealthy - prioritize fixing failing workflows")
    elif ci_health["status"] == "degraded":
        recommendations.append("- 🟡 CI/CD degraded - review recent failures")

    if failing_workflows:
        recommendations.append(f"- Fix {len(failing_workflows)} failing workflow(s)")

    if open_prs["ready"] > 0:
        recommendations.append(f"- {open_prs['ready']} PR(s) ready for review")

    if open_prs["draft"] > 5:
        recommendations.append(
            f"- {open_prs['draft']} draft PRs - consider completing or closing stale drafts"
        )

    if not recommendations:
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

    except subprocess.CalledProcessError as e:
        print(f"Error running gh command: {e}", file=sys.stderr)
        print(f"Stdout: {e.stdout}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error generating status report: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
