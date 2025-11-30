"""Session management for orchestration patterns.

Provides session-level context including log directories, session IDs,
and factory methods for creating ClaudeProcess instances.
"""

import time
from pathlib import Path

from .claude_process import ClaudeProcess


class OrchestratorSession:
    """Manages a session for orchestrating Claude processes.

    A session provides:
    - Unique session ID for tracking
    - Dedicated log directory
    - Factory methods for creating processes
    - Session-level configuration

    Example:
        >>> session = OrchestratorSession(
        ...     pattern_name="parallel-analysis",
        ...     working_dir=Path("/project"),
        ...     base_log_dir=Path("/logs")
        ... )
        >>> process1 = session.create_process("analyze security", "security")
        >>> process2 = session.create_process("analyze performance", "performance")
        >>> # Both processes share the same session context
    """

    def __init__(
        self,
        pattern_name: str,
        working_dir: Path | None = None,
        base_log_dir: Path | None = None,
        model: str | None = None,
    ):
        """Initialize orchestrator session.

        Args:
            pattern_name: Name of the orchestration pattern (e.g., "parallel-analysis")
            working_dir: Working directory for processes (default: current dir)
            base_log_dir: Base directory for logs (default: .claude/runtime/logs)
            model: Default Claude model for all processes (default: None = CLI default)
        """
        self.pattern_name = pattern_name
        self.working_dir = working_dir or Path.cwd()

        # Generate unique session ID
        timestamp = int(time.time())
        self.session_id = f"{pattern_name}_{timestamp}"

        # Create session log directory
        if base_log_dir is None:
            base_log_dir = self.working_dir / ".claude" / "runtime" / "logs"

        self.log_dir = base_log_dir / self.session_id
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Session configuration
        self.model = model
        self._process_counter = 0

        # Write session metadata
        self._write_metadata()

    def create_process(
        self,
        prompt: str,
        process_id: str | None = None,
        model: str | None = None,
        stream_output: bool = True,
        timeout: int | None = None,
    ) -> ClaudeProcess:
        """Create a ClaudeProcess with session context.

        Factory method that creates processes configured with the session's
        working directory, log directory, and default model.

        Args:
            prompt: The prompt to send to Claude
            process_id: Unique identifier (default: auto-generated)
            model: Claude model to use (default: session default)
            stream_output: Whether to stream output to console (default: True)
            timeout: Timeout in seconds (default: None)

        Returns:
            Configured ClaudeProcess instance

        Example:
            >>> session = OrchestratorSession("analysis", Path("/project"))
            >>> p1 = session.create_process("analyze code", "code-analysis")
            >>> p2 = session.create_process("review tests")  # auto-generated ID
        """
        # Auto-generate process ID if not provided
        if process_id is None:
            self._process_counter += 1
            process_id = f"process_{self._process_counter:03d}"

        # Use session model if process doesn't specify one
        if model is None:
            model = self.model

        return ClaudeProcess(
            prompt=prompt,
            process_id=process_id,
            working_dir=self.working_dir,
            log_dir=self.log_dir,
            model=model,
            stream_output=stream_output,
            timeout=timeout,
        )

    def get_session_log_path(self) -> Path:
        """Get path to the session log file.

        Returns:
            Path to session.log
        """
        return self.log_dir / "session.log"

    def get_process_log_path(self, process_id: str) -> Path:
        """Get path to a specific process log file.

        Args:
            process_id: Process identifier

        Returns:
            Path to process log file
        """
        return self.log_dir / f"{process_id}.log"

    def log(self, msg: str, level: str = "INFO"):
        """Log message to session log.

        Args:
            msg: Message to log
            level: Log level (INFO, WARNING, ERROR)
        """
        log_msg = f"[{time.strftime('%H:%M:%S')}] [{level}] {msg}"
        print(f"[SESSION] {log_msg}")

        with open(self.get_session_log_path(), "a") as f:
            f.write(log_msg + "\n")

    def _write_metadata(self):
        """Write session metadata to log directory.

        Creates a session.log file with session information.
        """
        metadata = [
            f"Session ID: {self.session_id}",
            f"Pattern: {self.pattern_name}",
            f"Working Directory: {self.working_dir}",
            f"Log Directory: {self.log_dir}",
            f"Model: {self.model or 'default'}",
            f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "-" * 80,
        ]

        with open(self.get_session_log_path(), "w") as f:
            f.write("\n".join(metadata) + "\n")

    def summarize(self) -> str:
        """Generate session summary.

        Returns:
            Summary string with session information
        """
        return f"""
Session Summary:
  ID: {self.session_id}
  Pattern: {self.pattern_name}
  Working Dir: {self.working_dir}
  Log Dir: {self.log_dir}
  Processes Created: {self._process_counter}
        """.strip()
