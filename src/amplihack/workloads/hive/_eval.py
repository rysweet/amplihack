"""Internal eval helper: event-driven agent evaluation via HIVE_AGENT_READY signalling.

Replaces the sleep-timer polling in query_hive.py with proper event subscription.
Called by HiveMindWorkload.eval() and the ``haymaker hive eval`` CLI extension.
NOT imported directly by external callers.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


async def run_eval(
    deployment_id: str,
    repeats: int,
    wait_for_ready: int,
    timeout_seconds: int,
    sb_conn_str: str,
    topic_name: str,
) -> list[dict[str, Any]]:
    """Wait for agents ready, then run eval rounds via HIVE_QUERY events.

    Args:
        deployment_id: Deployment to evaluate.
        repeats: Number of question rounds to run.
        wait_for_ready: How many HIVE_AGENT_READY events to wait for (0 = skip).
        timeout_seconds: Max wait time for agents to become ready.
        sb_conn_str: Service Bus connection string.
        topic_name: Service Bus topic name.

    Returns:
        List of {question, query_id, answers: [{agent, answer}]} dicts.
    """

    if wait_for_ready > 0:
        logger.info(
            "eval: waiting for %d HIVE_AGENT_READY events (timeout=%ds)",
            wait_for_ready,
            timeout_seconds,
        )
        ready_count = await _wait_for_ready_events(
            deployment_id=deployment_id,
            expected_count=wait_for_ready,
            timeout_seconds=timeout_seconds,
            sb_conn_str=sb_conn_str,
            topic_name=topic_name,
        )
        logger.info("eval: %d agents signalled ready", ready_count)
    else:
        logger.info("eval: skipping AGENT_READY wait (wait_for_ready=0)")

    questions = _build_eval_questions(repeats)
    results: list[dict[str, Any]] = []

    for i, question in enumerate(questions):
        query_id = uuid.uuid4().hex[:8]
        logger.info("eval: round %d/%d query_id=%s question=%r", i + 1, repeats, query_id, question)

        await _publish_query(
            deployment_id=deployment_id,
            query_id=query_id,
            question=question,
            sb_conn_str=sb_conn_str,
            topic_name=topic_name,
        )

        answers = await _collect_responses(
            deployment_id=deployment_id,
            query_id=query_id,
            timeout_seconds=30,
            sb_conn_str=sb_conn_str,
            topic_name=topic_name,
        )
        results.append({"question": question, "query_id": query_id, "answers": answers})
        logger.info("eval: round %d collected %d responses", i + 1, len(answers))

    return results


async def _wait_for_ready_events(
    deployment_id: str,
    expected_count: int,
    timeout_seconds: int,
    sb_conn_str: str,
    topic_name: str,
) -> int:
    """Subscribe to the eval topic and count HIVE_AGENT_READY events.

    Returns:
        Number of AGENT_READY events received before timeout.
    """
    from amplihack.workloads.hive.events import HIVE_AGENT_READY

    ready_agents: set[str] = set()
    deadline = asyncio.get_event_loop().time() + timeout_seconds

    if not sb_conn_str:
        logger.warning("No Service Bus connection string — skipping AGENT_READY wait")
        return 0

    try:
        from azure.servicebus import ServiceBusClient
    except ImportError:
        logger.warning("azure-servicebus not installed — skipping AGENT_READY wait")
        return 0

    subscription_name = f"eval-ready-{deployment_id[:8]}"

    def _poll_sync() -> list[dict]:
        received: list[dict] = []
        try:
            import json

            with ServiceBusClient.from_connection_string(sb_conn_str) as client:
                with client.get_subscription_receiver(
                    topic_name=topic_name,
                    subscription_name=subscription_name,
                    max_wait_time=5,
                ) as receiver:
                    msgs = receiver.receive_messages(max_message_count=50, max_wait_time=5)
                    for msg in msgs:
                        try:
                            body = json.loads(str(msg))
                            if body.get("topic") == HIVE_AGENT_READY:
                                received.append(body)
                            receiver.complete_message(msg)
                        except Exception:
                            pass
        except Exception as exc:
            logger.debug("Poll error: %s", exc)
        return received

    loop = asyncio.get_event_loop()
    while loop.time() < deadline and len(ready_agents) < expected_count:
        events = await loop.run_in_executor(None, _poll_sync)
        for evt in events:
            agent_name = (evt.get("data") or {}).get("agent_name", str(uuid.uuid4()))
            ready_agents.add(agent_name)
            logger.info(
                "eval: agent ready: %s (%d/%d)", agent_name, len(ready_agents), expected_count
            )
        if len(ready_agents) < expected_count:
            await asyncio.sleep(2)

    if len(ready_agents) < expected_count:
        logger.warning(
            "eval: timeout waiting for agents — got %d/%d AGENT_READY events",
            len(ready_agents),
            expected_count,
        )
    return len(ready_agents)


async def _publish_query(
    deployment_id: str,
    query_id: str,
    question: str,
    sb_conn_str: str,
    topic_name: str,
) -> None:
    """Publish a HIVE_QUERY event."""
    from amplihack.workloads.hive.events import make_query_event

    event = make_query_event(deployment_id=deployment_id, query_id=query_id, question=question)

    if not sb_conn_str:
        logger.info("LOCAL QUERY event: %s", event.model_dump_json())
        return

    try:
        from azure.servicebus import ServiceBusClient, ServiceBusMessage

        def _send() -> None:
            with ServiceBusClient.from_connection_string(sb_conn_str) as client:
                with client.get_topic_sender(topic_name=topic_name) as sender:
                    sender.send_messages(
                        ServiceBusMessage(
                            body=event.model_dump_json(),
                            application_properties={
                                "topic": event.topic,
                                "deployment_id": deployment_id,
                                "query_id": query_id,
                            },
                        )
                    )

        await asyncio.get_event_loop().run_in_executor(None, _send)
    except ImportError:
        logger.warning("azure-servicebus not available — query not sent")


async def _collect_responses(
    deployment_id: str,
    query_id: str,
    timeout_seconds: int,
    sb_conn_str: str,
    topic_name: str,
) -> list[dict[str, Any]]:
    """Collect HIVE_QUERY_RESPONSE events for the given query_id."""
    from amplihack.workloads.hive.events import HIVE_QUERY_RESPONSE

    if not sb_conn_str:
        return []

    try:
        from azure.servicebus import ServiceBusClient
    except ImportError:
        return []

    answers: list[dict[str, Any]] = []
    subscription_name = f"eval-resp-{deployment_id[:8]}"
    deadline = asyncio.get_event_loop().time() + timeout_seconds

    def _poll_sync() -> list[dict]:
        import json

        received: list[dict] = []
        try:
            with ServiceBusClient.from_connection_string(sb_conn_str) as client:
                with client.get_subscription_receiver(
                    topic_name=topic_name,
                    subscription_name=subscription_name,
                    max_wait_time=3,
                ) as receiver:
                    msgs = receiver.receive_messages(max_message_count=100, max_wait_time=3)
                    for msg in msgs:
                        try:
                            body = json.loads(str(msg))
                            if (
                                body.get("topic") == HIVE_QUERY_RESPONSE
                                and (body.get("data") or {}).get("query_id") == query_id
                            ):
                                received.append(body)
                            receiver.complete_message(msg)
                        except Exception:
                            pass
        except Exception as exc:
            logger.debug("Response poll error: %s", exc)
        return received

    loop = asyncio.get_event_loop()
    while loop.time() < deadline:
        events = await loop.run_in_executor(None, _poll_sync)
        for evt in events:
            data = evt.get("data") or {}
            answers.append(
                {
                    "agent": data.get("agent_name", "unknown"),
                    "answer": data.get("answer", ""),
                }
            )
        if events:
            break  # got responses — stop polling
        await asyncio.sleep(1)

    return answers


def _build_eval_questions(repeats: int) -> list[str]:
    """Build evaluation questions from amplihack_eval or a fallback pool."""
    try:
        from amplihack_eval.data import generate_dialogue

        gt = generate_dialogue(num_turns=300, seed=42)
        questions = [
            t.content for t in gt.turns if t.block_name in ("questions", "qa") and t.content
        ][:repeats]
        if questions:
            return questions
    except Exception:
        pass

    fallback = [
        "What is the CVSS score for CVE-2021-44228 and why is it so high?",
        "Which threat actor is associated with the SolarWinds attack?",
        "What is DNS tunneling and which incident involved it?",
        "Describe the indicators of compromise from INC-2024-003.",
        "What post-incident actions were taken after INC-2024-001?",
    ]
    return (
        fallback[:repeats]
        if repeats <= len(fallback)
        else (fallback * ((repeats // len(fallback)) + 1))[:repeats]
    )
