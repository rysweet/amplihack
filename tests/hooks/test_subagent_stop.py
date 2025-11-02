"""
Unit and integration tests for subagent_stop hook.

Tests subagent detection, metric logging, and non-interference with stop behavior.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def subagent_stop_hook(temp_project_root):
    """Create SubagentStopHook instance with test paths.

    Args:
        temp_project_root: Temporary project root fixture

    Returns:
        SubagentStopHook: Configured hook instance for testing
    """
    # Import here to avoid circular import issues
    sys.path.insert(
        0, str(Path(__file__).parent.parent.parent / ".claude/tools/amplihack/hooks")
    )
    from subagent_stop import SubagentStopHook

    hook = SubagentStopHook()
    hook.project_root = temp_project_root
    hook.log_dir = temp_project_root / ".claude/runtime/logs"
    hook.metrics_dir = temp_project_root / ".claude/runtime/metrics"
    hook.analysis_dir = temp_project_root / ".claude/runtime/analysis"
    hook.log_file = hook.log_dir / "subagent_stop.log"

    return hook


@pytest.fixture
def captured_subagent_subprocess(temp_project_root):
    """Run subagent_stop hook as subprocess and capture output.

    Args:
        temp_project_root: Temporary project root fixture

    Returns:
        callable: Function to run hook subprocess
    """
    # Path to the actual subagent_stop.py hook
    hook_script = (
        Path(__file__).parent.parent.parent / ".claude/tools/amplihack/hooks/subagent_stop.py"
    )

    def _run(
        input_data: dict, agent_env: str = None, extra_env: dict = None
    ) -> subprocess.CompletedProcess:
        """Run hook as subprocess with input.

        Args:
            input_data: JSON input to pass to hook
            agent_env: Value for CLAUDE_AGENT environment variable
            extra_env: Additional environment variables

        Returns:
            CompletedProcess with stdout, stderr, exit code
        """
        # Setup environment
        (temp_project_root / ".claude/tools/amplihack/hooks").mkdir(parents=True, exist_ok=True)

        # Prepare input
        json_input = json.dumps(input_data)

        # Set environment
        env = os.environ.copy()
        env["AMPLIHACK_PROJECT_ROOT"] = str(temp_project_root)

        if agent_env:
            env["CLAUDE_AGENT"] = agent_env

        if extra_env:
            env.update(extra_env)

        # Run subprocess
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json_input,
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(temp_project_root),
            env=env,
        )

        return result

    return _run


# =============================================================================
# Unit Tests - Subagent Detection
# =============================================================================


def test_unit_detect_env_variable(subagent_stop_hook):
    """UNIT-SUBAGENT-001: Detect subagent from CLAUDE_AGENT environment variable."""
    # Set environment variable
    os.environ["CLAUDE_AGENT"] = "architect"

    try:
        input_data = {"session_id": "test-session"}
        detection = subagent_stop_hook._detect_subagent_context(input_data)

        assert detection["is_subagent"] is True
        assert detection["agent_name"] == "architect"
        assert detection["detection_method"] == "env"
    finally:
        # Cleanup
        del os.environ["CLAUDE_AGENT"]


def test_unit_detect_session_id_prefix(subagent_stop_hook):
    """UNIT-SUBAGENT-002: Detect subagent from session_id with agent prefix."""
    input_data = {"session_id": "agent-builder-12345"}
    detection = subagent_stop_hook._detect_subagent_context(input_data)

    assert detection["is_subagent"] is True
    assert detection["agent_name"] == "agent-builder-12345"
    assert detection["detection_method"] == "session"


def test_unit_detect_session_id_subagent_prefix(subagent_stop_hook):
    """UNIT-SUBAGENT-003: Detect subagent from session_id with subagent prefix."""
    input_data = {"session_id": "subagent-reviewer-67890"}
    detection = subagent_stop_hook._detect_subagent_context(input_data)

    assert detection["is_subagent"] is True
    assert detection["agent_name"] == "subagent-reviewer-67890"
    assert detection["detection_method"] == "session"


def test_unit_detect_metadata_agent_name(subagent_stop_hook):
    """UNIT-SUBAGENT-004: Detect subagent from agent_name in input metadata."""
    input_data = {"session_id": "regular-session", "agent_name": "security"}
    detection = subagent_stop_hook._detect_subagent_context(input_data)

    assert detection["is_subagent"] is True
    assert detection["agent_name"] == "security"
    assert detection["detection_method"] == "metadata"


def test_unit_detect_metadata_is_subagent_flag(subagent_stop_hook):
    """UNIT-SUBAGENT-005: Detect subagent from is_subagent flag."""
    input_data = {"session_id": "regular-session", "is_subagent": True, "agent_name": "tester"}
    detection = subagent_stop_hook._detect_subagent_context(input_data)

    assert detection["is_subagent"] is True
    assert detection["agent_name"] == "tester"
    assert detection["detection_method"] == "metadata"


def test_unit_detect_no_subagent(subagent_stop_hook):
    """UNIT-SUBAGENT-006: No subagent detected in regular context."""
    input_data = {"session_id": "regular-session"}
    detection = subagent_stop_hook._detect_subagent_context(input_data)

    assert detection["is_subagent"] is False
    assert detection["agent_name"] is None
    assert detection["detection_method"] == "none"


# =============================================================================
# Unit Tests - Metric Extraction
# =============================================================================


def test_unit_extract_session_metrics(subagent_stop_hook):
    """UNIT-SUBAGENT-007: Extract session metrics from input data."""
    input_data = {
        "session_id": "test-session",
        "turn_count": 5,
        "tool_use_count": 15,
        "error_count": 2,
        "duration_seconds": 120.5,
    }

    metrics = subagent_stop_hook._extract_session_metrics(input_data)

    assert metrics["session_id"] == "test-session"
    assert metrics["turn_count"] == 5
    assert metrics["tool_use_count"] == 15
    assert metrics["error_count"] == 2
    assert metrics["duration_seconds"] == 120.5


def test_unit_extract_partial_metrics(subagent_stop_hook):
    """UNIT-SUBAGENT-008: Extract metrics with missing fields (defaults)."""
    input_data = {"session_id": "test-session"}

    metrics = subagent_stop_hook._extract_session_metrics(input_data)

    assert metrics["session_id"] == "test-session"
    assert metrics["turn_count"] == 0
    assert metrics["tool_use_count"] == 0
    assert metrics["error_count"] == 0
    assert metrics["duration_seconds"] is None


# =============================================================================
# Integration Tests - Process Method
# =============================================================================


def test_integ_process_subagent_logs_metrics(subagent_stop_hook):
    """INTEG-SUBAGENT-001: Processing subagent stop logs metrics."""
    input_data = {
        "session_id": "agent-architect-12345",
        "turn_count": 3,
        "tool_use_count": 10,
    }

    result = subagent_stop_hook.process(input_data)

    # Should return empty dict (no interference)
    assert result == {}

    # Check metrics file was created
    metrics_file = subagent_stop_hook.metrics_dir / "subagent_stop_metrics.jsonl"
    assert metrics_file.exists()

    # Read and verify metrics
    with open(metrics_file) as f:
        lines = f.readlines()
        assert len(lines) >= 2  # At least 2 metrics logged

        # Parse last two lines
        metric1 = json.loads(lines[-2])
        metric2 = json.loads(lines[-1])

        # One should be termination details, one should be count
        metrics = [metric1, metric2]
        termination = next(m for m in metrics if m["metric"] == "subagent_termination")
        count = next(m for m in metrics if m["metric"] == "subagent_stops")

        # Verify termination metric
        assert termination["value"]["agent_name"] == "agent-architect-12345"
        assert termination["value"]["turn_count"] == 3
        assert termination["value"]["tool_use_count"] == 10

        # Verify count metric
        assert count["value"] == 1
        assert count["metadata"]["agent_name"] == "agent-architect-12345"


def test_integ_process_regular_stop_no_metrics(subagent_stop_hook):
    """INTEG-SUBAGENT-002: Processing regular stop doesn't log metrics."""
    input_data = {"session_id": "regular-session"}

    result = subagent_stop_hook.process(input_data)

    # Should return empty dict
    assert result == {}

    # Check metrics file doesn't contain subagent metrics
    metrics_file = subagent_stop_hook.metrics_dir / "subagent_stop_metrics.jsonl"

    if metrics_file.exists():
        with open(metrics_file) as f:
            lines = f.readlines()
            # Should not contain any subagent metrics
            for line in lines:
                metric = json.loads(line)
                assert metric["metric"] not in ["subagent_termination", "subagent_stops"]


