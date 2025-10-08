#!/usr/bin/env python3
"""
Manual Test Script: Stop Hook Visibility Fix

This script demonstrates that the stop hook visibility fix works correctly.
Run this script to manually verify the three bugs were fixed:

1. Reflection module imports work (no ImportError)
2. Decision summary displays even when learnings is empty
3. Output dict is properly initialized

Usage:
    python tests/manual_test_stop_hook_visibility.py
"""

import json
import sys
import tempfile
from pathlib import Path

# Add project paths
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack" / "hooks"))
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack" / "reflection"))


def test_1_reflection_imports():
    """Test 1: Verify reflection module imports work without errors."""
    print("\n" + "=" * 70)
    print("TEST 1: Reflection Module Imports")
    print("=" * 70)

    try:
        # This should NOT raise ImportError (Bug #1 fix)
        from reflection import analyze_session_patterns, process_reflection_analysis

        print("✅ SUCCESS: Reflection module imported without errors")
        print(f"   - analyze_session_patterns: {callable(analyze_session_patterns)}")
        print(f"   - process_reflection_analysis: {callable(process_reflection_analysis)}")

        # Test that analyze_session_patterns works
        patterns = analyze_session_patterns([])
        print(f"✅ SUCCESS: analyze_session_patterns([]) returned: {type(patterns)}")

        return True

    except ImportError as e:
        print(f"❌ FAILED: ImportError - {e}")
        return False
    except Exception as e:
        print(f"⚠️  WARNING: Unexpected error - {e}")
        return False


def test_2_decision_summary_visibility():
    """Test 2: Verify decision summary displays even with empty learnings."""
    print("\n" + "=" * 70)
    print("TEST 2: Decision Summary Visibility (Empty Learnings)")
    print("=" * 70)

    try:
        from unittest.mock import patch

        from stop import StopHook

        # Create temporary test environment
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup hook with temporary paths
            hook = StopHook()
            hook.project_root = Path(temp_dir)
            hook.log_dir = Path(temp_dir) / ".claude" / "runtime" / "logs"
            hook.metrics_dir = Path(temp_dir) / ".claude" / "runtime" / "metrics"
            hook.analysis_dir = Path(temp_dir) / ".claude" / "runtime" / "analysis"
            hook.log_dir.mkdir(parents=True, exist_ok=True)
            hook.metrics_dir.mkdir(parents=True, exist_ok=True)
            hook.analysis_dir.mkdir(parents=True, exist_ok=True)
            hook.session_id = "manual_test_session"
            hook.session_dir = hook.log_dir / hook.session_id
            hook.session_dir.mkdir(parents=True, exist_ok=True)

            # Create DECISIONS.md file
            decisions_file = hook.session_dir / "DECISIONS.md"
            decisions_content = """# Session Decisions

## Decision: Use PostgreSQL for database
**What**: Selected PostgreSQL as primary database
**Why**: Better support for complex queries
**Alternatives**: MySQL, MongoDB

## Decision: Implement REST API
**What**: Build REST API endpoints
**Why**: Simpler than GraphQL for this use case
**Alternatives**: GraphQL, gRPC
"""
            decisions_file.write_text(decisions_content, encoding="utf-8")

            print(f"📁 Created test DECISIONS.md: {decisions_file}")
            print("   Contains 2 decisions")

            # Mock extract_learnings to return EMPTY list (the critical bug scenario)
            with patch.object(hook, "extract_learnings", return_value=[]):
                with patch.object(hook, "save_session_analysis"):
                    # Process with messages
                    input_data = {
                        "messages": [{"role": "user", "content": "test message"}],
                        "session_id": hook.session_id,
                    }

                    print("\n🔄 Processing stop hook with EMPTY learnings...")
                    result = hook.process(input_data)

                    # Verify output (Bug #2 fix: decision summary should be visible)
                    print("\n📊 Result Analysis:")
                    print(f"   - Result type: {type(result)}")
                    print(f"   - Result keys: {list(result.keys())}")

                    if "message" in result:
                        print("✅ SUCCESS: 'message' field exists in output")
                        message = result["message"]
                        print(f"   - Message length: {len(message)} characters")

                        if "Decision Records Summary" in message:
                            print("✅ SUCCESS: Decision summary appears in message")
                        else:
                            print("❌ FAILED: Decision summary NOT in message")
                            return False

                        if "PostgreSQL" in message:
                            print("✅ SUCCESS: Decision content visible in message")
                        else:
                            print("❌ FAILED: Decision content NOT visible")
                            return False

                        # Display sample of message
                        print("\n📝 Message Preview (first 500 chars):")
                        print("-" * 70)
                        print(message[:500])
                        if len(message) > 500:
                            print("... (truncated)")
                        print("-" * 70)

                    else:
                        print("❌ FAILED: 'message' field missing from output")
                        print(f"   Actual output: {result}")
                        return False

                    # Verify no metadata field (since no learnings)
                    if "metadata" not in result:
                        print("✅ SUCCESS: No 'metadata' field (expected with empty learnings)")
                    else:
                        print("⚠️  WARNING: 'metadata' field exists despite empty learnings")

                    return True

    except Exception as e:
        print(f"❌ FAILED: Exception - {e}")
        import traceback

        traceback.print_exc()
        return False


