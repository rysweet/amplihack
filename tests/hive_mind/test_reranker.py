"""Tests for hive_mind.reranker -- cross-encoder reranking and RRF merge.

Tests both the cross-encoder path (mocked) and the dependency-free RRF
merge, plus hybrid scoring.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import numpy as np


class TestHasCrossEncoder:
    """Test availability detection."""

    def test_has_cross_encoder_flag_exists(self):
        """HAS_CROSS_ENCODER flag is exported."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import HAS_CROSS_ENCODER

        assert isinstance(HAS_CROSS_ENCODER, bool)


class TestScoredFact:
    """Test ScoredFact dataclass."""

    def test_scored_fact_creation(self):
        """ScoredFact stores fact, score, and source."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import ScoredFact

        sf = ScoredFact(fact="test", score=0.9, source="keyword")
        assert sf.fact == "test"
        assert sf.score == 0.9
        assert sf.source == "keyword"

    def test_scored_fact_default_source(self):
        """ScoredFact defaults source to 'unknown'."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import ScoredFact

        sf = ScoredFact(fact="test", score=0.5)
        assert sf.source == "unknown"


class TestCrossEncoderReranker:
    """Test CrossEncoderReranker with mocked model."""

    def test_unavailable_falls_back_to_confidence(self):
        """When model unavailable, falls back to confidence-based ranking."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import CrossEncoderReranker

        reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
        reranker._model = None
        reranker._model_name = "test"

        @dataclass
        class FakeFact:
            content: str
            confidence: float

        facts = [
            FakeFact(content="low", confidence=0.3),
            FakeFact(content="high", confidence=0.9),
            FakeFact(content="mid", confidence=0.6),
        ]

        scored = reranker.rerank("query", facts)
        assert len(scored) == 3
        assert scored[0].fact.confidence == 0.9
        assert scored[1].fact.confidence == 0.6
        assert scored[2].fact.confidence == 0.3
        assert scored[0].source == "confidence_fallback"

    def test_empty_facts_returns_empty(self):
        """Reranking empty list returns empty."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import CrossEncoderReranker

        reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
        reranker._model = None
        reranker._model_name = "test"

        assert reranker.rerank("query", []) == []

    def test_rerank_with_mock_model(self):
        """Reranking with mock model uses cross-encoder scores."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import CrossEncoderReranker

        reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.2, 0.8, 0.5])
        reranker._model = mock_model
        reranker._model_name = "test"

        @dataclass
        class FakeFact:
            content: str
            confidence: float

        facts = [
            FakeFact(content="a", confidence=0.9),
            FakeFact(content="b", confidence=0.3),
            FakeFact(content="c", confidence=0.6),
        ]

        scored = reranker.rerank("query", facts)
        assert len(scored) == 3
        # Should be sorted by cross-encoder score: b(0.8) > c(0.5) > a(0.2)
        assert scored[0].fact.content == "b"
        assert scored[1].fact.content == "c"
        assert scored[2].fact.content == "a"
        assert scored[0].source == "cross_encoder"

    def test_rerank_respects_limit(self):
        """Reranking respects the limit parameter."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import CrossEncoderReranker

        reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
        reranker._model = None
        reranker._model_name = "test"

        @dataclass
        class FakeFact:
            content: str
            confidence: float

        facts = [FakeFact(content=f"fact{i}", confidence=i * 0.1) for i in range(10)]
        scored = reranker.rerank("query", facts, limit=3)
        assert len(scored) == 3

    def test_available_property(self):
        """available reflects model state."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import CrossEncoderReranker

        reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
        reranker._model = None
        reranker._model_name = "test"
        assert reranker.available is False

        reranker._model = MagicMock()
        assert reranker.available is True


class TestHybridScore:
    """Test hybrid_score combining keyword and vector scores."""

    def test_default_weights(self):
        """Default weights: 0.4 keyword + 0.6 vector."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import hybrid_score

        score = hybrid_score(keyword_score=1.0, vector_score=1.0)
        assert abs(score - 1.0) < 1e-5

    def test_keyword_only(self):
        """Keyword-only score with zero vector."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import hybrid_score

        score = hybrid_score(keyword_score=1.0, vector_score=0.0)
        assert abs(score - 0.4) < 1e-5

    def test_vector_only(self):
        """Vector-only score with zero keyword."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import hybrid_score

        score = hybrid_score(keyword_score=0.0, vector_score=1.0)
        assert abs(score - 0.6) < 1e-5

    def test_custom_weights(self):
        """Custom weights are respected."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import hybrid_score

        score = hybrid_score(
            keyword_score=1.0,
            vector_score=1.0,
            keyword_weight=0.7,
            vector_weight=0.3,
        )
        assert abs(score - 1.0) < 1e-5

    def test_zero_scores(self):
        """Zero scores produce zero result."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import hybrid_score

        assert hybrid_score(0.0, 0.0) == 0.0


