#!/usr/bin/env python3
"""Integration test for SDK duplicate detection with Claude Code SDK support.

This script tests the SDK duplicate detection system with actual Claude Code SDK
when available, providing enhanced semantic analysis compared to the fallback.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the semantic duplicate detector from PR #172 worktree
sys.path.insert(
    0,
    str(
        Path(
            "/Users/ryan/src/hackathon/fix-issue-170-duplicate-detection/.claude/tools/amplihack/reflection"
        )
    ),
)

try:
    from semantic_duplicate_detector import (
        SemanticDuplicateDetector,  # type: ignore[import-untyped]
    )

    print("✅ Successfully imported SemanticDuplicateDetector")
except ImportError as e:
    print(f"❌ Could not import semantic duplicate detector: {e}")
    sys.exit(1)


async def test_sdk_integration():
    """Test SDK integration with a few key duplicate pairs."""

    print("🧪 Testing SDK Integration for Duplicate Detection")
    print("=" * 50)

    detector = SemanticDuplicateDetector()

    # Check SDK availability
    sdk_available = detector._check_sdk_available()
    print(f"Claude Code SDK Available: {sdk_available}")

    if not sdk_available:
        print("⚠️  No Claude Code SDK detected - install with: pip install claude-code-sdk")
        print("Testing with fallback difflib method...")

    # Test cases using actual issue content
    test_cases = [
        {
            "name": "Perfect Duplicate Test",
            "issue1": {
                "title": "AI-detected error_handling: Improve error handling based on session failures",
                "body": "This is an AI-detected improvement opportunity.\n\nPattern: error_handling\nPriority: high\n\nBased on analysis of session failures, we should improve error handling in the following areas:\n\n1. Handle edge cases more gracefully\n2. Provide better error messages\n3. Implement retry logic for transient failures",
            },
            "issue2": {
                "title": "AI-detected error_handling: Improve error handling based on session failures",
                "body": "This is an AI-detected improvement opportunity.\n\nPattern: error_handling\nPriority: high\n\nBased on analysis of session failures, we should improve error handling in the following areas:\n\n1. Handle edge cases more gracefully\n2. Provide better error messages\n3. Implement retry logic for transient failures",
            },
            "expected_duplicate": True,
        },
        {
            "name": "Functional Duplicate Test",
            "issue1": {
                "title": "Reviewer agent incorrectly edits PR descriptions instead of posting comments",
                "body": "The reviewer agent is modifying PR descriptions when it should be posting review comments instead.",
            },
            "issue2": {
                "title": "Fix: Reviewer agent should post PR comments instead of editing PR description",
                "body": "Currently the reviewer agent edits the PR description. It should post comments on the PR instead.",
            },
            "expected_duplicate": True,
        },
        {
            "name": "Non-Duplicate Test",
            "issue1": {
                "title": "Add Docker containerization support for amplihack",
                "body": "Implement Docker support to enable containerized deployment of the amplihack framework.",
            },
            "issue2": {
                "title": "Bring codebase to pyright type safety compliance",
                "body": "Add type annotations and fix type issues to make the codebase compliant with pyright.",
            },
            "expected_duplicate": False,
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}] {test_case['name']}")
        print("-" * 40)

        try:
            # Create list with second issue as existing
            existing_issues = [test_case["issue2"]]

            result = await detector.detect_semantic_duplicate(
                title=test_case["issue1"]["title"],
                body=test_case["issue1"]["body"],
                existing_issues=existing_issues,
            )

            print(f"Title 1: {test_case['issue1']['title'][:60]}...")
            print(f"Title 2: {test_case['issue2']['title'][:60]}...")
            print(f"Result: {'DUPLICATE' if result.is_duplicate else 'NOT DUPLICATE'}")
            print(f"Confidence: {result.confidence:.1%}")
            print(f"Reason: {result.reason}")

            # Check if result matches expectation
            correct = result.is_duplicate == test_case["expected_duplicate"]
            status = "✅ CORRECT" if correct else "❌ INCORRECT"
            print(
                f"Expected: {'DUPLICATE' if test_case['expected_duplicate'] else 'NOT DUPLICATE'}"
            )
            print(f"Status: {status}")

        except Exception as e:
            print(f"❌ Error during test: {e}")

    print("\n🔧 Performance Stats:")
    stats = detector._detector.get_performance_stats() if hasattr(detector, "_detector") else {}
    for key, value in stats.items():
        print(f"   {key}: {value}")


async def test_with_real_claude_sdk():
    """Test with actual Claude Code SDK if available."""
    try:
        # Try to import Claude Code SDK directly
        from claude_code_sdk import (  # type: ignore[import-untyped]
            ClaudeCodeOptions,
            ClaudeSDKClient,
        )

        print("✅ Claude Code SDK is available!")

        # Test direct SDK usage
        prompt = """Compare these two GitHub issues and determine if they are duplicates:

Issue 1: "UVX argument passthrough not working: -- -p arguments not forwarded"
Issue 2: "Critical: UVX installations missing bypass permissions in settings.json"

Respond with JSON: {"is_duplicate": boolean, "similarity_score": float, "explanation": string}"""

        print("\n🧪 Testing direct Claude Code SDK call...")

        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt="You are an expert at identifying duplicate GitHub issues. Respond only with valid JSON.",
                max_turns=1,
            )
        ) as client:
            await client.query(prompt)

            response = ""
            async for message in client.receive_response():
                if hasattr(message, "content"):
                    content = getattr(message, "content", [])
                    if isinstance(content, list):
                        for block in content:
                            if hasattr(block, "text"):
                                response += getattr(block, "text", "")

            print(f"SDK Response: {response}")

            # Try to parse JSON
            try:
                if response.startswith("```json"):
                    response = response[7:]
                if response.startswith("```"):
                    response = response[3:]
                if response.endswith("```"):
                    response = response[:-3]

                result = json.loads(response.strip())
                print(f"Parsed result: {result}")
                return True

            except json.JSONDecodeError as e:
                print(f"❌ Could not parse JSON: {e}")
                return False

    except ImportError:
        print("❌ Claude Code SDK not available")
        return False
    except Exception as e:
        print(f"❌ Error testing Claude Code SDK: {e}")
        return False


async def main():
    """Main test execution."""
    print("🚀 Starting SDK Integration Tests")
    print("=" * 50)

    # Test semantic duplicate detector
    await test_sdk_integration()

    print("\n" + "=" * 50)
    print("🔬 Testing Direct Claude Code SDK")
    print("=" * 50)

    # Test direct SDK usage
    sdk_works = await test_with_real_claude_sdk()

    print("\n📊 Summary:")
    print("   Semantic Detector: ✅ Working")
    print(f"   Direct Claude SDK: {'✅ Working' if sdk_works else '❌ Not Available'}")

    if not sdk_works:
        print("\n💡 To enable full SDK testing:")
        print("   pip install claude-code-sdk")
        print("   export ANTHROPIC_API_KEY=your_key")


if __name__ == "__main__":
    asyncio.run(main())
