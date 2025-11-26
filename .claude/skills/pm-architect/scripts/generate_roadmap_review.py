#!/usr/bin/env python3
"""
PM Architect - Weekly Roadmap Review using Claude Agent SDK.

Uses Claude Agent SDK to analyze roadmap alignment, goal progress, and
generate strategic recommendations for project direction.
"""

import asyncio
import json
import sys
from pathlib import Path

# Try to import Claude SDK
try:
    from claude_agent_sdk import ClaudeAgentOptions, query

    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False


def load_project_state(project_root: Path) -> dict | None:
    """Load PM state files for analysis.

    Args:
        project_root: Project root directory

    Returns:
        Dictionary with backlog, workstreams, and metrics, or None if not found
    """
    pm_state_dir = project_root / ".claude" / "pm_state"

    if not pm_state_dir.exists():
        return None

    state = {}

    # Load backlog
    backlog_file = pm_state_dir / "backlog.yaml"
    if backlog_file.exists():
        import yaml

        with open(backlog_file) as f:
            state["backlog"] = yaml.safe_load(f)

    # Load workstreams
    workstreams_file = pm_state_dir / "workstreams.yaml"
    if workstreams_file.exists():
        import yaml

        with open(workstreams_file) as f:
            state["workstreams"] = yaml.safe_load(f)

    # Load project config
    config_file = pm_state_dir / "project_config.yaml"
    if config_file.exists():
        import yaml

        with open(config_file) as f:
            state["config"] = yaml.safe_load(f)

    return state if state else None


def get_git_velocity_metrics(project_root: Path) -> str:
    """Get git-based velocity metrics (commits, PRs merged).

    Args:
        project_root: Project root directory

    Returns:
        Formatted string with velocity metrics
    """
    import subprocess
    from datetime import datetime, timedelta

    try:
        # Get commits in last 7 days
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        result = subprocess.run(
            [
                "git",
                "log",
                "--oneline",
                f"--since={week_ago}",
                "--all",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )

        commit_count = 0
        if result.returncode == 0:
            commit_count = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0

        # Get merged PRs in last 7 days using gh CLI
        pr_count = 0
        try:
            pr_result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--state",
                    "merged",
                    "--json",
                    "number,mergedAt",
                    "--limit",
                    "100",
                ],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if pr_result.returncode == 0:
                prs = json.loads(pr_result.stdout)
                # Count PRs merged in last 7 days
                week_ago_dt = datetime.now() - timedelta(days=7)
                pr_count = sum(
                    1
                    for pr in prs
                    if pr.get("mergedAt")
                    and datetime.fromisoformat(pr["mergedAt"].replace("Z", "+00:00")) > week_ago_dt
                )
        except Exception:
            pass

        return f"""
## Velocity Metrics (Last 7 Days)

- **Commits**: {commit_count}
- **PRs Merged**: {pr_count}
- **Daily Average**: {commit_count / 7:.1f} commits/day
"""

    except Exception as e:
        return f"\n## Velocity Metrics\n\nUnable to retrieve: {e}\n"


