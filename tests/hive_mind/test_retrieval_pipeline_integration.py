"""Integration tests for retrieval pipeline wired into hive mind.

Tests that embeddings, quality, reranker, and query_expansion are
properly integrated into InMemoryHiveGraph and CognitiveAdapter.
"""

from __future__ import annotations

import tempfile

import pytest

from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter
from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    HiveEdge,
    HiveFact,
    InMemoryHiveGraph,
)

# ---------------------------------------------------------------------------
# InMemoryHiveGraph with embedding_generator
# ---------------------------------------------------------------------------


class _MockEmbeddingGenerator:
    """Mock embedding generator for testing (bag-of-words, no ML)."""

    def __init__(self) -> None:
        self._vocab: dict[str, int] = {}
        self._dim: int = 0

    def _tokenize(self, text: str) -> list[str]:
        return [w.lower() for w in text.split() if len(w) > 1]

    def embed(self, text: str) -> list[float]:
        tokens = self._tokenize(text)
        for token in tokens:
            if token not in self._vocab:
                self._vocab[token] = self._dim
                self._dim += 1
        vec = [0.0] * self._dim
        for token in tokens:
            vec[self._vocab[token]] += 1.0
        return vec

    @property
    def available(self) -> bool:
        return True


class TestEmbeddingIntegration:
    """InMemoryHiveGraph with embedding_generator parameter."""

    @pytest.fixture
    def emb_gen(self):
        return _MockEmbeddingGenerator()

    @pytest.fixture
    def hive(self, emb_gen):
        h = InMemoryHiveGraph("emb-hive", embedding_generator=emb_gen)
        h.register_agent("agent_a", domain="biology")
        return h

    def test_init_accepts_embedding_generator(self, emb_gen):
        h = InMemoryHiveGraph("test", embedding_generator=emb_gen)
        assert h._embedding_generator is emb_gen

    def test_init_without_embedding_generator(self):
        h = InMemoryHiveGraph("test")
        assert h._embedding_generator is None

    def test_promote_fact_generates_embedding(self, hive):
        fid = hive.promote_fact(
            "agent_a",
            HiveFact(fact_id="", content="DNA stores genetic info", concept="genetics"),
        )
        assert fid in hive._embeddings
        assert len(hive._embeddings[fid]) > 0

    def test_query_facts_uses_vector_search(self, hive):
        hive.promote_fact(
            "agent_a",
            HiveFact(fact_id="f1", content="DNA stores genetic information", concept="genetics"),
        )
        hive.promote_fact(
            "agent_a",
            HiveFact(fact_id="f2", content="Python is a programming language", concept="coding"),
        )
        results = hive.query_facts("DNA genetics biology", limit=5)
        assert len(results) >= 1
        assert results[0].fact_id == "f1"

    def test_vector_search_fallback_to_keyword(self):
        h = InMemoryHiveGraph("test")
        h.register_agent("a")
        h.promote_fact("a", HiveFact(fact_id="f1", content="DNA genetics", concept="bio"))
        results = h.query_facts("DNA", limit=5)
        assert len(results) == 1

    def test_empty_query_with_embeddings(self, hive):
        hive.promote_fact("agent_a", HiveFact(fact_id="f1", content="some fact", concept="test"))
        results = hive.query_facts("", limit=5)
        assert len(results) >= 1

    def test_hybrid_scoring_with_confirmations(self, hive):
        hive.promote_fact(
            "agent_a",
            HiveFact(fact_id="f1", content="DNA stores genetic info", concept="genetics"),
        )
        hive.add_edge(HiveEdge(source_id="agent_b", target_id="f1", edge_type="CONFIRMED_BY"))
        results = hive.query_facts("DNA genetics", limit=5)
        assert len(results) >= 1

    def test_hybrid_scoring_uses_agent_trust(self, hive):
        hive.update_trust("agent_a", 2.0)
        hive.promote_fact(
            "agent_a",
            HiveFact(fact_id="f1", content="DNA stores info", concept="genetics"),
        )
        results = hive.query_facts("DNA genetics", limit=5)
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# Configurable broadcast_threshold
# ---------------------------------------------------------------------------


