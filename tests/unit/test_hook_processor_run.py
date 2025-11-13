"""
Unit tests for HookProcessor.run() method.

Tests the hook lifecycle including:
- Input reading from stdin
- Output writing to stdout
- Error handling
- Logging functionality
- Shutdown flag handling
"""

import json
import os
from io import StringIO
from unittest.mock import patch


def test_unit_run_001_valid_json_input_to_stdout_output(stop_hook):
    """UNIT-RUN-001: Valid JSON input to stdout output."""
    # Input
    input_data = {"session_id": "test"}
    json_input = json.dumps(input_data)

    # Mock stdin and stdout
    with patch("sys.stdin", StringIO(json_input)), patch(
        "sys.stdout", new_callable=StringIO
    ) as mock_stdout:
        # Run the hook
        stop_hook.run()

        # Get output
        output = mock_stdout.getvalue()

        # Expected: Valid JSON written to stdout
        output_data = json.loads(output)
        assert isinstance(output_data, dict)

    # Verify log shows successful completion
    log_content = stop_hook.log_file.read_text()
    assert "stop hook completed successfully" in log_content


def test_unit_run_002_empty_json_input(stop_hook):
    """UNIT-RUN-002: Empty JSON input."""
    # Input
    json_input = "{}"

    # Mock stdin and stdout
    with patch("sys.stdin", StringIO(json_input)), patch(
        "sys.stdout", new_callable=StringIO
    ) as mock_stdout:
        # Run the hook
        stop_hook.run()

        # Get output
        output = mock_stdout.getvalue()

        # Expected: Valid JSON output
        output_data = json.loads(output)
        assert isinstance(output_data, dict)


def test_unit_run_003_invalid_json_input(stop_hook):
    """UNIT-RUN-003: Invalid JSON input."""
    # Input
    json_input = "{invalid json}"

    # Mock stdin and stdout
    with patch("sys.stdin", StringIO(json_input)), patch(
        "sys.stdout", new_callable=StringIO
    ) as mock_stdout:
        # Run the hook
        stop_hook.run()

        # Get output
        output = mock_stdout.getvalue()

        # Expected: Error response in JSON format
        output_data = json.loads(output)
        assert "error" in output_data
        assert "Invalid JSON input" in output_data["error"]

    # Verify error was logged
    log_content = stop_hook.log_file.read_text()
    assert "Invalid JSON input" in log_content
    assert "ERROR" in log_content


def test_unit_run_004_empty_stdin_input(stop_hook):
    """UNIT-RUN-004: Empty stdin input."""
    # Input: empty string
    json_input = ""

    # Mock stdin and stdout
    with patch("sys.stdin", StringIO(json_input)), patch(
        "sys.stdout", new_callable=StringIO
    ) as mock_stdout:
        # Run the hook
        stop_hook.run()

        # Get output
        output = mock_stdout.getvalue()

        # Expected: Valid JSON output (empty dict)
        output_data = json.loads(output)
        assert output_data == {}


def test_unit_run_005_process_method_returns_none(stop_hook):
    """UNIT-RUN-005: Process method returns None."""
    # Mock process() to return None
    with patch.object(stop_hook, "process", return_value=None):
        # Input
        json_input = '{"session_id": "test"}'

        # Mock stdin and stdout
        with patch("sys.stdin", StringIO(json_input)), patch(
            "sys.stdout", new_callable=StringIO
        ) as mock_stdout:
            # Run the hook
            stop_hook.run()

            # Get output
            output = mock_stdout.getvalue()

            # Expected: Converts None to empty dict
            output_data = json.loads(output)
            assert output_data == {}


def test_unit_run_006_process_method_returns_non_dict(stop_hook):
    """UNIT-RUN-006: Process method returns non-dict."""
    # Mock process() to return a string
    with patch.object(stop_hook, "process", return_value="string"):
        # Input
        json_input = '{"session_id": "test"}'

        # Mock stdin and stdout
        with patch("sys.stdin", StringIO(json_input)), patch(
            "sys.stdout", new_callable=StringIO
        ) as mock_stdout:
            # Run the hook
            stop_hook.run()

            # Get output
            output = mock_stdout.getvalue()

            # Expected: Wraps non-dict in dict
            output_data = json.loads(output)
            assert "result" in output_data
            assert output_data["result"] == "string"


