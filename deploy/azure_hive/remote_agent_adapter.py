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
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path
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
        replicate_learning_to_all_agents: bool = False,
        question_failover_retries: int = 0,
    ) -> None:
        self._connection_string = connection_string
        self._input_hub = input_hub
        self._response_hub = response_hub
        self._resource_group = resource_group
        self._agent_count = agent_count

        self._learn_count = 0
        self._learn_turn_counts = [0 for _ in range(agent_count)]
        self._question_count = 0
        self._answer_timeout = answer_timeout
        self._replicate_learning_to_all_agents = replicate_learning_to_all_agents
        self._question_failover_retries = max(0, question_failover_retries)
        self._shutdown = threading.Event()
        self._startup_wait_done = threading.Event()
        self._idle_wait_done = threading.Event()

        # Thread safety for counters and answer dict
        self._counter_lock = threading.Lock()
        self._answer_lock = threading.Lock()
        self._producer_lock = threading.Lock()
        self._extractor_lock = threading.Lock()

        # Pending answers: event_id -> answer text
        self._pending_answers: dict[str, str] = {}
        self._answer_events: dict[str, threading.Event] = {}
        self._producer: Any | None = None
        self._fact_batch_extractor: Any | None = None
        self._fact_batch_extractor_dir: Path | None = None

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

    @staticmethod
    def _agent_name(agent_index: int) -> str:
        """Return the canonical agent name for an index."""
        return f"agent-{agent_index}"

    def _publish_event(self, payload: dict, partition_key: str) -> None:
        """Publish a single JSON event to the input Event Hub."""
        from azure.eventhub import EventData  # type: ignore[import-unresolved]

        payload["run_id"] = self._run_id
        route_partition_id: str | None = None
        if partition_key.startswith("agent-"):
            route_partition_id = self._target_partition(partition_key)

        producer = self._get_producer()
        try:
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
            self._reset_producer()
            producer2 = self._get_producer()
            try:
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

    def _get_producer(self) -> Any:
        """Return a cached Event Hub producer, creating it lazily when needed."""
        with self._producer_lock:
            if self._producer is None:
                from azure.eventhub import EventHubProducerClient  # type: ignore[import-unresolved]

                self._producer = EventHubProducerClient.from_connection_string(
                    self._connection_string,
                    eventhub_name=self._input_hub,
                )
            return self._producer

    def _reset_producer(self) -> None:
        """Close and clear the cached Event Hub producer."""
        with self._producer_lock:
            producer = self._producer
            self._producer = None
        if producer is not None:
            try:
                producer.close()
            except Exception:
                logger.debug("Failed to close cached producer cleanly", exc_info=True)

    def _get_fact_batch_extractor(self) -> Any:
        """Return a reusable local extractor for replicated fact batches."""
        with self._extractor_lock:
            if self._fact_batch_extractor is None:
                from amplihack.agents.goal_seeking.runtime_factory import create_goal_agent_runtime

                extractor_dir = Path(tempfile.mkdtemp(prefix="amplihack-azure-fact-batch-"))
                self._fact_batch_extractor_dir = extractor_dir
                self._fact_batch_extractor = create_goal_agent_runtime(
                    agent_name="eval-harness-fact-extractor",
                    storage_path=extractor_dir,
                    use_hierarchical=True,
                    runtime_kind="goal",
                    bind_answer_mode=False,
                )
            return self._fact_batch_extractor

    def _prepare_fact_batch(self, content: str) -> dict[str, Any]:
        """Prepare a direct-storage fact batch for replicated learning."""
        extractor = self._get_fact_batch_extractor()
        return extractor.prepare_fact_batch(content, include_summary=False)

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
        """Send content to one agent or to all agents when replication is enabled.

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
            if self._replicate_learning_to_all_agents:
                target_agents = list(range(self._agent_count))
                for agent_index in target_agents:
                    self._learn_turn_counts[agent_index] += 1
            else:
                target_agents = [target_agent]
                self._learn_turn_counts[target_agent] += 1

        fact_batch: dict[str, Any] | None = None
        if self._replicate_learning_to_all_agents:
            # Pre-extract facts locally so agents just do a fast DB write.
            # STORE_FACT_BATCH events are sent in order before FEED_COMPLETE.
            # Agents defer AGENT_READY until all expected fact batches are stored
            # (see expected_fact_batches in FEED_COMPLETE payload).
            fact_batch = self._prepare_fact_batch(content)

        for agent_index in target_agents:
            target_name = self._agent_name(agent_index)
            if self._replicate_learning_to_all_agents:
                payload = {
                    "event_type": "STORE_FACT_BATCH",
                    "event_id": event_id,
                    "target_agent": target_name,
                    "source_agent": "eval-harness",
                    "payload": {
                        "fact_batch": fact_batch,
                        "target_agent": target_name,
                    },
                }
            else:
                payload = {
                    "event_type": "LEARN_CONTENT",
                    "event_id": event_id,
                    "target_agent": target_name,
                    "source_agent": "eval-harness",
                    "payload": {
                        "content": content,
                        "target_agent": target_name,
                    },
                }
            self._publish_event(
                payload,
                partition_key=target_name,
            )

        log_every = 50 if self._replicate_learning_to_all_agents else 500
        if learn_count % log_every == 0:
            if self._replicate_learning_to_all_agents:
                logger.info(
                    "RemoteAgentAdapter: sent %d content turns (STORE_FACT_BATCH replicated to all %d agents)",
                    learn_count,
                    self._agent_count,
                )
            else:
                logger.info(
                    "RemoteAgentAdapter: sent %d content turns (%d per agent)",
                    learn_count,
                    learn_count // max(1, self._agent_count),
                )

        return {
            "facts_stored": len((fact_batch or {}).get("facts", [])) if fact_batch else 1,
            "event_id": event_id,
            "replicated_to": len(target_agents),
        }

    def _send_question_to_agent(self, question: str, target_agent: int) -> str:
        """Send one question attempt to one agent and wait for its answer."""
        event_id = uuid.uuid4().hex[:12]
        target_name = self._agent_name(target_agent)

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

    # Prefixes that indicate the agent understood the question but had no relevant
    # facts — semantically a non-answer even though it's a syntactically valid string.
    _ABSTENTION_PREFIXES: tuple[str, ...] = (
        "the provided facts do not contain",
        "the provided context does not contain",
        "no information available",
        "not enough context",
        "i don't have information",
        "i do not have information",
        "there is no information",
        "based on the provided",
        "the facts provided do not",
        "i cannot find",
        "no relevant information",
    )

    @classmethod
    def _is_semantic_abstention(cls, answer: str) -> bool:
        """Return True if the answer is a semantic abstention (agent had no facts)."""
        lowered = answer.strip().lower()
        return any(lowered.startswith(prefix) for prefix in cls._ABSTENTION_PREFIXES)

    def answer_question(self, question: str) -> str:
        """Send question to one agent, retrying on other agents when configured.

        Retries on:
        - "No answer received" (transport miss / timeout)
        - Semantic abstentions: answers that start with known no-context phrases,
          meaning the agent understood the question but lacked the relevant facts.
          Retrying on a different agent may surface facts stored on another shard.
        """
        # Wait for agents to finish processing content (blocks all threads)
        if self._learn_count > 0 and not self._idle_wait_done.is_set():
            with self._counter_lock:
                if not self._idle_wait_done.is_set():
                    self._wait_for_agents_idle()
                    self._idle_wait_done.set()

        with self._counter_lock:
            target_agent = self._question_count % self._agent_count
            self._question_count += 1

        max_attempts = min(self._agent_count, 1 + self._question_failover_retries)
        last_answer = "No answer received"
        for attempt in range(max_attempts):
            attempt_target = (target_agent + attempt) % self._agent_count
            if attempt > 0:
                logger.info(
                    "RemoteAgentAdapter: retrying question on %s after previous timeout/no-answer/abstention",
                    self._agent_name(attempt_target),
                )
            answer = self._send_question_to_agent(question, attempt_target)
            if answer != "No answer received" and not self._is_semantic_abstention(answer):
                return answer
            last_answer = answer

        return last_answer

    def _wait_for_agents_idle(self) -> None:
        """Wait for all agents to finish processing content.

        Sends FEED_COMPLETE to every agent, then waits for each to publish
        AGENT_READY on the eval-responses hub.  Event-driven — no polling.
        """
        min_turns = min(self._learn_turn_counts, default=0)
        max_turns = max(self._learn_turn_counts, default=0)
        if min_turns == max_turns:
            turns_summary = f"{max_turns} content turns each"
        else:
            turns_summary = f"{min_turns}-{max_turns} content turns per agent"
        logger.info(
            "Sending FEED_COMPLETE to all %d agents (%s)...",
            self._agent_count,
            turns_summary,
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
                target_agent = self._agent_index(target_name)
                total_turns = (
                    self._learn_turn_counts[target_agent]
                    if 0 <= target_agent < len(self._learn_turn_counts)
                    else self._learn_count // max(1, self._agent_count)
                )
                # Include expected event count so agents defer AGENT_READY until
                # all queued events in their partition have been processed.
                # - STORE_FACT_BATCH mode (replicate): agents get total_turns fact batches.
                # - LEARN_CONTENT mode (round-robin): agents get total_turns learn events.
                if self._replicate_learning_to_all_agents:
                    feed_payload: dict[str, Any] = {
                        "total_turns": total_turns,
                        "target_agent": target_name,
                        "expected_fact_batches": total_turns,
                    }
                else:
                    feed_payload = {
                        "total_turns": total_turns,
                        "target_agent": target_name,
                        "expected_learn_content": total_turns,
                    }
                self._publish_event(
                    {
                        "event_type": "FEED_COMPLETE",
                        "event_id": uuid.uuid4().hex[:12],
                        "target_agent": target_name,
                        "source_agent": "eval-harness",
                        "payload": feed_payload,
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
                    return

                if event_type == "AGENT_SHUTDOWN":
                    logger.warning(
                        "RemoteAgentAdapter: AGENT_SHUTDOWN from %s reason=%s detail=%s",
                        body.get("agent_id", "?"),
                        body.get("reason", ""),
                        body.get("detail", ""),
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
        self._reset_producer()
        extractor = self._fact_batch_extractor
        extractor_dir = self._fact_batch_extractor_dir
        self._fact_batch_extractor = None
        self._fact_batch_extractor_dir = None
        if extractor is not None:
            try:
                extractor.close()
            except Exception:
                logger.debug("Failed to close fact batch extractor cleanly", exc_info=True)
        if extractor_dir is not None:
            shutil.rmtree(extractor_dir, ignore_errors=True)
        if self._listener_thread.is_alive():
            self._listener_thread.join(timeout=5)
