"""Tests for partition routing and event handling in distributed_hive_graph.py and agent_entrypoint.py."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import queue
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest  # type: ignore[import-unresolved]

# ---- distributed_hive_graph ----
# We need to import it properly
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
    EventHubsShardTransport,
)
from amplihack.agents.goal_seeking.input_source import EventHubsInputSource

# ---- agent_entrypoint ----
_ENTRYPOINT_PATH = Path(__file__).parent.parent / "agent_entrypoint.py"
_REMOTE_ADAPTER_PATH = Path(__file__).parent.parent / "remote_agent_adapter.py"


def _load_entrypoint():
    spec = importlib.util.spec_from_file_location("agent_entrypoint", _ENTRYPOINT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_remote_agent_adapter():
    spec = importlib.util.spec_from_file_location("remote_agent_adapter", _REMOTE_ADAPTER_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_REMOTE_ADAPTER = _load_remote_agent_adapter()
RemoteAgentAdapter = _REMOTE_ADAPTER.RemoteAgentAdapter


def _stable_hash_index(agent_id: str) -> int:
    digest = hashlib.sha256(agent_id.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


# ===========================================================================
# EventHubsShardTransport — partition routing
# ===========================================================================


class TestAgentIndex:
    """EventHubsShardTransport._agent_index() static method."""

    def test_standard_agent_name(self):
        assert EventHubsShardTransport._agent_index("agent-0") == 0
        assert EventHubsShardTransport._agent_index("agent-42") == 42
        assert EventHubsShardTransport._agent_index("agent-99") == 99

    def test_multi_hyphen_name(self):
        # rsplit("-", 1) takes the last segment
        assert EventHubsShardTransport._agent_index("hive-agent-7") == 7

    def test_non_numeric_name_uses_stable_hash(self):
        result = EventHubsShardTransport._agent_index("coordinator")
        assert result == _stable_hash_index("coordinator")

    def test_empty_string_uses_stable_hash(self):
        result = EventHubsShardTransport._agent_index("")
        assert result == _stable_hash_index("")


class TestTargetPartition:
    """EventHubsShardTransport._target_partition() method."""

    @patch.object(EventHubsShardTransport, "__init__", lambda self, **kw: None)
    def _make_transport(self, num_partitions=32):
        t = EventHubsShardTransport()  # type: ignore[call-arg]
        t._num_partitions = num_partitions
        t._connection_string = "fake"
        t._consumer_group = "cg"
        t._eventhub_name = "hub"
        return t

    def test_partition_wraps_around(self):
        transport = self._make_transport(num_partitions=32)
        assert transport._target_partition("agent-0") == "0"
        assert transport._target_partition("agent-31") == "31"
        assert transport._target_partition("agent-32") == "0"  # wraps
        assert transport._target_partition("agent-33") == "1"

    def test_partition_small_hub(self):
        transport = self._make_transport(num_partitions=4)
        assert transport._target_partition("agent-0") == "0"
        assert transport._target_partition("agent-4") == "0"
        assert transport._target_partition("agent-5") == "1"

    def test_same_agent_always_same_partition(self):
        transport = self._make_transport(num_partitions=16)
        p1 = transport._target_partition("agent-42")
        p2 = transport._target_partition("agent-42")
        assert p1 == p2


class TestGetNumPartitions:
    """EventHubsShardTransport._get_num_partitions() method."""

    @patch.object(EventHubsShardTransport, "__init__", lambda self, **kw: None)
    def _make_transport(self):
        t = EventHubsShardTransport()  # type: ignore[call-arg]
        t._num_partitions = None
        t._connection_string = "fake"
        t._consumer_group = "cg"
        t._eventhub_name = "hub"
        return t

    def test_cached_value_returned(self):
        t = self._make_transport()
        t._num_partitions = 16
        assert t._get_num_partitions() == 16

    def test_fallback_on_import_error(self):
        t = self._make_transport()
        with (
            patch.dict("sys.modules", {"azure.eventhub": None}),
            patch(
                "amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph.logger.warning"
            ) as mock_warning,
        ):
            # Force import to fail
            result = t._get_num_partitions()
            assert result == 32  # default fallback
        mock_warning.assert_called_once()

    def test_caches_after_first_call(self):
        t = self._make_transport()
        t._num_partitions = None
        # Simulate failure so it falls back to 32
        with patch.dict("sys.modules", {"azure.eventhub": None}):
            t._get_num_partitions()
        assert t._num_partitions == 32
        # Second call returns cached
        assert t._get_num_partitions() == 32


class TestInputSourcePartitionRouting:
    """EventHubsInputSource must read the agent's deterministic partition."""

    @patch.object(EventHubsInputSource, "__init__", lambda self, *args, **kwargs: None)
    def _make_source(self, agent_name="agent-5", num_partitions=32):
        src = EventHubsInputSource()  # type: ignore[call-arg]
        src._agent_name = agent_name
        src._consumer_group = "cg-app-1"
        src._eventhub_name = "hub"
        src._num_partitions = num_partitions
        src._starting_position = "@latest"
        src._consumer = MagicMock()
        src._consumer.get_partition_ids.return_value = [str(i) for i in range(num_partitions)]
        src._max_wait_time = 1
        src._shutdown = threading.Event()
        src._closed = False
        src._queue = queue.Queue()
        src._inline_event_handler = None
        return src

    def test_target_partition_wraps(self):
        src = self._make_source(agent_name="agent-33", num_partitions=32)
        assert src._target_partition("agent-33") == "1"

    def test_target_partition_uses_stable_hash_for_non_numeric_agent(self):
        src = self._make_source(agent_name="coordinator", num_partitions=32)
        expected = str(_stable_hash_index("coordinator") % 32)
        assert src._target_partition("coordinator") == expected

    def test_receive_uses_explicit_partition_id(self):
        src = self._make_source(agent_name="agent-5")
        first_call = True

        def _receive(**_):
            nonlocal first_call
            if first_call:
                first_call = False
                src._shutdown.set()
            return

        src._consumer.receive.side_effect = _receive

        src._receive_loop()

        kwargs = src._consumer.receive.call_args.kwargs
        assert kwargs["partition_id"] == "5"
        assert kwargs["starting_position"] == "@latest"

    def test_receive_loop_retries_after_unexpected_return(self):
        src = self._make_source(agent_name="agent-5")

        call_count = 0

        def _receive(**_):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                src._shutdown.set()
            return

        src._consumer.receive.side_effect = _receive

        with patch("amplihack.agents.goal_seeking.input_source.time.sleep", return_value=None):
            src._receive_loop()

        assert call_count == 2

    def test_next_ignores_unexpected_shutdown_sentinel(self):
        src = self._make_source(agent_name="agent-5")
        src._queue.put((None, {}))
        src._queue.put(("hello", {"event_id": "evt-1"}))

        assert src.next() == "hello"
        assert src.last_event_metadata == {"event_id": "evt-1"}

    def test_partition_count_fallback_logs_warning(self):
        src = self._make_source(agent_name="agent-5")
        src._num_partitions = None
        src._consumer.get_partition_ids.side_effect = RuntimeError("boom")

        with patch("amplihack.agents.goal_seeking.input_source.logger.warning") as mock_warning:
            result = src._get_num_partitions()

        assert result == 32
        mock_warning.assert_called_once()

    def test_receive_loop_handles_online_check_inline(self):
        src = self._make_source(agent_name="agent-5")
        src._inline_event_handler = MagicMock(return_value=True)
        partition_context = MagicMock()
        event = MagicMock()
        event.body_as_str.return_value = json.dumps(
            {
                "event_type": "ONLINE_CHECK",
                "event_id": "evt-online-1",
                "run_id": "run-123",
                "target_agent": "agent-5",
                "payload": {"target_agent": "agent-5"},
            }
        )

        def _receive(**kwargs):
            kwargs["on_event"](partition_context, event)
            src._shutdown.set()

        src._consumer.receive.side_effect = _receive

        src._receive_loop()

        src._inline_event_handler.assert_called_once()
        metadata = src._inline_event_handler.call_args.args[0]
        assert metadata["event_type"] == "ONLINE_CHECK"
        assert metadata["run_id"] == "run-123"
        queued_text, queued_meta = src._queue.get_nowait()
        assert queued_text is None
        assert queued_meta == {}
        assert src._queue.empty()
        partition_context.update_checkpoint.assert_called_once_with(event)


