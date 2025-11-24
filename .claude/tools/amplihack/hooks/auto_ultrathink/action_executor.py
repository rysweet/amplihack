"""Action executor for auto-ultrathink feature.

Execute the decided action: invoke UltraThink automatically, ask user for confirmation,
or pass through unchanged.
"""

import sys
from dataclasses import dataclass
from typing import Optional

from decision_engine import Action, Decision


@dataclass
class ExecutionResult:
    """Result of action execution."""

    modified_prompt: str  # Original or modified prompt
    action_taken: Action  # INVOKE, ASK, or SKIP
    user_choice: Optional[str]  # User's choice if ASK (yes/no)
    metadata: dict  # Additional context


def execute_action(prompt: str, decision: Decision) -> ExecutionResult:
    """
    Execute the decided action.

    Args:
        prompt: Original user prompt
        decision: Decision from decision_engine

    Returns:
        ExecutionResult with modified prompt and metadata

    Raises:
        Never raises - returns pass-through on errors
    """
    try:
        if decision.action == Action.SKIP:
            return _execute_skip(prompt, decision)
        elif decision.action == Action.INVOKE:
            return _execute_invoke(prompt, decision)
        elif decision.action == Action.ASK:
            return _execute_ask(prompt, decision)
        else:
            # Unknown action - fail-open
            return _execute_skip(prompt, decision)

    except Exception as e:
        # Log error to stderr
        print(f"Action execution error: {e}", file=sys.stderr)

        # Fail-open: pass through
        return ExecutionResult(
            modified_prompt=prompt,
            action_taken=Action.SKIP,
            user_choice=None,
            metadata={"error": str(e)},
        )


def _execute_skip(prompt: str, decision: Decision) -> ExecutionResult:
    """Execute SKIP action."""
    return ExecutionResult(
        modified_prompt=prompt,
        action_taken=Action.SKIP,
        user_choice=None,
        metadata={
            "reason": decision.reason,
            "classification": decision.classification.reason,
        },
    )


def _execute_invoke(prompt: str, decision: Decision) -> ExecutionResult:
    """Execute INVOKE action."""
    modified_prompt = _modify_prompt_for_ultrathink(prompt)

    return ExecutionResult(
        modified_prompt=modified_prompt,
        action_taken=Action.INVOKE,
        user_choice=None,
        metadata={
            "reason": decision.reason,
            "confidence": decision.classification.confidence,
            "patterns": decision.classification.matched_patterns,
        },
    )


def _execute_ask(prompt: str, decision: Decision) -> ExecutionResult:
    """Execute ASK action (MVP: inject question)."""
    # Format question
    question = _format_user_question(decision)

    # Create modified prompt that includes question
    # Claude will ask user and then process based on response
    modified_prompt = f"{question}\n\nOriginal request: {prompt}"

    return ExecutionResult(
        modified_prompt=modified_prompt,
        action_taken=Action.ASK,
        user_choice=None,  # Will be determined in conversation
        metadata={
            "reason": decision.reason,
            "confidence": decision.classification.confidence,
            "question_injected": True,
        },
    )


def _modify_prompt_for_ultrathink(prompt: str) -> str:
    """Prepend /ultrathink to prompt."""
    # Handle edge cases
    if not prompt or prompt.isspace():
        return prompt

    # Already has /ultrathink? Don't duplicate
    if prompt.strip().startswith("/ultrathink"):
        return prompt

    # Prepend /ultrathink
    return f"/ultrathink {prompt}"


def _format_user_question(decision: Decision) -> str:
    """Format question for user."""
    confidence_pct = int(decision.classification.confidence * 100)
    patterns = ", ".join(decision.classification.matched_patterns)

    return f"""🤖 **UltraThink Recommendation**

{decision.reason}

- **Classification**: {patterns}
- **Confidence**: {confidence_pct}%

Would you like to use UltraThink for this request?"""
