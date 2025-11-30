#!/usr/bin/env python3
"""
Claude SDK-based session reflection.

Uses Claude Agent SDK to intelligently analyze sessions and fill out
the FEEDBACK_SUMMARY template, replacing simple pattern matching with
AI-powered reflection.
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

# Repository constants
AMPLIHACK_REPO_URI = "https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding"

# Template paths (relative to this file)
TEMPLATE_DIR = Path(__file__).parent / "templates"
REFLECTION_PROMPT_TEMPLATE = TEMPLATE_DIR / "reflection_prompt.txt"


def load_session_conversation(session_dir: Path) -> list[dict] | None:
    """Load conversation messages from session directory.

    Args:
        session_dir: Path to session log directory

    Returns:
        List of message dicts, or None if not found
    """
    # Try different possible file locations
    candidates = [
        session_dir / "conversation_transcript.json",
        session_dir / "messages.json",
        session_dir / "session.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            try:
                with open(candidate) as f:
                    data = json.load(f)
                # Handle different data structures
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "messages" in data:
                    return data["messages"]
            except (OSError, json.JSONDecodeError):
                continue

    return None


def load_power_steering_redirects(session_dir: Path) -> list[dict] | None:
    """Load power-steering redirect history from session directory.

    Args:
        session_dir: Path to session log directory

    Returns:
        List of redirect dicts, or None if no redirects file exists
    """
    redirects_file = session_dir / "redirects.jsonl"

    if not redirects_file.exists():
        return None

    redirects = []
    try:
        with open(redirects_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    redirect = json.loads(line)
                    redirects.append(redirect)
                except json.JSONDecodeError:
                    continue  # Skip malformed lines
    except OSError:
        return None

    return redirects if redirects else None


def format_redirects_context(redirects: list[dict] | None) -> str:
    """Format redirect history for inclusion in reflection prompt.

    Args:
        redirects: List of redirect dictionaries

    Returns:
        Formatted markdown string describing redirects
    """
    if not redirects:
        return ""

    redirect_word = "redirect" if len(redirects) == 1 else "redirects"
    parts = [
        "",
        "## Power-Steering Redirect History",
        "",
        f"This session had {len(redirects)} power-steering {redirect_word} where Claude was blocked from stopping due to incomplete work:",
        "",
    ]

    for redirect in redirects:
        redirect_num = redirect.get("redirect_number", "?")
        timestamp = redirect.get("timestamp", "unknown")
        failed = redirect.get("failed_considerations", [])
        prompt = redirect.get("continuation_prompt", "")

        parts.append(f"### Redirect #{redirect_num} ({timestamp})")
        parts.append("")
        parts.append(f"**Failed Checks:** {', '.join(failed)}")
        parts.append("")
        parts.append("**Continuation Prompt Given:**")
        parts.append("```")
        parts.append(prompt)
        parts.append("```")
        parts.append("")

    parts.append(
        "**Analysis Note:** These redirects indicate areas where work was incomplete. "
        "In your feedback, consider whether the redirects were justified and whether "
        "Claude successfully addressed the blockers after being redirected."
    )
    parts.append("")

    return "\n".join(parts)


def load_feedback_template(project_root: Path) -> str:
    """Load FEEDBACK_SUMMARY template.

    Args:
        project_root: Project root directory

    Returns:
        Template content as string
    """
    template_path = project_root / ".claude" / "templates" / "FEEDBACK_SUMMARY.md"

    if not template_path.exists():
        # Fallback minimal template
        return """## Task Summary
[What was accomplished]

## Feedback Summary
**User Interactions:** [Observations]
**Workflow Adherence:** [Did workflow get followed?]
**Subagent Usage:** [Which agents used?]
**Learning Opportunities:** [What to improve]
"""

    return template_path.read_text()


def load_prompt_template() -> str:
    """Load reflection prompt template.

    Returns:
        Raw template content with {VARIABLE} placeholders

    Raises:
        FileNotFoundError: If template file is missing (configuration error)
    """
    if not REFLECTION_PROMPT_TEMPLATE.exists():
        raise FileNotFoundError(
            f"Reflection prompt template not found at {REFLECTION_PROMPT_TEMPLATE}. "
            "This is a configuration error - the template file must exist."
        )

    return REFLECTION_PROMPT_TEMPLATE.read_text()


def format_reflection_prompt(template: str, variables: dict[str, str]) -> str:
    """Format reflection prompt with variable substitution.

    Args:
        template: Raw template with {VARIABLE} placeholders
        variables: Dictionary of variable name -> value mappings

    Returns:
        Formatted prompt with all variables substituted

    Raises:
        KeyError: If required variable is missing
    """
    return template.format(**variables)


def get_repository_context(project_root: Path) -> str:
    """Detect repository context to distinguish amplihack vs project issues.

    Args:
        project_root: Project root directory

    Returns:
        Formatted repository context guidance for reflection prompt
    """
    import subprocess

    try:
        # Get current repository URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            current_repo = result.stdout.strip()

            # Normalize URLs for comparison (handle .git suffix and https/ssh)
            def normalize_url(url: str) -> str:
                url = url.rstrip("/").replace(".git", "")
                if url.startswith("git@github.com:"):
                    url = url.replace("git@github.com:", "https://github.com/")
                return url.lower()

            current_normalized = normalize_url(current_repo)
            amplihack_normalized = normalize_url(AMPLIHACK_REPO_URI)

            is_amplihack_repo = current_normalized == amplihack_normalized

            if is_amplihack_repo:
                return f"""
## Repository Context

**Current Repository**: {current_repo}
**Context**: Working on Amplihack itself

