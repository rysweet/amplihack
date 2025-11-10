"""
Unit tests for path and file system operations.

Tests path resolution for lock file, continuation prompt, and logs.
"""


def test_unit_path_001_lock_file_path_resolution(stop_hook):
    """UNIT-PATH-001: Lock file path resolution."""
    # Expected: Path is .claude/runtime/locks/.lock_active
    expected_path = stop_hook.project_root / ".claude/runtime/locks/.lock_active"

    assert stop_hook.lock_flag == expected_path
    assert ".claude" in str(stop_hook.lock_flag)
    assert "runtime" in str(stop_hook.lock_flag)
    assert "locks" in str(stop_hook.lock_flag)
    assert ".lock_active" in str(stop_hook.lock_flag)


def test_unit_path_002_continuation_prompt_file_path_resolution(stop_hook):
    """UNIT-PATH-002: Continuation prompt file path resolution."""
    # Expected: Path is .claude/runtime/locks/.continuation_prompt
    expected_path = stop_hook.project_root / ".claude/runtime/locks/.continuation_prompt"

    assert stop_hook.continuation_prompt_file == expected_path
    assert ".claude" in str(stop_hook.continuation_prompt_file)
    assert "runtime" in str(stop_hook.continuation_prompt_file)
    assert "locks" in str(stop_hook.continuation_prompt_file)
    assert ".continuation_prompt" in str(stop_hook.continuation_prompt_file)


def test_unit_path_003_log_file_path_resolution(stop_hook):
    """UNIT-PATH-003: Log file path resolution."""
    # Expected: Path is .claude/runtime/logs/stop.log
    expected_path = stop_hook.project_root / ".claude/runtime/logs/stop.log"

    assert stop_hook.log_file == expected_path
    assert ".claude" in str(stop_hook.log_file)
    assert "runtime" in str(stop_hook.log_file)
    assert "logs" in str(stop_hook.log_file)
    assert "stop.log" in str(stop_hook.log_file)
