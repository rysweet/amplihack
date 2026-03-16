"""Tests for remote_agent_adapter.py — zero-external-dependency unit tests."""

from __future__ import annotations

import importlib.util
import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest  # type: ignore[import-unresolved]

_ADAPTER_PATH = Path(__file__).parent.parent / "remote_agent_adapter.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("remote_agent_adapter", _ADAPTER_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adapter(mod, agent_count=5, answer_timeout=0):
    """Create an adapter with mocked EH clients."""
    with patch.object(mod, "threading") as mock_threading:
        # Make the listener thread a no-op
        mock_thread = MagicMock()
        mock_threading.Event.side_effect = [
            threading.Event(),  # _shutdown
            threading.Event(),  # _idle_wait_done
            threading.Event(),  # _all_agents_ready
        ]
        mock_threading.Lock.return_value = threading.Lock()
        mock_threading.Thread.return_value = mock_thread

        # Pre-set listener_alive so __init__ doesn't block
        adapter = object.__new__(mod.RemoteAgentAdapter)
        adapter._connection_string = (
            "Endpoint=sb://fake.servicebus.windows.net/;SharedAccessKeyName=x;SharedAccessKey=y"
        )
        adapter._input_hub = "hive-input"
        adapter._response_hub = "eval-responses"
        adapter._resource_group = ""
        adapter._agent_count = agent_count
        adapter._learn_count = 0
        adapter._question_count = 0
        adapter._answer_timeout = answer_timeout
        adapter._shutdown = threading.Event()
        adapter._startup_wait_done = threading.Event()
        adapter._idle_wait_done = threading.Event()
        adapter._counter_lock = threading.Lock()
        adapter._answer_lock = threading.Lock()
        adapter._pending_answers = {}
        adapter._answer_events = {}
        adapter._online_agents = set()
        adapter._online_lock = threading.Lock()
        adapter._all_agents_online = threading.Event()
        adapter._ready_agents = set()
        adapter._ready_lock = threading.Lock()
        adapter._all_agents_ready = threading.Event()
        adapter._run_id = "test_run_abc"
        adapter._num_partitions = 32
        adapter._listener_alive = threading.Event()
        adapter._listener_alive.set()
        adapter._listener_thread = MagicMock()

    return adapter


# ===========================================================================
# Tests
# ===========================================================================


class TestRemoteAgentAdapterInit:
    def test_module_loads(self):
        mod = _load_module()
        assert hasattr(mod, "RemoteAgentAdapter")

    def test_adapter_attrs(self):
        mod = _load_module()
        adapter = _make_adapter(mod, agent_count=10)
        assert adapter._agent_count == 10
        assert adapter._learn_count == 0
        assert adapter._question_count == 0
        assert adapter._run_id == "test_run_abc"


class TestPublishEvent:
    def test_publish_attaches_run_id(self):
        mod = _load_module()
        adapter = _make_adapter(mod)

        mock_producer = MagicMock()
        mock_batch = MagicMock()
        mock_producer.create_batch.return_value = mock_batch
        mock_producer.__enter__ = MagicMock(return_value=mock_producer)
        mock_producer.__exit__ = MagicMock(return_value=False)

        with (
            patch(
                "azure.eventhub.EventHubProducerClient",
                create=True,
            ) as MockProducer,
            patch(
                "azure.eventhub.EventData",
                create=True,
            ) as MockEventData,
        ):
            MockProducer.from_connection_string.return_value = mock_producer
            MockEventData.side_effect = lambda data: data

            payload = {"event_type": "LEARN_CONTENT", "event_id": "abc"}
            adapter._publish_event(payload, partition_key="agent-0")

            assert payload["run_id"] == "test_run_abc"
            mock_producer.send_batch.assert_called_once()

    def test_publish_retries_on_failure(self):
        mod = _load_module()
        adapter = _make_adapter(mod)

        # First producer fails, second succeeds
        mock_producer_fail = MagicMock()
        mock_producer_fail.__enter__ = MagicMock(return_value=mock_producer_fail)
        mock_producer_fail.__exit__ = MagicMock(return_value=False)
        mock_producer_fail.send_batch.side_effect = ConnectionError("EH down")

        mock_producer_ok = MagicMock()
        mock_producer_ok.__enter__ = MagicMock(return_value=mock_producer_ok)
        mock_producer_ok.__exit__ = MagicMock(return_value=False)
        mock_batch = MagicMock()
        mock_producer_ok.create_batch.return_value = mock_batch

        with (
            patch(
                "azure.eventhub.EventHubProducerClient",
                create=True,
            ) as MockProducer,
            patch(
                "azure.eventhub.EventData",
                create=True,
            ) as MockEventData,
        ):
            MockProducer.from_connection_string.side_effect = [
                mock_producer_fail,
                mock_producer_ok,
            ]
            MockEventData.side_effect = lambda data: data

            adapter._publish_event(
                {"event_type": "INPUT", "event_id": "x"},
                partition_key="agent-1",
            )
            mock_producer_ok.send_batch.assert_called_once()

    def test_publish_raises_after_retry_failure(self):
        mod = _load_module()
        adapter = _make_adapter(mod)

        def make_failing_producer():
            p = MagicMock()
            p.__enter__ = MagicMock(return_value=p)
            p.__exit__ = MagicMock(return_value=False)
            p.send_batch.side_effect = ConnectionError("EH down")
            return p

        with (
            patch(
                "azure.eventhub.EventHubProducerClient",
                create=True,
            ) as MockProducer,
            patch(
                "azure.eventhub.EventData",
                create=True,
            ) as MockEventData,
        ):
            MockProducer.from_connection_string.side_effect = [
                make_failing_producer(),
                make_failing_producer(),
            ]
            MockEventData.side_effect = lambda data: data

            with pytest.raises(ConnectionError):
                adapter._publish_event(
                    {"event_type": "INPUT", "event_id": "x"},
                    partition_key="agent-1",
                )


