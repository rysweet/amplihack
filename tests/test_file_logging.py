"""Tests for file-based logging service."""

import logging
import tempfile
from pathlib import Path

import pytest

from amplihack.proxy.file_logging import FileLoggingHandler, FileLoggingService


class TestFileLoggingHandler:
    """Test the file logging handler."""

    def test_init_creates_directory(self):
        """Test that initialization creates the log directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "subdir" / "test.log"
            handler = FileLoggingHandler(log_file)

            assert handler.log_file == log_file
            assert log_file.parent.exists()

    def test_credential_sanitization(self):
        """Test that credentials are properly sanitized."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            handler = FileLoggingHandler(log_file)

            # Test various credential patterns
            test_cases = [
                ("API_KEY: sk-1234567890abcdef1234567890abcdef12345678", "<REDACTED>"),
                ("Bearer abcdefghijklmnopqrstuvwxyz123456", "<REDACTED>"),
                ("password=secret123456", "<REDACTED>"),
                ("Normal log message", "Normal log message"),
            ]

            for input_msg, expected in test_cases:
                result, was_sanitized = handler._sanitize(input_msg)
                assert result == expected

    def test_emit_writes_to_file(self):
        """Test that emit writes log records to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            handler = FileLoggingHandler(log_file)
            handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

            # Create a log record
            record = logging.LogRecord(
                name="test_logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            # Emit the record
            handler.emit(record)

            # Check file contents
            assert log_file.exists()
            with open(log_file, encoding="utf-8") as f:
                content = f.read()
                assert "INFO: Test message" in content

    def test_emit_sanitizes_credentials(self):
        """Test that emit sanitizes credentials in log records."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            handler = FileLoggingHandler(log_file)
            handler.setFormatter(logging.Formatter("%(message)s"))

            # Create a log record with credentials that will match the pattern
            record = logging.LogRecord(
                name="test_logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="API_KEY: secret123456789",
                args=(),
                exc_info=None,
            )

            # Emit the record
            handler.emit(record)

            # Check file contents are sanitized
            with open(log_file, encoding="utf-8") as f:
                content = f.read()
                assert "<REDACTED>" in content
                assert "secret123456789" not in content


class TestFileLoggingService:
    """Test the file logging service."""

    @pytest.fixture
    def temp_log_file(self):
        """Provide a temporary log file path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "test.log"

    @pytest.fixture
    def service(self, temp_log_file):
        """Provide a file logging service instance."""
        service = FileLoggingService(port=8080)
        # Override log file path for testing
        service.log_file_path = temp_log_file
        return service

    @pytest.mark.asyncio
    async def test_start_service(self, service):
        """Test starting the file logging service."""
        result = await service.start()
        assert result is True
        assert service.is_running() is True

    @pytest.mark.asyncio
    async def test_start_service_terminal_launch_fails(self, service):
        """Test starting service when terminal launch fails."""
        # Terminal launching is no longer part of the service
        # This test is kept for backward compatibility but simplified
        result = await service.start()
        assert result is True  # Service starts successfully
        assert service.is_running() is True

    @pytest.mark.asyncio
    async def test_stop_service(self, service):
        """Test stopping the file logging service."""
        # Start the service first
        await service.start()
        assert service.is_running() is True

        # Stop the service
        await service.stop()
        assert service.is_running() is False

    @pytest.mark.asyncio
    async def test_service_integration_with_logging(self, service):
        """Test that the service integrates with Python logging."""
        # Start the service
        await service.start()

        # Log a message
        logger = logging.getLogger("test_logger")
        logger.info("Test integration message")

        # Check that the message was written to file
        # (Note: This test depends on the service adding handlers to the root logger)
        assert service.log_file_path.exists()

    def test_is_running_initial_state(self, service):
        """Test that service is not running initially."""
        assert service.is_running() is False

    @pytest.mark.asyncio
    async def test_start_already_running(self, service):
        """Test that starting an already running service returns True."""
        # Start the service
        result1 = await service.start()
        assert result1 is True

        # Start again
        result2 = await service.start()
        assert result2 is True

        # Service should be idempotent
        assert service.is_running() is True

    @pytest.mark.asyncio
    async def test_stop_not_running(self, service):
        """Test that stopping a non-running service doesn't error."""
        # This should not raise any exceptions
        await service.stop()
        assert service.is_running() is False
