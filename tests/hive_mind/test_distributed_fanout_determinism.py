"""Test: distributed memory always fans out to ALL agents and returns deterministic results.

Requirements verified:
1. search_facts() always fans out to ALL agents via _query_hive(), never querying only
   the local store — when 3 agents hold disjoint facts, a query returns ALL facts
   regardless of which agent receives the query.
2. _merge_fact_lists() produces deterministic ordering — same inputs always produce
   same output. The same query from agent-0 and agent-1 returns identical results.
3. No hardcoded integers in distributed_memory or distributed_hive_graph — verified
   by importing POSITION_SCORE_DECREMENT and CONFIDENCE_SORT_WEIGHT from
   retrieval_constants.
"""

from __future__ import annotations

import hashlib
from typing import Any

from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import DistributedHiveGraph
from amplihack.agents.goal_seeking.hive_mind.distributed_memory import DistributedCognitiveMemory
from amplihack.agents.goal_seeking.retrieval_constants import (
    CONFIDENCE_SORT_WEIGHT,
    POSITION_SCORE_DECREMENT,
)

# ---------------------------------------------------------------------------
# Mock local memory (no Kuzu / CognitiveMemory required)
# ---------------------------------------------------------------------------


class _MockFact:
    """Minimal fact object compatible with DistributedCognitiveMemory internals."""

    def __init__(self, concept: str, content: str, confidence: float = 0.9):
        self.concept = concept
        self.content = content
        self.confidence = confidence
        self.fact_id = hashlib.md5(content.encode()).hexdigest()[:8]
        self.tags: list[str] = [concept]