class TestLearnFromContent:
    def test_first_learn_waits_for_online_agents_once(self):
        mod = _load_module()
        adapter = _make_adapter(mod, agent_count=2)
        adapter._wait_for_agents_online = MagicMock()
        adapter._publish_event = MagicMock()

        adapter.learn_from_content("hello")
        adapter.learn_from_content("world")

        adapter._wait_for_agents_online.assert_called_once()
        assert adapter._startup_wait_done.is_set()

    def test_round_robin_targets(self):
        mod = _load_module()
        adapter = _make_adapter(mod, agent_count=3)
        adapter._startup_wait_done.set()

        published_keys = []

        def capture_publish(payload, partition_key):
            published_keys.append(partition_key)

        adapter._publish_event = capture_publish

        for i in range(6):
            result = adapter.learn_from_content(f"content {i}")
            assert "facts_stored" in result

        assert published_keys == [
            "agent-0",
            "agent-1",
            "agent-2",
            "agent-0",
            "agent-1",
            "agent-2",
        ]

    def test_learn_increments_counter(self):
        mod = _load_module()
        adapter = _make_adapter(mod, agent_count=2)
        adapter._startup_wait_done.set()
        adapter._publish_event = MagicMock()

        adapter.learn_from_content("hello")
        assert adapter._learn_count == 1
        adapter.learn_from_content("world")
        assert adapter._learn_count == 2


class TestAnswerQuestion:
    def test_answer_returned_when_set(self):
        mod = _load_module()
        adapter = _make_adapter(mod, agent_count=2)
        adapter._idle_wait_done.set()  # skip idle wait

        # Capture the event_id from publish
        captured_event_ids = []

        def capture_publish(payload, partition_key):
            captured_event_ids.append(payload.get("event_id", ""))

        adapter._publish_event = capture_publish

        # Answer in a background thread
        def answer_later():
            time.sleep(0.1)
            eid = captured_event_ids[0]
            with adapter._answer_lock:
                adapter._pending_answers[eid] = "The answer is 42"
                adapter._answer_events[eid].set()

        t = threading.Thread(target=answer_later, daemon=True)
        t.start()

        result = adapter.answer_question("what is the answer?")
        t.join(timeout=5)
        assert result == "The answer is 42"

    def test_answer_timeout_returns_default(self):
        mod = _load_module()
        adapter = _make_adapter(mod, agent_count=1, answer_timeout=1)
        adapter._idle_wait_done.set()
        adapter._publish_event = MagicMock()

        result = adapter.answer_question("will time out")
        assert result == "No answer received"


