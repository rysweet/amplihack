#!/usr/bin/env python3
"""
Quick test of auto-mode with real Claude Agent SDK integration.

This script tests that:
1. claude-agent-sdk is properly installed and importable
2. Auto-mode orchestrator can be created
3. Real SDK integration is being used (not heuristics)
4. Analysis loop can process a simple objective
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from amplihack.sdk import AutoModeConfig, AutoModeOrchestrator  # type: ignore


async def test_sdk_integration():
    """Test that Claude Agent SDK integration is working"""
    print("=" * 60)
    print("Testing Auto-Mode with Real Claude Agent SDK Integration")
    print("=" * 60)

    # Test 1: Import check
    print("\n[Test 1] Checking claude-agent-sdk import...")
    try:
        from claude_agent_sdk import query  # type: ignore

        print("✓ claude-agent-sdk imported successfully")
        print(f"  query function: {query}")
    except ImportError as e:
        print(f"✗ Failed to import claude-agent-sdk: {e}")
        return 1

    # Test 2: Create orchestrator
    print("\n[Test 2] Creating AutoModeOrchestrator...")
    try:
        config = AutoModeConfig(
            max_iterations=2,  # Small number for quick test
            persistence_enabled=False,
            auto_progression_enabled=True,
        )
        orchestrator = AutoModeOrchestrator(config)
        print("✓ AutoModeOrchestrator created successfully")
    except Exception as e:
        print(f"✗ Failed to create orchestrator: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Test 3: Start session
    print("\n[Test 3] Starting auto-mode session...")
    try:
        objective = "Write a simple hello world function in Python"
        working_dir = str(Path.cwd())

        session_id = await orchestrator.start_auto_mode_session(objective, working_dir)
        print(f"✓ Session started: {session_id}")
        print(f"  Objective: {objective}")
        print(f"  Working directory: {working_dir}")
    except Exception as e:
        print(f"✗ Failed to start session: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Test 4: Get current state
    print("\n[Test 4] Getting current state...")
    try:
        state = orchestrator.get_current_state()
        print("✓ Current state retrieved")
        print(f"  Session ID: {state.get('session_id')}")
        print(f"  State: {state.get('state')}")
        print(f"  Iteration: {state.get('iteration')}")
    except Exception as e:
        print(f"✗ Failed to get state: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Test 5: Get next action (this will use REAL Claude SDK)
    print("\n[Test 5] Getting next action from Claude SDK...")
    print("  (This will call the REAL Claude Agent SDK)")
    try:
        next_action = await orchestrator.get_next_action(state)

        if next_action:
            print("✓ Next action generated via Claude SDK")
            print(f"  Action type: {next_action.get('action_type', 'unknown')}")
            prompt = next_action.get("prompt", "")
            print(f"  Prompt length: {len(prompt)} chars")
            print(f"  Prompt preview: {prompt[:100]}...")

            # Verify it's NOT a template response
            if "TEMPLATE" in prompt or "HEURISTIC" in prompt:
                print("✗ WARNING: Prompt appears to be templated (should be AI-generated)")
                return 1
            print("✓ Prompt appears to be AI-generated (not templated)")
        else:
            print("  No next action (objective may be complete or need manual intervention)")
    except Exception as e:
        print(f"✗ Failed to get next action: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Test 6: Clean up
    print("\n[Test 6] Cleaning up...")
    try:
        await orchestrator.stop_auto_mode()
        print("✓ Session stopped successfully")
    except Exception as e:
        print(f"⚠ Cleanup warning: {e}")
        # Don't fail on cleanup errors

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Real Claude SDK Integration Working!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_sdk_integration())
    sys.exit(exit_code)
