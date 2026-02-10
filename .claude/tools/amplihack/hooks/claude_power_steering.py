#!/usr/bin/env python3
"""
Claude SDK-based power-steering analysis with graceful shutdown support.

Uses Claude Agent SDK to intelligently analyze session transcripts against
considerations, replacing heuristic pattern matching with AI-powered analysis.

Shutdown Behavior:
    During application shutdown (AMPLIHACK_SHUTDOWN_IN_PROGRESS=1), all sync
    wrapper functions immediately return safe defaults to prevent asyncio
    event loop hangs. This enables clean 2-3 second exits without Ctrl-C.

    Fail-Open Philosophy: If shutdown is in progress, bypass async operations
    and return values that never block users:
    - analyze_claims_sync() → [] (no claims detected)
    - analyze_if_addressed_sync() → None (no evidence found)
    - analyze_consideration_sync() → (True, None) (assume satisfied)

Optional Dependencies:
    claude-agent-sdk: Required for AI-powered analysis
        Install: pip install claude-agent-sdk

    When unavailable, the system gracefully falls back to keyword-based
    heuristics (see fallback_heuristics.py). This ensures power steering
    always works, even without the SDK.

Philosophy:
- Ruthlessly Simple: Single-purpose module with clear contract
- Fail-Open: Never block users due to bugs - always allow stop on errors
- Zero-BS: No stubs, every function works or doesn't exist
- Modular: Self-contained brick that plugs into power_steering_checker
- Clean Shutdown: Detect shutdown in progress, bypass async, return safe defaults
"""

import asyncio
import os
import re
from pathlib import Path

# Try to import Claude SDK
try:
    from claude_agent_sdk import ClaudeAgentOptions, query

    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False

# Template paths (relative to this file)
TEMPLATE_DIR = Path(__file__).parent / "templates"
POWER_STEERING_PROMPT_TEMPLATE = TEMPLATE_DIR / "power_steering_prompt.txt"

# Security constants
MAX_SDK_RESPONSE_LENGTH = 5000
SUSPICIOUS_PATTERNS = [
    r"<script",
    r"javascript:",
    r"data:text/html",
    r"onerror=",
    r"onclick=",
    r"on\w+=",  # onerror=, onload=, onmouseover=, etc.
    r"<iframe",
    r"<object",
    r"<embed",
    r"vbscript:",
    r"data:image/svg",
    r"&#x[0-9a-f]",  # HTML entity encoding
    r"\\u[0-9a-f]{4}",  # Unicode escapes
]

# Timeout hierarchy: HOOK_TIMEOUT (120s) > PARALLEL_TIMEOUT (60s) > CHECKER_TIMEOUT (25s)
# Each checker must complete within 25s to fit within parallel execution budget
CHECKER_TIMEOUT = 25  # 25 seconds per SDK call (within 60s parallel budget)

# Public API (the "studs" for this brick)
__all__ = [
    "analyze_consideration",
    "generate_final_guidance",
    "analyze_claims_sync",
    "analyze_if_addressed_sync",
    "analyze_consideration_sync",
    "CLAUDE_SDK_AVAILABLE",
]


def is_shutting_down() -> bool:
    """Check if application shutdown is in progress.

    Returns:
        True if AMPLIHACK_SHUTDOWN_IN_PROGRESS environment variable is set,
        False otherwise

    Note:
        This function enables graceful shutdown by allowing sync wrapper
        functions to detect shutdown state and return safe defaults instead
        of starting new async operations that may hang during event loop
        teardown.

    Example:
        >>> os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        >>> is_shutting_down()
        True
        >>> del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]
        >>> is_shutting_down()
        False
    """
    return os.environ.get("AMPLIHACK_SHUTDOWN_IN_PROGRESS") == "1"


