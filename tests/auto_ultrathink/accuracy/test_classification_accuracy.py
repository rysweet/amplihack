"""Accuracy tests for request classifier.

Tests classification accuracy against a curated corpus of 100+ examples.
Measures precision, recall, and F1 score.
"""

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def load_corpus():
    """Load test corpus from YAML file."""
    corpus_path = Path(__file__).parent / "test_corpus.yaml"
    with open(corpus_path, "r") as f:
        return yaml.safe_load(f)


def test_classification_accuracy(load_corpus):
    """Test classification accuracy against full corpus."""
    from request_classifier import classify_request

    corpus = load_corpus
    results = {
        "true_positive": 0,  # Correctly identified as needs_ultrathink
        "true_negative": 0,  # Correctly identified as not needs_ultrathink
        "false_positive": 0,  # Incorrectly identified as needs_ultrathink
        "false_negative": 0,  # Incorrectly identified as not needs_ultrathink
    }

    errors = []

    for entry in corpus:
        prompt = entry["prompt"]
        expected = entry["expected"]
        category = entry.get("category", "unknown")

        try:
            classification = classify_request(prompt)
            actual = classification.needs_ultrathink

            if expected and actual:
                results["true_positive"] += 1
            elif not expected and not actual:
                results["true_negative"] += 1
            elif not expected and actual:
                results["false_positive"] += 1
                errors.append(f"FALSE POSITIVE: {category} - '{prompt}' (confidence: {classification.confidence:.2f})")
            else:  # expected and not actual
                results["false_negative"] += 1
                errors.append(f"FALSE NEGATIVE: {category} - '{prompt}' (confidence: {classification.confidence:.2f})")

        except Exception as e:
            errors.append(f"ERROR: {category} - '{prompt}' - {str(e)}")
            # Count as false negative if expected to trigger, false positive otherwise
            if expected:
                results["false_negative"] += 1
            else:
                results["false_positive"] += 1

    # Calculate metrics
    total = sum(results.values())
    true_positive = results["true_positive"]
    false_positive = results["false_positive"]
    false_negative = results["false_negative"]

    # Avoid division by zero
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) > 0 else 0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (results["true_positive"] + results["true_negative"]) / total if total > 0 else 0

    # Print detailed results
    print("\n" + "=" * 70)
    print("CLASSIFICATION ACCURACY REPORT")
    print("=" * 70)
    print(f"\nTotal test cases: {total}")
    print(f"  True Positives:  {results['true_positive']}")
    print(f"  True Negatives:  {results['true_negative']}")
    print(f"  False Positives: {results['false_positive']}")
    print(f"  False Negatives: {results['false_negative']}")
    print("\nAccuracy Metrics:")
    print(f"  Precision: {precision:.2%}")
    print(f"  Recall:    {recall:.2%}")
    print(f"  F1 Score:  {f1:.2%}")
    print(f"  Accuracy:  {accuracy:.2%}")

    # Print errors if any
    if errors:
        print(f"\nErrors and Misclassifications ({len(errors)}):")
        for error in errors[:20]:  # Print first 20 errors
            print(f"  {error}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")

    print("=" * 70 + "\n")

    # Assertions with helpful error messages
    assert precision >= 0.90, (
        f"Precision {precision:.2%} below target 90%\n"
        f"False positives: {false_positive}/{total}\n"
        f"Review: {[e for e in errors if 'FALSE POSITIVE' in e][:5]}"
    )

    assert recall >= 0.85, (
        f"Recall {recall:.2%} below target 85%\n"
        f"False negatives: {false_negative}/{total}\n"
        f"Review: {[e for e in errors if 'FALSE NEGATIVE' in e][:5]}"
    )

    assert f1 >= 0.88, (
        f"F1 score {f1:.2%} below target 88%\n"
        f"Balance between precision and recall needs improvement"
    )


def test_confidence_scores(load_corpus):
    """Test that confidence scores meet minimum thresholds."""
    from request_classifier import classify_request

    corpus = load_corpus
    confidence_failures = []

    for entry in corpus:
        prompt = entry["prompt"]
        expected = entry["expected"]
        min_confidence = entry.get("min_confidence", 0.0)

        try:
            classification = classify_request(prompt)

            # Only check confidence if classification is correct
            if classification.needs_ultrathink == expected:
                if classification.confidence < min_confidence:
                    confidence_failures.append(
                        f"Low confidence: '{prompt}' - "
                        f"got {classification.confidence:.2f}, expected >={min_confidence:.2f}"
                    )
        except Exception as e:
            confidence_failures.append(f"Error: '{prompt}' - {str(e)}")

    # Print failures
    if confidence_failures:
        print(f"\nConfidence threshold failures ({len(confidence_failures)}):")
        for failure in confidence_failures[:10]:
            print(f"  {failure}")

    # Allow some tolerance (90% of cases should meet confidence threshold)
    max_failures = len(corpus) * 0.10
    assert len(confidence_failures) <= max_failures, (
        f"Too many confidence failures: {len(confidence_failures)}/{len(corpus)}\n"
        f"Maximum allowed: {max_failures}"
    )


