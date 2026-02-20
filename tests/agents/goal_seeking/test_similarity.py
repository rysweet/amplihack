"""Tests for similarity computation module.

Philosophy:
- Deterministic tests (no randomness)
- Verify Jaccard coefficient behavior
- Verify composite similarity weighting
"""

import pytest

from amplihack.agents.goal_seeking.similarity import (
    compute_similarity,
    compute_tag_similarity,
    compute_word_similarity,
    rerank_facts_by_query,
)


class TestWordSimilarity:
    """Tests for compute_word_similarity."""

    def test_identical_texts_return_one(self):
        """Identical texts should have similarity 1.0."""
        score = compute_word_similarity(
            "photosynthesis converts light energy",
            "photosynthesis converts light energy",
        )
        assert score == pytest.approx(1.0)

    def test_disjoint_texts_return_zero(self):
        """Completely different texts should have similarity 0.0."""
        score = compute_word_similarity(
            "quantum entanglement physics",
            "chocolate cake recipe baking",
        )
        assert score == pytest.approx(0.0)

    def test_partial_overlap(self):
        """Partially overlapping texts should have intermediate similarity."""
        score = compute_word_similarity(
            "plants use photosynthesis for energy",
            "photosynthesis converts light into energy",
        )
        assert 0.0 < score < 1.0

    def test_empty_text_returns_zero(self):
        """Empty texts should return 0.0."""
        assert compute_word_similarity("", "hello world") == 0.0
        assert compute_word_similarity("hello world", "") == 0.0
        assert compute_word_similarity("", "") == 0.0

    def test_stop_words_ignored(self):
        """Stop words should not contribute to similarity."""
        # "the" and "is" are stop words, only "cat" and "mat" matter
        score = compute_word_similarity("the cat", "the mat")
        # cat vs mat = no overlap -> 0.0
        assert score == pytest.approx(0.0)


class TestTagSimilarity:
    """Tests for compute_tag_similarity."""

    def test_identical_tags(self):
        """Identical tag lists should have similarity 1.0."""
        score = compute_tag_similarity(["biology", "plants"], ["biology", "plants"])
        assert score == pytest.approx(1.0)

    def test_disjoint_tags(self):
        """Completely different tags should have similarity 0.0."""
        score = compute_tag_similarity(["biology", "plants"], ["physics", "quantum"])
        assert score == pytest.approx(0.0)

    def test_partial_overlap_tags(self):
        """Partial tag overlap should give intermediate similarity."""
        score = compute_tag_similarity(["biology", "plants", "energy"], ["biology", "energy"])
        # intersection=2, union=3 -> 2/3
        assert score == pytest.approx(2.0 / 3.0)

    def test_empty_tags_return_zero(self):
        """Empty tag lists should return 0.0."""
        assert compute_tag_similarity([], ["biology"]) == 0.0
        assert compute_tag_similarity(["biology"], []) == 0.0


class TestCompositeSimilarity:
    """Tests for compute_similarity (weighted composite)."""

    def test_identical_nodes_return_one(self):
        """Identical nodes should have similarity 1.0."""
        node = {
            "content": "Plants use photosynthesis",
            "tags": ["biology", "plants"],
            "concept": "photosynthesis",
        }
        score = compute_similarity(node, node)
        assert score == pytest.approx(1.0)

    def test_weights_applied_correctly(self):
        """Verify that weights 0.5/0.2/0.3 are applied."""
        # Node with only content similarity
        node_a = {"content": "photosynthesis energy", "tags": [], "concept": ""}
        node_b = {"content": "photosynthesis energy", "tags": ["unrelated"], "concept": "other"}

        score = compute_similarity(node_a, node_b)
        # word_sim = 1.0, tag_sim = 0.0, concept_sim = 0.0
        # 0.5*1.0 + 0.2*0.0 + 0.3*0.0 = 0.5
        assert score == pytest.approx(0.5)

    def test_empty_nodes(self):
        """Empty nodes should have similarity 0.0."""
        score = compute_similarity({}, {})
        assert score == pytest.approx(0.0)


class TestRerankFactsByQuery:
    """Tests for rerank_facts_by_query."""

    def test_reranks_most_relevant_first(self):
        """Facts most relevant to query should be ranked first."""
        facts = [
            {"context": "General", "outcome": "Dogs are popular pets"},
            {"context": "Climate", "outcome": "Norway won gold medals in skiing"},
            {"context": "Sports", "outcome": "Gold medal count for Olympics"},
        ]
        reranked = rerank_facts_by_query(facts, "How many gold medals did Norway win?")
        # "Norway" + "gold" + "medals" appear in fact[1], so it should rank first
        assert "Norway" in reranked[0]["outcome"]

    def test_preserves_all_facts(self):
        """All facts should be preserved even if irrelevant."""
        facts = [
            {"context": "A", "outcome": "Cats are cute"},
            {"context": "B", "outcome": "Dogs are loyal"},
            {"context": "C", "outcome": "Fish swim well"},
        ]
        reranked = rerank_facts_by_query(facts, "Tell me about quantum physics")
        assert len(reranked) == 3

    def test_empty_query_returns_original_order(self):
        """Empty query should return facts in original order."""
        facts = [
            {"context": "A", "outcome": "First fact"},
            {"context": "B", "outcome": "Second fact"},
        ]
        reranked = rerank_facts_by_query(facts, "")
        assert reranked == facts

    def test_empty_facts_returns_empty(self):
        """Empty facts list should return empty."""
        assert rerank_facts_by_query([], "some query") == []

    def test_top_k_limits_results(self):
        """top_k should limit returned facts."""
        facts = [
            {"context": "A", "outcome": "Fact one about topic"},
            {"context": "B", "outcome": "Fact two about something"},
            {"context": "C", "outcome": "Fact three about topic"},
        ]
        reranked = rerank_facts_by_query(facts, "topic", top_k=2)
        assert len(reranked) == 2
