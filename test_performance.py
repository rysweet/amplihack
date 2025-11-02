#!/usr/bin/env python
"""
Quick performance test for subagent-mapper.

Tests that report generation completes in < 3 seconds.
"""

import time
import json
import tempfile
from pathlib import Path
from datetime import datetime

from src.amplihack.analytics.metrics_reader import MetricsReader
from src.amplihack.analytics.visualization import ReportGenerator


def create_test_metrics(metrics_dir: Path, num_executions: int = 100):
    """Create test metrics with specified number of executions."""

    # Create agents
    agents = ["orchestrator", "architect", "builder", "reviewer", "tester", "analyzer"]

    start_events = []
    stop_events = []

    base_time = datetime(2025, 11, 2, 14, 30, 0)

    for i in range(num_executions):
        agent = agents[i % len(agents)]
        parent = agents[(i - 1) % len(agents)] if i > 0 else None

        start_time = base_time.replace(second=(base_time.second + i * 10) % 60, minute=base_time.minute + (i * 10 // 60))

        start_events.append({
            "event": "start",
            "agent_name": agent,
            "session_id": "perf_test",
            "timestamp": start_time.isoformat() + "Z",
            "parent_agent": parent,
            "execution_id": f"exec_{i:03d}"
        })

        stop_events.append({
            "event": "stop",
            "agent_name": agent,
            "session_id": "perf_test",
            "timestamp": start_time.replace(second=(start_time.second + 5) % 60).isoformat() + "Z",
            "execution_id": f"exec_{i:03d}",
            "duration_ms": 5000.0 + (i * 100)
        })

    # Write files
    with open(metrics_dir / "subagent_start.jsonl", "w") as f:
        for event in start_events:
            f.write(json.dumps(event) + "\n")

    with open(metrics_dir / "subagent_stop.jsonl", "w") as f:
        for event in stop_events:
            f.write(json.dumps(event) + "\n")


def test_performance():
    """Test report generation performance."""

    with tempfile.TemporaryDirectory() as tmpdir:
        metrics_dir = Path(tmpdir)

        # Create test data
        print("Creating test data with 100 executions...")
        create_test_metrics(metrics_dir, num_executions=100)

        # Initialize components
        reader = MetricsReader(metrics_dir=metrics_dir)
        generator = ReportGenerator(reader)

        # Test text report generation
        print("\nTesting text report generation...")
        start_time = time.time()
        text_report = generator.generate_text_report(session_id="perf_test")
        text_time = time.time() - start_time

        print(f"Text report generation time: {text_time:.3f}s")
        print(f"Text report length: {len(text_report)} chars")

        # Test JSON report generation
        print("\nTesting JSON report generation...")
        start_time = time.time()
        json_report = generator.generate_json_report(session_id="perf_test")
        json_time = time.time() - start_time

        print(f"JSON report generation time: {json_time:.3f}s")
        print(f"JSON report executions: {len(json_report['executions'])}")

        # Verify performance requirement
        max_time = max(text_time, json_time)
        print(f"\nMaximum time: {max_time:.3f}s")

        if max_time < 3.0:
            print("✓ Performance requirement met (< 3s)")
            return True
        else:
            print("✗ Performance requirement NOT met (>= 3s)")
            return False


if __name__ == "__main__":
    success = test_performance()
    exit(0 if success else 1)
