"""Simple reflection display utility - shows user what reflection is doing."""

import os
import sys
from functools import lru_cache


@lru_cache(maxsize=1)
def should_show_output() -> bool:
    """Check if reflection output should be visible with caching."""
    env_value = os.environ.get("REFLECTION_VISIBILITY", "true").lower()
    return env_value not in {"false", "0", "no", "off"}


def show_analysis_start(message_count: int) -> None:
    """Show that reflection analysis is starting."""
    if not should_show_output():
        return

    print(f"\n{'=' * 50}")
    print("🤖 AI REFLECTION ANALYSIS STARTING")
    print(f"📊 Analyzing {message_count} messages for improvements...")
    print(f"{'=' * 50}")
    sys.stdout.flush()


def show_pattern_found(pattern_type: str, suggestion: str, priority: str) -> None:
    """Show that a pattern was discovered."""
    if not should_show_output():
        return

    print(f"🎯 Found {priority} priority {pattern_type}: {suggestion}")
    sys.stdout.flush()


def show_issue_created(issue_url: str, pattern_type: str) -> None:
    """Show that a GitHub issue was created."""
    # Always show issue creation (user needs to know)
    issue_number = issue_url.split("/")[-1] if issue_url else "unknown"
    print(f"✅ Created GitHub issue #{issue_number} for {pattern_type} improvement")
    print(f"📎 {issue_url}")
    sys.stdout.flush()


def show_automation_status(issue_number: str, success: bool) -> None:
    """Show automation delegation status."""
    if not should_show_output():
        return

    if success:
        print(f"🚀 UltraThink will create PR for issue #{issue_number}")
    else:
        print(f"⚠️  Manual follow-up needed for issue #{issue_number}")
    sys.stdout.flush()


def show_analysis_complete(patterns_found: int, issues_created: int) -> None:
    """Show analysis completion."""
    # Always show completion summary
    print(f"\n{'=' * 50}")
    print("🏁 REFLECTION ANALYSIS COMPLETE")
    print(f"📊 Found {patterns_found} improvement opportunities")
    if issues_created > 0:
        print(f"🎫 Created {issues_created} GitHub issue(s)")
    print(f"{'=' * 50}\n")
    sys.stdout.flush()


def show_error(error_msg: str) -> None:
    """Show error message."""
    # Always show errors
    print(f"❌ REFLECTION ERROR: {error_msg}")
    sys.stdout.flush()