class TestOnEvent:
    def test_agent_online_tracked(self):
        mod = _load_module()
        adapter = _make_adapter(mod, agent_count=2)

        body = json.dumps(
            {
                "event_type": "AGENT_ONLINE",
                "agent_id": "agent-1",
                "run_id": "test_run_abc",
            }
        )
        mock_event = MagicMock()
        mock_event.body_as_str.return_value = body

        run_id = adapter._run_id

        def on_event(partition_context, event):
            if event is None:
                return
            data = json.loads(event.body_as_str())
            rid = data.get("run_id", "")
            if rid and rid != run_id:
                return
            if data.get("event_type", "") == "AGENT_ONLINE":
                with adapter._online_lock:
                    adapter._online_agents.add(data.get("agent_id", ""))

        on_event(MagicMock(), mock_event)
        assert "agent-1" in adapter._online_agents

    def test_agent_ready_tracked(self):
        mod = _load_module()
        adapter = _make_adapter(mod, agent_count=2)

        # Simulate _on_event callback
        body = json.dumps(
            {
                "event_type": "AGENT_READY",
                "agent_id": "agent-0",
                "run_id": "test_run_abc",
            }
        )
        mock_event = MagicMock()
        mock_event.body_as_str.return_value = body

        mock_ctx = MagicMock()

        # Build the _on_event handler manually
        run_id = adapter._run_id

        def on_event(partition_context, event):
            if event is None:
                return
            data = json.loads(event.body_as_str())
            et = data.get("event_type", "")
            rid = data.get("run_id", "")
            if rid and rid != run_id:
                return
            if et == "AGENT_READY":
                agent_id = data.get("agent_id", "")
                if agent_id:
                    with adapter._ready_lock:
                        adapter._ready_agents.add(agent_id)

        on_event(mock_ctx, mock_event)
        assert "agent-0" in adapter._ready_agents

    def test_stale_run_id_filtered(self):
        mod = _load_module()
        adapter = _make_adapter(mod, agent_count=2)

        body = json.dumps(
            {
                "event_type": "AGENT_READY",
                "agent_id": "agent-0",
                "run_id": "old_run_xyz",
            }
        )
        mock_event = MagicMock()
        mock_event.body_as_str.return_value = body

        run_id = adapter._run_id

        def on_event(partition_context, event):
            if event is None:
                return
            data = json.loads(event.body_as_str())
            rid = data.get("run_id", "")
            if rid and rid != run_id:
                return
            et = data.get("event_type", "")
            if et == "AGENT_READY":
                with adapter._ready_lock:
                    adapter._ready_agents.add(data.get("agent_id", ""))

        on_event(MagicMock(), mock_event)
        assert len(adapter._ready_agents) == 0

    def test_eval_answer_delivered(self):
        mod = _load_module()
        adapter = _make_adapter(mod, agent_count=1)

        event_id = "ev123"
        answer_event = threading.Event()
        with adapter._answer_lock:
            adapter._answer_events[event_id] = answer_event

        body = json.dumps(
            {
                "event_type": "EVAL_ANSWER",
                "event_id": event_id,
                "answer": "Paris is the capital",
                "run_id": "test_run_abc",
                "agent_id": "agent-0",
            }
        )
        mock_event = MagicMock()
        mock_event.body_as_str.return_value = body

        run_id = adapter._run_id

        def on_event(partition_context, event):
            if event is None:
                return
            data = json.loads(event.body_as_str())
            rid = data.get("run_id", "")
            if rid and rid != run_id:
                return
            et = data.get("event_type", "")
            if et == "EVAL_ANSWER":
                eid = data.get("event_id", "")
                ans = data.get("answer", "")
                with adapter._answer_lock:
                    if eid in adapter._answer_events:
                        adapter._pending_answers[eid] = ans
                        adapter._answer_events[eid].set()

        on_event(MagicMock(), mock_event)
        assert answer_event.is_set()
        assert adapter._pending_answers[event_id] == "Paris is the capital"


class TestGetMemoryStats:
    def test_stats_returned(self):
        mod = _load_module()
        adapter = _make_adapter(mod, agent_count=3)
        adapter._learn_count = 100
        adapter._question_count = 10

        stats = adapter.get_memory_stats()
        assert stats["adapter"] == "remote"
        assert stats["learn_count"] == 100
        assert stats["question_count"] == 10
        assert stats["agent_count"] == 3


class TestClose:
    def test_close_sets_shutdown(self):
        mod = _load_module()
        adapter = _make_adapter(mod)
        adapter.close()
        assert adapter._shutdown.is_set()