def test_integ_process_always_returns_empty_dict(subagent_stop_hook):
    """INTEG-SUBAGENT-003: Process always returns empty dict (never blocks)."""
    test_cases = [
        {"session_id": "agent-test"},  # Subagent
        {"session_id": "regular"},  # Regular
        {"agent_name": "builder"},  # Subagent via metadata
        {},  # Empty input
    ]

    for input_data in test_cases:
        result = subagent_stop_hook.process(input_data)
        assert result == {}, f"Failed for input: {input_data}"


# =============================================================================
# E2E Tests - Subprocess Execution
# =============================================================================


def test_e2e_subprocess_env_detection(captured_subagent_subprocess, temp_project_root):
    """E2E-SUBAGENT-001: Subprocess detects subagent from environment."""
    input_data = {"session_id": "test-session", "turn_count": 5}

    result = captured_subagent_subprocess(input_data, agent_env="architect")

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output == {}

    # Verify metrics were logged
    metrics_file = temp_project_root / ".claude/runtime/metrics/subagent_stop_metrics.jsonl"
    assert metrics_file.exists()

    with open(metrics_file) as f:
        lines = f.readlines()
        assert len(lines) >= 1

        # Find termination metric
        for line in lines:
            metric = json.loads(line)
            if metric["metric"] == "subagent_termination":
                assert metric["value"]["agent_name"] == "architect"
                assert metric["value"]["turn_count"] == 5
                break
        else:
            pytest.fail("No termination metric found")


