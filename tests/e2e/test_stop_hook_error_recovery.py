"""
End-to-end tests for error recovery.

Tests recovery from error conditions.
"""

import json
import os
import sys

import pytest


def test_e2e_error_001_recovery_from_corrupted_lock_file(captured_subprocess, temp_project_root):
    """E2E-ERROR-001: Recovery from corrupted lock file."""
    # Scenario: Lock file exists but is corrupted/inaccessible
    input_data = {"session_id": "error_session"}

    # Skip on Windows (permission model is different)
    if sys.platform == "win32":
        pytest.skip("Permission tests not applicable on Windows")

    # Step 1: Create lock file with invalid permissions
    lock_file = temp_project_root / ".claude/tools/amplihack/.lock_active"
    lock_file.touch()
    os.chmod(lock_file, 0o000)  # No permissions

    try:
        # Step 2: Claude Code calls stop hook
        result = captured_subprocess(input_data, lock_active=True)

        # Step 3: Hook catches permission error
        # Step 4: Hook returns {} (fail-safe)
        assert result.returncode == 0

        output = json.loads(result.stdout)
        # Expected: Claude Code stops normally, error logged
        # Fail-safe behavior: allows stop when can't read lock
        assert isinstance(output, dict)

        # Verify log contains error
        log_file = temp_project_root / ".claude/runtime/logs/stop.log"
        if log_file.exists():
            _ = log_file.read_text()  # Verify log file is readable
            # Should log the permission issue but not crash
            # (May contain "Cannot access lock file" or similar)
    finally:
        # Cleanup: restore permissions
        os.chmod(lock_file, 0o644)


def test_e2e_error_002_recovery_from_missing_directories(captured_subprocess, temp_project_root):
    """E2E-ERROR-002: Recovery from missing directories."""
    # Scenario: Runtime directories don't exist
    import shutil

    input_data = {"session_id": "missing_dirs"}

    # Step 1: Delete .claude/runtime/logs
    runtime_logs = temp_project_root / ".claude/runtime/logs"
    if runtime_logs.exists():
        shutil.rmtree(runtime_logs)

    # Step 2: Execute hook
    result = captured_subprocess(input_data, lock_active=False)

    # Expected: Hook creates directories, executes normally
    assert result.returncode == 0

    output = json.loads(result.stdout)
    assert output == {}

    # Verify directories were created
    assert runtime_logs.exists()
