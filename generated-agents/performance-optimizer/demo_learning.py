"""
Demo script showing the Performance Optimizer agent's learning capabilities.

This demonstrates how the agent improves its optimization effectiveness
through experience.
"""

import sys

sys.path.insert(0, ".")

from agent import PerformanceOptimizer

# Sample slow code
SLOW_CODE = """
def process_data(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result

def find_value(data, target):
    valid_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    for value in data:
        if value in valid_ids:
            print(f"Valid: {value}")

def build_message(words):
    result = ""
    for word in words:
        result += word + " "
    return result.strip()
"""


def main():
    """Demonstrate learning behavior."""
    print("=" * 70)
    print("Performance Optimizer - Learning Demonstration")
    print("=" * 70)

    # Create optimizer
    print("\n1. Creating Performance Optimizer agent...")
    optimizer = PerformanceOptimizer()

    # First analysis - no prior experience
    print("\n2. FIRST ANALYSIS (No Prior Experience)")
    print("-" * 70)
    analysis1 = optimizer.optimize_code(SLOW_CODE, "example_v1.py")

    print(f"Found {len(analysis1.optimizations)} optimization opportunities")
    print(f"Estimated speedup: {analysis1.estimated_total_speedup:.2f}x\n")

    for opt in analysis1.optimizations:
        status = "✓ APPLIED" if opt.applied else "○ SUGGESTED"
        print(f"{status} {opt.technique}")
        print(f"   Confidence: {opt.confidence:.2%}")
        print(f"   Speedup: {opt.estimated_speedup:.2f}x")
        print(f"   Reason: {opt.reason}\n")

    # Simulate successful learning experiences
    print("\n3. LEARNING PHASE - Simulating Successful Optimizations")
    print("-" * 70)

    learning_data = [
        ("list_comprehension", 1.8, "Loop to comprehension"),
        ("list_comprehension", 1.9, "Another loop optimization"),
        ("list_comprehension", 1.7, "Third successful application"),
        ("set_membership", 8.0, "List to set membership"),
        ("set_membership", 7.5, "Another set optimization"),
        ("join_strings", 15.0, "String concatenation fix"),
        ("join_strings", 12.0, "Another string join"),
    ]

    for technique, speedup, description in learning_data:
        optimizer.store.store_experience(
            exp_type="success",
            context={"type": "optimization", "technique": technique},
            action="applied_optimization",
            outcome={"speedup": speedup},
        )
        print(f"  ✓ Learned: {description} ({speedup:.1f}x speedup)")

    # Update confidence from learned experiences
    print("\n4. UPDATING TECHNIQUE CONFIDENCE FROM EXPERIENCES")
    print("-" * 70)
    optimizer._update_technique_confidence()

    for technique_name, technique in sorted(optimizer.techniques.items()):
        print(f"  {technique_name:35s} confidence: {technique.confidence:.2%}")

    # Second analysis - with learned experience
    print("\n5. SECOND ANALYSIS (After Learning)")
    print("-" * 70)
    analysis2 = optimizer.optimize_code(SLOW_CODE, "example_v2.py")

    print(f"Found {len(analysis2.optimizations)} optimization opportunities")
    print(f"Estimated speedup: {analysis2.estimated_total_speedup:.2f}x\n")

    for opt in analysis2.optimizations:
        status = "✓ APPLIED" if opt.applied else "○ SUGGESTED"
        print(f"{status} {opt.technique}")
        print(f"   Confidence: {opt.confidence:.2%}")
        print(f"   Speedup: {opt.estimated_speedup:.2f}x")
        print(f"   Reason: {opt.reason}\n")

    # Show improvement
    print("\n6. LEARNING IMPROVEMENT SUMMARY")
    print("=" * 70)

    applied_before = len([o for o in analysis1.optimizations if o.applied])
    applied_after = len([o for o in analysis2.optimizations if o.applied])

    print(f"Optimizations applied before learning: {applied_before}")
    print(f"Optimizations applied after learning:  {applied_after}")
    print(f"Improvement: {applied_after - applied_before:+d}")

    # Calculate confidence improvement for techniques that were in both analyses
    confidence_improvements = []
    for opt1 in analysis1.optimizations:
        for opt2 in analysis2.optimizations:
            if opt1.technique == opt2.technique:
                improvement = opt2.confidence - opt1.confidence
                if improvement > 0:
                    confidence_improvements.append((opt1.technique, improvement))

    if confidence_improvements:
        print("\nConfidence improvements:")
        for technique, improvement in confidence_improvements:
            print(f"  {technique:35s} +{improvement:.2%}")

    # Get learning stats
    stats = optimizer.get_learning_stats()
    print("\nLearning Statistics:")
    print(f"  Total optimizations tracked: {stats['total_optimizations']}")
    print(f"  Average speedup: {stats['avg_speedup']:.2f}x")
    print(f"  Learning trend: {stats['trend']}")

    print("\n" + "=" * 70)
    print("Demo complete! The agent learned from experience and now applies")
    print("optimizations more confidently based on proven effectiveness.")
    print("=" * 70)


if __name__ == "__main__":
    main()