def _validate_sdk_response(response: str) -> bool:
    """Validate SDK response for security (fail-open).

    Args:
        response: SDK response text to validate

    Returns:
        True if response is safe or on validation error (fail-open),
        False only if clear security issue detected

    Note:
        Checks for excessive length and suspicious patterns.
        Returns True (allow) on any validation error to maintain fail-open behavior.
    """
    try:
        # Check length
        if len(response) > MAX_SDK_RESPONSE_LENGTH:
            return False

        # Check for suspicious patterns (case-insensitive)
        response_lower = response.lower()
        for pattern in SUSPICIOUS_PATTERNS:
            if re.search(pattern, response_lower):
                return False

        return True
    except Exception:
        # Fail-open on validation error
        return True


def _sanitize_html(text: str) -> str:
    """Remove potentially dangerous HTML tags from text.

    Args:
        text: Text that may contain HTML

    Returns:
        Text with dangerous HTML tags removed

    Note:
        Removes <script>, <img>, <iframe>, <object>, <embed> tags.
    """
    try:
        # Remove dangerous HTML tags
        dangerous_tags = [
            r"<script[^>]*>.*?</script>",
            r"<img[^>]*>",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
            r"<embed[^>]*>",
        ]

        sanitized = text
        for tag_pattern in dangerous_tags:
            sanitized = re.sub(tag_pattern, "", sanitized, flags=re.IGNORECASE | re.DOTALL)

        return sanitized
    except Exception:
        # On error, return original text (fail-open)
        return text


def load_prompt_template() -> str | None:
    """Load power-steering prompt template.

    Returns:
        Raw template content with {VARIABLE} placeholders, or None if template missing

    Note:
        Returns None instead of raising to support fail-open behavior.
        Caller should handle None gracefully and use fallback.
    """
    if not POWER_STEERING_PROMPT_TEMPLATE.exists():
        return None

    try:
        return POWER_STEERING_PROMPT_TEMPLATE.read_text()
    except Exception:
        return None


def format_prompt(template: str, variables: dict[str, str]) -> str:
    """Format prompt with variable substitution.

    Args:
        template: Raw template with {VARIABLE} placeholders
        variables: Dictionary of variable name -> value mappings

    Returns:
        Formatted prompt with all variables substituted

    Raises:
        KeyError: If required variable is missing
    """
    return template.format(**variables)


async def analyze_consideration(
    conversation: list[dict], consideration: dict, project_root: Path
) -> tuple[bool, str | None]:
    """Use Claude SDK to analyze if consideration is satisfied.

    Args:
        conversation: Session messages (list of dicts)
        consideration: Consideration dict (id, question, description, etc.)
        project_root: Project root directory

    Returns:
        Tuple of (satisfied, reason):
        - satisfied: True if consideration satisfied, False otherwise
        - reason: String explanation if not satisfied, None if satisfied
        (Fail-open: returns (True, None) on SDK unavailable or errors)
    """
    if not CLAUDE_SDK_AVAILABLE:
        return (True, None)  # Fail-open if SDK unavailable

    # Format prompt for this consideration
    try:
        prompt = _format_consideration_prompt(consideration, conversation)
    except Exception as e:
        _log_sdk_error(consideration["id"], e)
        return (True, None)  # Fail-open on prompt formatting error

    try:
        options = ClaudeAgentOptions(
            cwd=str(project_root),
        )

        # Query Claude with timeout
        response_parts = []
        async with asyncio.timeout(CHECKER_TIMEOUT):
            async for message in query(prompt=prompt, options=options):
                if hasattr(message, "text"):
                    response_parts.append(message.text)
                elif hasattr(message, "content"):
                    response_parts.append(str(message.content))

        # Join all parts
        response = "".join(response_parts)

        # Sanitize HTML before processing
        response = _sanitize_html(response)

        # Validate response before processing
        if not _validate_sdk_response(response):
            # Security validation failed - fail-open (assume satisfied)
            return (True, None)

        response_lower = response.lower()

        # Parse response for yes/no decision
        # Look for clear indicators of satisfaction
        satisfied_indicators = [
            "satisfied",
            "yes",
            "complete",
            "fulfilled",
            "met",
            "achieved",
            "accomplished",
        ]
        unsatisfied_indicators = [
            "not satisfied",
            "no",
            "incomplete",
            "unfulfilled",
            "not met",
            "missing",
            "failed",
        ]

        # Check for unsatisfied indicators first (more specific)
        for indicator in unsatisfied_indicators:
            if indicator in response_lower:
                # Extract reason from response
                reason = _extract_reason_from_response(response)
                return (False, reason)

        # Then check for satisfied indicators
        for indicator in satisfied_indicators:
            if indicator in response_lower:
                return (True, None)

        # Ambiguous response - fail-open (assume satisfied)
        return (True, None)

    except Exception as e:
        # Log error and fail-open on any error
        _log_sdk_error(consideration["id"], e)
        return (True, None)


