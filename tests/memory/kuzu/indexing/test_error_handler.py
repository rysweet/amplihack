"""Tests for ErrorHandler module.

Tests error handling actions (SKIP, RETRY, ABORT),
user-friendly error messages, and hang prevention.
"""

from unittest.mock import patch

import pytest

from amplihack.memory.kuzu.indexing.error_handler import (
    ErrorAction,
    ErrorHandler,
    ErrorSeverity,
    IndexingError,
)


class TestErrorHandler:
    """Test error handling during indexing."""

    @pytest.fixture
    def handler(self):
        """Create ErrorHandler instance."""
        return ErrorHandler()

    def test_skip_language_action_for_missing_tools(self, handler):
        """Test SKIP_LANGUAGE action for missing tools."""
        # Arrange
        error = IndexingError(
            language="python",
            error_type="missing_tool",
            message="scip-python binary not found",
            severity=ErrorSeverity.WARNING,
        )

        # Act
        action = handler.handle_error(error)

        # Assert
        assert action.action_type == ErrorAction.SKIP_LANGUAGE
        assert action.language == "python"
        assert action.can_continue is True
        assert "skip" in action.user_message.lower()

    def test_retry_action_for_timeouts(self, handler):
        """Test RETRY action for timeouts."""
        # Arrange
        error = IndexingError(
            language="javascript",
            error_type="timeout",
            message="Indexing timed out after 300 seconds",
            severity=ErrorSeverity.RECOVERABLE,
        )

        # Act
        action = handler.handle_error(error)

        # Assert
        assert action.action_type == ErrorAction.RETRY
        assert action.language == "javascript"
        assert action.max_retries > 0
        assert "retry" in action.user_message.lower()

    def test_abort_action_for_critical_errors(self, handler):
        """Test ABORT action for critical errors."""
        # Arrange
        error = IndexingError(
            language="python",
            error_type="database_corruption",
            message="Kuzu database file corrupted",
            severity=ErrorSeverity.CRITICAL,
        )

        # Act
        action = handler.handle_error(error)

        # Assert
        assert action.action_type == ErrorAction.ABORT
        assert action.can_continue is False
        assert "abort" in action.user_message.lower() or "critical" in action.user_message.lower()

    def test_user_friendly_error_messages(self, handler):
        """Test that error messages are user-friendly."""
        # Arrange
        error = IndexingError(
            language="typescript",
            error_type="missing_dependency",
            message="runtime_dependencies.json not found in /path/to/config",
            severity=ErrorSeverity.WARNING,
        )

        # Act
        action = handler.handle_error(error)

        # Assert
        # User-friendly message should not contain stack traces or internal paths
        assert "runtime_dependencies.json" in action.user_message
        assert action.user_message != error.message  # Should be transformed
        assert not action.user_message.startswith("Traceback")

    def test_errors_dont_cause_hangs(self, handler):
        """Test that errors don't cause hangs."""
        # Arrange
        error = IndexingError(
            language="python",
            error_type="infinite_loop",
            message="Parser stuck in infinite loop",
            severity=ErrorSeverity.CRITICAL,
        )

        # Act
        with patch("time.time") as mock_time:
            # Simulate timeout detection
            mock_time.side_effect = [0, 301]  # Simulate 301 seconds elapsed
            action = handler.handle_error(error, timeout=300)

        # Assert
        assert action.action_type == ErrorAction.ABORT
        assert "timeout" in action.user_message.lower() or "hung" in action.user_message.lower()

    def test_retry_with_backoff(self, handler):
        """Test retry with exponential backoff."""
        # Arrange
        error = IndexingError(
            language="csharp",
            error_type="transient_failure",
            message="Network connection failed",
            severity=ErrorSeverity.RECOVERABLE,
        )

        # Act - Multiple retries
        action1 = handler.handle_error(error, attempt=1)
        action2 = handler.handle_error(error, attempt=2)
        action3 = handler.handle_error(error, attempt=3)

        # Assert
        assert action1.retry_delay < action2.retry_delay < action3.retry_delay
        assert all(a.action_type == ErrorAction.RETRY for a in [action1, action2, action3])

    def test_max_retries_exceeded_converts_to_skip(self, handler):
        """Test that exceeding max retries converts to SKIP."""
        # Arrange
        error = IndexingError(
            language="python",
            error_type="transient_failure",
            message="Temporary error",
            severity=ErrorSeverity.RECOVERABLE,
        )

        # Act - Exceed max retries
        action = handler.handle_error(error, attempt=4, max_retries=3)

        # Assert
        assert action.action_type == ErrorAction.SKIP_LANGUAGE
        assert "max retries exceeded" in action.user_message.lower()

    def test_aggregate_error_report(self, handler):
        """Test aggregated error report generation."""
        # Arrange
        errors = [
            IndexingError("python", "missing_tool", "scip-python not found", ErrorSeverity.WARNING),
            IndexingError("typescript", "timeout", "Indexing timed out", ErrorSeverity.RECOVERABLE),
            IndexingError("csharp", "unsupported_version", "dotnet 10.0.2", ErrorSeverity.WARNING),
        ]

        # Act
        for error in errors:
            handler.handle_error(error)

        report = handler.generate_error_report()

        # Assert
        assert "python" in report
        assert "typescript" in report
        assert "csharp" in report
        assert report.count("WARNING") >= 2

    def test_error_severity_levels(self, handler):
        """Test different error severity levels."""
        # Arrange & Act
        warning = IndexingError("python", "minor", "Minor issue", ErrorSeverity.WARNING)
        recoverable = IndexingError("python", "retry", "Retry issue", ErrorSeverity.RECOVERABLE)
        critical = IndexingError("python", "fatal", "Fatal issue", ErrorSeverity.CRITICAL)

        warning_action = handler.handle_error(warning)
        recoverable_action = handler.handle_error(recoverable)
        critical_action = handler.handle_error(critical)

        # Assert
        assert warning_action.can_continue is True
        assert recoverable_action.can_continue is True
        assert critical_action.can_continue is False

    def test_context_preserved_in_error_messages(self, handler):
        """Test that context is preserved in error messages."""
        # Arrange
        error = IndexingError(
            language="python",
            error_type="parse_error",
            message="Failed to parse file: /path/to/file.py at line 42",
            severity=ErrorSeverity.WARNING,
            context={"file": "/path/to/file.py", "line": 42},
        )

        # Act
        action = handler.handle_error(error)

        # Assert
        assert "file.py" in action.user_message
        assert "42" in action.user_message

    def test_skip_single_file_vs_skip_language(self, handler):
        """Test distinction between skipping a file vs skipping entire language."""
        # Arrange
        file_error = IndexingError(
            language="python",
            error_type="parse_error",
            message="Cannot parse single file",
            severity=ErrorSeverity.WARNING,
            scope="file",
        )

        language_error = IndexingError(
            language="python",
            error_type="missing_tool",
            message="Tool not available",
            severity=ErrorSeverity.WARNING,
            scope="language",
        )

        # Act
        file_action = handler.handle_error(file_error)
        language_action = handler.handle_error(language_error)

        # Assert
        assert file_action.action_type == ErrorAction.SKIP_FILE
        assert language_action.action_type == ErrorAction.SKIP_LANGUAGE

    def test_error_callback_registration(self, handler):
        """Test registering callbacks for error notifications."""
        # Arrange
        callback_called = []

        def error_callback(error, action):
            callback_called.append((error, action))

        handler.register_callback(error_callback)

        error = IndexingError("python", "test", "Test error", ErrorSeverity.WARNING)

        # Act
        action = handler.handle_error(error)

        # Assert
        assert len(callback_called) == 1
        assert callback_called[0][0] == error
        assert callback_called[0][1] == action

    def test_graceful_degradation(self, handler):
        """Test graceful degradation when multiple languages fail."""
        # Arrange
        errors = [
            IndexingError("python", "missing_tool", "scip-python", ErrorSeverity.WARNING),
            IndexingError("typescript", "missing_tool", "tsserver", ErrorSeverity.WARNING),
            IndexingError("csharp", "version", "unsupported", ErrorSeverity.WARNING),
        ]

        # Act
        actions = [handler.handle_error(e) for e in errors]
        summary = handler.get_degradation_summary()

        # Assert
        assert all(a.action_type == ErrorAction.SKIP_LANGUAGE for a in actions)
        assert summary.total_languages == 3
        assert summary.failed_languages == 3
        assert summary.degraded_mode is True
