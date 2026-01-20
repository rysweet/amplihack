#!/usr/bin/env python3
"""
Manual outside-in test for INFORMATIONAL Q&A sessions.

Tests that simple Q&A sessions skip power-steering checks after fix to considerations.yaml.
This is an outside-in test that verifies user-facing behavior.

Usage:
    python3 tests/manual_test_power_steering_qa_sessions.py
"""

import json
import sys
import tempfile
from pathlib import Path

# Add the hooks directory to path
hooks_dir = Path(__file__).parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
sys.path.insert(0, str(hooks_dir))

from power_steering_checker import PowerSteeringChecker


def create_qa_session_transcript(transcript_path: Path) -> None:
    """Create a realistic INFORMATIONAL Q&A session transcript.

    Simulates a user asking 'What hooks are currently configured?'
    and the assistant reading config files and responding.
    """
    print(f"📝 Creating Q&A session transcript at {transcript_path}")

    transcript = [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": "What hooks are currently configured?"
            }
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "Let me check the hooks configuration for you."
                    },
                    {
                        "type": "tool_use",
                        "id": "toolu_01ABC123",
                        "name": "Read",
                        "input": {
                            "file_path": ".claude/tools/amplihack/hooks/"
                        }
                    }
                ]
            }
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_01ABC123",
                        "content": "stop.py\nsession_stop.py\nerror_protocol.py\nhook_processor.py"
                    }
                ]
            }
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": "The currently configured hooks are:\n\n1. **stop.py** - Stop hook that handles session termination\n2. **session_stop.py** - Session stop event handler\n\nThese hooks are located in `.claude/tools/amplihack/hooks/`."
            }
        }
    ]

    # Write as JSONL format (one JSON object per line)
    with open(transcript_path, 'w') as f:
        for entry in transcript:
            f.write(json.dumps(entry) + '\n')

    print(f"✅ Created transcript with {len(transcript)} entries")


def create_simple_question_transcript(transcript_path: Path) -> None:
    """Create an even simpler Q&A session - just a question and answer.

    Simulates: 'tell me what agents you have'
    """
    print(f"📝 Creating simple question transcript at {transcript_path}")

    transcript = [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": "tell me what agents you have"
            }
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": "I have the following specialized agents available:\n\n- **architect** - System design and specifications\n- **builder** - Code generation from specs\n- **tester** - Test generation and validation\n- **reviewer** - Code review and debugging\n- **api-designer** - API contract design\n- **optimizer** - Performance optimization\n\nThese agents can be invoked using the Task tool with the appropriate subagent_type."
            }
        }
    ]

    with open(transcript_path, 'w') as f:
        for entry in transcript:
            f.write(json.dumps(entry) + '\n')

    print(f"✅ Created simple transcript with {len(transcript)} entries")


def test_qa_session_detection(checker: PowerSteeringChecker, transcript_path: Path) -> bool:
    """Test that Q&A sessions are detected as INFORMATIONAL."""
    print("\n🔍 TEST 1: Session Type Detection")
    print("=" * 60)

    # Load transcript
    transcript = []
    with open(transcript_path) as f:
        for line in f:
            if line.strip():
                transcript.append(json.loads(line))

    session_type = checker.detect_session_type(transcript)

    print(f"Detected session type: {session_type}")

    if session_type == "INFORMATIONAL":
        print("✅ PASS: Session correctly detected as INFORMATIONAL")
        return True
    else:
        print(f"❌ FAIL: Expected INFORMATIONAL, got {session_type}")
        return False


def test_no_applicable_checks(checker: PowerSteeringChecker) -> bool:
    """Test that INFORMATIONAL sessions have no applicable checks."""
    print("\n🔍 TEST 2: Applicable Considerations")
    print("=" * 60)

    applicable = checker.get_applicable_considerations("INFORMATIONAL")

    print(f"Number of applicable checks: {len(applicable)}")

    if len(applicable) == 0:
        print("✅ PASS: No checks apply to INFORMATIONAL sessions")
        return True
    else:
        print(f"❌ FAIL: Expected 0 applicable checks, got {len(applicable)}")
        print("\nApplicable checks:")
        for check in applicable:
            print(f"  - {check['id']}: {check['question']}")
        return False


