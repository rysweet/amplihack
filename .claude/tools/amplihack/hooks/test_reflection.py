#!/usr/bin/env python3
"""
Test script for reflection module and loop prevention.
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent))

# Import after path manipulation to avoid E402
from reflection import SessionReflector, save_reflection_summary  # noqa: E402


def test_loop_prevention():
    """Test that CLAUDE_REFLECTION_MODE prevents loops"""
    print("\n=== Testing Loop Prevention ===")

    # Test without environment variable
    reflector1 = SessionReflector()
    assert reflector1.enabled, "Should be enabled without env var"
    print("✓ Reflection enabled without env var")

    # Test with environment variable set
    os.environ["CLAUDE_REFLECTION_MODE"] = "1"
    reflector2 = SessionReflector()
    assert not reflector2.enabled, "Should be disabled with env var"
    print("✓ Reflection disabled with CLAUDE_REFLECTION_MODE=1")

    # Clean up
    del os.environ["CLAUDE_REFLECTION_MODE"]
    print("✓ Loop prevention mechanism working")


def test_pattern_detection():
    """Test pattern detection capabilities"""
    print("\n=== Testing Pattern Detection ===")

    reflector = SessionReflector()

    # Test repeated commands
    messages_repeated = [
        {"role": "assistant", "content": '<function_calls><invoke name="Bash">'},
        {"role": "assistant", "content": '<function_calls><invoke name="Bash">'},
        {"role": "assistant", "content": '<function_calls><invoke name="Bash">'},
        {"role": "assistant", "content": '<function_calls><invoke name="Bash">'},
    ]

    analysis = reflector.analyze_session(messages_repeated)
    assert len(analysis["patterns"]) > 0, "Should detect repeated bash usage"
    print(f"✓ Detected repeated tool use: {analysis['patterns'][0]['type']}")

    # Test error patterns
    messages_errors = [
        {"role": "assistant", "content": "Error: Command failed"},
        {"role": "user", "content": "It's still not working"},
        {"role": "assistant", "content": "Let me retry that"},
        {"role": "assistant", "content": "Another error occurred"},
    ]

    analysis = reflector.analyze_session(messages_errors)
    error_patterns = [p for p in analysis["patterns"] if p["type"] == "error_patterns"]
    assert len(error_patterns) > 0, "Should detect error patterns"
    print(f"✓ Detected error patterns: {error_patterns[0]['count']} errors")

    # Test frustration detection
    messages_frustration = [
        {"role": "user", "content": "This doesn't work at all"},
        {"role": "user", "content": "Still failing, I don't understand"},
        {"role": "assistant", "content": "Let me try a different approach"},
    ]

    analysis = reflector.analyze_session(messages_frustration)
    frustration = [p for p in analysis["patterns"] if p["type"] == "user_frustration"]
    assert len(frustration) > 0, "Should detect user frustration"
    print(f"✓ Detected user frustration: {frustration[0]['indicators']} indicators")

    # Test long session detection
    messages_long = [{"role": "user", "content": f"Message {i}"} for i in range(150)]
    analysis = reflector.analyze_session(messages_long)
    long_session = [p for p in analysis["patterns"] if p["type"] == "long_session"]
    assert len(long_session) > 0, "Should detect long session"
    print(f"✓ Detected long session: {long_session[0]['message_count']} messages")


def test_suggestion_generation():
    """Test that suggestions are generated appropriately"""
    print("\n=== Testing Suggestion Generation ===")

    reflector = SessionReflector()

    # Create a session with multiple patterns
    messages = []

    # Add repeated bash commands
    for _ in range(6):
        messages.append({"role": "assistant", "content": '<function_calls><invoke name="Bash">'})

    # Add errors
    for _ in range(4):
        messages.append({"role": "assistant", "content": "Error occurred, retrying..."})

    # Add frustration
    messages.append({"role": "user", "content": "This still doesn't work"})
    messages.append({"role": "user", "content": "Why isn't this working?"})

    analysis = reflector.analyze_session(messages)

    assert len(analysis["suggestions"]) > 0, "Should generate suggestions"
    print(f"✓ Generated {len(analysis['suggestions'])} suggestions:")
    for i, suggestion in enumerate(analysis["suggestions"][:3], 1):
        print(f"  {i}. {suggestion[:80]}...")

    # Check for high priority suggestion
    if any(p["type"] == "user_frustration" for p in analysis["patterns"]):
        assert any("HIGH PRIORITY" in s for s in analysis["suggestions"]), (
            "Should have high priority suggestion"
        )
        print("✓ High priority suggestion included for frustration")


def test_save_reflection_summary():
    """Test saving reflection summary to file"""
    print("\n=== Testing Summary Save ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        analysis = {
            "timestamp": datetime.now().isoformat(),
            "metrics": {"total_messages": 50, "tool_uses": 10},
            "patterns": [
                {
                    "type": "repeated_tool_use",
                    "tool": "bash",
                    "count": 5,
                    "suggestion": "Create a script",
                }
            ],
            "suggestions": ["Consider automating repetitive tasks"],
        }

        summary_file = save_reflection_summary(analysis, output_dir)
        assert summary_file is not None, "Should return summary file"
        assert summary_file.exists(), "Should create summary file"
        print(f"✓ Created summary file: {summary_file.name}")

        # Verify content
        with open(summary_file) as f:
            saved = json.load(f)
            assert "action_items" in saved, "Should have action items"
            assert len(saved["action_items"]) > 0, "Should generate action items"
            print(f"✓ Summary contains {len(saved['action_items'])} action items")


def test_integration_with_stop_hook():
    """Test integration with stop.py hook"""
    print("\n=== Testing Stop Hook Integration ===")

    # Import stop hook class (local import to test integration)
    from stop import StopHook  # noqa: E402

    # Create hook instance
    hook = StopHook()

    # Test with reflection disabled (loop prevention)
    os.environ["CLAUDE_REFLECTION_MODE"] = "1"
    messages = [
        {"role": "user", "content": "Test message"},
        {"role": "assistant", "content": "Response"},
    ]

    learnings = hook.extract_learnings(messages)
    assert isinstance(learnings, list), "Should return a list even when disabled"
    print("✓ Stop hook handles disabled reflection gracefully")

    # Clean up
    del os.environ["CLAUDE_REFLECTION_MODE"]

    # Test with reflection enabled
    messages_with_patterns = [
        {"role": "assistant", "content": '<function_calls><invoke name="Bash">'},
        {"role": "assistant", "content": '<function_calls><invoke name="Bash">'},
        {"role": "assistant", "content": '<function_calls><invoke name="Bash">'},
        {"role": "user", "content": "This doesn't work"},
    ]

    learnings = hook.extract_learnings(messages_with_patterns)
    assert len(learnings) > 0, "Should extract learnings from patterns"
    print(f"✓ Stop hook extracted {len(learnings)} learnings")

    # Verify learning structure
    if learnings:
        learning = learnings[0]
        assert "type" in learning, "Learning should have type"
        assert "suggestion" in learning, "Learning should have suggestion"
        print(f"✓ Learning structure valid: {learning['type']}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Reflection Module and Loop Prevention")
    print("=" * 60)

    try:
        test_loop_prevention()
        test_pattern_detection()
        test_suggestion_generation()
        test_save_reflection_summary()
        test_integration_with_stop_hook()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nReflection system is working correctly!")
        print("Loop prevention mechanism is active.")
        print("Pattern detection is functional.")
        print("Ready for deployment.")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
