"""Tests for hive_mind.quality -- content quality scoring and gating.

Tests quality scoring heuristics and the QualityGate for promotion,
retrieval, and broadcast decisions.
"""

from __future__ import annotations


class TestScoreContentQuality:
    """Test the score_content_quality function."""

    def test_empty_content_scores_zero(self):
        """Empty or whitespace content scores 0.0."""
        from amplihack.agents.goal_seeking.hive_mind.quality import score_content_quality

        assert score_content_quality("") == 0.0
        assert score_content_quality("   ") == 0.0

    def test_very_short_content_scores_low(self):
        """Very short content (< 10 chars) scores low."""
        from amplihack.agents.goal_seeking.hive_mind.quality import score_content_quality

        score = score_content_quality("hi")
        assert score < 0.35

    def test_good_content_scores_high(self):
        """Well-structured, specific content scores well."""
        from amplihack.agents.goal_seeking.hive_mind.quality import score_content_quality

        content = (
            "DNA polymerase III is the primary enzyme responsible for "
            "DNA replication in E. coli, synthesizing approximately 1000 "
            "nucleotides per second with high fidelity."
        )
        score = score_content_quality(content, "biology")
        assert score >= 0.5

    def test_vague_content_scores_low(self):
        """Content with vague words scores lower."""
        from amplihack.agents.goal_seeking.hive_mind.quality import score_content_quality

        score_vague = score_content_quality("something about stuff and whatever things maybe")
        score_specific = score_content_quality(
            "Mitochondria are membrane-bound organelles found in eukaryotic cells."
        )
        assert score_specific > score_vague

    def test_concept_alignment_boosts_score(self):
        """Content mentioning the concept scores higher."""
        from amplihack.agents.goal_seeking.hive_mind.quality import score_content_quality

        content = "Genetics studies hereditary variation in living organisms."
        score_aligned = score_content_quality(content, "genetics")
        score_unaligned = score_content_quality(content, "astronomy")
        assert score_aligned >= score_unaligned

    def test_numeric_content_gets_specificity_bonus(self):
        """Content with numbers gets a specificity bonus."""
        from amplihack.agents.goal_seeking.hive_mind.quality import score_content_quality

        score_with_numbers = score_content_quality(
            "The human genome contains approximately 3 billion base pairs."
        )
        score_without = score_content_quality(
            "The human genome contains many many base pairs in total."
        )
        assert score_with_numbers >= score_without

    def test_score_always_between_0_and_1(self):
        """Score is always in [0.0, 1.0] range."""
        from amplihack.agents.goal_seeking.hive_mind.quality import score_content_quality

        test_cases = [
            "",
            "x",
            "short",
            "A normal sentence about biology.",
            "A" * 1000,
            "something stuff whatever maybe probably",
        ]
        for content in test_cases:
            score = score_content_quality(content)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for: {content!r}"


class TestQualityGate:
    """Test the QualityGate dataclass."""

    def test_default_thresholds(self):
        """Default thresholds are reasonable."""
        from amplihack.agents.goal_seeking.hive_mind.quality import QualityGate

        gate = QualityGate()
        assert gate.promotion_threshold == 0.3
        assert gate.retrieval_confidence_threshold == 0.0
        assert gate.broadcast_threshold == 0.9

    def test_custom_thresholds(self):
        """Custom thresholds can be set."""
        from amplihack.agents.goal_seeking.hive_mind.quality import QualityGate

        gate = QualityGate(
            promotion_threshold=0.5,
            retrieval_confidence_threshold=0.3,
            broadcast_threshold=0.8,
        )
        assert gate.promotion_threshold == 0.5
        assert gate.retrieval_confidence_threshold == 0.3
        assert gate.broadcast_threshold == 0.8

    def test_should_promote_good_content(self):
        """Good content passes promotion gate."""
        from amplihack.agents.goal_seeking.hive_mind.quality import QualityGate

        gate = QualityGate(promotion_threshold=0.3)
        assert gate.should_promote(
            "DNA polymerase is essential for DNA replication in all organisms.",
            "biology",
        )

    def test_should_not_promote_garbage(self):
        """Garbage content fails promotion gate."""
        from amplihack.agents.goal_seeking.hive_mind.quality import QualityGate

        gate = QualityGate(promotion_threshold=0.3)
        assert not gate.should_promote("x")

    def test_should_retrieve_above_threshold(self):
        """Facts above confidence threshold pass retrieval gate."""
        from amplihack.agents.goal_seeking.hive_mind.quality import QualityGate

        gate = QualityGate(retrieval_confidence_threshold=0.5)
        assert gate.should_retrieve(0.8)
        assert gate.should_retrieve(0.5)
        assert not gate.should_retrieve(0.4)

    def test_should_retrieve_default_no_gate(self):
        """Default retrieval threshold (0.0) lets everything through."""
        from amplihack.agents.goal_seeking.hive_mind.quality import QualityGate

        gate = QualityGate()
        assert gate.should_retrieve(0.0)
        assert gate.should_retrieve(0.1)

    def test_should_broadcast_above_threshold(self):
        """Facts above broadcast threshold pass."""
        from amplihack.agents.goal_seeking.hive_mind.quality import QualityGate

        gate = QualityGate(broadcast_threshold=0.9)
        assert gate.should_broadcast(0.95)
        assert gate.should_broadcast(0.9)
        assert not gate.should_broadcast(0.89)

    def test_score_caching(self):
        """score() caches results for same content."""
        from amplihack.agents.goal_seeking.hive_mind.quality import QualityGate

        gate = QualityGate()
        content = "A well-formed fact about biology and genetics."
        score1 = gate.score(content, "biology")
        score2 = gate.score(content, "biology")
        assert score1 == score2
        assert len(gate._quality_scores) == 1


