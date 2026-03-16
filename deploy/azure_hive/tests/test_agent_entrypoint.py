"""Tests for agent_entrypoint.py."""

from __future__ import annotations

import importlib.util
import os
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest  # type: ignore[import-unresolved]

# Load agent_entrypoint as a module (not installed as package)
_ENTRYPOINT_PATH = Path(__file__).parent.parent / "agent_entrypoint.py"


def _load_entrypoint():
    spec = importlib.util.spec_from_file_location("agent_entrypoint", _ENTRYPOINT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestAgentEntrypoint:
    def test_entrypoint_file_exists(self):
        assert _ENTRYPOINT_PATH.exists()

    def test_entrypoint_has_main(self):
        mod = _load_entrypoint()
        assert hasattr(mod, "main")
        assert callable(mod.main)

    def test_missing_agent_name_exits_1(self, monkeypatch):
        monkeypatch.delenv("AMPLIHACK_AGENT_NAME", raising=False)
        mod = _load_entrypoint()
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code == 1

    def test_main_initializes_learning_agent(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AMPLIHACK_AGENT_NAME", "test-agent")
        monkeypatch.setenv("AMPLIHACK_MEMORY_TRANSPORT", "local")
        monkeypatch.setenv("AMPLIHACK_MEMORY_STORAGE_PATH", str(tmp_path / "test-agent"))

        mock_memory_instance = MagicMock()
        mock_memory_instance.stats.return_value = {"fact_count": 0}

        mock_learning_agent = MagicMock()

        # Make the OODA loop exit after one iteration
        call_count = [0]

        def fast_sleep(secs):
            call_count[0] += 1
            if call_count[0] > 2:
                raise KeyboardInterrupt

        mod = _load_entrypoint()

        with patch("amplihack.memory.facade.Memory", return_value=mock_memory_instance):
            with patch(
                "amplihack.agents.goal_seeking.learning_agent.LearningAgent",
                return_value=mock_learning_agent,
            ):
                with patch.object(mod, "_ooda_tick"):
                    with patch("time.sleep", side_effect=fast_sleep):
                        try:
                            mod.main()
                        except (KeyboardInterrupt, SystemExit):
                            pass

        # LearningAgent should have been used for initial context (not memory.remember)
        mock_learning_agent.learn_from_content.assert_called()
        mock_memory_instance.remember.assert_not_called()

    def test_ooda_tick_logs_stats_every_10_ticks(self, monkeypatch):
        mod = _load_entrypoint()
        mock_mem = MagicMock()
        mock_mem.stats.return_value = {"fact_count": 5}
        mock_agent = MagicMock()

        # Tick 0 should call stats
        mod._ooda_tick("agent", mock_mem, 0, mock_agent)
        mock_mem.stats.assert_called_once()

        # Tick 5 should NOT call stats
        mock_mem.stats.reset_mock()
        mod._ooda_tick("agent", mock_mem, 5, mock_agent)
        mock_mem.stats.assert_not_called()

        # Tick 10 should call stats again
        mod._ooda_tick("agent", mock_mem, 10, mock_agent)
        mock_mem.stats.assert_called_once()

        # memory.recall should never be called (replaced by LearningAgent)
        mock_mem.recall.assert_not_called()

    def test_handle_query_event_uses_agent_process(self):
        """QUERY events feed input text to agent.process() via OODA loop."""
        mod = _load_entrypoint()
        mock_mem = MagicMock()

        mock_agent = MagicMock()
        mock_agent.process.return_value = "42 is the answer"

        query_event = {
            "event_type": "QUERY",
            "payload": {"query_id": "qid-1", "question": "What is 6 times 7?"},
        }
        mod._handle_event("agent", query_event, mock_mem, mock_agent)

        mock_agent.process.assert_called_once_with("What is 6 times 7?")
        mock_mem.recall.assert_not_called()

    def test_handle_learn_content_uses_store_only_path(self):
        """LEARN_CONTENT must use the store-only path even for question-like text."""
        mod = _load_entrypoint()
        mock_mem = MagicMock()
        mock_agent = MagicMock()

        learn_event = {
            "event_type": "LEARN_CONTENT",
            "payload": {"turn": 1, "content": "What is Sarah Chen's birthday?"},
        }
        mod._handle_event("agent", learn_event, mock_mem, mock_agent)

        mock_agent.process_store.assert_called_once_with("What is Sarah Chen's birthday?")
        mock_agent.process.assert_not_called()
        mock_mem.remember.assert_not_called()

    def test_run_event_driven_loop_uses_store_only_path_for_learn_content(self):
        mod = _load_entrypoint()
        agent = MagicMock()
        answer_publisher = MagicMock()
        memory = MagicMock()
        shutdown_event = threading.Event()

        class FakeInputSource:
            def __init__(self):
                self._source = self
                self.last_event_metadata = {}
                self._items = [
                    ("What is Sarah Chen's birthday?", {"event_type": "LEARN_CONTENT"}),
                    (None, {}),
                ]

            def next(self):
                text, meta = self._items.pop(0)
                self.last_event_metadata = meta
                if text is None:
                    shutdown_event.set()
                return text

        mod._run_event_driven_loop(
            "agent-0",
            agent,
            FakeInputSource(),
            answer_publisher,
            memory,
            shutdown_event,
        )

        agent.process_store.assert_called_once_with("What is Sarah Chen's birthday?")
        agent.process.assert_not_called()

    def test_handle_store_fact_batch_uses_direct_storage_path(self):
        mod = _load_entrypoint()
        mock_mem = MagicMock()
        mock_agent = MagicMock()
        fact_batch = {
            "facts": [
                {"context": "Campaign", "fact": "CAMP-1 is active", "confidence": 0.9, "tags": []}
            ],
            "summary_fact": None,
        }

        learn_event = {
            "event_type": "STORE_FACT_BATCH",
            "payload": {"fact_batch": fact_batch},
        }
        mod._handle_event("agent", learn_event, mock_mem, mock_agent)

        mock_agent.store_fact_batch.assert_called_once_with(fact_batch)
        mock_agent.process_store.assert_not_called()
        mock_agent.process.assert_not_called()

    def test_run_event_driven_loop_uses_direct_storage_for_fact_batch(self):
        mod = _load_entrypoint()
        agent = MagicMock()
        answer_publisher = MagicMock()
        memory = MagicMock()
        shutdown_event = threading.Event()
        fact_batch = {
            "facts": [
                {"context": "Campaign", "fact": "CAMP-1 is active", "confidence": 0.9, "tags": []}
            ],
            "summary_fact": None,
        }

        class FakeInputSource:
            def __init__(self):
                self._source = self
                self.last_event_metadata = {}
                self._items = [
                    (
                        "__STORE_FACT_BATCH__",
                        {"event_type": "STORE_FACT_BATCH", "payload": {"fact_batch": fact_batch}},
                    ),
                    (None, {}),
                ]

            def next(self):
                text, meta = self._items.pop(0)
                self.last_event_metadata = meta
                if text is None:
                    shutdown_event.set()
                return text

        mod._run_event_driven_loop(
            "agent-0",
            agent,
            FakeInputSource(),
            answer_publisher,
            memory,
            shutdown_event,
        )

        agent.store_fact_batch.assert_called_once_with(fact_batch)
        agent.process_store.assert_not_called()
        agent.process.assert_not_called()

    def test_run_event_driven_loop_publishes_agent_online_for_online_check(self):
        mod = _load_entrypoint()
        agent = MagicMock()
        answer_publisher = MagicMock()
        memory = MagicMock()
        shutdown_event = threading.Event()

        class FakeInputSource:
            def __init__(self):
                self._source = self
                self.last_event_metadata = {}
                self._items = [
                    ("__ONLINE_CHECK__", {"event_type": "ONLINE_CHECK", "run_id": "run-123"}),
                    (None, {}),
                ]

            def next(self):
                text, meta = self._items.pop(0)
                self.last_event_metadata = meta
                if text is None:
                    shutdown_event.set()
                return text

        mod._run_event_driven_loop(
            "agent-0",
            agent,
            FakeInputSource(),
            answer_publisher,
            memory,
            shutdown_event,
        )

        answer_publisher.publish_agent_online.assert_called_once_with(run_id="run-123")
        agent.process.assert_not_called()
        agent.process_store.assert_not_called()

    def test_run_event_driven_loop_ignores_transient_none_without_shutdown(self):
        mod = _load_entrypoint()
        agent = MagicMock()
        answer_publisher = MagicMock()
        memory = MagicMock()
        shutdown_event = threading.Event()

        class FakeInputSource:
            def __init__(self):
                self._source = self
                self.last_event_metadata = {}
                self._items = [
                    (None, {}),
                    ("__ONLINE_CHECK__", {"event_type": "ONLINE_CHECK", "run_id": "run-456"}),
                ]

            def next(self):
                text, meta = self._items.pop(0)
                self.last_event_metadata = meta
                if text == "__ONLINE_CHECK__":
                    shutdown_event.set()
                return text

        with patch.object(mod.time, "sleep", return_value=None):
            mod._run_event_driven_loop(
                "agent-0",
                agent,
                FakeInputSource(),
                answer_publisher,
                memory,
                shutdown_event,
            )

        answer_publisher.publish_agent_online.assert_called_once_with(run_id="run-456")
        agent.process.assert_not_called()
        agent.process_store.assert_not_called()

    def test_run_event_driven_loop_publishes_shutdown_event_when_none_follows_shutdown(self):
        mod = _load_entrypoint()
        agent = MagicMock()
        answer_publisher = MagicMock()
        memory = MagicMock()
        shutdown_event = threading.Event()
        publish_shutdown_event = MagicMock()

        class FakeInputSource:
            def __init__(self):
                self._source = self
                self.last_event_metadata = {"run_id": "run-shutdown"}

            def next(self):
                shutdown_event.set()
                return

        mod._run_event_driven_loop(
            "agent-0",
            agent,
            FakeInputSource(),
            answer_publisher,
            memory,
            shutdown_event,
            publish_shutdown_event=publish_shutdown_event,
        )

        publish_shutdown_event.assert_called_once_with(
            "input_shutdown",
            "input_source returned None with shutdown_event set",
            "run-shutdown",
        )
        agent.process.assert_not_called()
        agent.process_store.assert_not_called()

    def test_handle_event_passes_learning_agent_from_ooda_tick(self):
        """_ooda_tick forwards the learning_agent to _handle_event; memory.recall never called."""
        mod = _load_entrypoint()
        mock_mem = MagicMock()
        mock_mem.receive_events.return_value = [
            {"event_type": "QUERY", "payload": {"query_id": "q1", "question": "test?"}}
        ]
        mock_mem.receive_query_events.return_value = []

        mock_agent = MagicMock()
        mock_agent.process.return_value = "test answer"

        mod._ooda_tick("agent", mock_mem, 5, mock_agent)

        # The OODA tick calls agent.process() via _handle_event
        mock_agent.process.assert_called_once_with("test?")
        # memory.recall must never be called — LearningAgent handles all recall
        mock_mem.recall.assert_not_called()


class TestAnswerPublisher:
    def test_publish_agent_shutdown_uses_run_context(self):
        mod = _load_entrypoint()
        publisher = mod.AnswerPublisher(
            "agent-0",
            "Endpoint=sb://fake.servicebus.windows.net/;SharedAccessKeyName=x;SharedAccessKey=y",
            "eval-responses",
        )
        publisher._publish_to_eh = MagicMock()
        publisher._current_run_id = "run-ctx"

        publisher.publish_agent_shutdown(reason="signal", detail="signal=15")

        payload = publisher._publish_to_eh.call_args.args[0]
        assert payload["event_type"] == "AGENT_SHUTDOWN"
        assert payload["agent_id"] == "agent-0"
        assert payload["reason"] == "signal"
        assert payload["detail"] == "signal=15"
        assert payload["run_id"] == "run-ctx"


class TestDockerfile:
    def test_dockerfile_exists(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        assert dockerfile.exists()

    def test_dockerfile_has_python_base(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "python:3.11-slim" in content

    def test_dockerfile_has_non_root_user(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "useradd" in content
        assert "USER amplihack-agent" in content

    def test_dockerfile_installs_kuzu(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "kuzu" in content

    def test_dockerfile_installs_sentence_transformers(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "sentence-transformers" in content

    def test_dockerfile_has_entrypoint(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "agent_entrypoint.py" in content


class TestDeployScript:
    def test_deploy_sh_exists(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        assert deploy_sh.exists()

    def test_deploy_sh_is_executable(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        assert os.access(deploy_sh, os.X_OK)

    def test_deploy_sh_provisions_event_hubs(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert (
            "EventHub" in content
            or "eventhub" in content.lower()
            or "event_hub" in content.lower()
            or "azure_event_hubs" in content.lower()
        )

    def test_deploy_sh_provisions_acr(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert "acr" in content.lower() or "ContainerRegistry" in content

    def test_deploy_sh_uses_emptydir_volumes(self):
        """Deploy uses EmptyDir volumes (Kuzu needs POSIX locks, not Azure Files SMB)."""
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert "EmptyDir" in content or "emptydir" in content.lower()

    def test_deploy_sh_has_container_apps(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert "containerapp" in content.lower() or "Container App" in content

    def test_deploy_sh_defaults_to_one_agent_per_app(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert 'AGENTS_PER_APP="${HIVE_AGENTS_PER_APP:-1}"' in content

    def test_deploy_sh_exposes_distributed_retrieval_toggle(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert (
            'ENABLE_DISTRIBUTED_RETRIEVAL="${HIVE_ENABLE_DISTRIBUTED_RETRIEVAL:-true}"' in content
        )

    def test_deploy_sh_has_cleanup_mode(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert "--cleanup" in content


class TestBicep:
    def test_bicep_exists(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        assert bicep.exists()

    def test_bicep_has_container_apps_env(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "managedEnvironments" in content

    def test_bicep_has_event_hubs(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "EventHub" in content or "eventhub" in content.lower()

    def test_bicep_uses_emptydir_volumes(self):
        """Bicep uses EmptyDir volumes (Kuzu needs POSIX locks, not Azure Files SMB)."""
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "EmptyDir" in content

    def test_bicep_has_container_registry(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "ContainerRegistry" in content

    def test_bicep_has_agent_count_param(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "agentCount" in content

    def test_bicep_has_agents_per_app_param(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "agentsPerApp" in content

    def test_bicep_defaults_to_one_agent_per_app(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "param agentsPerApp int = 1" in content

    def test_bicep_single_agent_packing_uses_high_headroom(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "var perAgentCpu = json(agentsPerApp <= 1 ? '2.0'" in content
        assert "var perAgentMemory = agentsPerApp <= 1 ? '4Gi'" in content

    def test_bicep_references_eh_connection_string(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "AMPLIHACK_EH_CONNECTION_STRING" in content

    def test_bicep_has_distributed_retrieval_toggle(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "enableDistributedRetrieval" in content
        assert "AMPLIHACK_ENABLE_DISTRIBUTED_RETRIEVAL" in content

    def test_bicep_has_shards_hub(self):
        """Bicep must declare hive-shards Event Hub for cross-shard DHT queries."""
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "hive-shards-" in content

    def test_bicep_has_shards_consumer_groups(self):
        """Bicep must declare consumer groups on the shards hub."""
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "ehShardsConsumerGroups" in content

    def test_bicep_has_eval_responses_hub(self):
        """Bicep must declare eval-responses Event Hub for eval answer collection."""
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "eval-responses-" in content

    def test_bicep_no_service_bus(self):
        """Bicep must NOT reference Service Bus — CBS auth fails in Container Apps."""
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "Microsoft.ServiceBus" not in content


class TestShardTransport:
    """Tests for EventHubsShardTransport DI pattern (injected into DistributedHiveGraph)."""

    def test_entrypoint_has_no_sharded_hive_store(self):
        """ShardedHiveStore class must not exist in the updated entrypoint."""
        mod = _load_entrypoint()
        assert not hasattr(mod, "ShardedHiveStore"), (
            "ShardedHiveStore was deleted in v7 DI refactor — should not be present"
        )

    def test_init_dht_hive_exists(self):
        """_init_dht_hive function must exist and return 3 values on success."""
        mod = _load_entrypoint()
        assert hasattr(mod, "_init_dht_hive")
        assert callable(mod._init_dht_hive)

    def test_init_dht_hive_returns_none_without_eh_vars(self):
        """_init_dht_hive returns None when EH env vars are absent (no SB fallback)."""
        mod = _load_entrypoint()
        result = mod._init_dht_hive(
            agent_name="agent-0",
            agent_count=1,
            connection_string="",
            hive_name="test-hive",
            eh_connection_string="",
            eh_name="",
        )
        assert result is None, "Must return None without EH vars — no Service Bus fallback"

    def test_init_dht_hive_uses_configured_shard_timeout(self, monkeypatch):
        """Azure entrypoint should pass the configured shard timeout to EH transport."""
        mod = _load_entrypoint()
        monkeypatch.setenv("AMPLIHACK_SHARD_QUERY_TIMEOUT_SECONDS", "75")

        transport = MagicMock()
        graph = MagicMock()

        with (
            patch(
                "amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph.EventHubsShardTransport",
                return_value=transport,
            ) as mock_transport,
            patch(
                "amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph.DistributedHiveGraph",
                return_value=graph,
            ),
        ):
            result = mod._init_dht_hive(
                agent_name="agent-0",
                agent_count=3,
                connection_string="",
                hive_name="test-hive",
                eh_connection_string="Endpoint=sb://dummy/",
                eh_name="hive-shards-test",
                consumer_group="cg-app-0",
            )

        assert result == (graph, None, transport)
        assert mock_transport.call_args.kwargs["timeout"] == 75.0

    def test_main_exits_when_distributed_topology_requested_but_hive_init_fails(
        self, monkeypatch, tmp_path
    ):
        """Distributed topology must fail fast instead of silently degrading to local-only."""
        mod = _load_entrypoint()

        monkeypatch.setenv("AMPLIHACK_AGENT_NAME", "agent-0")
        monkeypatch.setenv("AMPLIHACK_AGENT_TOPOLOGY", "distributed")
        monkeypatch.setenv("AMPLIHACK_EH_CONNECTION_STRING", "Endpoint=sb://dummy/")
        monkeypatch.setenv("AMPLIHACK_EH_NAME", "hive-shards-test")
        monkeypatch.setenv("AMPLIHACK_MEMORY_STORAGE_PATH", str(tmp_path / "agent-0"))

        with patch.object(mod, "_init_dht_hive", return_value=None):
            with patch(
                "amplihack.agents.goal_seeking.goal_seeking_agent.GoalSeekingAgent",
                return_value=MagicMock(),
            ):
                with patch("amplihack.memory.facade.Memory", return_value=MagicMock()):
                    with patch(
                        "amplihack.agents.goal_seeking.input_source.EventHubsInputSource",
                        return_value=MagicMock(),
                    ):
                        with patch.object(
                            mod,
                            "_run_event_driven_loop",
                            side_effect=AssertionError("distributed startup should fail first"),
                        ):
                            with pytest.raises(SystemExit) as exc_info:
                                mod.main()

        assert exc_info.value.code == 1

    def test_main_skips_hive_init_when_distributed_retrieval_disabled(self, monkeypatch, tmp_path):
        mod = _load_entrypoint()

        monkeypatch.setenv("AMPLIHACK_AGENT_NAME", "agent-0")
        monkeypatch.setenv("AMPLIHACK_EH_CONNECTION_STRING", "Endpoint=sb://dummy/")
        monkeypatch.setenv("AMPLIHACK_EH_NAME", "hive-shards-test")
        monkeypatch.setenv("AMPLIHACK_EH_INPUT_HUB", "hive-events-test")
        monkeypatch.setenv("AMPLIHACK_MEMORY_STORAGE_PATH", str(tmp_path / "agent-0"))
        monkeypatch.setenv("AMPLIHACK_ENABLE_DISTRIBUTED_RETRIEVAL", "false")

        mock_agent = MagicMock()
        mock_agent.memory = MagicMock()
        mock_agent.memory.memory = MagicMock()
        mock_input_source = MagicMock()

        with patch.object(mod, "_init_dht_hive") as init_hive:
            with patch(
                "amplihack.agents.goal_seeking.goal_seeking_agent.GoalSeekingAgent",
                return_value=mock_agent,
            ):
                with patch("amplihack.memory.facade.Memory", return_value=MagicMock()):
                    with patch(
                        "amplihack.agents.goal_seeking.input_source.EventHubsInputSource",
                        return_value=mock_input_source,
                    ):
                        with patch.object(mod, "_run_event_driven_loop", side_effect=SystemExit(0)):
                            with pytest.raises(SystemExit) as exc_info:
                                mod.main()

        assert exc_info.value.code == 0
        init_hive.assert_not_called()

    def test_handle_shard_query_publishes_response(self):
        """EH transport handle_shard_query looks up local shard and publishes SHARD_RESPONSE."""

        from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
            DistributedHiveGraph,
            EventHubsShardTransport,
        )
        from amplihack.agents.goal_seeking.hive_mind.event_bus import BusEvent
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import HiveFact

        # Use _start_receiving=False to skip background EH consumer thread
        transport_0 = EventHubsShardTransport(
            connection_string="dummy://",
            eventhub_name="hive-shards",
            agent_id="agent-0",
            _start_receiving=False,
        )
        transport_req = EventHubsShardTransport(
            connection_string="dummy://",
            eventhub_name="hive-shards",
            agent_id="requester",
            _start_receiving=False,
        )

        graph = DistributedHiveGraph(
            hive_id="test-e-hq", enable_gossip=False, transport=transport_0
        )
        graph.register_agent("agent-0")
        graph.promote_fact(
            "agent-0",
            HiveFact(
                fact_id="",
                content="Paris is the capital of France",
                concept="geography",
                confidence=0.9,
                source_agent="agent-0",
                tags=["geo"],
                created_at=0.0,
            ),
        )

        # Intercept _publish calls and inject into requester's mailbox
        published: list[dict] = []

        def mock_publish(payload, partition_key=None):
            published.append(payload)
            evt = BusEvent(
                event_id=payload.get("event_id", ""),
                event_type=payload["event_type"],
                source_agent=payload.get("source_agent", ""),
                timestamp=payload.get("timestamp", 0.0),
                payload=payload["payload"],
            )
            with transport_req._mailbox_lock:
                transport_req._mailbox.append(evt)
            transport_req._mailbox_ready.set()

        transport_0._publish = mock_publish
        search_agent = MagicMock()
        search_agent.memory.search_local.return_value = [
            {
                "experience_id": "paris-fact",
                "context": "geography",
                "outcome": "Paris is the capital of France",
                "confidence": 0.9,
                "tags": ["geo"],
            }
        ]
        transport_0.bind_agent(search_agent)

        event = MagicMock()
        event.payload = {
            "query": "capital France",
            "limit": 5,
            "correlation_id": "corr-1",
            "target_agent": "agent-0",
        }
        transport_0.handle_shard_query(event, agent=search_agent)

        with transport_req._mailbox_lock:
            responses = [e for e in transport_req._mailbox if e.event_type == "SHARD_RESPONSE"]
        assert len(responses) == 1
        assert responses[0].payload["correlation_id"] == "corr-1"
        assert any("Paris" in f["content"] for f in responses[0].payload["facts"])

    def test_handle_shard_response_wakes_pending_query(self):
        """EH transport handle_shard_response signals threading.Event."""
        from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
            EventHubsShardTransport,
        )

        transport = EventHubsShardTransport(
            connection_string="dummy://",
            eventhub_name="hive-shards",
            agent_id="agent-0",
            _start_receiving=False,
        )

        done_event = threading.Event()
        results = []
        with transport._pending_lock:
            transport._pending["corr-2"] = (done_event, results)

        event = MagicMock()
        event.payload = {
            "correlation_id": "corr-2",
            "facts": [{"content": "test fact", "confidence": 0.9}],
        }
        transport.handle_shard_response(event)

        assert done_event.is_set()
        assert len(results) == 1
        assert results[0]["content"] == "test fact"

    def test_promote_fact_stores_locally_no_publish(self):
        """promote_fact stores in local shard only — no EH publish."""
        from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
            DistributedHiveGraph,
            EventHubsShardTransport,
        )
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import HiveFact

        transport = EventHubsShardTransport(
            connection_string="dummy://",
            eventhub_name="hive-shards",
            agent_id="agent-0",
            _start_receiving=False,
        )
        published: list[dict] = []
        transport._publish = lambda payload, partition_key=None: published.append(payload)

        graph = DistributedHiveGraph(
            hive_id="test-promote-local", enable_gossip=False, transport=transport
        )
        graph.register_agent("agent-0")

        graph.promote_fact(
            "agent-0",
            HiveFact(
                fact_id="",
                content="Local fact no replication",
                concept="test",
                confidence=0.8,
                source_agent="agent-0",
                tags=[],
                created_at=0.0,
            ),
        )

        assert published == [], "Local store must not publish to EH"


class TestShardQueryListener:
    """Tests for the background _shard_query_listener thread (DI pattern).

    The listener takes a transport (EventHubsShardTransport) injected via DI.
    """

    def test_listener_exits_on_shutdown(self):
        """Listener thread exits when shutdown_event is set."""
        mod = _load_entrypoint()

        mock_transport = MagicMock()
        mock_bus = MagicMock()
        mock_bus.poll.return_value = []

        shutdown = threading.Event()
        shutdown.set()  # Immediately signal shutdown

        # Should exit quickly without hanging
        mod._shard_query_listener(mock_transport, "agent-0", mock_bus, shutdown)

    def test_listener_handles_shard_query_events(self):
        """Listener dispatches SHARD_QUERY events to transport.handle_shard_query."""
        mod = _load_entrypoint()

        from amplihack.agents.goal_seeking.hive_mind.event_bus import make_event

        query_event = make_event(
            event_type="SHARD_QUERY",
            source_agent="requester",
            payload={"query": "test", "limit": 5, "correlation_id": "corr-x"},
        )

        call_count = [0]
        mock_transport = MagicMock()
        mock_bus = MagicMock()
        mock_bus.poll.side_effect = lambda _: [query_event] if call_count[0] == 0 else []

        shutdown = threading.Event()

        def stop():
            time.sleep(0.05)
            shutdown.set()

        t = threading.Thread(target=stop)
        t.start()

        mod._shard_query_listener(mock_transport, "agent-0", mock_bus, shutdown)
        t.join()

        mock_transport.handle_shard_query.assert_called()

    def test_listener_handles_shard_response_events(self):
        """Listener dispatches SHARD_RESPONSE events to transport.handle_shard_response."""
        mod = _load_entrypoint()

        from amplihack.agents.goal_seeking.hive_mind.event_bus import make_event

        response_event = make_event(
            event_type="SHARD_RESPONSE",
            source_agent="agent-1",
            payload={"correlation_id": "corr-y", "facts": []},
        )

        mock_transport = MagicMock()
        mock_bus = MagicMock()
        call_count = [0]

        def poll_side_effect(_):
            call_count[0] += 1
            if call_count[0] == 1:
                return [response_event]
            return []

        mock_bus.poll.side_effect = poll_side_effect

        shutdown = threading.Event()

        def stop():
            time.sleep(0.05)
            shutdown.set()

        t = threading.Thread(target=stop)
        t.start()

        mod._shard_query_listener(mock_transport, "agent-0", mock_bus, shutdown)
        t.join()

        mock_transport.handle_shard_response.assert_called()


# ---------------------------------------------------------------------------
# Question propagation: original question string reaches query_facts unchanged
# ---------------------------------------------------------------------------


class TestQuestionPropagationEndToEnd:
    """Regression guards for ingress question propagation in the Azure entrypoint."""

    def test_extract_input_text_preserves_original_question(self) -> None:
        """_extract_input_text('INPUT', {'question': q}) returns q unchanged."""
        mod = _load_entrypoint()
        original_question = "What animal facts are known?"

        result = mod._extract_input_text(
            "INPUT",
            {"question": original_question},
            {},
        )
        assert result == original_question, (
            f"_extract_input_text returned {result!r}, expected {original_question!r}"
        )

    def test_handle_input_event_delivers_question_to_agent_process(self) -> None:
        """INPUT event with payload.question delivers the original question to agent.process().

        Regression guard for the ingress INPUT event path:
          _handle_event(INPUT event) → _extract_input_text → agent.process(original_question)

        The question must reach agent.process() verbatim — no mutation or transformation
        by the event dispatch layer.
        """
        mod = _load_entrypoint()
        mock_mem = MagicMock()
        mock_agent = MagicMock()
        mock_agent.process.return_value = "answer"

        original_question = "What animal facts are known?"
        input_event = {
            "event_type": "INPUT",
            "payload": {"question": original_question},
        }
        mod._handle_event("agent", input_event, mock_mem, mock_agent)

        mock_agent.process.assert_called_once_with(original_question)
        mock_mem.recall.assert_not_called()
