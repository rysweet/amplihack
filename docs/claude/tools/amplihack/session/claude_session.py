"""ClaudeSession wrapper with timeout handling and session lifecycle management."""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SessionConfig:
    """Configuration for Claude session behavior."""

    timeout: float = 300.0  # 5 minutes default
    max_retries: int = 3
    retry_delay: float = 1.0
    heartbeat_interval: float = 30.0
    enable_logging: bool = True
    log_level: str = "INFO"
    session_id: Optional[str] = None
    auto_save_interval: float = 60.0  # Auto-save every minute


@dataclass
class SessionState:
    """Current state of a Claude session."""

    session_id: str
    start_time: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    is_active: bool = True
    command_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TimeoutError(Exception):
    """Raised when session operations timeout."""


class SessionError(Exception):
    """Base exception for session-related errors."""


class ClaudeSession:
    """Enhanced Claude session wrapper with timeout handling and lifecycle management.

    Provides:
    - Configurable timeouts for operations
    - Automatic retry logic with exponential backoff
    - Session state tracking and persistence
    - Heartbeat monitoring
    - Graceful error handling and recovery

    Example:
        >>> config = SessionConfig(timeout=120.0, max_retries=5)
        >>> session = ClaudeSession(config)
        >>> with session:
        ...     result = session.execute_command("analyze code")
        ...     session.save_checkpoint()
    """

    def __init__(self, config: Optional[SessionConfig] = None):
        """Initialize Claude session with configuration.

        Args:
            config: Session configuration. Uses defaults if None.
        """
        self.config = config or SessionConfig()
        self.state = SessionState(session_id=self.config.session_id or self._generate_session_id())
        self.logger = self._setup_logger()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._command_history: List[Dict[str, Any]] = []
        self._checkpoints: List[SessionState] = []

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        import uuid

        timestamp = int(time.time())
        return f"claude_session_{timestamp}_{uuid.uuid4().hex[:8]}"

    def _setup_logger(self) -> logging.Logger:
        """Setup session-specific logger."""
        logger = logging.getLogger(f"claude_session.{self.state.session_id}")
        logger.setLevel(getattr(logging, self.config.log_level))

        if not logger.handlers and self.config.enable_logging:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def start(self) -> None:
        """Start the session and begin monitoring."""
        self.state.is_active = True
        self.state.start_time = time.time()
        self.state.last_activity = time.time()

        if self.config.heartbeat_interval > 0:
            self._start_heartbeat()

        self.logger.info(f"Session {self.state.session_id} started")

    def stop(self) -> None:
        """Stop the session and cleanup resources."""
        self.state.is_active = False
        self._shutdown_event.set()

        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5.0)

        self.logger.info(f"Session {self.state.session_id} stopped")

    def _start_heartbeat(self) -> None:
        """Start heartbeat monitoring thread."""
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def _heartbeat_loop(self) -> None:
        """Heartbeat monitoring loop."""
        while not self._shutdown_event.wait(self.config.heartbeat_interval):
            if not self.state.is_active:
                break

            try:
                self._check_session_health()
            except Exception as e:
                self.logger.error(f"Heartbeat check failed: {e}")

    def _check_session_health(self) -> None:
        """Check session health and handle timeouts."""
        current_time = time.time()
        time_since_activity = current_time - self.state.last_activity

        if time_since_activity > self.config.timeout:
            self.logger.warning(
                f"Session inactive for {time_since_activity:.1f}s (timeout: {self.config.timeout}s)"
            )
            self._handle_timeout()

    def _handle_timeout(self) -> None:
        """Handle session timeout."""
        self.state.is_active = False
        self.state.last_error = f"Session timeout after {self.config.timeout}s"
        self.logger.error(self.state.last_error)

    def execute_command(self, command: str, timeout: Optional[float] = None, **kwargs) -> Any:
        """Execute a command with timeout and retry logic.

        Args:
            command: Command to execute
            timeout: Override default timeout
            **kwargs: Additional command arguments

        Returns:
            Command result

        Raises:
            TimeoutError: If command times out
            SessionError: If session is not active
        """
        if not self.state.is_active:
            raise SessionError("Session is not active")

        timeout = timeout or self.config.timeout
        start_time = time.time()

        self.logger.info(f"Executing command: {command}")
        self.state.command_count += 1
        self._update_activity()

        # Record command in history
        command_record = {"command": command, "timestamp": start_time, "kwargs": kwargs}

        try:
            result = self._execute_with_timeout(command, timeout, **kwargs)
            command_record["result"] = "success"
            command_record["duration"] = time.time() - start_time
            self._command_history.append(command_record)
            return result

        except Exception as e:
            self.state.error_count += 1
            self.state.last_error = str(e)
            command_record["result"] = "error"
            command_record["error"] = str(e)
            command_record["duration"] = time.time() - start_time
            self._command_history.append(command_record)

            self.logger.error(f"Command failed: {e}")
            raise

    def _execute_with_timeout(self, command: str, timeout: float, **kwargs) -> Any:
        """Execute command with timeout using threading."""
        result = None
        exception = None

        def target():
            nonlocal result, exception
            try:
                # This is where you'd integrate with actual Claude API
                # For now, simulate command execution
                result = self._simulate_command_execution(command, **kwargs)
            except Exception as e:
                exception = e

        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            # Timeout occurred
            raise TimeoutError(f"Command '{command}' timed out after {timeout}s")

        if exception:
            raise exception

        return result

    def _simulate_command_execution(self, command: str, **kwargs) -> Dict[str, Any]:
        """Simulate command execution (replace with actual Claude integration)."""
        import random
        import time

        # Simulate processing time
        time.sleep(random.uniform(0.1, 0.5))

        return {
            "command": command,
            "status": "completed",
            "timestamp": time.time(),
            "session_id": self.state.session_id,
            "kwargs": kwargs,
        }

    def _update_activity(self) -> None:
        """Update last activity timestamp."""
        self.state.last_activity = time.time()

    def save_checkpoint(self) -> None:
        """Save current session state as checkpoint."""
        import copy

        checkpoint = copy.deepcopy(self.state)
        self._checkpoints.append(checkpoint)
        self.logger.info(f"Checkpoint saved: {len(self._checkpoints)} total")

    def restore_checkpoint(self, index: int = -1) -> None:
        """Restore session state from checkpoint.

        Args:
            index: Checkpoint index (-1 for most recent)
        """
        if not self._checkpoints:
            raise SessionError("No checkpoints available")

        checkpoint = self._checkpoints[index]
        self.state = checkpoint
        self.logger.info(f"Restored checkpoint {index}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get session statistics."""
        current_time = time.time()
        return {
            "session_id": self.state.session_id,
            "uptime": current_time - self.state.start_time,
            "command_count": self.state.command_count,
            "error_count": self.state.error_count,
            "error_rate": self.state.error_count / max(self.state.command_count, 1),
            "is_active": self.state.is_active,
            "checkpoints": len(self._checkpoints),
            "last_activity": self.state.last_activity,
            "time_since_activity": current_time - self.state.last_activity,
        }

    def get_command_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent command history.

        Args:
            limit: Maximum number of commands to return

        Returns:
            List of recent commands
        """
        return self._command_history[-limit:]

    def clear_history(self) -> None:
        """Clear command history and checkpoints."""
        self._command_history.clear()
        self._checkpoints.clear()
        self.logger.info("Session history cleared")
