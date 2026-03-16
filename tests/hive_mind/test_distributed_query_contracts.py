"""TDD: explicit failure and deterministic ordering contracts for distributed queries."""

from __future__ import annotations

import time

import pytest

from amplihack.agents.goal_seeking.hive_mind.dht import ShardFact
from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
    DistributedHiveGraph,
    _search_for_shard_response,
)


def _fact(agent_id: str, content: str) -> ShardFact:
    return ShardFact(
        fact_id=f"{agent_id}-{content}",
        content=content,
        concept="test",
        confidence=0.9,
        source_agent=agent_id,
        tags=["test"],
    )


class _FakeTransport:
    def __init__(
        self,
        responses: dict[str, list[ShardFact]] | None = None,
        errors: dict[str, Exception] | None = None,
        delays: dict[str, float] | None = None,
    ) -> None:
        self._responses = responses or {}
        self._errors = errors or {}
        self._delays = delays or {}

    def bind_local(self, graph: object) -> None:
        self._graph = graph

    def bind_agent(self, agent: object) -> None:
        self._agent = agent

    def query_shard(self, agent_id: str, query: str, limit: int) -> list[ShardFact]:
        delay = self._delays.get(agent_id, 0.0)
        if delay:
            time.sleep(delay)
        if agent_id in self._errors:
            raise self._errors[agent_id]
        return list(self._responses.get(agent_id, []))

    def store_on_shard(self, agent_id: str, fact: ShardFact) -> None:
        return None


def _make_graph(transport: _FakeTransport) -> DistributedHiveGraph:
    graph = DistributedHiveGraph(
        hive_id="query-contracts", enable_gossip=False, transport=transport
    )
    for agent_id in ("agent-0", "agent-1", "agent-2"):
        graph.register_agent(agent_id)
    return graph


def test_query_facts_raises_when_any_shard_fails() -> None:
    """Distributed reads must surface shard failures instead of returning partial data."""
    graph = _make_graph(
        _FakeTransport(
            responses={
                "agent-0": [_fact("agent-0", "agent-0 fact")],
                "agent-2": [_fact("agent-2", "agent-2 fact")],
            },
            errors={"agent-1": TimeoutError("agent-1 timed out")},
        )
    )

    with pytest.raises(RuntimeError, match="agent-1"):
        graph.query_facts("shared query", limit=10)


def test_query_facts_uses_stable_tiebreaker_under_out_of_order_responses() -> None:
    """Equal-score shard results must not depend on response completion order."""
    graph = _make_graph(
        _FakeTransport(
            responses={
                "agent-0": [_fact("agent-0", "agent-0 fact")],
                "agent-1": [_fact("agent-1", "agent-1 fact")],
                "agent-2": [_fact("agent-2", "agent-2 fact")],
            },
            delays={
                "agent-0": 0.06,
                "agent-1": 0.03,
                "agent-2": 0.00,
            },
        )
    )

    results = graph.query_facts("shared query", limit=10)

    assert [fact.content for fact in results] == [
        "agent-0 fact",
        "agent-1 fact",
        "agent-2 fact",
    ]


def test_search_for_shard_response_does_not_hide_local_search_failures() -> None:
    """Shard handlers must not silently raw-fallback when local cognitive search fails."""

    class _ExplodingMemory:
        def search_local(self, query: str, limit: int = 10) -> list[dict]:
            raise RuntimeError("search_local exploded")

    class _ExplodingAgent:
        memory = _ExplodingMemory()

    graph = DistributedHiveGraph(hive_id="search-failure", enable_gossip=False)
    graph.register_agent("agent-0")

    with pytest.raises(RuntimeError, match="search_local exploded"):
        _search_for_shard_response(
            query="anything",
            limit=5,
            agent=_ExplodingAgent(),
            local_graph=graph,
            agent_id="agent-0",
        )
