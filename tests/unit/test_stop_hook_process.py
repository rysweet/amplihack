"""
Unit tests for StopHook.process() method.

Tests the core processing logic including:
- Lock detection
- Permission error handling
- Input validation
- Output structure validation
- Metrics tracking
"""


def test_unit_process_001_no_lock_file_exists(stop_hook):
    """UNIT-PROCESS-001: No lock file exists."""
    # Input
    input_data = {"session_id": "test_123", "hook_event_name": "stop"}

    # Expected: Returns empty dict, logs "No lock active - allowing stop"
    result = stop_hook.process(input_data)

    assert result == {}

    # Verify log contains expected message
    assert stop_hook.log_file.exists()
    log_content = stop_hook.log_file.read_text()
    assert "No lock active - allowing stop" in log_content


def test_unit_process_002_lock_file_exists_with_default_prompt(stop_hook, active_lock):
    """UNIT-PROCESS-002: Lock file exists with default prompt."""
    # Input
    input_data = {"session_id": "test_123", "hook_event_name": "stop"}

    # Expected: Returns block decision with default prompt
    result = stop_hook.process(input_data)

    assert result == {
        "decision": "block",
        "reason": (
            "we must keep pursuing the user's objective and must not stop the turn - "
            "look for any additional TODOs, next steps, or unfinished work and pursue it "
            "diligently in as many parallel tasks as you can"
        ),
    }

    # Verify log contains expected message
    log_content = stop_hook.log_file.read_text()
    assert "Lock is active - blocking stop to continue working" in log_content


def test_unit_process_003_lock_file_exists_with_custom_prompt(
    stop_hook, active_lock, custom_prompt
):
    """UNIT-PROCESS-003: Lock file exists with custom prompt."""
    # Setup custom prompt
    custom_prompt("Custom continuation message")

    # Input
    input_data = {"session_id": "test_123", "hook_event_name": "stop"}

    # Expected: Returns block decision with custom prompt
    result = stop_hook.process(input_data)

    assert result == {"decision": "block", "reason": "Custom continuation message"}


def test_unit_process_004_permission_error_accessing_lock_file(stop_hook, monkeypatch):
    """UNIT-PROCESS-004: Permission error accessing lock file."""

    # Mock lock_flag.exists() to raise PermissionError
    def mock_exists():
        raise PermissionError("Access denied")

    monkeypatch.setattr(stop_hook.lock_flag, "exists", mock_exists)

    # Input
    input_data = {"session_id": "test_123", "hook_event_name": "stop"}

    # Expected: Returns empty dict (fail-safe behavior), logs warning
    result = stop_hook.process(input_data)

    assert result == {}

    # Verify warning was logged
    log_content = stop_hook.log_file.read_text()
    assert "Cannot access lock file" in log_content
    assert "WARNING" in log_content


def test_unit_process_005_oserror_accessing_lock_file(stop_hook, monkeypatch):
    """UNIT-PROCESS-005: OSError accessing lock file."""

    # Mock lock_flag.exists() to raise OSError
    def mock_exists():
        raise OSError("I/O error")

    monkeypatch.setattr(stop_hook.lock_flag, "exists", mock_exists)

    # Input
    input_data = {"session_id": "test_123", "hook_event_name": "stop"}

    # Expected: Returns empty dict (fail-safe behavior), logs warning
    result = stop_hook.process(input_data)

    assert result == {}

    # Verify warning was logged
    log_content = stop_hook.log_file.read_text()
    assert "Cannot access lock file" in log_content
    assert "WARNING" in log_content


def test_unit_process_006_empty_input_data(stop_hook):
    """UNIT-PROCESS-006: Empty input data."""
    # Input
    input_data = {}

    # Expected: Returns empty dict without errors
    result = stop_hook.process(input_data)

    assert result == {}


def test_unit_process_007_input_with_extra_fields(stop_hook):
    """UNIT-PROCESS-007: Input with extra fields."""
    # Input with extra field
    input_data = {"session_id": "test_123", "hook_event_name": "stop", "extra": "field"}

    # Expected: Ignores extra fields, returns based on lock state
    result = stop_hook.process(input_data)

    # No lock = empty dict
    assert result == {}


def test_unit_process_008_lock_file_created_during_execution(stop_hook):
    """UNIT-PROCESS-008: Lock file created during execution."""
    # Input
    input_data = {"session_id": "test_123", "hook_event_name": "stop"}

    # Check lock state atomically - first call without lock
    result1 = stop_hook.process(input_data)
    assert result1 == {}

    # Create lock
    stop_hook.lock_flag.touch()

    # Second call with lock
    result2 = stop_hook.process(input_data)
    assert result2["decision"] == "block"
    assert "reason" in result2


def test_unit_process_009_lock_file_deleted_during_execution(stop_hook, active_lock):
    """UNIT-PROCESS-009: Lock file deleted during execution."""
    # Input
    input_data = {"session_id": "test_123", "hook_event_name": "stop"}

    # First call with lock active
    result1 = stop_hook.process(input_data)
    assert result1["decision"] == "block"

    # Delete lock
    stop_hook.lock_flag.unlink()

    # Second call without lock
    result2 = stop_hook.process(input_data)
    assert result2 == {}


def test_unit_process_010_output_structure_validation_no_extra_fields(stop_hook, active_lock):
    """UNIT-PROCESS-010: Output structure validation - no extra fields."""
    # Input
    input_data = {"session_id": "test_123", "hook_event_name": "stop"}

    # Get result
    result = stop_hook.process(input_data)

    # Expected: Output only contains "decision" and "reason" (no "continue" or other fields)
    assert set(result.keys()) == {"decision", "reason"}
    assert "continue" not in result


def test_unit_process_011_output_structure_validation_field_types(stop_hook, active_lock):
    """UNIT-PROCESS-011: Output structure validation - field types."""
    # Input
    input_data = {"session_id": "test_123", "hook_event_name": "stop"}

    # Get result
    result = stop_hook.process(input_data)

    # Expected: "decision" is string, "reason" is string
    assert isinstance(result["decision"], str)
    assert isinstance(result["reason"], str)
    assert result["decision"] == "block"


def test_unit_process_012_metrics_saved_on_lock_block(stop_hook, active_lock):
    """UNIT-PROCESS-012: Metrics saved on lock block."""
    # Input
    input_data = {"session_id": "test_123", "hook_event_name": "stop"}

    # Get result
    result = stop_hook.process(input_data)

    # Expected: save_metric("lock_blocks", 1) was called
    assert result["decision"] == "block"

    # Verify metrics file was created
    metrics_file = stop_hook.metrics_dir / "stop_metrics.jsonl"
    assert metrics_file.exists()

    # Verify metrics content
    metrics_content = metrics_file.read_text()
    assert "lock_blocks" in metrics_content
    assert '"value": 1' in metrics_content
