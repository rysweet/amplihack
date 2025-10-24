"""Thread-safe shared state for auto mode UI.

This module provides a thread-safe state container that allows the auto mode
execution thread to communicate with the UI thread without race conditions.
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional


@dataclass
class AutoModeState:
    """Thread-safe shared state between auto mode execution and UI.

    This class uses a threading.Lock to ensure all state access is atomic
    and safe for concurrent access from multiple threads.

    Attributes:
        session_id: Session identifier (NOT process ID for security)
        start_time: Unix timestamp when session started
        turn: Current turn number
        max_turns: Maximum number of turns
        objective: User's original prompt/objective
        todos: List of todo items with status
        logs: Deque of log messages (limited size)
        costs: Cost tracking dictionary (input_tokens, output_tokens, estimated_cost)
        status: Current status (running, paused, stopped, completed, error)
        pause_requested: Flag to request pause
        kill_requested: Flag to request termination
    """

    # Core session info
    session_id: str = ""
    start_time: float = 0.0
    turn: int = 1
    max_turns: int = 10
    objective: str = ""

    # Dynamic state
    todos: List[Dict[str, str]] = field(default_factory=list)
    logs: Deque[str] = field(default_factory=lambda: deque(maxlen=1000))
    costs: Dict[str, Any] = field(default_factory=dict)

    # Control state
    status: str = "running"  # running, paused, stopped, completed, error
    pause_requested: bool = False
    kill_requested: bool = False

    # Thread synchronization
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self):
        """Initialize the lock after dataclass initialization."""
        if not hasattr(self, '_lock') or self._lock is None:
            object.__setattr__(self, '_lock', threading.Lock())

    def snapshot(self) -> Dict[str, Any]:
        """Get a thread-safe snapshot of current state.

        Returns:
            Dictionary with all state values at this moment
        """
        with self._lock:
            return {
                'session_id': self.session_id,
                'start_time': self.start_time,
                'turn': self.turn,
                'max_turns': self.max_turns,
                'objective': self.objective,
                'todos': list(self.todos),  # Copy list
                'logs': list(self.logs),    # Copy deque to list
                'costs': dict(self.costs),  # Copy dict
                'status': self.status,
                'pause_requested': self.pause_requested,
                'kill_requested': self.kill_requested,
            }

    def add_log(self, message: str, timestamp: bool = True) -> None:
        """Add a log message to the deque.

        Args:
            message: Log message to add
            timestamp: Whether to prepend timestamp (default True)
        """
        with self._lock:
            if timestamp:
                ts = time.strftime("[%H:%M:%S]")
                message = f"{ts} {message}"
            self.logs.append(message)

    def update_turn(self, turn: int) -> None:
        """Update current turn number.

        Args:
            turn: New turn number
        """
        with self._lock:
            self.turn = turn

    def update_todos(self, todos: List[Dict[str, str]]) -> None:
        """Update todo list.

        Args:
            todos: New todo list
        """
        with self._lock:
            self.todos = list(todos)  # Copy to avoid reference issues

    def update_costs(self, input_tokens: int = 0, output_tokens: int = 0,
                     estimated_cost: float = 0.0) -> None:
        """Update cost tracking information.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            estimated_cost: Estimated cost in dollars
        """
        with self._lock:
            # Accumulate tokens
            self.costs['input_tokens'] = self.costs.get('input_tokens', 0) + input_tokens
            self.costs['output_tokens'] = self.costs.get('output_tokens', 0) + output_tokens
            self.costs['estimated_cost'] = self.costs.get('estimated_cost', 0.0) + estimated_cost

    def update_status(self, status: str) -> None:
        """Update execution status.

        Args:
            status: New status (running, paused, stopped, completed, error)
        """
        with self._lock:
            self.status = status

    def request_pause(self) -> None:
        """Request execution to pause."""
        with self._lock:
            self.pause_requested = True

    def clear_pause_request(self) -> None:
        """Clear pause request."""
        with self._lock:
            self.pause_requested = False

    def request_kill(self) -> None:
        """Request execution to terminate."""
        with self._lock:
            self.kill_requested = True

    def is_pause_requested(self) -> bool:
        """Check if pause is requested.

        Returns:
            True if pause requested
        """
        with self._lock:
            return self.pause_requested

    def is_kill_requested(self) -> bool:
        """Check if kill is requested.

        Returns:
            True if kill requested
        """
        with self._lock:
            return self.kill_requested

    def get_status(self) -> str:
        """Get current status.

        Returns:
            Current status string
        """
        with self._lock:
            return self.status

    def get_turn(self) -> int:
        """Get current turn.

        Returns:
            Current turn number
        """
        with self._lock:
            return self.turn

    def get_elapsed_time(self) -> float:
        """Get elapsed time since session start.

        Returns:
            Elapsed seconds (clamped to 0 if negative)
        """
        with self._lock:
            elapsed = time.time() - self.start_time
            return max(0, elapsed)  # Clamp to 0 for clock skew

    def get_logs(self, n: Optional[int] = None) -> List[str]:
        """Get recent log messages.

        Args:
            n: Number of recent logs to get (None = all)

        Returns:
            List of log messages
        """
        with self._lock:
            if n is None:
                return list(self.logs)
            return list(self.logs)[-n:]

    def get_todos(self) -> List[Dict[str, str]]:
        """Get current todo list.

        Returns:
            Copy of current todo list
        """
        with self._lock:
            return list(self.todos)

    def get_costs(self) -> Dict[str, Any]:
        """Get cost tracking information.

        Returns:
            Dictionary with cost info
        """
        with self._lock:
            return dict(self.costs)
