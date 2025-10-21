"""
End-to-end tests for complete workflows.

Tests real-world scenarios from user perspective.
"""

import json


def test_e2e_workflow_001_standard_stop_without_lock(captured_subprocess, temp_project_root):
    """E2E-WORKFLOW-001: Standard stop without lock (user stops session)."""
    # Scenario: User completes task and stops
    input_data = {"session_id": "user_session"}

    # Step 1: No lock file exists
    lock_file = temp_project_root / ".claude/tools/amplihack/.lock_active"
    assert not lock_file.exists()

    # Step 2: Claude Code calls stop hook
    result = captured_subprocess(input_data, lock_active=False)

    # Step 3: Hook returns {}
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output == {}

    # Step 4: Claude Code stops normally
    # Expected: Clean stop, no messages to user
    # Verify no error output
    # Note: stderr may contain INFO logs but not errors
    if result.stderr:
        assert "ERROR" not in result.stderr.upper()
        assert "HOOK ERROR" not in result.stderr


def test_e2e_workflow_002_continuous_work_mode_active(captured_subprocess, temp_project_root):
    """E2E-WORKFLOW-002: Continuous work mode active (hook blocks stop)."""
    # Scenario: User enables continuous work, tries to stop
    input_data = {"session_id": "continuous_session"}

    # Step 1: Lock file created (continuous work enabled)
    lock_file = temp_project_root / ".claude/tools/amplihack/.lock_active"
    lock_file.touch()

    # Step 2: Custom prompt set to "Complete all TODOs"
    prompt_file = temp_project_root / ".claude/tools/amplihack/.continuation_prompt"
    prompt_file.write_text("Complete all TODOs", encoding="utf-8")

    # Step 3: Claude Code calls stop hook
    result = captured_subprocess(input_data, lock_active=True)

    # Step 4: Hook returns block decision with custom prompt
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["decision"] == "block"
    assert output["reason"] == "Complete all TODOs"

    # Step 5: Claude Code continues with prompt
    # Expected: Claude continues working, user sees prompt
    # Verify the prompt is what user set
    assert output["reason"] == "Complete all TODOs"


def test_e2e_workflow_003_continuous_work_mode_disabled(captured_subprocess, temp_project_root):
    """E2E-WORKFLOW-003: Continuous work mode disabled (user regains control)."""
    # Scenario: User disables continuous work after enabling
    input_data = {"session_id": "toggle_session"}

    # Step 1: Lock file exists
    lock_file = temp_project_root / ".claude/tools/amplihack/.lock_active"
    lock_file.touch()

    # Step 2: Hook blocks stop (continuous work happening)
    result1 = captured_subprocess(input_data, lock_active=True)
    assert result1.returncode == 0
    output1 = json.loads(result1.stdout)
    assert output1["decision"] == "block"

    # Step 3: User disables mode (deletes lock file)
    lock_file.unlink()

    # Step 4: Claude Code calls stop hook
    result2 = captured_subprocess(input_data, lock_active=False)

    # Step 5: Hook returns {}
    assert result2.returncode == 0
    output2 = json.loads(result2.stdout)
    assert output2 == {}

    # Step 6: Claude Code stops
    # Expected: Clean stop after mode disabled
    if result2.stderr:
        assert "ERROR" not in result2.stderr.upper()
