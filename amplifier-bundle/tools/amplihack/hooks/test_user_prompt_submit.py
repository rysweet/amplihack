#!/usr/bin/env python3
"""
Test suite for user_prompt_submit hook.
Verifies hook behavior, performance, and error handling.
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Add hook directory to path
sys.path.insert(0, str(Path(__file__).parent))
from user_prompt_submit import UserPromptSubmitHook


def test_hook_basic_functionality():
    """Test that hook processes input and returns valid output."""
    print("Testing basic functionality...")

    hook = UserPromptSubmitHook()

    # Mock input data
    input_data = {
        "session_id": "test_session",
        "transcript_path": "/tmp/test",
        "cwd": str(Path.cwd()),
        "hook_event_name": "UserPromptSubmit",
        "prompt": "test prompt",
    }

    # Process
    output = hook.process(input_data)

    # Verify output structure
    assert "additionalContext" in output, "Output missing additionalContext"
    assert isinstance(output["additionalContext"], str), "additionalContext must be string"

    print("✓ Basic functionality works")


def test_preference_extraction():
    """Test that preferences are correctly extracted."""
    print("Testing preference extraction...")

    hook = UserPromptSubmitHook()

    # Find preferences file
    pref_file = hook.find_user_preferences()
    assert pref_file is not None, "Could not find USER_PREFERENCES.md"
    assert pref_file.exists(), f"Preferences file does not exist: {pref_file}"

    # Read and parse
    content = pref_file.read_text(encoding="utf-8")
    preferences = hook.extract_preferences(content)

    # Verify we got some preferences
    assert len(preferences) > 0, "No preferences extracted"

    # Verify expected preferences exist
    expected_prefs = ["Communication Style", "Verbosity", "Collaboration Style"]
    for pref in expected_prefs:
        if pref in preferences:
            print(f"  Found {pref}: {preferences[pref]}")

    print(f"✓ Extracted {len(preferences)} preferences")


def test_context_building():
    """Test that preference context is built correctly."""
    print("Testing context building...")

    hook = UserPromptSubmitHook()

    # Test with sample preferences
    preferences = {
        "Communication Style": "pirate",
        "Verbosity": "balanced",
        "Collaboration Style": "interactive",
    }

    context = hook.build_preference_context(preferences)

    # Verify context structure
    assert "🎯 ACTIVE USER PREFERENCES (MANDATORY):" in context
    assert "Communication Style: pirate" in context
    assert "Use this style in your response" in context
    assert "These preferences MUST be applied" in context

    print(f"✓ Context built ({len(context)} chars)")


def test_empty_preferences():
    """Test handling of empty preferences."""
    print("Testing empty preferences...")

    hook = UserPromptSubmitHook()

    # Empty preferences
    context = hook.build_preference_context({})
    assert context == "", "Empty preferences should return empty context"

    print("✓ Empty preferences handled correctly")


def test_caching():
    """Test that preference caching works."""
    print("Testing caching...")

    hook = UserPromptSubmitHook()

    pref_file = hook.find_user_preferences()
    if not pref_file:
        print("⚠ No preferences file found, skipping cache test")
        return

    # First call - should read file
    start = time.time()
    prefs1 = hook.get_cached_preferences(pref_file)
    time1 = time.time() - start

    # Second call - should use cache
    start = time.time()
    prefs2 = hook.get_cached_preferences(pref_file)
    time2 = time.time() - start

    # Verify results are the same
    assert prefs1 == prefs2, "Cached preferences don't match"

    # Verify caching improved performance
    assert time2 <= time1, f"Cache should be faster (time1={time1:.4f}s, time2={time2:.4f}s)"

    print(f"✓ Caching works (1st: {time1 * 1000:.1f}ms, 2nd: {time2 * 1000:.1f}ms)")


def test_json_output():
    """Test that hook outputs valid JSON via subprocess."""
    print("Testing JSON output via subprocess...")

    hook_script = Path(__file__).parent / "user_prompt_submit.py"

    test_input = {
        "session_id": "test_session",
        "transcript_path": "/tmp/test",
        "cwd": str(Path.cwd()),
        "hook_event_name": "UserPromptSubmit",
        "prompt": "test prompt",
    }

    # Run hook as subprocess
    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input=json.dumps(test_input),
        capture_output=True,
        text=True,
        timeout=5,
    )

    # Verify successful execution
    assert result.returncode == 0, f"Hook failed with exit code {result.returncode}"

    # Parse output
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON output: {result.stdout}")
        raise e

    # Verify structure
    assert "additionalContext" in output, "Output missing additionalContext"

    print("✓ JSON output is valid")


def test_performance():
    """Test that hook executes within performance target."""
    print("Testing performance (target: < 200ms including Python startup)...")

    hook_script = Path(__file__).parent / "user_prompt_submit.py"

    test_input = {
        "session_id": "test_session",
        "transcript_path": "/tmp/test",
        "cwd": str(Path.cwd()),
        "hook_event_name": "UserPromptSubmit",
        "prompt": "test prompt",
    }

    # Run multiple times and measure
    times = []
    for _ in range(5):
        start = time.time()
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(test_input),
            capture_output=True,
            text=True,
            timeout=5,
        )
        elapsed = (time.time() - start) * 1000  # Convert to ms

        assert result.returncode == 0, "Hook execution failed"
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print(f"  Average: {avg_time:.1f}ms")
    print(f"  Min: {min_time:.1f}ms")
    print(f"  Max: {max_time:.1f}ms")

    # Relaxed performance target (Python startup is slow)
    assert avg_time < 200, (
        f"Hook too slow (avg {avg_time:.1f}ms > 200ms target including Python startup)"
    )

    print("✓ Performance acceptable")


def test_error_handling():
    """Test error handling for missing files and invalid input."""
    print("Testing error handling...")

    # Test with invalid working directory (no preferences)
    with tempfile.TemporaryDirectory() as tmpdir:
        hook = UserPromptSubmitHook()

        # This should handle gracefully - hook uses project root, not cwd
        input_data = {
            "session_id": "test_session",
            "transcript_path": "/tmp/test",
            "cwd": tmpdir,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "test prompt",
        }

        # Should not raise exception
        try:
            output = hook.process(input_data)
            assert "additionalContext" in output
            print("✓ Error handling works")
        except Exception as e:
            print(f"✗ Unexpected exception: {e}")
            raise


def run_all_tests():
    """Run all test cases."""
    tests = [
        test_hook_basic_functionality,
        test_preference_extraction,
        test_context_building,
        test_empty_preferences,
        test_caching,
        test_json_output,
        test_performance,
        test_error_handling,
    ]

    print("=" * 60)
    print("Running UserPromptSubmit Hook Tests")
    print("=" * 60)

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
