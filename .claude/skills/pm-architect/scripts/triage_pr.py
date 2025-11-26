#!/usr/bin/env python3
"""
PM Architect - PR Triage using Claude Agent SDK.

Uses Claude Agent SDK to analyze pull requests and provide intelligent
triage recommendations including priority, complexity, and reviewer suggestions.
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


def get_pr_details(project_root: Path, pr_number: int) -> dict | None:
    """Get PR details using gh CLI.

    Args:
        project_root: Project root directory
        pr_number: Pull request number

    Returns:
        Dictionary with PR details, or None if retrieval fails
    """
    import subprocess

    try:
        # Get PR details
        result = subprocess.run(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                "number,title,author,body,createdAt,files,additions,deletions,labels,reviews",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode == 0:
            return json.loads(result.stdout)

        return None

    except Exception as e:
        print(f"Error retrieving PR details: {e}", file=sys.stderr)
        return None


def get_pr_diff_summary(project_root: Path, pr_number: int) -> str:
    """Get summarized diff for PR.

    Args:
        project_root: Project root directory
        pr_number: Pull request number

    Returns:
        Formatted diff summary
    """
    import subprocess

    try:
        # Get diff stat
        result = subprocess.run(
            ["gh", "pr", "diff", str(pr_number), "--stat"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode == 0:
            return f"""
## File Changes Summary

```
{result.stdout.strip()}
```
"""

        return "\n## File Changes Summary\n\nUnable to retrieve diff.\n"

    except Exception:
        return "\n## File Changes Summary\n\nUnable to retrieve diff.\n"


def get_related_issues(project_root: Path, pr_body: str) -> str:
    """Extract and fetch related issues from PR body.

    Args:
        project_root: Project root directory
        pr_body: PR body text

    Returns:
        Formatted string with related issues
    """
    import re
    import subprocess

    # Extract issue references (#123, GH-123, fixes #123, etc.)
    issue_patterns = [
        r"#(\d+)",
        r"GH-(\d+)",
        r"(?:fixes|closes|resolves)\s+#(\d+)",
    ]

    issue_numbers = set()
    for pattern in issue_patterns:
        matches = re.finditer(pattern, pr_body, re.IGNORECASE)
        issue_numbers.update(match.group(1) for match in matches)

    if not issue_numbers:
        return "\n## Related Issues\n\nNo issue references found in PR description.\n"

    # Fetch issue details
    issue_details = []
    for issue_num in list(issue_numbers)[:5]:  # Limit to 5 issues
        try:
            result = subprocess.run(
                ["gh", "issue", "view", issue_num, "--json", "number,title,state,labels"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                issue = json.loads(result.stdout)
                labels = ", ".join(label["name"] for label in issue.get("labels", []))
                issue_details.append(
                    f"- #{issue['number']}: {issue['title']} [{issue['state']}] ({labels or 'no labels'})"
                )
        except Exception:
            continue

    if issue_details:
        return f"""
## Related Issues

{chr(10).join(issue_details)}
"""

    return "\n## Related Issues\n\nUnable to retrieve issue details.\n"


async def triage_pr(project_root: Path, pr_number: int) -> str | None:
    """Triage PR using Claude Agent SDK.

    Args:
        project_root: Project root directory
        pr_number: Pull request number

    Returns:
        Markdown triage analysis, or None if analysis fails
    """
    if not CLAUDE_SDK_AVAILABLE:
        print("Error: Claude SDK not available", file=sys.stderr)
        return None

    # Get PR details
    pr_details = get_pr_details(project_root, pr_number)
    if not pr_details:
        print(f"Error: Could not retrieve PR #{pr_number}", file=sys.stderr)
        return None

    # Gather additional context
    diff_summary = get_pr_diff_summary(project_root, pr_number)
    related_issues = get_related_issues(project_root, pr_details.get("body", ""))

    # Format PR details for analysis
    pr_context = f"""