**IMPORTANT**: Since we're working on the Amplihack framework itself, ALL issues identified in this session are Amplihack framework issues and should be filed against the Amplihack repository.
"""
            return f"""
## Repository Context

**Current Repository**: {current_repo}
**Amplihack Repository**: {AMPLIHACK_REPO_URI}
**Context**: Working on a user project (not Amplihack itself)
"""

        # Git command failed - provide generic guidance
        return f"""
## Repository Context

**Amplihack Repository**: {AMPLIHACK_REPO_URI}
**Context**: Repository detection unavailable
"""

    except Exception:
        # Subprocess failed - provide generic guidance
        return f"""
## Repository Context

**Amplihack Repository**: {AMPLIHACK_REPO_URI}
**Context**: Repository detection unavailable
"""


async def analyze_session_with_claude(
    conversation: list[dict],
    template: str,
    project_root: Path,
    session_dir: Path | None = None,
) -> str | None:
    """Use Claude SDK to analyze session and fill out template.

    Args:
        conversation: Session conversation messages
        template: FEEDBACK_SUMMARY template
        project_root: Project root directory
        session_dir: Optional session directory for loading redirects

    Returns:
        Filled template as string, or None if analysis fails
    """
    if not CLAUDE_SDK_AVAILABLE:
        print("Claude SDK not available - cannot run AI-powered reflection", file=sys.stderr)
        return None

    # Load USER_PREFERENCES for context (same as session_start does)
    user_preferences_context = ""
    try:
        # Try to use FrameworkPathResolver if available
        try:
            sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack"))
            from amplihack.utils.paths import FrameworkPathResolver

            preferences_file = FrameworkPathResolver.resolve_preferences_file()
        except ImportError:
            # Fallback to default location
            preferences_file = project_root / ".claude" / "context" / "USER_PREFERENCES.md"

        if preferences_file and preferences_file.exists():
            with open(preferences_file) as f:
                prefs_content = f.read()
            user_preferences_context = f"""
## User Preferences (MANDATORY - MUST FOLLOW)

The following preferences are REQUIRED and CANNOT be ignored:

{prefs_content}

**IMPORTANT**: When analyzing this session, consider whether Claude followed these user preferences. Do NOT criticize behavior that aligns with configured preferences.
"""
    except Exception as e:
        print(f"Warning: Could not load USER_PREFERENCES: {e}", file=sys.stderr)
        # Continue without preferences

    # Get repository context for issue categorization
    repository_context = get_repository_context(project_root)

    # Load power-steering redirects if available
    redirects_context = ""
    if session_dir:
        redirects = load_power_steering_redirects(session_dir)
        redirects_context = format_redirects_context(redirects)

    # Load prompt template and format with variables
    prompt_template = load_prompt_template()
    prompt = format_reflection_prompt(
        prompt_template,
        {
            "user_preferences_context": user_preferences_context,
            "repository_context": repository_context,
            "amplihack_repo_uri": AMPLIHACK_REPO_URI,
            "message_count": str(len(conversation)),
            "conversation_summary": _format_conversation_summary(conversation),
            "redirects_context": redirects_context,
            "template": template,
        },
    )

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
        filled_template = "".join(response_parts)
        return filled_template if filled_template.strip() else None

    except Exception as e:
        print(f"Error during Claude reflection: {e}", file=sys.stderr)
        return None


def _format_conversation_summary(conversation: list[dict], max_length: int = 5000) -> str:
    """Format conversation summary for analysis.

    Args:
        conversation: List of message dicts
        max_length: Maximum summary length

    Returns:
        Formatted conversation summary
    """
    summary_parts = []
    current_length = 0

    for i, msg in enumerate(conversation):
        role = msg.get("role", "unknown")
        content = str(msg.get("content", ""))

        # Truncate long messages
        if len(content) > 500:
            content = content[:497] + "..."

        msg_summary = f"\n**Message {i + 1} ({role}):** {content}\n"

        # Check if adding this would exceed limit
        if current_length + len(msg_summary) > max_length:
            summary_parts.append(f"\n[... {len(conversation) - i} more messages ...]")
            break

        summary_parts.append(msg_summary)
        current_length += len(msg_summary)

    return "".join(summary_parts)


def run_claude_reflection(
    session_dir: Path, project_root: Path, conversation: list[dict] | None = None
) -> str | None:
    """Run Claude SDK-based reflection on a session.

    Args:
        session_dir: Session log directory
        project_root: Project root directory
        conversation: Optional pre-loaded conversation (if None, loads from session_dir)

    Returns:
        Filled FEEDBACK_SUMMARY template, or None if failed
    """
    # Load conversation if not provided
    if conversation is None:
        conversation = load_session_conversation(session_dir)
        if not conversation:
            print(f"No conversation found in {session_dir}", file=sys.stderr)
            return None

    # Load template
    template = load_feedback_template(project_root)

    # Run async analysis with session_dir for redirect loading
    try:
        result = asyncio.run(
            analyze_session_with_claude(conversation, template, project_root, session_dir)
        )
        return result
    except Exception as e:
        print(f"Claude reflection failed: {e}", file=sys.stderr)
        return None


# For testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Claude-powered session reflection")
    parser.add_argument("session_dir", type=Path, help="Session directory path")
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )

    args = parser.parse_args()

    result = run_claude_reflection(args.session_dir, args.project_root)
    if result:
        print("\n" + "=" * 70)
        print("CLAUDE REFLECTION RESULT")
        print("=" * 70)
        print(result)
        print("=" * 70)
    else:
        print("Reflection failed")
        sys.exit(1)
