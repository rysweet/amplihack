#!/usr/bin/env python3
"""
Test file for stop_azure_continuation.py hook.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Test data for various scenarios
TEST_MESSAGES_WITH_TODOS = [
    {"role": "user", "content": "Help me implement a feature with user registration and login"},
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "I'll help you implement user registration and login. Let me create a todo list to track this.",
            },
            {
                "type": "tool_use",
                "id": "test_1",
                "name": "TodoWrite",
                "input": {
                    "todos": [
                        {
                            "content": "Create user model",
                            "status": "completed",
                            "activeForm": "Creating user model",
                        },
                        {
                            "content": "Implement registration endpoint",
                            "status": "in_progress",
                            "activeForm": "Implementing registration endpoint",
                        },
                        {
                            "content": "Add login functionality",
                            "status": "pending",
                            "activeForm": "Adding login functionality",
                        },
                        {
                            "content": "Set up authentication",
                            "status": "pending",
                            "activeForm": "Setting up authentication",
                        },
                    ]
                },
            },
        ],
    },
]

TEST_MESSAGES_WITH_CONTINUATION = [
    {"role": "user", "content": "Fix the bug in the authentication system"},
    {
        "role": "assistant",
        "content": "I've identified the issue in the authentication system. The token validation was failing due to an incorrect expiry check. I've fixed that. Next, I'll update the tests to cover this edge case.",
    },
]

TEST_MESSAGES_NO_CONTINUATION = [
    {"role": "user", "content": "What is the purpose of the git status command?"},
    {
        "role": "assistant",
        "content": "The git status command shows the current state of your working directory and staging area. It displays which changes have been staged, which haven't, and which files aren't being tracked by Git.",
    },
]

TEST_MESSAGES_MULTI_REQUEST = [
    {
        "role": "user",
        "content": """Please help me with these tasks:
1. Create a database schema
2. Add API endpoints
3. Write tests
4. Update documentation""",
    },
    {
        "role": "assistant",
        "content": "I'll help you with all these tasks. I've completed the database schema and API endpoints. Now let me work on the tests.",
    },
]


def run_hook(
    messages: List[Dict[str, Any]], env_vars: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Run the hook with given messages and environment.

    Args:
        messages: Test messages to send to hook.
        env_vars: Environment variables to set.

    Returns:
        Hook output as dictionary.
    """
    hook_path = Path(__file__).parent / "stop_azure_continuation.py"

    # Prepare input
    input_data = json.dumps({"messages": messages})

    # Prepare environment
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    try:
        # Run the hook
        result = subprocess.run(
            [sys.executable, str(hook_path)],
            input=input_data,
            capture_output=True,
            text=True,
            env=env,
        )

        # Parse output
        if result.stdout:
            return json.loads(result.stdout)
        return {}
    except Exception as e:
        print(f"Error running hook: {e}")
        return {}


def test_proxy_not_active():
    """Test that hook bypasses when proxy is not active."""
    print("\n=== Test: Proxy Not Active ===")

    # Clear proxy-related environment variables
    clean_env = {
        "ANTHROPIC_BASE_URL": "",
        "CLAUDE_CODE_PROXY_LAUNCHER": "",
        "AZURE_OPENAI_KEY": "",
        "OPENAI_API_KEY": "",
        "OPENAI_BASE_URL": "",
    }

    result = run_hook(TEST_MESSAGES_WITH_TODOS, clean_env)
    print(f"Result: {result}")

    # Should return empty (bypass)
    assert result == {}, f"Expected empty result, got: {result}"
    print("✓ Hook correctly bypassed when proxy not active")


def test_proxy_active_with_todos():
    """Test continuation when proxy is active and TODOs are pending."""
    print("\n=== Test: Proxy Active with Pending TODOs ===")

    # Set proxy environment
    proxy_env = {"ANTHROPIC_BASE_URL": "http://localhost:8080"}

    result = run_hook(TEST_MESSAGES_WITH_TODOS, proxy_env)
    print(f"Result: {result}")

    # Should return continue decision
    assert result.get("decision") == "continue", f"Expected continue decision, got: {result}"
    assert "instructions" in result, "Expected instructions in result"
    print("✓ Hook correctly continues with pending TODOs")


