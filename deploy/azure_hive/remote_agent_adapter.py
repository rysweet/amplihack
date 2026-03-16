"""RemoteAgentAdapter — makes a deployed Azure Container Apps agent look like a local agent.

Implements the same interface as LearningAgent (learn_from_content, answer_question)
so it can be passed directly to LongHorizonMemoryEval.run(). The eval harness
uses the exact same code path for local and distributed agents.

Transport: Azure Event Hubs (CBS-free AMQP — works reliably in Container Apps).
  - learn_from_content() sends LEARN_CONTENT events via EH producer,
    routed to the target agent's deterministic partition.
  - answer_question() sends INPUT events via EH producer,
    waits for EVAL_ANSWER on the eval-responses Event Hub.
  - learn_from_content() first pings all agents with ONLINE_CHECK so feed
    content is not published before every target agent is actually listening.
  - _wait_for_agents_idle() sends FEED_COMPLETE to all agents and waits
    for N AGENT_READY events on the eval-responses hub.

Content is partitioned round-robin across agents (each agent learns N/agent_count turns).
Questions are targeted to specific agents via target_agent field.
Answers are collected from the eval-responses Event Hub, correlated by event_id.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class RemoteAgentAdapter:
    """Adapter that forwards learn/answer calls to deployed agents via Event Hubs."""

    def __init__(
        self,
        connection_string: str,
        input_hub: str,
        response_hub: str,
        agent_count: int = 100,
        resource_group: str = "",
        answer_timeout: int = 0,
    ) -> None:
        self._connection_string = connection_string
        self._input_hub = input_hub
        self._response_hub = response_hub
        self._resource_group = resource_group
        self._agent_count = agent_count

        self._learn_count = 0
        self._question_count = 0
        self._answer_timeout = answer_timeout
        self._shutdown = threading.Event()
        self._startup_wait_done = threading.Event()
        self._idle_wait_done = threading.Event()

        # Thread safety for counters and answer dict
        self._counter_lock = threading.Lock()
        self._answer_lock = threading.Lock()

        # Pending answers: event_id -> answer text
        self._pending_answers: dict[str, str] = {}
        self._answer_events: dict[str, threading.Event] = {}

        # AGENT_READY tracking for _wait_for_agents_idle
        self._ready_agents: set[str] = set()
        self._ready_lock = threading.Lock()
        self._all_agents_ready = threading.Event()

        # AGENT_ONLINE tracking for pre-feed startup synchronization
        self._online_agents: set[str] = set()
        self._online_lock = threading.Lock()
        self._all_agents_online = threading.Event()

        # Unique run_id to filter stale events from previous eval runs
        self._run_id = uuid.uuid4().hex[:12]
        self._num_partitions: int | None = None

        # Listener liveness flag — fail fast if listener can't connect
        self._listener_alive = threading.Event()

        self._listener_thread = threading.Thread(target=self._listen_for_answers, daemon=True)
        self._listener_thread.start()

        # Wait up to 30s for listener to connect
        if not self._listener_alive.wait(timeout=30):
            raise RuntimeError(
                f"Failed to connect to response hub '{response_hub}'. "
                "Check that the Event Hub and consumer group 'eval-reader' exist."
            )

        logger.info(
            "RemoteAgentAdapter: input=%s response=%s agents=%d run_id=%s",
            input_hub,
            response_hub,
            agent_count,
            self._run_id,
        )

    @staticmethod
    def _agent_index(agent_id: str) -> int:
        """Extract numeric index from ``agent-N`` names."""
        try:
            return int(agent_id.rsplit("-", 1)[-1])
        except (ValueError, IndexError):
            return abs(hash(agent_id))

    def _get_num_partitions(self) -> int:
        """Return the input hub partition count, caching the first result."""
        if self._num_partitions is not None:
            return self._num_partitions
        try:
            from azure.eventhub import EventHubConsumerClient  # type: ignore[import-unresolved]

            consumer = EventHubConsumerClient.from_connection_string(
                self._connection_string,
                consumer_group="$Default",
                eventhub_name=self._input_hub,
            )
            self._num_partitions = len(consumer.get_partition_ids())
            consumer.close()
        except Exception:
            self._num_partitions = 32
        return self._num_partitions

    def _target_partition(self, agent_id: str) -> str:
        """Deterministic partition for an agent: agent_index % num_partitions."""
        return str(self._agent_index(agent_id) % self._get_num_partitions())

    def _publish_event(self, payload: dict, partition_key: str) -> None:
        """Publish a single JSON event to the input Event Hub."""
        from azure.eventhub import (  # type: ignore[import-unresolved]
            EventData,
            EventHubProducerClient,
        )

        payload["run_id"] = self._run_id
        route_partition_id: str | None = None
        if partition_key.startswith("agent-"):
            route_partition_id = self._target_partition(partition_key)

        producer = EventHubProducerClient.from_connection_string(
            self._connection_string, eventhub_name=self._input_hub
        )
        try:
            with producer:
                kwargs: dict[str, str] = {}
                if route_partition_id is not None:
                    kwargs["partition_id"] = route_partition_id
                else:
                    kwargs["partition_key"] = partition_key
                batch = producer.create_batch(**kwargs)
                batch.add(EventData(json.dumps(payload)))
                producer.send_batch(batch)
        except Exception:
            logger.warning("EH publish failed, retrying once", exc_info=True)
            producer2 = EventHubProducerClient.from_connection_string(
                self._connection_string, eventhub_name=self._input_hub
            )
            try:
                with producer2:
                    kwargs: dict[str, str] = {}
                    if route_partition_id is not None:
                        kwargs["partition_id"] = route_partition_id
                    else:
                        kwargs["partition_key"] = partition_key
                    batch = producer2.create_batch(**kwargs)
                    batch.add(EventData(json.dumps(payload)))
                    producer2.send_batch(batch)
            except Exception:
                logger.error(
                    "EH publish failed after retry (event_type=%s)",
                    payload.get("event_type", "?"),
                    exc_info=True,
                )
                raise

    def _wait_for_agents_online(self) -> None:
        """Wait until every target agent acknowledges ONLINE_CHECK.

        This prevents the eval feed from starting while some agents are still
        booting and not yet consuming their assigned Event Hubs partitions.
        """
        logger.info(
            "Sending ONLINE_CHECK to all %d agents before feed phase...",
            self._agent_count,
        )

        with self._online_lock:
            self._online_agents.clear()
            self._all_agents_online.clear()

        poll_interval = 10
        while True:
            with self._online_lock:
                missing_agents = [
                    f"agent-{i}"
                    for i in range(self._agent_count)
                    if f"agent-{i}" not in self._online_agents
                ]
                online_count = self._agent_count - len(missing_agents)

            if not missing_agents:
                logger.info("All %d agents online. Starting feed phase.", self._agent_count)
                return

            for target_name in missing_agents:
                self._publish_event(
                    {
                        "event_type": "ONLINE_CHECK",
                        "event_id": uuid.uuid4().hex[:12],
                        "target_agent": target_name,
                        "source_agent": "eval-harness",
                        "payload": {"target_agent": target_name},
                    },
                    partition_key=target_name,
                )

            logger.info(
                "  %d/%d agents online, pinging missing agents: %s",
                online_count,
                self._agent_count,
                ", ".join(missing_agents),
            )
            time.sleep(poll_interval)

    def learn_from_content(self, content: str) -> dict[str, Any]:
        """Send content to one agent (round-robin partition).

        5000 turns / N agents = ~(5000/N) turns each. Each agent learns its
        partition locally. The hive mind shares knowledge between agents
        so any agent can answer questions about any content.
        """
        if not self._startup_wait_done.is_set():
            with self._counter_lock:
                if not self._startup_wait_done.is_set():
                    self._wait_for_agents_online()
                    self._startup_wait_done.set()

        event_id = uuid.uuid4().hex[:12]
        with self._counter_lock:
            target_agent = self._learn_count % self._agent_count
            self._learn_count += 1
            learn_count = self._learn_count
        target_name = f"agent-{target_agent}"

        self._publish_event(
            {
                "event_type": "LEARN_CONTENT",
                "event_id": event_id,
                "target_agent": target_name,
                "source_agent": "eval-harness",
                "payload": {
                    "content": content,
                    "target_agent": target_name,
                },
            },
            partition_key=target_name,
        )

        if learn_count % 500 == 0:
            logger.info(
                "RemoteAgentAdapter: sent %d content turns (%d per agent)",
                learn_count,
                learn_count // max(1, self._agent_count),
            )

        return {"facts_stored": 1, "event_id": event_id}

    def answer_question(self, question: str) -> str:
        """Send question to one agent, wait for answer. No timeout."""
        # Wait for agents to finish processing content (blocks all threads)
        if self._learn_count > 0 and not self._idle_wait_done.is_set():
            with self._counter_lock:
                if not self._idle_wait_done.is_set():
                    self._wait_for_agents_idle()
                    self._idle_wait_done.set()

        with self._counter_lock:
            target_agent = self._question_count % self._agent_count
            self._question_count += 1

        event_id = uuid.uuid4().hex[:12]
        target_name = f"agent-{target_agent}"

        # Register signal before sending
        answer_event = threading.Event()
        with self._answer_lock:
            self._answer_events[event_id] = answer_event

        self._publish_event(
            {
                "event_type": "INPUT",
                "event_id": event_id,
                "target_agent": target_name,
                "source_agent": "eval-harness",
                "payload": {
                    "question": question,
                    "question_id": f"q_{target_agent}_{event_id}",
                    "target_agent": target_name,
                },
            },
            partition_key=target_name,
        )

        logger.info(
            "RemoteAgentAdapter: sent question to %s (event_id=%s): %s",
            target_name,
            event_id,
            question[:60],
        )

        timeout = self._answer_timeout if self._answer_timeout > 0 else None
        got_answer = answer_event.wait(timeout=timeout)
        if not got_answer:
            logger.warning(
                "answer_question: timeout after %ds waiting for event_id=%s",
                self._answer_timeout,
                event_id,
            )

        with self._answer_lock:
            answer = self._pending_answers.pop(event_id, "No answer received")
            self._answer_events.pop(event_id, None)

        return answer

    def _wait_for_agents_idle(self) -> None:
        """Wait for all agents to finish processing content.

        Sends FEED_COMPLETE to every agent, then waits for each to publish
        AGENT_READY on the eval-responses hub.  Event-driven — no polling.
        """
        turns_per_agent = self._learn_count // max(1, self._agent_count)
        logger.info(
            "Sending FEED_COMPLETE to all %d agents (%d content turns each)...",
            self._agent_count,
            turns_per_agent,
        )

        # Reset ready tracking
        with self._ready_lock:
            self._ready_agents.clear()
            self._all_agents_ready.clear()

        logger.info(
            "Waiting for %d AGENT_READY events on '%s'...",
            self._agent_count,
            self._response_hub,
        )

        # Wait for all agents to report ready (no timeout — eval is not time-bound)
        poll_interval = 15
        while True:
            with self._ready_lock:
                missing_agents = [
                    f"agent-{i}"
                    for i in range(self._agent_count)
                    if f"agent-{i}" not in self._ready_agents
                ]
                ready_count = self._agent_count - len(missing_agents)
            if ready_count >= self._agent_count:
                logger.info("All %d agents ready. Starting question phase.", self._agent_count)
                return

            for target_name in missing_agents:
                self._publish_event(
                    {
                        "event_type": "FEED_COMPLETE",
                        "event_id": uuid.uuid4().hex[:12],
                        "target_agent": target_name,
                        "source_agent": "eval-harness",
                        "payload": {
                            "total_turns": turns_per_agent,
                            "target_agent": target_name,
                        },
                    },
                    partition_key=target_name,
                )

            logger.info(
                "  %d/%d agents ready, re-sent FEED_COMPLETE to: %s",
                ready_count,
                self._agent_count,
                ", ".join(missing_agents),
            )
            time.sleep(poll_interval)

    def _listen_for_answers(self) -> None:
        """Background thread: collect eval lifecycle and answer events."""
        try:
            from azure.eventhub import EventHubConsumerClient  # type: ignore[import-unresolved]
        except ImportError:
            logger.error("azure-eventhub not installed — RemoteAgentAdapter cannot receive answers")
            return

        def _on_event(partition_context: Any, event: Any) -> None:
            if event is None:
                return
            try:
                body = json.loads(event.body_as_str())
                event_type = body.get("event_type", "")

                # Filter stale events from previous eval runs
                run_id = body.get("run_id", "")
                if run_id and run_id != self._run_id:
                    return

                if event_type == "AGENT_ONLINE":
                    agent_id = body.get("agent_id", "")
                    if agent_id:
                        with self._online_lock:
                            self._online_agents.add(agent_id)
                            online_count = len(self._online_agents)
                        logger.info(
                            "RemoteAgentAdapter: AGENT_ONLINE from %s (%d/%d)",
                            agent_id,
                            online_count,
                            self._agent_count,
                        )
                    if hasattr(partition_context, "update_checkpoint"):
                        partition_context.update_checkpoint(event)
                    return

                if event_type == "AGENT_READY":
                    agent_id = body.get("agent_id", "")
                    if agent_id:
                        with self._ready_lock:
                            self._ready_agents.add(agent_id)
                            ready_count = len(self._ready_agents)
                        logger.info(
                            "RemoteAgentAdapter: AGENT_READY from %s (%d/%d)",
                            agent_id,
                            ready_count,
                            self._agent_count,
                        )
                    if hasattr(partition_context, "update_checkpoint"):
                        partition_context.update_checkpoint(event)
                    return

                if event_type == "EVAL_ANSWER":
                    event_id = body.get("event_id", "")
                    answer = body.get("answer", "")

                    with self._answer_lock:
                        if event_id in self._answer_events:
                            self._pending_answers[event_id] = answer
                            self._answer_events[event_id].set()
                            logger.info(
                                "RemoteAgentAdapter: got answer for %s from %s: %s",
                                event_id,
                                body.get("agent_id", "?"),
                                answer[:80] if answer else "(empty)",
                            )
                        else:
                            logger.warning(
                                "RemoteAgentAdapter: answer for unknown event_id=%s (stale?)",
                                event_id,
                            )

                if hasattr(partition_context, "update_checkpoint"):
                    partition_context.update_checkpoint(event)
            except Exception:
                logger.debug("Failed to parse response message", exc_info=True)

        consumer = EventHubConsumerClient.from_connection_string(
            self._connection_string,
            consumer_group="eval-reader",
            eventhub_name=self._response_hub,
        )
        self._listener_alive.set()
        logger.info("RemoteAgentAdapter: listening on '%s' (eval-reader)", self._response_hub)

        try:
            consumer.receive(on_event=_on_event, starting_position="@latest")
        except Exception:
            if not self._shutdown.is_set():
                logger.debug("Response listener error", exc_info=True)
        finally:
            try:
                consumer.close()
            except Exception:
                pass

    def get_memory_stats(self) -> dict[str, Any]:
        """Return adapter stats."""
        return {
            "adapter": "remote",
            "learn_count": self._learn_count,
            "question_count": self._question_count,
            "agent_count": self._agent_count,
        }

    def close(self) -> None:
        """Clean up Event Hubs connections."""
        self._shutdown.set()
        if self._listener_thread.is_alive():
            self._listener_thread.join(timeout=5)