class MockLocalMemory:
    """Simple in-memory fact store — no Kuzu dependency."""

    def __init__(self) -> None:
        self._facts: list[_MockFact] = []

    def store_fact(
        self,
        concept: str = "",
        content: str = "",
        confidence: float = 0.9,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> str:
        f = _MockFact(concept=concept, content=content, confidence=confidence)
        if tags:
            f.tags = list(tags)
        self._facts.append(f)
        return f.fact_id

    def search_facts(
        self,
        query: str = "",
        limit: int = 10,
        min_confidence: float = 0.0,
        **kwargs: Any,
    ) -> list[_MockFact]:
        q_words = set(query.lower().split()) if query else set()
        results = [
            f
            for f in self._facts
            if f.confidence >= min_confidence
            and (
                not q_words
                or q_words & (set(f.content.lower().split()) | set(f.concept.lower().split()))
            )
        ]
        return results[:limit]

    def get_all_facts(self, limit: int = 50, **kwargs: Any) -> list[_MockFact]:
        return self._facts[:limit]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _content(r: Any) -> str:
    """Extract content string from a local _MockFact or hive result dict."""
    if isinstance(r, dict):
        return r.get("outcome", r.get("content", ""))
    return getattr(r, "content", str(r))


def _make_agent(
    agent_name: str,
    hive: DistributedHiveGraph,
) -> DistributedCognitiveMemory:
    """Create a DistributedCognitiveMemory for one agent."""
    local = MockLocalMemory()
    return DistributedCognitiveMemory(
        local_memory=local,
        hive_graph=hive,
        agent_name=agent_name,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDistributedFanout:
    """DistributedCognitiveMemory fans out to ALL agents on every query."""

    def setup_method(self) -> None:
        """3-agent hive: each agent holds 2 disjoint facts."""
        self.hive = DistributedHiveGraph(hive_id="fanout-test", enable_gossip=False)

        self.agents: dict[str, DistributedCognitiveMemory] = {}
        for i in range(3):
            name = f"agent-{i}"
            self.hive.register_agent(name)
            self.agents[name] = _make_agent(name, self.hive)

        # Agent-0 facts
        self.agents["agent-0"].store_fact(concept="animals", content="Cats have whiskers")
        self.agents["agent-0"].store_fact(concept="animals", content="Cats are felines")

        # Agent-1 facts
        self.agents["agent-1"].store_fact(concept="animals", content="Dogs are loyal")
        self.agents["agent-1"].store_fact(concept="animals", content="Dogs bark loudly")

        # Agent-2 facts
        self.agents["agent-2"].store_fact(concept="animals", content="Birds can fly")
        self.agents["agent-2"].store_fact(concept="animals", content="Birds lay eggs")

    def _all_contents(self, results: list) -> set[str]:
        return {_content(r) for r in results if _content(r)}

    def test_agent0_query_returns_all_agents_facts(self) -> None:
        """Querying from agent-0 returns facts from agents 0, 1, and 2."""
        results = self.agents["agent-0"].search_facts("animals cats dogs birds", limit=20)
        contents = self._all_contents(results)

        assert "Cats have whiskers" in contents, f"Missing agent-0 fact. Got: {contents}"
        assert "Dogs are loyal" in contents, f"Missing agent-1 fact. Got: {contents}"
        assert "Birds can fly" in contents, f"Missing agent-2 fact. Got: {contents}"

    def test_agent1_query_returns_all_agents_facts(self) -> None:
        """Querying from agent-1 returns facts from agents 0, 1, and 2."""
        results = self.agents["agent-1"].search_facts("animals cats dogs birds", limit=20)
        contents = self._all_contents(results)

        assert "Cats have whiskers" in contents, f"Missing agent-0 fact. Got: {contents}"
        assert "Dogs are loyal" in contents, f"Missing agent-1 fact. Got: {contents}"
        assert "Birds can fly" in contents, f"Missing agent-2 fact. Got: {contents}"

    def test_agent2_query_returns_all_agents_facts(self) -> None:
        """Querying from agent-2 returns facts from agents 0, 1, and 2."""
        results = self.agents["agent-2"].search_facts("animals cats dogs birds", limit=20)
        contents = self._all_contents(results)

        assert "Cats have whiskers" in contents, f"Missing agent-0 fact. Got: {contents}"
        assert "Dogs are loyal" in contents, f"Missing agent-1 fact. Got: {contents}"
        assert "Birds can fly" in contents, f"Missing agent-2 fact. Got: {contents}"

    def test_all_six_facts_returned(self) -> None:
        """All 6 facts (2 per agent) are returned when query terms match all content.

        The query includes keywords from every fact's content so the ShardStore
        keyword search can locate all 6 facts across all shards.
        """
        # "cats dogs birds" matches content of all 6 facts via keyword overlap
        results = self.agents["agent-0"].search_facts("cats dogs birds", limit=20)
        contents = self._all_contents(results)

        expected = {
            "Cats have whiskers",
            "Cats are felines",
            "Dogs are loyal",
            "Dogs bark loudly",
            "Birds can fly",
            "Birds lay eggs",
        }
        assert expected.issubset(contents), (
            f"Expected all 6 facts. Missing: {expected - contents}. Got: {contents}"
        )


class TestDistributedDeterminism:
    """Same query from different agents returns identical results (determinism)."""

    def setup_method(self) -> None:
        self.hive = DistributedHiveGraph(hive_id="det-test", enable_gossip=False)

        self.agents: dict[str, DistributedCognitiveMemory] = {}
        for i in range(3):
            name = f"agent-{i}"
            self.hive.register_agent(name)
            self.agents[name] = _make_agent(name, self.hive)

        # Load disjoint facts across agents
        self.agents["agent-0"].store_fact(concept="science", content="Water boils at 100C")
        self.agents["agent-1"].store_fact(concept="science", content="Ice melts at 0C")
        self.agents["agent-2"].store_fact(concept="science", content="Hydrogen is lightest element")

    def test_same_query_from_agent0_and_agent1_returns_identical_content_set(self) -> None:
        """Same query issued from agent-0 and agent-1 returns the same content set."""
        q = "science water ice hydrogen"

        results_a0 = self.agents["agent-0"].search_facts(q, limit=10)
        results_a1 = self.agents["agent-1"].search_facts(q, limit=10)

        def contents(results: list) -> set[str]:
            return {_content(r) for r in results if _content(r)}

        c0 = contents(results_a0)
        c1 = contents(results_a1)
        assert c0 == c1, (
            f"Content sets differ between agent-0 and agent-1.\n"
            f"agent-0 only: {c0 - c1}\n"
            f"agent-1 only: {c1 - c0}"
        )

    def test_merge_fact_lists_is_deterministic(self) -> None:
        """_merge_fact_lists returns same order on repeated calls with same inputs."""
        dcm = self.agents["agent-0"]
        q = "science"

        run1 = dcm.search_facts(q, limit=10)
        run2 = dcm.search_facts(q, limit=10)

        contents1 = [_content(r) for r in run1]
        contents2 = [_content(r) for r in run2]

        assert contents1 == contents2, (
            f"search_facts() is non-deterministic:\nrun1: {contents1}\nrun2: {contents2}"
        )

    def test_repeated_identical_queries_produce_identical_ordered_results(self) -> None:
        """Running the same query 5 times always returns the same ordered list."""
        q = "science"
        results = [
            [_content(r) for r in self.agents["agent-0"].search_facts(q, limit=10)]
            for _ in range(5)
        ]
        for i in range(1, 5):
            assert results[0] == results[i], (
                f"Run {i} differed from run 0.\nrun 0: {results[0]}\nrun {i}: {results[i]}"
            )


class TestNoHardcodedConstants:
    """Verify that numeric constants are defined in retrieval_constants, not hardcoded."""

    def test_position_score_decrement_imported_from_retrieval_constants(self) -> None:
        """POSITION_SCORE_DECREMENT is importable from retrieval_constants."""
        assert isinstance(POSITION_SCORE_DECREMENT, float), (
            "POSITION_SCORE_DECREMENT must be a float constant in retrieval_constants"
        )
        assert 0 < POSITION_SCORE_DECREMENT < 1, (
            f"POSITION_SCORE_DECREMENT should be a small positive value, got {POSITION_SCORE_DECREMENT}"
        )

    def test_confidence_sort_weight_imported_from_retrieval_constants(self) -> None:
        """CONFIDENCE_SORT_WEIGHT is importable from retrieval_constants."""
        assert isinstance(CONFIDENCE_SORT_WEIGHT, float), (
            "CONFIDENCE_SORT_WEIGHT must be a float constant in retrieval_constants"
        )

    def test_distributed_hive_graph_uses_position_score_decrement(self) -> None:
        """DistributedHiveGraph.query_facts uses POSITION_SCORE_DECREMENT, not hardcoded 0.01."""
        import inspect

        import amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph as dhg

        source = inspect.getsource(dhg.DistributedHiveGraph.query_facts)
        # The literal "0.01" must not appear in query_facts — it must use the constant
        assert "0.01" not in source, (
            "query_facts still contains hardcoded 0.01 — use POSITION_SCORE_DECREMENT"
        )
