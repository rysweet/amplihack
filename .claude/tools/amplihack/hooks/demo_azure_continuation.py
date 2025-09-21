#!/usr/bin/env python3
"""
Demo script showing how the Azure continuation hook prevents premature stops.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Sample conversation that would typically stop prematurely with Azure OpenAI
DEMO_CONVERSATION = {
    "messages": [
        {
            "role": "user",
            "content": "Please implement these features:\n1. User authentication\n2. Database connection\n3. API endpoints\n4. Unit tests",
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "I'll help you implement these features. Let me create a todo list to track progress.",
                },
                {
                    "type": "tool_use",
                    "id": "demo_1",
                    "name": "TodoWrite",
                    "input": {
                        "todos": [
                            {
                                "content": "Implement user authentication",
                                "status": "completed",
                                "activeForm": "Implementing user authentication",
                            },
                            {
                                "content": "Set up database connection",
                                "status": "completed",
                                "activeForm": "Setting up database connection",
                            },
                            {
                                "content": "Create API endpoints",
                                "status": "in_progress",
                                "activeForm": "Creating API endpoints",
                            },
                            {
                                "content": "Write unit tests",
                                "status": "pending",
                                "activeForm": "Writing unit tests",
                            },
                        ]
                    },
                },
            ],
        },
        {
            "role": "assistant",
            "content": "I've completed the user authentication and database setup. Now let me work on the API endpoints.",
        },
    ]
}


def run_demo():
    """Run demonstration of the Azure continuation hook."""
    hook_path = Path(__file__).parent / "stop_azure_continuation.py"

    print("=" * 60)
    print("Azure Continuation Hook Demo")
    print("=" * 60)

    # Test 1: Without proxy (hook should bypass)
    print("\n1. Testing WITHOUT proxy (normal behavior):")
    print("-" * 40)

    env_no_proxy = os.environ.copy()
    env_no_proxy.pop("ANTHROPIC_BASE_URL", None)
    env_no_proxy.pop("AZURE_OPENAI_KEY", None)

    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(DEMO_CONVERSATION),
        capture_output=True,
        text=True,
        env=env_no_proxy,
    )

    output = json.loads(result.stdout) if result.stdout else {}
    if not output or "decision" not in output:
        print("✓ Hook bypassed (no proxy detected)")
        print("  Result: Would STOP normally")
    else:
        print("✗ Unexpected behavior")

    # Test 2: With proxy (hook should continue)
    print("\n2. Testing WITH Azure proxy:")
    print("-" * 40)

    env_with_proxy = os.environ.copy()
    env_with_proxy["ANTHROPIC_BASE_URL"] = "http://localhost:8080"

    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(DEMO_CONVERSATION),
        capture_output=True,
        text=True,
        env=env_with_proxy,
    )

    output = json.loads(result.stdout) if result.stdout else {}
    if output.get("decision") == "continue":
        print("✓ Hook activated (proxy detected)")
        print("  Decision: CONTINUE")
        print("  Reason: Uncompleted TODO items found")
        print(f"  Instructions: {output.get('instructions', 'N/A')}")
    else:
        print("✗ Hook should have continued")

    # Test 3: Check log file
    print("\n3. Checking hook logs:")
    print("-" * 40)

    project_log = (
        hook_path.parent.parent.parent.parent.parent
        / ".claude"
        / "runtime"
        / "logs"
        / "stop_azure_continuation.log"
    )

    if project_log.exists():
        with open(project_log) as f:
            lines = f.readlines()
            recent_lines = lines[-10:] if len(lines) > 10 else lines
            print("Recent log entries:")
            for line in recent_lines:
                print(f"  {line.strip()}")
    else:
        print("  No log file found (will be created on first real use)")

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)
    print("\nThe hook will automatically activate when:")
    print("1. You launch Claude Code with 'amplihack launch --with-proxy-config'")
    print("2. The Azure OpenAI proxy is running")
    print("3. Claude Code tries to stop prematurely")
    print("\nIt will continue working until all tasks are complete!")


if __name__ == "__main__":
    run_demo()