class TestPublishPartitionRouting:
    """Verify _publish converts agent-N partition_key to explicit partition_id."""

    @patch.object(EventHubsShardTransport, "__init__", lambda self, **kw: None)
    def _make_transport(self):
        import threading

        t = EventHubsShardTransport()  # type: ignore[call-arg]
        t._num_partitions = 32
        t._connection_string = "fake"
        t._consumer_group = "cg"
        t._eventhub_name = "hub"
        t._agent_id = "agent-0"
        t._producer = None
        t._producer_lock = threading.Lock()
        t._shutdown = MagicMock()
        t._shutdown.is_set.return_value = False
        return t

    def test_publish_uses_partition_id_for_agent_name(self):
        transport = self._make_transport()

        mock_producer = MagicMock()
        mock_batch = MagicMock()
        mock_producer.create_batch.return_value = mock_batch

        with (
            patch(
                "azure.eventhub.EventHubProducerClient",
            ) as MockProducer,
            patch(
                "azure.eventhub.EventData",
            ) as MockEventData,
        ):
            MockProducer.from_connection_string.return_value = mock_producer
            MockEventData.side_effect = lambda data: data

            transport._publish(
                {"event_type": "SHARD_QUERY", "payload": {"target_agent": "agent-5"}},
                partition_key="agent-5",
            )

            # Should use partition_id=5 (not partition_key)
            create_kwargs = mock_producer.create_batch.call_args[1]
            assert "partition_id" in create_kwargs
            assert create_kwargs["partition_id"] == "5"
            assert "partition_key" not in create_kwargs

    def test_publish_uses_partition_key_for_non_agent(self):
        transport = self._make_transport()

        mock_producer = MagicMock()
        mock_batch = MagicMock()
        mock_producer.create_batch.return_value = mock_batch

        with (
            patch(
                "azure.eventhub.EventHubProducerClient",
            ) as MockProducer,
            patch(
                "azure.eventhub.EventData",
            ) as MockEventData,
        ):
            MockProducer.from_connection_string.return_value = mock_producer
            MockEventData.side_effect = lambda data: data

            transport._publish(
                {"event_type": "SOME_EVENT", "payload": {}},
                partition_key="broadcast-key",
            )

            create_kwargs = mock_producer.create_batch.call_args[1]
            assert "partition_key" in create_kwargs
            assert create_kwargs["partition_key"] == "broadcast-key"

    def test_publish_resets_producer_on_send_failure(self):
        transport = self._make_transport()

        mock_producer = MagicMock()
        mock_producer.create_batch.side_effect = ConnectionError("network down")

        with (
            patch(
                "azure.eventhub.EventHubProducerClient",
            ) as MockProducer,
            patch(
                "azure.eventhub.EventData",
            ),
        ):
            MockProducer.from_connection_string.return_value = mock_producer

            # Should not raise — logs warning and resets producer
            transport._publish(
                {"event_type": "SHARD_QUERY", "payload": {"target_agent": "agent-1"}},
                partition_key="agent-1",
            )
            assert transport._producer is None


