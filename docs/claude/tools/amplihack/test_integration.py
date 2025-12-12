#!/usr/bin/env python3
"""
Integration test for power steering progress visibility.

Tests the full integration between ProgressTracker and PowerSteeringChecker.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "hooks"))

from power_steering_checker import PowerSteeringChecker
from power_steering_progress import ProgressTracker


def create_test_transcript(temp_dir: Path) -> Path:
    """Create a minimal test transcript.

    Args:
        temp_dir: Temporary directory for transcript

    Returns:
        Path to transcript file
    """
    transcript_path = temp_dir / "transcript.jsonl"

    # Create minimal transcript with a few messages
    messages = [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": "Create a simple Python function to add two numbers",
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'll create a function for you."},
                    {
                        "type": "tool_use",
                        "name": "Write",
                        "input": {
                            "file_path": "add.py",
                            "content": "def add(a, b):\n    return a + b",
                        },
                    },
                ],
            },
        },
        {
            "type": "tool_result",
            "message": {
                "tool_use_id": "test",
                "content": [{"type": "tool_result", "content": "File created"}],
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "TodoWrite",
                        "input": {
                            "todos": [
                                {
                                    "content": "Create function",
                                    "status": "completed",
                                    "activeForm": "Creating function",
                                }
                            ]
                        },
                    }
                ],
            },
        },
    ]

    with open(transcript_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    return transcript_path


def test_integration_with_summary_mode():
    """Test integration with SUMMARY mode."""
    print("=" * 70)
    print("INTEGRATION TEST 1: PowerSteeringChecker + ProgressTracker (SUMMARY)")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create project structure
        claude_dir = temp_path / ".claude"
        claude_dir.mkdir()
        tools_dir = claude_dir / "tools" / "amplihack"
        tools_dir.mkdir(parents=True)

        # Create minimal config
        config = {"enabled": True, "phase": 1, "checkers_enabled": {}}
        config_path = tools_dir / ".power_steering_config"
        config_path.write_text(json.dumps(config))

        # Create test transcript
        transcript_path = create_test_transcript(temp_path)

        # Initialize checker and tracker
        checker = PowerSteeringChecker(project_root=temp_path)
        tracker = ProgressTracker(verbosity="summary", project_root=temp_path)

        # Run check with progress callback
        print("\nRunning power-steering check with progress tracking...\n")
        result = checker.check(transcript_path, "test_session_001", progress_callback=tracker.emit)

        # Display summary
        tracker.display_summary()

        print(f"\nResult: {result.decision}")
        print(f"Reasons: {result.reasons}")

        print("\n✓ Integration Test 1 passed\n")
        return True


def test_integration_with_detailed_mode():
    """Test integration with DETAILED mode."""
    print("=" * 70)
    print("INTEGRATION TEST 2: PowerSteeringChecker + ProgressTracker (DETAILED)")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create project structure
        claude_dir = temp_path / ".claude"
        claude_dir.mkdir()
        tools_dir = claude_dir / "tools" / "amplihack"
        tools_dir.mkdir(parents=True)

        # Create minimal config
        config = {"enabled": True, "phase": 1, "checkers_enabled": {}}
        config_path = tools_dir / ".power_steering_config"
        config_path.write_text(json.dumps(config))

        # Create test transcript
        transcript_path = create_test_transcript(temp_path)

        # Initialize checker and tracker
        checker = PowerSteeringChecker(project_root=temp_path)
        tracker = ProgressTracker(verbosity="detailed", project_root=temp_path)

        # Run check with progress callback
        print("\nRunning power-steering check with detailed progress...\n")
        result = checker.check(transcript_path, "test_session_002", progress_callback=tracker.emit)

        # Display summary
        tracker.display_summary()

        print(f"\nResult: {result.decision}")
        print(f"Reasons: {result.reasons}")

        print("\n✓ Integration Test 2 passed\n")
        return True


def main():
    """Run all integration tests."""
    print("\n🧪 POWER STEERING INTEGRATION TESTS\n")

    try:
        test_integration_with_summary_mode()
        test_integration_with_detailed_mode()

        print("=" * 70)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("=" * 70)
        return 0

    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
