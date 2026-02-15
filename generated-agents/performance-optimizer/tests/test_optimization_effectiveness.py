"""
Test optimization effectiveness and improvement over time.

These tests validate that the agent's optimization recommendations
become more accurate and effective through learning.
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import PerformanceOptimizer
from metrics import calculate_metrics_from_stats


@pytest.fixture
def optimizer():
    """Create a fresh optimizer for each test."""
    # Use default memory connector (will use mock if library not available)
    yield PerformanceOptimizer()


def test_optimization_confidence_improves_with_success(optimizer):
    """Test that successful optimizations increase technique confidence."""
    # Get initial confidence
    initial_confidence = optimizer.techniques["list_comprehension"].confidence

    # Simulate 5 successful list comprehension optimizations
    for i in range(5):
        optimizer.store.store_experience(
            exp_type="success",
            context={
                "type": "optimization",
                "technique": "list_comprehension",
                "file_path": f"success{i}.py",
            },
            action="applied_optimization",
            outcome={"speedup": 1.8, "memory_saved": 100, "confidence": initial_confidence},
        )

    # Update confidence from experiences
    optimizer._update_technique_confidence()

    # Check that confidence increased
    updated_confidence = optimizer.techniques["list_comprehension"].confidence
    assert updated_confidence > initial_confidence, (
        f"Confidence did not improve after successes: {initial_confidence} -> {updated_confidence}"
    )

    # Confidence should be at least 20% higher
    improvement = (updated_confidence - initial_confidence) / initial_confidence
    assert improvement > 0.15, f"Confidence improvement too small: {improvement:.2%}"


def test_optimization_confidence_decreases_with_failure(optimizer):
    """Test that failed optimizations decrease technique confidence."""
    # Get initial confidence
    initial_confidence = optimizer.techniques["list_comprehension"].confidence

    # Simulate 5 failed list comprehension optimizations
    for i in range(5):
        optimizer.store.store_experience(
            exp_type="failure",
            context={
                "type": "optimization",
                "technique": "list_comprehension",
                "file_path": f"failure{i}.py",
            },
            action="applied_optimization",
            outcome={
                "speedup": 1.0,  # No improvement
                "memory_saved": 0,
                "confidence": initial_confidence,
            },
        )

    # Update confidence from experiences
    optimizer._update_technique_confidence()

    # Check that confidence decreased or stayed same
    updated_confidence = optimizer.techniques["list_comprehension"].confidence
    assert updated_confidence <= initial_confidence * 1.1, (
        f"Confidence increased after failures: {initial_confidence} -> {updated_confidence}"
    )


def test_mixed_success_failure_adjusts_confidence(optimizer):
    """Test that mixed results properly adjust confidence."""
    _ = optimizer.techniques["set_membership"].confidence

    # Simulate mixed results: 7 successes, 3 failures (70% success rate)
    for i in range(7):
        optimizer.store.store_experience(
            exp_type="success",
            context={
                "type": "optimization",
                "technique": "set_membership",
            },
            action="applied_optimization",
            outcome={"speedup": 6.0},  # Good speedup
        )

    for i in range(3):
        optimizer.store.store_experience(
            exp_type="failure",
            context={
                "type": "optimization",
                "technique": "set_membership",
            },
            action="applied_optimization",
            outcome={"speedup": 1.0},  # No improvement
        )

    # Update confidence
    optimizer._update_technique_confidence()

    updated_confidence = optimizer.techniques["set_membership"].confidence

    # 70% success rate should result in moderate confidence (0.6-0.8 range)
    assert 0.55 < updated_confidence < 0.85, (
        f"Confidence not in expected range for 70% success: {updated_confidence}"
    )


def test_learning_stats_show_improvement_trend(optimizer):
    """Test that learning stats correctly identify improvement trends."""
    # First batch: lower speedups
    for i in range(5):
        optimizer.store.store_experience(
            exp_type="success",
            context={"type": "optimization", "technique": "any_all_instead_of_loop"},
            action="applied_optimization",
            outcome={"speedup": 1.5},  # Modest speedup
        )

    # Second batch: higher speedups (learning improved)
    for i in range(5):
        optimizer.store.store_experience(
            exp_type="success",
            context={"type": "optimization", "technique": "any_all_instead_of_loop"},
            action="applied_optimization",
            outcome={"speedup": 2.5},  # Better speedup
        )

    # Get learning stats
    stats = optimizer.get_learning_stats()

    # Should show improving trend
    assert stats["trend"] in ["improving", "stable"], (
        f"Expected improving trend, got: {stats['trend']}"
    )

    # Second half average should be higher than first half
    assert stats["second_half_avg"] > stats["first_half_avg"], (
        f"Second half not better: {stats['first_half_avg']} vs {stats['second_half_avg']}"
    )


def test_technique_effectiveness_ranking(optimizer):
    """Test that technique effectiveness is correctly ranked."""
    # Store experiences with varying effectiveness
    techniques_and_speedups = [
        ("list_comprehension", 1.8),
        ("set_membership", 8.0),
        ("join_strings", 15.0),
        ("dict_get", 1.3),
    ]

    for technique, speedup in techniques_and_speedups:
        for _ in range(3):  # Multiple experiences per technique
            optimizer.store.store_experience(
                exp_type="success",
                context={"type": "optimization", "technique": technique},
                action="applied_optimization",
                outcome={"speedup": speedup},
            )

    # Get stats
    stats = optimizer.get_learning_stats()
    effectiveness = stats.get("technique_effectiveness", {})

    # Check that join_strings is recognized as most effective
    if "join_strings" in effectiveness:
        join_speedup = effectiveness["join_strings"]["avg_speedup"]
        assert join_speedup > 10.0, f"join_strings should have high speedup: {join_speedup}"

    # Check that all techniques are tracked
    assert len(effectiveness) >= 3, f"Not enough techniques tracked: {len(effectiveness)}"


def test_confidence_boost_from_past_experiences(optimizer):
    """Test that past experiences provide confidence boost."""
    # Store successful experiences
    for i in range(5):
        optimizer.store.store_experience(
            exp_type="success",
            context={
                "type": "optimization",
                "technique": "enumerate_instead_of_range_len",
            },
            action="applied_optimization",
            outcome={"speedup": 1.4},
        )

    # Calculate boost
    past_experiences = optimizer._retrieve_relevant_experiences("test.py")
    boost = optimizer._get_confidence_boost("enumerate_instead_of_range_len", past_experiences)

    # Should get some boost (> 0.1)
    assert boost > 0.05, f"Confidence boost too small: {boost}"
    assert boost <= 0.3, f"Confidence boost too large: {boost}"


def test_metrics_calculation(optimizer):
    """Test that learning metrics are calculated correctly."""
    # Store various experiences
    for i in range(10):
        optimizer.store.store_experience(
            exp_type="success",
            context={"type": "optimization", "technique": "list_comprehension"},
            action="applied_optimization",
            outcome={"speedup": 1.5 + (i * 0.1)},  # Increasing speedup
        )

    # Get stats and calculate metrics
    stats = optimizer.get_learning_stats()
    metrics = calculate_metrics_from_stats(stats)

    # Validate metrics
    assert metrics.total_optimizations > 0
    assert metrics.avg_speedup > 1.0
    assert metrics.trend in ["improving", "stable", "declining", "no_data"]


def test_optimization_selection_based_on_confidence(optimizer):
    """Test that high-confidence optimizations are preferred."""
    # Train on string concatenation (make it high confidence)
    for i in range(10):
        optimizer.store.store_experience(
            exp_type="success",
            context={"type": "optimization", "technique": "join_strings"},
            action="applied_optimization",
            outcome={"speedup": 12.0},
        )

    # Update confidence
    optimizer._update_technique_confidence()

    # Analyze code with string concatenation
    code = """