class TestQualityGateIntegration:
    """Test quality gate integration with CognitiveAdapter."""

    def test_quality_gate_in_promote_to_hive(self):
        """_promote_to_hive applies quality gate."""
        from unittest.mock import MagicMock

        from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter

        # Create adapter with mock memory and hive
        adapter = CognitiveAdapter.__new__(CognitiveAdapter)
        adapter.agent_name = "test_agent"
        adapter._hive_store = MagicMock()
        adapter._hive_store.promote_fact = MagicMock()
        adapter._hive_store.get_agent = MagicMock(return_value=None)
        adapter._hive_store.register_agent = MagicMock()

        # Good content should pass quality gate
        adapter._promote_to_hive(
            "biology",
            "DNA polymerase III synthesizes new DNA strands during replication.",
            0.9,
        )
        adapter._hive_store.promote_fact.assert_called_once()

    def test_quality_gate_rejects_garbage(self):
        """_promote_to_hive rejects low-quality content."""
        from unittest.mock import MagicMock

        from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter

        adapter = CognitiveAdapter.__new__(CognitiveAdapter)
        adapter.agent_name = "test_agent"
        adapter._hive_store = MagicMock()
        adapter._hive_store.promote_fact = MagicMock()

        # Garbage content should be rejected by quality gate
        adapter._promote_to_hive("x", "x", 0.9)
        adapter._hive_store.promote_fact.assert_not_called()


class TestBroadcastThresholdConfigurable:
    """Test that broadcast_threshold is configurable on InMemoryHiveGraph."""

    def test_default_broadcast_threshold(self):
        """Default broadcast threshold is 0.9."""
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import InMemoryHiveGraph

        hive = InMemoryHiveGraph("test")
        assert hive._broadcast_threshold == 0.9

    def test_custom_broadcast_threshold(self):
        """Custom broadcast threshold can be set."""
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import InMemoryHiveGraph

        hive = InMemoryHiveGraph("test", broadcast_threshold=0.7)
        assert hive._broadcast_threshold == 0.7

    def test_broadcast_uses_configurable_threshold(self):
        """promote_fact uses configurable broadcast_threshold."""
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
            HiveFact,
            InMemoryHiveGraph,
        )

        parent = InMemoryHiveGraph("parent")
        # Child with lowered threshold
        child = InMemoryHiveGraph("child", broadcast_threshold=0.5)
        child.set_parent(parent)
        parent.add_child(child)
        child.register_agent("a1")

        # Fact at 0.6 confidence -- below default 0.9 but above custom 0.5
        child.promote_fact(
            "a1",
            HiveFact(fact_id="f1", content="Moderate confidence fact", confidence=0.6),
        )

        # Parent should have received the broadcast
        parent_facts = parent.query_facts("")
        assert any("Moderate confidence fact" in f.content for f in parent_facts), (
            "Fact should be broadcast with lowered threshold"
        )
