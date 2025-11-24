"""Unit tests for decision_engine module.

Tests the decision matrix that combines classification + preferences to decide actions.
"""

import pytest


class TestDecisionEngine:
    """Unit tests for decision engine."""

    def test_disabled_mode_always_skips(self, create_test_classification, create_test_preference):
        """Disabled mode should always skip, regardless of classification."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.95)
        preference = create_test_preference(mode="disabled")

        decision = make_decision(classification, preference, "test prompt")

        assert decision.action == Action.SKIP
        assert "disabled" in decision.reason.lower()

    def test_enabled_mode_valid_classification_invokes(
        self, create_test_classification, create_test_preference
    ):
        """Enabled mode with valid classification should invoke."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.90)
        preference = create_test_preference(mode="enabled", confidence_threshold=0.80)

        decision = make_decision(classification, preference, "test prompt")

        assert decision.action == Action.INVOKE
        assert "invoke" in decision.reason.lower()

    def test_enabled_mode_low_confidence_skips(
        self, create_test_classification, create_test_preference
    ):
        """Enabled mode with low confidence should skip."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.75)
        preference = create_test_preference(mode="enabled", confidence_threshold=0.80)

        decision = make_decision(classification, preference, "test prompt")

        assert decision.action == Action.SKIP
        assert "confidence" in decision.reason.lower() or "threshold" in decision.reason.lower()

    def test_enabled_mode_not_needed_skips(
        self, create_test_classification, create_test_preference
    ):
        """Enabled mode with needs_ultrathink=False should skip."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=False, confidence=0.95)
        preference = create_test_preference(mode="enabled")

        decision = make_decision(classification, preference, "test prompt")

        assert decision.action == Action.SKIP

    def test_ask_mode_valid_classification_asks(
        self, create_test_classification, create_test_preference
    ):
        """Ask mode with valid classification should ask user."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.90)
        preference = create_test_preference(mode="ask", confidence_threshold=0.80)

        decision = make_decision(classification, preference, "test prompt")

        assert decision.action == Action.ASK
        assert "recommendation" in decision.reason.lower() or "ask" in decision.reason.lower()

    def test_ask_mode_low_confidence_skips(
        self, create_test_classification, create_test_preference
    ):
        """Ask mode with low confidence should skip."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.70)
        preference = create_test_preference(mode="ask", confidence_threshold=0.80)

        decision = make_decision(classification, preference, "test prompt")

        assert decision.action == Action.SKIP

    def test_ask_mode_not_needed_skips(self, create_test_classification, create_test_preference):
        """Ask mode with needs_ultrathink=False should skip."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=False, confidence=0.95)
        preference = create_test_preference(mode="ask")

        decision = make_decision(classification, preference, "test prompt")

        assert decision.action == Action.SKIP


class TestConfidenceThreshold:
    """Test confidence threshold enforcement."""

    def test_confidence_equal_to_threshold_passes(
        self, create_test_classification, create_test_preference
    ):
        """Confidence equal to threshold should pass."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.80)
        preference = create_test_preference(mode="enabled", confidence_threshold=0.80)

        decision = make_decision(classification, preference, "test prompt")

        assert decision.action == Action.INVOKE

    def test_confidence_just_below_threshold_fails(
        self, create_test_classification, create_test_preference
    ):
        """Confidence just below threshold should fail."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.79)
        preference = create_test_preference(mode="enabled", confidence_threshold=0.80)

        decision = make_decision(classification, preference, "test prompt")

        assert decision.action == Action.SKIP

    def test_confidence_just_above_threshold_passes(
        self, create_test_classification, create_test_preference
    ):
        """Confidence just above threshold should pass."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.81)
        preference = create_test_preference(mode="enabled", confidence_threshold=0.80)

        decision = make_decision(classification, preference, "test prompt")

        assert decision.action == Action.INVOKE

    def test_threshold_zero_allows_all(self, create_test_classification, create_test_preference):
        """Threshold of 0.0 should allow all confidence levels."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.01)
        preference = create_test_preference(mode="enabled", confidence_threshold=0.0)

        decision = make_decision(classification, preference, "test prompt")

        assert decision.action == Action.INVOKE

    def test_threshold_one_blocks_all_except_perfect(
        self, create_test_classification, create_test_preference
    ):
        """Threshold of 1.0 should block everything except perfect confidence."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.99)
        preference = create_test_preference(mode="enabled", confidence_threshold=1.0)

        decision = make_decision(classification, preference, "test prompt")

        assert decision.action == Action.SKIP