def test_proxy_active_with_continuation_phrases():
    """Test continuation when continuation phrases are detected."""
    print("\n=== Test: Proxy Active with Continuation Phrases ===")

    proxy_env = {"ANTHROPIC_BASE_URL": "http://localhost:8080"}

    result = run_hook(TEST_MESSAGES_WITH_CONTINUATION, proxy_env)
    print(f"Result: {result}")

    # Should return continue decision
    assert result.get("decision") == "continue", f"Expected continue decision, got: {result}"
    print("✓ Hook correctly continues with continuation phrases")


def test_proxy_active_no_continuation():
    """Test that hook allows stop when no continuation is needed."""
    print("\n=== Test: Proxy Active, No Continuation Needed ===")

    proxy_env = {"ANTHROPIC_BASE_URL": "http://localhost:8080"}

    result = run_hook(TEST_MESSAGES_NO_CONTINUATION, proxy_env)
    print(f"Result: {result}")

    # Should return empty (allow stop)
    assert result == {}, f"Expected empty result, got: {result}"
    print("✓ Hook correctly allows stop when no continuation needed")


def test_multi_request_detection():
    """Test detection of multi-part user requests."""
    print("\n=== Test: Multi-Request Detection ===")

    proxy_env = {"AZURE_OPENAI_KEY": "test-key"}

    result = run_hook(TEST_MESSAGES_MULTI_REQUEST, proxy_env)
    print(f"Result: {result}")

    # Should return continue decision
    assert result.get("decision") == "continue", f"Expected continue decision, got: {result}"
    print("✓ Hook correctly detects multi-part requests")


def test_azure_url_detection():
    """Test proxy detection via Azure OpenAI URL."""
    print("\n=== Test: Azure URL Detection ===")

    azure_env = {
        "OPENAI_API_KEY": "test-key",  # pragma: allowlist secret
        "OPENAI_BASE_URL": "https://myinstance.openai.azure.com/openai/deployments/gpt-4",
    }

    result = run_hook(TEST_MESSAGES_WITH_CONTINUATION, azure_env)
    print(f"Result: {result}")

    # Should return continue decision
    assert result.get("decision") == "continue", f"Expected continue decision, got: {result}"
    print("✓ Hook correctly detects Azure via URL")


def test_error_handling():
    """Test that hook handles errors gracefully."""
    print("\n=== Test: Error Handling ===")

    # Send invalid JSON structure
    hook_path = Path(__file__).parent / "stop_azure_continuation.py"

    try:
        result = subprocess.run(
            [sys.executable, str(hook_path)],
            input="invalid json",
            capture_output=True,
            text=True,
            env={"ANTHROPIC_BASE_URL": "http://localhost:8080"},
        )

        # Should still return valid JSON (empty)
        if result.stdout:
            output = json.loads(result.stdout)
            assert output == {}, f"Expected empty result on error, got: {output}"
        print("✓ Hook handles errors gracefully")
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")


def test_completed_todos():
    """Test that hook allows stop when all TODOs are completed."""
    print("\n=== Test: All TODOs Completed ===")

    messages = [
        {"role": "user", "content": "Help me with a task"},
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "name": "TodoWrite",
                    "input": {
                        "todos": [
                            {"content": "Task 1", "status": "completed", "activeForm": "Task 1"},
                            {"content": "Task 2", "status": "completed", "activeForm": "Task 2"},
                        ]
                    },
                }
            ],
        },
    ]

    proxy_env = {"ANTHROPIC_BASE_URL": "http://localhost:8080"}
    result = run_hook(messages, proxy_env)
    print(f"Result: {result}")

    # Should return empty (allow stop)
    assert result == {}, f"Expected empty result with completed TODOs, got: {result}"
    print("✓ Hook correctly allows stop with all TODOs completed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing stop_azure_continuation.py hook")
    print("=" * 60)

    tests = [
        test_proxy_not_active,
        test_proxy_active_with_todos,
        test_proxy_active_with_continuation_phrases,
        test_proxy_active_no_continuation,
        test_multi_request_detection,
        test_azure_url_detection,
        test_completed_todos,
        test_error_handling,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
