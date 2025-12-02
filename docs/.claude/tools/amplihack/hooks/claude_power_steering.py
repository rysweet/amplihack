#!/usr/bin/env python3
"""
Claude SDK-based power-steering analysis.

Uses Claude Agent SDK to intelligently analyze session transcripts against
considerations, replacing heuristic pattern matching with AI-powered analysis.

Philosophy:
- Ruthlessly Simple: Single-purpose module with clear contract
- Fail-Open: Never block users due to bugs - always allow stop on errors
- Zero-BS: No stubs, every function works or doesn't exist
- Modular: Self-contained brick that plugs into power_steering_checker
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional

# Try to import Claude SDK
try:
    from claude_agent_sdk import ClaudeAgentOptions, query

    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False

# Template paths (relative to this file)
TEMPLATE_DIR = Path(__file__).parent / "templates"
POWER_STEERING_PROMPT_TEMPLATE = TEMPLATE_DIR / "power_steering_prompt.txt"


def load_prompt_template() -> Optional[str]:
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


def format_prompt(template: str, variables: Dict[str, str]) -> str:
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
    conversation: List[Dict], consideration: Dict, project_root: Path
) -> bool:
    """Use Claude SDK to analyze if consideration is satisfied.

    Args:
        conversation: Session messages (list of dicts)
        consideration: Consideration dict (id, question, description, etc.)
        project_root: Project root directory

    Returns:
        True if consideration satisfied, False otherwise
        (Fail-open: returns True on SDK unavailable or errors)
    """
    if not CLAUDE_SDK_AVAILABLE:
        return True  # Fail-open if SDK unavailable

    # Format prompt for this consideration
    try:
        prompt = _format_consideration_prompt(consideration, conversation)
    except Exception:
        return True  # Fail-open on prompt formatting error

    try:
        options = ClaudeAgentOptions(
            cwd=str(project_root),
            permission_mode="bypassPermissions",
        )

        # Query Claude
        response_parts = []
        async for message in query(prompt=prompt, options=options):
            if hasattr(message, "text"):
                response_parts.append(message.text)
            elif hasattr(message, "content"):
                response_parts.append(str(message.content))

        # Join all parts
        response = "".join(response_parts).lower()

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
            if indicator in response:
                return False

        # Then check for satisfied indicators
        for indicator in satisfied_indicators:
            if indicator in response:
                return True

        # Ambiguous response - fail-open (assume satisfied)
        return True

    except Exception:
        # Fail-open on any error
        return True


def _format_consideration_prompt(consideration: Dict, conversation: List[Dict]) -> str:
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


def _format_conversation_summary(conversation: List[Dict], max_length: int = 5000) -> str:
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

        # Truncate long messages
        if len(content_text) > 500:
            content_text = content_text[:497] + "..."

        msg_summary = f"\n**Message {i + 1} ({role}):** {content_text}\n"

        # Check if adding this would exceed limit
        if current_length + len(msg_summary) > max_length:
            summary_parts.append(f"\n[... {len(conversation) - i} more messages ...]")
            break

        summary_parts.append(msg_summary)
        current_length += len(msg_summary)

    return "".join(summary_parts)


async def analyze_claims(delta_text: str, project_root: Path) -> List[str]:
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
            permission_mode="bypassPermissions",
        )

        response_parts = []
        async for message in query(prompt=prompt, options=options):
            if hasattr(message, "text"):
                response_parts.append(message.text)
            elif hasattr(message, "content"):
                response_parts.append(str(message.content))

        response = "".join(response_parts).strip()

        # Parse JSON array from response
        import json

        # Try to extract JSON array
        if response.startswith("["):
            try:
                claims = json.loads(response)
                if isinstance(claims, list):
                    return [str(c) for c in claims if c]
            except json.JSONDecodeError:
                pass

        # Try to find JSON array in response
        import re

        match = re.search(r"\[.*?\]", response, re.DOTALL)
        if match:
            try:
                claims = json.loads(match.group())
                if isinstance(claims, list):
                    return [str(c) for c in claims if c]
            except json.JSONDecodeError:
                pass

        return []

    except Exception:
        return []  # Fail-open on any error


async def analyze_if_addressed(
    failure_id: str,
    failure_reason: str,
    delta_text: str,
    project_root: Path,
) -> Optional[str]:
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
            permission_mode="bypassPermissions",
        )

        response_parts = []
        async for message in query(prompt=prompt, options=options):
            if hasattr(message, "text"):
                response_parts.append(message.text)
            elif hasattr(message, "content"):
                response_parts.append(str(message.content))

        response = "".join(response_parts).strip().lower()

        # Check for ADDRESSED indicator
        if "addressed:" in response:
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


def analyze_claims_sync(delta_text: str, project_root: Path) -> List[str]:
    """Synchronous wrapper for analyze_claims.

    Args:
        delta_text: New transcript content since last block
        project_root: Project root directory

    Returns:
        List of detected completion claims
    """
    try:
        return asyncio.run(analyze_claims(delta_text, project_root))
    except Exception:
        return []  # Fail-open on any error


def analyze_if_addressed_sync(
    failure_id: str,
    failure_reason: str,
    delta_text: str,
    project_root: Path,
) -> Optional[str]:
    """Synchronous wrapper for analyze_if_addressed.

    Args:
        failure_id: ID of the failed consideration
        failure_reason: Reason it failed
        delta_text: New transcript content
        project_root: Project root directory

    Returns:
        Evidence string if addressed, None otherwise
    """
    try:
        return asyncio.run(
            analyze_if_addressed(failure_id, failure_reason, delta_text, project_root)
        )
    except Exception:
        return None  # Fail-open on any error


def analyze_consideration_sync(
    conversation: List[Dict], consideration: Dict, project_root: Path
) -> bool:
    """Synchronous wrapper for analyze_consideration.

    Args:
        conversation: Session messages
        consideration: Consideration dict
        project_root: Project root

    Returns:
        True if consideration satisfied, False otherwise
    """
    try:
        return asyncio.run(analyze_consideration(conversation, consideration, project_root))
    except Exception:
        return True  # Fail-open on any error


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
