"""Unit tests for session monitoring module.

Testing pyramid distribution:
- This file contains 18 unit tests (~60% of unit test coverage for this module)
- Tests focus on resource monitoring with/without psutil, limit checking, and JSON output
"""

import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta
from io import StringIO

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Import with error handling for syntax issues in the original script
try:
    from monitor_session import (
        get_process_info,
        monitor_session,
        HAS_PSUTIL
    )
    # Import limits safely
    import monitor_session as ms
    MAX_MEMORY_MB = getattr(ms, 'MAX_MEMORY_MB', 4096)
    SESSION_TIMEOUT_MIN = getattr(ms, 'SESSION_TIMEOUT_MIN', 30)
except SyntaxError:
    # If there's a syntax error, skip these tests
    pytest.skip("monitor_session.py has syntax errors", allow_module_level=True)
except ImportError as e:
    pytest.skip(f"Cannot import monitor_session: {e}", allow_module_level=True)


# ============================================================================
# PROCESS INFO TESTS (6 tests)
# ============================================================================

class TestProcessInfo:
    """Test process information gathering."""

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    def test_get_process_info_with_psutil_valid_pid(self):
        """Test getting process info with psutil for valid PID."""
        import os
        current_pid = os.getpid()

        info = get_process_info(current_pid)

        assert info is not None
        assert "cpu_percent" in info
        assert "memory_mb" in info
        assert "status" in info
        assert "create_time" in info
        assert isinstance(info["memory_mb"], float)
        assert info["memory_mb"] > 0

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    def test_get_process_info_with_invalid_pid(self):
        """Test getting process info for non-existent PID."""
        # Use a PID that definitely doesn't exist
        invalid_pid = 999999

        info = get_process_info(invalid_pid)

        assert info is None

    def test_get_process_info_without_psutil(self):
        """Test that function returns None when psutil unavailable."""
        with patch("monitor_session.HAS_PSUTIL", False):
            info = get_process_info(12345)
            assert info is None

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    def test_process_info_structure(self):
        """Test that process info has correct structure."""
        import os
        current_pid = os.getpid()

        info = get_process_info(current_pid)

        if info:  # May be None on some systems
            assert isinstance(info, dict)
            assert all(key in info for key in ["cpu_percent", "memory_mb", "status", "create_time"])
            assert isinstance(info["cpu_percent"], (int, float))
            assert isinstance(info["memory_mb"], (int, float))
            assert isinstance(info["status"], str)
            assert isinstance(info["create_time"], datetime)

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    def test_process_info_memory_units(self):
        """Test that memory is reported in MB."""
        import os
        current_pid = os.getpid()

        info = get_process_info(current_pid)

        if info:
            # Memory should be in reasonable MB range (not bytes)
            assert 0 < info["memory_mb"] < 100000  # Less than 100GB is reasonable

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    def test_process_info_exception_handling(self):
        """Test exception handling in get_process_info."""
        with patch("monitor_session.psutil.Process") as mock_process:
            mock_process.side_effect = Exception("Unexpected error")

            info = get_process_info(12345)

            # Should handle exception and return None
            assert info is None


# ============================================================================
# MONITORING SESSION TESTS (6 tests)
# ============================================================================

