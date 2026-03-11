"""RemoteAgentAdapter — makes a deployed Azure Container Apps agent look like a local agent.

Implements the same interface as LearningAgent (learn_from_content, answer_question)
so it can be passed directly to LongHorizonMemoryEval.run(). The eval harness
uses the exact same code path for local and distributed agents.

Content is partitioned round-robin across agents (each agent learns N/agent_count turns).
Questions are targeted to specific agents via target_agent field.
Answers are collected from the eval-responses Service Bus topic, correlated
by event_id via the GoalSeekingAgent.on_answer callback.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import threading
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class RemoteAgentAdapter:
    """Adapter that forwards learn/answer calls to deployed agents via Service Bus."""

    def __init__(
        self,
        connection_string: str,
        input_topic: str,
        response_topic: str,
        agent_count: int = 100,
        resource_group: str = "",
        idle_wait_timeout: int = 0,
        answer_timeout: int = 120,
    ) -> None:
        from azure.servicebus import ServiceBusClient

        self._input_topic = input_topic
        self._response_topic = response_topic
        self._resource_group = resource_group
        self._agent_count = agent_count

        # Extract SB namespace from connection string
        ns_match = re.search(r'Endpoint=sb://([^.]+)\.', connection_string)
        self._sb_namespace = ns_match.group(1) if ns_match else ""

        self._learn_count = 0
        self._question_count = 0
        self._idle_wait_timeout = idle_wait_timeout  # 0 means no timeout
        self._answer_timeout = answer_timeout  # seconds to wait per answer (0 = no timeout)
        self._shutdown = threading.Event()
        self._idle_wait_done = threading.Event()  # Signals all threads that content processing is complete

        # Thread safety for counters and answer dict
        self._counter_lock = threading.Lock()
        self._answer_lock = threading.Lock()

        if not resource_group:
            raise ValueError("resource_group is required for queue depth polling")

        # Service Bus client
        self._client = ServiceBusClient.from_connection_string(connection_string)
        self._sender = self._client.get_topic_sender(topic_name=input_topic)

        # Pending answers: event_id -> answer text
        self._pending_answers: dict[str, str] = {}
        self._answer_events: dict[str, threading.Event] = {}

        # Listener liveness flag — fail fast if listener can't connect
        self._listener_alive = threading.Event()

        self._listener_thread = threading.Thread(
            target=self._listen_for_answers, daemon=True
        )
        self._listener_thread.start()

        # Wait up to 30s for listener to connect
        if not self._listener_alive.wait(timeout=30):
            raise RuntimeError(
                f"Failed to connect to response topic {response_topic}/eval-reader. "
                "Check that the topic and subscription exist."
            )

        logger.info(
            "RemoteAgentAdapter: input=%s response=%s agents=%d",
            input_topic, response_topic, agent_count,
        )

    def learn_from_content(self, content: str) -> dict[str, Any]:
        """Send content to one agent (round-robin partition).

        5000 turns / 100 agents = 50 turns each. Each agent learns its
        partition locally. The hive mind shares knowledge between agents
        so any agent can answer questions about any content.
        """
        from azure.servicebus import ServiceBusMessage

        event_id = uuid.uuid4().hex[:12]
        with self._counter_lock:
            target_agent = self._learn_count % self._agent_count
            self._learn_count += 1
            learn_count = self._learn_count
        target_name = f"agent-{target_agent}"

        msg = ServiceBusMessage(
            json.dumps({
                "event_type": "LEARN_CONTENT",
                "event_id": event_id,
                "target_agent": target_name,
                "source_agent": "eval-harness",
                "payload": {
                    "content": content,
                    "target_agent": target_name,
                },
            }),
            content_type="application/json",
        )
        self._sender.send_messages(msg)

        if learn_count % 500 == 0:
            logger.info("RemoteAgentAdapter: sent %d content turns (%d per agent)",
                        learn_count, learn_count // self._agent_count)

        return {"facts_stored": 1, "event_id": event_id}

    def answer_question(self, question: str) -> str:
        """Send question to one agent, wait for answer. No timeout."""
        # Wait for agents to finish processing content (blocks all threads)
        if self._learn_count > 0 and not self._idle_wait_done.is_set():
            with self._counter_lock:
                # Double-check under lock — only one thread does the actual wait
                if not self._idle_wait_done.is_set():
                    self._wait_for_agents_idle()
                    self._idle_wait_done.set()

        with self._counter_lock:
            target_agent = self._question_count % self._agent_count
            self._question_count += 1

        from azure.servicebus import ServiceBusMessage

        event_id = uuid.uuid4().hex[:12]
        target_name = f"agent-{target_agent}"

        # Register signal before sending
        answer_event = threading.Event()
        with self._answer_lock:
            self._answer_events[event_id] = answer_event

        msg = ServiceBusMessage(
            json.dumps({
                "event_type": "INPUT",
                "event_id": event_id,
                "target_agent": target_name,
                "source_agent": "eval-harness",
                "payload": {
                    "question": question,
                    "question_id": f"q_{target_agent}_{event_id}",
                    "target_agent": target_name,
                },
            }),
            content_type="application/json",
        )
        self._sender.send_messages(msg)

        logger.info(
            "RemoteAgentAdapter: sent question to %s (event_id=%s): %s",
            target_name, event_id, question[:60],
        )

        # Wait for answer — optional timeout to prevent indefinite hangs
        timeout = self._answer_timeout if self._answer_timeout > 0 else None
        got_answer = answer_event.wait(timeout=timeout)
        if not got_answer:
            logger.warning(
                "answer_question: timeout after %ds waiting for event_id=%s from %s",
                self._answer_timeout, event_id, target_name,
            )

        with self._answer_lock:
            answer = self._pending_answers.pop(event_id, "No answer received")
            self._answer_events.pop(event_id, None)

        return answer

    def _wait_for_agents_idle(self) -> None:
        """Wait for agents to finish processing content.

        Polls the LAST agent's subscription (highest index, last to receive
        its final partitioned message) until queue depth reaches 0 or
        idle_wait_timeout seconds have elapsed (0 = no timeout).

        If timeout is hit, logs a warning and proceeds to the question phase
        with whatever state the agents have reached — partial results are
        better than a hung eval.
        """
        last_agent = self._agent_count - 1
        agent_name = f"agent-{last_agent}"

        logger.info("Waiting for agents to process %d content turns (%d per agent). Polling %s...",
                    self._learn_count, self._learn_count // max(1, self._agent_count), agent_name)

        poll_interval = 15
        start_time = time.time()

        while True:
            if self._idle_wait_timeout > 0:
                elapsed = time.time() - start_time
                if elapsed >= self._idle_wait_timeout:
                    logger.warning(
                        "idle_wait_timeout=%ds exceeded (elapsed=%.0fs). "
                        "Proceeding to question phase — agents may not have fully processed all content.",
                        self._idle_wait_timeout, elapsed,
                    )
                    return

            try:
                result = subprocess.run(
                    ["az", "servicebus", "topic", "subscription", "show",
                     "--namespace-name", self._sb_namespace,
                     "--topic-name", self._input_topic,
                     "--name", agent_name,
                     "--resource-group", self._resource_group,
                     "--query", "countDetails.activeMessageCount",
                     "-o", "tsv"],
                    capture_output=True, text=True, timeout=30,
                )
                count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else -1
                if count == 0:
                    logger.info("Agent queues empty. Starting question phase.")
                    return
                elif count > 0:
                    elapsed = time.time() - start_time
                    remaining = (
                        f", {self._idle_wait_timeout - elapsed:.0f}s until timeout"
                        if self._idle_wait_timeout > 0 else ""
                    )
                    logger.info("  %s queue: %d messages remaining (elapsed=%.0fs%s)...",
                                agent_name, count, elapsed, remaining)
            except Exception as e:
                logger.warning("Queue depth check failed: %s", e)

            time.sleep(poll_interval)

    def _listen_for_answers(self) -> None:
        """Background thread: collect answers from eval-responses topic."""
        try:
            receiver = self._client.get_subscription_receiver(
                topic_name=self._response_topic,
                subscription_name="eval-reader",
                max_wait_time=10,
            )
        except Exception as e:
            logger.error("RemoteAgentAdapter: failed to connect to response topic: %s", e)
            return  # _listener_alive never set — constructor will raise

        self._listener_alive.set()
        logger.info("RemoteAgentAdapter: listening on %s/eval-reader", self._response_topic)

        while not self._shutdown.is_set():
            try:
                messages = receiver.receive_messages(
                    max_message_count=50, max_wait_time=5,
                )
                for msg in messages:
                    try:
                        body = json.loads(str(msg))
                        event_id = body.get("event_id", "")
                        answer = body.get("answer", "")

                        with self._answer_lock:
                            if event_id in self._answer_events:
                                self._pending_answers[event_id] = answer
                                self._answer_events[event_id].set()
                                logger.info(
                                    "RemoteAgentAdapter: got answer for %s from %s: %s",
                                    event_id, body.get("agent_id", "?"),
                                    answer[:80] if answer else "(empty)",
                                )
                            else:
                                logger.warning(
                                    "RemoteAgentAdapter: answer for unknown event_id=%s (stale?)",
                                    event_id,
                                )

                        receiver.complete_message(msg)
                    except Exception:
                        logger.debug("Failed to parse response message", exc_info=True)
                        try:
                            receiver.complete_message(msg)
                        except Exception:
                            pass
            except Exception:
                if not self._shutdown.is_set():
                    logger.debug("Response listener error", exc_info=True)
                    time.sleep(1)

        try:
            receiver.close()
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
        """Clean up Service Bus connections."""
        self._shutdown.set()
        try:
            self._sender.close()
        except Exception:
            pass
        try:
            self._client.close()
        except Exception:
            pass
        if self._listener_thread.is_alive():
            self._listener_thread.join(timeout=5)
