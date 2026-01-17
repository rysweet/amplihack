"""Claude Code Strategy for Adaptive Hooks.

Philosophy:
- Use Claude's hookSpecificOutput mechanism for context injection
- Power steering via hook blocking (return decision, let Claude continue)
- Zero external dependencies

This strategy implements Claude Code's specific mechanisms for context
injection and autonomous power steering.
"""

from typing import Dict, Any, Optional

from .base import HookStrategy


class ClaudeStrategy(HookStrategy):
    """Hook strategy for Claude Code launcher.

    Claude Code uses a specific mechanism for hook-to-session communication:
    - Context injection: Return {"hookSpecificOutput": {"additionalContext": ...}}
    - Power steering: Hook blocks, returns, and Claude continues autonomously

    See Claude Code hook documentation for details.
    """

    def inject_context(self, context: str) -> Dict[str, Any]:
        """Inject context into Claude Code session.

        Claude Code hooks can inject context by returning a specific
        dictionary structure in hookSpecificOutput.

        Args:
            context: Context string (markdown or plain text)

        Returns:
            Dictionary with hookSpecificOutput structure for Claude Code

        Example return value:
            {
                "hookSpecificOutput": {
                    "additionalContext": "# Session Context\n\n..."
                }
            }
        """
        return {
            "hookSpecificOutput": {
                "additionalContext": context
            }
        }

    def power_steer(self, prompt: str, session_id: Optional[str] = None) -> bool:
        """Execute power steering in Claude Code.

        For Claude Code, power steering works via hook blocking:
        1. Hook returns a "block" decision with the prompt
        2. Claude Code continues the session with that prompt
        3. No external process needed

        Args:
            prompt: The prompt to execute
            session_id: Not used for Claude (hook manages this internally)

        Returns:
            True (steering handled by hook return, not here)

        Note:
            The actual steering happens in the hook's decision logic,
            not in this method. This method just confirms that steering
            is supported and will be handled.
        """
        # For Claude, the hook infrastructure handles steering via its
        # decision return value. This method just validates that steering
        # is possible.
        return True


__all__ = ["ClaudeStrategy"]
