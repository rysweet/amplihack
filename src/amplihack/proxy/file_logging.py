"""File-based logging service to replace browser-based log streaming."""

import logging
import re
import subprocess
from pathlib import Path
from typing import Optional, Union


class FileLoggingHandler(logging.Handler):
    """File-based logging handler with credential sanitization."""

    def __init__(self, log_file: Path):
        """Initialize the file logging handler.

        Args:
            log_file: Path to the log file
        """
        super().__init__()
        self.log_file = log_file
        self._credential_pattern = re.compile(
            r'(?i)(?:api[_-]?key|token|password|authorization)["\s:=]*["\s]*([a-zA-Z0-9\-_+/=!@#$%^&*()]{8,})|sk-[a-zA-Z0-9]{48}|Bearer\s+[a-zA-Z0-9\-_+/=]{20,}'
        )

        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _sanitize(self, message: str) -> tuple[str, bool]:
        """Remove credentials from log message.

        Args:
            message: Original log message

        Returns:
            Tuple of (sanitized_message, was_sanitized)
        """
        if self._credential_pattern.search(message):
            return self._credential_pattern.sub("<REDACTED>", message), True
        return message, False

    def emit(self, record: logging.LogRecord) -> None:
        """Handle log record by writing to file.

        Args:
            record: The log record to handle
        """
        try:
            message = self.format(record)
            sanitized_message, was_sanitized = self._sanitize(message)

            # Write to file with timestamp
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{sanitized_message}\n")
                f.flush()

        except Exception:
            # Silently ignore logging errors to prevent cascading failures
            pass


class FileLoggingHandlerWithRotation(logging.Handler):
    """File logging handler with both rotation and credential sanitization."""

    def __init__(self, log_file: Path):
        """Initialize the handler with rotation and sanitization.

        Args:
            log_file: Path to the log file
        """
        super().__init__()
        from logging.handlers import RotatingFileHandler

        self.log_file = log_file
        self._credential_pattern = re.compile(
            r'(?i)(?:api[_-]?key|token|password|authorization)["\s:=]*["\s]*([a-zA-Z0-9\-_+/=!@#$%^&*()]{8,})|sk-[a-zA-Z0-9]{48}|Bearer\s+[a-zA-Z0-9\-_+/=]{20,}'
        )

        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create the rotating file handler internally
        self._rotating_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3,
            encoding="utf-8",
        )

    def _sanitize(self, message: str) -> tuple[str, bool]:
        """Remove credentials from log message.

        Args:
            message: Original log message

        Returns:
            Tuple of (sanitized_message, was_sanitized)
        """
        if self._credential_pattern.search(message):
            return self._credential_pattern.sub("<REDACTED>", message), True
        return message, False

    def setFormatter(self, fmt: logging.Formatter | None) -> None:
        """Set formatter for both this handler and the internal rotating handler."""
        super().setFormatter(fmt)
        self._rotating_handler.setFormatter(fmt)

    def setLevel(self, level) -> None:
        """Set level for both this handler and the internal rotating handler."""
        super().setLevel(level)
        self._rotating_handler.setLevel(level)

    def emit(self, record: logging.LogRecord) -> None:
        """Handle log record by sanitizing and delegating to rotating handler.

        Args:
            record: The log record to handle
        """
        try:
            # Get the original message (before formatting)
            original_msg = record.getMessage()

            # Sanitize the original message
            sanitized_msg, was_sanitized = self._sanitize(original_msg)

            # Create a new record with the sanitized message
            sanitized_record = logging.LogRecord(
                name=record.name,
                level=record.levelno,
                pathname=record.pathname,
                lineno=record.lineno,
                msg=sanitized_msg,
                args=(),  # No args since we sanitized the message
                exc_info=record.exc_info,
            )

            # Copy other attributes that might be needed
            sanitized_record.created = record.created
            sanitized_record.msecs = record.msecs
            sanitized_record.relativeCreated = record.relativeCreated
            sanitized_record.thread = record.thread
            sanitized_record.threadName = record.threadName
            sanitized_record.processName = record.processName
            sanitized_record.process = record.process
            sanitized_record.module = record.module
            sanitized_record.filename = record.filename
            sanitized_record.funcName = record.funcName

            # Delegate to the rotating handler (it will format the sanitized record)
            self._rotating_handler.emit(sanitized_record)

        except Exception:
            # Silently ignore logging errors to prevent cascading failures
            pass


class FileLoggingService:
    """File-based logging service with automatic terminal launching."""

    def __init__(self, port: int):
        """Initialize the file logging service.

        Args:
            port: Port number (kept for compatibility with LogStreamingService interface)
        """
        self.port = port  # Keep for interface compatibility
        self.log_file_path = Path("./.claude/runtime/proxy/amplihack_proxy.log")
        self.handler: Optional[Union[FileLoggingHandler, FileLoggingHandlerWithRotation]] = None
        self.terminal_process: Optional[subprocess.Popen] = None
        self.running = False

    async def start(self) -> bool:
        """Start the file logging service.

        Returns:
            True if service started successfully, False otherwise
        """
        if self.running:
            return True

        try:
            # Setup rotating file handler
            self._setup_logging()

            # Just print the log file path - no terminal spawning
            print(f"📝 Log file: {self.log_file_path.absolute()}")
            self.terminal_process = None

            self.running = True
            return True

        except Exception as e:
            print(f"File logging failed to start: {e}")
            return False

    async def stop(self) -> None:
        """Stop the file logging service."""
        if not self.running:
            return

        try:
            # Remove logging handler
            if self.handler:
                logging.getLogger().removeHandler(self.handler)
                self.handler = None

            # Terminate terminal process if it exists
            if self.terminal_process:
                try:
                    self.terminal_process.terminate()
                except Exception:
                    pass
                self.terminal_process = None

            self.running = False

        except Exception:
            pass

    def is_running(self) -> bool:
        """Check if service is running.

        Returns:
            True if service is running
        """
        return self.running

    def _setup_logging(self) -> None:
        """Setup file logging integration with rotation and sanitization."""

        # Create our custom handler with sanitization that uses RotatingFileHandler internally
        self.handler = FileLoggingHandlerWithRotation(self.log_file_path)

        # Set formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        if self.handler is not None:
            self.handler.setFormatter(formatter)
            self.handler.setLevel(logging.DEBUG)

        # Add only our custom handler to root logger
        root_logger = logging.getLogger()
        if self.handler is not None:
            root_logger.addHandler(self.handler)
