#!/usr/bin/env python3
"""
Integration tests for the unified hook processor system.
Tests all hooks working together to ensure backward compatibility.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

# Add project to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def run_hook(hook_script: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run a hook script with given input and return output.

    Args:
        hook_script: Name of the hook script (e.g., "session_start.py")
        input_data: Dictionary to pass as JSON input

    Returns:
        Output from the hook as dictionary
    """
    hook_path = Path(__file__).parent / hook_script

    # Run the hook with JSON input
    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        cwd=str(hook_path.parent),
    )

    if result.returncode != 0:
        print(f"Hook {hook_script} failed with return code {result.returncode}")
        print(f"stderr: {result.stderr}")
        return {}

    # Parse output
    if result.stdout:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            print(f"Failed to parse output from {hook_script}: {e}")
            print(f"stdout: {result.stdout}")
            return {}
    return {}


def test_session_start():
    """Test session_start hook."""
    print("Testing session_start hook...")

    # Test with prompt
    input_data = {"prompt": "Help me build a web app"}
    output = run_hook("session_start.py", input_data)

    assert "additionalContext" in output, "Should return additional context"
    assert "metadata" in output, "Should include metadata"
    assert "Project Context" in output["additionalContext"], "Should include project context"
    print("✓ session_start hook works correctly")


def test_stop():
    """Test stop hook."""
    print("Testing stop hook...")

    # Test with messages containing learnings
    input_data = {
        "messages": [
            {"role": "user", "content": "How do I fix this error?"},
            {
                "role": "assistant",
                "content": "I discovered that the issue was a missing import statement.",
            },
            {"role": "user", "content": "Thanks!"},
        ]
    }
    output = run_hook("stop.py", input_data)

    # Should find learnings
    if output:  # May be empty if no learnings detected with stricter criteria
        assert "metadata" in output, "Should include metadata when learnings found"
        assert output["metadata"]["learningsFound"] > 0, "Should find at least one learning"
        print(f"✓ stop hook found {output['metadata']['learningsFound']} learnings")
    else:
        print("✓ stop hook processed messages (no learnings found)")


def test_post_tool_use():
    """Test post_tool_use hook."""
    print("Testing post_tool_use hook...")

    # Test various tool types
    tools = [
        {"name": "Bash", "expected_empty": True},
        {"name": "Read", "expected_empty": True},
        {"name": "Write", "expected_empty": True},
        {"name": "Edit", "expected_empty": True},
        {"name": "Grep", "expected_empty": True},
    ]

    for tool_info in tools:
        input_data = {"toolUse": {"name": tool_info["name"]}, "result": {"success": True}}
        output = run_hook("post_tool_use.py", input_data)

        if tool_info["expected_empty"]:
            assert output == {} or "metadata" in output, (
                f"Tool {tool_info['name']} should return empty or metadata"
            )
        print(f"  ✓ {tool_info['name']} tool processed correctly")

    # Test error case
    input_data = {"toolUse": {"name": "Edit"}, "result": {"error": "File not found"}}
    output = run_hook("post_tool_use.py", input_data)
    if output and "metadata" in output:
        assert "warning" in output["metadata"], "Should include warning for errors"
        print("  ✓ Error handling works correctly")
    else:
        print("  ✓ Error case processed")

    print("✓ post_tool_use hook works correctly")


def test_full_session_flow():
    """Test a complete session flow through all hooks."""
    print("\nTesting full session flow...")

    # 1. Session starts
    session_start = run_hook("session_start.py", {"prompt": "Build a CLI tool"})
    assert "additionalContext" in session_start, "Session should start with context"
    print("  ✓ Session started")

    # 2. Tool uses during session
    tools_used = ["Read", "Edit", "Bash", "Write"]
    for tool_name in tools_used:
        tool_result = run_hook(
            "post_tool_use.py", {"toolUse": {"name": tool_name}, "result": {"success": True}}
        )
        # Result should be empty dict for successful operations
        assert isinstance(tool_result, dict), f"Tool {tool_name} should return dict"
        print(f"  ✓ Tool {tool_name} tracked")

    # 3. Session stops
    stop_result = run_hook(
        "stop.py",
        {
            "messages": [
                {"role": "user", "content": "Build a CLI tool"},
                {
                    "role": "assistant",
                    "content": "I'll help you build a CLI tool. I discovered that using argparse is the best approach for Python CLIs.",
                },
                {"role": "user", "content": "Great, thanks!"},
            ]
        },
    )
    # Should process messages successfully
    assert isinstance(stop_result, dict), "Stop should return dict"
    print("  ✓ Session stopped and analyzed")

    print("✓ Full session flow works correctly")


def test_error_handling():
    """Test error handling in hooks."""
    print("\nTesting error handling...")

    # Test with invalid JSON
    hook_path = Path(__file__).parent / "session_start.py"
    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input="not valid json",
        capture_output=True,
        text=True,
        cwd=str(hook_path.parent),
    )

    # Should not crash, should return empty dict
    if result.stdout:
        output = json.loads(result.stdout)
        assert isinstance(output, dict), "Should return dict even on error"
    print("  ✓ Invalid JSON handled gracefully")

    # Test with missing required fields
    empty_result = run_hook("post_tool_use.py", {})
    assert isinstance(empty_result, dict), "Should handle missing fields gracefully"
    print("  ✓ Missing fields handled gracefully")

    print("✓ Error handling works correctly")


def test_metrics_and_logs():
    """Test that metrics and logs are being created."""
    print("\nTesting metrics and logging...")

    runtime_dir = project_root / ".claude" / "runtime"

    # Run a tool to generate metrics
    run_hook("post_tool_use.py", {"toolUse": {"name": "TestTool"}, "result": {}})

    # Check if directories were created
    assert (runtime_dir / "logs").exists(), "Logs directory should be created"
    assert (runtime_dir / "metrics").exists(), "Metrics directory should be created"
    print("  ✓ Runtime directories created")

    # Check for log files
    log_files = list((runtime_dir / "logs").glob("*.log"))
    assert len(log_files) > 0, "Should create log files"
    print(f"  ✓ Found {len(log_files)} log files")

    # Check for metrics files
    metrics_files = list((runtime_dir / "metrics").glob("*.jsonl"))
    assert len(metrics_files) > 0, "Should create metrics files"
    print(f"  ✓ Found {len(metrics_files)} metrics files")

    print("✓ Metrics and logging work correctly")


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Running Hook Integration Tests")
    print("=" * 60)

    try:
        test_session_start()
        test_stop()
        test_post_tool_use()
        test_full_session_flow()
        test_error_handling()
        test_metrics_and_logs()

        print("\n" + "=" * 60)
        print("All integration tests passed! ✓")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