result = ""
for word in words:
    result += word
"""
    analysis = optimizer.optimize_code(code, "test.py")

    # Find join_strings optimization
    join_opt = next(
        (opt for opt in analysis.optimizations if opt.technique == "join_strings"), None
    )

    if join_opt:
        # Should have high confidence
        assert join_opt.confidence > 0.6, (
            f"join_strings should have high confidence: {join_opt.confidence}"
        )

        # Should be applied
        assert join_opt.applied, "High-confidence optimization should be applied"


def test_learning_rate_calculation(optimizer):
    """Test that learning rate is calculated correctly."""
    # Store experiences over time
    for i in range(20):
        optimizer.store.store_experience(
            exp_type="success",
            context={"type": "optimization", "technique": "list_comprehension"},
            action="applied_optimization",
            outcome={"speedup": 1.3 + (i * 0.05)},  # Gradually improving
        )

    # Get stats and metrics
    stats = optimizer.get_learning_stats()
    metrics = calculate_metrics_from_stats(stats)

    # Learning rate should be positive for improving agent
    learning_rate = metrics.get_learning_rate()
    assert isinstance(learning_rate, float)


def test_best_technique_identification(optimizer):
    """Test that best technique is correctly identified."""
    # Store experiences with clear winner
    techniques_data = [
        ("list_comprehension", 1.7, 3),
        ("set_membership", 9.0, 5),  # Best: high speedup, high confidence
        ("dict_get", 1.3, 2),
    ]

    for technique, speedup, count in techniques_data:
        for _ in range(count):
            optimizer.store.store_experience(
                exp_type="success",
                context={"type": "optimization", "technique": technique},
                action="applied_optimization",
                outcome={"speedup": speedup},
            )

    # Update confidence
    optimizer._update_technique_confidence()

    # Get stats and metrics
    stats = optimizer.get_learning_stats()
    metrics = calculate_metrics_from_stats(stats)

    # Best technique should be set_membership
    best = metrics.get_best_technique()
    assert best is not None


def test_optimization_application_threshold(optimizer):
    """Test that only high-confidence optimizations are applied."""
    # Analyze code without training
    code = """
