"""RemoteAgentAdapter — makes a deployed Azure Container Apps agent look like a local agent.

Implements the same interface as LearningAgent (learn_from_content, answer_question)
so it can be passed directly to LongHorizonMemoryEval.run(). The eval harness
uses the exact same code path for local and distributed agents.

Transport: Azure Event Hubs (CBS-free AMQP — works reliably in Container Apps).
  - learn_from_content() sends LEARN_CONTENT events via EH producer,
    partition_key=target_agent for consistent routing.
  - answer_question() sends INPUT events via EH producer,
    waits for EVAL_ANSWER on the eval-responses Event Hub.
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

        # Unique run_id to filter stale events from previous eval runs
        self._run_id = uuid.uuid4().hex[:12]

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

    def _publish_event(self, payload: dict, partition_key: str) -> None:
        """Publish a single JSON event to the input Event Hub."""
        from azure.eventhub import (  # type: ignore[import-unresolved]
            EventData,
            EventHubProducerClient,
        )

        payload["run_id"] = self._run_id

        producer = EventHubProducerClient.from_connection_string(
            self._connection_string, eventhub_name=self._input_hub
        )
        try:
            with producer:
                batch = producer.create_batch(partition_key=partition_key)
                batch.add(EventData(json.dumps(payload)))
                producer.send_batch(batch)
        except Exception:
            logger.warning("EH publish failed, retrying once", exc_info=True)
            # One retry with a fresh producer
            producer2 = EventHubProducerClient.from_connection_string(
                self._connection_string, eventhub_name=self._input_hub
            )
            with producer2:
                batch = producer2.create_batch(partition_key=partition_key)
                batch.add(EventData(json.dumps(payload)))
                producer2.send_batch(batch)

    def learn_from_content(self, content: str) -> dict[str, Any]:
        """Send content to one agent (round-robin partition).

        5000 turns / N agents = ~(5000/N) turns each. Each agent learns its
        partition locally. The hive mind shares knowledge between agents
        so any agent can answer questions about any content.
        """
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
        logger.info(
            "Sending FEED_COMPLETE to all %d agents (%d content turns each)...",
            self._agent_count,
            self._learn_count // max(1, self._agent_count),
        )

        # Reset ready tracking
        with self._ready_lock:
            self._ready_agents.clear()
            self._all_agents_ready.clear()

        # Send FEED_COMPLETE to each agent
        for i in range(self._agent_count):
            target_name = f"agent-{i}"
            self._publish_event(
                {
                    "event_type": "FEED_COMPLETE",
                    "event_id": uuid.uuid4().hex[:12],
                    "target_agent": target_name,
                    "source_agent": "eval-harness",
                    "payload": {
                        "total_turns": self._learn_count // max(1, self._agent_count),
                        "target_agent": target_name,
                    },
                },
                partition_key=target_name,
            )

        logger.info(
            "Waiting for %d AGENT_READY events on '%s'...",
            self._agent_count,
            self._response_hub,
        )

        # Wait for all agents to report ready (no timeout — eval is not time-bound)
        poll_interval = 15
        while True:
            with self._ready_lock:
                ready_count = len(self._ready_agents)
            if ready_count >= self._agent_count:
                logger.info("All %d agents ready. Starting question phase.", self._agent_count)
                return
            logger.info("  %d/%d agents ready, waiting...", ready_count, self._agent_count)
            time.sleep(poll_interval)

    def _listen_for_answers(self) -> None:
        """Background thread: collect EVAL_ANSWER and AGENT_READY events from eval-responses hub."""
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
