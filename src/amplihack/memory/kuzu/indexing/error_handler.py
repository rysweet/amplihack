"""Error handling for Blarify indexing operations.

Provides graceful error handling with user-friendly messages and recovery strategies.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class ErrorAction(Enum):
    """Action to take in response to an error."""

    SKIP_FILE = "skip_file"
    SKIP_LANGUAGE = "skip_language"
    RETRY = "retry"
    ABORT = "abort"


class ErrorSeverity(Enum):
    """Severity level of an error."""

    WARNING = "warning"
    RECOVERABLE = "recoverable"
    CRITICAL = "critical"


@dataclass
class IndexingError(Exception):
    """Representation of an indexing error."""

    language: str
    error_type: str
    message: str
    severity: ErrorSeverity
    context: dict = field(default_factory=dict)
    scope: str = "language"  # "file" or "language"

    def __str__(self) -> str:
        return f"{self.language}: {self.message}"


@dataclass
class ErrorActionResult:
    """Result of error handling."""

    action_type: ErrorAction
    language: str
    can_continue: bool
    user_message: str
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class DegradationSummary:
    """Summary of degraded operation."""

    total_languages: int
    failed_languages: int
    degraded_mode: bool


class ErrorHandler:
    """Handle errors during Blarify indexing."""

    def __init__(self):
        """Initialize error handler."""
        self._errors: list[IndexingError] = []
        self._callbacks: list[Callable] = []
        self._retry_counts: dict[str, int] = {}

    def handle_error(
        self,
        error: IndexingError,
        attempt: int = 1,
        max_retries: int = 3,
        timeout: float | None = None,
    ) -> ErrorActionResult:
        """Handle an indexing error.

        Args:
            error: The error to handle
            attempt: Current attempt number
            max_retries: Maximum retry attempts
            timeout: Optional timeout in seconds

        Returns:
            ErrorActionResult with recommended action
        """
        self._errors.append(error)

        # Notify callbacks
        action_result = self._determine_action(error, attempt, max_retries, timeout)
        for callback in self._callbacks:
            callback(error, action_result)

        return action_result

    def _determine_action(
        self,
        error: IndexingError,
        attempt: int,
        max_retries: int,
        timeout: float | None,
    ) -> ErrorActionResult:
        """Determine what action to take for an error."""

        # Check for timeout/hang conditions
        if timeout is not None and error.error_type in ["infinite_loop", "timeout"]:
            return ErrorActionResult(
                action_type=ErrorAction.ABORT,
                language=error.language,
                can_continue=False,
                user_message=f"Critical: Indexing hung or timed out for {error.language}. Aborting.",
            )

        # Critical errors always abort
        if error.severity == ErrorSeverity.CRITICAL:
            return ErrorActionResult(
                action_type=ErrorAction.ABORT,
                language=error.language,
                can_continue=False,
                user_message=f"Critical error in {error.language}: {self._make_user_friendly(error)}",
            )

        # Check if max retries exceeded
        if attempt > max_retries:
            return ErrorActionResult(
                action_type=ErrorAction.SKIP_LANGUAGE,
                language=error.language,
                can_continue=True,
                user_message=f"Max retries exceeded for {error.language}. Skipping language.",
            )

        # Recoverable errors can be retried
        if error.severity == ErrorSeverity.RECOVERABLE:
            delay = self._calculate_backoff(attempt)
            return ErrorActionResult(
                action_type=ErrorAction.RETRY,
                language=error.language,
                can_continue=True,
                user_message=f"Retrying {error.language} (attempt {attempt}/{max_retries})...",
                max_retries=max_retries,
                retry_delay=delay,
            )

        # File-scope errors skip the file
        if error.scope == "file":
            return ErrorActionResult(
                action_type=ErrorAction.SKIP_FILE,
                language=error.language,
                can_continue=True,
                user_message=f"Skipping problematic file in {error.language}: {self._make_user_friendly(error)}",
            )

        # Language-scope warnings skip the language
        if error.severity == ErrorSeverity.WARNING:
            return ErrorActionResult(
                action_type=ErrorAction.SKIP_LANGUAGE,
                language=error.language,
                can_continue=True,
                user_message=f"Skipping {error.language}: {self._make_user_friendly(error)}",
            )

        # Default: skip language
        return ErrorActionResult(
            action_type=ErrorAction.SKIP_LANGUAGE,
            language=error.language,
            can_continue=True,
            user_message=f"Skipping {error.language} due to error: {self._make_user_friendly(error)}",
        )

    def _make_user_friendly(self, error: IndexingError) -> str:
        """Convert error message to user-friendly format.

        Args:
            error: The error to format

        Returns:
            User-friendly error message
        """
        message = error.message

        # Extract context information
        if error.context:
            if "file" in error.context:
                file_path = error.context["file"]
                # Show only filename, not full path
                if "/" in file_path:
                    filename = file_path.split("/")[-1]
                    message = message.replace(file_path, filename)

            if "line" in error.context:
                line_num = error.context["line"]
                if str(line_num) not in message:
                    message += f" (line {line_num})"

        # Remove internal technical details
        if message.startswith("Traceback"):
            # Extract just the error message
            lines = message.split("\n")
            message = lines[-1] if lines else message

        return message

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: Attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        base_delay = 1.0
        return base_delay * (2 ** (attempt - 1))

    def register_callback(self, callback: Callable) -> None:
        """Register a callback for error notifications.

        Args:
            callback: Function to call when errors occur
        """
        self._callbacks.append(callback)

    def generate_error_report(self) -> str:
        """Generate a report of all errors.

        Returns:
            Formatted error report
        """
        if not self._errors:
            return "No errors occurred."

        lines = []
        lines.append("Error Report")
        lines.append("=" * 40)

        # Group errors by language
        by_language: dict[str, list[IndexingError]] = {}
        for error in self._errors:
            if error.language not in by_language:
                by_language[error.language] = []
            by_language[error.language].append(error)

        for language, errors in by_language.items():
            lines.append(f"\n{language} ({len(errors)} errors):")
            for error in errors:
                severity_label = error.severity.value.upper()
                lines.append(f"  [{severity_label}] {error.message}")

        return "\n".join(lines)

    def get_degradation_summary(self) -> DegradationSummary:
        """Get summary of degraded operation.

        Returns:
            DegradationSummary with statistics
        """
        # Count unique languages that failed
        failed_languages = set(error.language for error in self._errors)
        total_languages = len(failed_languages)

        return DegradationSummary(
            total_languages=total_languages,
            failed_languages=len(failed_languages),
            degraded_mode=len(failed_languages) > 0,
        )