def get_milestone_progress(project_root: Path) -> str:
    """Get milestone and project progress.

    Args:
        project_root: Project root directory

    Returns:
        Formatted string with milestone progress
    """
    import subprocess

    try:
        # Get milestones using gh CLI
        result = subprocess.run(
            ["gh", "api", "repos/:owner/:repo/milestones", "--jq", "."],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            milestones = json.loads(result.stdout)
            if milestones:
                milestone_info = []
                for milestone in milestones[:5]:  # Limit to 5 most recent
                    title = milestone.get("title", "Unknown")
                    open_issues = milestone.get("open_issues", 0)
                    closed_issues = milestone.get("closed_issues", 0)
                    total = open_issues + closed_issues
                    progress = (closed_issues / total * 100) if total > 0 else 0
                    milestone_info.append(
                        f"- **{title}**: {closed_issues}/{total} ({progress:.0f}%)"
                    )

                return f"""
## Milestone Progress

{chr(10).join(milestone_info)}
"""

        return "\n## Milestone Progress\n\nNo active milestones found.\n"

    except Exception:
        return "\n## Milestone Progress\n\nUnable to retrieve (gh CLI not available)\n"


async def generate_roadmap_review(project_root: Path, state: dict | None = None) -> str | None:
    """Generate weekly roadmap review using Claude Agent SDK.

    Args:
        project_root: Project root directory
        state: Optional pre-loaded project state

    Returns:
        Markdown roadmap review, or None if generation fails
    """
    if not CLAUDE_SDK_AVAILABLE:
        print("Error: Claude SDK not available", file=sys.stderr)
        return None

    # Load state if not provided
    if state is None:
        state = load_project_state(project_root)

    # Gather context
    velocity_metrics = get_git_velocity_metrics(project_root)
    milestone_progress = get_milestone_progress(project_root)

    # Format state for analysis
    state_context = ""
    if state:
        config = state.get("config", {})
        goals = config.get("goals", [])

        state_context = f"""
## Project Configuration

**Project Name**: {config.get("name", "Unknown")}
**Project Type**: {config.get("type", "Unknown")}
**Quality Bar**: {config.get("quality_bar", "Unknown")}

**Project Goals**:
{chr(10).join(f"- {goal}" for goal in goals) if goals else "- No goals defined"}

## Current Project State

### Backlog Summary
{json.dumps(state.get("backlog", {}), indent=2)}

### Active Workstreams
{json.dumps(state.get("workstreams", {}), indent=2)}
"""
    else:
        state_context = "\n## Current Project State\n\nNo PM state files found. This may be a new project or PM Architect has not been initialized.\n"

    # Build comprehensive prompt
    from datetime import datetime

    week_num = datetime.now().strftime("%Y-W%V")

    prompt = f"""You are the PM Architect performing a strategic weekly roadmap review.

{state_context}

{velocity_metrics}

{milestone_progress}

## Task

Generate a comprehensive weekly roadmap review in markdown format for **Week {week_num}** with the following sections:

1. **Executive Summary** (3-4 sentences)
   - Overall strategic health of the project
   - Alignment with project goals
   - Key achievements this week
   - Critical strategic concerns

2. **Goal Progress Analysis**
   - For each project goal, assess:
     - Current status (On Track / At Risk / Blocked)
     - Progress made this week
     - Remaining work estimate
     - Blockers or dependencies
   - If no goals defined, recommend creating strategic goals

3. **Velocity and Capacity Analysis**
   - Analyze velocity trends (improving/stable/declining)
   - Compare actual vs planned velocity
   - Team capacity assessment
   - Bottleneck identification
   - Recommendations for velocity improvement

4. **Roadmap Alignment**
   - Are current workstreams aligned with project goals?
   - Are we working on the right things?
   - Should priorities be adjusted?
   - Recommended focus shifts

5. **Strategic Risks and Opportunities**
   - Technical debt accumulation
   - Dependencies on external factors
   - Market or competitive considerations
   - Opportunities to accelerate delivery
   - Resource constraints

6. **Milestone and Release Planning**
   - Progress toward next milestone/release
   - Are we on track for commitments?
   - Should milestone dates be adjusted?
   - Recommended scope adjustments

7. **Recommendations for Next Week**
   - Top 3-5 strategic priorities
   - Backlog grooming needs
   - Team focus areas
   - Process improvements
   - Items requiring stakeholder decisions

8. **Long-term Outlook** (2-4 weeks ahead)
   - Upcoming challenges or opportunities
   - Planning needs
   - Resource requirements

Use markdown formatting with clear headers, bullet points, and emphasis where appropriate.
Be strategic and forward-looking. Use emojis sparingly for visual clarity (✅, ⚠️, 🚫, 📊, 🎯, 🚀).

Generate the roadmap review now:
"""

    try:
        # Configure SDK
        options = ClaudeAgentOptions(
            cwd=str(project_root),
            permission_mode="bypassPermissions",
        )

        # Collect response
        response_parts = []
        async for message in query(prompt=prompt, options=options):
            if hasattr(message, "text"):
                response_parts.append(message.text)
            elif hasattr(message, "content"):
                response_parts.append(str(message.content))

        # Join all parts
        review = "".join(response_parts)
        return review if review.strip() else None

    except Exception as e:
        print(f"Error generating roadmap review: {e}", file=sys.stderr)
        return None


def main():
    """Main entry point for roadmap review generation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate weekly roadmap review using Claude Agent SDK"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: stdout)",
    )

    args = parser.parse_args()

    if not CLAUDE_SDK_AVAILABLE:
        print("Error: claude-agent-sdk not installed", file=sys.stderr)
        print("Install with: pip install claude-agent-sdk", file=sys.stderr)
        sys.exit(1)

    # Generate review
    review = asyncio.run(generate_roadmap_review(args.project_root))

    if not review:
        print("Error: Failed to generate roadmap review", file=sys.stderr)
        sys.exit(1)

    # Output review
    if args.output:
        args.output.write_text(review)
        print(f"Roadmap review written to {args.output}", file=sys.stderr)
    else:
        print(review)

    sys.exit(0)


if __name__ == "__main__":
    main()
