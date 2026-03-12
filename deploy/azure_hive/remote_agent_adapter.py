"""RemoteAgentAdapter — makes a deployed Azure Container Apps agent look like a local agent.

Implements the same interface as LearningAgent (learn_from_content, answer_question)
so it can be passed directly to LongHorizonMemoryEval.run(). The eval harness
uses the exact same code path for local and distributed agents.

Content is partitioned round-robin across agents (each agent learns N/agent_count turns).
Questions are targeted to specific agents via target_agent field.
Answers are collected from the eval-responses Event Hub, correlated by event_id.

v2: Fully migrated from Service Bus to Azure Event Hubs (CBS-free AMQP transport).
    - learn_from_content / answer_question publish via EventHubProducerClient
    - _listen_for_answers consumes from eval-responses hub via EventHubConsumerClient
    - _wait_for_agents_idle uses a time-based wait (EH has no direct queue-depth API)
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
        eh_connection_string: str,
        input_hub: str,
        response_hub: str,
        agent_count: int = 100,
        resource_group: str = "",
    ) -> None:
        from azure.eventhub import EventHubProducerClient  # type: ignore[import-unresolved]

        self._eh_connection_string = eh_connection_string
        self._input_hub = input_hub
        self._response_hub = response_hub
        self._resource_group = resource_group
        self._agent_count = agent_count

        self._learn_count = 0
        self._question_count = 0
        self._shutdown = threading.Event()
        self._idle_wait_done = threading.Event()

        self._counter_lock = threading.Lock()
        self._answer_lock = threading.Lock()

        # EH producer for sending learn/question events
        self._producer = EventHubProducerClient.from_connection_string(
            eh_connection_string,
            eventhub_name=input_hub,
        )
        self._producer_lock = threading.Lock()

        # Pending answers: event_id -> answer text
        self._pending_answers: dict[str, str] = {}
        self._answer_events: dict[str, threading.Event] = {}

        self._listener_alive = threading.Event()
        self._listener_thread = threading.Thread(target=self._listen_for_answers, daemon=True)
        self._listener_thread.start()

        if not self._listener_alive.wait(timeout=30):
            raise RuntimeError(
                f"Failed to connect to response hub {response_hub}/cg-eval-reader. "
                "Check that the hub and consumer group exist."
            )

        logger.info(
            "RemoteAgentAdapter: input=%s response=%s agents=%d",
            input_hub,
            response_hub,
            agent_count,
        )

    def _send(self, payload: dict[str, Any], partition_key: str) -> None:
        """Publish a JSON event to the input Event Hub."""
        from azure.eventhub import EventData  # type: ignore[import-unresolved]

        with self._producer_lock:
            batch = self._producer.create_batch(partition_key=partition_key)
            batch.add(EventData(json.dumps(payload)))
            self._producer.send_batch(batch)

    def learn_from_content(self, content: str) -> dict[str, Any]:
        """Send content to one agent (round-robin partition).

        5000 turns / 100 agents = 50 turns each. Each agent learns its
        partition locally. The hive mind shares knowledge between agents
        so any agent can answer questions about any content.
        """
        event_id = uuid.uuid4().hex[:12]
        with self._counter_lock:
            target_agent = self._learn_count % self._agent_count
            self._learn_count += 1
            learn_count = self._learn_count
        target_name = f"agent-{target_agent}"

        self._send(
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
                learn_count // self._agent_count,
            )

        return {"facts_stored": 1, "event_id": event_id}

    def answer_question(self, question: str) -> str:
        """Send question to one agent, wait for answer. No timeout."""
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

        answer_event = threading.Event()
        with self._answer_lock:
            self._answer_events[event_id] = answer_event

        self._send(
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

        answer_event.wait()

        with self._answer_lock:
            answer = self._pending_answers.pop(event_id, "No answer received")
            self._answer_events.pop(event_id, None)

        return answer

    def _wait_for_agents_idle(self) -> None:
        """Wait for agents to finish processing content.

        EH does not have a direct queue-depth API like Service Bus.
        Strategy: wait a proportional delay based on content volume,
        then optionally poll partition properties for lull detection.
        Operators can tune AMPLIHACK_IDLE_WAIT_SECS env var.
        """
        import os

        turns_per_agent = self._learn_count // max(1, self._agent_count)
        default_wait = max(30, turns_per_agent * 2)
        wait_secs = int(os.environ.get("AMPLIHACK_IDLE_WAIT_SECS", str(default_wait)))

        logger.info(
            "Waiting %ds for agents to process %d content turns (%d per agent). "
            "Set AMPLIHACK_IDLE_WAIT_SECS to override.",
            wait_secs,
            self._learn_count,
            turns_per_agent,
        )
        time.sleep(wait_secs)
        logger.info("Agent idle wait complete. Starting question phase.")

    def _listen_for_answers(self) -> None:
        """Background thread: collect answers from eval-responses Event Hub."""
        try:
            from azure.eventhub import EventHubConsumerClient  # type: ignore[import-unresolved]

            consumer = EventHubConsumerClient.from_connection_string(
                self._eh_connection_string,
                consumer_group="cg-eval-reader",
                eventhub_name=self._response_hub,
            )
        except Exception as e:
            logger.error("RemoteAgentAdapter: failed to connect to response hub: %s", e)
            return

        self._listener_alive.set()
        logger.info("RemoteAgentAdapter: listening on %s/cg-eval-reader", self._response_hub)

        def _on_event(partition_context, event) -> None:
            if event is None or self._shutdown.is_set():
                return
            try:
                body = json.loads(event.body_as_str())
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
                partition_context.update_checkpoint(event)
            except Exception:
                logger.debug("Failed to parse response message", exc_info=True)

        try:
            consumer.receive(on_event=_on_event, starting_position="-1")
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
        try:
            self._producer.close()
        except Exception:
            pass
        if self._listener_thread.is_alive():
            self._listener_thread.join(timeout=5)