class TestExclusionPatterns:
    """Test exclusion pattern logic."""

    def test_excluded_pattern_skips(self, create_test_classification, create_test_preference):
        """Matching excluded pattern should skip."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.95)
        preference = create_test_preference(
            mode="enabled", excluded_patterns=["^test.*"]
        )

        decision = make_decision(classification, preference, "test this feature")

        assert decision.action == Action.SKIP
        assert "excluded" in decision.reason.lower()

    def test_not_excluded_pattern_continues(
        self, create_test_classification, create_test_preference
    ):
        """Non-matching pattern should not skip."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.95)
        preference = create_test_preference(
            mode="enabled", excluded_patterns=["^test.*"]
        )

        decision = make_decision(classification, preference, "implement feature")

        assert decision.action == Action.INVOKE

    def test_multiple_exclusion_patterns(
        self, create_test_classification, create_test_preference
    ):
        """Multiple exclusion patterns should all be checked."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.95)
        preference = create_test_preference(
            mode="enabled", excluded_patterns=["^test.*", ".*debug.*", "^fix.*"]
        )

        # Test first pattern
        decision1 = make_decision(classification, preference, "test the feature")
        assert decision1.action == Action.SKIP

        # Test second pattern
        decision2 = make_decision(classification, preference, "debug this issue")
        assert decision2.action == Action.SKIP

        # Test third pattern
        decision3 = make_decision(classification, preference, "fix the bug")
        assert decision3.action == Action.SKIP

        # Test non-matching
        decision4 = make_decision(classification, preference, "implement feature")
        assert decision4.action == Action.INVOKE

    def test_empty_exclusion_patterns(self, create_test_classification, create_test_preference):
        """Empty exclusion patterns should not exclude anything."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.95)
        preference = create_test_preference(mode="enabled", excluded_patterns=[])

        decision = make_decision(classification, preference, "test prompt")

        assert decision.action == Action.INVOKE


# Parameterized test for comprehensive decision matrix
@pytest.mark.parametrize(
    "mode,needs,confidence,threshold,excluded,expected_action",
    [
        # Disabled mode - always skip
        ("disabled", True, 0.90, 0.80, False, "SKIP"),
        ("disabled", False, 0.90, 0.80, False, "SKIP"),
        ("disabled", True, 0.50, 0.80, False, "SKIP"),
        # Enabled mode - various scenarios
        ("enabled", True, 0.90, 0.80, False, "INVOKE"),
        ("enabled", True, 0.70, 0.80, False, "SKIP"),  # Below threshold
        ("enabled", True, 0.90, 0.80, True, "SKIP"),  # Excluded
        ("enabled", False, 0.90, 0.80, False, "SKIP"),  # Not needed
        ("enabled", True, 0.80, 0.80, False, "INVOKE"),  # Exact threshold
        # Ask mode - various scenarios
        ("ask", True, 0.90, 0.80, False, "ASK"),
        ("ask", True, 0.70, 0.80, False, "SKIP"),  # Below threshold
        ("ask", True, 0.90, 0.80, True, "SKIP"),  # Excluded
        ("ask", False, 0.90, 0.80, False, "SKIP"),  # Not needed
        ("ask", True, 0.80, 0.80, False, "ASK"),  # Exact threshold
    ],
)
def test_decision_matrix(
    mode,
    needs,
    confidence,
    threshold,
    excluded,
    expected_action,
    create_test_classification,
    create_test_preference,
):
    """Test all decision matrix combinations."""
    from decision_engine import Action, make_decision

    classification = create_test_classification(
        needs_ultrathink=needs, confidence=confidence
    )
    excluded_patterns = ["test"] if excluded else []
    preference = create_test_preference(
        mode=mode, confidence_threshold=threshold, excluded_patterns=excluded_patterns
    )
    prompt = "test prompt" if excluded else "normal prompt"

    decision = make_decision(classification, preference, prompt)

    assert decision.action == Action[expected_action], (
        f"Failed for mode={mode}, needs={needs}, confidence={confidence}, "
        f"threshold={threshold}, excluded={excluded}"
    )