def test_unit_run_007_process_method_raises_exception(stop_hook):
    """UNIT-RUN-007: Process method raises exception."""
    # Mock process() to raise RuntimeError
    with patch.object(stop_hook, "process", side_effect=RuntimeError("Test error")):
        # Input
        json_input = '{"session_id": "test"}'

        # Mock stdin and stdout (and stderr to avoid noise)
        with patch("sys.stdin", StringIO(json_input)), patch(
            "sys.stdout", new_callable=StringIO
        ) as mock_stdout, patch("sys.stderr", new_callable=StringIO):
            # Run the hook
            stop_hook.run()

            # Get output
            output = mock_stdout.getvalue()

            # Expected: Logs error, writes empty dict
            output_data = json.loads(output)
            assert output_data == {}

    # Verify error was logged
    log_content = stop_hook.log_file.read_text()
    assert "Error in stop: Test error" in log_content
    assert "ERROR" in log_content


def test_unit_run_008_logging_functionality(stop_hook):
    """UNIT-RUN-008: Logging functionality."""
    # Input
    json_input = '{"session_id": "test"}'

    # Mock stdin and stdout
    with patch("sys.stdin", StringIO(json_input)), patch("sys.stdout", new_callable=StringIO):
        # Run the hook
        stop_hook.run()

    # Expected: Log file contains timestamped entries
    assert stop_hook.log_file.exists()
    log_content = stop_hook.log_file.read_text()

    # Verify log structure
    assert "INFO:" in log_content
    assert "stop hook starting" in log_content
    assert "Received input with keys:" in log_content
    assert "stop hook completed successfully" in log_content

    # Verify timestamps are ISO format (contains T separator)
    lines = log_content.split("\n")
    for line in lines:
        if line.strip():
            # Should start with [timestamp] format
            assert line.startswith("[")
            assert "T" in line[:30]  # ISO timestamp in first 30 chars


def test_unit_run_009_shutdown_flag_skips_stdin_read(stop_hook):
    """UNIT-RUN-009: Shutdown flag prevents stdin read to avoid SystemExit race."""
    # Set the shutdown flag
    os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

    try:
        # Mock stdin with data (should NOT be read)
        json_input = '{"session_id": "test"}'

        # Mock stdin and stdout
        with patch("sys.stdin", StringIO(json_input)), patch(
            "sys.stdout", new_callable=StringIO
        ) as mock_stdout:
            # Run the hook
            stop_hook.run()

            # Get output
            output = mock_stdout.getvalue()

            # Expected: Empty dict returned (stdin was not read)
            output_data = json.loads(output)
            assert output_data == {}

        # Verify log shows shutdown was detected
        log_content = stop_hook.log_file.read_text()
        assert "Skipping stdin read during shutdown" in log_content
        assert "DEBUG" in log_content

    finally:
        # Clean up environment variable
        os.environ.pop("AMPLIHACK_SHUTDOWN_IN_PROGRESS", None)


def test_unit_run_010_no_shutdown_flag_reads_stdin_normally(stop_hook):
    """UNIT-RUN-010: Without shutdown flag, stdin is read normally."""
    # Ensure shutdown flag is NOT set
    os.environ.pop("AMPLIHACK_SHUTDOWN_IN_PROGRESS", None)

    # Input
    input_data = {"session_id": "test"}
    json_input = json.dumps(input_data)

    # Mock stdin and stdout
    with patch("sys.stdin", StringIO(json_input)), patch(
        "sys.stdout", new_callable=StringIO
    ) as mock_stdout:
        # Run the hook
        stop_hook.run()

        # Get output
        output = mock_stdout.getvalue()

        # Expected: Valid JSON output (stdin was read)
        output_data = json.loads(output)
        assert isinstance(output_data, dict)

    # Verify log shows normal operation
    log_content = stop_hook.log_file.read_text()
    assert "Received input with keys:" in log_content
    assert "Skipping stdin read during shutdown" not in log_content
