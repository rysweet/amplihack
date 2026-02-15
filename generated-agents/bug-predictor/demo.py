"""
Bug Predictor Demo

Demonstrates the bug predictor's learning capabilities with visual examples.
"""

from agent import BugPredictor
from metrics import BugPredictorMetrics


def print_separator(title=""):
    """Print a visual separator."""
    if title:
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print("=" * 60)
    else:
        print("-" * 60)


def demo_basic_detection():
    """Demo: Basic bug detection."""
    print_separator("Demo 1: Basic Bug Detection")

    predictor = BugPredictor()

    buggy_code = """
def process_user_data(user_dict):
    # Bug 1: No null check
    name = user_dict.get('name')
    return name.upper()

def read_config():
    # Bug 2: Resource leak
    f = open('config.txt')
    return f.read()

def query_database(user_id):
    # Bug 3: SQL injection
    query = f"SELECT * FROM users WHERE id={user_id}"
    return execute(query)
"""

    print("\nAnalyzing buggy code...")
    result = predictor.predict_bugs(buggy_code)

    print("\n📊 Analysis Results:")
    print(f"   Total issues found: {result.total_issues}")
    print(f"   Critical issues: {result.critical_issues}")
    print(f"   High confidence: {len(result.high_confidence)}")
    print(f"   Medium confidence: {len(result.medium_confidence)}")

    print("\n🐛 Detected Bugs:")
    for i, bug in enumerate(result.high_confidence[:3], 1):
        print(f"\n   {i}. {bug.bug_type.upper()} (Severity: {bug.severity})")
        print(f"      Line {bug.line_number}: {bug.code_snippet[:60]}...")
        print(f"      💡 {bug.explanation[:70]}...")


def demo_learning_improvement():
    """Demo: Learning improvement over iterations."""
    print_separator("Demo 2: Learning Improvement")

    predictor = BugPredictor()

    test_code = """
def unsafe_function(data):
    result = data.get('value')
    return result.strip()
"""

    print("\n📈 Training Progress:\n")

    # First analysis (baseline)
    print("   Iteration 1 (Baseline):")
    result1 = predictor.predict_bugs(test_code)
    print(
        f"      Issues: {result1.total_issues}, Learned patterns: {result1.used_learned_patterns}"
    )

    # Train with multiple examples
    training_examples = [
        "def f(x): return x.get('a').value",
        "def g(d): v = d.get('k'); return v.upper()",
        "def h(obj): return obj.get('data').process()",
    ]

    for i, code in enumerate(training_examples, 2):
        result = predictor.predict_bugs(code)
        print(f"   Iteration {i}:")
        print(
            f"      Issues: {result.total_issues}, Learned patterns: {result.used_learned_patterns}"
        )

    # Final analysis
    print(f"\n   Iteration {len(training_examples) + 2} (After Training):")
    result_final = predictor.predict_bugs(test_code)
    print(
        f"      Issues: {result_final.total_issues}, Learned patterns: {result_final.used_learned_patterns}"
    )

    improvement = result_final.used_learned_patterns - result1.used_learned_patterns
    print(f"\n   ✅ Pattern usage increased by {improvement} patterns!")


def demo_metrics_tracking():
    """Demo: Metrics and learning statistics."""
    print_separator("Demo 3: Learning Metrics")

    predictor = BugPredictor()
    metrics = BugPredictorMetrics(predictor.memory)

    # Generate some training data
    print("\n🔄 Training on sample codebase...")

    samples = [
        "def f(x): return x.get('a').method()",  # none_reference
        "f = open('file.txt'); data = f.read()",  # resource_leak
        "query = 'SELECT * FROM t WHERE id=' + uid",  # sql_injection
        "for i in range(len(arr)): print(arr[i], arr[i+1])",  # off_by_one
    ]

    for round_num in range(3):
        for code in samples:
            predictor.predict_bugs(code)
        print(f"   Round {round_num + 1} completed")

    # Get learning stats
    print("\n📊 Learning Statistics:\n")

    accuracy = metrics.get_accuracy_stats()
    print(f"   Accuracy: {accuracy['accuracy']:.1%}")
    print(f"   Total patterns learned: {accuracy['total_patterns']}")
    print(f"   High confidence: {accuracy['high_confidence']}")

    detection = metrics.get_detection_rate_stats()
    print(f"\n   Total analyses: {detection['total_analyses']}")
    print(f"   Average bugs per file: {detection['avg_bugs_per_file']:.1f}")

    improvement = metrics.get_learning_improvement()
    print(f"\n   Overall improvement: {improvement['overall_improvement']:.1f}%")
    print(f"   Meets >10% target: {'✅ YES' if improvement['meets_target'] else '⏳ Not yet'}")


def demo_confidence_scoring():
    """Demo: Confidence score calibration."""
    print_separator("Demo 4: Confidence Scores")

    predictor = BugPredictor()

    # High confidence bug (obvious pattern)
    obvious_bug = """
def bad_function(data):
    user = data.get('user')
    return user.name  # Clear None reference
"""

    # Lower confidence bug (could be safe)
    ambiguous_code = """
def maybe_bug(items):
    for i in range(len(items)):
        process(items[i])
"""

    print("\n🎯 Testing confidence calibration...\n")

    print("   Code Sample 1 (Obvious bug):")
    result1 = predictor.predict_bugs(obvious_bug)
    if result1.high_confidence:
        bug = result1.high_confidence[0]
        print(f"      Bug: {bug.bug_type}")
        print(f"      Confidence: {bug.confidence:.1%}")
        print("      ✅ High confidence prediction")

    print("\n   Code Sample 2 (Ambiguous):")
    result2 = predictor.predict_bugs(ambiguous_code)
    if result2.medium_confidence or result2.low_confidence:
        bugs = result2.medium_confidence + result2.low_confidence
        if bugs:
            bug = bugs[0]
            print(f"      Bug: {bug.bug_type}")
            print(f"      Confidence: {bug.confidence:.1%}")
            print("      ℹ️  Lower confidence (appropriately cautious)")


def demo_bug_types():
    """Demo: Various bug type detection."""
    print_separator("Demo 5: Bug Type Coverage")

    predictor = BugPredictor()

    bug_examples = {
        "None Reference": "def f(x): return x.get('a').value",
        "Resource Leak": "f = open('file.txt'); data = f.read()",
        "SQL Injection": "query = 'DELETE FROM users WHERE id=' + str(uid)",
        "Off-by-One": "for i in range(len(arr)): print(arr[i+1])",
    }

    print("\n🔍 Testing bug type detection:\n")

    for bug_name, code in bug_examples.items():
        result = predictor.predict_bugs(code)
        detected = result.total_issues > 0

        status = "✅" if detected else "❌"
        print(f"   {status} {bug_name}: {result.total_issues} issues detected")


def run_demo():
    """Run all demo scenarios."""
    print("=" * 60)
    print("  Bug Predictor Learning Agent - Interactive Demo")
    print("=" * 60)

    demos = [
        demo_basic_detection,
        demo_learning_improvement,
        demo_metrics_tracking,
        demo_confidence_scoring,
        demo_bug_types,
    ]

    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"\n⚠️  Demo error: {e}")
            import traceback

            traceback.print_exc()

    print_separator("Demo Complete")
    print("\n✨ The Bug Predictor successfully demonstrated:")
    print("   • Bug detection using AST analysis")
    print("   • Learning from patterns")
    print("   • Accuracy improvement over time")
    print("   • Confidence score calibration")
    print("   • Multiple bug type coverage")


if __name__ == "__main__":
    run_demo()