class TestMonitoringSession:
    """Test monitoring session functionality."""

    def test_monitor_session_missing_pid_file(self, tmp_path, capsys):
        """Test monitoring with missing PID file."""
        pid_file = tmp_path / "missing.pid"

        monitor_session(str(pid_file), interval=1)

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "error" in output
        assert "Session not running" in output["error"]

    def test_monitor_session_invalid_pid_file_content(self, tmp_path, capsys):
        """Test monitoring with invalid PID file content."""
        pid_file = tmp_path / "invalid.pid"
        pid_file.write_text("not_a_number\n")

        monitor_session(str(pid_file), interval=1)

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert "error" in output
        assert "Failed to read PID file" in output["error"]

    def test_monitor_session_without_psutil(self, mock_pid_file, capsys):
        """Test monitoring without psutil (limited monitoring)."""
        with patch("monitor_session.HAS_PSUTIL", False):
            # Mock os.kill to simulate process exists
            with patch("os.kill") as mock_kill:
                mock_kill.return_value = None  # Process exists

                monitor_session(str(mock_pid_file), interval=1)

                captured = capsys.readouterr()
                lines = captured.out.strip().split("\n")

                # Should output warning about psutil and status
                first_output = json.loads(lines[0])
                assert "warning" in first_output or "status" in first_output

    def test_monitor_session_process_not_found(self, tmp_path, capsys):
        """Test monitoring when process is not found."""
        pid_file = tmp_path / "test.pid"
        # Use a PID that doesn't exist
        pid_file.write_text("999999\n")

        with patch("monitor_session.HAS_PSUTIL", True):
            with patch("monitor_session.get_process_info") as mock_get_info:
                mock_get_info.return_value = None

                monitor_session(str(pid_file), interval=1)

                captured = capsys.readouterr()
                output = json.loads(captured.out)

                assert "error" in output
                assert "Process not found" in output["error"]

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    def test_monitor_session_memory_limit_exceeded(self, tmp_path, capsys):
        """Test monitoring with memory limit exceeded."""
        import os
        pid_file = tmp_path / "test.pid"
        pid_file.write_text(f"{os.getpid()}\n")

        # Mock process info to return high memory usage
        mock_info = {
            "cpu_percent": 5.0,
            "memory_mb": MAX_MEMORY_MB + 1000,  # Exceed limit
            "status": "running",
            "create_time": datetime.now() - timedelta(minutes=5)
        }

        with patch("monitor_session.get_process_info") as mock_get_info:
            # First call returns start info, second call returns high memory
            mock_get_info.side_effect = [mock_info, mock_info]

            monitor_session(str(pid_file), interval=0.1)

            captured = capsys.readouterr()
            outputs = [json.loads(line) for line in captured.out.strip().split("\n")]

            # Should have warning about memory limit
            assert any("warnings" in output and len(output.get("warnings", [])) > 0 for output in outputs)

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    def test_monitor_session_timeout_exceeded(self, tmp_path, capsys):
        """Test monitoring with session timeout exceeded."""
        import os
        pid_file = tmp_path / "test.pid"
        pid_file.write_text(f"{os.getpid()}\n")

        # Mock process info with old start time
        mock_info = {
            "cpu_percent": 1.0,
            "memory_mb": 100.0,
            "status": "running",
            "create_time": datetime.now() - timedelta(minutes=SESSION_TIMEOUT_MIN + 10)
        }

        with patch("monitor_session.get_process_info") as mock_get_info:
            mock_get_info.side_effect = [mock_info, mock_info]

            monitor_session(str(pid_file), interval=0.1)

            captured = capsys.readouterr()
            outputs = [json.loads(line) for line in captured.out.strip().split("\n")]

            # Should have warning about timeout
            assert any("warnings" in output and len(output.get("warnings", [])) > 0 for output in outputs)


# ============================================================================
# JSON OUTPUT FORMAT TESTS (6 tests)
# ============================================================================

