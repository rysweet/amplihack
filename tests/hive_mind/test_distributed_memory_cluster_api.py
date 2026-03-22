"""TDD: cluster-wide API parity for distributed cognitive memory.

These tests lock in the intended behavior for higher-level memory operations
used by LearningAgent. In distributed mode, `retrieve_by_entity` and
`execute_aggregation` must stop behaving like local-only shortcuts and instead
include remote knowledge as part of the authoritative distributed layer.
"""

from __future__ import annotations

from typing import Any


class _SemanticFact:
    """Minimal fact object compatible with CognitiveAdapter conversions."""

    def __init__(self, content: str, concept: str = "people", confidence: float = 0.9) -> None:
        self.content = content
        self.concept = concept
        self.confidence = confidence
        self.fact_id = content.replace(" ", "-").lower()
        self.node_id = self.fact_id
        self.created_at = 0.0
        self.tags = [concept]


class _LocalMemory:
    """Minimal local memory backend for DistributedCognitiveMemory tests."""

    def search_facts(
        self,
        query: str = "",
        limit: int = 10,
        min_confidence: float = 0.0,
        **kwargs: Any,
    ) -> list[_SemanticFact]:
        return []

    def get_all_facts(self, limit: int = 50, **kwargs: Any) -> list[_SemanticFact]:
        return []

    def retrieve_by_entity(self, entity_name: str, limit: int = 50) -> list[_SemanticFact]:
        return [_SemanticFact(f"{entity_name} manages Project Atlas", concept="people")]

    def execute_aggregation(self, query_type: str, entity_filter: str = "") -> dict[str, Any]:
        if query_type == "list_entities":
            return {"items": ["Project Atlas"], "count": 1}
        return {"query_type": query_type, "count": 0, "items": []}


class _RecordingHive:
    """Fake hive with the planned distributed higher-level operations."""

    def __init__(self) -> None:
        self.retrieve_by_entity_calls: list[tuple[str, int]] = []
        self.execute_aggregation_calls: list[tuple[str, str]] = []

    def retrieve_by_entity(self, entity_name: str, limit: int = 50) -> list[_SemanticFact]:
        self.retrieve_by_entity_calls.append((entity_name, limit))
        return [_SemanticFact(f"{entity_name}'s birthday is March 15", concept="people")]

    def execute_aggregation(self, query_type: str, entity_filter: str = "") -> dict[str, Any]:
        self.execute_aggregation_calls.append((query_type, entity_filter))
        if query_type == "list_entities":
            return {"items": ["Project Atlas", "Project Beacon"], "count": 2}
        return {"query_type": query_type, "count": 0, "items": []}

    def promote_fact(self, *args: object, **kwargs: object) -> None:
        pass


def _make_adapter() -> tuple[object, _RecordingHive]:
    """Return a CognitiveAdapter backed by DistributedCognitiveMemory."""
    from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter
    from amplihack.agents.goal_seeking.hive_mind.distributed_memory import (
        DistributedCognitiveMemory,
    )

    hive = _RecordingHive()
    distributed = DistributedCognitiveMemory(
        local_memory=_LocalMemory(),
        hive_graph=hive,
        agent_name="agent-0",
    )

    adapter: CognitiveAdapter = CognitiveAdapter.__new__(CognitiveAdapter)
    adapter.agent_name = "agent-0"
    adapter.memory = distributed
    adapter._cognitive = True
    adapter._hive_store = None
    adapter._quality_threshold = 0.0
    adapter._confidence_gate = 0.0
    adapter._enable_query_expansion = False
    adapter._buffer_pool_size = 0
    adapter._db_path = None
    return adapter, hive


def test_cognitive_adapter_retrieve_by_entity_includes_remote_facts() -> None:
    """Distributed entity retrieval must merge local and remote knowledge."""
    adapter, hive = _make_adapter()

    results = adapter.retrieve_by_entity("Sarah Chen", limit=10)
    outcomes = {r["outcome"] for r in results}

    assert outcomes == {
        "Sarah Chen manages Project Atlas",
        "Sarah Chen's birthday is March 15",
    }
    assert hive.retrieve_by_entity_calls == [("Sarah Chen", 10)]


def test_cognitive_adapter_retrieve_by_entity_local_skips_hive() -> None:
    """Local-only entity retrieval must bypass distributed fan-out."""
    adapter, hive = _make_adapter()

    results = adapter.retrieve_by_entity_local("Sarah Chen", limit=10)
    outcomes = {r["outcome"] for r in results}

    assert outcomes == {"Sarah Chen manages Project Atlas"}
    assert hive.retrieve_by_entity_calls == []


def test_cognitive_adapter_execute_aggregation_includes_remote_knowledge() -> None:
    """Distributed aggregations must merge local and remote knowledge."""
    adapter, hive = _make_adapter()

    result = adapter.execute_aggregation("list_entities", entity_filter="project")

    assert result["count"] == 2
    assert result["items"] == ["Project Atlas", "Project Beacon"]
    assert hive.execute_aggregation_calls == [("list_entities", "project")]


def test_cognitive_adapter_execute_aggregation_local_skips_hive() -> None:
    """Local-only aggregations must bypass distributed fan-out."""
    adapter, hive = _make_adapter()

    result = adapter.execute_aggregation_local("list_entities", entity_filter="project")

    assert result["count"] == 1
    assert result["items"] == ["Project Atlas"]
    assert hive.execute_aggregation_calls == []


def test_shard_payload_round_trip_preserves_metadata() -> None:
    """Transport payload conversion must preserve source/timestamp/metadata."""
    from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
        _payload_facts_to_shard_facts,
        _result_to_fact_payload,
    )

    result = {
        "experience_id": "sem-1",
        "context": "Project Atlas",
        "outcome": "Project Atlas deadline moved to September 20",
        "confidence": 0.9,
        "source": "hive:agent_a",
        "timestamp": "123.0",
        "tags": ["project", "date:2024-09-20", "time:September 2024"],
        "metadata": {
            "source_label": "Atlas planning memo",
            "source_date": "2024-09-20",
            "temporal_order": "September 2024",
            "temporal_index": 20240920,
        },
    }

    payload = _result_to_fact_payload(result, "agent-default")

    assert payload is not None
    assert payload["source_agent"] == "agent_a"
    assert payload["created_at"] == "123.0"
    assert payload["metadata"]["source_label"] == "Atlas planning memo"

    shard_facts = _payload_facts_to_shard_facts([payload])

    assert len(shard_facts) == 1
    assert shard_facts[0].source_agent == "agent_a"
    assert shard_facts[0].created_at == "123.0"
    assert shard_facts[0].metadata["source_label"] == "Atlas planning memo"
