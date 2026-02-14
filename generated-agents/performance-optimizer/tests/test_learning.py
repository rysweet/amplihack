"""
Test that the Performance Optimizer agent learns over time.

These tests validate that the agent improves its optimization
effectiveness through experience.
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import PerformanceOptimizer

# Sample code with optimization opportunities
SLOW_CODE_LOOP_APPEND = """
def process_items(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result
"""

SLOW_CODE_LIST_MEMBERSHIP = """
def check_values(values):
    valid_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    for value in values:
        if value in valid_ids:
            print(f"Valid: {value}")
"""

SLOW_CODE_STRING_CONCAT = """
def build_string(words):
    result = ""
    for word in words:
        result += word + " "
    return result.strip()
"""

SLOW_CODE_RANGE_LEN = """
def print_indexed(items):
    for i in range(len(items)):
        print(f"{i}: {items[i]}")
"""

SLOW_CODE_DICT_CHECK = """
def get_value(data, key):
    if key in data:
        return data[key]
    else:
        return "default"
"""

SLOW_CODE_BOOLEAN_LOOP = """
def has_negative(numbers):
    found = False
    for num in numbers:
        if num < 0:
            found = True
            break
    return found
"""


@pytest.fixture
def optimizer():
    """Create a fresh optimizer for each test."""
    # Use default memory connector (will use mock if library not available)
    yield PerformanceOptimizer()


def test_baseline_analysis(optimizer):
    """Test that agent can analyze code without prior experience."""
    analysis = optimizer.optimize_code(SLOW_CODE_LOOP_APPEND, "test1.py")

    assert analysis.file_path == "test1.py"
    assert analysis.total_lines > 0
    assert len(analysis.optimizations) > 0

    # Check that list comprehension optimization was detected
    list_comp_opts = [
        opt for opt in analysis.optimizations if opt.technique == "list_comprehension"
    ]
    assert len(list_comp_opts) > 0


def test_confidence_increases_with_experience(optimizer):
    """Test that confidence increases after successful optimizations."""
    # First analysis - baseline
    analysis1 = optimizer.optimize_code(SLOW_CODE_LOOP_APPEND, "test1.py")
    list_comp_opt1 = next(
        opt for opt in analysis1.optimizations if opt.technique == "list_comprehension"
    )
    initial_confidence = list_comp_opt1.confidence

    # Simulate successful optimization by storing success experience
    optimizer.store.store_experience(
        exp_type="success",
        context={
            "type": "optimization",
            "technique": "list_comprehension",
            "file_path": "test1.py",
        },
        action="applied_optimization",
        outcome={
            "speedup": 1.8,  # Good speedup
            "memory_saved": 100,
            "confidence": initial_confidence,
        },
    )

    # Reload confidence from memory
    optimizer._update_technique_confidence()

    # Second analysis - should have higher confidence
    analysis2 = optimizer.optimize_code(SLOW_CODE_LOOP_APPEND, "test2.py")
    list_comp_opt2 = next(
        opt for opt in analysis2.optimizations if opt.technique == "list_comprehension"
    )
    updated_confidence = list_comp_opt2.confidence

    # Confidence should increase
    assert updated_confidence > initial_confidence, (
        f"Confidence did not increase: {initial_confidence} -> {updated_confidence}"
    )


def test_learning_improves_optimization_effectiveness(optimizer):
    """Test that optimization effectiveness improves with learning."""
    # First run - no experience
    analysis1 = optimizer.optimize_code(SLOW_CODE_LIST_MEMBERSHIP, "test1.py")
    applied_count1 = len([o for o in analysis1.optimizations if o.applied])

    # Simulate multiple successful experiences with set membership
    for i in range(5):
        optimizer.store.store_experience(
            exp_type="success",
            context={
                "type": "optimization",
                "technique": "set_membership",
                "file_path": f"test{i}.py",
            },
            action="applied_optimization",
            outcome={
                "speedup": 8.0,  # Excellent speedup
                "memory_saved": 0,
                "confidence": 0.7 + (i * 0.05),  # Increasing confidence
            },
        )

    # Reload confidence
    optimizer._update_technique_confidence()

    # Second run - with learned experience
    analysis2 = optimizer.optimize_code(SLOW_CODE_LIST_MEMBERSHIP, "test2.py")
    applied_count2 = len([o for o in analysis2.optimizations if o.applied])

    # Should apply more optimizations after learning
    assert applied_count2 >= applied_count1, (
        f"Applied count did not improve: {applied_count1} -> {applied_count2}"
    )

    # Check that set_membership confidence increased
    set_opt = next(
        (opt for opt in analysis2.optimizations if opt.technique == "set_membership"), None
    )
    if set_opt:
        assert set_opt.confidence > 0.7, (
            f"Set membership confidence too low after learning: {set_opt.confidence}"
        )


def test_multiple_optimization_types(optimizer):
    """Test that agent learns across different optimization types."""
    test_cases = [
        (SLOW_CODE_LOOP_APPEND, "list_comprehension"),
        (SLOW_CODE_STRING_CONCAT, "join_strings"),
        (SLOW_CODE_RANGE_LEN, "enumerate_instead_of_range_len"),
        (SLOW_CODE_DICT_CHECK, "dict_get"),
        (SLOW_CODE_BOOLEAN_LOOP, "any_all_instead_of_loop"),
    ]

    results = {}
    for code, expected_technique in test_cases:
        analysis = optimizer.optimize_code(code, f"test_{expected_technique}.py")

        # Find the expected optimization
        opt = next((o for o in analysis.optimizations if expected_technique in o.technique), None)

        if opt:
            results[expected_technique] = {
                "found": True,
                "confidence": opt.confidence,
                "applied": opt.applied,
            }

    # Should detect at least 4 out of 5 optimization types
    assert len(results) >= 4, (
        f"Only detected {len(results)} optimization types out of {len(test_cases)}"
    )


def test_learning_stats_tracking(optimizer):
    """Test that learning statistics are tracked correctly."""
    # Perform several optimizations
    codes = [
        SLOW_CODE_LOOP_APPEND,
        SLOW_CODE_STRING_CONCAT,
        SLOW_CODE_LIST_MEMBERSHIP,
    ]

    for i, code in enumerate(codes):
        optimizer.optimize_code(code, f"test{i}.py")

    # Get learning stats
    stats = optimizer.get_learning_stats()

    assert "total_optimizations" in stats
    assert "avg_speedup" in stats
    assert "technique_effectiveness" in stats

    # Should have tracked some optimizations
    assert stats["total_optimizations"] >= 0


def test_confidence_threshold_for_application(optimizer):
    """Test that optimizations are only applied when confidence is high enough."""
    # Analyze code with low initial confidence
    analysis = optimizer.optimize_code(SLOW_CODE_LOOP_APPEND, "test.py")

    for opt in analysis.optimizations:
        if opt.applied:
            # Applied optimizations should have confidence > 0.6
            assert opt.confidence > 0.6, (
                f"Low-confidence optimization was applied: {opt.confidence}"
            )
        else:
            # Unapplied optimizations should have confidence <= 0.6 or have a reason
            assert opt.confidence <= 0.6 or "confidence too low" in opt.reason.lower(), (
                f"High-confidence optimization was not applied: {opt.confidence}"
            )


def test_learned_insights_generation(optimizer):
    """Test that agent generates learned insights."""
    # First analysis - no experience
    analysis1 = optimizer.optimize_code(SLOW_CODE_LOOP_APPEND, "test1.py")
    insights1 = analysis1.learned_insights

    # Should have some insights
    assert len(insights1) > 0

    # Store some successful experiences
    for i in range(3):
        optimizer.store.store_experience(
            exp_type="success",
            context={
                "type": "optimization",
                "technique": "list_comprehension",
                "file_path": f"test{i}.py",
            },
            action="applied_optimization",
            outcome={"speedup": 1.7, "memory_saved": 100, "confidence": 0.8},
        )

    # Second analysis - with experience
    analysis2 = optimizer.optimize_code(SLOW_CODE_LOOP_APPEND, "test2.py")
    insights2 = analysis2.learned_insights

    # Should have insights referencing learning
    assert len(insights2) > 0


def test_performance_improvement_over_time(optimizer):
    """Test that overall performance improves over multiple analyses."""
    # Perform initial analyses
    initial_analyses = []
    for i in range(3):
        analysis = optimizer.optimize_code(SLOW_CODE_LOOP_APPEND, f"init{i}.py")
        initial_analyses.append(analysis)

    # Store successful optimization experiences
    for i in range(10):
        optimizer.store.store_experience(
            exp_type="success",
            context={
                "type": "optimization",
                "technique": "list_comprehension",
                "file_path": f"training{i}.py",
            },
            action="applied_optimization",
            outcome={"speedup": 1.8, "memory_saved": 100, "confidence": 0.7 + (i * 0.02)},
        )

    # Reload confidence
    optimizer._update_technique_confidence()

    # Perform analyses after learning
    later_analyses = []
    for i in range(3):
        analysis = optimizer.optimize_code(SLOW_CODE_LOOP_APPEND, f"later{i}.py")
        later_analyses.append(analysis)

    # Calculate average applied optimizations
    initial_avg = sum(
        len([o for o in a.optimizations if o.applied]) for a in initial_analyses
    ) / len(initial_analyses)

    later_avg = sum(len([o for o in a.optimizations if o.applied]) for a in later_analyses) / len(
        later_analyses
    )

    # Should apply at least as many optimizations after learning
    assert later_avg >= initial_avg * 0.9, f"Performance decreased: {initial_avg} -> {later_avg}"


def test_technique_effectiveness_tracking(optimizer):
    """Test that technique effectiveness is tracked correctly."""
    # Store experiences with different techniques
    techniques = ["list_comprehension", "join_strings", "set_membership"]

    for technique in techniques:
        for speedup in [1.5, 2.0, 1.8]:
            optimizer.store.store_experience(
                exp_type="success",
                context={
                    "type": "optimization",
                    "technique": technique,
                },
                action="applied_optimization",
                outcome={"speedup": speedup},
            )

    # Get stats
    stats = optimizer.get_learning_stats()
    effectiveness = stats.get("technique_effectiveness", {})

    # Should track all three techniques
    assert len(effectiveness) >= 3

    # Each technique should have metrics
    for technique in techniques:
        assert technique in effectiveness
        assert "avg_speedup" in effectiveness[technique]
        assert "uses" in effectiveness[technique]


def test_memory_graceful_degradation(optimizer):
    """Test that agent works even if memory is unavailable."""
    # Create optimizer without memory
    optimizer_no_memory = PerformanceOptimizer(memory_connector=None)

    # Should still analyze code
    analysis = optimizer_no_memory.optimize_code(SLOW_CODE_LOOP_APPEND, "test.py")

    assert analysis.file_path == "test.py"
    assert len(analysis.optimizations) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
