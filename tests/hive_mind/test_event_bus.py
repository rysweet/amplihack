"""Tests for the transport-agnostic event bus module.

Testing pyramid:
- 70% Unit tests (BusEvent serialization, LocalEventBus behavior)
- 20% Integration tests (multi-subscriber scenarios, thread safety)
- 10% Factory tests (create_event_bus validation)

Azure and Redis backends are not tested here because they require
live infrastructure. LocalEventBus is the primary test target.
"""

from __future__ import annotations

import json
import threading
import time

import pytest

from amplihack.agents.goal_seeking.hive_mind.event_bus import (
    BusEvent,
    EventBus,
    LocalEventBus,
    _make_event,
    create_event_bus,
)

# ---------------------------------------------------------------------------
# BusEvent serialization tests
# ---------------------------------------------------------------------------


class TestBusEventSerialization:
    """Unit tests for BusEvent JSON round-trip."""

    def test_to_json_returns_valid_json(self) -> None:
        evt = _make_event("FACT_LEARNED", "agent_a", {"fact": "water is wet"})
        data = evt.to_json()
        parsed = json.loads(data)
        assert parsed["event_type"] == "FACT_LEARNED"
        assert parsed["source_agent"] == "agent_a"
        assert parsed["payload"]["fact"] == "water is wet"

    def test_from_json_round_trip(self) -> None:
        original = _make_event("CONTRADICTION_DETECTED", "agent_b", {"old": "A", "new": "B"})
        restored = BusEvent.from_json(original.to_json())
        assert restored == original

    def test_from_json_missing_payload_defaults_to_empty_dict(self) -> None:
        raw = json.dumps(
            {
                "event_id": "abc123",
                "event_type": "TEST",
                "source_agent": "x",
                "timestamp": 1234567890.0,
            }
        )
        evt = BusEvent.from_json(raw)
        assert evt.payload == {}

    def test_from_json_invalid_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            BusEvent.from_json("not json at all")

    def test_from_json_missing_required_field_raises(self) -> None:
        raw = json.dumps({"event_id": "abc"})
        with pytest.raises(KeyError):
            BusEvent.from_json(raw)

    def test_event_is_frozen(self) -> None:
        evt = _make_event("TEST", "agent_a")
        with pytest.raises(AttributeError):
            evt.event_type = "CHANGED"  # type: ignore[misc]

    def test_make_event_generates_unique_ids(self) -> None:
        ids = {_make_event("TEST", "a").event_id for _ in range(100)}
        assert len(ids) == 100

    def test_make_event_timestamp_is_recent(self) -> None:
        before = time.time()
        evt = _make_event("TEST", "a")
        after = time.time()
        assert before <= evt.timestamp <= after


# ---------------------------------------------------------------------------
# LocalEventBus core behavior tests
# ---------------------------------------------------------------------------


