#!/usr/bin/env python3
"""
PM Architect - Daily Status Report Generation using Claude Agent SDK.

Uses Claude Agent SDK to analyze project state and generate comprehensive
daily status reports with insights, blockers, and recommendations.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Optional

# Try to import Claude SDK
try:
    from claude_agent_sdk import ClaudeAgentOptions, query

    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False


def load_project_state(project_root: Path) -> Optional[Dict]:
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


def get_recent_git_activity(project_root: Path) -> str:
    """Get recent git commits and branch activity.

    Args:
        project_root: Project root directory

    Returns:
        Formatted string with recent git activity
    """
    import subprocess

    try:
        # Get recent commits (last 24 hours)
        result = subprocess.run(
            [
                "git",
                "log",
                "--oneline",
                "--since=24 hours ago",
                "--all",
                "--decorate",
                "--max-count=20",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout.strip():
            commits = result.stdout.strip()
            return f"""
## Recent Git Activity (Last 24 Hours)

```
{commits}
```
"""

        return "\n## Recent Git Activity\n\nNo commits in the last 24 hours.\n"

    except Exception as e:
        return f"\n## Recent Git Activity\n\nUnable to retrieve: {e}\n"


def get_open_prs_and_issues(project_root: Path) -> str:
    """Get count of open PRs and issues.

    Args:
        project_root: Project root directory

    Returns:
        Formatted string with PR/issue counts
    """
    import subprocess

    try:
        # Try to use gh CLI
        result = subprocess.run(
            ["gh", "pr", "list", "--json", "number,title,state"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )

        prs = []
        if result.returncode == 0:
            prs = json.loads(result.stdout)

        result = subprocess.run(
            ["gh", "issue", "list", "--json", "number,title,state"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )

        issues = []
        if result.returncode == 0:
            issues = json.loads(result.stdout)

        return f"""
## Open PRs and Issues

- **Open PRs**: {len(prs)}
- **Open Issues**: {len(issues)}
"""

    except Exception:
        return "\n## Open PRs and Issues\n\nUnable to retrieve (gh CLI not available)\n"


async def generate_status_report(project_root: Path, state: Optional[Dict] = None) -> Optional[str]:
    """Generate daily status report using Claude Agent SDK.

    Args:
        project_root: Project root directory
        state: Optional pre-loaded project state

    Returns:
        Markdown status report, or None if generation fails
    """
    if not CLAUDE_SDK_AVAILABLE:
        print("Error: Claude SDK not available", file=sys.stderr)
        return None

    # Load state if not provided
    if state is None:
        state = load_project_state(project_root)

    # Gather context
    git_activity = get_recent_git_activity(project_root)
    prs_issues = get_open_prs_and_issues(project_root)

    # Format state for analysis
    state_context = ""
    if state:
        state_context = f"""
## Current Project State

### Backlog Summary
{json.dumps(state.get("backlog", {}), indent=2)}

### Active Workstreams
{json.dumps(state.get("workstreams", {}), indent=2)}

### Project Configuration
{json.dumps(state.get("config", {}), indent=2)}
"""
    else:
        state_context = "\n## Current Project State\n\nNo PM state files found. This may be a new project or PM Architect has not been initialized.\n"

    # Build comprehensive prompt
    prompt = f"""You are the PM Architect analyzing project status for a daily status report.

{state_context}

{git_activity}

{prs_issues}

## Task

Generate a comprehensive daily status report in markdown format with the following sections:

1. **Executive Summary** (2-3 sentences)
   - Overall project health
   - Key accomplishments in last 24 hours
   - Critical issues requiring attention

2. **Workstream Status**
   - List each active workstream with status (RUNNING/BLOCKED/COMPLETED)
   - Progress indicators
   - Blockers or risks

3. **Backlog Health**
   - Number of items by priority (HIGH/MEDIUM/LOW)
   - Items marked as READY vs BLOCKED
   - Recommended focus areas

4. **Velocity and Metrics**
   - Items completed in last 24 hours
   - Items added to backlog
   - Trend analysis (velocity increasing/stable/declining)

5. **Blockers and Risks**
   - Critical blockers requiring immediate attention
   - Risk items that could impact delivery
   - Dependencies waiting on external factors

6. **Recommendations**
   - Top 3 priorities for the next 24 hours
   - Suggested actions for PM or team
   - Items that should be escalated

7. **Next Review**
   - Key milestones to track
   - Expected deliverables in next 24 hours

Use markdown formatting with clear headers, bullet points, and emphasis where appropriate.
Be concise but informative. Use emojis sparingly for visual clarity (✅, ⚠️, 🚫, 📊).

Generate the report now:
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
        report = "".join(response_parts)
        return report if report.strip() else None

    except Exception as e:
        print(f"Error generating status report: {e}", file=sys.stderr)
        return None


def main():
    """Main entry point for daily status generation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate daily PM status report using Claude Agent SDK"
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

    # Generate report
    report = asyncio.run(generate_status_report(args.project_root))

    if not report:
        print("Error: Failed to generate status report", file=sys.stderr)
        sys.exit(1)

    # Output report
    if args.output:
        args.output.write_text(report)
        print(f"Status report written to {args.output}", file=sys.stderr)
    else:
        print(report)

    sys.exit(0)


if __name__ == "__main__":
    main()
