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
from datetime import timezone
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

    def __init__(self, project_root: Path, log_func=None):
        """Initialize strategy.

        Args:
            project_root: Root directory of the project
            log_func: Optional logging function (for hooks)
        """
        self.project_root = project_root
        self.log = log_func or (lambda msg, level="INFO": print(f"[{level}] {msg}"))

    @abstractmethod
    def inject_context(self, context: dict[str, Any] | str) -> str:
        """Inject context for the launcher.

        Args:
            context: Context data to inject (dict or string)

        Returns:
            Formatted context string for the launcher
        """

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up any injected context."""

    @abstractmethod
    def handle_stop(self, input_data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle stop hook event.

        Args:
            input_data: Stop hook input data

        Returns:
            Strategy-specific modifications to stop behavior, or None for default
        """

    @abstractmethod
    def handle_pre_tool_use(self, input_data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle pre_tool_use hook event.

        Args:
            input_data: Tool use input data

        Returns:
            Strategy-specific modifications (block decisions, etc.), or None for default
        """

    @abstractmethod
    def handle_post_tool_use(self, input_data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle post_tool_use hook event.

        Args:
            input_data: Tool use result data

        Returns:
            Strategy-specific output (warnings, metadata), or None for default
        """

    @abstractmethod
    def handle_user_prompt_submit(self, input_data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle user_prompt_submit hook event.

        Args:
            input_data: User prompt data

        Returns:
            Strategy-specific additional context, or None for default
        """


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

    def inject_context(self, context: dict[str, Any] | str) -> str:
        """Write context to .claude/runtime/ for Claude to discover.

        Args:
            context: Context data (dict or string)

        Returns:
            Formatted context string

        Example:
            >>> strategy = ClaudeStrategy(Path.cwd())
            >>> formatted = strategy.inject_context({
            ...     "hook": "session_start",
            ...     "launcher": "claude",
            ...     "timestamp": "2025-01-17T12:00:00Z"
            ... })
        """
        import json
        from datetime import datetime

        # Handle string context (like preferences)
        if isinstance(context, str):
            # For Claude Code, just return the context with minimal formatting
            return f"\n## 🎯 USER PREFERENCES (MANDATORY - MUST FOLLOW)\n\n{context}\n"

        # Handle dict context
        context_path = self.project_root / self.CONTEXT_FILE
        context_path.parent.mkdir(parents=True, exist_ok=True)

        # Add timestamp if not present
        if "timestamp" not in context:
            context["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Write context with error handling
        try:
            context_path.write_text(json.dumps(context, indent=2))
        except OSError as e:
            # Fail gracefully - log error but don't crash
            self.log(f"Failed to write context to {context_path}: {e}", "WARNING")
            # Continue anyway - context injection optional

        # Return formatted context
        return json.dumps(context, indent=2)

    def cleanup(self) -> None:
        """Remove injected context file.

        Example:
            >>> strategy = ClaudeStrategy(Path.cwd())
            >>> strategy.cleanup()  # Removes .claude/runtime/hook_context.json
        """
        context_path = self.project_root / self.CONTEXT_FILE
        if context_path.exists():
            context_path.unlink()

    def handle_stop(self, input_data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle stop hook for Claude Code.

        Claude Code uses standard stop hook behavior, no special handling needed.

        Args:
            input_data: Stop hook input data

        Returns:
            None (use default behavior)
        """
        # Claude Code uses default stop behavior
        return None

    def handle_pre_tool_use(self, input_data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle pre_tool_use hook for Claude Code.

        Claude Code uses standard pre-tool validation.

        Args:
            input_data: Tool use input data

        Returns:
            None (use default behavior)
        """
        # Claude Code uses default pre-tool behavior
        return None

    def handle_post_tool_use(self, input_data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle post_tool_use hook for Claude Code.

        Claude Code uses standard post-tool logging.

        Args:
            input_data: Tool use result data

        Returns:
            None (use default behavior)
        """
        # Claude Code uses default post-tool behavior
        return None

    def handle_user_prompt_submit(self, input_data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle user_prompt_submit hook for Claude Code.

        Claude Code uses standard prompt processing.

        Args:
            input_data: User prompt data

        Returns:
            None (use default behavior)
        """
        # Claude Code uses default prompt handling
        return None


class CopilotStrategy(HookStrategy):
    """Copilot CLI strategy - AGENTS.md workaround (push model).

    Copilot CLI auto-discovers AGENTS.md from repository root.
    We inject context there so Copilot loads it at session start.

    This is a workaround for Copilot's observe-only hook model.

    Example:
        >>> strategy = CopilotStrategy(Path("/project"))
        >>> strategy.inject_context({"agent": "builder", "task": "implement"})
        >>> # Copilot discovers context in AGENTS.md at repo root
    """

    AGENTS_FILE = "AGENTS.md"  # Must be in repository root per Copilot CLI docs
    CONTEXT_MARKER_START = "<!-- AMPLIHACK_CONTEXT_START -->"
    CONTEXT_MARKER_END = "<!-- AMPLIHACK_CONTEXT_END -->"

    MAX_CONTEXT_SIZE = 10 * 1024 * 1024  # 10MB limit for context injection

    def inject_context(self, context: dict[str, Any] | str) -> str:
        """Inject context into AGENTS.md at repository root.

        Args:
            context: Context data (dict or string)

        Returns:
            Formatted context string

        Raises:
            ValueError: If context exceeds MAX_CONTEXT_SIZE

        Example:
            >>> strategy = CopilotStrategy(Path.cwd())
            >>> formatted = strategy.inject_context({
            ...     "hook": "session_start",
            ...     "launcher": "copilot",
            ...     "workflow": "DEFAULT_WORKFLOW"
            ... })
            >>> # Context now in AGENTS.md at repository root
        """
        import json
        from datetime import datetime

        # Security: Prevent resource exhaustion
        context_str = context if isinstance(context, str) else json.dumps(context)
        if len(context_str) > self.MAX_CONTEXT_SIZE:
            raise ValueError(
                f"Context too large: {len(context_str)} bytes (max {self.MAX_CONTEXT_SIZE})"
            )

        agents_path = self.project_root / self.AGENTS_FILE

        # Security: Validate path is within project root
        try:
            resolved_path = agents_path.resolve(strict=False)
            if not resolved_path.is_relative_to(self.project_root.resolve()):
                raise ValueError(f"AGENTS.md path escapes project root: {resolved_path}")
        except (ValueError, RuntimeError) as e:
            self.log(f"Path validation failed: {e}", "ERROR")
            raise

        # Ensure directory exists
        agents_path.parent.mkdir(parents=True, exist_ok=True)

        # Handle string context (like preferences)
        if isinstance(context, str):
            context_md = self._format_string_context(context)
        else:
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

        # Write updated content with error handling
        try:
            agents_path.write_text("\n".join(lines))
        except OSError as e:
            # Fail gracefully - log error but don't crash
            self.log(f"Failed to write AGENTS.md to {agents_path}: {e}", "WARNING")
            # Continue anyway - context injection optional

        # Return the markdown context for logging
        return context_md

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

    def _format_string_context(self, context: str) -> str:
        """Format string context (like preferences) as markdown.

        Args:
            context: String context (typically preferences)

        Returns:
            Markdown-formatted context section
        """
        lines = [
            self.CONTEXT_MARKER_START,
            "",
            "## 🎯 USER PREFERENCES (MANDATORY - MUST FOLLOW)",
            "",
            context,
            "",
            self.CONTEXT_MARKER_END,
        ]

        return "\n".join(lines)

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

    def handle_stop(self, input_data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle stop hook for Copilot CLI.

        For Copilot CLI, we log stop events to AGENTS.md but don't modify behavior.

        Args:
            input_data: Stop hook input data

        Returns:
            None (use default behavior - logging only)
        """
        # Log the stop event (for debugging Copilot sessions)
        self.log("Stop hook triggered in Copilot CLI mode - logging only")
        return None

    def handle_pre_tool_use(self, input_data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle pre_tool_use hook for Copilot CLI.

        For Copilot CLI, we log tool use but don't block operations.
        Permission control is handled by Copilot's own mechanisms.

        Args:
            input_data: Tool use input data

        Returns:
            None (logging only, no blocking)
        """
        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "unknown")
        self.log(f"Pre-tool hook in Copilot mode - tool: {tool_name} (logging only)")
        return None

    def handle_post_tool_use(self, input_data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle post_tool_use hook for Copilot CLI.

        For Copilot CLI, we log tool results but don't modify output.

        Args:
            input_data: Tool use result data

        Returns:
            None (logging only)
        """
        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "unknown")
        self.log(f"Post-tool hook in Copilot mode - tool: {tool_name} (logging only)")
        return None

    def handle_user_prompt_submit(self, input_data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle user_prompt_submit hook for Copilot CLI.

        For Copilot CLI, we log prompts but context is already in AGENTS.md.

        Args:
            input_data: User prompt data

        Returns:
            None (context already injected via AGENTS.md)
        """
        self.log("User prompt submit in Copilot mode - context via AGENTS.md")
        return None