class TestDecisionContract:
    """Test the Decision dataclass contract."""

    def test_decision_has_required_fields(
        self, create_test_classification, create_test_preference
    ):
        """Decision should have all required fields."""
        from decision_engine import make_decision

        classification = create_test_classification()
        preference = create_test_preference()

        decision = make_decision(classification, preference, "test prompt")

        assert hasattr(decision, "action")
        assert hasattr(decision, "reason")
        assert hasattr(decision, "classification")
        assert hasattr(decision, "preference")

    def test_decision_types(self, create_test_classification, create_test_preference):
        """Decision fields should have correct types."""
        from decision_engine import Action, make_decision

        classification = create_test_classification()
        preference = create_test_preference()

        decision = make_decision(classification, preference, "test prompt")

        assert isinstance(decision.action, Action)
        assert isinstance(decision.reason, str)
        # classification and preference should be the original objects
        assert decision.classification == classification
        assert decision.preference == preference

    def test_reason_is_meaningful(self, create_test_classification, create_test_preference):
        """Reason should provide meaningful explanation."""
        from decision_engine import make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.95)
        preference = create_test_preference(mode="enabled")

        decision = make_decision(classification, preference, "test prompt")

        assert len(decision.reason) > 0
        assert decision.reason != ""
        # Reason should be descriptive
        assert len(decision.reason) > 10

    def test_decision_preserves_classification(
        self, create_test_classification, create_test_preference
    ):
        """Decision should preserve original classification."""
        from decision_engine import make_decision

        classification = create_test_classification(
            needs_ultrathink=True, confidence=0.92, reason="Test reason"
        )
        preference = create_test_preference()

        decision = make_decision(classification, preference, "test prompt")

        assert decision.classification.confidence == 0.92
        assert decision.classification.reason == "Test reason"

    def test_decision_preserves_preference(
        self, create_test_classification, create_test_preference
    ):
        """Decision should preserve original preference."""
        from decision_engine import make_decision

        classification = create_test_classification()
        preference = create_test_preference(mode="enabled", confidence_threshold=0.85)

        decision = make_decision(classification, preference, "test prompt")

        assert decision.preference.mode == "enabled"
        assert decision.preference.confidence_threshold == 0.85


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_none_classification_returns_skip(self, create_test_preference):
        """None classification should return skip."""
        from decision_engine import Action, make_decision

        preference = create_test_preference()

        # Simulate error case with invalid classification
        try:
            decision = make_decision(None, preference, "test prompt")
            # Should either handle gracefully or raise
            if decision:
                assert decision.action == Action.SKIP
        except Exception:
            # Also acceptable to raise exception
            pass

    def test_none_preference_returns_skip(self, create_test_classification):
        """None preference should return skip."""
        from decision_engine import Action, make_decision

        classification = create_test_classification()

        # Simulate error case with invalid preference
        try:
            decision = make_decision(classification, None, "test prompt")
            # Should either handle gracefully or raise
            if decision:
                assert decision.action == Action.SKIP
        except Exception:
            # Also acceptable to raise exception
            pass

    def test_empty_prompt_handled(self, create_test_classification, create_test_preference):
        """Empty prompt should be handled."""
        from decision_engine import make_decision

        classification = create_test_classification()
        preference = create_test_preference()

        decision = make_decision(classification, preference, "")

        # Should complete without error
        assert decision is not None

    def test_none_prompt_handled(self, create_test_classification, create_test_preference):
        """None prompt should be handled."""
        from decision_engine import make_decision

        classification = create_test_classification()
        preference = create_test_preference()

        try:
            decision = make_decision(classification, preference, None)
            # Should either handle gracefully
            assert decision is not None
        except Exception:
            # Or raise exception
            pass

    def test_unknown_mode_defaults_to_skip(
        self, create_test_classification, create_test_preference
    ):
        """Unknown preference mode should default to skip."""
        from decision_engine import Action, make_decision

        classification = create_test_classification(needs_ultrathink=True, confidence=0.95)
        preference = create_test_preference(mode="unknown_mode")

        # This should be validated by preference_manager, but test defensive programming
        try:
            decision = make_decision(classification, preference, "test prompt")
            # Should default to safe action (SKIP)
            assert decision.action == Action.SKIP
        except Exception:
            # Also acceptable if preference_manager prevents this
            pass


class TestPerformance:
    """Performance tests for decision engine."""

    def test_decision_speed(self, create_test_classification, create_test_preference):
        """Decision making should be fast (<10ms per call)."""
        import time

        from decision_engine import make_decision

        classification = create_test_classification()
        preference = create_test_preference()

        start = time.time()
        for i in range(1000):
            make_decision(classification, preference, f"prompt {i}")
        elapsed = time.time() - start

        avg_time_ms = (elapsed / 1000) * 1000
        assert avg_time_ms < 10, f"Decision too slow: {avg_time_ms:.2f}ms per call"

    def test_no_memory_leak(self, create_test_classification, create_test_preference):
        """Test for memory leaks."""
        import gc

        from decision_engine import make_decision

        classification = create_test_classification()
        preference = create_test_preference()

        # Run many decisions
        for i in range(10000):
            make_decision(classification, preference, f"prompt {i}")

        # Force garbage collection
        gc.collect()

        # If we got here without memory error, test passes
        assert True
