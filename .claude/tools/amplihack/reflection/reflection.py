"""Simple AI-powered reflection system with user visibility.

Analyzes session logs and creates GitHub issues for improvements.
Shows the user what's happening during reflection analysis.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from display import (
    show_analysis_complete,
    show_analysis_start,
    show_automation_status,
    show_error,
    show_issue_created,
    show_pattern_found,
)


def is_reflection_enabled() -> bool:
    """Check if reflection is enabled via environment variable."""
    return os.environ.get("REFLECTION_ENABLED", "true").lower() not in ["false", "0", "no", "off"]


def analyze_session_patterns(messages: List[Dict]) -> List[Dict]:
    """Analyze session for improvement patterns."""
    patterns = []
    content = " ".join(str(msg.get("content", "")) for msg in messages).lower()

    # Look for error patterns
    if "error" in content or "failed" in content:
        patterns.append(
            {
                "type": "error_handling",
                "priority": "high",
                "suggestion": "Improve error handling based on session failures",
            }
        )

    # Look for workflow issues
    if "try again" in content or "repeat" in content:
        patterns.append(
            {
                "type": "workflow",
                "priority": "medium",
                "suggestion": "Streamline workflow to reduce repetitive actions",
            }
        )

    # Look for automation opportunities
    tool_count = content.count("tool_use")
    if tool_count > 10:
        patterns.append(
            {
                "type": "automation",
                "priority": "medium",
                "suggestion": f"Consider automating frequent tool combinations ({tool_count} uses detected)",
            }
        )

    return patterns


def create_github_issue(pattern: Dict) -> Optional[str]:
    """Create GitHub issue for improvement pattern."""
    try:
        title = f"AI-detected {pattern['type']}: {pattern['suggestion'][:60]}"

        body = f"""# AI-Detected Improvement Opportunity

**Type**: {pattern["type"]}
**Priority**: {pattern["priority"]}

## Suggestion
{pattern["suggestion"]}

## Next Steps
This improvement was identified by AI analysis. Please review and implement as appropriate.

**Labels**: ai-improvement, {pattern["type"]}, {pattern["priority"]}-priority
"""

        result = subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--title",
                title,
                "--body",
                body,
                "--label",
                f"ai-improvement,{pattern['type']},{pattern['priority']}-priority",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            issue_url = result.stdout.strip()
            show_issue_created(issue_url, pattern["type"])
            return issue_url.split("/")[-1] if issue_url else None
        else:
            show_error(f"Failed to create GitHub issue: {result.stderr}")
            return None

    except Exception as e:
        show_error(f"Exception creating GitHub issue: {e}")
        return None


def delegate_to_ultrathink(issue_number: str, pattern: Dict) -> bool:
    """Delegate issue to UltraThink for automated fix."""
    try:
        task = f"Fix GitHub issue #{issue_number}: {pattern['suggestion']}"

        result = subprocess.run(
            ["claude", "ultrathink", task], capture_output=True, text=True, timeout=300
        )

        success = result.returncode == 0
        show_automation_status(issue_number, success)
        return success

    except Exception as e:
        show_error(f"Failed to delegate to UltraThink: {e}")
        return False


def process_reflection_analysis(analysis_path: Path) -> Optional[str]:
    """Main reflection analysis entry point with user visibility."""

    if not is_reflection_enabled():
        print("ℹ️  Reflection analysis disabled (set REFLECTION_ENABLED=true to enable)")
        return None

    try:
        # Load session data
        if not analysis_path.exists():
            show_error(f"Analysis file not found: {analysis_path}")
            return None

        with open(analysis_path) as f:
            data = json.load(f)

        # Get messages from data
        messages = data.get("messages", [])
        if not messages and "learnings" in data:
            # Use learnings as fallback
            messages = [{"content": str(data["learnings"])}]

        if not messages:
            show_error("No session messages found for analysis")
            return None

        # Start analysis with user visibility
        show_analysis_start(len(messages))

        # Analyze patterns
        patterns = analyze_session_patterns(messages)

        # Show discovered patterns
        for i, pattern in enumerate(patterns, 1):
            show_pattern_found(pattern["type"], pattern["suggestion"], pattern["priority"])

        # Create issue for highest priority pattern
        issue_number = None
        if patterns:
            top_pattern = max(
                patterns, key=lambda p: {"high": 3, "medium": 2, "low": 1}[p["priority"]]
            )
            issue_number = create_github_issue(top_pattern)

            if issue_number:
                # Try automated fix
                delegate_to_ultrathink(issue_number, top_pattern)

        # Show completion
        show_analysis_complete(len(patterns), 1 if patterns else 0)

        return issue_number if patterns else None

    except Exception as e:
        show_error(f"Reflection analysis failed: {e}")
        return None


def main():
    """CLI interface for testing."""
    if len(sys.argv) != 2:
        print("Usage: python simple_reflection.py <analysis_file.json>")
        sys.exit(1)

    analysis_path = Path(sys.argv[1])
    result = process_reflection_analysis(analysis_path)

    if result:
        print(f"Issue created: #{result}")
    else:
        print("No issues created")


if __name__ == "__main__":
    main()
