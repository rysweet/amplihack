"""Output formatting utilities for Copilot CLI integration.

Provides consistent formatting for:
- Agent output
- Progress indicators
- Status messages
- Tables and lists
"""

import platform
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any

# Platform-specific emoji support
IS_WINDOWS = platform.system() == "Windows"


class StatusType(Enum):
    """Status message types."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    PROGRESS = "progress"


@dataclass
class FormattingConfig:
    """Configuration for output formatting."""

    use_color: bool = True
    use_emoji: bool = not IS_WINDOWS
    verbose: bool = False


class OutputFormatter:
    """Format output for consistent UX across Claude Code and Copilot CLI."""

    def __init__(self, config: FormattingConfig | None = None):
        """Initialize formatter.

        Args:
            config: Formatting configuration. Defaults to platform-appropriate config.
        """
        self.config = config or FormattingConfig()

        # Color codes (ANSI)
        self.colors = {
            "reset": "\033[0m" if self.config.use_color else "",
            "green": "\033[92m" if self.config.use_color else "",
            "red": "\033[91m" if self.config.use_color else "",
            "yellow": "\033[93m" if self.config.use_color else "",
            "blue": "\033[94m" if self.config.use_color else "",
            "cyan": "\033[96m" if self.config.use_color else "",
        }

        # Status symbols
        self.symbols = {
            StatusType.SUCCESS: "✓" if self.config.use_emoji else "[OK]",
            StatusType.ERROR: "✗" if self.config.use_emoji else "[ERROR]",
            StatusType.WARNING: "⚠" if self.config.use_emoji else "[WARN]",
            StatusType.INFO: "ℹ" if self.config.use_emoji else "[INFO]",
            StatusType.PROGRESS: "⋯" if self.config.use_emoji else "[...]",
        }

    def status(self, message: str, status_type: StatusType) -> str:
        """Format a status message.

        Args:
            message: Message to format
            status_type: Type of status

        Returns:
            Formatted status message
        """
        symbol = self.symbols[status_type]
        color_map = {
            StatusType.SUCCESS: self.colors["green"],
            StatusType.ERROR: self.colors["red"],
            StatusType.WARNING: self.colors["yellow"],
            StatusType.INFO: self.colors["blue"],
            StatusType.PROGRESS: self.colors["cyan"],
        }
        color = color_map[status_type]

        return f"{color}{symbol}{self.colors['reset']} {message}"

    def success(self, message: str) -> str:
        """Format a success message."""
        return self.status(message, StatusType.SUCCESS)

    def error(self, message: str) -> str:
        """Format an error message."""
        return self.status(message, StatusType.ERROR)

    def warning(self, message: str) -> str:
        """Format a warning message."""
        return self.status(message, StatusType.WARNING)

    def info(self, message: str) -> str:
        """Format an info message."""
        return self.status(message, StatusType.INFO)

    def progress(self, message: str) -> str:
        """Format a progress message."""
        return self.status(message, StatusType.PROGRESS)

    def table(self, headers: list[str], rows: list[list[Any]]) -> str:
        """Format data as a table.

        Args:
            headers: Column headers
            rows: Table rows

        Returns:
            Formatted table string
        """
        if not rows:
            return self.info("No data to display")

        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # Build table
        lines = []

        # Header
        header_line = " | ".join(
            f"{h:<{col_widths[i]}}" for i, h in enumerate(headers)
        )
        lines.append(header_line)

        # Separator
        separator = "-+-".join("-" * w for w in col_widths)
        lines.append(separator)

        # Rows
        for row in rows:
            row_line = " | ".join(
                f"{str(cell):<{col_widths[i]}}" for i, cell in enumerate(row)
            )
            lines.append(row_line)

        return "\n".join(lines)

    def list_items(self, items: list[str], numbered: bool = False) -> str:
        """Format a list of items.

        Args:
            items: Items to format
            numbered: Use numbered list (1., 2., 3.)

        Returns:
            Formatted list string
        """
        if not items:
            return self.info("No items to display")

        lines = []
        for i, item in enumerate(items, 1):
            prefix = f"{i}. " if numbered else "  • "
            lines.append(f"{prefix}{item}")

        return "\n".join(lines)

    def section(self, title: str, content: str) -> str:
        """Format a section with title and content.

        Args:
            title: Section title
            content: Section content

        Returns:
            Formatted section string
        """
        separator = "=" * len(title)
        return f"\n{title}\n{separator}\n{content}\n"


class ProgressIndicator:
    """Progress indicator for long-running operations."""

    def __init__(self, formatter: OutputFormatter | None = None):
        """Initialize progress indicator.

        Args:
            formatter: Output formatter. Creates default if None.
        """
        self.formatter = formatter or OutputFormatter()
        self.current_step = 0
        self.total_steps = 0
        self.current_message = ""

    def start(self, total_steps: int, initial_message: str = "Starting") -> None:
        """Start progress tracking.

        Args:
            total_steps: Total number of steps
            initial_message: Initial progress message
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.current_message = initial_message
        self._print_progress()

    def step(self, message: str) -> None:
        """Advance to next step.

        Args:
            message: Progress message for this step
        """
        self.current_step += 1
        self.current_message = message
        self._print_progress()

    def complete(self, message: str = "Complete") -> None:
        """Mark progress as complete.

        Args:
            message: Completion message
        """
        self.current_step = self.total_steps
        print(self.formatter.success(message))

    def _print_progress(self) -> None:
        """Print current progress."""
        if self.total_steps > 0:
            percent = int((self.current_step / self.total_steps) * 100)
            bar_length = 40
            filled = int((bar_length * self.current_step) / self.total_steps)
            bar = "█" * filled + "░" * (bar_length - filled)
            msg = f"[{bar}] {percent}% - {self.current_message}"
        else:
            msg = self.current_message

        # Use carriage return to overwrite previous line
        print(f"\r{self.formatter.progress(msg)}", end="", file=sys.stderr)
        if self.current_step >= self.total_steps:
            print()  # New line when complete


def format_agent_output(output: str, agent_name: str, formatter: OutputFormatter | None = None) -> str:
    """Format output from an agent invocation.

    Args:
        output: Raw agent output
        agent_name: Name of the agent
        formatter: Output formatter. Creates default if None.

    Returns:
        Formatted agent output
    """
    formatter = formatter or OutputFormatter()

    # Extract key sections from agent output
    lines = output.strip().split("\n")

    # Build formatted output
    result = []
    result.append(formatter.info(f"Agent: {agent_name}"))
    result.append("-" * 70)

    for line in lines:
        # Highlight error lines
        if "error" in line.lower() or "fail" in line.lower():
            result.append(formatter.error(line))
        # Highlight warning lines
        elif "warn" in line.lower():
            result.append(formatter.warning(line))
        # Highlight success lines
        elif "success" in line.lower() or "complete" in line.lower():
            result.append(formatter.success(line))
        else:
            result.append(line)

    result.append("-" * 70)

    return "\n".join(result)
