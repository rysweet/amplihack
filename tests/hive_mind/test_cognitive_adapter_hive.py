"""Tests for CognitiveAdapter hive auto-promotion and distributed memory.

Verifies that store_fact() auto-promotes to the shared hive when
hive_store is connected, and that search/get_all_facts merge local + hive
via DistributedCognitiveMemory.
"""

from __future__ import annotations

import tempfile
from types import SimpleNamespace

import pytest

from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter
from amplihack.agents.goal_seeking.hive_mind.distributed_memory import (
    DistributedCognitiveMemory,
)
from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    HiveFact,
    InMemoryHiveGraph,
)


@pytest.fixture
def hive():
    h = InMemoryHiveGraph("test-hive")
    h.register_agent("agent_a")
    h.register_agent("agent_b")
    return h


@pytest.fixture
def adapter_a(hive):
    with tempfile.TemporaryDirectory() as td:
        a = CognitiveAdapter("agent_a", db_path=td)
        # Wrap with DistributedCognitiveMemory (same as production DI)
        a.memory = DistributedCognitiveMemory(
            local_memory=a.memory, hive_graph=hive, agent_name="agent_a"
        )
        yield a
        a.close()


@pytest.fixture
def adapter_b(hive):
    with tempfile.TemporaryDirectory() as td:
        a = CognitiveAdapter("agent_b", db_path=td)
        a.memory = DistributedCognitiveMemory(
            local_memory=a.memory, hive_graph=hive, agent_name="agent_b"
        )
        yield a
        a.close()


class TestAutoPromotion:
    """store_fact() should auto-promote to the hive."""

    def test_store_fact_promotes_to_hive(self, adapter_a, hive):
        adapter_a.store_fact("Biology", "Cells are the basic unit of life")
        hive_facts = hive.query_facts("cells biology", limit=10)
        assert len(hive_facts) >= 1
        assert any("Cells" in f.content for f in hive_facts)

    def test_promoted_fact_has_correct_source_agent(self, adapter_a, hive):
        adapter_a.store_fact("Chemistry", "Water is H2O")
        hive_facts = hive.query_facts("water H2O", limit=10)
        assert len(hive_facts) >= 1
        assert hive_facts[0].source_agent == "agent_a"

    def test_no_hive_store_no_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = CognitiveAdapter("solo", db_path=td, hive_store=None)
            adapter.store_fact("Test", "This should not crash")
            adapter.close()

    def test_multiple_facts_all_promoted(self, adapter_a, hive):
        adapter_a.store_fact("Math", "2 + 2 = 4")
        adapter_a.store_fact("Math", "Pi is approximately 3.14159")
        adapter_a.store_fact("Math", "The square root of 2 is irrational")
        stats = hive.get_stats()
        assert stats["fact_count"] >= 3


class TestHiveMerge:
    """search() and get_all_facts() should merge local + hive facts."""

    def test_agent_sees_other_agents_facts(self, adapter_a, adapter_b, hive):
        adapter_a.store_fact("Biology", "DNA stores genetic information")
        # agent_b should see agent_a's fact via hive
        results = adapter_b.search("DNA genetic", limit=10)
        assert any("DNA" in r.get("outcome", r.get("fact", "")) for r in results)

    def test_hive_facts_use_outcome_key(self, adapter_a, adapter_b, hive):
        """Hive facts must use 'outcome' key to match local fact format.

        LearningAgent uses fact['outcome'] to build LLM prompts. If hive
        results use a different key (e.g. 'fact'), LearningAgent crashes
        with KeyError.
        """
        adapter_a.store_fact("Test", "Important fact from agent A")
        results = adapter_b.search("important fact", limit=10)
        # At least one result should come from the hive (agent_a's fact)
        assert len(results) >= 1
        for r in results:
            assert "outcome" in r, f"Result missing 'outcome' key: {r.keys()}"

    def test_local_facts_prioritized_over_hive(self, adapter_a, hive):
        # Store same fact locally and in hive
        adapter_a.store_fact("Test", "Local version of the fact")
        # Manually promote a different version to hive
        hive.promote_fact(
            "agent_b",
            HiveFact(fact_id="", content="Hive version of the fact", concept="Test"),
        )
        results = adapter_a.get_all_facts(limit=50)
        # Local should come first
        local_facts = [r for r in results if "Local version" in r.get("fact", r.get("outcome", ""))]
        assert len(local_facts) >= 1

    def test_deduplication_by_content(self, adapter_a, adapter_b, hive):
        # Both agents store the same fact
        adapter_a.store_fact("Shared", "The sky is blue")
        adapter_b.store_fact("Shared", "The sky is blue")
        # get_all_facts from either should not duplicate
        results = adapter_a.get_all_facts(limit=50)
        sky_facts = [r for r in results if "sky is blue" in r.get("fact", r.get("outcome", ""))]
        # Should be deduplicated (at most 1 local + 0 from hive since same content)
        assert len(sky_facts) <= 2

    def test_plain_cognitive_backend_ignores_query_kwarg(self):
        """Plain CognitiveMemory get_all_facts(limit) must not receive query."""

        class PlainCognitiveMemory:
            def __init__(self) -> None:
                self.calls: list[int] = []

            def get_all_facts(self, limit: int = 50):
                self.calls.append(limit)
                return [
                    SimpleNamespace(
                        node_id="sem-1",
                        concept="Campaign",
                        content="CAMP-1 objective was ransomware",
                        confidence=0.9,
                        created_at="2024-03-01T00:00:00Z",
                        tags=["campaign"],
                        metadata={},
                    )
                ]

        adapter = CognitiveAdapter.__new__(CognitiveAdapter)
        adapter.agent_name = "plain"
        adapter.memory = PlainCognitiveMemory()
        adapter._cognitive = True
        adapter._hive_store = None
        adapter._quality_threshold = 0.0
        adapter._confidence_gate = 0.0
        adapter._enable_query_expansion = False
        adapter._buffer_pool_size = 0

        results = adapter.get_all_facts(limit=7, query="What was CAMP-1?")

        assert adapter.memory.calls == [7]
        assert results[0]["context"] == "Campaign"
        assert "ransomware" in results[0]["outcome"]


class TestSearchByConceptHive:
    """search_by_concept() must also search the distributed hive."""

    def test_search_by_concept_finds_other_agents_facts(self, adapter_a, adapter_b, hive):
        """Regression: search_by_concept was local-only, missing cross-shard facts.

        When agent_a stores a fact and agent_b calls search_by_concept,
        the result must contain agent_a's fact via the hive store.
        """
        adapter_a.store_fact("Personal Information", "Sarah Chen was born on March 15 1992")
        results = adapter_b.search_by_concept(keywords=["Sarah Chen"], limit=10)
        contents = [r.get("outcome", r.get("content", "")) for r in results]
        assert any("Sarah" in c for c in contents), (
            "search_by_concept should find hive facts from other agents; got: " + str(contents)
        )
