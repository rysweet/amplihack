"""
End-to-end performance test.

Tests performance under load.
"""

import json
import time
import pytest


@pytest.mark.slow
@pytest.mark.performance
def test_e2e_perf_001_hook_performance_under_load(captured_subprocess, temp_project_root):
    """E2E-PERF-001: Hook performance under load."""
    # Scenario: Rapid repeated stop calls
    input_data = {"session_id": "perf_test"}

    # Step 1: Execute hook 100 times in quick succession
    # Step 2: Mix lock active/inactive states
    results = []
    timings = []

    for i in range(100):
        lock_active = i % 2 == 0

        # Create/delete lock as needed
        lock_file = temp_project_root / ".claude/tools/amplihack/.lock_active"
        if lock_active and not lock_file.exists():
            lock_file.touch()
        elif not lock_active and lock_file.exists():
            lock_file.unlink()

        # Step 3: Measure execution times
        start = time.perf_counter()
        result = captured_subprocess(input_data, lock_active=lock_active)
        duration_ms = (time.perf_counter() - start) * 1000

        results.append(result)
        timings.append(duration_ms)

    # Expected:
    # - All executions < 250ms (allowing some margin for CI/test overhead)
    assert all(t < 250 for t in timings), (
        f"Some executions too slow: max={max(timings):.2f}ms, avg={sum(timings) / len(timings):.2f}ms"
    )

    # - No failures
    assert all(r.returncode == 0 for r in results), "Some executions failed"

    # - Consistent results
    for i, result in enumerate(results):
        output = json.loads(result.stdout)
        lock_active = i % 2 == 0

        if lock_active:
            assert "decision" in output and output["decision"] == "block"
        else:
            assert output == {}

    # - No memory leaks (approximate check via timing consistency)
    # First 10 vs last 10 should be similar
    first_10_avg = sum(timings[:10]) / 10
    last_10_avg = sum(timings[-10:]) / 10

    # Last 10 shouldn't be significantly slower (no more than 2x)
    assert last_10_avg < first_10_avg * 2, (
        f"Performance degraded: first={first_10_avg:.2f}ms, last={last_10_avg:.2f}ms"
    )

    # Report statistics
    print("\nPerformance Statistics:")
    print(f"  Total executions: {len(timings)}")
    print(f"  Min: {min(timings):.2f}ms")
    print(f"  Max: {max(timings):.2f}ms")
    print(f"  Avg: {sum(timings) / len(timings):.2f}ms")
    print(f"  P95: {sorted(timings)[int(len(timings) * 0.95)]:.2f}ms")
    print(f"  P99: {sorted(timings)[int(len(timings) * 0.99)]:.2f}ms")
