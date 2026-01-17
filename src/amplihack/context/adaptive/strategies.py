"""Hook strategies for different launchers.

Provides launcher-specific strategies for context injection:
- Claude Code: Direct injection (pull model)
- Copilot CLI: AGENTS.md workaround (push model)

Philosophy:
- Strategy pattern for launcher-specific behavior
- Simple implementations (file-based for both)
- No complex injection frameworks
- Self-contained and regeneratable
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class HookStrategy(ABC):
    """Base strategy for launcher-specific hook behavior.

    Each launcher has different context injection mechanisms:
    - Claude Code: Pulls from .claude/ automatically
    - Copilot CLI: Requires explicit @file references or AGENTS.md injection

    Example:
        >>> strategy = ClaudeStrategy(Path("/project"))
        >>> strategy.inject_context({"key": "value"})
    """

    def __init__(self, project_root: Path):
        """Initialize strategy.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root

    @abstractmethod
    def inject_context(self, context: dict[str, Any]) -> None:
        """Inject context for the launcher.

        Args:
            context: Context data to inject
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up any injected context."""
        pass


class ClaudeStrategy(HookStrategy):
    """Claude Code strategy - direct injection (pull model).

    Claude Code automatically pulls from .claude/ directory, so we just
    write context files there and Claude discovers them.

    Example:
        >>> strategy = ClaudeStrategy(Path("/project"))
        >>> strategy.inject_context({"agent": "builder", "task": "implement"})
        >>> # Claude Code automatically discovers .claude/runtime/context.json
    """

    CONTEXT_FILE = ".claude/runtime/hook_context.json"

    def inject_context(self, context: dict[str, Any]) -> None:
        """Write context to .claude/runtime/ for Claude to discover.

        Args:
            context: Context data (will be serialized to JSON)

        Example:
            >>> strategy = ClaudeStrategy(Path.cwd())
            >>> strategy.inject_context({
            ...     "hook": "session_start",
            ...     "launcher": "claude",
            ...     "timestamp": "2025-01-17T12:00:00Z"
            ... })
        """
        import json
        from datetime import datetime, timezone

        context_path = self.project_root / self.CONTEXT_FILE
        context_path.parent.mkdir(parents=True, exist_ok=True)

        # Add timestamp if not present
        if "timestamp" not in context:
            context["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Write context
        context_path.write_text(json.dumps(context, indent=2))

    def cleanup(self) -> None:
        """Remove injected context file.

        Example:
            >>> strategy = ClaudeStrategy(Path.cwd())
            >>> strategy.cleanup()  # Removes .claude/runtime/hook_context.json
        """
        context_path = self.project_root / self.CONTEXT_FILE
        if context_path.exists():
            context_path.unlink()


class CopilotStrategy(HookStrategy):
    """Copilot CLI strategy - AGENTS.md workaround (push model).

    Copilot CLI doesn't auto-discover .claude/ files. Instead, we inject
    context into .github/agents/AGENTS.md which Copilot loads automatically.

    This is a workaround until Copilot gets proper context injection APIs.

    Example:
        >>> strategy = CopilotStrategy(Path("/project"))
        >>> strategy.inject_context({"agent": "builder", "task": "implement"})
        >>> # Copilot discovers context in .github/agents/AGENTS.md
    """

    AGENTS_FILE = ".github/agents/AGENTS.md"
    CONTEXT_MARKER_START = "<!-- AMPLIHACK_CONTEXT_START -->"
    CONTEXT_MARKER_END = "<!-- AMPLIHACK_CONTEXT_END -->"

    def inject_context(self, context: dict[str, Any]) -> None:
        """Inject context into .github/agents/AGENTS.md.

        Args:
            context: Context data (will be formatted as markdown)

        Example:
            >>> strategy = CopilotStrategy(Path.cwd())
            >>> strategy.inject_context({
            ...     "hook": "session_start",
            ...     "launcher": "copilot",
            ...     "workflow": "DEFAULT_WORKFLOW"
            ... })
            >>> # Context now in .github/agents/AGENTS.md
        """
        import json
        from datetime import datetime, timezone

        agents_path = self.project_root / self.AGENTS_FILE

        # Ensure directory exists
        agents_path.parent.mkdir(parents=True, exist_ok=True)

        # Add timestamp if not present
        if "timestamp" not in context:
            context["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Format context as markdown
        context_md = self._format_context_markdown(context)

        # Read existing content or create new
        if agents_path.exists():
            content = agents_path.read_text()
            # Remove old context if present
            content = self._remove_old_context(content)
        else:
            content = "# Amplihack Agents\n\n"

        # Inject context at the top (after title)
        lines = content.split("\n")
        title_line = 0
        for i, line in enumerate(lines):
            if line.startswith("# "):
                title_line = i
                break

        # Insert context after title
        lines.insert(title_line + 1, "\n" + context_md + "\n")

        # Write updated content
        agents_path.write_text("\n".join(lines))

    def cleanup(self) -> None:
        """Remove injected context from AGENTS.md.

        Example:
            >>> strategy = CopilotStrategy(Path.cwd())
            >>> strategy.cleanup()  # Removes context markers from AGENTS.md
        """
        agents_path = self.project_root / self.AGENTS_FILE

        if not agents_path.exists():
            return

        content = agents_path.read_text()
        cleaned = self._remove_old_context(content)

        # Only write if content changed
        if cleaned != content:
            agents_path.write_text(cleaned)

    def _format_context_markdown(self, context: dict[str, Any]) -> str:
        """Format context as markdown section.

        Args:
            context: Context data

        Returns:
            Markdown-formatted context section
        """
        import json

        lines = [
            self.CONTEXT_MARKER_START,
            "",
            "## Current Session Context",
            "",
            "**Launcher**: Copilot CLI (via amplihack)",
            "",
            "**Context Data**:",
            "```json",
            json.dumps(context, indent=2),
            "```",
            "",
            self.CONTEXT_MARKER_END,
        ]

        return "\n".join(lines)

    def _remove_old_context(self, content: str) -> str:
        """Remove old context markers from content.

        Args:
            content: Current AGENTS.md content

        Returns:
            Content with context markers removed
        """
        if self.CONTEXT_MARKER_START not in content:
            return content

        # Find marker positions
        start_idx = content.find(self.CONTEXT_MARKER_START)
        end_idx = content.find(self.CONTEXT_MARKER_END)

        if start_idx == -1 or end_idx == -1:
            return content

        # Remove everything between markers (inclusive)
        before = content[:start_idx]
        after = content[end_idx + len(self.CONTEXT_MARKER_END) :]

        # Clean up extra newlines
        result = before.rstrip() + "\n\n" + after.lstrip()

        return result
