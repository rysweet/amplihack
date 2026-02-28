"""Tests for the event-sourced hive mind module.

Testing pyramid:
- 60% Unit tests (HiveEvent, HiveEventBus, EventLog individually)
- 30% Integration tests (EventSourcedMemory + bus, HiveOrchestrator)
- 10% E2E tests (multi-agent scenario with 3 agents)
"""

from __future__ import annotations

import json

# Import module under test
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from amplihack.agents.goal_seeking.hive_mind.event_sourced import (
    ALL_EVENT_TYPES,
    ANSWER_GIVEN,
    CONFIDENCE_UPDATED,
    FACT_LEARNED,
    QUESTION_ASKED,
    EventLog,
    EventSourcedMemory,
    HiveEvent,
    HiveEventBus,
    HiveOrchestrator,
)

# ---------------------------------------------------------------------------
# Fake memory adapter for tests (no real DB dependency)
# ---------------------------------------------------------------------------


class FakeMemory:
    """Minimal in-memory adapter implementing store_fact/search/get_all_facts."""

    def __init__(self) -> None:
        self._facts: list[dict[str, Any]] = []
        self._id_counter = 0

    def store_fact(
        self,
        context: str,
        fact: str,
        confidence: float = 0.9,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> str:
        self._id_counter += 1
        fact_id = f"fake_{self._id_counter}"
        self._facts.append(
            {
                "id": fact_id,
                "context": context,
                "outcome": fact,
                "confidence": confidence,
                "tags": tags or [],
            }
        )
        return fact_id

    def search(self, query: str, limit: int = 10, **kwargs: Any) -> list[dict[str, Any]]:
        query_lower = query.lower()
        results = []
        for f in self._facts:
            if query_lower in f["context"].lower() or query_lower in f["outcome"].lower():
                results.append(f)
        return results[:limit]

    def get_all_facts(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(self._facts[:limit])


# ===========================================================================
# UNIT TESTS (60%)
# ===========================================================================


class TestHiveEvent:
    """Test HiveEvent creation, immutability, and serialization."""

    def test_create_event_with_defaults(self) -> None:
        evt = HiveEvent(event_type=FACT_LEARNED, source_agent_id="agent_a")
        assert evt.event_type == FACT_LEARNED
        assert evt.source_agent_id == "agent_a"
        assert evt.sequence_number == 0
        assert isinstance(evt.event_id, str)
        assert len(evt.event_id) == 36  # UUID4 format
        assert isinstance(evt.timestamp, datetime)

    def test_create_event_with_payload(self) -> None:
        payload = {"context": "Biology", "fact": "Cells divide", "confidence": 0.9, "tags": ["bio"]}
        evt = HiveEvent(
            event_type=FACT_LEARNED,
            source_agent_id="agent_b",
            payload=payload,
            sequence_number=42,
        )
        assert evt.payload["fact"] == "Cells divide"
        assert evt.sequence_number == 42

    def test_event_is_frozen(self) -> None:
        evt = HiveEvent(event_type=FACT_LEARNED, source_agent_id="a")
        with pytest.raises(AttributeError):
            evt.event_type = "CHANGED"  # type: ignore[misc]

    def test_to_dict_serialization(self) -> None:
        evt = HiveEvent(
            event_type=QUESTION_ASKED,
            source_agent_id="agent_c",
            payload={"question": "What is DNA?", "level": "L1"},
            sequence_number=7,
        )
        d = evt.to_dict()
        assert d["event_type"] == QUESTION_ASKED
        assert d["source_agent_id"] == "agent_c"
        assert d["sequence_number"] == 7
        assert isinstance(d["timestamp"], str)
        # Must be JSON-serializable
        json_str = json.dumps(d)
        assert "QUESTION_ASKED" in json_str

    def test_from_dict_deserialization(self) -> None:
        evt = HiveEvent(
            event_type=ANSWER_GIVEN,
            source_agent_id="agent_d",
            payload={"answer": "42"},
            sequence_number=3,
        )
        d = evt.to_dict()
        restored = HiveEvent.from_dict(d)
        assert restored.event_type == evt.event_type
        assert restored.source_agent_id == evt.source_agent_id
        assert restored.payload == evt.payload
        assert restored.sequence_number == 3

    def test_roundtrip_serialization(self) -> None:
        original = HiveEvent(
            event_type=CONFIDENCE_UPDATED,
            source_agent_id="x",
            payload={"fact_id": "f1", "old": 0.5, "new": 0.8},
            sequence_number=99,
        )
        restored = HiveEvent.from_dict(original.to_dict())
        assert restored.event_type == original.event_type
        assert restored.payload == original.payload
        assert restored.sequence_number == original.sequence_number

    def test_all_event_types_defined(self) -> None:
        assert FACT_LEARNED in ALL_EVENT_TYPES
        assert QUESTION_ASKED in ALL_EVENT_TYPES
        assert ANSWER_GIVEN in ALL_EVENT_TYPES
        assert CONFIDENCE_UPDATED in ALL_EVENT_TYPES
        assert len(ALL_EVENT_TYPES) == 4


class TestHiveEventBus:
    """Test the pub/sub event bus."""

    def test_subscribe_and_poll(self) -> None:
        bus = HiveEventBus()
        bus.subscribe("listener")
        evt = HiveEvent(
            event_type=FACT_LEARNED, source_agent_id="producer", payload={"fact": "test"}
        )
        delivered = bus.publish(evt)
        assert delivered == 1
        events = bus.poll("listener")
        assert len(events) == 1
        assert events[0].payload["fact"] == "test"

    def test_no_self_delivery(self) -> None:
        bus = HiveEventBus()
        bus.subscribe("agent_a")
        evt = HiveEvent(event_type=FACT_LEARNED, source_agent_id="agent_a")
        delivered = bus.publish(evt)
        assert delivered == 0
        events = bus.poll("agent_a")
        assert len(events) == 0

    def test_type_filtering(self) -> None:
        bus = HiveEventBus()
        bus.subscribe("listener", event_types=[FACT_LEARNED])
        # Publish a FACT_LEARNED -- should be delivered
        evt1 = HiveEvent(event_type=FACT_LEARNED, source_agent_id="other")
        bus.publish(evt1)
        # Publish a QUESTION_ASKED -- should be filtered out
        evt2 = HiveEvent(event_type=QUESTION_ASKED, source_agent_id="other")
        bus.publish(evt2)
        events = bus.poll("listener")
        assert len(events) == 1
        assert events[0].event_type == FACT_LEARNED

    def test_multiple_subscribers(self) -> None:
        bus = HiveEventBus()
        bus.subscribe("a")
        bus.subscribe("b")
        bus.subscribe("c")
        evt = HiveEvent(event_type=FACT_LEARNED, source_agent_id="producer")
        delivered = bus.publish(evt)
        assert delivered == 3
        assert len(bus.poll("a")) == 1
        assert len(bus.poll("b")) == 1
        assert len(bus.poll("c")) == 1

    def test_unsubscribe(self) -> None:
        bus = HiveEventBus()
        bus.subscribe("agent_x")
        bus.unsubscribe("agent_x")
        evt = HiveEvent(event_type=FACT_LEARNED, source_agent_id="other")
        delivered = bus.publish(evt)
        assert delivered == 0

    def test_poll_empty(self) -> None:
        bus = HiveEventBus()
        assert bus.poll("nonexistent") == []
        bus.subscribe("agent")
        assert bus.poll("agent") == []

    def test_poll_drains_queue(self) -> None:
        bus = HiveEventBus()
        bus.subscribe("listener")
        for i in range(5):
            bus.publish(HiveEvent(event_type=FACT_LEARNED, source_agent_id=f"p{i}"))
        events = bus.poll("listener")
        assert len(events) == 5
        # Second poll should be empty
        assert bus.poll("listener") == []

    def test_subscriber_count(self) -> None:
        bus = HiveEventBus()
        assert bus.subscriber_count == 0
        bus.subscribe("a")
        bus.subscribe("b")
        assert bus.subscriber_count == 2
        bus.unsubscribe("a")
        assert bus.subscriber_count == 1

    def test_global_listener(self) -> None:
        bus = HiveEventBus()
        captured: list[HiveEvent] = []
        bus.add_listener(lambda e: captured.append(e))
        evt = HiveEvent(event_type=FACT_LEARNED, source_agent_id="any")
        bus.publish(evt)
        assert len(captured) == 1
        assert captured[0] is evt

    def test_thread_safety(self) -> None:
        bus = HiveEventBus()
        bus.subscribe("listener")
        errors: list[str] = []

        def publisher(agent_id: str, count: int) -> None:
            try:
                for i in range(count):
                    bus.publish(
                        HiveEvent(
                            event_type=FACT_LEARNED,
                            source_agent_id=agent_id,
                            payload={"i": i},
                        )
                    )
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=publisher, args=(f"p{j}", 100)) for j in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        events = bus.poll("listener")
        assert len(events) == 500


class TestEventLog:
    """Test append-only event log."""

    def test_append_and_replay(self) -> None:
        log = EventLog()
        evt = HiveEvent(
            event_type=FACT_LEARNED,
            source_agent_id="a",
            payload={"fact": "water"},
            sequence_number=1,
        )
        log.append(evt)
        replayed = log.replay()
        assert len(replayed) == 1
        assert replayed[0].payload["fact"] == "water"

    def test_replay_with_since(self) -> None:
        log = EventLog()
        for i in range(5):
            log.append(
                HiveEvent(
                    event_type=FACT_LEARNED,
                    source_agent_id="a",
                    sequence_number=i + 1,
                )
            )
        result = log.replay(since=3)
        assert len(result) == 2
        assert result[0].sequence_number == 4
        assert result[1].sequence_number == 5

    def test_replay_since_zero_returns_all(self) -> None:
        log = EventLog()
        for i in range(3):
            log.append(HiveEvent(event_type=FACT_LEARNED, source_agent_id="a", sequence_number=i))
        assert len(log.replay(since=0)) == 3

    def test_query_by_event_type(self) -> None:
        log = EventLog()
        log.append(HiveEvent(event_type=FACT_LEARNED, source_agent_id="a"))
        log.append(HiveEvent(event_type=QUESTION_ASKED, source_agent_id="a"))
        log.append(HiveEvent(event_type=FACT_LEARNED, source_agent_id="b"))
        results = log.query_events(event_type=FACT_LEARNED)
        assert len(results) == 2

    def test_query_by_agent_id(self) -> None:
        log = EventLog()
        log.append(HiveEvent(event_type=FACT_LEARNED, source_agent_id="a"))
        log.append(HiveEvent(event_type=FACT_LEARNED, source_agent_id="b"))
        log.append(HiveEvent(event_type=FACT_LEARNED, source_agent_id="a"))
        results = log.query_events(agent_id="a")
        assert len(results) == 2

    def test_query_combined_filters(self) -> None:
        log = EventLog()
        log.append(HiveEvent(event_type=FACT_LEARNED, source_agent_id="a", sequence_number=1))
        log.append(HiveEvent(event_type=QUESTION_ASKED, source_agent_id="a", sequence_number=2))
        log.append(HiveEvent(event_type=FACT_LEARNED, source_agent_id="b", sequence_number=3))
        results = log.query_events(event_type=FACT_LEARNED, agent_id="a")
        assert len(results) == 1

    def test_size_property(self) -> None:
        log = EventLog()
        assert log.size == 0
        log.append(HiveEvent(event_type=FACT_LEARNED, source_agent_id="x"))
        assert log.size == 1

    def test_file_persistence(self, tmp_path: Path) -> None:
        log_file = tmp_path / "events.jsonl"

        # Write events
        log1 = EventLog(persist_path=log_file)
        log1.append(
            HiveEvent(
                event_type=FACT_LEARNED,
                source_agent_id="a",
                payload={"fact": "persistent"},
                sequence_number=1,
            )
        )
        log1.append(
            HiveEvent(
                event_type=QUESTION_ASKED,
                source_agent_id="b",
                payload={"question": "why?"},
                sequence_number=2,
            )
        )
        assert log_file.exists()

        # Read back in a new EventLog instance
        log2 = EventLog(persist_path=log_file)
        events = log2.replay()
        assert len(events) == 2
        assert events[0].payload["fact"] == "persistent"
        assert events[1].payload["question"] == "why?"

    def test_file_persistence_append(self, tmp_path: Path) -> None:
        log_file = tmp_path / "events.jsonl"
        log1 = EventLog(persist_path=log_file)
        log1.append(HiveEvent(event_type=FACT_LEARNED, source_agent_id="a", sequence_number=1))

        # Open again and append more
        log2 = EventLog(persist_path=log_file)
        log2.append(HiveEvent(event_type=FACT_LEARNED, source_agent_id="b", sequence_number=2))

        # log2 should have both (1 loaded + 1 new)
        assert log2.size == 2

        # Verify on disk: file has 2 lines (1 from log1, 1 from log2)
        log3 = EventLog(persist_path=log_file)
        assert log3.size == 2


# ===========================================================================
# INTEGRATION TESTS (30%)
# ===========================================================================


class TestEventSourcedMemory:
    """Test EventSourcedMemory wrapper with fake local memory."""

    def test_store_fact_publishes_event(self) -> None:
        bus = HiveEventBus()
        mem_a = FakeMemory()
        esm_a = EventSourcedMemory("agent_a", mem_a, bus)
        bus.subscribe("agent_b")

        esm_a.store_fact("Biology", "Cells divide", 0.9, ["bio"])

        # Check local storage
        assert len(mem_a.get_all_facts()) == 1

        # Check event was published to bus
        events = bus.poll("agent_b")
        assert len(events) == 1
        assert events[0].event_type == FACT_LEARNED
        assert events[0].source_agent_id == "agent_a"
        assert events[0].payload["fact"] == "Cells divide"

    def test_search_delegates_to_local(self) -> None:
        bus = HiveEventBus()
        mem = FakeMemory()
        esm = EventSourcedMemory("agent_a", mem, bus)
        esm.store_fact("Physics", "Light is fast", 0.95)

        results = esm.search("light")
        assert len(results) == 1

    def test_get_all_facts_delegates(self) -> None:
        bus = HiveEventBus()
        mem = FakeMemory()
        esm = EventSourcedMemory("agent_a", mem, bus)
        esm.store_fact("Math", "Pi is 3.14", 0.99)
        esm.store_fact("Math", "E is 2.71", 0.99)
        assert len(esm.get_all_facts()) == 2

    def test_incorporate_peer_fact(self) -> None:
        bus = HiveEventBus()
        mem_a = FakeMemory()
        mem_b = FakeMemory()
        esm_a = EventSourcedMemory("agent_a", mem_a, bus)
        esm_b = EventSourcedMemory("agent_b", mem_b, bus, relevance_threshold=0.0)

        bus.subscribe("agent_b")

        # Agent A stores a fact
        esm_a.store_fact("Biology", "DNA stores genetic information", 0.95, ["bio"])

        # Agent B processes the event
        incorporated = esm_b.process_pending_events()
        assert incorporated == 1
        assert len(mem_b.get_all_facts()) == 1

        # Incorporated fact should have provenance tag
        stored = mem_b.get_all_facts()[0]
        assert "hive:from:agent_a" in stored["tags"]

    def test_incorporate_applies_confidence_discount(self) -> None:
        bus = HiveEventBus()
        mem_a = FakeMemory()
        mem_b = FakeMemory()
        esm_a = EventSourcedMemory("agent_a", mem_a, bus)
        esm_b = EventSourcedMemory("agent_b", mem_b, bus, relevance_threshold=0.0)
        bus.subscribe("agent_b")

        esm_a.store_fact("Test", "Fact with high confidence", 1.0)
        esm_b.process_pending_events()

        stored = mem_b.get_all_facts()[0]
        # Peer knowledge gets 0.9x discount
        assert stored["confidence"] == pytest.approx(0.9, abs=0.01)

    def test_relevance_filtering(self) -> None:
        bus = HiveEventBus()
        mem_a = FakeMemory()
        mem_b = FakeMemory()
        esm_a = EventSourcedMemory("agent_a", mem_a, bus)
        # Agent B with very high relevance threshold
        esm_b = EventSourcedMemory("agent_b", mem_b, bus, relevance_threshold=0.99)
        bus.subscribe("agent_b")

        # First, give agent B some domain context
        esm_b.store_fact("Security", "Encryption protects data", 0.9, ["security"])

        # Agent A publishes a completely unrelated fact
        esm_a.store_fact("Cooking", "Salt improves flavor", 0.85, ["food"])

        # Agent B should not incorporate the cooking fact (low relevance)
        esm_b.process_pending_events()
        # Only 1 fact in mem_b (its own)
        assert len(mem_b.get_all_facts()) == 1

    def test_no_duplicate_incorporation(self) -> None:
        bus = HiveEventBus()
        mem = FakeMemory()
        esm = EventSourcedMemory("agent_b", mem, bus, relevance_threshold=0.0)
        bus.subscribe("agent_b")

        evt = HiveEvent(
            event_type=FACT_LEARNED,
            source_agent_id="agent_a",
            payload={"context": "Test", "fact": "Dup check", "confidence": 0.9, "tags": []},
            sequence_number=1,
        )

        # Incorporate twice
        assert esm.incorporate_peer_event(evt) is True
        assert esm.incorporate_peer_event(evt) is False  # Already seen
        assert len(mem.get_all_facts()) == 1

    def test_non_fact_events_not_incorporated(self) -> None:
        bus = HiveEventBus()
        mem = FakeMemory()
        esm = EventSourcedMemory("agent_b", mem, bus, relevance_threshold=0.0)

        question_evt = HiveEvent(
            event_type=QUESTION_ASKED,
            source_agent_id="agent_a",
            payload={"question": "What?"},
        )
        assert esm.incorporate_peer_event(question_evt) is False
        assert len(mem.get_all_facts()) == 0

    def test_sequence_numbers_increment(self) -> None:
        bus = HiveEventBus()
        captured: list[HiveEvent] = []
        bus.add_listener(lambda e: captured.append(e))

        mem = FakeMemory()
        esm = EventSourcedMemory("agent_a", mem, bus)

        esm.store_fact("A", "fact 1", 0.9)
        esm.store_fact("B", "fact 2", 0.8)
        esm.store_fact("C", "fact 3", 0.7)

        assert captured[0].sequence_number == 1
        assert captured[1].sequence_number == 2
        assert captured[2].sequence_number == 3


class TestHiveOrchestrator:
    """Test the top-level hive coordinator."""

    def test_register_agent(self) -> None:
        orch = HiveOrchestrator()
        mem = FakeMemory()
        esm = orch.register_agent("agent_a", mem)
        assert isinstance(esm, EventSourcedMemory)
        assert orch.get_hive_stats()["agent_count"] == 1

    def test_register_duplicate_raises(self) -> None:
        orch = HiveOrchestrator()
        orch.register_agent("agent_a", FakeMemory())
        with pytest.raises(ValueError, match="already registered"):
            orch.register_agent("agent_a", FakeMemory())

    def test_unregister_agent(self) -> None:
        orch = HiveOrchestrator()
        orch.register_agent("agent_a", FakeMemory())
        orch.unregister_agent("agent_a")
        assert orch.get_hive_stats()["agent_count"] == 0

    def test_events_logged_automatically(self) -> None:
        orch = HiveOrchestrator()
        esm = orch.register_agent("agent_a", FakeMemory())
        esm.store_fact("Topic", "A fact", 0.9)

        stats = orch.get_hive_stats()
        assert stats["total_events"] == 1
        assert stats["events_by_type"][FACT_LEARNED] == 1
        assert stats["events_by_agent"]["agent_a"] == 1

    def test_propagate_all(self) -> None:
        orch = HiveOrchestrator()
        esm_a = orch.register_agent("agent_a", FakeMemory(), relevance_threshold=0.0)
        orch.register_agent("agent_b", FakeMemory(), relevance_threshold=0.0)

        # Agent A stores a fact
        esm_a.store_fact("Science", "Gravity pulls things down", 0.95)

        # Propagate to all
        results = orch.propagate_all()
        assert results["agent_b"] >= 1

    def test_replay_for_new_agent(self) -> None:
        orch = HiveOrchestrator()
        esm_a = orch.register_agent("agent_a", FakeMemory())

        # Agent A stores facts BEFORE agent_b joins
        esm_a.store_fact("History", "Rome was founded in 753 BC", 0.9)
        esm_a.store_fact("History", "The Roman Empire fell in 476 AD", 0.85)

        # Agent B joins late -- replay should catch it up
        mem_b = FakeMemory()
        orch.register_agent("agent_b", mem_b, relevance_threshold=0.0)

        # Agent B should have received the replayed events
        assert len(mem_b.get_all_facts()) == 2

    def test_get_agent_memory(self) -> None:
        orch = HiveOrchestrator()
        esm = orch.register_agent("a", FakeMemory())
        assert orch.get_agent_memory("a") is esm
        assert orch.get_agent_memory("nonexistent") is None

    def test_hive_stats_comprehensive(self) -> None:
        orch = HiveOrchestrator()
        esm_a = orch.register_agent("agent_a", FakeMemory(), relevance_threshold=0.0)
        esm_b = orch.register_agent("agent_b", FakeMemory(), relevance_threshold=0.0)

        esm_a.store_fact("X", "Fact from A", 0.9)
        esm_b.store_fact("Y", "Fact from B", 0.8)

        orch.propagate_all()

        stats = orch.get_hive_stats()
        assert stats["agent_count"] == 2
        assert set(stats["agent_ids"]) == {"agent_a", "agent_b"}
        assert stats["total_events"] == 2
        assert stats["events_by_type"][FACT_LEARNED] == 2
        assert stats["events_by_agent"]["agent_a"] == 1
        assert stats["events_by_agent"]["agent_b"] == 1
        # Each should have incorporated one peer event
        inc = stats["incorporation_stats"]
        assert inc["agent_a"] >= 1
        assert inc["agent_b"] >= 1


# ===========================================================================
# E2E TESTS (10%)
# ===========================================================================


class TestMultiAgentScenario:
    """End-to-end test with 3 agents learning different domains."""

    def test_three_agent_cross_domain_knowledge_sharing(self) -> None:
        """Three agents learn domain-specific facts, then share via events."""
        orch = HiveOrchestrator()

        # Register 3 domain-specific agents with low threshold (accept everything)
        mem_infra = FakeMemory()
        mem_sec = FakeMemory()
        mem_perf = FakeMemory()

        esm_infra = orch.register_agent("infra_agent", mem_infra, relevance_threshold=0.0)
        esm_sec = orch.register_agent("security_agent", mem_sec, relevance_threshold=0.0)
        esm_perf = orch.register_agent("perf_agent", mem_perf, relevance_threshold=0.0)

        # Each agent learns domain-specific facts
        infra_facts = [
            ("Infrastructure", "Server runs on port 8080"),
            ("Infrastructure", "Database has 3 replicas"),
            ("Infrastructure", "Load balancer uses round-robin"),
        ]
        for ctx, fact in infra_facts:
            esm_infra.store_fact(ctx, fact, 0.9, ["infra"])

        sec_facts = [
            ("Security", "TLS 1.3 is required for all connections"),
            ("Security", "API keys are rotated every 90 days"),
        ]
        for ctx, fact in sec_facts:
            esm_sec.store_fact(ctx, fact, 0.9, ["security"])

        perf_facts = [
            ("Performance", "P99 latency must be under 100ms"),
            ("Performance", "Cache hit rate is 95%"),
        ]
        for ctx, fact in perf_facts:
            esm_perf.store_fact(ctx, fact, 0.9, ["performance"])

        # Propagate events across all agents
        orch.propagate_all()

        # Verify cross-pollination
        # Infra agent should know about security + performance
        infra_facts_all = mem_infra.get_all_facts()
        assert len(infra_facts_all) >= 6  # 3 own + 2 sec + 2 perf - 1 = at least 6

        # Security agent should know about infra + performance
        sec_facts_all = mem_sec.get_all_facts()
        assert len(sec_facts_all) >= 6

        # Performance agent should know about infra + security
        perf_facts_all = mem_perf.get_all_facts()
        assert len(perf_facts_all) >= 6

        # Verify provenance tags exist
        peer_facts_in_infra = [
            f for f in infra_facts_all if any("hive:from:" in t for t in f["tags"])
        ]
        assert len(peer_facts_in_infra) >= 3

        # Verify stats
        stats = orch.get_hive_stats()
        assert stats["agent_count"] == 3
        assert stats["total_events"] == 7  # 3 + 2 + 2

    def test_late_joiner_catches_up(self) -> None:
        """A fourth agent joins after events are already flowing."""
        orch = HiveOrchestrator()
        esm_a = orch.register_agent("early_a", FakeMemory(), relevance_threshold=0.0)
        esm_b = orch.register_agent("early_b", FakeMemory(), relevance_threshold=0.0)

        # Early agents share knowledge
        esm_a.store_fact("Topic", "Fact 1 from A", 0.9)
        esm_a.store_fact("Topic", "Fact 2 from A", 0.85)
        esm_b.store_fact("Topic", "Fact 1 from B", 0.9)
        orch.propagate_all()

        # Late joiner registers
        mem_late = FakeMemory()
        orch.register_agent("late_agent", mem_late, relevance_threshold=0.0)

        # Late joiner should have all historical facts via replay
        late_facts = mem_late.get_all_facts()
        assert len(late_facts) == 3  # All 3 facts from A and B

    def test_event_log_persistence_across_orchestrators(self, tmp_path: Path) -> None:
        """Events persist to disk and are available to a new orchestrator."""
        log_file = tmp_path / "hive_events.jsonl"
        event_log = EventLog(persist_path=log_file)

        # First orchestrator session
        orch1 = HiveOrchestrator(event_log=event_log)
        esm = orch1.register_agent("agent_a", FakeMemory())
        esm.store_fact("Persistent", "This fact survives restarts", 0.95)

        # New orchestrator session loading same log
        event_log2 = EventLog(persist_path=log_file)
        orch2 = HiveOrchestrator(event_log=event_log2)
        mem_new = FakeMemory()
        orch2.register_agent("new_agent", mem_new, relevance_threshold=0.0)

        # New agent should get the persisted fact via replay
        assert len(mem_new.get_all_facts()) == 1
        assert mem_new.get_all_facts()[0]["outcome"] == "This fact survives restarts"

    def test_concurrent_agents_thread_safety(self) -> None:
        """Multiple agents storing facts concurrently should not corrupt state."""
        orch = HiveOrchestrator()
        agent_count = 5
        facts_per_agent = 20
        esms: list[EventSourcedMemory] = []

        for i in range(agent_count):
            esm = orch.register_agent(f"agent_{i}", FakeMemory(), relevance_threshold=0.0)
            esms.append(esm)

        errors: list[str] = []

        def agent_work(esm: EventSourcedMemory, agent_idx: int) -> None:
            try:
                for j in range(facts_per_agent):
                    esm.store_fact(
                        f"Domain_{agent_idx}",
                        f"Fact {j} from agent {agent_idx}",
                        0.9,
                        [f"agent_{agent_idx}"],
                    )
            except Exception as e:
                errors.append(f"agent_{agent_idx}: {e}")

        threads = [
            threading.Thread(target=agent_work, args=(esms[i], i)) for i in range(agent_count)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

        stats = orch.get_hive_stats()
        assert stats["total_events"] == agent_count * facts_per_agent

        # Propagate and check
        orch.propagate_all()
        for i in range(agent_count):
            esm = esms[i]
            local = esm.local_memory.get_all_facts()
            # Should have own facts + some peer facts
            assert len(local) >= facts_per_agent