def _format_consideration_prompt(consideration: dict, conversation: list[dict]) -> str:
    """Format analysis prompt for a consideration.

    Args:
        consideration: Consideration dictionary
        conversation: Session conversation messages

    Returns:
        Formatted prompt string
    """
    # Format conversation summary
    conv_summary = _format_conversation_summary(conversation)

    # Simple inline prompt (no template file needed for fail-open behavior)
    prompt = f"""You are analyzing a Claude Code session to determine if the following consideration is satisfied:

**Consideration**: {consideration["question"]}
**Description**: {consideration.get("description", consideration.get("question", ""))}
**Category**: {consideration.get("category", "General")}

**Session Conversation** ({len(conversation)} messages):
{conv_summary}

## Your Task

Analyze the conversation and determine if this consideration is satisfied.

**Respond with ONE of:**
- "SATISFIED: [brief reason]" if the consideration is met
- "NOT SATISFIED: [brief reason]" if the consideration is not met

Be direct and specific. Reference actual events from the conversation.
Focus on evidence - what tools were used, what actions were taken, what the user and assistant discussed.

If the consideration is not applicable to this session (e.g., no relevant work was done), respond with SATISFIED.
"""

    return prompt


def _extract_reason_from_response(response: str) -> str | None:
    """Extract failure reason from SDK response.

    Args:
        response: Full SDK response text

    Returns:
        Extracted reason string (truncated to 200 chars), or generic fallback

    Note:
        Looks for patterns like "NOT SATISFIED: reason" or "UNSATISFIED: reason"
        and extracts the reason part.
    """
    if not response:
        return "Check not satisfied"

    response_lower = response.lower()

    # Look for common failure patterns
    patterns = [
        "not satisfied:",
        "unsatisfied:",
        "not met:",
        "incomplete:",
        "missing:",
        "failed:",
    ]

    for pattern in patterns:
        idx = response_lower.find(pattern)
        if idx != -1:
            # Extract text after the pattern
            reason_start = idx + len(pattern)
            reason = response[reason_start:].strip()

            # Return full reason without truncation

            return reason if reason else "Check not satisfied"

    # No specific pattern found - use generic fallback
    return "Check not satisfied"


def _log_sdk_error(consideration_id: str, error: Exception) -> None:
    """Log SDK error to stderr for debugging with sensitive data scrubbed.

    Args:
        consideration_id: ID of the consideration that failed
        error: Exception that was raised

    Note:
        Logs to stderr to avoid interfering with stdout tool output.
        Scrubs file paths and tokens from error messages.
        Format: [Power Steering SDK Error] {id}: {sanitized_error}
    """
    import sys

    error_msg = str(error)

    # Scrub file paths (replace with [PATH])
    error_msg = re.sub(r"/[^\s]+", "[PATH]", error_msg)
    error_msg = re.sub(r"[A-Z]:\\[^\s]+", "[PATH]", error_msg)  # Windows paths

    # Scrub potential tokens (40+ hex characters)
    error_msg = re.sub(r"\b[a-fA-F0-9]{40,}\b", "[REDACTED]", error_msg)

    # Truncate to 200 chars
    if len(error_msg) > 200:
        error_msg = error_msg[:200] + "..."

    sanitized_msg = f"[Power Steering SDK Error] {consideration_id}: {error_msg}\n"
    sys.stderr.write(sanitized_msg)
    sys.stderr.flush()


