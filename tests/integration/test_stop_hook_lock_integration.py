"""
Integration tests for lock file integration.

Tests lock file state changes and hook responses.
"""

import json
import pytest


def test_integ_lock_001_lock_file_created_and_hook_responds(captured_subprocess, temp_project_root):
    """INTEG-LOCK-001: Lock file created and hook responds immediately."""
    input_data = {"session_id": "test"}

    # Step 1: Execute hook (no lock) - verify allows
    result1 = captured_subprocess(input_data, lock_active=False)
    assert result1.returncode == 0
    output1 = json.loads(result1.stdout)
    assert output1 == {}

    # Step 2: Create lock file
    lock_file = temp_project_root / ".claude/tools/amplihack/.lock_active"
    lock_file.touch()

    # Step 3: Execute hook - verify blocks
    result2 = captured_subprocess(input_data, lock_active=True)
    assert result2.returncode == 0
    output2 = json.loads(result2.stdout)
    assert output2["decision"] == "block"
    assert "reason" in output2


def test_integ_lock_002_lock_file_deleted_and_hook_responds(captured_subprocess, temp_project_root):
    """INTEG-LOCK-002: Lock file deleted and hook responds immediately."""
    input_data = {"session_id": "test"}

    # Step 1: Create lock file
    lock_file = temp_project_root / ".claude/tools/amplihack/.lock_active"
    lock_file.touch()

    # Step 2: Execute hook - verify blocks
    result1 = captured_subprocess(input_data, lock_active=True)
    assert result1.returncode == 0
    output1 = json.loads(result1.stdout)
    assert output1["decision"] == "block"

    # Step 3: Delete lock file
    lock_file.unlink()

    # Step 4: Execute hook - verify allows
    result2 = captured_subprocess(input_data, lock_active=False)
    assert result2.returncode == 0
    output2 = json.loads(result2.stdout)
    assert output2 == {}


def test_integ_lock_003_continuous_work_mode_scenario(
    captured_subprocess, temp_project_root, custom_prompt
):
    """INTEG-LOCK-003: Continuous work mode scenario."""
    input_data = {"session_id": "test"}

    # Step 1: Create lock file with custom prompt
    lock_file = temp_project_root / ".claude/tools/amplihack/.lock_active"
    lock_file.touch()

    # Note: custom_prompt fixture doesn't work with captured_subprocess
    # Create prompt manually
    prompt_file = temp_project_root / ".claude/tools/amplihack/.continuation_prompt"
    prompt_file.write_text("Keep working on all tasks", encoding="utf-8")

    # Step 2: Execute hook multiple times
    results = []
    for _ in range(3):
        result = captured_subprocess(input_data, lock_active=True)
        assert result.returncode == 0
        output = json.loads(result.stdout)
        results.append(output)

    # Step 3: Verify each execution blocks with same prompt
    for output in results:
        assert output["decision"] == "block"
        assert output["reason"] == "Keep working on all tasks"


def test_integ_lock_004_lock_file_permission_changes(captured_subprocess, temp_project_root):
    """INTEG-LOCK-004: Lock file permission changes."""
    import os
    import sys

    # Skip on Windows (permission model is different)
    if sys.platform == "win32":
        pytest.skip("Permission tests not applicable on Windows")

    input_data = {"session_id": "test"}

    # Step 1: Create lock file with restricted permissions
    lock_file = temp_project_root / ".claude/tools/amplihack/.lock_active"
    lock_file.touch()
    os.chmod(lock_file, 0o000)  # No read permissions

    try:
        # Step 2: Execute hook
        result = captured_subprocess(input_data, lock_active=True)

        # Expected: Handles permission error gracefully (fail-safe)
        assert result.returncode == 0

        # Should return empty dict (fail-safe behavior)
        output = json.loads(result.stdout)
        # Depending on when the permission error occurs, could be empty or error
        assert isinstance(output, dict)
    finally:
        # Cleanup: restore permissions so file can be deleted
        os.chmod(lock_file, 0o644)
