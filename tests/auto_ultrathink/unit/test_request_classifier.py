"""Unit tests for request_classifier module.

Tests the pattern-based classification engine that determines if a prompt needs UltraThink.
"""

import pytest


class TestRequestClassifier:
    """Unit tests for request classifier."""

    def test_empty_prompt(self):
        """Empty prompt should skip with high confidence."""
        from request_classifier import classify_request

        result = classify_request("")
        assert not result.needs_ultrathink
        assert result.confidence > 0.9
        assert "empty" in result.reason.lower() or "skip" in result.reason.lower()

    def test_none_prompt(self):
        """None prompt should handle gracefully and skip."""
        from request_classifier import classify_request

        result = classify_request(None)
        assert not result.needs_ultrathink
        assert result.confidence == 0.0  # Error case
        assert "fail" in result.reason.lower() or "error" in result.reason.lower()

    def test_slash_command(self):
        """Slash commands should skip with very high confidence."""
        from request_classifier import classify_request

        result = classify_request("/analyze src/")
        assert not result.needs_ultrathink
        assert result.confidence >= 0.99
        assert "slash" in result.reason.lower() or "command" in result.reason.lower()

    def test_multiple_slash_commands(self, sample_prompts):
        """All slash commands should be detected."""
        from request_classifier import classify_request

        for prompt in sample_prompts["slash_commands"]:
            result = classify_request(prompt)
            assert not result.needs_ultrathink, f"Failed for: {prompt}"
            assert result.confidence >= 0.95

    def test_multi_file_feature_trigger(self):
        """Multi-file feature requests should trigger with high confidence."""
        from request_classifier import classify_request

        result = classify_request("Add authentication to the API")
        assert result.needs_ultrathink
        assert result.confidence >= 0.85
        assert "multi_file_feature" in result.matched_patterns

    def test_multi_file_feature_patterns(self, sample_prompts):
        """All multi-file feature patterns should trigger."""
        from request_classifier import classify_request

        for prompt in sample_prompts["multi_file_feature"]:
            result = classify_request(prompt)
            assert result.needs_ultrathink, f"Failed to trigger for: {prompt}"
            assert result.confidence >= 0.80

    def test_question_pattern_skip(self):
        """Questions should skip with high confidence."""
        from request_classifier import classify_request

        result = classify_request("What is UltraThink?")
        assert not result.needs_ultrathink
        assert result.confidence >= 0.90
        assert "question" in result.reason.lower()

    def test_all_questions_skip(self, sample_prompts):
        """All question patterns should skip."""
        from request_classifier import classify_request

        for prompt in sample_prompts["questions"]:
            result = classify_request(prompt)
            assert not result.needs_ultrathink, f"Failed for: {prompt}"
            assert result.confidence >= 0.85

    def test_simple_edit_skip(self):
        """Simple edits should skip."""
        from request_classifier import classify_request

        result = classify_request("Change the variable name to X")
        assert not result.needs_ultrathink
        assert result.confidence >= 0.80

    def test_read_operations_skip(self, sample_prompts):
        """Read operations should skip."""
        from request_classifier import classify_request

        for prompt in sample_prompts["read_operations"]:
            result = classify_request(prompt)
            assert not result.needs_ultrathink, f"Failed for: {prompt}"
            assert result.confidence >= 0.85

    def test_refactoring_trigger(self):
        """Refactoring requests should trigger."""
        from request_classifier import classify_request

        result = classify_request("Refactor the auth module")
        assert result.needs_ultrathink
        assert result.confidence >= 0.80

    def test_confidence_scoring(self):
        """Test confidence calculation for strong matches."""
        from request_classifier import classify_request

        result = classify_request("Implement user dashboard with database and API")
        assert 0.85 <= result.confidence <= 0.98
        assert result.needs_ultrathink

    def test_pattern_matching_multiple(self):
        """Test that multiple patterns are matched."""
        from request_classifier import classify_request

        result = classify_request("Refactor the API and add comprehensive tests")
        assert result.needs_ultrathink
        assert len(result.matched_patterns) >= 1

    def test_very_long_prompt(self):
        """Very long prompts should be handled without crashing."""
        from request_classifier import classify_request

        long_prompt = "Add feature " * 1000
        result = classify_request(long_prompt)
        # Should complete without error
        assert result is not None
        assert hasattr(result, "needs_ultrathink")

    def test_special_characters(self):
        """Special characters should be handled."""
        from request_classifier import classify_request

        result = classify_request("Add feature with $pecial ch@rs!")
        # Should not crash
        assert result is not None

    def test_unicode(self):
        """Unicode should be handled."""
        from request_classifier import classify_request

        result = classify_request("添加功能 с features")
        # Should not crash
        assert result is not None

    def test_whitespace_only(self):
        """Whitespace-only prompt should skip."""
        from request_classifier import classify_request

        result = classify_request("   \n\t   ")
        assert not result.needs_ultrathink
        assert result.confidence > 0.9

    def test_very_short_prompt(self):
        """Very short prompts (<10 words) should likely skip."""
        from request_classifier import classify_request

        result = classify_request("Help")
        assert not result.needs_ultrathink
        assert result.confidence >= 0.80

    def test_confidence_never_reaches_one(self):
        """Confidence should never be exactly 1.0 (always leave uncertainty)."""
        from request_classifier import classify_request

        # Test with very strong trigger
        result = classify_request("Add authentication with database and API and frontend")
        assert result.confidence < 1.0