def _format_conversation_summary(conversation: list[dict], max_length: int | None = None) -> str:
    """Format conversation summary for analysis.

    Args:
        conversation: List of message dicts
        max_length: Optional maximum summary length (None = unlimited, includes all messages)

    Returns:
        Formatted conversation summary

    Note:
        All messages in the conversation are included in the analysis unless max_length is specified.
        Individual messages longer than 500 chars are truncated for readability.
    """
    summary_parts = []
    current_length = 0

    for i, msg in enumerate(conversation):
        role = msg.get("role", msg.get("type", "unknown"))
        content = msg.get("content", msg.get("message", {}))

        # Handle different content formats
        content_text = ""
        if isinstance(content, str):
            content_text = content
        elif isinstance(content, dict):
            # Extract text from message dict
            msg_content = content.get("content", "")
            if isinstance(msg_content, str):
                content_text = msg_content
            elif isinstance(msg_content, list):
                # Extract text blocks
                text_blocks = []
                for block in msg_content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_blocks.append(str(block.get("text", "")))
                        elif block.get("type") == "tool_use":
                            tool_name = block.get("name", "unknown")
                            text_blocks.append(f"[Tool: {tool_name}]")
                content_text = " ".join(text_blocks)
        elif isinstance(content, list):
            # Direct list of blocks
            text_blocks = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_blocks.append(str(block.get("text", "")))
                    elif block.get("type") == "tool_use":
                        tool_name = block.get("name", "unknown")
                        text_blocks.append(f"[Tool: {tool_name}]")
            content_text = " ".join(text_blocks)

        # Truncate long individual messages for readability
        if len(content_text) > 500:
            content_text = content_text[:497] + "..."

        msg_summary = f"\n**Message {i + 1} ({role}):** {content_text}\n"

        # Only check length limit if max_length is specified
        if max_length is not None and current_length + len(msg_summary) > max_length:
            truncation_indicator = f"\n[... {len(conversation) - i} more messages ...]"
            # Only add truncation indicator if we have room for it
            if current_length + len(truncation_indicator) <= max_length:
                summary_parts.append(truncation_indicator)
            break

        summary_parts.append(msg_summary)
        current_length += len(msg_summary)

    return "".join(summary_parts)


async def generate_final_guidance(
    failed_checks: list[tuple[str, str]],
    conversation: list[dict],
    project_root: Path,
) -> str:
    """Generate context-aware final guidance using Claude SDK.

    Args:
        failed_checks: List of (check_id, reason) tuples for failed checks
        conversation: Session conversation messages
        project_root: Project root directory

    Returns:
        Specific guidance string based on actual failures.
        (Fail-open: returns template-based guidance on SDK unavailable or errors)

    Note:
        This provides context-aware, specific guidance rather than generic advice.
        Falls back to template if SDK unavailable or fails.
    """
    if not CLAUDE_SDK_AVAILABLE:
        return _generate_template_guidance(failed_checks)

    if not failed_checks:
        return "All checks passed. You may proceed."

    # Format failed checks for prompt
    failures_text = "\n".join([f"- {check_id}: {reason}" for check_id, reason in failed_checks])

    prompt = f"""You are analyzing a Claude Code session to provide specific, actionable guidance.

**Failed Checks:**
{failures_text}

**Your Task:**

Provide specific, actionable guidance to address these failed checks. Be concrete and reference the actual failure reasons. Do NOT give generic advice.

**Format:**

Provide 1-3 sentences with specific actions based on the actual failures listed above.

Example good guidance:
"Complete the 3 incomplete TODOs shown in the task list and run pytest locally to verify your changes work."

Example bad guidance:
"Make sure to complete all tasks and test your code."

Be direct and specific."""

    try:
        options = ClaudeAgentOptions(
            cwd=str(project_root),
        )

        response_parts = []
        async with asyncio.timeout(CHECKER_TIMEOUT):
            async for message in query(prompt=prompt, options=options):
                if hasattr(message, "text"):
                    response_parts.append(message.text)
                elif hasattr(message, "content"):
                    response_parts.append(str(message.content))

        guidance = "".join(response_parts).strip()

        # Sanitize HTML before processing
        guidance = _sanitize_html(guidance)

        # Validate response before using
        if not _validate_sdk_response(guidance):
            # Security validation failed - use template fallback
            return _generate_template_guidance(failed_checks)

        # Return SDK-generated guidance if non-empty
        if guidance and len(guidance) > 10:
            return guidance

        # Empty or too short - use template fallback
        return _generate_template_guidance(failed_checks)

    except Exception:
        # Fail-open to template guidance
        return _generate_template_guidance(failed_checks)


