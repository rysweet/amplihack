"""
Integration tests for logging and metrics.

Tests log file creation, metrics tracking, and log rotation.
"""

import json

import pytest


def test_integ_log_001_log_file_created_and_populated(captured_subprocess, temp_project_root):
    """INTEG-LOG-001: Log file created and populated."""
    input_data = {"session_id": "test"}

    log_file = temp_project_root / ".claude/runtime/logs/stop.log"

    # Execute hook multiple times
    for i in range(3):
        result = captured_subprocess(input_data, lock_active=(i % 2 == 0))
        assert result.returncode == 0

    # Expected: Log file contains entries for each execution
    assert log_file.exists()

    log_content = log_file.read_text()

    # Should have multiple "stop hook starting" entries
    assert log_content.count("stop hook starting") >= 3

    # Should have completion messages
    assert "stop hook completed successfully" in log_content

    # Should have timestamps
    assert "[" in log_content  # Timestamp format starts with [
    assert "T" in log_content  # ISO timestamp contains T


def test_integ_log_002_metrics_file_created_and_populated(captured_subprocess, temp_project_root):
    """INTEG-LOG-002: Metrics file created and populated."""
    input_data = {"session_id": "test"}

    metrics_file = temp_project_root / ".claude/runtime/metrics/stop_metrics.jsonl"

    # Execute hook with lock active (triggers metric)
    result = captured_subprocess(input_data, lock_active=True)
    assert result.returncode == 0

    # Expected: Metrics file contains "lock_blocks" entry
    assert metrics_file.exists()

    metrics_content = metrics_file.read_text()

    # Should contain lock_blocks metric
    assert "lock_blocks" in metrics_content
    assert '"value": 1' in metrics_content
    assert '"hook": "stop"' in metrics_content

    # Should be valid JSON lines
    for line in metrics_content.strip().split("\n"):
        if line:
            metric = json.loads(line)
            assert "timestamp" in metric
            assert "metric" in metric
            assert "value" in metric
            assert "hook" in metric


@pytest.mark.slow
def test_integ_log_003_log_rotation_when_file_exceeds_10mb(stop_hook, temp_project_root):
    """INTEG-LOG-003: Log rotation when file exceeds 10MB."""
    log_file = temp_project_root / ".claude/runtime/logs/stop.log"

    # Create a log file > 10MB
    large_log = "x" * (11 * 1024 * 1024)  # 11 MB
    log_file.write_text(large_log)

    # Trigger a log write
    stop_hook.log("Test message after rotation")

    # Expected: Log file rotated with timestamp backup
    log_dir = temp_project_root / ".claude/runtime/logs"
    log_files = list(log_dir.glob("stop.*.log"))

    # Should have a backup file
    assert len(log_files) >= 1

    # New log file should be smaller
    assert log_file.stat().st_size < 1024  # Small, just has test message


@pytest.mark.slow
def test_integ_log_004_concurrent_logging_from_multiple_hook_executions(
    captured_subprocess, temp_project_root
):
    """INTEG-LOG-004: Concurrent logging from multiple hook executions."""
    import concurrent.futures

    input_data = {"session_id": "concurrent"}

    log_file = temp_project_root / ".claude/runtime/logs/stop.log"

    # Run 10 hooks simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(captured_subprocess, input_data, lock_active=(i % 2 == 0))
            for i in range(10)
        ]

        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Expected: All log entries present, no corruption
    assert all(r.returncode == 0 for r in results)

    log_content = log_file.read_text()

    # Should have at least 10 "stop hook starting" entries
    assert log_content.count("stop hook starting") >= 10

    # File should be readable (not corrupted)
    lines = log_content.split("\n")
    for line in lines:
        if line.strip():
            # Each line should start with timestamp
            assert line.startswith("[") or line.startswith(" ")  # Continuation lines