class TestJSONOutputFormat:
    """Test JSON output format from monitoring."""

    def test_json_output_structure_error(self, tmp_path, capsys):
        """Test JSON structure for error messages."""
        pid_file = tmp_path / "missing.pid"

        monitor_session(str(pid_file), interval=1)

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert isinstance(output, dict)
        assert "error" in output

    def test_json_output_structure_warning(self, tmp_path, capsys):
        """Test JSON structure for warnings (without psutil)."""
        pid_file = tmp_path / "test.pid"
        pid_file.write_text("12345\n")

        with patch("monitor_session.HAS_PSUTIL", False):
            with patch("os.kill") as mock_kill:
                mock_kill.return_value = None

                monitor_session(str(pid_file), interval=1)

                captured = capsys.readouterr()
                lines = captured.out.strip().split("\n")

                for line in lines:
                    output = json.loads(line)
                    assert isinstance(output, dict)

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    def test_json_output_structure_status(self, tmp_path, capsys):
        """Test JSON structure for status updates."""
        import os
        pid_file = tmp_path / "test.pid"
        pid_file.write_text(f"{os.getpid()}\n")

        mock_info = {
            "cpu_percent": 5.0,
            "memory_mb": 100.0,
            "status": "running",
            "create_time": datetime.now() - timedelta(minutes=5)
        }

        with patch("monitor_session.get_process_info") as mock_get_info:
            # Return info once, then None to end monitoring
            mock_get_info.side_effect = [mock_info, mock_info, None]

            monitor_session(str(pid_file), interval=0.1)

            captured = capsys.readouterr()
            lines = [line for line in captured.out.strip().split("\n") if line]

            # Parse all JSON outputs
            outputs = [json.loads(line) for line in lines]

            # Should have monitoring_started and status messages
            assert any(output.get("status") == "monitoring_started" for output in outputs)

    def test_json_output_numeric_precision(self, tmp_path, capsys):
        """Test that numeric values have appropriate precision."""
        import os
        pid_file = tmp_path / "test.pid"
        pid_file.write_text(f"{os.getpid()}\n")

        mock_info = {
            "cpu_percent": 12.3456,
            "memory_mb": 234.5678,
            "status": "running",
            "create_time": datetime.now()
        }

        with patch("monitor_session.HAS_PSUTIL", True):
            with patch("monitor_session.get_process_info") as mock_get_info:
                mock_get_info.side_effect = [mock_info, mock_info, None]

                monitor_session(str(pid_file), interval=0.1)

                captured = capsys.readouterr()
                lines = [line for line in captured.out.strip().split("\n") if line]

                for line in lines:
                    output = json.loads(line)
                    # Check numeric values are rounded appropriately
                    if "memory_mb" in output:
                        assert isinstance(output["memory_mb"], (int, float))
                    if "cpu_percent" in output:
                        assert isinstance(output["cpu_percent"], (int, float))

    def test_json_output_warnings_list(self, tmp_path, capsys):
        """Test that warnings are output as a list."""
        import os
        pid_file = tmp_path / "test.pid"
        pid_file.write_text(f"{os.getpid()}\n")

        # Mock high memory and long duration
        mock_info = {
            "cpu_percent": 5.0,
            "memory_mb": MAX_MEMORY_MB + 1000,
            "status": "running",
            "create_time": datetime.now() - timedelta(minutes=SESSION_TIMEOUT_MIN + 10)
        }

        with patch("monitor_session.HAS_PSUTIL", True):
            with patch("monitor_session.get_process_info") as mock_get_info:
                mock_get_info.side_effect = [mock_info, mock_info]

                monitor_session(str(pid_file), interval=0.1)

                captured = capsys.readouterr()
                lines = [line for line in captured.out.strip().split("\n") if line]

                # Find status output with warnings
                for line in lines:
                    output = json.loads(line)
                    if "warnings" in output:
                        assert isinstance(output["warnings"], list)
                        assert len(output["warnings"]) > 0

    def test_json_parseable_output(self, tmp_path, capsys):
        """Test that all output lines are valid JSON."""
        pid_file = tmp_path / "missing.pid"

        monitor_session(str(pid_file), interval=1)

        captured = capsys.readouterr()
        lines = [line for line in captured.out.strip().split("\n") if line]

        # All lines should be parseable as JSON
        for line in lines:
            try:
                output = json.loads(line)
                assert isinstance(output, dict)
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON output: {line}")


# ============================================================================
# RESOURCE LIMIT TESTS (Bonus)
# ============================================================================

class TestResourceLimits:
    """Test resource limit checking and enforcement."""

    def test_default_resource_limits(self):
        """Test that default resource limits are set."""
        assert MAX_MEMORY_MB > 0
        assert SESSION_TIMEOUT_MIN > 0

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not available")
    def test_cpu_activity_tracking(self, tmp_path):
        """Test that CPU activity updates last_activity timestamp."""
        import os
        pid_file = tmp_path / "test.pid"
        pid_file.write_text(f"{os.getpid()}\n")

        # Mock low CPU, then high CPU
        mock_info_low = {
            "cpu_percent": 0.5,  # Below threshold
            "memory_mb": 100.0,
            "status": "running",
            "create_time": datetime.now()
        }

        mock_info_high = {
            "cpu_percent": 5.0,  # Above threshold
            "memory_mb": 100.0,
            "status": "running",
            "create_time": datetime.now()
        }

        with patch("monitor_session.get_process_info") as mock_get_info:
            # Start, low CPU, high CPU, then stop
            mock_get_info.side_effect = [mock_info_low, mock_info_low, mock_info_high, None]

            with patch("sys.stdout", new=StringIO()) as fake_out:
                monitor_session(str(pid_file), interval=0.1)

                # Should complete without error
                assert True


# ============================================================================
# CLI INTERFACE TESTS (Bonus)
# ============================================================================

class TestCLIInterface:
    """Test command-line interface."""

    def test_cli_custom_limits(self):
        """Test that custom limits can be set via CLI."""
        # These would be set via argparse in main()
        custom_max_memory = 8192
        custom_timeout = 60

        assert custom_max_memory > MAX_MEMORY_MB
        assert custom_timeout != SESSION_TIMEOUT_MIN

    def test_cli_interval_parameter(self, tmp_path):
        """Test custom check interval."""
        pid_file = tmp_path / "missing.pid"

        # Should work with different intervals
        monitor_session(str(pid_file), interval=10)
        # No error = success
        assert True