def _generate_template_guidance(failed_checks: list[tuple[str, str]]) -> str:
    """Generate template-based guidance when SDK unavailable.

    Args:
        failed_checks: List of (check_id, reason) tuples

    Returns:
        Template-based guidance string
    """
    if not failed_checks:
        return "All checks passed."

    # Group checks by category/type for better guidance
    guidance_parts = ["Address the following failed checks:"]
    for check_id, reason in failed_checks:
        guidance_parts.append(f"- {check_id}: {reason}")

    return "\n".join(guidance_parts)


async def analyze_claims(delta_text: str, project_root: Path) -> list[str]:
    """Use Claude SDK to detect completion claims in delta text.

    Replaces regex-based claim detection with LLM-powered analysis.

    Args:
        delta_text: New transcript content since last block
        project_root: Project root directory

    Returns:
        List of detected completion claims with context.
        (Fail-open: returns empty list on SDK unavailable or errors)
    """
    if not CLAUDE_SDK_AVAILABLE:
        return []  # Fail-open if SDK unavailable

    if not delta_text or len(delta_text.strip()) < 20:
        return []  # Nothing meaningful to analyze

    prompt = f"""Analyze the following conversation excerpt and identify any claims about task completion.

**Conversation Content:**
{delta_text[:3000]}

## Your Task

Identify any statements where the user or assistant claims that work is complete. Look for:
- Claims about completing tasks, features, or implementations
- Statements about tests passing or CI being green
- Claims that todos are done or workflow is complete
- Assertions that PRs are ready or mergeable

**Respond with a JSON array of claim strings, each with surrounding context (max 100 chars).**

Format: ["...claim with context...", "...another claim..."]

If no completion claims are found, respond with: []

Be specific - only include actual claims about completion, not general discussion."""

    try:
        options = ClaudeAgentOptions(
            cwd=str(project_root),
        )

        response_parts = []
        async with asyncio.timeout(CHECKER_TIMEOUT):
            async for message in query(prompt=prompt, options=options):
                if hasattr(message, "text"):
                    response_parts.append(message.text)
                elif hasattr(message, "content"):
                    response_parts.append(str(message.content))

        response = "".join(response_parts).strip()

        # Validate response before parsing
        if not _validate_sdk_response(response):
            # Security validation failed - fail-open (return empty list)
            return []

        # Parse JSON array from response
        import json

        claims = []

        # Try to extract JSON array
        if response.startswith("["):
            try:
                parsed = json.loads(response)
                if isinstance(parsed, list):
                    claims = parsed
            except json.JSONDecodeError:
                pass

        # Try to find JSON array in response if direct parse failed
        if not claims:
            match = re.search(r"\[.*?\]", response, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group())
                    if isinstance(parsed, list):
                        claims = parsed
                except json.JSONDecodeError:
                    pass

        # Validate and sanitize claims
        if claims:
            validated_claims = []
            for claim in claims[:100]:  # Max 100 items (schema validation)
                if claim and isinstance(claim, str):
                    # Sanitize HTML tags
                    sanitized = _sanitize_html(claim)
                    # Truncate to 200 chars (schema validation)
                    if len(sanitized) > 200:
                        sanitized = sanitized[:200]
                    validated_claims.append(sanitized)
            return validated_claims

        return []

    except Exception:
        return []  # Fail-open on any error


