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

# Import security utilities
try:
    from .security import (
        create_safe_preview,
        filter_pattern_suggestion,
        sanitize_content,
        sanitize_messages,
    )
except ImportError:
    # Fallback security functions if security module not available
    def sanitize_messages(messages: List[Dict]) -> List[Dict]:
        """Fallback sanitizer."""
        return [
            {
                "content": str(msg.get("content", ""))[:100] + "..."
                if len(str(msg.get("content", ""))) > 100
                else str(msg.get("content", ""))
            }
            for msg in messages[:10]
        ]

    def sanitize_content(content: str, max_length: int = 200) -> str:
        """Fallback content sanitizer."""
        return content[:max_length] + "..." if len(content) > max_length else content

    def filter_pattern_suggestion(suggestion: str) -> str:
        """Fallback suggestion filter."""
        return suggestion[:100] + "..." if len(suggestion) > 100 else suggestion

    def create_safe_preview(content: str, context: str = "") -> str:
        """Fallback preview creator."""
        safe_content = content[:50] + "..." if len(content) > 50 else content
        return f"{context}: {safe_content}" if context else safe_content


def is_reflection_enabled() -> bool:
    """Check if reflection is enabled via environment variable."""
    return os.environ.get("REFLECTION_ENABLED", "true").lower() not in ["false", "0", "no", "off"]


def analyze_session_patterns(messages: List[Dict]) -> List[Dict]:
    """Analyze session for improvement patterns with security filtering."""
    patterns = []

    # SECURITY: Sanitize messages before processing
    safe_messages = sanitize_messages(messages)

    # Build sanitized content for pattern analysis
    safe_content_parts = []
    for msg in safe_messages:
        if isinstance(msg, dict) and "content" in msg:
            safe_content_parts.append(str(msg["content"]))

    content = " ".join(safe_content_parts).lower()

    # Look for error patterns (using sanitized content)
    if "error" in content or "failed" in content:
        patterns.append(
            {
                "type": "error_handling",
                "priority": "high",
                "suggestion": "Improve error handling based on session failures",
            }
        )

    # Look for workflow issues (using sanitized content)
    if "try again" in content or "repeat" in content:
        patterns.append(
            {
                "type": "workflow",
                "priority": "medium",
                "suggestion": "Streamline workflow to reduce repetitive actions",
            }
        )

    # Look for automation opportunities (safe count)
    tool_count = content.count("tool_use")
    if tool_count > 10:
        patterns.append(
            {
                "type": "automation",
                "priority": "medium",
                "suggestion": f"Consider automating frequent tool combinations ({tool_count} uses detected)",
            }
        )

    # SECURITY: Filter all suggestions before returning
    for pattern in patterns:
        pattern["suggestion"] = filter_pattern_suggestion(pattern["suggestion"])

    return patterns


def create_github_issue(pattern: Dict) -> Optional[str]:
    """Create GitHub issue for improvement pattern."""
    try:
        # SECURITY: Sanitize all content before creating GitHub issue
        safe_type = sanitize_content(pattern.get("type", "unknown"), max_length=50)
        safe_suggestion = filter_pattern_suggestion(pattern.get("suggestion", ""))
        safe_priority = sanitize_content(pattern.get("priority", "medium"), max_length=20)

        # Truncate title to prevent information disclosure
        title = f"AI-detected {safe_type}: {safe_suggestion[:60]}"

        body = f"""# AI-Detected Improvement Opportunity

**Type**: {safe_type}
**Priority**: {safe_priority}

## Suggestion
{safe_suggestion}

## Next Steps
This improvement was identified by AI analysis. Please review and implement as appropriate.

**Labels**: ai-improvement, {safe_type}, {safe_priority}-priority
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
                f"ai-improvement,{safe_type},{safe_priority}-priority",
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


def process_reflection_analysis(messages: List[Dict]) -> Optional[str]:
    """Main reflection analysis entry point with user visibility."""

    if not is_reflection_enabled():
        print("ℹ️  Reflection analysis disabled (set REFLECTION_ENABLED=true to enable)")
        return None

    try:
        # Validate messages input
        if not messages:
            show_error("No session messages provided for analysis")
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

    # Load session data from file
    try:
        if not analysis_path.exists():
            print(f"Error: Analysis file not found: {analysis_path}")
            sys.exit(1)

        with open(analysis_path) as f:
            data = json.load(f)

        # Get messages from data
        messages = data.get("messages", [])
        if not messages and "learnings" in data:
            # Use learnings as fallback
            messages = [{"content": str(data["learnings"])}]

        if not messages:
            print("Error: No session messages found for analysis")
            sys.exit(1)

        result = process_reflection_analysis(messages)

        if result:
            print(f"Issue created: #{result}")
        else:
            print("No issues created")

    except Exception as e:
        print(f"Error processing analysis file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