def test_auto_approval(checker: PowerSteeringChecker, transcript_path: Path, session_id: str) -> bool:
    """Test that INFORMATIONAL sessions auto-approve without blocking."""
    print("\n🔍 TEST 3: Auto-Approval Behavior")
    print("=" * 60)

    try:
        result = checker.check(transcript_path, session_id)

        print(f"Decision: {result.decision}")
        print(f"Reasons: {result.reasons}")

        # Check that it approved
        if result.decision != "approve":
            print(f"❌ FAIL: Expected 'approve', got '{result.decision}'")
            return False

        # Check that it has the right reason
        # Valid reasons for Q&A sessions:
        # - "qa_session": Backward compatibility check (line 702 in checker)
        # - "no_applicable_checks": New session type filtering
        # - "auto_approve_threshold": Auto-approval logic
        expected_reasons = ["qa_session", "no_applicable_checks", "auto_approve_threshold"]
        has_expected_reason = any(reason in result.reasons for reason in expected_reasons)

        if has_expected_reason:
            print(f"✅ PASS: Session auto-approved with reason: {result.reasons}")
            return True
        else:
            print(f"❌ FAIL: Expected reason in {expected_reasons}, got {result.reasons}")
            return False

    except Exception as e:
        print(f"❌ FAIL: Exception during check: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all outside-in tests for INFORMATIONAL Q&A sessions."""
    print("\n" + "=" * 60)
    print("🏴‍☠️  OUTSIDE-IN TEST: INFORMATIONAL Q&A SESSIONS")
    print("=" * 60)
    print("\nTesting power-steering behavior for simple Q&A sessions")
    print("Issue #2021 & #2011: Power-steering should skip checks for Q&A\n")

    # Create temporary project directory
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # Create .claude directory structure
        claude_dir = project_root / ".claude"
        tools_dir = claude_dir / "tools" / "amplihack"
        tools_dir.mkdir(parents=True)

        # Copy considerations.yaml to temp project
        source_considerations = Path(__file__).parent.parent / ".claude" / "tools" / "amplihack" / "considerations.yaml"
        dest_considerations = tools_dir / "considerations.yaml"

        if source_considerations.exists():
            import shutil
            shutil.copy(source_considerations, dest_considerations)
            print(f"📋 Copied considerations.yaml to test project")
        else:
            print(f"⚠️  Warning: Could not find considerations.yaml at {source_considerations}")
            print(f"   Tests will use default considerations")

        # Create power-steering directory
        ps_dir = claude_dir / "runtime" / "power-steering"
        ps_dir.mkdir(parents=True)

        # Create checker instance
        checker = PowerSteeringChecker(project_root=project_root)

        # Test 1: Q&A session with Read tool
        print("\n📌 Scenario 1: Q&A with Read tool")
        print("-" * 60)
        transcript1 = project_root / "transcript-qa.jsonl"
        create_qa_session_transcript(transcript1)

        test1_detection = test_qa_session_detection(checker, transcript1)
        test1_checks = test_no_applicable_checks(checker)
        test1_approval = test_auto_approval(checker, transcript1, "test-session-qa-001")

        # Test 2: Simple question without tools
        print("\n📌 Scenario 2: Simple question (no tools)")
        print("-" * 60)
        transcript2 = project_root / "transcript-simple.jsonl"
        create_simple_question_transcript(transcript2)

        test2_detection = test_qa_session_detection(checker, transcript2)
        test2_approval = test_auto_approval(checker, transcript2, "test-session-simple-002")

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)

        all_tests = [
            ("Scenario 1: Session Type Detection", test1_detection),
            ("Scenario 1: No Applicable Checks", test1_checks),
            ("Scenario 1: Auto-Approval", test1_approval),
            ("Scenario 2: Session Type Detection", test2_detection),
            ("Scenario 2: Auto-Approval", test2_approval),
        ]

        passed = sum(1 for _, result in all_tests if result)
        total = len(all_tests)

        print(f"\nTests Passed: {passed}/{total}")
        print()

        for test_name, result in all_tests:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test_name}")

        print("\n" + "=" * 60)

        if passed == total:
            print("🎉 ALL TESTS PASSED!")
            print("\nThe fix is working correctly:")
            print("- INFORMATIONAL sessions are detected properly")
            print("- No power-steering checks apply to Q&A sessions")
            print("- Sessions auto-approve without blocking")
            print("\n⚓ Fair winds and following seas! The bugs be fixed!")
            return 0
        else:
            print("⚠️  SOME TESTS FAILED")
            print(f"\n{total - passed} test(s) failed - review output above for details")
            return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