async def analyze_if_addressed(
    failure_id: str,
    failure_reason: str,
    delta_text: str,
    project_root: Path,
) -> str | None:
    """Use Claude SDK to check if delta content addresses a previous failure.

    Replaces heuristic keyword matching with LLM-powered analysis.

    Args:
        failure_id: ID of the failed consideration (e.g., "todos_complete")
        failure_reason: Human-readable reason the check failed
        delta_text: New transcript content since last block
        project_root: Project root directory

    Returns:
        Evidence string if delta addresses the failure, None otherwise.
        (Fail-open: returns None on SDK unavailable or errors)
    """
    if not CLAUDE_SDK_AVAILABLE:
        return None  # Fail-open if SDK unavailable

    if not delta_text or len(delta_text.strip()) < 20:
        return None  # Nothing meaningful to analyze

    prompt = f"""Analyze if the following new conversation content addresses a previous verification failure.

**Previous Failure:**
- Check ID: {failure_id}
- Reason it failed: {failure_reason}

**New Conversation Content:**
{delta_text[:3000]}

## Your Task

Determine if the new content shows evidence that the previously failed check has now been addressed.

Look for:
- Actions taken to fix the issue
- Evidence the concern was resolved
- Tool outputs or results showing completion
- Explicit discussion addressing the failure reason

**Respond with ONE of:**
- "ADDRESSED: [specific evidence from the conversation showing why]"
- "NOT ADDRESSED: [brief explanation]"

Be conservative - only say ADDRESSED if there is clear evidence in the new content."""

    try:
        options = ClaudeAgentOptions(
            cwd=str(project_root),
        )

        response_parts = []
        async with asyncio.timeout(CHECKER_TIMEOUT):
            async for message in query(prompt=prompt, options=options):
                if hasattr(message, "text"):
                    response_parts.append(message.text)
                elif hasattr(message, "content"):
                    response_parts.append(str(message.content))

        response = "".join(response_parts).strip()

        # Sanitize HTML before processing
        response = _sanitize_html(response)

        response_lower = response.lower()

        # Check for ADDRESSED indicator
        if "addressed:" in response_lower:
            # Extract the evidence
            idx = response.find("addressed:")
            evidence = response[idx + 10 :].strip()
            # Clean up and truncate
            evidence = evidence.replace("not addressed:", "").strip()
            if evidence and len(evidence) > 10:
                return evidence[:200]  # Truncate evidence
            return "Delta content addresses this concern"

        return None

    except Exception:
        return None  # Fail-open on any error


def analyze_claims_sync(delta_text: str, project_root: Path) -> list[str]:
    """Synchronous wrapper for analyze_claims with shutdown detection.

    During shutdown, returns empty list immediately to prevent asyncio hang.
    Otherwise, runs async analysis to detect completion claims in transcript.

    Args:
        delta_text: New transcript content since last block
        project_root: Project root directory

    Returns:
        List of detected completion claims, or [] if shutting down

    Shutdown Behavior:
        When AMPLIHACK_SHUTDOWN_IN_PROGRESS=1, immediately returns [] without
        starting async operation. This prevents asyncio event loop hangs during
        application teardown.

    Example:
        >>> # Normal operation - runs full analysis
        >>> claims = analyze_claims_sync("Task complete!", Path.cwd())
        >>> len(claims) > 0
        True

        >>> # During shutdown - returns empty list immediately
        >>> os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        >>> claims = analyze_claims_sync("Task complete!", Path.cwd())
        >>> claims
        []
    """
    # Shutdown check: bypass async operation during teardown
    if is_shutting_down():
        return []  # Fail-open: no claims detected during shutdown

    try:
        return asyncio.run(analyze_claims(delta_text, project_root))
    except Exception:
        return []  # Fail-open on any error