class TestRRFMerge:
    """Test Reciprocal Rank Fusion merge."""

    def test_single_list(self):
        """Single list returns items in same order."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import rrf_merge

        @dataclass
        class Item:
            fact_id: str
            value: str

        items = [Item("a", "first"), Item("b", "second"), Item("c", "third")]
        result = rrf_merge(items)
        assert len(result) == 3
        assert result[0].fact.fact_id == "a"

    def test_two_lists_boost_shared_items(self):
        """Items appearing in both lists get higher RRF score."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import rrf_merge

        @dataclass
        class Item:
            fact_id: str

        # 'b' appears in both lists, should rank higher
        list1 = [Item("a"), Item("b"), Item("c")]
        list2 = [Item("b"), Item("d"), Item("a")]

        result = rrf_merge(list1, list2)
        # 'b' appears at rank 1 in list1 and rank 0 in list2 -> highest combined
        ids = [r.fact.fact_id for r in result]
        assert ids[0] in ("a", "b")  # Both appear in both lists

    def test_empty_lists(self):
        """Empty lists produce empty result."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import rrf_merge

        result = rrf_merge([], [])
        assert result == []

    def test_respects_limit(self):
        """RRF respects the limit parameter."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import rrf_merge

        @dataclass
        class Item:
            fact_id: str

        items = [Item(f"item{i}") for i in range(10)]
        result = rrf_merge(items, limit=3)
        assert len(result) == 3

    def test_rrf_scores_decrease(self):
        """RRF scores decrease for lower-ranked items."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import rrf_merge

        @dataclass
        class Item:
            fact_id: str

        items = [Item(f"item{i}") for i in range(5)]
        result = rrf_merge(items)
        for i in range(len(result) - 1):
            assert result[i].score >= result[i + 1].score

    def test_source_is_rrf(self):
        """RRF results have source='rrf'."""
        from amplihack.agents.goal_seeking.hive_mind.reranker import rrf_merge

        @dataclass
        class Item:
            fact_id: str

        result = rrf_merge([Item("a")])
        assert result[0].source == "rrf"


class TestQueryFederatedUsesRRF:
    """Test that query_federated uses RRF for merging."""

    def test_federated_query_returns_results(self):
        """query_federated works with federation tree."""
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
            HiveFact,
            InMemoryHiveGraph,
        )

        parent = InMemoryHiveGraph("parent")
        child1 = InMemoryHiveGraph("child1")
        child2 = InMemoryHiveGraph("child2")

        child1.set_parent(parent)
        child2.set_parent(parent)
        parent.add_child(child1)
        parent.add_child(child2)

        parent.register_agent("relay")
        child1.register_agent("bio_agent", domain="biology")
        child2.register_agent("cs_agent", domain="computing")

        child1.promote_fact(
            "bio_agent",
            HiveFact(fact_id="f1", content="DNA stores genetic information", concept="genetics"),
        )
        child2.promote_fact(
            "cs_agent",
            HiveFact(
                fact_id="f2",
                content="DNA sequence analysis uses algorithms",
                concept="bioinformatics",
            ),
        )

        results = parent.query_federated("DNA genetics", limit=10)
        assert len(results) >= 1
        contents = {f.content for f in results}
        assert "DNA stores genetic information" in contents
