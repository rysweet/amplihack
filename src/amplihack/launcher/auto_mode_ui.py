"""Rich CLI user interface for auto mode interactive display.

This module provides a full-screen terminal UI using the Rich library,
displaying auto mode execution state with 5 main panels:
- Title (generated from prompt)
- Session details (turn, time, costs)
- Todo list
- Log streaming area
- Prompt input area
"""

import select
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any, Deque, Dict, List, Optional

try:
    from rich import box
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Define placeholder types for type hints when Rich not available
    if not TYPE_CHECKING:
        Layout = Any
        Panel = Any
        Live = Any

from .auto_mode_state import AutoModeState


class AutoModeUI:
    """Rich CLI interface for auto mode execution.

    Provides a full-screen terminal UI with real-time updates for:
    - Session title (generated from prompt)
    - Session details (turn counter, elapsed time, cost tracking)
    - Todo list with status indicators
    - Streaming log output
    - Prompt input area for injecting new instructions

    Keyboard commands:
    - x: Exit UI (auto mode continues in background)
    - h: Show help overlay
    """

    def __init__(self, state: AutoModeState, auto_mode, working_dir: Path):
        """Initialize UI.

        Args:
            state: Shared AutoModeState instance
            auto_mode: AutoMode instance (for prompt and append_dir access)
            working_dir: Working directory for instruction files
        """
        if not RICH_AVAILABLE:
            raise ImportError(
                "Rich library required for UI mode. Install with: pip install rich"
            )

        self.state = state
        self.auto_mode = auto_mode
        self.working_dir = working_dir
        self.console = Console()

        # UI state
        self._should_exit = False
        self._showing_help = False
        self._pending_input: Deque[str] = deque()

        # Generate title
        self.title = self._generate_title_from_prompt(auto_mode.prompt)

        # Create layout
        self.layout = self._create_layout()

        # Update throttling (max 30 updates/sec)
        self._last_update = 0.0
        self._update_interval = 1.0 / 30.0

    def _generate_title_from_prompt(self, prompt: str) -> str:
        """Generate short title from user prompt.

        Simple truncation of prompt for display.

        Args:
            prompt: User's original prompt

        Returns:
            Title string (max 50 chars)
        """
        if not prompt or not prompt.strip():
            return "Auto Mode Session"

        # Simple truncation
        if len(prompt) <= 50:
            return prompt

        return prompt[:47] + "..."

    def _create_layout(self) -> Layout:
        """Create Rich layout structure.

        Returns:
            Configured Layout instance with 5 areas
        """
        layout = Layout()

        # Split into 5 rows
        layout.split(
            Layout(name="title", size=3),
            Layout(name="session", size=3),
            Layout(name="todos", size=10),
            Layout(name="logs", ratio=1),
            Layout(name="input", size=5),
        )

        return layout

    def _build_title_panel(self) -> Panel:
        """Build title panel.

        Returns:
            Rich Panel with session title
        """
        title_text = Text(self.title, style="bold cyan", justify="center")
        return Panel(title_text, box=box.ROUNDED, border_style="cyan")

    def _build_session_panel(self) -> Panel:
        """Build session details panel.

        Shows turn counter, elapsed time, and cost tracking.

        Returns:
            Rich Panel with session info
        """
        snapshot = self.state.snapshot()

        # Format elapsed time
        elapsed = snapshot['start_time']
        if elapsed > 0:
            elapsed_sec = time.time() - elapsed
            if elapsed_sec < 0:
                elapsed_str = "0s"
            elif elapsed_sec < 60:
                elapsed_str = f"{int(elapsed_sec)}s"
            else:
                minutes = int(elapsed_sec // 60)
                seconds = int(elapsed_sec % 60)
                elapsed_str = f"{minutes}m {seconds}s"
        else:
            elapsed_str = "0s"

        # Format costs
        costs = snapshot['costs']
        input_tokens = costs.get('input_tokens', 0)
        output_tokens = costs.get('output_tokens', 0)
        estimated_cost = costs.get('estimated_cost', 0.0)

        # Format numbers with commas
        input_str = f"{input_tokens:,}" if input_tokens else "0"
        output_str = f"{output_tokens:,}" if output_tokens else "0"
        cost_str = f"${estimated_cost:.4f}" if estimated_cost else "$0.0000"

        # Status indicator
        status = snapshot['status']
        if status == "running":
            status_icon = "▶"
            status_style = "green"
        elif status == "completed":
            status_icon = "✓"
            status_style = "bright_green"
        elif status == "error":
            status_icon = "✗"
            status_style = "red"
        else:
            status_icon = "◆"
            status_style = "white"

        # Build table
        table = Table.grid(padding=(0, 2))
        table.add_column(justify="left")
        table.add_column(justify="left")
        table.add_column(justify="left")
        table.add_column(justify="left")

        table.add_row(
            f"[bold]Turn:[/bold] {snapshot['turn']}/{snapshot['max_turns']}",
            f"[bold]Time:[/bold] {elapsed_str}",
            f"[{status_style}]{status_icon} {status.upper()}[/{status_style}]",
            ""
        )
        table.add_row(
            f"[bold]Input:[/bold] {input_str}",
            f"[bold]Output:[/bold] {output_str}",
            f"[bold]Cost:[/bold] {cost_str}",
            ""
        )

        return Panel(table, title="Session Details", box=box.ROUNDED, border_style="blue")

    def _build_todo_panel(self) -> Panel:
        """Build todo list panel.

        Shows todos with status indicators (⏸ pending, ▶ in_progress, ✓ completed).

        Returns:
            Rich Panel with todo list
        """
        snapshot = self.state.snapshot()
        todos = snapshot['todos']

        if not todos:
            content = Text("No tasks yet", style="dim")
        else:
            table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
            table.add_column("Status", width=2)
            table.add_column("Task")

            for todo in todos:
                status = todo.get('status', 'pending')
                content = todo.get('content', '')

                if status == 'completed':
                    icon = "✓"
                    style = "green"
                elif status == 'in_progress':
                    icon = "▶"
                    style = "yellow bold"
                else:  # pending
                    icon = "⏸"
                    style = "dim"

                table.add_row(f"[{style}]{icon}[/{style}]", f"[{style}]{content}[/{style}]")

            content = table

        return Panel(content, title="Tasks", box=box.ROUNDED, border_style="green")

    def _build_log_panel(self) -> Panel:
        """Build log streaming panel.

        Shows recent log messages with timestamps.

        Returns:
            Rich Panel with logs
        """
        snapshot = self.state.snapshot()
        logs = snapshot['logs']

        if not logs:
            content = Text("Waiting for logs...", style="dim")
        else:
            # Show last 50 logs (scrollback buffer)
            recent_logs = logs[-50:]
            content = Text("\n".join(recent_logs))

        return Panel(
            content,
            title="Logs",
            box=box.ROUNDED,
            border_style="magenta"
        )

    def _build_input_panel(self) -> Panel:
        """Build prompt input panel.

        Shows instructions for injecting new prompts.

        Returns:
            Rich Panel with input instructions
        """
        help_text = Text()
        help_text.append("Commands: ", style="bold")
        help_text.append("[x] Exit UI  ", style="cyan")
        help_text.append("[h] Help", style="white")

        if self._pending_input:
            status = Text(f"\n✓ {len(self._pending_input)} instruction(s) queued", style="green")
            help_text.append(status)

        return Panel(help_text, title="Controls", box=box.ROUNDED, border_style="white")

    def update_display(self, live: Live) -> None:
        """Update display with current state.

        Args:
            live: Rich Live display instance
        """
        # Throttle updates
        now = time.time()
        if now - self._last_update < self._update_interval:
            return

        self._last_update = now

        # Update layout panels
        self.layout["title"].update(self._build_title_panel())
        self.layout["session"].update(self._build_session_panel())
        self.layout["todos"].update(self._build_todo_panel())
        self.layout["logs"].update(self._build_log_panel())
        self.layout["input"].update(self._build_input_panel())

        # Refresh display
        live.update(self.layout)

    def handle_keyboard_input(self, key: str) -> None:
        """Handle keyboard command input.

        Args:
            key: Key pressed (single character)
        """
        key = key.lower()

        if key == 'x':
            # Exit UI but continue auto mode
            self._should_exit = True
            self.state.add_log("UI exit requested (auto mode continues)")

        elif key == 'h':
            # Show help
            self._showing_help = not self._showing_help
            if self._showing_help:
                self.state.add_log("Help: x=exit ui, h=help")

    def submit_input(self, text: str) -> None:
        """Submit new instruction via input panel.

        Creates timestamped instruction file in append/ directory.

        Args:
            text: Instruction text to inject
        """
        if not text or not text.strip():
            return

        try:
            # Import append handler
            from .append_handler import append_instructions

            result = append_instructions(text)
            self._pending_input.append(text)
            self.state.add_log(f"Instruction queued: {result.filename}")

        except Exception as e:
            self.state.add_log(f"Error submitting instruction: {e}")

    def should_exit(self) -> bool:
        """Check if UI should exit.

        Returns:
            True if exit requested
        """
        return self._should_exit

    def is_showing_help(self) -> bool:
        """Check if help overlay is showing.

        Returns:
            True if showing help
        """
        return self._showing_help

    def has_pending_input(self) -> bool:
        """Check if there is pending input.

        Returns:
            True if input queued
        """
        return len(self._pending_input) > 0

    def get_pending_input(self) -> Optional[str]:
        """Get and clear next pending input.

        Returns:
            Next pending input or None
        """
        if self._pending_input:
            return self._pending_input.popleft()
        return None

    # Methods for test compatibility
    def get_title(self) -> str:
        """Get current title."""
        return self.title

    def get_session_details(self) -> str:
        """Get session details as text."""
        panel = self._build_session_panel()
        # Extract text representation for tests
        return str(panel)

    def get_todo_display(self) -> str:
        """Get todo display as text."""
        panel = self._build_todo_panel()
        return str(panel)

    def get_log_content(self) -> str:
        """Get log content as text."""
        snapshot = self.state.snapshot()
        return "\n".join(snapshot['logs'])

    def update_todos(self, todos: List[Dict[str, str]]) -> None:
        """Update todo list in state."""
        self.state.update_todos(todos)

    def append_log(self, message: str) -> None:
        """Append log message to state."""
        self.state.add_log(message)

    def get_input_placeholder(self) -> str:
        """Get input placeholder text."""
        return "Type new instructions..."

    def set_input_text(self, text: str) -> None:
        """Set input text (for tests)."""
        self._pending_input.append(text)

    def get_cost_info(self) -> Optional[Dict]:
        """Get cost info from state."""
        costs = self.state.get_costs()
        return costs if costs else None

    def _append_to_buffer(self, message: str) -> None:
        """Internal method to append to buffer (for test mocking)."""
        self.state.add_log(message)

    def _keyboard_listener_thread(self):
        """Background thread to capture keyboard input without blocking.

        Runs in daemon mode and listens for single-character commands.
        Uses non-blocking stdin reading to avoid interfering with main thread.
        """
        # Configure terminal for non-blocking, non-canonical mode
        # This allows reading single characters without Enter
        import termios
        import tty

        # Save original terminal settings
        old_settings = None
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            # Set terminal to raw mode (no echo, no line buffering)
            tty.setcbreak(sys.stdin.fileno())

            while not self._should_exit:
                # Check if input is available (non-blocking)
                if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    if key:
                        self.handle_keyboard_input(key)

        except Exception as e:
            # Log error but don't crash the thread
            self.state.add_log(f"Keyboard listener error: {e}")
        finally:
            # Restore original terminal settings
            if old_settings is not None:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except Exception:
                    pass

    def run(self, update_interval: float = 0.1) -> None:
        """Main run loop - displays UI and handles keyboard input.

        This is the main entry point for the UI. It:
        1. Starts keyboard listener thread
        2. Creates Rich Live context
        3. Continuously updates display until exit requested

        Args:
            update_interval: Time between display updates in seconds (default 0.1)
        """
        # Start keyboard listener in background thread
        keyboard_thread = threading.Thread(
            target=self._keyboard_listener_thread,
            daemon=True,
            name="KeyboardListener"
        )
        keyboard_thread.start()

        # Create Live display context and run update loop
        try:
            with Live(
                self.layout,
                console=self.console,
                screen=True,
                refresh_per_second=10
            ) as live:
                # Initial display
                self.update_display(live)

                # Main update loop
                while not self._should_exit:
                    # Update display with current state
                    self.update_display(live)

                    # Check if auto mode execution is complete
                    status = self.state.get_status()
                    if status in ["completed", "error", "stopped"]:
                        # Give user a moment to see final state
                        time.sleep(2)
                        break

                    # Sleep before next update
                    time.sleep(update_interval)

        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            self.state.add_log("UI interrupted by user (Ctrl+C)")
            self._should_exit = True
        finally:
            # Wait for keyboard thread to finish
            keyboard_thread.join(timeout=1.0)
