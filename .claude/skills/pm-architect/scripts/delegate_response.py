#!/usr/bin/env python3
"""
PM Architect - Label-Triggered Delegation.

Handles pm:delegate label by preparing context and spawning auto mode
to generate response for issues or PRs.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional


def get_issue_pr_details(project_root: Path, number: int, item_type: str) -> Optional[Dict]:
    """Get issue or PR details using gh CLI.

    Args:
        project_root: Project root directory
        number: Issue or PR number
        item_type: Either 'issue' or 'pr'

    Returns:
        Dictionary with details, or None if retrieval fails
    """
    try:
        cmd = ["gh", item_type, "view", str(number), "--json", "number,title,author,body,comments"]

        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            return json.loads(result.stdout)

        print(f"Error: gh {item_type} view failed: {result.stderr}", file=sys.stderr)
        return None

    except Exception as e:
        print(f"Error retrieving {item_type} details: {e}", file=sys.stderr)
        return None


def prepare_delegation_prompt(details: Dict, number: int, item_type: str) -> str:
    """Prepare delegation prompt from issue/PR details.

    Args:
        details: Issue/PR details from GitHub
        number: Issue/PR number
        item_type: 'issue' or 'pr'

    Returns:
        Formatted delegation prompt
    """
    title = details.get("title", "")
    body = details.get("body", "") or "(No description provided)"
    comments = details.get("comments", [])
    latest_comment = comments[-1]["body"] if comments else None

    prompt = f"""PM Architect Delegation Request

**Context**: {item_type.upper()} #{number}
**Title**: {title}

**Description**:
{body}
"""

    if latest_comment:
        prompt += f"""
**Latest Comment**:
{latest_comment}
"""

    prompt += """
**Task**: Analyze this request and provide a comprehensive response. Consider:
1. What is being requested?
2. What information or action is needed?
3. What is the best approach to address this?
4. Are there any blockers or dependencies?
5. What are the next steps?

Provide a clear, actionable response that addresses the request.
"""

    return prompt


def run_auto_mode_delegation(
    prompt: str, project_root: Path, max_turns: int = 5
) -> tuple[bool, str]:
    """Run amplihack auto mode with delegation prompt.

    Args:
        prompt: Delegation prompt to execute
        project_root: Project root directory
        max_turns: Maximum auto mode turns

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        # Run amplihack auto mode
        cmd = ["amplihack", "claude", "--auto", "--max-turns", str(max_turns), "--", "-p", prompt]

        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout
        )

        # Auto mode may return non-zero but still produce output
        output = result.stdout + result.stderr

        # Check if output looks reasonable
        if len(output) > 100:  # At least some content
            return True, output
        return False, f"Auto mode produced insufficient output:\n{output}"

    except subprocess.TimeoutExpired:
        return False, "Auto mode execution timed out (10 minutes)"
    except Exception as e:
        return False, f"Auto mode execution failed: {e}"


def format_response_for_github(output: str) -> str:
    """Format auto mode output for GitHub comment.

    Args:
        output: Raw auto mode output

    Returns:
        Formatted markdown for GitHub comment
    """
    # Add header
    formatted = """## 🤖 PM Architect Delegation Response

*This response was generated automatically by PM Architect via the `pm:delegate` label.*

---

"""

    # Add the output (take last reasonable portion to avoid noise)
    lines = output.split("\n")

    # Try to find the start of meaningful content (skip initialization)
    start_idx = 0
    for i, line in enumerate(lines):
        if "AUTONOMOUS MODE" in line or "Auto mode" in line:
            start_idx = i
            break

    # Take from meaningful start, limit to last 200 lines max
    meaningful_lines = lines[start_idx:]
    if len(meaningful_lines) > 200:
        meaningful_lines = meaningful_lines[-200:]

    formatted += "\n".join(meaningful_lines)

    # Add footer
    formatted += """

---

*To continue the conversation or provide feedback, reply to this comment or use the `pm:delegate` label again.*
"""

    return formatted


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(description="PM Architect Label-Triggered Delegation")
    parser.add_argument("number", type=int, help="Issue or PR number")
    parser.add_argument("type", choices=["issue", "pr"], help="Type: issue or pr")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Project root")
    parser.add_argument("--output", type=Path, required=True, help="Output file for response")
    parser.add_argument("--max-turns", type=int, default=5, help="Max auto mode turns")

    args = parser.parse_args()

    # Get issue/PR details
    print(f"Fetching {args.type} #{args.number} details...")
    details = get_issue_pr_details(args.project_root, args.number, args.type)

    if not details:
        print(f"Error: Could not fetch {args.type} details", file=sys.stderr)
        sys.exit(1)

    # Prepare delegation prompt
    print("Preparing delegation prompt...")
    prompt = prepare_delegation_prompt(details, args.number, args.type)

    # Run auto mode
    print(f"Running auto mode delegation (max {args.max_turns} turns)...")
    success, output = run_auto_mode_delegation(prompt, args.project_root, args.max_turns)

    if not success:
        print(f"Error: Auto mode failed: {output}", file=sys.stderr)
        # Write error response
        error_response = f"""## ❌ PM Architect Delegation Failed

The PM Architect delegation encountered an error:

```
{output}
```

Please check the workflow logs for more details or try again.
"""
        args.output.write_text(error_response)
        sys.exit(1)

    # Format and save response
    print("Formatting response for GitHub...")
    formatted_response = format_response_for_github(output)
    args.output.write_text(formatted_response)

    print(f"Delegation response written to {args.output}")
    print("Success!")


if __name__ == "__main__":
    main()