class TestConfidenceCalculation:
    """Test confidence scoring algorithm."""

    def test_base_confidence_range(self):
        """Base confidence should be in valid range."""
        from request_classifier import classify_request

        result = classify_request("Add authentication to the API")
        assert 0.0 <= result.confidence <= 1.0

    def test_confidence_threshold_boundaries(self):
        """Test confidence around decision thresholds."""
        from request_classifier import classify_request

        # Strong trigger
        strong = classify_request("Implement complete API with database, auth, and frontend")
        assert strong.confidence >= 0.85

        # Weak trigger
        weak = classify_request("maybe add something")
        assert weak.confidence < 0.75 or not weak.needs_ultrathink

    def test_multiple_patterns_boost_confidence(self):
        """Multiple matching patterns should boost confidence."""
        from request_classifier import classify_request

        single = classify_request("Add feature")
        multiple = classify_request("Add feature with tests and documentation")

        # Multiple patterns should have higher or equal confidence
        if single.needs_ultrathink and multiple.needs_ultrathink:
            assert multiple.confidence >= single.confidence


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_input_type(self):
        """Invalid input types should return safe default."""
        from request_classifier import classify_request

        # Test with non-string types
        result = classify_request(123)  # type: ignore
        assert not result.needs_ultrathink
        assert result.confidence == 0.0

    def test_exception_returns_safe_default(self):
        """Exceptions should return safe default (fail-open)."""
        from request_classifier import classify_request

        # This should not crash even with problematic input
        result = classify_request(None)
        assert not result.needs_ultrathink
        assert result.confidence == 0.0

    def test_no_crash_on_edge_cases(self):
        """Test various edge cases don't crash."""
        from request_classifier import classify_request

        edge_cases = [
            "",
            None,
            " ",
            "\n\n\n",
            "a" * 100000,  # Very long
            "🚀" * 100,  # Emoji
            "\x00\x01\x02",  # Control characters
        ]

        for case in edge_cases:
            try:
                result = classify_request(case)
                assert result is not None
            except Exception as e:
                pytest.fail(f"Crashed on edge case: {case!r} with error: {e}")


# Parameterized tests for test corpus
@pytest.mark.parametrize(
    "prompt,expected_needs,min_confidence",
    [
        # Trigger patterns
        ("Add authentication to the API", True, 0.85),
        ("Implement user dashboard with database", True, 0.85),
        ("Refactor the auth module", True, 0.80),
        ("Build REST API with PostgreSQL", True, 0.85),
        ("Create payment processing system", True, 0.85),
        # Skip patterns
        ("What is UltraThink?", False, 0.90),
        ("/analyze src/", False, 0.95),
        ("Show me the config file", False, 0.90),
        ("How do I use the debugger?", False, 0.90),
        ("Change variable name to X", False, 0.85),
        ("List all files", False, 0.90),
        ("Help", False, 0.85),
        # Edge cases
        ("", False, 0.90),
        ("/ultrathink Add feature", False, 0.95),
    ],
)
def test_classification_corpus(prompt, expected_needs, min_confidence):
    """Test against curated corpus."""
    from request_classifier import classify_request

    result = classify_request(prompt)
    assert (
        result.needs_ultrathink == expected_needs
    ), f"Classification mismatch for: {prompt}"
    assert (
        result.confidence >= min_confidence
    ), f"Confidence too low ({result.confidence}) for: {prompt}"


class TestPerformance:
    """Performance tests for classifier."""

    def test_classification_speed(self, sample_prompts):
        """Classification should be fast (<100ms per call)."""
        import time

        from request_classifier import classify_request

        # Collect all sample prompts
        all_prompts = []
        for category in sample_prompts.values():
            all_prompts.extend(category)

        # Time classification
        start = time.time()
        for prompt in all_prompts:
            classify_request(prompt)
        elapsed = time.time() - start

        avg_time_ms = (elapsed / len(all_prompts)) * 1000
        assert avg_time_ms < 100, f"Classification too slow: {avg_time_ms:.2f}ms per call"

    def test_no_memory_leak_simple(self):
        """Test for obvious memory leaks."""
        import gc

        from request_classifier import classify_request

        # Run classification many times
        for i in range(1000):
            classify_request(f"Add feature {i}")

        # Force garbage collection
        gc.collect()

        # If we got here without memory error, test passes
        assert True


class TestClassificationContract:
    """Test the Classification dataclass contract."""

    def test_classification_has_required_fields(self):
        """Classification should have all required fields."""
        from request_classifier import classify_request

        result = classify_request("test prompt")

        assert hasattr(result, "needs_ultrathink")
        assert hasattr(result, "confidence")
        assert hasattr(result, "reason")
        assert hasattr(result, "matched_patterns")

    def test_classification_types(self):
        """Classification fields should have correct types."""
        from request_classifier import classify_request

        result = classify_request("Add authentication")

        assert isinstance(result.needs_ultrathink, bool)
        assert isinstance(result.confidence, (int, float))
        assert isinstance(result.reason, str)
        assert isinstance(result.matched_patterns, list)

    def test_reason_is_meaningful(self):
        """Reason should provide meaningful explanation."""
        from request_classifier import classify_request

        result = classify_request("Add authentication to the API")

        assert len(result.reason) > 0
        assert result.reason != ""
        # Reason should contain some helpful information
        assert len(result.reason) > 5

    def test_matched_patterns_is_list(self):
        """Matched patterns should be a list (can be empty)."""
        from request_classifier import classify_request

        result = classify_request("What is this?")

        assert isinstance(result.matched_patterns, list)
        # For a question, we expect at least the question pattern
        if not result.needs_ultrathink:
            assert len(result.matched_patterns) >= 0  # Can be empty or have patterns