class TestLocalEventBusBasics:
    """Unit tests for publish/subscribe/poll lifecycle."""

    def test_subscribe_and_poll_empty(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a")
        assert bus.poll("agent_a") == []

    def test_poll_unsubscribed_agent_returns_empty(self) -> None:
        bus = LocalEventBus()
        assert bus.poll("nobody") == []

    def test_publish_delivers_to_subscriber(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a")
        bus.subscribe("agent_b")
        evt = _make_event("FACT_LEARNED", "agent_a", {"fact": "test"})
        bus.publish(evt)
        received = bus.poll("agent_b")
        assert len(received) == 1
        assert received[0] == evt

    def test_no_self_delivery(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a")
        evt = _make_event("FACT_LEARNED", "agent_a")
        bus.publish(evt)
        assert bus.poll("agent_a") == []

    def test_poll_drains_mailbox(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a")
        bus.subscribe("agent_b")
        bus.publish(_make_event("TEST", "agent_a"))
        bus.publish(_make_event("TEST", "agent_a"))
        first_poll = bus.poll("agent_b")
        assert len(first_poll) == 2
        second_poll = bus.poll("agent_b")
        assert second_poll == []

    def test_multiple_subscribers_receive_same_event(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a")
        bus.subscribe("agent_b")
        bus.subscribe("agent_c")
        evt = _make_event("FACT_LEARNED", "agent_a")
        bus.publish(evt)
        assert len(bus.poll("agent_b")) == 1
        assert len(bus.poll("agent_c")) == 1
        assert bus.poll("agent_a") == []  # sender excluded


class TestLocalEventBusFiltering:
    """Unit tests for event type filtering."""

    def test_event_type_filter_includes_matching(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a", event_types=["FACT_LEARNED"])
        bus.publish(_make_event("FACT_LEARNED", "agent_b"))
        assert len(bus.poll("agent_a")) == 1

    def test_event_type_filter_excludes_non_matching(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a", event_types=["FACT_LEARNED"])
        bus.publish(_make_event("CONTRADICTION_DETECTED", "agent_b"))
        assert bus.poll("agent_a") == []

    def test_no_filter_receives_all_types(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a")
        bus.publish(_make_event("FACT_LEARNED", "agent_b"))
        bus.publish(_make_event("CONTRADICTION_DETECTED", "agent_b"))
        bus.publish(_make_event("QUESTION_ASKED", "agent_b"))
        assert len(bus.poll("agent_a")) == 3

    def test_multiple_type_filter(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a", event_types=["FACT_LEARNED", "FACT_PROMOTED"])
        bus.publish(_make_event("FACT_LEARNED", "agent_b"))
        bus.publish(_make_event("FACT_PROMOTED", "agent_b"))
        bus.publish(_make_event("CONTRADICTION_DETECTED", "agent_b"))
        events = bus.poll("agent_a")
        assert len(events) == 2
        types = {e.event_type for e in events}
        assert types == {"FACT_LEARNED", "FACT_PROMOTED"}

    def test_resubscribe_updates_filter(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a", event_types=["FACT_LEARNED"])
        bus.publish(_make_event("CONTRADICTION_DETECTED", "agent_b"))
        assert bus.poll("agent_a") == []

        # Re-subscribe with broader filter
        bus.subscribe("agent_a", event_types=["FACT_LEARNED", "CONTRADICTION_DETECTED"])
        bus.publish(_make_event("CONTRADICTION_DETECTED", "agent_b"))
        assert len(bus.poll("agent_a")) == 1


class TestLocalEventBusClose:
    """Tests for close behavior."""

    def test_close_clears_mailboxes(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("agent_a")
        bus.publish(_make_event("TEST", "agent_b"))
        bus.close()
        assert bus.poll("agent_a") == []

    def test_publish_after_close_raises(self) -> None:
        bus = LocalEventBus()
        bus.close()
        with pytest.raises(RuntimeError, match="closed"):
            bus.publish(_make_event("TEST", "agent_a"))


# ---------------------------------------------------------------------------
# Thread safety tests
# ---------------------------------------------------------------------------


class TestLocalEventBusThreadSafety:
    """Integration tests for concurrent access."""

    def test_concurrent_publishers(self) -> None:
        """10 threads each publish 50 events -- subscriber receives all non-self events."""
        bus = LocalEventBus()
        num_threads = 10
        events_per_thread = 50
        subscriber_id = "subscriber"
        bus.subscribe(subscriber_id)

        barrier = threading.Barrier(num_threads)
        errors: list[Exception] = []

        def publisher(agent_id: str) -> None:
            try:
                barrier.wait(timeout=5.0)
                for i in range(events_per_thread):
                    bus.publish(_make_event("TEST", agent_id, {"seq": i}))
            except Exception as e:
                errors.append(e)

        threads = []
        for t_idx in range(num_threads):
            t = threading.Thread(target=publisher, args=(f"pub_{t_idx}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10.0)

        assert not errors, f"Publisher threads raised errors: {errors}"

        events = bus.poll(subscriber_id)
        expected = num_threads * events_per_thread
        assert len(events) == expected, f"Expected {expected} events, got {len(events)}"

    def test_concurrent_publish_and_poll(self) -> None:
        """Publish and poll simultaneously without deadlocks or data loss."""
        bus = LocalEventBus()
        bus.subscribe("consumer")
        total_published = 200
        collected: list[BusEvent] = []
        lock = threading.Lock()

        def publisher() -> None:
            for i in range(total_published):
                bus.publish(_make_event("TEST", "producer", {"i": i}))

        def consumer() -> None:
            deadline = time.time() + 5.0
            while time.time() < deadline:
                batch = bus.poll("consumer")
                if batch:
                    with lock:
                        collected.extend(batch)
                if len(collected) >= total_published:
                    break
                time.sleep(0.001)

        pub_thread = threading.Thread(target=publisher)
        con_thread = threading.Thread(target=consumer)
        pub_thread.start()
        con_thread.start()
        pub_thread.join(timeout=10.0)
        con_thread.join(timeout=10.0)

        # Drain any remaining
        remaining = bus.poll("consumer")
        collected.extend(remaining)

        assert len(collected) == total_published


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


class TestCreateEventBus:
    """Tests for the create_event_bus factory function."""

    def test_create_local_bus(self) -> None:
        bus = create_event_bus("local")
        assert isinstance(bus, LocalEventBus)
        bus.close()

    def test_unknown_backend_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown event bus backend"):
            create_event_bus("carrier_pigeon")

    def test_azure_without_sdk_raises_import_error(self) -> None:
        # Unless azure-servicebus is installed, this should raise ImportError
        # We test this conditionally
        try:
            import azure.servicebus  # noqa: F401

            pytest.skip("azure-servicebus is installed, cannot test ImportError path")
        except ImportError:
            with pytest.raises(ImportError, match="azure-servicebus"):
                create_event_bus("azure", connection_string="fake")

    def test_redis_without_sdk_raises_import_error(self) -> None:
        try:
            import redis  # noqa: F401

            pytest.skip("redis is installed, cannot test ImportError path")
        except ImportError:
            with pytest.raises(ImportError, match="redis"):
                create_event_bus("redis")


# ---------------------------------------------------------------------------
# Protocol compliance test
# ---------------------------------------------------------------------------


class TestProtocolCompliance:
    """Verify LocalEventBus satisfies the EventBus protocol."""

    def test_local_bus_is_event_bus(self) -> None:
        bus = LocalEventBus()
        assert isinstance(bus, EventBus)
        bus.close()


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary and edge case tests."""

    def test_publish_with_no_subscribers(self) -> None:
        """Publishing with no subscribers should not raise."""
        bus = LocalEventBus()
        bus.publish(_make_event("TEST", "agent_a"))
        # No error = success

    def test_large_payload_round_trip(self) -> None:
        payload = {"data": "x" * 100_000, "nested": {"a": [1, 2, 3]}}
        evt = _make_event("BIG_EVENT", "agent_a", payload)
        restored = BusEvent.from_json(evt.to_json())
        assert restored.payload["data"] == "x" * 100_000

    def test_event_ordering_preserved(self) -> None:
        bus = LocalEventBus()
        bus.subscribe("receiver")
        for i in range(100):
            bus.publish(_make_event("SEQ", "sender", {"seq": i}))
        events = bus.poll("receiver")
        assert [e.payload["seq"] for e in events] == list(range(100))

    def test_subscribe_preserves_pending_events(self) -> None:
        """Re-subscribing with a new filter should not drop pending events."""
        bus = LocalEventBus()
        bus.subscribe("agent_a")
        bus.publish(_make_event("TYPE_A", "sender"))
        # Re-subscribe (changes filter but keeps mailbox)
        bus.subscribe("agent_a", event_types=["TYPE_A", "TYPE_B"])
        events = bus.poll("agent_a")
        assert len(events) == 1
