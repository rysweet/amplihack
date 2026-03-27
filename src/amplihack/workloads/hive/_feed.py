"""Internal feed helper: publishes HIVE_LEARN_CONTENT events via EventData/ServiceBus.

Called by HiveMindWorkload.feed() and the ``haymaker hive feed`` CLI extension.
NOT imported directly by external callers — use the workload method or CLI instead.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

logger = logging.getLogger(__name__)


async def run_feed(
    deployment_id: str,
    turns: int,
    topic_name: str,
    sb_conn_str: str,
    source: str = "haymaker-hive-feed",
) -> None:
    """Publish *turns* HIVE_LEARN_CONTENT events then HIVE_FEED_COMPLETE.

    Uses typed agent-haymaker EventData and ServiceBusEventBus (dual-write).
    Falls back to local event bus if Service Bus connection string is missing.

    Args:
        deployment_id: Deployment receiving the events.
        turns: Number of LEARN_CONTENT turns to send.
        topic_name: Service Bus topic name.
        sb_conn_str: Service Bus connection string (empty → local fallback).
        source: Source label attached to each event.
    """
    from amplihack.workloads.hive.events import (
        make_feed_complete_event,
        make_learn_content_event,
    )

    content_pool = _build_content_pool()

    logger.info(
        "hive feed: deployment=%s turns=%d topic=%s transport=%s",
        deployment_id,
        turns,
        topic_name,
        "azure_service_bus" if sb_conn_str else "local",
    )

    events = [
        make_learn_content_event(
            deployment_id=deployment_id,
            content=content_pool[i % len(content_pool)],
            turn=i,
            source=source,
        )
        for i in range(turns)
    ]
    feed_complete_event = make_feed_complete_event(
        deployment_id=deployment_id, total_turns=turns
    )

    if sb_conn_str:
        await _publish_via_service_bus(events + [feed_complete_event], sb_conn_str, topic_name)
    else:
        logger.warning(
            "No Service Bus connection string — publishing to local event bus (dev/test only)"
        )
        _publish_local(events + [feed_complete_event])

    logger.info("hive feed: finished — %d LEARN_CONTENT + 1 FEED_COMPLETE sent", turns)


async def _publish_via_service_bus(events: list, connection_string: str, topic_name: str) -> None:
    """Publish EventData objects to Azure Service Bus."""
    try:
        from azure.servicebus import ServiceBusClient, ServiceBusMessage
    except ImportError as exc:
        raise ImportError(
            "azure-servicebus is required. Install with: pip install azure-servicebus"
        ) from exc

    loop = asyncio.get_event_loop()

    def _send_sync() -> None:
        with ServiceBusClient.from_connection_string(connection_string) as client:
            with client.get_topic_sender(topic_name=topic_name) as sender:
                for event in events:
                    body = event.model_dump_json()
                    msg = ServiceBusMessage(
                        body=body,
                        application_properties={
                            "topic": event.topic,
                            "deployment_id": event.deployment_id,
                        },
                    )
                    sender.send_messages(msg)
                    logger.debug("Published %s to %s", event.topic, topic_name)

    await loop.run_in_executor(None, _send_sync)


def _publish_local(events: list) -> None:
    """Publish EventData objects to the local in-process event bus (dev only)."""
    try:
        from agent_haymaker.events.bus import LocalEventBus

        bus = LocalEventBus()
        for event in events:
            asyncio.get_event_loop().run_until_complete(
                bus.publish(event.topic, event.model_dump())
            )
        logger.info("Published %d events to local bus", len(events))
    except Exception as exc:
        logger.warning("Local bus publish failed (%s); events logged only", exc)
        for event in events:
            logger.info("LOCAL EVENT: %s", event.model_dump_json())


def _build_content_pool() -> list[str]:
    """Load security content from amplihack_eval or fall back to hardcoded pool."""
    try:
        from amplihack_eval.data import generate_dialogue

        gt = generate_dialogue(num_turns=300, seed=42)
        items = [
            t.content
            for t in gt.turns
            if t.block_name in ("security_logs", "incidents") and t.content
        ]
        if items:
            return items
    except Exception:
        pass

    # Minimal fallback pool (same items used by feed_content.py)
    return [
        "The Log4Shell vulnerability (CVE-2021-44228) had a CVSS score of 10.0.",
        "The SolarWinds attack compromised 18,000 organizations in 2020.",
        "Supply chain attacks increased 742% between 2019 and 2022.",
        "Hardware security keys provide the strongest form of 2FA.",
        "Memory-safe languages prevent 70% of security vulnerabilities.",
        "Brute force attack detected: 847 failed SSH login attempts over 12 minutes.",
        "C2 beacon traffic detected using HTTPS tunneling on port 443.",
        "Insider threat: bulk download of 15,234 sensitive documents triggered DLP policy.",
        "Ransomware attack on production database servers — 3 servers encrypted.",
        "APT29 supply chain attack via malicious npm package; DNS tunneling detected.",
    ]
