#!/usr/bin/env python3
"""PM Roadmap Review Generator.

Generates weekly roadmap analysis by:
- Analyzing open issues and PRs
- Comparing actual vs planned progress
- Identifying blockers
- Providing velocity metrics
- Generating actionable recommendations

Uses GitHub API for data collection and Claude for analysis.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent.parent


def get_week_number() -> str:
    """Get ISO week number for current week."""
    return datetime.now().strftime("%Y-W%V")


def fetch_issues_created_this_week() -> list[dict[str, Any]]:
    """Fetch issues created in the past week."""
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    result = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--json",
            "number,title,state,createdAt,labels,assignees",
            "--search",
            f"created:>={week_ago}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return json.loads(result.stdout)


def fetch_prs_merged_this_week() -> list[dict[str, Any]]:
    """Fetch PRs merged in the past week."""
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "merged",
            "--json",
            "number,title,mergedAt,labels,author",
            "--search",
            f"merged:>={week_ago}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return json.loads(result.stdout)


def fetch_open_prs() -> list[dict[str, Any]]:
    """Fetch currently open PRs."""
    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--json",
            "number,title,createdAt,labels,author,isDraft",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return json.loads(result.stdout)


def fetch_blocked_issues() -> list[dict[str, Any]]:
    """Fetch issues labeled as blocked."""
    result = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--label",
            "blocked",
            "--json",
            "number,title,labels,assignees",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return json.loads(result.stdout)


def analyze_priority_distribution(issues: list[dict[str, Any]]) -> dict[str, int]:
    """Analyze priority distribution across issues."""
    priorities = {"critical": 0, "high": 0, "medium": 0, "low": 0, "none": 0}

    for issue in issues:
        labels = [label["name"] for label in issue.get("labels", [])]

        if any("priority:critical" in label for label in labels):
            priorities["critical"] += 1
        elif any("priority:high" in label for label in labels):
            priorities["high"] += 1
        elif any("priority:medium" in label for label in labels):
            priorities["medium"] += 1
        elif any("priority:low" in label for label in labels):
            priorities["low"] += 1
        else:
            priorities["none"] += 1

    return priorities


def generate_roadmap_report(
    week_num: str,
    new_issues: list[dict[str, Any]],
    merged_prs: list[dict[str, Any]],
    open_prs: list[dict[str, Any]],
    blocked_issues: list[dict[str, Any]],
) -> str:
    """Generate comprehensive roadmap review report."""

    priority_dist = analyze_priority_distribution(
        new_issues + [{"labels": pr.get("labels", [])} for pr in open_prs]
    )

    report_parts = [
        f"## Weekly Roadmap Review - {week_num}",
        "",
        f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "### Velocity Analysis",
        "",
        f"**Issues Created This Week**: {len(new_issues)}",
        f"**PRs Merged This Week**: {len(merged_prs)}",
        f"**Open PRs**: {len(open_prs)} ({len([pr for pr in open_prs if pr.get('isDraft')])} drafts)",
        "",
        "**Priority Distribution**:",
    ]

    for priority, count in priority_dist.items():
        if count > 0:
            report_parts.append(f"- {priority.title()}: {count}")

    report_parts.extend(["", "### Recent Achievements", ""])

    if merged_prs:
        for pr in merged_prs[:5]:  # Show top 5
            author = pr.get("author", {}).get("login", "unknown")
            report_parts.append(f"- #{pr['number']}: {pr['title']} (@{author})")
        if len(merged_prs) > 5:
            report_parts.append(f"- ... and {len(merged_prs) - 5} more")
    else:
        report_parts.append("- No PRs merged this week")

    report_parts.extend(["", "### Active Work (Open PRs)", ""])

    if open_prs:
        for pr in open_prs[:5]:  # Show top 5
            author = pr.get("author", {}).get("login", "unknown")
            status = " [DRAFT]" if pr.get("isDraft") else ""
            report_parts.append(f"- #{pr['number']}: {pr['title']} (@{author}){status}")
        if len(open_prs) > 5:
            report_parts.append(f"- ... and {len(open_prs) - 5} more")
    else:
        report_parts.append("- No open PRs")

    report_parts.extend(["", "### Blockers", ""])

    if blocked_issues:
        for issue in blocked_issues:
            assignees = ", ".join([f"@{a['login']}" for a in issue.get("assignees", [])])
            assignee_str = f" ({assignees})" if assignees else ""
            report_parts.append(f"- #{issue['number']}: {issue['title']}{assignee_str}")
    else:
        report_parts.append("- No blocked issues")

    report_parts.extend(
        [
            "",
            "### Recommendations",
            "",
        ]
    )

    # Generate recommendations based on data
    recommendations = []

    if len(blocked_issues) > 0:
        recommendations.append(f"- Address {len(blocked_issues)} blocked issue(s) as priority")

    if len(open_prs) > 10:
        recommendations.append(f"- High PR count ({len(open_prs)}), consider focusing on reviews")

    draft_count = len([pr for pr in open_prs if pr.get("isDraft")])
    if draft_count > 5:
        recommendations.append(f"- {draft_count} draft PRs - may need completion or closure")

    if priority_dist.get("critical", 0) > 0:
        recommendations.append(
            f"- {priority_dist['critical']} critical priority item(s) need immediate attention"
        )

    if not recommendations:
        recommendations.append("- Continue current trajectory - healthy project state")

    report_parts.extend(recommendations)

    report_parts.extend(
        [
            "",
            "### Next Steps",
            "",
            "- [ ] Review blocked issues and remove blockers",
            "- [ ] Complete draft PRs or close if no longer needed",
            "- [ ] Prioritize critical/high priority items",
            "- [ ] Maintain review velocity for open PRs",
            "",
            "---",
            "*Generated by PM Architect automation*",
        ]
    )

    return "\n".join(report_parts)


def main():
    """Main entry point for roadmap review generation."""
    try:
        print("Fetching project data...")

        week_num = get_week_number()
        new_issues = fetch_issues_created_this_week()
        merged_prs = fetch_prs_merged_this_week()
        open_prs = fetch_open_prs()
        blocked_issues = fetch_blocked_issues()

        print(f"Generating roadmap review for {week_num}...")
        report = generate_roadmap_report(
            week_num,
            new_issues,
            merged_prs,
            open_prs,
            blocked_issues,
        )

        # Write to file
        output_file = Path("roadmap_review.md")
        output_file.write_text(report)

        print(f"Roadmap review written to {output_file}")

        # Also output to console for GitHub Actions summary
        print("\n" + report)

    except subprocess.CalledProcessError as e:
        print(f"Error running gh command: {e}", file=sys.stderr)
        print(f"Stdout: {e.stdout}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error generating roadmap review: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
