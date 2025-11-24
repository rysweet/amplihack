"""Hook integration for auto-ultrathink feature.

Integrate auto-ultrathink pipeline into Claude Code's user_prompt_submit.py hook.
Orchestrates all modules to provide seamless auto-invocation experience.
"""

import sys
import time
from typing import Optional

from action_executor import execute_action
from decision_engine import make_decision
from logger import log_auto_ultrathink, log_error
from preference_manager import get_auto_ultrathink_preference
from request_classifier import classify_request


def auto_ultrathink_hook(prompt: str, context: dict) -> str:
    """
    Hook function to integrate auto-ultrathink into Claude Code.

    Args:
        prompt: Raw user input string
        context: Session context from Claude Code
            - session_id: str
            - user_id: str (optional)
            - preferences_path: str (optional)

    Returns:
        Modified prompt (with /ultrathink prepended if needed)

    Raises:
        Never raises - returns original prompt on errors
    """
    start_time = time.time()

    try:
        # 1. Quick check: already a slash command?
        if prompt.strip().startswith("/"):
            return prompt

        # Get session ID (use "unknown" if not provided)
        session_id = context.get("session_id", "unknown")

        # 2. Classify request
        try:
            classification = classify_request(prompt)
        except Exception as e:
            log_error(session_id, "classification", e, prompt)
            return prompt

        # 3. Get user preference
        try:
            preference = get_auto_ultrathink_preference()
        except Exception as e:
            log_error(session_id, "preference", e, prompt)
            return prompt

        # 4. Make decision
        try:
            decision = make_decision(classification, preference, prompt)
        except Exception as e:
            log_error(session_id, "decision", e, prompt)
            return prompt

        # 5. Execute action
        try:
            result = execute_action(prompt, decision)
        except Exception as e:
            log_error(session_id, "execution", e, prompt)
            return prompt

        # 6. Log result
        try:
            execution_time_ms = (time.time() - start_time) * 1000
            log_auto_ultrathink(
                session_id=session_id,
                prompt=prompt,
                classification=classification,
                preference=preference,
                decision=decision,
                result=result,
                execution_time_ms=execution_time_ms,
            )
        except Exception as e:
            # Logging errors shouldn't block pipeline
            print(f"Logging error: {e}", file=sys.stderr)

        # 7. Return modified prompt
        return result.modified_prompt

    except Exception as e:
        # Comprehensive error handling
        print(f"Auto-ultrathink hook error: {e}", file=sys.stderr)

        # Fail-open: return original prompt
        return prompt


def process_request(prompt: str, context: Optional[dict] = None) -> str:
    """
    Convenience wrapper for processing requests.

    This provides a simpler interface for testing and integration.

    Args:
        prompt: Raw user input string
        context: Optional session context (uses default if not provided)

    Returns:
        Modified prompt
    """
    if context is None:
        context = {"session_id": "default"}

    return auto_ultrathink_hook(prompt, context)
