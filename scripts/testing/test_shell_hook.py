#!/usr/bin/env python3
"""
Test script for the shell command hook functionality.

This script simulates the UserPromptSubmit hook input and tests
various scenarios to ensure the hook works correctly.
"""

import json
import subprocess
from pathlib import Path


def test_hook_with_input(prompt: str, session_id: str = "test-session") -> dict:
    """
    Test the shell command hook with given input.

    Args:
        prompt: The prompt to test
        session_id: Session ID for the test

    Returns:
        Dictionary with test results
    """
    # Create test input
    test_input = {
        "session_id": session_id,
        "transcript_path": "/tmp/test-transcript",
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
    }

    # Convert to JSON
    input_json = json.dumps(test_input)

    # Run the hook
    hook_path = Path(__file__).parent / ".claude" / "hooks" / "user_prompt_submit.py"

    try:
        result = subprocess.run(
            ["python3", str(hook_path)],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Parse output if any
        output = None
        if result.stdout.strip():
            try:
                output = json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                output = {"raw_output": result.stdout.strip()}

        return {
            "success": True,
            "exit_code": result.returncode,
            "output": output,
            "stderr": result.stderr.strip() if result.stderr else None,
            "blocked": output is not None and output.get("decision") == "block",
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Hook execution timed out",
            "exit_code": -1,
            "blocked": False,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "exit_code": -1, "blocked": False}


def run_tests():
    """Run comprehensive tests of the shell command hook."""
    test_cases = [
        {
            "name": "Normal prompt (should not block)",
            "prompt": "Hello, how are you?",
            "should_block": False,
        },
        {"name": "Empty shell command", "prompt": "!", "should_block": True},
        {"name": "Simple shell command", "prompt": "!echo 'Hello World'", "should_block": True},
        {"name": "List files command", "prompt": "!ls -la", "should_block": True},
        {"name": "Current directory command", "prompt": "!pwd", "should_block": True},
        {"name": "Date command", "prompt": "!date", "should_block": True},
        {
            "name": "Potentially dangerous command (should be blocked)",
            "prompt": "!rm -rf /",
            "should_block": True,
        },
        {"name": "Command with spaces", "prompt": "!echo 'test with spaces'", "should_block": True},
    ]

    print("🧪 Testing Shell Command Hook Functionality")
    print("=" * 50)

    passed = 0
    total = len(test_cases)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Input: {test_case['prompt']}")

        result = test_hook_with_input(test_case["prompt"])

        if result["success"]:
            blocked = result["blocked"]
            should_block = test_case["should_block"]

            if blocked == should_block:
                print(f"   ✅ PASS - {'Blocked' if blocked else 'Allowed'} as expected")
                if blocked and result["output"]:
                    reason = result["output"].get("reason", "")
                    preview = reason[:100] + "..." if len(reason) > 100 else reason
                    print(f"   📝 Reason: {preview}")
                passed += 1
            else:
                print(
                    f"   ❌ FAIL - Expected {'block' if should_block else 'allow'}, got {'block' if blocked else 'allow'}"
                )
        else:
            print(f"   ❌ FAIL - Hook execution failed: {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 50)
    print(f"🏁 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Shell command hook is working correctly.")
        return True
    print("❌ Some tests failed. Please review the implementation.")
    return False


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
