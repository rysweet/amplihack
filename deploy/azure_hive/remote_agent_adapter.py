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
    Answers are collected from Log Analytics (agent stdout → Container Apps logs).
    """

    def __init__(
        self,
        connection_string: str,
        input_topic: str = "hive-events",
        workspace_id: str = "",
        agent_count: int = 100,
        answer_timeout: float = 600.0,
        response_topic: str = "",  # unused, kept for backward compat
    ) -> None:
        from azure.servicebus import ServiceBusClient

        self._conn_str = connection_string
        self._input_topic = input_topic
        self._workspace_id = workspace_id
        self._agent_count = agent_count
        self._answer_timeout = answer_timeout
        self._learn_count = 0
        self._question_count = 0
        self._closed = False

        # Service Bus client for sending
        self._client = ServiceBusClient.from_connection_string(connection_string)
        self._sender = self._client.get_topic_sender(topic_name=input_topic)

        # Log Analytics client for reading answers
        self._la_client = None
        if workspace_id:
            try:
                from azure.identity import AzureCliCredential
                from azure.monitor.query import LogsQueryClient
                self._la_client = LogsQueryClient(AzureCliCredential())
            except Exception as e:
                logger.warning("RemoteAgentAdapter: LA client init failed: %s", e)

        logger.info(
            "RemoteAgentAdapter: input=%s workspace=%s agents=%d",
            input_topic, workspace_id, agent_count,
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
        """Send question to one agent via INPUT event, poll LA for answer.

        The question goes through the agent's full OODA loop (observe → orient
        → decide → act). The agent prints the answer to stdout, which Container
        Apps streams to Log Analytics. We poll LA for the ANSWER line from the
        target agent.

        On the first question, waits for agents to finish processing content
        by polling LA until LLM activity drops to near-zero.
        """
        # On first question, wait for agents to finish processing content
        if self._question_count == 0 and self._learn_count > 0:
            self._wait_for_agents_idle()

        from azure.servicebus import ServiceBusMessage

        event_id = uuid.uuid4().hex[:12]
        target_agent = self._question_count % self._agent_count
        target_name = f"agent-{target_agent}"
        self._question_count += 1

        send_time = time.time()

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

        logger.info(
            "RemoteAgentAdapter: sent question to %s: %s",
            target_name, question[:60],
        )

        # Poll Log Analytics for the answer
        if not self._la_client:
            logger.warning("No LA client — cannot collect answer")
            return "No answer (Log Analytics client not configured)"

        return self._poll_la_for_answer(target_name, send_time)

    def _wait_for_agents_idle(self) -> None:
        """Wait for agents to finish processing content before asking questions."""
        if not self._la_client:
            logger.info("No LA client — waiting 5 min for agents to process content")
            time.sleep(300)
            return

        import datetime
        from azure.monitor.query import LogsQueryStatus

        logger.info("Waiting for agents to finish processing %d content turns...", self._learn_count)
        quiet_count = 0
        quiet_threshold = 5  # 5 consecutive low-activity checks

        while quiet_count < quiet_threshold:
            try:
                end_dt = datetime.datetime.now(tz=datetime.timezone.utc)
                start_dt = end_dt - datetime.timedelta(minutes=2)
                query = (
                    "ContainerAppConsoleLogs_CL"
                    " | where Log_s has 'Completed Call'"
                    " | count"
                )
                response = self._la_client.query_workspace(
                    workspace_id=self._workspace_id,
                    query=query,
                    timespan=(start_dt, end_dt),
                )
                count = 0
                if response.status == LogsQueryStatus.SUCCESS and response.tables:
                    for row in response.tables[0].rows:
                        count = int(row[0]) if row else 0

                if count < 20:
                    quiet_count += 1
                    logger.info("  Low activity: %d calls (quiet %d/%d)", count, quiet_count, quiet_threshold)
                else:
                    quiet_count = 0
                    logger.info("  Agents processing: %d calls in 2min...", count)
            except Exception as e:
                logger.debug("LA poll during wait failed: %s", e)

            time.sleep(30)

        logger.info("Agents idle. Starting question phase.")

    def _poll_la_for_answer(self, agent_name: str, since_ts: float) -> str:
        """Poll Log Analytics for an ANSWER line from a specific agent."""
        import datetime
        from azure.monitor.query import LogsQueryStatus

        deadline = time.time() + self._answer_timeout
        poll_interval = 10.0

        while time.time() < deadline:
            start_dt = datetime.datetime.fromtimestamp(
                since_ts - 60, tz=datetime.timezone.utc  # 60s lookback buffer
            )
            end_dt = datetime.datetime.now(tz=datetime.timezone.utc)

            query = (
                "ContainerAppConsoleLogs_CL"
                f' | where ContainerName_s == "{agent_name}"'
                ' | where Log_s has "ANSWER:"'
                f' | where Log_s startswith "[{agent_name}]"'
                " | order by TimeGenerated desc"
                " | project Log_s"
                " | take 1"
            )

            try:
                response = self._la_client.query_workspace(
                    workspace_id=self._workspace_id,
                    query=query,
                    timespan=(start_dt, end_dt),
                )
                if response.status == LogsQueryStatus.SUCCESS:
                    if response.tables and response.tables[0].rows:
                        log_line = str(response.tables[0].rows[0][0])
                        if "ANSWER:" in log_line:
                            marker = "ANSWER: "
                            idx = log_line.find(marker)
                            answer = log_line[idx + len(marker):].strip() if idx >= 0 else log_line
                            if "internal error" not in answer.lower():
                                logger.info(
                                    "RemoteAgentAdapter: got answer from %s: %s",
                                    agent_name, answer[:80],
                                )
                                return answer
            except Exception as e:
                logger.debug("LA poll failed: %s", e)

            time.sleep(poll_interval)

        logger.warning("RemoteAgentAdapter: timeout waiting for %s (%ds)", agent_name, self._answer_timeout)
        return "No answer received (timeout)"

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