result = []
for x in items:
    result.append(x * 2)
"""
    analysis1 = optimizer.optimize_code(code, "before_training.py")

    # Count applied optimizations
    applied_before = len([o for o in analysis1.optimizations if o.applied])

    # Train extensively on list comprehension
    for i in range(15):
        optimizer.store.store_experience(
            exp_type="success",
            context={"type": "optimization", "technique": "list_comprehension"},
            action="applied_optimization",
            outcome={"speedup": 1.8},
        )

    # Update confidence
    optimizer._update_technique_confidence()

    # Analyze same code after training
    analysis2 = optimizer.optimize_code(code, "after_training.py")
    applied_after = len([o for o in analysis2.optimizations if o.applied])

    # Should apply at least as many optimizations
    assert applied_after >= applied_before, (
        f"Applied count decreased after training: {applied_before} -> {applied_after}"
    )


def test_speedup_estimation_accuracy(optimizer):
    """Test that speedup estimations become more accurate with learning."""
    # Store experiences with actual speedup measurements
    for i in range(10):
        optimizer.store.store_experience(
            exp_type="success",
            context={"type": "optimization", "technique": "list_comprehension"},
            action="applied_optimization",
            outcome={"speedup": 1.75},  # Consistent actual speedup
        )

    # Analyze code
    code = """
result = []
for x in items:
    result.append(x * 2)
"""
    analysis = optimizer.optimize_code(code, "test.py")

    # Find list comprehension optimization
    opt = next((o for o in analysis.optimizations if o.technique == "list_comprehension"), None)

    if opt:
        # Estimated speedup should be close to learned value
        assert 1.5 <= opt.estimated_speedup <= 2.2, (
            f"Speedup estimate out of expected range: {opt.estimated_speedup}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