class TestBroadcastThreshold:
    """broadcast_threshold is configurable on InMemoryHiveGraph constructor."""

    def test_default_threshold_is_09(self):
        h = InMemoryHiveGraph("test")
        assert h._broadcast_threshold == 0.9

    def test_custom_threshold(self):
        h = InMemoryHiveGraph("test", broadcast_threshold=0.7)
        assert h._broadcast_threshold == 0.7

    def test_threshold_clamped(self):
        h = InMemoryHiveGraph("test", broadcast_threshold=1.5)
        assert h._broadcast_threshold == 1.0
        h2 = InMemoryHiveGraph("test2", broadcast_threshold=-0.5)
        assert h2._broadcast_threshold == 0.0

    def test_low_threshold_broadcasts_to_siblings(self):
        parent = InMemoryHiveGraph("parent")
        child_a = InMemoryHiveGraph("child_a", broadcast_threshold=0.5)
        child_a.register_agent("agent_a")
        child_b = InMemoryHiveGraph("child_b")
        child_b.register_agent("agent_b")
        parent.add_child(child_a)
        parent.add_child(child_b)
        child_a.set_parent(parent)
        child_b.set_parent(parent)

        child_a.promote_fact(
            "agent_a",
            HiveFact(fact_id="f1", content="Low threshold fact", concept="test", confidence=0.6),
        )
        sibling_facts = child_b.query_facts("Low threshold", limit=10)
        assert len(sibling_facts) >= 1

    def test_high_threshold_blocks_broadcast(self):
        parent = InMemoryHiveGraph("parent")
        child_a = InMemoryHiveGraph("child_a", broadcast_threshold=0.95)
        child_a.register_agent("agent_a")
        child_b = InMemoryHiveGraph("child_b")
        child_b.register_agent("agent_b")
        parent.add_child(child_a)
        parent.add_child(child_b)
        child_a.set_parent(parent)
        child_b.set_parent(parent)

        child_a.promote_fact(
            "agent_a",
            HiveFact(fact_id="f1", content="High threshold fact", concept="test", confidence=0.9),
        )
        sibling_facts = child_b.query_facts("High threshold", limit=10)
        assert len(sibling_facts) == 0


# ---------------------------------------------------------------------------
# RRF merge in query_federated()
# ---------------------------------------------------------------------------


class TestRRFInFederated:
    """query_federated() uses rrf_merge for Phase 2 re-ranking."""

    @pytest.fixture
    def federated_hive(self):
        root = InMemoryHiveGraph("root")
        root.register_agent("root_agent")
        child = InMemoryHiveGraph("child")
        child.register_agent("child_agent")
        root.add_child(child)
        child.set_parent(root)
        return root, child

    def test_federated_query_returns_results(self, federated_hive):
        root, child = federated_hive
        root.promote_fact(
            "root_agent",
            HiveFact(fact_id="f1", content="Root DNA fact", concept="genetics"),
        )
        child.promote_fact(
            "child_agent",
            HiveFact(fact_id="f2", content="Child DNA fact", concept="genetics"),
        )
        results = root.query_federated("DNA genetics", limit=10)
        assert len(results) >= 2

    def test_federated_query_deduplicates(self, federated_hive):
        root, child = federated_hive
        root.promote_fact(
            "root_agent",
            HiveFact(fact_id="f1", content="Same DNA fact", concept="genetics"),
        )
        child.promote_fact(
            "child_agent",
            HiveFact(fact_id="f2", content="Same DNA fact", concept="genetics"),
        )
        results = root.query_federated("DNA genetics", limit=10)
        contents = [f.content for f in results]
        assert contents.count("Same DNA fact") == 1


# ---------------------------------------------------------------------------
# Quality gate in CognitiveAdapter._promote_to_hive()
# ---------------------------------------------------------------------------


class TestQualityGateConfigurable:
    """CognitiveAdapter quality threshold is configurable."""

    @pytest.fixture
    def hive(self):
        h = InMemoryHiveGraph("test-hive")
        h.register_agent("agent_a")
        return h

    def test_high_quality_fact_promoted(self, hive):
        with tempfile.TemporaryDirectory() as td:
            adapter = CognitiveAdapter("agent_a", db_path=td, hive_store=hive)
            adapter.store_fact(
                "Biology",
                "Mitochondria are the powerhouses of the cell, producing ATP through oxidative phosphorylation.",
            )
            hive_facts = hive.query_facts("mitochondria", limit=10)
            assert len(hive_facts) >= 1
            adapter.close()

    def test_low_quality_fact_rejected_with_high_threshold(self, hive):
        with tempfile.TemporaryDirectory() as td:
            adapter = CognitiveAdapter(
                "agent_a", db_path=td, hive_store=hive, quality_threshold=0.9
            )
            adapter.store_fact("Test", "ok things")
            hive_facts = hive.query_facts("ok things", limit=10)
            assert len(hive_facts) == 0
            adapter.close()

    def test_quality_threshold_zero_accepts_all(self, hive):
        with tempfile.TemporaryDirectory() as td:
            adapter = CognitiveAdapter(
                "agent_a", db_path=td, hive_store=hive, quality_threshold=0.0
            )
            adapter.store_fact("Test", "short fact")
            hive_facts = hive.query_facts("short fact", limit=10)
            assert len(hive_facts) >= 1
            adapter.close()


# ---------------------------------------------------------------------------
# Confidence gate in CognitiveAdapter._search_hive()
# ---------------------------------------------------------------------------


