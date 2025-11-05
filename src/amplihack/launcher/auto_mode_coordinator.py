"""Thread coordinator for auto mode background execution.

This module manages the lifecycle of auto mode execution in a background thread,
providing methods to start and monitor execution while maintaining thread-safe
communication with the UI.
"""

import threading
import time
from typing import Callable, Optional

from .auto_mode_state import AutoModeState


class AutoModeCoordinator:
    """Manages auto mode execution in background thread.

    This coordinator wraps auto mode execution in a background thread and
    provides lifecycle management (start, monitor) while maintaining
    thread-safe state updates via AutoModeState.

    Attributes:
        auto_mode: The AutoMode instance to execute
        state: Shared thread-safe state container
        execution_thread: Background thread running auto mode
        state_callback: Optional callback for state updates
    """

    def __init__(
        self,
        auto_mode,
        state: AutoModeState,
        state_callback: Optional[Callable[[AutoModeState], None]] = None,
    ):
        """Initialize coordinator.

        Args:
            auto_mode: AutoMode instance to execute in background
            state: Shared AutoModeState instance
            state_callback: Optional callback invoked on state changes
        """
        self.auto_mode = auto_mode
        self.state = state
        self.state_callback = state_callback
        self.execution_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start auto mode execution in background thread.

        This creates and starts a new thread that will execute auto_mode.run().
        """
        if self.execution_thread and self.execution_thread.is_alive():
            raise RuntimeError("Auto mode already running")

        # Initialize state (session_id already set from AutoMode.log_dir.name)
        self.state.start_time = time.time()
        self.state.turn = 1
        self.state.max_turns = self.auto_mode.max_turns
        self.state.objective = self.auto_mode.prompt
        self.state.update_status("running")

        # Create and start execution thread
        self.execution_thread = threading.Thread(
            target=self._run_with_state_updates, name="AutoModeExecution", daemon=False
        )
        self.execution_thread.start()

        # Log start
        self.state.add_log(f"Auto mode started (max {self.state.max_turns} turns)")
        self._notify_callback()

    def _run_with_state_updates(self) -> None:
        """Run auto mode with periodic state updates.

        This is the target function for the background thread. It executes
        auto mode while updating shared state.
        """
        try:
            # Inject state update hooks into auto mode
            original_log = self.auto_mode.log

            def state_aware_log(msg: str, level: str = "INFO"):
                """Log that also updates shared state."""
                original_log(msg, level)
                self.state.add_log(f"[{level}] {msg}")
                self._notify_callback()

            self.auto_mode.log = state_aware_log

            # Execute auto mode
            exit_code = self.auto_mode.run()

            # Update final status
            if exit_code == 0:
                self.state.update_status("completed")
                self.state.add_log("Auto mode completed successfully")
            else:
                self.state.update_status("error")
                self.state.add_log(f"Auto mode exited with code {exit_code}")

        except Exception as e:
            self.state.update_status("error")
            self.state.add_log(f"Auto mode error: {e}")
        finally:
            self._notify_callback()

    def wait(self, timeout: Optional[float] = None) -> None:
        """Wait for execution thread to complete.

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)
        """
        if self.execution_thread and self.execution_thread.is_alive():
            self.execution_thread.join(timeout=timeout)

    def is_alive(self) -> bool:
        """Check if execution thread is alive.

        Returns:
            True if thread is running
        """
        return self.execution_thread is not None and self.execution_thread.is_alive()

    def _notify_callback(self) -> None:
        """Notify state callback if configured."""
        if self.state_callback:
            try:
                self.state_callback(self.state)
            except Exception as e:
                # Don't let callback errors crash coordinator
                self.state.add_log(f"State callback error: {e}", timestamp=True)
