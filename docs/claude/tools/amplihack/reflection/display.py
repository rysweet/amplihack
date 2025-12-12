"""Simple reflection display utility - shows user what reflection is doing."""

import os
import sys
from functools import lru_cache

# Import security utilities
try:
    from .security import create_safe_preview, filter_pattern_suggestion
except ImportError:
    try:
        from security import create_safe_preview, filter_pattern_suggestion
    except ImportError:
        # Fallback security functions if security module not available
        import re

        def filter_pattern_suggestion(suggestion: str) -> str:
            """Fallback sanitization for pattern suggestions."""
            # Remove sensitive patterns
            sensitive_patterns = [
                r'\b(?:password|passwd|pwd)\s*[=:]\s*[^\s\'"]+',
                r'\b(?:token|auth|bearer)\s*[=:]\s*[^\s\'"]+',
                r'\b(?:key|secret|private)\s*[=:]\s*[^\s\'"]+',
                r"\bsk-[A-Za-z0-9]+",
            ]

            sanitized = suggestion
            for pattern in sensitive_patterns:
                sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

            # Truncate if needed
            if len(sanitized) > 100:
                sanitized = sanitized[:97] + "..."

            return sanitized

        def create_safe_preview(content: str, context: str = "") -> str:
            """Fallback safe preview creation."""
            # Basic sanitization
            sensitive_words = ["password", "token", "secret", "key", "sk-"]
            safe_content = content

            for word in sensitive_words:
                if word in safe_content.lower():
                    safe_content = re.sub(
                        f"{word}[=:]?[^\\s]*", "[REDACTED]", safe_content, flags=re.IGNORECASE
                    )

            # Truncate
            if len(safe_content) > 50:
                safe_content = safe_content[:47] + "..."

            return f"{context}: {safe_content}" if context else safe_content


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

    # Sanitize suggestion before displaying to user
    safe_suggestion = filter_pattern_suggestion(suggestion)
    print(f"🎯 Found {priority} priority {pattern_type}: {safe_suggestion}")
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
    # Always show errors - but sanitize error content first
    safe_error = create_safe_preview(error_msg, "Error")
    print(f"❌ REFLECTION ERROR: {safe_error}")
    sys.stdout.flush()
