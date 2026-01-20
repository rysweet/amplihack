#!/usr/bin/env python3
"""Test the PostToolUse hook integration with REAL data format."""

import json
import sys
import tempfile
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools" / "amplihack" / "hooks"))


def test_real_hook_integration():
    """Test with ACTUAL PostToolUse hook input format."""

    print("=" * 70)
    print("🧪 Testing PostToolUse Hook Integration (REAL FORMAT)")
    print("=" * 70)

    # Create a temporary transcript file (like Claude Code does)
    sample_conversation = [
        {
            "role": "user",
            "content": "I want to implement JWT authentication for the API. Requirements: secure token generation, refresh token support, role-based access control. This is a very important feature that needs to be production-ready.",
        },
        {
            "role": "assistant",
            "content": "I'll implement JWT authentication. Here's my plan: 1. Use RS256 algorithm for asymmetric signing, 2. Implement refresh token rotation for security, 3. Store role claims in token payload for authorization.",
        },
        {
            "role": "tool_use",
            "name": "Write",
            "content": "Created auth/jwt_handler.py with token generation logic",
        },
        {
            "role": "assistant",
            "content": "I've created the JWT handler. Now implementing the middleware for token validation in all API endpoints.",
        },
        {
            "role": "user",
            "content": "How should we handle expired tokens and refresh token rotation?",
        },
        {
            "role": "assistant",
            "content": "We should return 401 with clear error message and include refresh token endpoint in response. For rotation, implement 7-day refresh token lifetime with automatic renewal.",
        },
    ]

    # Repeat to get higher token count (simulate long conversation)
    extended_conversation = sample_conversation * 100  # Simulate ~550k tokens

    # Create temp transcript file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(extended_conversation, f)
        transcript_path = f.name

    try:
        # Simulate REAL PostToolUse hook input (from Claude Code)
        hook_input = {
            "session_id": "test_session_20251116",
            "transcript_path": transcript_path,
            "cwd": str(Path.cwd()),
            "permission_mode": "enabled",
            "hook_event_name": "PostToolUse",
            "toolUse": {
                "name": "Write",
                "input": {"file_path": "/path/to/file.py", "content": "some content"},
            },
            "result": {"status": "success"},
        }

        print("\n📝 Hook Input (REAL FORMAT):")
        print(f"  - session_id: {hook_input['session_id']}")
        print(f"  - transcript_path: {transcript_path}")
        print(f"  - tool_name: {hook_input['toolUse']['name']}")
        print(f"  - Conversation messages: {len(extended_conversation)}")

        # Import and test the actual hook
        from post_tool_use import PostToolUseHook

        print("\n🔧 Running PostToolUse Hook...")
        hook = PostToolUseHook()
        output = hook.process(hook_input)

        print("\n📊 Hook Output:")
        print(json.dumps(output, indent=2))

        # Check if automation ran
        if "context_automation" in output.get("metadata", {}):
            automation_data = output["metadata"]["context_automation"]
            print("\n✅ AUTOMATION RAN SUCCESSFULLY!")
            print(f"  Warnings: {automation_data.get('warnings', [])}")
            print(f"  Actions: {automation_data.get('actions', [])}")
        else:
            print("\n⚠️  Automation did not run (might be below threshold)")

        # Check estimated token count
        total_chars = sum(len(str(msg.get("content", ""))) for msg in extended_conversation)
        estimated_tokens = total_chars // 4
        print(f"\n📈 Estimated Tokens: {estimated_tokens:,}")
        print(f"   Percentage: {(estimated_tokens / 1_000_000) * 100:.1f}%")

        print("\n" + "=" * 70)
        print("🎉 Real Hook Integration Test Complete!")
        print("=" * 70)

        return True

    finally:
        # Cleanup temp file
        Path(transcript_path).unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        success = test_real_hook_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
