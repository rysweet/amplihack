# Auto Mode Interactive UI - Architecture Specification

## Module: auto_mode_state.py

### Purpose

Thread-safe shared state container for communication between auto mode execution thread and UI thread.

### Contract

**Inputs**: Updates from auto mode thread (logs, todos, costs, status)
**Outputs**: Snapshots for UI rendering (thread-safe reads)
**Side Effects**: None (pure state container)

### Class: AutoModeState

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from threading import Lock
from enum import Enum
from collections import deque

class ExecutionStatus(Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    KILLED = "killed"

@dataclass
class TodoItem:
    content: str
    status: str  # "pending", "in_progress", "completed"
    activeForm: str

@dataclass
class SessionInfo:
    session_title: Optional[str] = None
    total_cost: float = 0.0
    message_count: int = 0
    start_time: Optional[float] = None
    current_prompt: Optional[str] = None

class AutoModeState:
    """Thread-safe state container for auto mode execution."""

    def __init__(self, max_log_lines: int = 1000):
        self._lock = Lock()

        # Execution state
        self.status: ExecutionStatus = ExecutionStatus.INITIALIZING
        self.error_message: Optional[str] = None

        # Session info
        self.session_info = SessionInfo()

        # Logs (circular buffer)
        self.logs: deque = deque(maxlen=max_log_lines)

        # Todos
        self.todos: List[TodoItem] = []

        # User commands
        self.pause_requested: bool = False
        self.kill_requested: bool = False
        self.exit_ui_requested: bool = False

    def append_log(self, log_line: str) -> None:
        """Thread-safe log append."""
        with self._lock:
            self.logs.append(log_line)

    def update_todos(self, todos: List[Dict[str, Any]]) -> None:
        """Thread-safe todo update."""
        with self._lock:
            self.todos = [
                TodoItem(
                    content=t.get("content", ""),
                    status=t.get("status", "pending"),
                    activeForm=t.get("activeForm", t.get("content", ""))
                )
                for t in todos
            ]

    def update_session_info(self, **kwargs) -> None:
        """Thread-safe session info update."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.session_info, key):
                    setattr(self.session_info, key, value)

    def set_status(self, status: ExecutionStatus, error: Optional[str] = None) -> None:
        """Thread-safe status update."""
        with self._lock:
            self.status = status
            if error:
                self.error_message = error

    def get_snapshot(self) -> Dict[str, Any]:
        """Get thread-safe snapshot of current state for UI rendering."""
        with self._lock:
            return {
                "status": self.status,
                "error_message": self.error_message,
                "session_info": {
                    "session_title": self.session_info.session_title,
                    "total_cost": self.session_info.total_cost,
                    "message_count": self.session_info.message_count,
                    "start_time": self.session_info.start_time,
                    "current_prompt": self.session_info.current_prompt,
                },
                "logs": list(self.logs),  # Copy
                "todos": [
                    {"content": t.content, "status": t.status, "activeForm": t.activeForm}
                    for t in self.todos
                ],
                "pause_requested": self.pause_requested,
                "kill_requested": self.kill_requested,
                "exit_ui_requested": self.exit_ui_requested,
            }

    def request_pause(self) -> None:
        """User requested pause."""
        with self._lock:
            self.pause_requested = not self.pause_requested

    def request_kill(self) -> None:
        """User requested kill."""
        with self._lock:
            self.kill_requested = True

    def request_exit_ui(self) -> None:
        """User requested UI exit (auto mode continues)."""
        with self._lock:
            self.exit_ui_requested = True

    def is_kill_requested(self) -> bool:
        """Check if kill was requested."""
        with self._lock:
            return self.kill_requested

    def is_pause_requested(self) -> bool:
        """Check if currently paused."""
        with self._lock:
            return self.pause_requested

    def is_exit_ui_requested(self) -> bool:
        """Check if UI exit was requested."""
        with self._lock:
            return self.exit_ui_requested
```

### Dependencies

- Python threading (stdlib)
- dataclasses (stdlib)
- collections.deque (stdlib)

### Implementation Notes

- Use `deque(maxlen=N)` for automatic log rotation
- Lock granularity: one lock for entire state (simplicity over performance)
- Snapshots create copies to prevent UI from holding locks during rendering

### Test Requirements

- Concurrent reads/writes from multiple threads
- Log rotation at max size
- State consistency under load

---

## Module: auto_mode_coordinator.py

### Purpose

Coordinate auto mode execution thread with UI thread. Handle threading lifecycle and communication.

### Contract

**Inputs**: Auto mode configuration, prompts, state object
**Outputs**: Execution results, exit codes
**Side Effects**: Spawns background thread, modifies shared state

### Class: AutoModeCoordinator

```python
import threading
from typing import Callable, Optional, List, Any
from .auto_mode_state import AutoModeState, ExecutionStatus
import logging

logger = logging.getLogger(__name__)

class AutoModeCoordinator:
    """Coordinates auto mode execution in background thread."""

    def __init__(
        self,
        state: AutoModeState,
        auto_mode_func: Callable,
        prompts: List[str],
        append_mode: bool = False,
        **auto_mode_kwargs
    ):
        """
        Args:
            state: Shared state object
            auto_mode_func: The actual auto mode execution function
            prompts: List of prompts to execute
            append_mode: Whether --append was used
            **auto_mode_kwargs: Additional args for auto_mode_func
        """
        self.state = state
        self.auto_mode_func = auto_mode_func
        self.prompts = prompts
        self.append_mode = append_mode
        self.auto_mode_kwargs = auto_mode_kwargs

        self.thread: Optional[threading.Thread] = None
        self.exception: Optional[Exception] = None

    def start(self) -> None:
        """Start auto mode execution in background thread."""
        self.state.set_status(ExecutionStatus.RUNNING)
        self.thread = threading.Thread(
            target=self._run_auto_mode,
            daemon=False,  # We want to wait for completion
            name="auto-mode-execution"
        )
        self.thread.start()
        logger.info("Auto mode execution thread started")

    def _run_auto_mode(self) -> None:
        """Execute auto mode in background thread."""
        try:
            logger.info("Starting auto mode execution")

            # Wrap auto mode function with state updates
            result = self._execute_with_state_updates()

            self.state.set_status(ExecutionStatus.COMPLETED)
            logger.info("Auto mode execution completed successfully")

        except Exception as e:
            self.exception = e
            self.state.set_status(ExecutionStatus.ERROR, str(e))
            logger.error(f"Auto mode execution failed: {e}", exc_info=True)

    def _execute_with_state_updates(self) -> Any:
        """
        Execute auto mode with hooks to update state.
        This is where we intercept SDK callbacks.
        """
        # This will be implemented to wrap the auto mode function
        # and inject state updates via SDK callbacks

        # Key integration points:
        # 1. Intercept streaming output → append_log
        # 2. Intercept todo updates → update_todos
        # 3. Track message costs → update_session_info
        # 4. Generate title on first message → update_session_info
        # 5. Check kill/pause flags periodically

        return self.auto_mode_func(
            prompts=self.prompts,
            state=self.state,  # Pass state for callbacks
            **self.auto_mode_kwargs
        )

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for auto mode thread to complete.

        Args:
            timeout: Maximum time to wait (None = wait forever)

        Returns:
            True if completed, False if timeout
        """
        if self.thread is None:
            return False

        self.thread.join(timeout=timeout)
        return not self.thread.is_alive()

    def is_alive(self) -> bool:
        """Check if execution thread is still running."""
        return self.thread is not None and self.thread.is_alive()
```

### Dependencies

- threading (stdlib)
- logging (stdlib)
- auto_mode_state module

### Implementation Notes

- Daemon=False ensures thread completes even if UI exits
- Exception handling captures errors for UI display
- State updates happen via callbacks injected into SDK

### Test Requirements

- Thread starts and completes successfully
- Exceptions are captured and stored
- Kill/pause signals are respected

---

## Module: auto_mode_ui.py

### Purpose

Rich TUI implementation with 5 areas, keyboard input, live updates.

### Contract

**Inputs**: AutoModeState object, refresh rate
**Outputs**: Visual UI, exit code
**Side Effects**: Terminal rendering, keyboard capture

### Class: AutoModeUI

```python
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich import box
from rich.align import Align
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
import time
import sys
from typing import Optional
from .auto_mode_state import AutoModeState, ExecutionStatus

class AutoModeUI:
    """Rich TUI for auto mode monitoring and control."""

    def __init__(self, state: AutoModeState, refresh_rate: float = 0.1):
        """
        Args:
            state: Shared state object
            refresh_rate: UI refresh interval in seconds
        """
        self.state = state
        self.refresh_rate = refresh_rate
        self.console = Console()

        # UI state
        self.log_scroll_offset = 0  # For arrow key scrolling
        self.running = True

    def run(self) -> int:
        """
        Run the UI loop until exit.

        Returns:
            Exit code (0 = success, 1 = error)
        """
        # Setup keyboard bindings
        kb = self._create_key_bindings()

        try:
            with Live(
                self._create_layout(),
                console=self.console,
                refresh_per_second=int(1 / self.refresh_rate),
                screen=True
            ) as live:
                while self.running:
                    # Update layout with current state
                    live.update(self._create_layout())

                    # Check for exit conditions
                    if self.state.is_exit_ui_requested():
                        self.console.print("\n[yellow]Exiting UI, auto mode continues...[/yellow]")
                        return 0

                    snapshot = self.state.get_snapshot()
                    if snapshot["status"] in [ExecutionStatus.COMPLETED, ExecutionStatus.ERROR, ExecutionStatus.KILLED]:
                        # Auto mode finished, wait a moment for user to see
                        time.sleep(2)
                        return 0 if snapshot["status"] == ExecutionStatus.COMPLETED else 1

                    time.sleep(self.refresh_rate)

        except KeyboardInterrupt:
            self.console.print("\n[yellow]UI interrupted[/yellow]")
            return 130

        except Exception as e:
            self.console.print(f"\n[red]UI Error: {e}[/red]")
            return 1

    def _create_layout(self) -> Layout:
        """Create the 5-area layout."""
        snapshot = self.state.get_snapshot()

        layout = Layout()

        # Split into main areas
        layout.split_column(
            Layout(name="title", size=3),
            Layout(name="session", size=5),
            Layout(name="todos", size=12),
            Layout(name="logs", ratio=1),  # Takes remaining space
            Layout(name="status", size=3),
        )

        # Populate areas
        layout["title"].update(self._render_title(snapshot))
        layout["session"].update(self._render_session(snapshot))
        layout["todos"].update(self._render_todos(snapshot))
        layout["logs"].update(self._render_logs(snapshot))
        layout["status"].update(self._render_status(snapshot))

        return layout

    def _render_title(self, snapshot: dict) -> Panel:
        """Render title area."""
        session_title = snapshot["session_info"].get("session_title", "Generating title...")
        status = snapshot["status"]

        # Status indicator
        status_colors = {
            ExecutionStatus.INITIALIZING: "yellow",
            ExecutionStatus.RUNNING: "green",
            ExecutionStatus.PAUSED: "yellow",
            ExecutionStatus.COMPLETED: "blue",
            ExecutionStatus.ERROR: "red",
            ExecutionStatus.KILLED: "red",
        }

        status_text = Text()
        status_text.append("● ", style=status_colors.get(status, "white"))
        status_text.append(status.value.upper())

        title_text = Text.assemble(
            (session_title, "bold cyan"),
            " ",
            status_text
        )

        return Panel(
            Align.center(title_text),
            border_style="cyan",
            box=box.ROUNDED
        )

    def _render_session(self, snapshot: dict) -> Panel:
        """Render session details area."""
        info = snapshot["session_info"]

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold")
        table.add_column()

        table.add_row("Messages:", str(info.get("message_count", 0)))
        table.add_row("Total Cost:", f"${info.get('total_cost', 0.0):.4f}")

        if info.get("start_time"):
            elapsed = time.time() - info["start_time"]
            table.add_row("Elapsed:", f"{int(elapsed // 60)}m {int(elapsed % 60)}s")

        if info.get("current_prompt"):
            prompt_preview = info["current_prompt"][:50] + "..." if len(info["current_prompt"]) > 50 else info["current_prompt"]
            table.add_row("Current:", prompt_preview)

        return Panel(
            table,
            title="[bold]Session Details[/bold]",
            border_style="blue",
            box=box.ROUNDED
        )

    def _render_todos(self, snapshot: dict) -> Panel:
        """Render todos area."""
        todos = snapshot["todos"]

        if not todos:
            content = Text("No todos yet...", style="dim")
        else:
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column(width=2)
            table.add_column(ratio=1)

            for todo in todos:
                status = todo["status"]
                content_text = todo.get("activeForm" if status == "in_progress" else "content", todo["content"])

                # Status icons
                if status == "completed":
                    icon = "[green]✓[/green]"
                elif status == "in_progress":
                    icon = "[yellow]►[/yellow]"
                else:
                    icon = "[dim]○[/dim]"

                table.add_row(icon, content_text)

            content = table

        return Panel(
            content,
            title="[bold]Tasks[/bold]",
            border_style="green",
            box=box.ROUNDED
        )

    def _render_logs(self, snapshot: dict) -> Panel:
        """Render logs area with scrolling."""
        logs = snapshot["logs"]

        if not logs:
            content = Text("Waiting for output...", style="dim")
        else:
            # Apply scroll offset
            visible_logs = logs[self.log_scroll_offset:]

            # Limit to reasonable number for rendering
            visible_logs = visible_logs[-100:]  # Last 100 lines

            log_text = Text("\n".join(visible_logs))
            content = log_text

        title = "[bold]Logs[/bold]"
        if self.log_scroll_offset > 0:
            title += f" (scrolled up {self.log_scroll_offset})"

        return Panel(
            content,
            title=title,
            border_style="white",
            box=box.ROUNDED
        )

    def _render_status(self, snapshot: dict) -> Panel:
        """Render status bar with keyboard commands."""
        status = snapshot["status"]

        commands = []

        if status == ExecutionStatus.RUNNING:
            commands.append("[bold cyan]p[/bold cyan]=pause")
        elif status == ExecutionStatus.PAUSED:
            commands.append("[bold cyan]p[/bold cyan]=resume")

        if status in [ExecutionStatus.RUNNING, ExecutionStatus.PAUSED]:
            commands.append("[bold red]k[/bold red]=kill")

        commands.append("[bold yellow]x[/bold yellow]=exit UI")
        commands.append("[bold]↑↓[/bold]=scroll logs")

        command_text = "  |  ".join(commands)

        return Panel(
            Align.center(command_text),
            border_style="yellow",
            box=box.ROUNDED
        )

    def _create_key_bindings(self) -> KeyBindings:
        """Create keyboard bindings."""
        kb = KeyBindings()

        @kb.add('x')
        def exit_ui(event):
            self.state.request_exit_ui()

        @kb.add('p')
        def toggle_pause(event):
            self.state.request_pause()

        @kb.add('k')
        def kill_execution(event):
            self.state.request_kill()

        @kb.add('up')
        def scroll_up(event):
            self.log_scroll_offset = max(0, self.log_scroll_offset - 5)

        @kb.add('down')
        def scroll_down(event):
            snapshot = self.state.get_snapshot()
            max_offset = max(0, len(snapshot["logs"]) - 50)
            self.log_scroll_offset = min(max_offset, self.log_scroll_offset + 5)

        @kb.add('c-c')
        def interrupt(event):
            self.running = False

        return kb
```

### Dependencies

- rich (layout, panels, live display)
- prompt_toolkit (keyboard input)
- time, sys (stdlib)

### Implementation Notes

- `Live` context manager handles terminal rendering
- Keyboard bindings use prompt_toolkit for non-blocking input
- Log scrolling uses offset into deque
- Refresh rate balances responsiveness vs CPU usage

### Test Requirements

- Layout renders correctly
- Keyboard commands trigger state changes
- UI handles state updates gracefully
- Scrolling works correctly

---

## Module: auto_mode.py (Modifications)

### Purpose

Integrate UI coordinator with existing auto mode implementation.

### Changes Required

#### 1. Add UI Entry Point

```python
def run_auto_mode_with_ui(
    prompts: List[str],
    append_mode: bool = False,
    **auto_mode_kwargs
) -> int:
    """
    Run auto mode with interactive UI.

    This is the new entry point when UI is enabled.
    """
    from .auto_mode_state import AutoModeState
    from .auto_mode_coordinator import AutoModeCoordinator
    from .auto_mode_ui import AutoModeUI
    import time

    # Create shared state
    state = AutoModeState()
    state.update_session_info(start_time=time.time())

    # Create coordinator
    coordinator = AutoModeCoordinator(
        state=state,
        auto_mode_func=run_auto_mode_execution,  # Wrapped version
        prompts=prompts,
        append_mode=append_mode,
        **auto_mode_kwargs
    )

    # Start execution in background
    coordinator.start()

    # Run UI in foreground
    ui = AutoModeUI(state=state)
    exit_code = ui.run()

    # If UI exited but execution still running, wait for completion
    if coordinator.is_alive():
        print("Auto mode continues in background...")
        coordinator.wait_for_completion()

    return exit_code
```

#### 2. Wrap Execution Function

```python
def run_auto_mode_execution(
    prompts: List[str],
    state: Optional[AutoModeState] = None,
    **kwargs
) -> Any:
    """
    Execute auto mode with optional state updates.

    This wraps the existing auto mode logic to inject state updates.
    """

    # Create SDK client with callbacks if state provided
    if state:
        # Inject streaming callback
        original_stream_handler = kwargs.get("stream_handler")

        def wrapped_stream_handler(chunk):
            # Update state with streaming output
            state.append_log(chunk)

            # Call original handler if exists
            if original_stream_handler:
                original_stream_handler(chunk)

        kwargs["stream_handler"] = wrapped_stream_handler

        # Inject todo callback
        original_todo_handler = kwargs.get("todo_handler")

        def wrapped_todo_handler(todos):
            state.update_todos(todos)
            if original_todo_handler:
                original_todo_handler(todos)

        kwargs["todo_handler"] = wrapped_todo_handler

        # Inject cost tracking
        original_message_handler = kwargs.get("message_handler")

        def wrapped_message_handler(message_data):
            # Extract cost and update
            cost = message_data.get("usage", {}).get("total_cost", 0)
            state.update_session_info(
                total_cost=state.session_info.total_cost + cost,
                message_count=state.session_info.message_count + 1
            )

            # Generate title on first message if needed
            if state.session_info.message_count == 1 and not state.session_info.session_title:
                title = generate_session_title(message_data)
                state.update_session_info(session_title=title)

            if original_message_handler:
                original_message_handler(message_data)

        kwargs["message_handler"] = wrapped_message_handler

    # Execute existing auto mode logic
    return _run_auto_mode_impl(prompts=prompts, **kwargs)
```

#### 3. Add CLI Flag

```python
# In CLI argument parsing
parser.add_argument(
    "--ui",
    action="store_true",
    help="Enable interactive UI for auto mode monitoring"
)

# In main execution logic
if args.auto_mode:
    if args.ui:
        return run_auto_mode_with_ui(
            prompts=prompts,
            append_mode=args.append,
            # ... other args
        )
    else:
        return run_auto_mode(prompts=prompts, append_mode=args.append)
```

### Dependencies

- New state/coordinator/ui modules
- Existing auto mode implementation

### Implementation Notes

- Minimal changes to existing auto mode logic
- Callbacks wrap existing handlers (composition pattern)
- CLI flag provides opt-in behavior

---

## Integration Points

### SDK Integration

#### 1. Title Generation

```python
def generate_session_title(first_message_data: dict) -> str:
    """
    Generate concise session title from first user message.

    Uses Claude Agent SDK with specific prompt.
    """
    prompt = first_message_data.get("content", "")[:500]  # First 500 chars

    # Call SDK with title generation prompt
    response = sdk_client.generate_title(prompt)

    return response.strip()[:80]  # Max 80 chars
```

#### 2. Cost Tracking

```python
# Extract from SDK response
usage = response.get("usage", {})
input_tokens = usage.get("input_tokens", 0)
output_tokens = usage.get("output_tokens", 0)

# Calculate cost (model-specific rates)
cost = calculate_cost(input_tokens, output_tokens, model_name)

# Update state
state.update_session_info(total_cost=state.session_info.total_cost + cost)
```

#### 3. Todo Tracking

```python
# SDK callback for todo updates
def on_todo_update(todos: List[dict]):
    state.update_todos(todos)

# Register callback
sdk_client.on("todo_update", on_todo_update)
```

#### 4. Streaming Output

```python
# SDK callback for streaming chunks
def on_stream_chunk(chunk: str):
    state.append_log(chunk)

# Register callback
sdk_client.on("stream_chunk", on_stream_chunk)
```

---

## Threading Model

### Thread Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Main Thread                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. Parse CLI args                                   │   │
│  │  2. Create AutoModeState (shared)                    │   │
│  │  3. Create AutoModeCoordinator                       │   │
│  │  4. coordinator.start() → spawns execution thread    │   │
│  │  5. Create AutoModeUI                                │   │
│  │  6. ui.run() → blocks on UI loop                     │   │
│  │  7. On UI exit: wait for execution or detach         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ spawns
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   Execution Thread                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. Execute auto mode logic                          │   │
│  │  2. SDK calls (blocking)                             │   │
│  │  3. Callbacks update state:                          │   │
│  │     - append_log(chunk)                              │   │
│  │     - update_todos(todos)                            │   │
│  │     - update_session_info(cost=...)                  │   │
│  │  4. Check state.is_kill_requested() periodically     │   │
│  │  5. On completion: set_status(COMPLETED)             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ updates
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    AutoModeState                            │
│                   (Thread-Safe)                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Lock-protected shared state:                        │   │
│  │  - status: ExecutionStatus                           │   │
│  │  - logs: deque (circular buffer)                     │   │
│  │  - todos: List[TodoItem]                             │   │
│  │  - session_info: SessionInfo                         │   │
│  │  - pause_requested: bool                             │   │
│  │  - kill_requested: bool                              │   │
│  │  - exit_ui_requested: bool                           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ reads
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                      UI Loop                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  while running:                                      │   │
│  │    1. snapshot = state.get_snapshot()                │   │
│  │    2. render_layout(snapshot)                        │   │
│  │    3. Check keyboard input (non-blocking)            │   │
│  │       - 'x' → state.request_exit_ui()                │   │
│  │       - 'p' → state.request_pause()                  │   │
│  │       - 'k' → state.request_kill()                   │   │
│  │    4. sleep(refresh_rate)                            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Communication Patterns

#### Execution → State → UI (One-way data flow)

```
Execution Thread          AutoModeState              UI Thread
     │                         │                         │
     │─append_log()──────────→│                         │
     │                         │                         │
     │                         │←──get_snapshot()────────│
     │                         │                         │
     │                         │──returns copy──────────→│
     │                         │                         │
     │─update_todos()────────→│                         │
     │                         │                         │
     │                         │←──get_snapshot()────────│
     │                         │──returns copy──────────→│
```

#### UI → State → Execution (Command flow)

```
UI Thread                 AutoModeState          Execution Thread
     │                         │                         │
     │──request_kill()───────→│                         │
     │                         │                         │
     │                         │←──is_kill_requested()───│
     │                         │──returns True──────────→│
     │                         │                         │
     │                         │                    [exits loop]
```

### Synchronization Guarantees

1. **Lock Scope**: Single lock for entire state (simple, prevents deadlock)
2. **Snapshot Pattern**: UI gets copy of state, never holds lock during render
3. **Non-blocking UI**: Keyboard input handled via prompt_toolkit (non-blocking)
4. **Graceful Degradation**: UI crash doesn't affect execution thread

---

## State Management

### State Lifecycle

```
INITIALIZING
     │
     ↓ (coordinator.start())
RUNNING
     │
     ├─→ (user presses 'p') → PAUSED
     │                           │
     │                           ↓ (user presses 'p')
     │   ←───────────────────────┘
     │
     ├─→ (user presses 'k') → KILLED
     │
     ├─→ (exception) → ERROR
     │
     ↓ (completion)
COMPLETED
```

### Pause/Resume Mechanism

```python
# In execution loop (pseudo-code)
for prompt in prompts:
    # Check pause state
    while state.is_pause_requested():
        time.sleep(0.1)  # Sleep while paused

        # Check if kill requested while paused
        if state.is_kill_requested():
            break

    # Check kill state
    if state.is_kill_requested():
        break

    # Execute prompt
    execute_prompt(prompt)
```

### Exit Without Killing

```python
# When user presses 'x'
state.request_exit_ui()

# UI loop checks
if state.is_exit_ui_requested():
    print("Exiting UI, auto mode continues...")
    return 0  # Exit UI

# Main thread after UI exits
if coordinator.is_alive():
    print("Auto mode running in background...")
    # Option 1: Wait for completion
    coordinator.wait_for_completion()

    # Option 2: Detach (not in v1)
    # sys.exit(0)
```

---

## Error Handling

### Error Scenarios

#### 1. UI Crashes, Execution Continues

```python
# In main thread
try:
    ui = AutoModeUI(state=state)
    exit_code = ui.run()
except Exception as e:
    logger.error(f"UI crashed: {e}")
    print("UI crashed, but auto mode continues...")

    # Wait for execution to complete
    coordinator.wait_for_completion()

    # Check final status
    snapshot = state.get_snapshot()
    if snapshot["status"] == ExecutionStatus.COMPLETED:
        return 0
    else:
        return 1
```

#### 2. Execution Crashes, UI Shows Error

```python
# In execution thread
try:
    execute_auto_mode()
except Exception as e:
    state.set_status(ExecutionStatus.ERROR, str(e))
    state.append_log(f"ERROR: {e}")
    raise

# UI renders error
def _render_title(self, snapshot: dict) -> Panel:
    if snapshot["status"] == ExecutionStatus.ERROR:
        error_msg = snapshot["error_message"]
        return Panel(
            f"[red bold]ERROR: {error_msg}[/red bold]",
            border_style="red"
        )
```

#### 3. SDK Failures, Graceful Degradation

```python
# Title generation fails
try:
    title = generate_session_title(first_message)
    state.update_session_info(session_title=title)
except Exception as e:
    logger.warning(f"Title generation failed: {e}")
    state.update_session_info(session_title="Auto Mode Session")

# Cost tracking fails
try:
    cost = calculate_cost(usage)
    state.update_session_info(total_cost=state.session_info.total_cost + cost)
except Exception as e:
    logger.warning(f"Cost calculation failed: {e}")
    # Continue without cost update
```

---

## Sequence Diagrams

### Startup Sequence

```
User         CLI        Main        Coordinator    Execution    UI         State
 │            │          │               │            │          │           │
 │──auto ────→│          │               │            │          │           │
 │   --ui     │          │               │            │          │           │
 │            │          │               │            │          │           │
 │            │──parse──→│               │            │          │           │
 │            │          │               │            │          │           │
 │            │          │──create──────────────────────────────────────────→│
 │            │          │               │            │          │           │
 │            │          │──create──────→│            │          │           │
 │            │          │               │            │          │           │
 │            │          │──start()─────→│            │          │           │
 │            │          │               │            │          │           │
 │            │          │               │──spawn────→│          │           │
 │            │          │               │            │          │           │
 │            │          │               │            │──update→│           │
 │            │          │               │            │  status  │           │
 │            │          │               │            │          │           │
 │            │          │──create────────────────────────────→│           │
 │            │          │               │            │          │           │
 │            │          │──run()────────────────────────────→│           │
 │            │          │               │            │          │           │
 │            │          │               │            │          │──render──→│
 │            │          │               │            │←─log────│           │
 │            │          │               │            │          │           │
 │            │          │               │            │          │←─snapshot─│
 │            │          │               │            │          │           │
```

### User Command Sequence (Pause)

```
User         UI         State       Execution
 │            │           │              │
 │──press p──→│           │              │
 │            │           │              │
 │            │──request_│              │
 │            │   pause()→│              │
 │            │           │              │
 │            │           │←─is_pause_   │
 │            │           │  requested() │
 │            │           │              │
 │            │           │──True───────→│
 │            │           │              │
 │            │           │         [pauses]
 │            │           │              │
 │──press p──→│           │              │
 │            │           │              │
 │            │──request_│              │
 │            │   pause()→│              │
 │            │       (toggle)           │
 │            │           │              │
 │            │           │←─is_pause_   │
 │            │           │  requested() │
 │            │           │              │
 │            │           │──False──────→│
 │            │           │              │
 │            │           │         [resumes]
```

### User Command Sequence (Kill)

```
User         UI         State       Execution      Main
 │            │           │              │           │
 │──press k──→│           │              │           │
 │            │           │              │           │
 │            │──request_│              │           │
 │            │   kill()─→│              │           │
 │            │           │              │           │
 │            │           │←─is_kill_    │           │
 │            │           │  requested() │           │
 │            │           │              │           │
 │            │           │──True───────→│           │
 │            │           │              │           │
 │            │           │         [exits]          │
 │            │           │              │           │
 │            │           │←─set_status()│           │
 │            │           │  (KILLED)    │           │
 │            │           │              │           │
 │            │←─snapshot()              │           │
 │            │           │              │           │
 │            │  [renders KILLED status] │           │
 │            │           │              │           │
 │            │───────────────────exit──────────────→│
 │            │           │              │           │
```

### User Command Sequence (Exit UI)

```
User         UI         State       Execution      Main
 │            │           │              │           │
 │──press x──→│           │              │           │
 │            │           │              │           │
 │            │──request_│              │           │
 │            │   exit_ui()              │           │
 │            │           │              │           │
 │            │←─is_exit_│              │           │
 │            │  ui_req? │              │           │
 │            │           │              │           │
 │            │──True────→│              │           │
 │            │           │              │           │
 │            │───────────────────return 0──────────→│
 │            │           │              │           │
 │            │           │              │  [checks  │
 │            │           │              │   alive]  │
 │            │           │              │           │
 │            │           │              │  [prints  │
 │            │           │              │   msg]    │
 │            │           │              │           │
 │            │           │              │  [waits]  │
 │            │           │              │           │
 │            │           │         [continues]      │
 │            │           │              │           │
```

---

## Performance Considerations

### Refresh Rate

- **Default**: 100ms (10 FPS)
- **Trade-off**: Lower = more responsive, higher CPU usage
- **Configurable**: Allow user override via CLI flag

### Log Buffer Size

- **Default**: 1000 lines
- **Memory**: ~1KB per line = ~1MB max
- **Rotation**: Automatic via deque(maxlen=1000)

### Lock Contention

- **Mitigation**: Single coarse lock (no nested locks)
- **Snapshot Pattern**: UI never holds lock during render
- **Write Frequency**: Logs most frequent (~10-100/sec), todos infrequent

### Terminal Rendering

- **Rich Live**: Efficient diff-based rendering
- **Layout Caching**: Reuse layout structure, update content

---

## Testing Strategy

### Unit Tests

1. **AutoModeState**
   - Concurrent read/write operations
   - Snapshot consistency
   - Log rotation
   - Command flags

2. **AutoModeCoordinator**
   - Thread lifecycle
   - Exception capture
   - Completion waiting

3. **AutoModeUI**
   - Layout rendering
   - State snapshot interpretation
   - Keyboard command handling (mocked)

### Integration Tests

1. **End-to-End**
   - Start UI, run mock auto mode, verify updates
   - Test pause/resume/kill commands
   - Test exit UI while execution continues

2. **Error Scenarios**
   - UI crash recovery
   - Execution crash display
   - SDK failure graceful degradation

### Manual Testing Checklist

- [ ] UI renders correctly in various terminal sizes
- [ ] Keyboard commands work reliably
- [ ] Log scrolling is smooth
- [ ] Todos update in real-time
- [ ] Costs accumulate correctly
- [ ] Title generation works
- [ ] Pause/resume transitions cleanly
- [ ] Kill terminates execution
- [ ] Exit UI leaves execution running
- [ ] Error states display clearly

---

## Implementation Plan

### Phase 1: Foundation (Builder Agent Tasks)

1. Create `auto_mode_state.py` with AutoModeState class
2. Create `auto_mode_coordinator.py` with AutoModeCoordinator class
3. Add unit tests for state and coordinator

### Phase 2: UI Implementation (Builder Agent Tasks)

4. Create `auto_mode_ui.py` with AutoModeUI class
5. Implement layout rendering
6. Add keyboard input handling
7. Add unit tests for UI components

### Phase 3: Integration (Builder Agent Tasks)

8. Modify `auto_mode.py` to add `run_auto_mode_with_ui()`
9. Wrap execution function with state callbacks
10. Add CLI flag `--ui`
11. Add integration tests

### Phase 4: SDK Integration (Builder Agent Tasks)

12. Implement title generation callback
13. Implement cost tracking callback
14. Implement todo tracking callback
15. Implement streaming output callback

### Phase 5: Polish (Builder Agent Tasks)

16. Error handling and graceful degradation
17. Performance tuning (refresh rate, buffer sizes)
18. Documentation and examples
19. Manual testing and bug fixes

---

## Dependencies Summary

### New Dependencies

- `rich>=13.0.0` - TUI rendering
- `prompt_toolkit>=3.0.0` - Keyboard input

### Existing Dependencies

- Claude Agent SDK (already in project)
- Standard library: threading, logging, time, collections

---

## Future Enhancements (Not in V1)

1. **Session Reattachment**
   - Save state to disk
   - Restore UI to running session

2. **Multiple Sessions**
   - List running sessions
   - Switch between sessions

3. **Advanced Log Filtering**
   - Search logs
   - Filter by level/pattern

4. **Configuration Persistence**
   - Save UI preferences
   - Custom keybindings

5. **Remote Monitoring**
   - Web-based UI
   - Multi-user access

---

## Success Criteria

✅ UI renders 5 distinct areas clearly
✅ Keyboard commands work reliably (x, p, k, arrows)
✅ Auto mode runs in background thread
✅ Logs stream in real-time
✅ Todos update in real-time
✅ Session title generates automatically
✅ Costs track accurately
✅ Pause/resume works without data loss
✅ Kill terminates cleanly
✅ Exit UI leaves auto mode running
✅ UI crashes don't kill execution
✅ Execution crashes display in UI
✅ Works with existing --append feature
