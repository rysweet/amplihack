"""
Integration tests for subprocess execution.

Tests the hook running as a subprocess with real stdin/stdout/stderr.
"""

import json
import time

import pytest


def test_integ_subprocess_001_hook_executed_with_no_lock(captured_subprocess):
    """INTEG-SUBPROCESS-001: Hook executed as subprocess with no lock."""
    # Input
    input_data = {"session_id": "test_123"}

    # Execute
    result = captured_subprocess(input_data, lock_active=False)

    # Expected:
    # - stdout contains {}
    # - stderr is empty
    # - exit code is 0
    assert result.returncode == 0, f"Exit code was {result.returncode}, stderr: {result.stderr}"

    # Parse stdout
    output = json.loads(result.stdout)
    assert output == {}

    # Note: stderr may contain log messages but should not contain errors during normal operation


def test_integ_subprocess_002_hook_executed_with_active_lock(captured_subprocess):
    """INTEG-SUBPROCESS-002: Hook executed as subprocess with active lock."""
    # Input
    input_data = {"session_id": "test_123"}

    # Execute with lock active
    result = captured_subprocess(input_data, lock_active=True)

    # Expected:
    # - stdout contains block decision JSON
    # - stderr is empty (no diagnostic output during normal operation)
    # - exit code is 0
    assert result.returncode == 0, f"Exit code was {result.returncode}, stderr: {result.stderr}"

    # Parse stdout
    output = json.loads(result.stdout)
    assert output["decision"] == "block"
    assert "reason" in output
    assert isinstance(output["reason"], str)
    assert len(output["reason"]) > 0


def test_integ_subprocess_003_hook_executed_with_corrupted_json(captured_subprocess):
    """INTEG-SUBPROCESS-003: Hook executed with corrupted JSON input."""
    # This test needs to bypass captured_subprocess to send bad JSON
    import subprocess
    import sys
    from pathlib import Path

    hook_script = Path(__file__).parent.parent.parent / ".claude/tools/amplihack/hooks/stop.py"

    # Execute with bad JSON
    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input="{bad json}",
        capture_output=True,
        text=True,
        timeout=5,
    )

    # Expected:
    # - stdout contains {"error": "Invalid JSON input"}
    # - exit code is 0 (fail-safe)
    assert result.returncode == 0

    # Parse stdout
    output = json.loads(result.stdout)
    assert "error" in output
    assert "Invalid JSON input" in output["error"]


def test_integ_subprocess_004_hook_executed_with_no_stdin(captured_subprocess):
    """INTEG-SUBPROCESS-004: Hook executed with no stdin."""
    import subprocess
    import sys
    from pathlib import Path

    hook_script = Path(__file__).parent.parent.parent / ".claude/tools/amplihack/hooks/stop.py"

    # Execute with empty stdin
    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input="",
        capture_output=True,
        text=True,
        timeout=5,
    )

    # Expected:
    # - stdout contains {}
    # - exit code is 0
    assert result.returncode == 0

    # Parse stdout
    output = json.loads(result.stdout)
    assert output == {}


@pytest.mark.performance
def test_integ_subprocess_005_hook_execution_performance(captured_subprocess):
    """INTEG-SUBPROCESS-005: Hook execution performance."""
    # Input
    input_data = {"session_id": "perf_test"}

    # Time the execution
    start = time.perf_counter()
    result = captured_subprocess(input_data, lock_active=False)
    duration_ms = (time.perf_counter() - start) * 1000

    # Expected: Completes in < 200ms
    assert duration_ms < 200, f"Hook took {duration_ms:.2f}ms (limit: 200ms)"
    assert result.returncode == 0

    # Also test with lock active
    start = time.perf_counter()
    result = captured_subprocess(input_data, lock_active=True)
    duration_ms = (time.perf_counter() - start) * 1000

    assert duration_ms < 200, f"Hook with lock took {duration_ms:.2f}ms (limit: 200ms)"
    assert result.returncode == 0


@pytest.mark.slow
def test_integ_subprocess_006_multiple_concurrent_hook_executions(captured_subprocess):
    """INTEG-SUBPROCESS-006: Multiple concurrent hook executions."""
    import concurrent.futures

    input_data = {"session_id": "concurrent_test"}

    # Run 5 instances simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(captured_subprocess, input_data, lock_active=(i % 2 == 0))
            for i in range(5)
        ]

        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Expected: All succeed, no race conditions, consistent results
    assert len(results) == 5

    for result in results:
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert isinstance(output, dict)
