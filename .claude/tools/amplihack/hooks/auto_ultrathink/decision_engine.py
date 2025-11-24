"""Decision engine for auto-ultrathink feature.

Combines classification results and user preferences to decide what action to take:
invoke UltraThink, ask user, or skip.
"""

import sys
from dataclasses import dataclass
from enum import Enum

from preference_manager import AutoUltraThinkPreference, is_excluded
from request_classifier import Classification


class Action(Enum):
    """Action to take based on decision."""

    INVOKE = "invoke"  # Automatically invoke UltraThink
    ASK = "ask"  # Ask user for confirmation
    SKIP = "skip"  # Don't invoke, pass through


@dataclass
class Decision:
    """Result of decision-making process."""

    action: Action
    reason: str
    classification: Classification
    preference: AutoUltraThinkPreference


def make_decision(
    classification: Classification,
    preference: AutoUltraThinkPreference,
    prompt: str,
) -> Decision:
    """
    Decide what action to take based on classification and preference.

    Args:
        classification: Classification result from request_classifier
        preference: User preference from preference_manager
        prompt: Original user prompt (for exclusion checking)

    Returns:
        Decision with action and reasoning

    Raises:
        Never raises - returns safe default (SKIP) on errors
    """
    try:
        # 1. Check if disabled
        if preference.mode == "disabled":
            return Decision(
                action=Action.SKIP,
                reason="Auto-ultrathink is disabled by user preference",
                classification=classification,
                preference=preference,
            )

        # 2. Check if classification says not needed
        if not classification.needs_ultrathink:
            return Decision(
                action=Action.SKIP,
                reason=f"Classification: {classification.reason}",
                classification=classification,
                preference=preference,
            )

        # 3. Check confidence threshold
        if classification.confidence < preference.confidence_threshold:
            return Decision(
                action=Action.SKIP,
                reason=(
                    f"Confidence {classification.confidence:.2f} below "
                    f"threshold {preference.confidence_threshold:.2f}"
                ),
                classification=classification,
                preference=preference,
            )

        # 4. Check excluded patterns
        if is_excluded(prompt, preference.excluded_patterns):
            return Decision(
                action=Action.SKIP,
                reason="Prompt matches excluded pattern",
                classification=classification,
                preference=preference,
            )

        # 5. Apply mode
        if preference.mode == "enabled":
            return Decision(
                action=Action.INVOKE,
                reason=(
                    f"Auto-invoke: {classification.reason} "
                    f"(confidence: {classification.confidence:.2f})"
                ),
                classification=classification,
                preference=preference,
            )
        elif preference.mode == "ask":
            return Decision(
                action=Action.ASK,
                reason=(
                    f"Recommendation: {classification.reason} "
                    f"(confidence: {classification.confidence:.2f})"
                ),
                classification=classification,
                preference=preference,
            )
        else:
            # Fallback for unknown mode (should never happen)
            return Decision(
                action=Action.SKIP,
                reason=f"Unknown preference mode: {preference.mode}",
                classification=classification,
                preference=preference,
            )

    except Exception as e:
        # Log error to stderr
        print(f"Decision error: {e}", file=sys.stderr)

        # Fail-safe: SKIP
        return Decision(
            action=Action.SKIP,
            reason=f"Decision failed: {type(e).__name__}",
            classification=classification,
            preference=preference,
        )
