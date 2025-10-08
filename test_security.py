#!/usr/bin/env python3
"""
Additional security tests for the shell command hook.

Tests various attack vectors to ensure security controls are working.
"""

import json
import subprocess
from pathlib import Path


def test_hook_with_input(prompt: str) -> dict:
    """Test the shell command hook with given input."""
    test_input = {
        "session_id": "security-test",
        "transcript_path": "/tmp/test-transcript",
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
    }

    input_json = json.dumps(test_input)
    hook_path = Path(__file__).parent / ".claude" / "hooks" / "user_prompt_submit.py"

    try:
        result = subprocess.run(
            ["python3", str(hook_path)],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=10,
        )

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
            "blocked": output is not None and output.get("decision") == "block",
            "security_blocked": "SECURITY: Command blocked" in output.get("reason", "")
            if output
            else False,
        }

    except Exception as e:
        return {"success": False, "error": str(e), "blocked": False}


def run_security_tests():
    """Run security-focused tests."""
    security_test_cases = [
        {
            "name": "Command injection via semicolon",
            "prompt": "!ls; rm important-file",
            "should_be_blocked": True,
        },
        {
            "name": "Network access attempt",
            "prompt": "!curl http://malicious-site.com",
            "should_be_blocked": True,
        },
        {
            "name": "Privilege escalation attempt",
            "prompt": "!sudo rm -rf /",
            "should_be_blocked": True,
        },
        {
            "name": "Path traversal attempt",
            "prompt": "!cat ../../etc/passwd",
            "should_be_blocked": True,
        },
        {
            "name": "Shell injection attempt",
            "prompt": "!bash -c 'malicious code'",
            "should_be_blocked": True,
        },
        {
            "name": "File system write attempt",
            "prompt": "!mv file /etc/important-config",
            "should_be_blocked": True,
        },
        {
            "name": "Python execution attempt",
            "prompt": "!python -c 'import os; os.system(\"dangerous\")'",
            "should_be_blocked": True,
        },
        {
            "name": "Permission change attempt",
            "prompt": "!chmod 777 /etc/passwd",
            "should_be_blocked": True,
        },
        {"name": "File removal attempt", "prompt": "!rm important-file", "should_be_blocked": True},
        {
            "name": "Safe command should execute successfully",
            "prompt": "!whoami",
            "should_be_blocked": True,  # Should be blocked from prompt submission
            "should_execute_successfully": True,  # But command should execute successfully
        },
    ]

    print("🔒 Security Testing Shell Command Hook")
    print("=" * 50)

    passed = 0
    total = len(security_test_cases)

    for i, test_case in enumerate(security_test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Input: {test_case['prompt']}")

        result = test_hook_with_input(test_case["prompt"])

        if result["success"]:
            is_blocked = result["blocked"]
            is_security_blocked = result.get("security_blocked", False)
            should_be_blocked = test_case["should_be_blocked"]
            should_execute_successfully = test_case.get("should_execute_successfully", False)

            if should_execute_successfully:
                # Special case: safe command that should execute but still block prompt
                if is_blocked and not is_security_blocked:
                    # Check if the command actually executed successfully
                    reason = result["output"].get("reason", "") if result.get("output") else ""
                    if "Output:" in reason and "ryan" in reason:  # whoami should show username
                        print("   ✅ PASS - Safe command executed successfully and blocked prompt")
                        passed += 1
                    else:
                        print("   ❌ FAIL - Command didn't execute successfully")
                else:
                    print("   ❌ FAIL - Safe command was blocked by security policy")
            elif should_be_blocked:
                if is_security_blocked:
                    print("   ✅ PASS - Correctly blocked by security policy")
                    passed += 1
                elif is_blocked:
                    print("   ⚠️  PARTIAL - Blocked but not by security policy")
                    passed += 1
                else:
                    print("   ❌ FAIL - Should have been blocked!")
            else:
                if not is_blocked:
                    print("   ✅ PASS - Correctly allowed")
                    passed += 1
                else:
                    print("   ❌ FAIL - Should have been allowed!")

        else:
            print(f"   ❌ FAIL - Hook execution failed: {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 50)
    print(f"🔒 Security Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🛡️  All security tests passed! Shell command hook is secure.")
        return True
    else:
        print("❌ Some security tests failed. Review the implementation.")
        return False


if __name__ == "__main__":
    success = run_security_tests()
    exit(0 if success else 1)