class TestReceiveLoopCheckpointing:
    """EventHubsShardTransport should checkpoint shard work only after handling."""

    @patch.object(EventHubsShardTransport, "__init__", lambda self, **kw: None)
    def _make_transport(self):
        t = EventHubsShardTransport()  # type: ignore[call-arg]
        t._num_partitions = 32
        t._connection_string = "fake"
        t._consumer_group = "cg-agent-5"
        t._eventhub_name = "hub"
        t._agent_id = "agent-5"
        t._local_boot_id = "boot-local"
        t._pending = {}
        t._pending_lock = threading.Lock()
        t._pending_errors = {}
        t._pending_payloads = {}
        t._pending_requests = {}
        t._peer_boot_ids = {}
        t._mailbox = []
        t._mailbox_lock = threading.Lock()
        t._mailbox_ready = threading.Event()
        t._shutdown = threading.Event()
        return t

    def test_receive_loop_defers_checkpoint_for_shard_query(self):
        import json

        transport = self._make_transport()
        partition_context = MagicMock()
        event = MagicMock()
        event.body_as_str.return_value = json.dumps(
            {
                "event_id": "evt-1",
                "event_type": "SHARD_QUERY",
                "source_agent": "requester",
                "timestamp": 1.23,
                "payload": {
                    "target_agent": "agent-5",
                    "correlation_id": "corr-1",
                    "query": "projects",
                    "limit": 5,
                },
            }
        )
        mock_consumer = MagicMock()

        def _receive(**kwargs):
            kwargs["on_event"](partition_context, event)
            transport._shutdown.set()

        mock_consumer.receive.side_effect = _receive

        with patch("azure.eventhub.EventHubConsumerClient") as MockConsumer:
            MockConsumer.from_connection_string.return_value = mock_consumer
            transport._receive_loop()

        partition_context.update_checkpoint.assert_not_called()

        items = transport.poll("agent-5")
        assert len(items) == 1
        mailbox_item = items[0]
        assert mailbox_item.event.event_type == "SHARD_QUERY"

        mailbox_item.ack()
        partition_context.update_checkpoint.assert_called_once_with(event)

    def test_handle_peer_online_fails_pending_query_on_new_boot(self):
        transport = self._make_transport()
        transport._publish = MagicMock()

        done = threading.Event()
        with transport._pending_lock:
            transport._pending["corr-1"] = (done, [])
            transport._pending_errors["corr-1"] = ""
            transport._pending_requests["corr-1"] = {
                "target_agent": "agent-9",
                "operation": "search",
                "request_payload": {"query": "projects", "limit": 5},
                "target_boot_id": "boot-old",
            }

        transport._handle_peer_online("agent-9", "boot-new")

        transport._publish.assert_not_called()
        assert done.is_set()
        assert transport._pending_errors["corr-1"].startswith(
            "Shard target agent-9 restarted before response"
        )

    def test_handle_peer_online_fails_unknown_boot_published_after_request(self):
        transport = self._make_transport()
        transport._publish = MagicMock()

        done = threading.Event()
        with transport._pending_lock:
            transport._pending["corr-1"] = (done, [])
            transport._pending_errors["corr-1"] = ""
            transport._pending_requests["corr-1"] = {
                "target_agent": "agent-9",
                "operation": "search",
                "request_payload": {"query": "projects", "limit": 5},
                "sent_at": 100.0,
                "target_boot_id": "",
            }

        transport._handle_peer_online("agent-9", "boot-new", observed_at=101.0)

        transport._publish.assert_not_called()
        assert done.is_set()
        assert transport._pending_errors["corr-1"].startswith(
            "Shard target agent-9 came online after request dispatch"
        )

    def test_handle_peer_online_ignores_stale_unknown_boot_broadcast(self):
        transport = self._make_transport()
        transport._publish = MagicMock()

        done = threading.Event()
        with transport._pending_lock:
            transport._pending["corr-1"] = (done, [])
            transport._pending_errors["corr-1"] = ""
            transport._pending_requests["corr-1"] = {
                "target_agent": "agent-9",
                "operation": "search",
                "request_payload": {"query": "projects", "limit": 5},
                "sent_at": 100.0,
                "target_boot_id": "",
            }

        transport._handle_peer_online("agent-9", "boot-new", observed_at=99.0)

        transport._publish.assert_not_called()
        assert not done.is_set()
        assert transport._pending_errors["corr-1"] == ""

    def test_publish_agent_online_broadcasts_to_all_partitions(self):
        transport = self._make_transport()
        transport._publish = MagicMock()
        transport._num_partitions = 4

        transport.publish_agent_online()

        assert transport._publish.call_count == 4
        partition_ids = [call.kwargs["partition_id"] for call in transport._publish.call_args_list]
        assert partition_ids == ["0", "1", "2", "3"]
        for call in transport._publish.call_args_list:
            payload = call.args[0]
            assert payload["event_type"] == "SHARD_AGENT_ONLINE"
            assert payload["timestamp"] > 0


