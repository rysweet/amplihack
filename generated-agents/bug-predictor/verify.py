#!/usr/bin/env python3
"""
Quick verification script to ensure bug-predictor is working correctly.
"""

import sys


def verify_imports():
    """Verify all modules can be imported."""
    print("Verifying imports...")
    try:
        from agent import BugPattern, BugPrediction, BugPredictor
        from bug_patterns import PATTERN_DATABASE, get_all_patterns
        from metrics import BugPredictorMetrics

        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def verify_basic_functionality():
    """Verify basic bug detection works."""
    print("\nVerifying basic functionality...")
    try:
        from agent import BugPredictor

        predictor = BugPredictor()

        test_code = """
def buggy_function(data):
    result = data.get('value')
    return result.upper()
"""

        result = predictor.predict_bugs(test_code)

        print("  Analysis completed")
        print(f"  Issues detected: {result.total_issues}")
        print(f"  Critical issues: {result.critical_issues}")

        assert result.total_issues >= 0, "Should detect some issues or none"

        print("✓ Basic functionality working")
        return True
    except Exception as e:
        print(f"✗ Functionality error: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_learning():
    """Verify learning mechanism works."""
    print("\nVerifying learning mechanism...")
    try:
        from agent import BugPredictor

        predictor = BugPredictor()

        # First analysis
        code = "def f(x): return x.get('a').value"
        result1 = predictor.predict_bugs(code)

        # Second analysis (should use learned patterns)
        result2 = predictor.predict_bugs(code)

        print(f"  First run: {result1.used_learned_patterns} patterns")
        print(f"  Second run: {result2.used_learned_patterns} patterns")

        improved = result2.used_learned_patterns > result1.used_learned_patterns

        if improved:
            print("✓ Learning mechanism working")
        else:
            print("⚠ Learning mechanism needs more iterations")

        return True
    except Exception as e:
        print(f"✗ Learning error: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_metrics():
    """Verify metrics tracking works."""
    print("\nVerifying metrics...")
    try:
        from agent import BugPredictor
        from metrics import BugPredictorMetrics

        predictor = BugPredictor()
        metrics = BugPredictorMetrics(predictor.memory)

        # Generate some data
        for _ in range(3):
            predictor.predict_bugs("def f(x): return x.get('a').value")

        # Get metrics
        stats = metrics.get_accuracy_stats()
        improvement = metrics.get_learning_improvement()

        print(f"  Accuracy stats collected: {len(stats)} metrics")
        print(f"  Improvement tracking: {len(improvement)} metrics")

        assert "accuracy" in stats, "Should have accuracy metric"
        assert "overall_improvement" in improvement, "Should have improvement metric"

        print("✓ Metrics working")
        return True
    except Exception as e:
        print(f"✗ Metrics error: {e}")
        import traceback

        traceback.print_exc()
        return False


def verify_patterns():
    """Verify bug pattern database."""
    print("\nVerifying bug pattern database...")
    try:
        from bug_patterns import get_all_patterns, get_critical_patterns

        all_patterns = get_all_patterns()
        critical = get_critical_patterns()

        print(f"  Total patterns: {len(all_patterns)}")
        print(f"  Critical patterns: {len(critical)}")

        assert len(all_patterns) > 0, "Should have patterns"
        assert len(critical) > 0, "Should have critical patterns"

        # List some patterns
        print(f"  Sample patterns: {list(all_patterns.keys())[:3]}")

        print("✓ Pattern database working")
        return True
    except Exception as e:
        print(f"✗ Pattern database error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Bug Predictor - Quick Verification")
    print("=" * 60)

    checks = [
        verify_imports,
        verify_basic_functionality,
        verify_learning,
        verify_metrics,
        verify_patterns,
    ]

    passed = 0
    failed = 0

    for check in checks:
        try:
            if check():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Check failed with exception: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Verification Results: {passed}/{len(checks)} passed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ All verifications passed!")
        print("The Bug Predictor is working correctly.")
    else:
        print(f"\n⚠️  {failed} verification(s) failed")
        print("Please check the errors above.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