def test_e2e_subprocess_session_detection(captured_subagent_subprocess, temp_project_root):
    """E2E-SUBAGENT-002: Subprocess detects subagent from session_id."""
    input_data = {"session_id": "agent-builder-abc", "tool_use_count": 20}

    result = captured_subagent_subprocess(input_data)

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output == {}

    # Verify metrics
    metrics_file = temp_project_root / ".claude/runtime/metrics/subagent_stop_metrics.jsonl"
    assert metrics_file.exists()

    with open(metrics_file) as f:
        content = f.read()
        assert "agent-builder-abc" in content
        assert "tool_use_count" in content


def test_e2e_subprocess_no_disruption(captured_subagent_subprocess):
    """E2E-SUBAGENT-003: Hook never disrupts stop behavior."""
    test_cases = [
        # Subagent cases
        ({"session_id": "agent-test"}, None),
        ({"session_id": "test"}, "security"),
        ({"agent_name": "reviewer"}, None),
        # Regular cases
        ({"session_id": "regular"}, None),
        ({}, None),
    ]

    for input_data, agent_env in test_cases:
        result = captured_subagent_subprocess(input_data, agent_env=agent_env)

        # Should always succeed and return empty dict
        assert result.returncode == 0, f"Failed for {input_data} with env={agent_env}"
        output = json.loads(result.stdout)
        assert output == {}, f"Non-empty output for {input_data}"


# =============================================================================
# JSONL Format Tests
# =============================================================================


def test_jsonl_format_valid(subagent_stop_hook):
    """JSONL-001: Metrics file uses valid JSONL format."""
    input_data = {"session_id": "agent-test", "turn_count": 1}

    subagent_stop_hook.process(input_data)

    metrics_file = subagent_stop_hook.metrics_dir / "subagent_stop_metrics.jsonl"
    assert metrics_file.exists()

    # Verify each line is valid JSON
    with open(metrics_file) as f:
        for line_num, line in enumerate(f, 1):
            try:
                metric = json.loads(line)
                assert isinstance(metric, dict)
                assert "timestamp" in metric
                assert "metric" in metric
                assert "hook" in metric
                assert metric["hook"] == "subagent_stop"
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON on line {line_num}: {e}")


def test_jsonl_format_multiple_entries(subagent_stop_hook):
    """JSONL-002: Multiple metrics create separate JSONL lines."""
    # Process multiple stops
    for i in range(3):
        input_data = {"session_id": f"agent-test-{i}", "turn_count": i + 1}
        subagent_stop_hook.process(input_data)

    metrics_file = subagent_stop_hook.metrics_dir / "subagent_stop_metrics.jsonl"
    assert metrics_file.exists()

    with open(metrics_file) as f:
        lines = f.readlines()
        # Should have at least 6 lines (2 metrics per stop)
        assert len(lines) >= 6

        # All lines should be valid JSON
        for line in lines:
            metric = json.loads(line)
            assert isinstance(metric, dict)


# =============================================================================
# Error Handling Tests
# =============================================================================


def test_error_invalid_input_data(subagent_stop_hook):
    """ERROR-001: Handle invalid input data gracefully."""
    invalid_inputs = [
        None,  # None input (will be dict in practice but test defensiveness)
        {"session_id": None},  # None session_id
        {"session_id": 12345},  # Non-string session_id
        {"turn_count": "not-a-number"},  # Invalid metric type
    ]

    for input_data in invalid_inputs:
        try:
            if input_data is None:
                input_data = {}
            result = subagent_stop_hook.process(input_data)
            # Should always return empty dict without crashing
            assert result == {}
        except Exception as e:
            pytest.fail(f"Hook crashed on input {input_data}: {e}")


def test_error_no_metrics_directory(subagent_stop_hook, temp_project_root):
    """ERROR-002: Handle missing metrics directory gracefully."""
    # Remove metrics directory
    import shutil

    if subagent_stop_hook.metrics_dir.exists():
        shutil.rmtree(subagent_stop_hook.metrics_dir)

    input_data = {"session_id": "agent-test"}

    # Should not crash
    result = subagent_stop_hook.process(input_data)
    assert result == {}

    # Metrics directory should be recreated
    assert subagent_stop_hook.metrics_dir.exists()