class TestRemoteAdapterPublishPartitionRouting:
    """Verify RemoteAgentAdapter uses explicit partition routing for targeted input."""

    @patch.object(RemoteAgentAdapter, "__init__", lambda self, **kw: None)
    def _make_adapter(self):
        adapter = RemoteAgentAdapter()  # type: ignore[call-arg]
        adapter._num_partitions = 32
        adapter._connection_string = "fake"
        adapter._input_hub = "hive-events-test"
        adapter._run_id = "run123"
        adapter._producer_lock = threading.Lock()
        adapter._producer = None
        return adapter

    def test_publish_uses_partition_id_for_agent_name(self):
        adapter = self._make_adapter()

        mock_producer = MagicMock()
        mock_batch = MagicMock()
        mock_producer.create_batch.return_value = mock_batch

        with (
            patch("azure.eventhub.EventHubProducerClient") as MockProducer,
            patch("azure.eventhub.EventData") as MockEventData,
        ):
            MockProducer.from_connection_string.return_value = mock_producer
            MockEventData.side_effect = lambda data: data

            adapter._publish_event({"event_type": "INPUT"}, partition_key="agent-5")

            create_kwargs = mock_producer.create_batch.call_args.kwargs
            assert create_kwargs["partition_id"] == "5"
            assert "partition_key" not in create_kwargs

    def test_publish_uses_partition_key_for_non_agent_key(self):
        adapter = self._make_adapter()

        mock_producer = MagicMock()
        mock_batch = MagicMock()
        mock_producer.create_batch.return_value = mock_batch

        with (
            patch("azure.eventhub.EventHubProducerClient") as MockProducer,
            patch("azure.eventhub.EventData") as MockEventData,
        ):
            MockProducer.from_connection_string.return_value = mock_producer
            MockEventData.side_effect = lambda data: data

            adapter._publish_event({"event_type": "INPUT"}, partition_key="broadcast-key")

            create_kwargs = mock_producer.create_batch.call_args.kwargs
            assert create_kwargs["partition_key"] == "broadcast-key"
            assert "partition_id" not in create_kwargs


