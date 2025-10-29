"""Rich CLI user interface for auto mode interactive display.

This module provides a full-screen terminal UI using the Rich library,
displaying auto mode execution state with 5 main panels:
- Title (generated from prompt)
- Session details (turn, time, costs)
- Todo list
- Log streaming area
- Prompt input area
"""

import sys
import time
import threading
import select
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any, Deque, Dict, List, Optional

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box

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

        Uses Claude SDK to generate concise title, falls back to truncation.

        Args:
            prompt: User's original prompt

        Returns:
            Title string (max 80 chars)
        """
        if not prompt or not prompt.strip():
            return "Auto Mode Session"

        # Try to use SDK to generate title
        try:
            # Try to import Claude SDK
            try:
                from claude_agent_sdk import query_sync, ClaudeAgentOptions
                SDK_AVAILABLE = True
            except ImportError:
                SDK_AVAILABLE = False

            if SDK_AVAILABLE:
                # Use SDK to generate concise title
                title_prompt = f"""Generate a concise, descriptive title (max 80 characters) for this auto mode session.
The title should capture the key objective in a clear, brief phrase.

User prompt: {prompt[:500]}

Respond with ONLY the title text, nothing else."""

                options = ClaudeAgentOptions(
                    cwd=str(self.working_dir),
                    permission_mode="bypassPermissions"
                )

                # Use synchronous query for title generation (fast, non-streaming)
                response = query_sync(prompt=title_prompt, options=options)

                # Extract text from response
                if hasattr(response, 'content'):
                    for block in response.content:
                        if hasattr(block, 'text'):
                            title = block.text.strip()
                            # Truncate to 80 chars if needed
                            if len(title) > 80:
                                title = title[:77] + "..."
                            return title
        except Exception as e:
            # Log error but don't crash - fall back to simple truncation
            self.state.add_log(f"Title generation via SDK failed: {e}", timestamp=False)

        # Fallback: Simple truncation
        if len(prompt) <= 80:
            return prompt

        return prompt[:77] + "..."

    def _create_layout(self) -> Layout:
        """Create Rich layout structure.

        Returns:
            Configured Layout instance with 5 areas
        """
        layout = Layout()

        # Split into 5 rows
        layout.split(
            Layout(name="title", size=3),
            Layout(name="session", size=8),  # Increased for additional fields
            Layout(name="todos", size=10),
            Layout(name="logs", ratio=1),
            Layout(name="status", size=3),  # Renamed from input
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

        Shows session_id, datetime, objective summary, turn counter, elapsed time, and cost tracking.

        Returns:
            Rich Panel with session info
        """
        snapshot = self.state.snapshot()

        # Format datetime (session start time)
        start_time = snapshot['start_time']
        if start_time > 0:
            datetime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
        else:
            datetime_str = "Unknown"

        # Format elapsed time
        if start_time > 0:
            elapsed_sec = time.time() - start_time
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

        # Format objective summary (first 50 chars)
        objective = snapshot.get('objective', '')
        if objective:
            objective_summary = objective[:50] + "..." if len(objective) > 50 else objective
        else:
            objective_summary = "N/A"

        # Format costs
        costs = snapshot['costs']
        input_tokens = costs.get('input_tokens', 0)
        output_tokens = costs.get('output_tokens', 0)
        estimated_cost = costs.get('estimated_cost', 0.0)

        # Format numbers with commas
        input_str = f"{input_tokens:,}" if input_tokens else "0"
        output_str = f"{output_tokens:,}" if output_tokens else "0"
        cost_str = f"${estimated_cost:.4f}" if estimated_cost else "$0.0000"

        # Session ID (truncate if too long)
        session_id = snapshot.get('session_id', 'unknown')
        if len(session_id) > 30:
            session_id = session_id[:27] + "..."

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
        elif status == "paused":
            status_icon = "⏸"
            status_style = "yellow"
        else:
            status_icon = "◆"
            status_style = "white"

        # Build table
        table = Table.grid(padding=(0, 1))
        table.add_column(justify="left")
        table.add_column(justify="left")

        table.add_row(
            f"[bold]Session:[/bold] {session_id}",
            f"[bold]Started:[/bold] {datetime_str}"
        )
        table.add_row(
            f"[bold]Objective:[/bold] {objective_summary}",
            ""
        )
        table.add_row(
            f"[bold]Turn:[/bold] {snapshot['turn']}/{snapshot['max_turns']}",
            f"[bold]Elapsed:[/bold] {elapsed_str}"
        )
        table.add_row(
            f"[bold]Tokens:[/bold] In:{input_str} Out:{output_str}",
            f"[bold]Cost:[/bold] {cost_str}"
        )
        table.add_row(
            f"[{status_style}]{status_icon} Status: {status.upper()}[/{status_style}]",
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

    def _render_status(self) -> Panel:
        """Build status bar with system info and keyboard commands.

        Shows git commit revision, Claude CLI version, and keyboard shortcuts.

        Returns:
            Rich Panel with status information
        """
        import subprocess

        # Get git commit revision (short hash)
        try:
            git_rev = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self.working_dir,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            git_info = f"Git: {git_rev}"
        except Exception:
            git_info = "Git: N/A"

        # Get Claude CLI version
        try:
            # Try to get version from package or CLI
            claude_version = subprocess.check_output(
                ["claude", "--version"],
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            # Extract just version number if present
            if "version" in claude_version.lower():
                claude_version = claude_version.split()[-1]
            version_info = f"Claude: {claude_version}"
        except Exception:
            version_info = "Claude: N/A"

        # Build status text with keyboard commands
        status_text = Text()
        status_text.append(f"{git_info}  |  {version_info}  |  ", style="dim")
        status_text.append("Commands: ", style="bold")

        # Show available commands based on current state
        snapshot = self.state.snapshot()
        status = snapshot['status']

        if status == "running":
            status_text.append("[p]", style="cyan bold")
            status_text.append("=pause  ", style="white")
        elif status == "paused":
            status_text.append("[p]", style="cyan bold")
            status_text.append("=resume  ", style="white")

        if status in ["running", "paused"]:
            status_text.append("[k]", style="red bold")
            status_text.append("=kill  ", style="white")

        status_text.append("[x]", style="yellow bold")
        status_text.append("=exit", style="white")

        return Panel(status_text, box=box.ROUNDED, border_style="white")

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
        self.layout["status"].update(self._render_status())

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

        elif key == 'p':
            # Toggle pause
            if self.state.is_pause_requested():
                self.state.clear_pause_request()
                self.state.add_log("Resume requested")
            else:
                self.state.request_pause()
                self.state.add_log("Pause requested")

        elif key == 'k':
            # Kill execution
            self.state.request_kill()
            self.state.add_log("Kill requested - terminating execution")

        elif key == 'h':
            # Show help
            self._showing_help = not self._showing_help
            if self._showing_help:
                self.state.add_log("Help: p=pause/resume, k=kill, x=exit ui, h=help")

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

    def register_todo_callback(self) -> None:
        """Register SDK callback to auto-update todos when TodoWrite tool is used.

        This should be called after SDK is initialized to hook into tool usage events.
        Note: Implementation depends on SDK's callback mechanism.
        """
        # TODO: SDK callback registration for TodoWrite tool
        # This will be implemented when SDK provides the callback mechanism
        # For now, todos are updated via direct calls from auto_mode.py
        pass

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
        import tty
        import termios

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