def analyze_if_addressed_sync(
    failure_id: str,
    failure_reason: str,
    delta_text: str,
    project_root: Path,
) -> str | None:
    """Synchronous wrapper for analyze_if_addressed with shutdown detection.

    During shutdown, returns None immediately to prevent asyncio hang.
    Otherwise, runs async analysis to check if failure was addressed.

    Args:
        failure_id: ID of the failed consideration
        failure_reason: Reason it failed
        delta_text: New transcript content
        project_root: Project root directory

    Returns:
        Evidence string if addressed, None if not addressed or shutting down

    Shutdown Behavior:
        When AMPLIHACK_SHUTDOWN_IN_PROGRESS=1, immediately returns None without
        starting async operation. This prevents asyncio event loop hangs during
        application teardown.

    Example:
        >>> # Normal operation - runs full analysis
        >>> evidence = analyze_if_addressed_sync(
        ...     "todos_complete", "3 TODOs incomplete",
        ...     "Completed all TODOs", Path.cwd()
        ... )
        >>> evidence is not None
        True

        >>> # During shutdown - returns None immediately
        >>> os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        >>> evidence = analyze_if_addressed_sync(
        ...     "todos_complete", "3 TODOs incomplete",
        ...     "Completed all TODOs", Path.cwd()
        ... )
        >>> evidence is None
        True
    """
    # Shutdown check: bypass async operation during teardown
    if is_shutting_down():
        return None  # Fail-open: no evidence found during shutdown

    try:
        return asyncio.run(
            analyze_if_addressed(failure_id, failure_reason, delta_text, project_root)
        )
    except Exception:
        return None  # Fail-open on any error


def analyze_consideration_sync(
    conversation: list[dict], consideration: dict, project_root: Path
) -> tuple[bool, str | None]:
    """Synchronous wrapper for analyze_consideration with shutdown detection.

    During shutdown, returns (True, None) immediately to prevent asyncio hang.
    Otherwise, runs async analysis to check if consideration is satisfied.

    Args:
        conversation: Session messages
        consideration: Consideration dict
        project_root: Project root

    Returns:
        Tuple of (satisfied, reason):
        - satisfied: True if consideration satisfied, False otherwise
        - reason: String explanation if not satisfied, None if satisfied
        Returns (True, None) during shutdown

    Shutdown Behavior:
        When AMPLIHACK_SHUTDOWN_IN_PROGRESS=1, immediately returns (True, None)
        without starting async operation. This prevents asyncio event loop hangs
        during application teardown.

        Fail-open philosophy: Assumes consideration is satisfied during shutdown
        to never block the user from exiting.

    Example:
        >>> # Normal operation - runs full analysis
        >>> conversation = [{"role": "user", "content": "Hello"}]
        >>> consideration = {"id": "tests_passing", "question": "Tests pass?"}
        >>> satisfied, reason = analyze_consideration_sync(
        ...     conversation, consideration, Path.cwd()
        ... )
        >>> isinstance(satisfied, bool)
        True

        >>> # During shutdown - returns satisfied immediately
        >>> os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"
        >>> satisfied, reason = analyze_consideration_sync(
        ...     conversation, consideration, Path.cwd()
        ... )
        >>> satisfied
        True
        >>> reason is None
        True
    """
    # Shutdown check: bypass async operation during teardown
    if is_shutting_down():
        return (True, None)  # Fail-open: assume satisfied during shutdown

    try:
        return asyncio.run(analyze_consideration(conversation, consideration, project_root))
    except Exception:
        return (True, None)  # Fail-open on any error


# For testing
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Test Claude-powered consideration analysis")
    parser.add_argument("transcript_file", type=Path, help="Transcript JSON file")
    parser.add_argument("consideration_id", type=str, help="Consideration ID to check")
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root directory"
    )

    args = parser.parse_args()

    # Load transcript
    with open(args.transcript_file) as f:
        transcript = json.load(f)

    # Example consideration
    consideration = {
        "id": args.consideration_id,
        "question": "Were all TODO items completed?",
        "description": "Check if all todo items in TodoWrite are marked as completed",
        "category": "Completion",
    }

    result = analyze_consideration_sync(transcript, consideration, args.project_root)
    print(f"\nConsideration '{consideration['id']}': {'SATISFIED' if result else 'NOT SATISFIED'}")
