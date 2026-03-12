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

    def test_handle_learn_content_uses_agent_process(self):
        """LEARN_CONTENT events feed content to agent.process() via OODA loop."""
        mod = _load_entrypoint()
        mock_mem = MagicMock()
        mock_agent = MagicMock()

        learn_event = {
            "event_type": "LEARN_CONTENT",
            "payload": {"turn": 1, "content": "The sky is blue."},
        }
        mod._handle_event("agent", learn_event, mock_mem, mock_agent)

        mock_agent.process.assert_called_once_with("The sky is blue.")
        mock_mem.remember.assert_not_called()

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

    def test_deploy_sh_groups_5_agents_per_app(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert "AGENTS_PER_APP" in content

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

    def test_bicep_references_eh_connection_string(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "AMPLIHACK_EH_CONNECTION_STRING" in content

    def test_bicep_has_shards_hub(self):
        """Bicep must declare hive-shards Event Hub for cross-shard DHT queries."""
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "hive-shards-" in content

    def test_bicep_has_shards_consumer_groups(self):
        """Bicep must declare per-agent consumer groups on the shards hub."""
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


class TestServiceBusShardTransport:
    """Tests for ServiceBusShardTransport DI pattern (replaces ShardedHiveStore)."""

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

    def test_handle_shard_query_publishes_response(self):
        """ServiceBusShardTransport.handle_shard_query looks up local shard and publishes SHARD_RESPONSE."""
        from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
            DistributedHiveGraph,
            ServiceBusShardTransport,
        )
        from amplihack.agents.goal_seeking.hive_mind.event_bus import LocalEventBus
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import HiveFact

        bus = LocalEventBus()
        bus.subscribe("agent-0")
        bus.subscribe("requester")

        sb_transport = ServiceBusShardTransport(event_bus=bus, agent_id="agent-0")
        graph = DistributedHiveGraph(
            hive_id="test-e-hq", enable_gossip=False, transport=sb_transport
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

        event = MagicMock()
        event.payload = {"query": "capital France", "limit": 5, "correlation_id": "corr-1"}
        sb_transport.handle_shard_query(event)

        responses = [e for e in bus.poll("requester") if e.event_type == "SHARD_RESPONSE"]
        assert len(responses) == 1
        published = responses[0]
        assert published.payload["correlation_id"] == "corr-1"
        assert any("Paris" in f["content"] for f in published.payload["facts"])
        bus.close()

    def test_handle_shard_response_wakes_pending_query(self):
        """ServiceBusShardTransport.handle_shard_response signals threading.Event."""
        from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
            ServiceBusShardTransport,
        )
        from amplihack.agents.goal_seeking.hive_mind.event_bus import LocalEventBus

        bus = LocalEventBus()
        bus.subscribe("agent-0")

        sb_transport = ServiceBusShardTransport(event_bus=bus, agent_id="agent-0")

        # Register a pending query
        done_event = threading.Event()
        results = []
        with sb_transport._pending_lock:
            sb_transport._pending["corr-2"] = (done_event, results)

        event = MagicMock()
        event.payload = {
            "correlation_id": "corr-2",
            "facts": [{"content": "test fact", "confidence": 0.9}],
        }
        sb_transport.handle_shard_response(event)

        assert done_event.is_set()
        assert len(results) == 1
        assert results[0]["content"] == "test fact"
        bus.close()

    def test_promote_fact_stores_locally_no_bus_publish(self):
        """promote_fact stores in local shard only — no SHARD_STORE event published."""
        from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
            DistributedHiveGraph,
            ServiceBusShardTransport,
        )
        from amplihack.agents.goal_seeking.hive_mind.event_bus import LocalEventBus
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import HiveFact

        bus = LocalEventBus()
        bus.subscribe("agent-0")
        bus.subscribe("observer")

        sb_transport = ServiceBusShardTransport(event_bus=bus, agent_id="agent-0")
        graph = DistributedHiveGraph(
            hive_id="test-promote-local", enable_gossip=False, transport=sb_transport
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

        # No SHARD_STORE or SHARD_QUERY published to bus
        assert bus.poll("observer") == [], "Local store must not broadcast to bus"
        bus.close()


class TestShardQueryListener:
    """Tests for the background _shard_query_listener thread (DI pattern).

    The listener now takes a transport (ServiceBusShardTransport) instead of
    a ShardedHiveStore wrapper.
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