## Pull Request Details

**Number**: #{pr_details["number"]}
**Title**: {pr_details["title"]}
**Author**: @{pr_details["author"]["login"]}
**Created**: {pr_details["createdAt"]}

**Labels**: {", ".join(label["name"] for label in pr_details.get("labels", [])) or "None"}

**Files Changed**: {len(pr_details.get("files", []))}
**Additions**: +{pr_details.get("additions", 0)} lines
**Deletions**: -{pr_details.get("deletions", 0)} lines

**Description**:
{pr_details.get("body", "No description provided.")}

{diff_summary}

{related_issues}

**Existing Reviews**:
{chr(10).join(f"- @{review['author']['login']}: {review['state']}" for review in pr_details.get("reviews", [])) or "- No reviews yet"}
"""

    # Build triage prompt
    prompt = f"""You are the PM Architect performing intelligent PR triage.

{pr_context}

## Task

Analyze this pull request and provide a comprehensive triage assessment in markdown format with the following sections:

1. **Priority Assessment** (Choose: CRITICAL / HIGH / MEDIUM / LOW)
   - Determine priority based on:
     - Impact on critical functionality
     - Blocking other work
     - Security or performance implications
     - Related to project goals or milestones
   - Provide rationale for priority level

2. **Complexity Analysis** (Choose: SIMPLE / MODERATE / COMPLEX / VERY COMPLEX)
   - Assess based on:
     - Number of files changed
     - Lines of code modified
     - Architectural changes
     - Cross-cutting concerns
     - Test coverage requirements
   - Estimated review time (minutes)

3. **Change Type Classification**
   - Feature / Enhancement / Bug Fix / Refactoring / Documentation / Tests / CI/CD / Security
   - Brief description of what this PR accomplishes

4. **Technical Review Checklist**
   - [ ] Code quality and best practices
   - [ ] Test coverage adequate
   - [ ] Documentation updated
   - [ ] Security considerations addressed
   - [ ] Performance implications reviewed
   - [ ] Backward compatibility maintained
   - [ ] CI/CD pipeline passes

5. **Suggested Reviewers** (2-3 people)
   - Based on files changed, suggest experts who should review
   - Consider: component ownership, expertise areas, recent contributors
   - If team structure unknown, suggest reviewer characteristics

6. **Potential Concerns or Risks**
   - Breaking changes
   - Performance impacts
   - Security vulnerabilities
   - Technical debt introduction
   - Missing test coverage
   - Documentation gaps

7. **Related Work**
   - Connection to project goals or roadmap
   - Dependencies on other PRs or issues
   - Follow-up work needed

8. **Recommendation**
   - Approve for review / Request changes before review / Needs discussion
   - Key areas reviewers should focus on
   - Suggested merge strategy (Squash / Rebase / Merge commit)

Use markdown formatting with clear headers, checkboxes, and emphasis where appropriate.
Be objective and thorough. Use emojis sparingly for visual clarity (✅, ⚠️, 🚫, 🔍, 🎯).

Generate the triage analysis now:
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
        triage = "".join(response_parts)
        return triage if triage.strip() else None

    except Exception as e:
        print(f"Error performing PR triage: {e}", file=sys.stderr)
        return None


def main():
    """Main entry point for PR triage."""
    import argparse

    parser = argparse.ArgumentParser(description="Triage PR using Claude Agent SDK")
    parser.add_argument("pr_number", type=int, help="Pull request number to triage")
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

    # Perform triage
    triage = asyncio.run(triage_pr(args.project_root, args.pr_number))

    if not triage:
        print(f"Error: Failed to triage PR #{args.pr_number}", file=sys.stderr)
        sys.exit(1)

    # Output triage
    if args.output:
        args.output.write_text(triage)
        print(f"Triage analysis written to {args.output}", file=sys.stderr)
    else:
        print(triage)

    sys.exit(0)


if __name__ == "__main__":
    main()