class TestConfidenceGate:
    """DistributedCognitiveMemory merges hive results into search."""

    @pytest.fixture
    def hive(self):
        h = InMemoryHiveGraph("test-hive")
        h.register_agent("agent_a")
        h.register_agent("agent_b")
        return h

    def test_high_confidence_results_returned(self, hive):
        hive.promote_fact(
            "agent_a",
            HiveFact(
                fact_id="f1",
                content="DNA stores genetic information",
                concept="genetics",
                confidence=0.9,
            ),
        )
        with tempfile.TemporaryDirectory() as td:
            from amplihack.agents.goal_seeking.hive_mind.distributed_memory import (
                DistributedCognitiveMemory,
            )

            adapter = CognitiveAdapter("agent_b", db_path=td)
            adapter.memory = DistributedCognitiveMemory(
                local_memory=adapter.memory, hive_graph=hive, agent_name="agent_b"
            )
            results = adapter.search("DNA genetics", limit=10)
            assert any("DNA" in r.get("outcome", "") for r in results)
            adapter.close()

    def test_low_confidence_results_still_available(self, hive):
        """Low confidence facts from hive are available (filtering moved to LLM layer)."""
        hive.promote_fact(
            "agent_a",
            HiveFact(
                fact_id="f1",
                content="Maybe DNA does something",
                concept="genetics",
                confidence=0.1,
            ),
        )
        with tempfile.TemporaryDirectory() as td:
            from amplihack.agents.goal_seeking.hive_mind.distributed_memory import (
                DistributedCognitiveMemory,
            )

            adapter = CognitiveAdapter("agent_b", db_path=td)
            adapter.memory = DistributedCognitiveMemory(
                local_memory=adapter.memory, hive_graph=hive, agent_name="agent_b"
            )
            results = adapter.search("DNA genetics", limit=10)
            # DistributedCognitiveMemory returns all hive results regardless of
            # confidence — gating is the LLM's responsibility.
            assert isinstance(results, list)
            assert any(
                "DNA" in r.get("outcome", "") or "DNA" in r.get("content", "") for r in results
            ), f"Expected low-confidence DNA fact in results but got: {results}"
            adapter.close()

    def test_confidence_gate_zero_disables(self, hive):
        hive.promote_fact(
            "agent_a",
            HiveFact(
                fact_id="f1",
                content="Low confidence DNA fact",
                concept="genetics",
                confidence=0.1,
            ),
        )
        with tempfile.TemporaryDirectory() as td:
            from amplihack.agents.goal_seeking.hive_mind.distributed_memory import (
                DistributedCognitiveMemory,
            )

            adapter = CognitiveAdapter("agent_b", db_path=td)
            adapter.memory = DistributedCognitiveMemory(
                local_memory=adapter.memory, hive_graph=hive, agent_name="agent_b"
            )
            results = adapter.search("DNA genetics Low confidence", limit=10)
            assert any("DNA" in r.get("outcome", "") for r in results)
            adapter.close()


# ---------------------------------------------------------------------------
# Query expansion integration
# ---------------------------------------------------------------------------


class TestQueryExpansionIntegration:
    """CognitiveAdapter optionally uses query expansion."""

    @pytest.fixture
    def hive(self):
        h = InMemoryHiveGraph("test-hive")
        h.register_agent("agent_a")
        h.register_agent("agent_b")
        return h

    def test_expansion_disabled_by_default(self, hive):
        with tempfile.TemporaryDirectory() as td:
            adapter = CognitiveAdapter("agent_b", db_path=td, hive_store=hive)
            assert adapter._enable_query_expansion is False
            adapter.close()

    def test_expansion_enabled_via_constructor(self, hive):
        with tempfile.TemporaryDirectory() as td:
            adapter = CognitiveAdapter(
                "agent_b", db_path=td, hive_store=hive, enable_query_expansion=True
            )
            assert adapter._enable_query_expansion is True
            adapter.close()

    def test_expansion_no_crash(self, hive):
        with tempfile.TemporaryDirectory() as td:
            adapter = CognitiveAdapter(
                "agent_b", db_path=td, hive_store=hive, enable_query_expansion=True
            )
            results = adapter.search("error system", limit=10)
            assert isinstance(results, list)
            adapter.close()


# hybrid_score_weighted tests are in test_reranker.py (canonical location)


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """All modules gracefully degrade when imports fail."""

    def test_hive_graph_without_embeddings(self):
        h = InMemoryHiveGraph("test")
        h.register_agent("a")
        h.promote_fact("a", HiveFact(fact_id="", content="test fact", concept="test"))
        results = h.query_facts("test", limit=5)
        assert len(results) >= 1

    def test_adapter_without_hive(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = CognitiveAdapter("a", db_path=td, hive_store=None)
            adapter.store_fact("Test", "Some fact about testing things")
            results = adapter.search("test", limit=5)
            assert isinstance(results, list)
            adapter.close()

    def test_broken_embedding_generator_falls_back(self):
        class BrokenGenerator:
            available = True

            def embed(self, text: str):
                raise RuntimeError("Broken!")

        h = InMemoryHiveGraph("test", embedding_generator=BrokenGenerator())
        h.register_agent("a")
        h.promote_fact("a", HiveFact(fact_id="f1", content="DNA genetics", concept="bio"))
        results = h.query_facts("DNA", limit=5)
        assert len(results) >= 1
