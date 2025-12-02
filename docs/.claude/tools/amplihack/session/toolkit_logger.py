"""ToolkitLogger for structured logging with session integration."""

import json
import logging
import sys
import threading
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .file_utils import safe_write_file


@dataclass
class LogEntry:
    """Structured log entry."""

    timestamp: float
    level: str
    message: str
    session_id: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = None
    error: Optional[str] = None
    traceback: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = LogEntry(
            timestamp=record.created,
            level=record.levelname,
            message=record.getMessage(),
        )

        # Add context from record
        if hasattr(record, "session_id"):
            log_entry.session_id = record.session_id
        if hasattr(record, "component"):
            log_entry.component = record.component
        if hasattr(record, "operation"):
            log_entry.operation = record.operation
        if hasattr(record, "duration"):
            log_entry.duration = record.duration
        if hasattr(record, "metadata"):
            log_entry.metadata = record.metadata

        # Add exception info
        if record.exc_info:
            log_entry.error = str(record.exc_info[1])
            log_entry.traceback = "".join(traceback.format_exception(*record.exc_info))

        return json.dumps(asdict(log_entry), default=str)


class FileRotatingHandler(logging.Handler):
    """Custom rotating file handler with size and time limits."""

    def __init__(
        self,
        base_path: Path,
        max_size: int = 10 * 1024 * 1024,  # 10MB
        max_files: int = 5,
        rotate_daily: bool = True,
    ):
        super().__init__()
        self.base_path = Path(base_path)
        self.base_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self.max_files = max_files
        self.rotate_daily = rotate_daily
        self.current_date = datetime.now().date()
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record."""
        try:
            with self._lock:
                log_file = self._get_current_log_file()

                # Check if rotation is needed
                if self._should_rotate(log_file):
                    self._rotate_logs()
                    log_file = self._get_current_log_file()

                # Write log entry
                log_entry = self.format(record)
                safe_write_file(log_file, log_entry + "\n", mode="a")

        except Exception:
            self.handleError(record)

    def _get_current_log_file(self) -> Path:
        """Get current log file path."""
        if self.rotate_daily:
            date_str = datetime.now().strftime("%Y%m%d")
            return self.base_path.parent / f"{self.base_path.stem}_{date_str}.log"
        return self.base_path

    def _should_rotate(self, log_file: Path) -> bool:
        """Check if log rotation is needed."""
        # Size-based rotation
        if log_file.exists() and log_file.stat().st_size > self.max_size:
            return True

        # Date-based rotation
        if self.rotate_daily:
            current_date = datetime.now().date()
            if current_date != self.current_date:
                self.current_date = current_date
                return True

        return False

    def _rotate_logs(self) -> None:
        """Rotate log files."""
        log_files = list(self.base_path.parent.glob(f"{self.base_path.stem}_*.log"))
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # Remove excess files
        for old_file in log_files[self.max_files - 1 :]:
            try:
                old_file.unlink()
            except Exception:
                pass


class ToolkitLogger:
    """Enhanced logger for Claude toolkit with structured logging and session integration.

    Features:
    - Structured JSON logging
    - Session-aware logging
    - Component and operation tracking
    - Performance monitoring
    - Automatic log rotation
    - Multiple output formats

    Example:
        >>> logger = ToolkitLogger("session_123", component="analyzer")
        >>> with logger.operation("code_analysis"):
        ...     logger.info("Starting analysis", metadata={"files": 5})
        ...     # ... do work ...
        ...     logger.success("Analysis complete", duration=12.5)
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        component: Optional[str] = None,
        log_dir: Optional[Path] = None,
        level: str = "INFO",
        enable_console: bool = True,
        enable_file: bool = True,
        enable_structured: bool = True,
    ):
        """Initialize toolkit logger.

        Args:
            session_id: Session identifier for log correlation
            component: Component name for log organization
            log_dir: Directory for log files
            level: Logging level
            enable_console: Enable console output
            enable_file: Enable file output
            enable_structured: Enable structured JSON format
        """
        self.session_id = session_id
        self.component = component
        self.log_dir = log_dir or Path(".claude/runtime/logs")
        self.enable_structured = enable_structured

        # Create logger
        logger_name = f"toolkit.{component}" if component else "toolkit"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.handlers.clear()  # Remove existing handlers

        # Operation tracking
        self._current_operation: Optional[str] = None
        self._operation_start_time: Optional[float] = None
        self._operation_stack: List[tuple] = []

        # Setup handlers
        if enable_console:
            self._setup_console_handler()
        if enable_file:
            self._setup_file_handler()

    def _setup_console_handler(self) -> None:
        """Setup console handler with appropriate formatter."""
        handler = logging.StreamHandler(sys.stdout)

        if self.enable_structured:
            handler.setFormatter(StructuredFormatter())
        else:
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def _setup_file_handler(self) -> None:
        """Setup file handler with rotation."""
        log_file = self.log_dir / f"{self.session_id or 'toolkit'}.log"
        handler = FileRotatingHandler(log_file)

        if self.enable_structured:
            handler.setFormatter(StructuredFormatter())
        else:
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def _log(
        self,
        level: str,
        message: str,
        operation: Optional[str] = None,
        duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ) -> None:
        """Internal logging method with context."""
        # Create log record
        record = self.logger.makeRecord(
            self.logger.name,
            getattr(logging, level.upper()),
            __file__,
            0,
            message,
            (),
            exc_info if exc_info else None,
        )

        # Add context
        record.session_id = self.session_id
        record.component = self.component
        record.operation = operation or self._current_operation
        record.duration = duration
        record.metadata = metadata or {}

        # Emit the record
        self.logger.handle(record)

    def debug(self, message: str, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log debug message."""
        self._log("DEBUG", message, metadata=metadata, **kwargs)

    def info(self, message: str, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log info message."""
        self._log("INFO", message, metadata=metadata, **kwargs)

    def warning(self, message: str, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log warning message."""
        self._log("WARNING", message, metadata=metadata, **kwargs)

    def error(
        self,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        exc_info: bool = True,
        **kwargs,
    ) -> None:
        """Log error message."""
        self._log("ERROR", message, metadata=metadata, exc_info=exc_info, **kwargs)

    def critical(
        self,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        exc_info: bool = True,
        **kwargs,
    ) -> None:
        """Log critical message."""
        self._log("CRITICAL", message, metadata=metadata, exc_info=exc_info, **kwargs)

    def success(
        self,
        message: str,
        duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """Log success message (custom level)."""
        self._log("INFO", f"✓ {message}", duration=duration, metadata=metadata, **kwargs)

    def start_operation(self, operation: str) -> None:
        """Start tracking an operation."""
        if self._current_operation:
            # Push current operation to stack
            self._operation_stack.append((self._current_operation, self._operation_start_time))

        self._current_operation = operation
        self._operation_start_time = time.time()
        self.info(f"Started operation: {operation}")

    def end_operation(self, success: bool = True, message: Optional[str] = None) -> Optional[float]:
        """End current operation and return duration."""
        if not self._current_operation:
            self.warning("No active operation to end")
            return None

        duration = time.time() - (self._operation_start_time or 0)
        operation = self._current_operation

        # Log completion
        if success:
            self.success(message or f"Completed operation: {operation}", duration=duration)
        else:
            self.error(message or f"Failed operation: {operation}", metadata={"duration": duration})

        # Restore previous operation
        if self._operation_stack:
            self._current_operation, self._operation_start_time = self._operation_stack.pop()
        else:
            self._current_operation = None
            self._operation_start_time = None

        return duration

    def operation(self, name: str):
        """Context manager for operation tracking.

        Example:
            >>> with logger.operation("file_processing"):
            ...     # work happens here
            ...     pass
        """
        return OperationContext(self, name)

    def get_session_logs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get logs for current session.

        Args:
            limit: Maximum number of log entries

        Returns:
            List of log entries
        """
        if not self.session_id:
            return []

        log_file = self.log_dir / f"{self.session_id}.log"
        if not log_file.exists():
            return []

        try:
            logs = []
            with open(log_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            log_entry = json.loads(line)
                            logs.append(log_entry)
                        except json.JSONDecodeError:
                            # Handle non-JSON lines
                            logs.append({"message": line, "level": "INFO"})

            # Apply limit
            if limit:
                logs = logs[-limit:]

            return logs

        except Exception as e:
            self.error(f"Failed to read session logs: {e}")
            return []

    def create_child_logger(self, component: str) -> "ToolkitLogger":
        """Create child logger with same session but different component."""
        return ToolkitLogger(
            session_id=self.session_id,
            component=f"{self.component}.{component}" if self.component else component,
            log_dir=self.log_dir,
            enable_console=False,  # Avoid duplicate console output
            enable_file=True,
            enable_structured=self.enable_structured,
        )


class OperationContext:
    """Context manager for operation tracking."""

    def __init__(self, logger: ToolkitLogger, operation: str):
        self.logger = logger
        self.operation = operation

    def __enter__(self):
        self.logger.start_operation(self.operation)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        if exc_type:
            message = f"Operation failed: {exc_val}"
        else:
            message = None
        self.logger.end_operation(success=success, message=message)
