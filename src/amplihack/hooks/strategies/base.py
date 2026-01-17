"""Base Strategy for Adaptive Hooks.

Philosophy:
- Strategy pattern for launcher-specific behavior
- Abstract base class defines contract
- Each launcher gets its own concrete strategy

This module defines the interface that all hook strategies must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class HookStrategy(ABC):
    """Abstract base class for hook strategies.

    Each AI launcher (Claude, Copilot, Codex) has different mechanisms for:
    1. Injecting context into sessions
    2. Power steering (autonomous prompt execution)

    Concrete strategies implement these mechanisms for their specific launcher.
    """

    @abstractmethod
    def inject_context(self, context: str) -> Dict[str, Any]:
        """Inject context into the current session.

        Args:
            context: Context string to inject (markdown or plain text)

        Returns:
            Dictionary for hook output. Structure varies by launcher:
            - Claude: {"hookSpecificOutput": {"additionalContext": context}}
            - Copilot: {} (context written to file instead)
            - Others: Implementation-specific

        The hook infrastructure uses this return value to communicate
        context to the launcher.
        """
        pass

    @abstractmethod
    def power_steer(self, prompt: str, session_id: Optional[str] = None) -> bool:
        """Execute autonomous power steering.

        Power steering = The hook autonomously continues the session with
        a new prompt, without user intervention.

        Args:
            prompt: The prompt to execute
            session_id: Session identifier (launcher-specific, optional)

        Returns:
            True if steering was initiated successfully, False otherwise

        Implementation approaches:
        - Claude: Hook blocks and returns decision, letting Claude continue
        - Copilot: Spawn subprocess with --continue flag
        - Others: Implementation-specific
        """
        pass

    def get_launcher_name(self) -> str:
        """Get the name of this strategy's launcher.

        Returns:
            Launcher name (e.g., "claude", "copilot")
        """
        # Default implementation extracts from class name
        # ClaudeStrategy -> "claude"
        class_name = self.__class__.__name__
        if class_name.endswith("Strategy"):
            return class_name[:-8].lower()
        return class_name.lower()


__all__ = ["HookStrategy"]