def test_accuracy_by_category(load_corpus):
    """Test accuracy broken down by category."""
    from request_classifier import classify_request

    corpus = load_corpus
    category_stats = {}

    for entry in corpus:
        prompt = entry["prompt"]
        expected = entry["expected"]
        category = entry.get("category", "unknown")

        if category not in category_stats:
            category_stats[category] = {"correct": 0, "incorrect": 0, "total": 0}

        try:
            classification = classify_request(prompt)
            actual = classification.needs_ultrathink

            category_stats[category]["total"] += 1
            if actual == expected:
                category_stats[category]["correct"] += 1
            else:
                category_stats[category]["incorrect"] += 1

        except Exception:
            category_stats[category]["total"] += 1
            category_stats[category]["incorrect"] += 1

    # Print category breakdown
    print("\n" + "=" * 70)
    print("ACCURACY BY CATEGORY")
    print("=" * 70)

    for category, stats in sorted(category_stats.items()):
        total = stats["total"]
        correct = stats["correct"]
        accuracy = correct / total if total > 0 else 0

        print(f"\n{category}:")
        print(f"  Correct:   {correct}/{total} ({accuracy:.1%})")
        print(f"  Incorrect: {stats['incorrect']}/{total}")

    print("=" * 70 + "\n")

    # Check that each category has at least 70% accuracy
    poor_categories = []
    for category, stats in category_stats.items():
        total = stats["total"]
        correct = stats["correct"]
        accuracy = correct / total if total > 0 else 0

        if accuracy < 0.70 and total >= 3:  # Only check categories with 3+ samples
            poor_categories.append(f"{category}: {accuracy:.1%}")

    assert len(poor_categories) == 0, (
        f"Some categories have poor accuracy (<70%):\n"
        f"{', '.join(poor_categories)}"
    )


def test_no_crashes_on_corpus(load_corpus):
    """Test that classifier doesn't crash on any corpus entry."""
    from request_classifier import classify_request

    corpus = load_corpus
    crashes = []

    for entry in corpus:
        prompt = entry["prompt"]

        try:
            classification = classify_request(prompt)
            # Verify result has expected structure
            assert hasattr(classification, "needs_ultrathink")
            assert hasattr(classification, "confidence")
            assert hasattr(classification, "reason")
            assert hasattr(classification, "matched_patterns")
        except Exception as e:
            crashes.append(f"Crash on '{prompt}': {str(e)}")

    assert len(crashes) == 0, (
        f"Classifier crashed on {len(crashes)} prompts:\n"
        f"{crashes[:5]}"
    )


def test_consistency(load_corpus):
    """Test that classifier returns consistent results for same prompt."""
    from request_classifier import classify_request

    corpus = load_corpus

    # Test first 20 entries for consistency
    for entry in corpus[:20]:
        prompt = entry["prompt"]

        # Classify 5 times
        results = []
        for _ in range(5):
            classification = classify_request(prompt)
            results.append(
                (classification.needs_ultrathink, classification.confidence)
            )

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, (
                f"Inconsistent results for '{prompt}':\n"
                f"Expected: {first_result}\n"
                f"Got: {result}"
            )


def test_edge_cases():
    """Test edge cases not in corpus."""
    from request_classifier import classify_request

    edge_cases = [
        ("", False),  # Empty string
        ("   ", False),  # Whitespace only
        ("a" * 100000, None),  # Very long string (should not crash)
        ("🚀" * 100, None),  # Many emojis (should not crash)
        ("\n\n\n", False),  # Only newlines
    ]

    for prompt, expected in edge_cases:
        try:
            classification = classify_request(prompt)

            if expected is not None:
                assert classification.needs_ultrathink == expected, (
                    f"Edge case failed: '{prompt[:50]}...'\n"
                    f"Expected: {expected}, Got: {classification.needs_ultrathink}"
                )

            # Verify basic structure
            assert hasattr(classification, "needs_ultrathink")
            assert hasattr(classification, "confidence")

        except Exception as e:
            pytest.fail(f"Classifier crashed on edge case '{prompt[:50]}...': {e}")


def test_performance_with_corpus(load_corpus):
    """Test classification performance with corpus data."""
    import time

    from request_classifier import classify_request

    corpus = load_corpus

    # Measure time for all classifications
    start = time.time()
    for entry in corpus:
        classify_request(entry["prompt"])
    elapsed = time.time() - start

    avg_time_ms = (elapsed / len(corpus)) * 1000

    print("\nPerformance on corpus:")
    print(f"  Total time: {elapsed:.3f}s")
    print(f"  Average per classification: {avg_time_ms:.2f}ms")
    print(f"  Total prompts: {len(corpus)}")

    # Should be fast (<100ms per classification)
    assert avg_time_ms < 100, (
        f"Classification too slow: {avg_time_ms:.2f}ms per prompt\n"
        f"Target: <100ms per prompt"
    )