def test_3_output_dict_initialization():
    """Test 3: Verify output dict is properly initialized before use."""
    print("\n" + "=" * 70)
    print("TEST 3: Output Dict Initialization")
    print("=" * 70)

    try:
        from unittest.mock import patch

        from stop import StopHook

        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup hook
            hook = StopHook()
            hook.project_root = Path(temp_dir)
            hook.log_dir = Path(temp_dir) / ".claude" / "runtime" / "logs"
            hook.metrics_dir = Path(temp_dir) / ".claude" / "runtime" / "metrics"
            hook.analysis_dir = Path(temp_dir) / ".claude" / "runtime" / "analysis"
            hook.log_dir.mkdir(parents=True, exist_ok=True)
            hook.metrics_dir.mkdir(parents=True, exist_ok=True)
            hook.analysis_dir.mkdir(parents=True, exist_ok=True)
            hook.session_id = "init_test_session"
            hook.session_dir = hook.log_dir / hook.session_id
            hook.session_dir.mkdir(parents=True, exist_ok=True)

            # Create DECISIONS.md
            decisions_file = hook.session_dir / "DECISIONS.md"
            decisions_file.write_text("## Decision: Test\n", encoding="utf-8")

            # Mock to ensure learnings is empty
            with patch.object(hook, "extract_learnings", return_value=[]):
                with patch.object(hook, "save_session_analysis"):
                    input_data = {
                        "messages": [{"role": "user", "content": "test"}],
                        "session_id": hook.session_id,
                    }

                    print("🔄 Processing stop hook...")

                    # Should NOT raise KeyError or AttributeError (Bug #3 fix)
                    try:
                        result = hook.process(input_data)
                        print("✅ SUCCESS: No KeyError or AttributeError raised")

                        # Verify result is valid dict
                        if isinstance(result, dict):
                            print("✅ SUCCESS: Result is a valid dict")
                        else:
                            print(f"❌ FAILED: Result is not dict, got {type(result)}")
                            return False

                        # Verify JSON serializable
                        try:
                            json_str = json.dumps(result)
                            print("✅ SUCCESS: Result is JSON serializable")
                            print(f"   JSON length: {len(json_str)} characters")
                        except (TypeError, ValueError) as e:
                            print(f"❌ FAILED: Result not JSON serializable - {e}")
                            return False

                        return True

                    except (KeyError, AttributeError) as e:
                        print(f"❌ FAILED: {type(e).__name__} raised - {e}")
                        print("   This means output dict was not properly initialized")
                        return False

    except Exception as e:
        print(f"❌ FAILED: Exception - {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all manual tests."""
    print("\n" + "=" * 70)
    print("MANUAL TEST SUITE: Stop Hook Visibility Fix")
    print("=" * 70)
    print("\nThis script verifies the three bugs were fixed:")
    print("1. Reflection module imports work without ImportError")
    print("2. Decision summary displays even when learnings is empty")
    print("3. Output dict is properly initialized before use")
    print()

    results = []

    # Run all tests
    results.append(("Test 1: Reflection Imports", test_1_reflection_imports()))
    results.append(("Test 2: Decision Summary Visibility", test_2_decision_summary_visibility()))
    results.append(("Test 3: Output Dict Initialization", test_3_output_dict_initialization()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print()
    print(f"Total: {passed} passed, {failed} failed out of {len(results)} tests")
    print("=" * 70)

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! The visibility fix is working correctly.")
        return 0
    print(f"\n⚠️  {failed} TEST(S) FAILED. Please review the output above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