# ===========================================================================
# _extract_input_text
# ===========================================================================


class TestExtractInputText:
    """Tests for agent_entrypoint._extract_input_text()."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.mod = _load_entrypoint()
        self.extract = self.mod._extract_input_text

    def test_learn_content(self):
        result = self.extract(
            "LEARN_CONTENT",
            {"content": "The sky is blue."},
            {},
        )
        assert result == "The sky is blue."

    def test_input_question(self):
        result = self.extract(
            "INPUT",
            {"question": "What color is the sky?"},
            {},
        )
        assert result == "What color is the sky?"

    def test_query_question(self):
        result = self.extract(
            "QUERY",
            {"question": "Who wrote Hamlet?"},
            {},
        )
        assert result == "Who wrote Hamlet?"

    def test_query_text_fallback(self):
        result = self.extract(
            "QUERY",
            {"text": "search for something"},
            {},
        )
        assert result == "search for something"

    def test_query_content_fallback(self):
        result = self.extract(
            "QUERY",
            {"content": "some content"},
            {},
        )
        assert result == "some content"

    def test_unknown_event_type_fallback_keys(self):
        result = self.extract(
            "CUSTOM_EVENT",
            {"message": "hello from custom"},
            {},
        )
        assert result == "hello from custom"

    def test_unknown_event_type_data_key(self):
        result = self.extract(
            "CUSTOM_EVENT",
            {"data": "raw data here"},
            {},
        )
        assert result == "raw data here"

    def test_empty_payload_returns_event_string(self):
        raw = {"event_type": "EMPTY", "payload": {}}
        result = self.extract("EMPTY", {}, raw)
        assert "Event received:" in result

    def test_none_payload_handled(self):
        result = self.extract("WHATEVER", None, {"raw": "event"})
        assert "Event received:" in result

    def test_learn_content_empty_content(self):
        result = self.extract("LEARN_CONTENT", {"content": ""}, {})
        assert result == ""

    def test_network_graph_search_query(self):
        result = self.extract(
            "network_graph.search_query",
            {"question": "distributed search query"},
            {},
        )
        assert result == "distributed search query"


# ===========================================================================
# _CorrelatingInputSource
# ===========================================================================


class TestCorrelatingInputSource:
    def test_sets_context_on_next(self):
        mod = _load_entrypoint()
        cls = mod._CorrelatingInputSource

        mock_source = MagicMock()
        mock_source.next.return_value = "hello"
        mock_source.last_event_metadata = {"event_id": "ev1", "question_id": "q1", "run_id": "r1"}

        mock_publisher = MagicMock()
        wrapper = cls(mock_source, mock_publisher)

        result = wrapper.next()
        assert result == "hello"
        mock_publisher.set_context.assert_called_once_with("ev1", "q1", run_id="r1")

    def test_clears_context_when_no_event_id(self):
        mod = _load_entrypoint()
        cls = mod._CorrelatingInputSource

        mock_source = MagicMock()
        mock_source.next.return_value = "data"
        mock_source.last_event_metadata = {}

        mock_publisher = MagicMock()
        wrapper = cls(mock_source, mock_publisher)

        wrapper.next()
        mock_publisher.clear_context.assert_called_once()

    def test_close_delegates(self):
        mod = _load_entrypoint()
        cls = mod._CorrelatingInputSource

        mock_source = MagicMock()
        mock_publisher = MagicMock()
        wrapper = cls(mock_source, mock_publisher)

        wrapper.close()
        mock_source.close.assert_called_once()


# ===========================================================================
# _handle_event
# ===========================================================================


class TestHandleEvent:
    def test_feed_complete_publishes_agent_ready(self):
        mod = _load_entrypoint()

        mock_agent = MagicMock()
        mock_memory = MagicMock()
        mock_transport = MagicMock()
        mock_memory._transport = mock_transport

        event = {
            "event_type": "FEED_COMPLETE",
            "payload": {"total_turns": 100},
        }

        mod._handle_event("agent-0", event, mock_memory, mock_agent)
        # Should have published AGENT_READY via transport
        mock_transport.publish.assert_called_once()
        call_args = mock_transport.publish.call_args
        bus_event = call_args[0][0]
        assert bus_event.event_type == "AGENT_READY"

    def test_agent_ready_ignored(self):
        mod = _load_entrypoint()
        mock_agent = MagicMock()
        mock_memory = MagicMock()

        event = {"event_type": "AGENT_READY", "payload": {}}
        mod._handle_event("agent-0", event, mock_memory, mock_agent)
        mock_agent.process.assert_not_called()

    def test_query_response_ignored(self):
        mod = _load_entrypoint()
        mock_agent = MagicMock()
        mock_memory = MagicMock()

        event = {
            "event_type": "QUERY_RESPONSE",
            "payload": {"query_id": "q1"},
        }
        mod._handle_event("agent-0", event, mock_memory, mock_agent)
        mock_agent.process.assert_not_called()

    def test_input_event_calls_process(self):
        mod = _load_entrypoint()
        mock_agent = MagicMock()
        mock_memory = MagicMock()

        event = {
            "event_type": "INPUT",
            "payload": {"question": "What is 2+2?"},
        }
        mod._handle_event("agent-0", event, mock_memory, mock_agent)
        mock_agent.process.assert_called_once_with("What is 2+2?")

    def test_learn_content_calls_process_store(self):
        mod = _load_entrypoint()
        mock_agent = MagicMock()
        mock_memory = MagicMock()

        event = {
            "event_type": "LEARN_CONTENT",
            "payload": {"content": "The earth orbits the sun."},
        }
        mod._handle_event("agent-0", event, mock_memory, mock_agent)
        mock_agent.process_store.assert_called_once_with("The earth orbits the sun.")
        mock_agent.process.assert_not_called()
