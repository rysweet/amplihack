#!/usr/bin/env python3
"""Manual test for subagent_stop hook."""

import json
import os
import sys
from pathlib import Path

# Add hooks directory to path
hooks_dir = Path(__file__).parent / ".claude/tools/amplihack/hooks"
sys.path.insert(0, str(hooks_dir))

from subagent_stop import SubagentStopHook

def test_subagent_detection():
    """Test subagent detection methods."""
    print("Testing subagent detection...")

    hook = SubagentStopHook()

    # Test 1: Environment variable detection
    os.environ["CLAUDE_AGENT"] = "architect"
    detection = hook._detect_subagent_context({"session_id": "test"})
    assert detection["is_subagent"] is True
    assert detection["agent_name"] == "architect"
    assert detection["detection_method"] == "env"
    print("✓ Environment variable detection")
    del os.environ["CLAUDE_AGENT"]

    # Test 2: Session ID prefix detection
    detection = hook._detect_subagent_context({"session_id": "agent-builder-123"})
    assert detection["is_subagent"] is True
    assert detection["agent_name"] == "agent-builder-123"
    assert detection["detection_method"] == "session"
    print("✓ Session ID prefix detection")

    # Test 3: Metadata detection
    detection = hook._detect_subagent_context({"session_id": "test", "agent_name": "security"})
    assert detection["is_subagent"] is True
    assert detection["agent_name"] == "security"
    assert detection["detection_method"] == "metadata"
    print("✓ Metadata detection")

    # Test 4: No subagent
    detection = hook._detect_subagent_context({"session_id": "regular-session"})
    assert detection["is_subagent"] is False
    assert detection["agent_name"] is None
    assert detection["detection_method"] == "none"
    print("✓ No subagent detection")

def test_metric_extraction():
    """Test metric extraction."""
    print("\nTesting metric extraction...")

    hook = SubagentStopHook()

    input_data = {
        "session_id": "test-123",
        "turn_count": 5,
        "tool_use_count": 15,
        "error_count": 2,
        "duration_seconds": 120.5,
    }

    metrics = hook._extract_session_metrics(input_data)
    assert metrics["session_id"] == "test-123"
    assert metrics["turn_count"] == 5
    assert metrics["tool_use_count"] == 15
    assert metrics["error_count"] == 2
    assert metrics["duration_seconds"] == 120.5
    print("✓ Full metrics extraction")

    # Test with missing fields
    metrics = hook._extract_session_metrics({"session_id": "test"})
    assert metrics["session_id"] == "test"
    assert metrics["turn_count"] == 0
    assert metrics["tool_use_count"] == 0
    print("✓ Partial metrics extraction")

def test_process_method():
    """Test the main process method."""
    print("\nTesting process method...")

    hook = SubagentStopHook()

    # Test subagent input
    input_data = {"session_id": "agent-test-123", "turn_count": 3}
    result = hook.process(input_data)
    assert result == {}
    print("✓ Subagent processing returns empty dict")

    # Verify metrics were logged
    metrics_file = hook.metrics_dir / "subagent_stop_metrics.jsonl"
    assert metrics_file.exists(), "Metrics file should exist"

    with open(metrics_file) as f:
        lines = f.readlines()
        assert len(lines) >= 2, f"Expected at least 2 metrics, got {len(lines)}"

        # Parse and verify
        for line in lines[-2:]:
            metric = json.loads(line)
            assert "timestamp" in metric
            assert "metric" in metric
            assert "hook" in metric
            assert metric["hook"] == "subagent_stop"

    print("✓ Metrics logged correctly")
    print(f"  - {len(lines)} total metric entries")

    # Test regular input (no subagent)
    input_data = {"session_id": "regular-session"}
    result = hook.process(input_data)
    assert result == {}
    print("✓ Regular session processing returns empty dict")

def test_jsonl_format():
    """Test JSONL format validity."""
    print("\nTesting JSONL format...")

    hook = SubagentStopHook()

    # Process multiple entries
    for i in range(3):
        hook.process({"session_id": f"agent-test-{i}", "turn_count": i + 1})

    metrics_file = hook.metrics_dir / "subagent_stop_metrics.jsonl"
    with open(metrics_file) as f:
        line_count = 0
        for line in f:
            line_count += 1
            metric = json.loads(line)  # Will raise if invalid JSON
            assert isinstance(metric, dict)
            assert "timestamp" in metric
            assert "metric" in metric

    print(f"✓ All {line_count} JSONL entries are valid JSON")

def main():
    """Run all tests."""
    print("=" * 60)
    print("SubagentStop Hook Manual Test Suite")
    print("=" * 60)

    try:
        test_subagent_detection()
        test_metric_extraction()
        test_process_method()
        test_jsonl_format()

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
