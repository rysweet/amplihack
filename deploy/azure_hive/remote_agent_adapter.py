"""RemoteAgentAdapter — makes a deployed Azure Container Apps agent look like a local agent.

Implements the same interface as LearningAgent (learn_from_content, answer_question)
so it can be passed directly to LongHorizonMemoryEval.run(). The eval harness
uses the exact same code path for local and distributed agents.

Content is sent via Service Bus LEARN_CONTENT events.
Questions are sent via Service Bus INPUT events with an event_id.
Answers are collected from a response topic (published by the AnswerPublisher
stdout wrapper on the agent side).

Usage:
    from deploy.azure_hive.remote_agent_adapter import RemoteAgentAdapter
    from amplihack.eval.long_horizon_memory import LongHorizonMemoryEval

    adapter = RemoteAgentAdapter(
        connection_string=sb_conn,
        input_topic="hive-events-amplihivev8",
        response_topic="eval-responses-amplihivev8",
        agent_count=100,
    )
    eval_harness = LongHorizonMemoryEval(num_turns=5000, num_questions=50)
    report = eval_harness.run(adapter, grader_model="claude-haiku-4-5-20251001")
    adapter.close()
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
    """Adapter that forwards learn/answer calls to deployed agents via Service Bus.

    Implements learn_from_content() and answer_question() so the standard
    LongHorizonMemoryEval can use it identically to a local LearningAgent.

    Content is broadcast to all agents (LEARN_CONTENT events).
    Questions are sent to a single agent (round-robin) as INPUT events.
    Answers are collected from the eval-responses topic with event_id correlation.
    """

    def __init__(
        self,
        connection_string: str,
        input_topic: str = "hive-events",
        response_topic: str = "eval-responses",
        agent_count: int = 100,
        answer_timeout: float = 600.0,
    ) -> None:
        from azure.servicebus import ServiceBusClient

        self._conn_str = connection_string
        self._input_topic = input_topic
        self._response_topic = response_topic
        self._agent_count = agent_count
        self._answer_timeout = answer_timeout
        self._learn_count = 0
        self._question_count = 0

        # Service Bus clients
        self._client = ServiceBusClient.from_connection_string(connection_string)
        self._sender = self._client.get_topic_sender(topic_name=input_topic)

        # Response listener runs in a background thread
        self._pending_answers: dict[str, str] = {}  # event_id -> answer
        self._answer_events: dict[str, threading.Event] = {}  # event_id -> signal
        self._lock = threading.Lock()
        self._closed = False

        self._listener_thread = threading.Thread(
            target=self._listen_for_answers, daemon=True
        )
        self._listener_thread.start()
        logger.info(
            "RemoteAgentAdapter: input=%s response=%s agents=%d",
            input_topic, response_topic, agent_count,
        )

    def learn_from_content(self, content: str) -> dict[str, Any]:
        """Send content to all agents via LEARN_CONTENT event (broadcast)."""
        from azure.servicebus import ServiceBusMessage

        event_id = uuid.uuid4().hex[:12]
        msg = ServiceBusMessage(
            json.dumps({
                "event_type": "LEARN_CONTENT",
                "event_id": event_id,
                "source_agent": "eval-harness",
                "payload": {"content": content},
            }),
            content_type="application/json",
        )
        self._sender.send_messages(msg)
        self._learn_count += 1

        if self._learn_count % 100 == 0:
            logger.info("RemoteAgentAdapter: sent %d content turns", self._learn_count)

        return {"facts_stored": 1, "event_id": event_id}

    def answer_question(self, question: str) -> str:
        """Send question to one agent via INPUT event, wait for answer.

        The question goes through the agent's full OODA loop (observe → orient
        → decide → act). The AnswerPublisher on the agent side publishes the
        correlated answer to the response topic.
        """
        from azure.servicebus import ServiceBusMessage

        event_id = uuid.uuid4().hex[:12]
        # Round-robin agent selection
        target_agent = self._question_count % self._agent_count
        self._question_count += 1

        # Prepare answer event before sending (avoid race)
        answer_event = threading.Event()
        with self._lock:
            self._answer_events[event_id] = answer_event

        # Send as INPUT event with event_id for correlation
        msg = ServiceBusMessage(
            json.dumps({
                "event_type": "INPUT",
                "event_id": event_id,
                "source_agent": "eval-harness",
                "payload": {
                    "question": question,
                    "question_id": f"q_{self._question_count}",
                },
            }),
            content_type="application/json",
        )
        self._sender.send_messages(msg)

        logger.debug(
            "RemoteAgentAdapter: sent question to agent-%d (event_id=%s): %s",
            target_agent, event_id, question[:60],
        )

        # Wait for answer
        if not answer_event.wait(timeout=self._answer_timeout):
            logger.warning(
                "RemoteAgentAdapter: timeout waiting for answer (event_id=%s, %ds)",
                event_id, self._answer_timeout,
            )
            return "No answer received (timeout)"

        with self._lock:
            answer = self._pending_answers.pop(event_id, "No answer received")
            self._answer_events.pop(event_id, None)

        return answer

    def _listen_for_answers(self) -> None:
        """Background thread: subscribe to response topic and collect answers."""
        try:
            receiver = self._client.get_subscription_receiver(
                topic_name=self._response_topic,
                subscription_name="eval-reader",
                max_wait_time=10,
            )
        except Exception as e:
            logger.error("RemoteAgentAdapter: failed to connect to response topic: %s", e)
            return

        logger.info("RemoteAgentAdapter: listening on %s/eval-reader", self._response_topic)

        while not self._closed:
            try:
                messages = receiver.receive_messages(
                    max_message_count=50, max_wait_time=5,
                )
                for msg in messages:
                    try:
                        body = json.loads(str(msg))
                        event_id = body.get("event_id", "")
                        answer = body.get("answer", "")

                        with self._lock:
                            if event_id in self._answer_events:
                                self._pending_answers[event_id] = answer
                                self._answer_events[event_id].set()

                        receiver.complete_message(msg)
                    except Exception:
                        logger.debug("Failed to parse response message", exc_info=True)
                        try:
                            receiver.complete_message(msg)
                        except Exception:
                            pass
            except Exception:
                if not self._closed:
                    logger.debug("Response listener error", exc_info=True)
                    time.sleep(1)

        try:
            receiver.close()
        except Exception:
            pass

    def get_memory_stats(self) -> dict[str, Any]:
        """Return adapter stats (not agent memory stats)."""
        return {
            "adapter": "remote",
            "learn_count": self._learn_count,
            "question_count": self._question_count,
            "agent_count": self._agent_count,
        }

    def close(self) -> None:
        """Clean up Service Bus connections."""
        self._closed = True
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
