#!/usr/bin/env python3
"""Feed learning content into the distributed hive via Azure Service Bus.

Sends LEARN_CONTENT events to the hive topic so that agents subscribed to the
event bus can ingest new knowledge.

Environment variables:
    AMPLIHACK_MEMORY_CONNECTION_STRING -- Azure Service Bus connection string
    AMPLIHACK_TOPIC_NAME               -- Service Bus topic (default: hive-graph)
    AMPLIHACK_SOURCE_AGENT             -- sender identity (default: feed-content)

Usage:
    python feed_content.py --turns 100
    python feed_content.py --turns 100 --topic hive-events
    python feed_content.py --turns 100 --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("feed_content")

# ---------------------------------------------------------------------------
# Security analyst scenario content — loaded from amplihack_eval
# ---------------------------------------------------------------------------

# Fallback hardcoded security pool used when amplihack_eval is unavailable.
_SECURITY_CONTENT_FALLBACK = [
    "The Log4Shell vulnerability (CVE-2021-44228) had a CVSS score of 10.0.",
    "The SolarWinds attack compromised 18,000 organizations in 2020.",
    "Supply chain attacks increased 742% between 2019 and 2022.",
    "Hardware security keys provide the strongest form of 2FA.",
    "Memory-safe languages prevent 70% of security vulnerabilities.",
    "Brute force attack detected from 192.168.1.45: 847 failed SSH login attempts targeting admin accounts over 12 minutes.",
    "C2 beacon traffic detected from 172.16.0.100 (svc_backup) to 185.220.101.45 on port 443 using HTTPS tunneling.",
    "Supply chain attack detected: malicious npm package event-stream@5.0.0 with crypto-mining payload found in CI pipeline.",
    "CVE-2024-3094 (xz-utils/sshd backdoor) detected on build servers; attacker used DNS tunneling via *.tunnel.attacker.net.",
    "SSRF vulnerability exploited in web application: attacker accessed AWS metadata endpoint http://169.254.169.254/latest/meta-data/.",
    "Insider threat indicator: bulk download of 15,234 sensitive documents by user jsmith detected; DLP policy triggered.",
    "INC-2024-001: Ransomware attack on production database servers; 3 servers encrypted; status: contained; CVE-2024-21626 involved.",
    "INC-2024-002: Data exfiltration via C2 server 185.220.101.45; 2.3GB exfiltrated; breach notification sent to 15,000 customers; status: remediated.",
    "INC-2024-003: APT29 (state-sponsored) supply chain attack; TTPs matched APT29; involved event-stream npm package, crypto mining on CI server, DNS tunneling, and xz-utils backdoor (CVE-2024-3094).",
    "INC-2024-004: Insider threat - bulk document download by jsmith; 15,234 documents over 4 hours; employee terminated; status: resolved.",
    "INC-2024-005: SSRF vulnerability exploitation leading to cloud metadata access; patched same day; no data exfiltration confirmed.",
    "Post-incident review complete; MFA enforced for all admin accounts after INC-2024-001 ransomware attack.",
    "All encrypted files restored from backup; attacker C2 server 185.220.101.45 blocked at firewall after INC-2024-002.",
    "Brute force attack on RDP services from multiple IPs; 10,432 attempts over 3 hours; blocked by WAF rate limiting.",
    "Privilege escalation attempt from 192.168.1.45 after successful SSH login; attacker gained root via sudo misconfiguration.",
    "DNS tunneling detected using *.tunnel.attacker.net domains; associated with APT29 campaign INC-2024-003.",
    "CVSS v3.1 base score uses Attack Vector, Attack Complexity, Privileges Required, User Interaction, Scope, and three CIA impact metrics.",
    "APT29 (Cozy Bear) is a Russian state-sponsored threat actor known for supply chain attacks and stealthy long-term persistence.",
    "Ransomware incident response playbook: isolate affected systems, preserve evidence, notify stakeholders, restore from clean backups, patch vulnerabilities.",
    "IOC correlation links 192.168.1.45 (SSH brute force), 185.220.101.45 (C2 server), event-stream@5.0.0 (malicious npm), and tunnel.attacker.net (DNS C2).",
]


def _build_security_content_pool() -> list[str]:
    """Build the security analyst content pool from amplihack_eval.

    Calls generate_dialogue(num_turns=300, seed=42) and filters turns
    to the security_logs and incidents blocks (block_name in
    {"security_logs", "incidents"}).  Falls back to
    _SECURITY_CONTENT_FALLBACK if amplihack_eval is unavailable or
    returns no security turns.

    Returns:
        List of content strings suitable for LEARN_CONTENT events.
    """
    try:
        from amplihack_eval.data import generate_dialogue

        ground_truth = generate_dialogue(num_turns=300, seed=42)
        security_turns = [
            t.content
            for t in ground_truth.turns
            if t.block_name in ("security_logs", "incidents") and t.content
        ]
        if security_turns:
            logger.info(
                "feed_content: loaded %d security turns from amplihack_eval",
                len(security_turns),
            )
            return security_turns
        logger.warning(
            "feed_content: amplihack_eval returned no security turns for num_turns=300; "
            "using fallback pool"
        )
    except Exception:
        logger.warning(
            "feed_content: could not load security content from amplihack_eval; "
            "using fallback pool",
            exc_info=True,
        )
    return list(_SECURITY_CONTENT_FALLBACK)


_CONTENT_POOL: list[str] = _build_security_content_pool()


def _build_event(content: str, source_agent: str, turn: int) -> dict:
    """Construct a LEARN_CONTENT event dict compatible with BusEvent JSON format."""
    return {
        "event_id": uuid.uuid4().hex,
        "event_type": "LEARN_CONTENT",
        "source_agent": source_agent,
        "timestamp": time.time(),
        "payload": {
            "content": content,
            "turn": turn,
            "source": "feed_content",
        },
    }


def _send_via_service_bus(
    events: list[dict],
    connection_string: str,
    topic_name: str,
) -> None:
    """Send events to an Azure Service Bus topic."""
    try:
        from azure.servicebus import ServiceBusClient, ServiceBusMessage
    except ImportError as exc:
        raise ImportError(
            "azure-servicebus package is required. Install with: pip install azure-servicebus"
        ) from exc

    import json

    logger.info("Connecting to Azure Service Bus topic '%s'", topic_name)
    with ServiceBusClient.from_connection_string(connection_string) as client:
        with client.get_topic_sender(topic_name=topic_name) as sender:
            for evt in events:
                body = json.dumps(evt, separators=(",", ":"))
                msg = ServiceBusMessage(
                    body=body,
                    application_properties={
                        "event_type": evt["event_type"],
                        "source_agent": evt["source_agent"],
                    },
                )
                sender.send_messages(msg)
                logger.info(
                    "Sent LEARN_CONTENT turn=%d event_id=%s",
                    evt["payload"]["turn"],
                    evt["event_id"],
                )


def _send_via_local_bus(events: list[dict]) -> None:
    """Simulate local event delivery by importing LocalEventBus and publishing."""
    import json
    import sys

    # Try to import from the amplihack package
    try:
        from amplihack.agents.goal_seeking.hive_mind.event_bus import (
            BusEvent,
            LocalEventBus,
        )

        bus = LocalEventBus()
        bus.subscribe("feed-content-receiver")
        for evt in events:
            bus_event = BusEvent(
                event_id=evt["event_id"],
                event_type=evt["event_type"],
                source_agent=evt["source_agent"],
                timestamp=evt["timestamp"],
                payload=evt["payload"],
            )
            bus.publish(bus_event)
            logger.info(
                "Published (local) LEARN_CONTENT turn=%d event_id=%s",
                evt["payload"]["turn"],
                evt["event_id"],
            )
        bus.close()
    except ImportError:
        # Fallback: just log each event as JSON
        for evt in events:
            logger.info(
                "DRY-RUN LEARN_CONTENT turn=%d payload=%s",
                evt["payload"]["turn"],
                json.dumps(evt["payload"], separators=(",", ":")),
            )


def run(turns: int, topic_name: str, source_agent: str, dry_run: bool) -> None:
    """Send *turns* LEARN_CONTENT events to the hive."""
    connection_string = os.environ.get("AMPLIHACK_MEMORY_CONNECTION_STRING", "")

    logger.info(
        "feed_content: turns=%d topic=%s source=%s transport=%s",
        turns,
        topic_name,
        source_agent,
        "dry-run" if dry_run else ("azure_service_bus" if connection_string else "local"),
    )

    events: list[dict] = []
    for turn in range(turns):
        content = _CONTENT_POOL[turn % len(_CONTENT_POOL)]
        events.append(_build_event(content, source_agent, turn))

    if dry_run:
        import json

        for evt in events:
            logger.info(
                "DRY-RUN turn=%d content='%s...'",
                evt["payload"]["turn"],
                evt["payload"]["content"][:60],
            )
        logger.info("DRY-RUN complete — %d events generated, none sent", len(events))
        return

    if connection_string:
        _send_via_service_bus(events, connection_string, topic_name)
    else:
        logger.warning(
            "AMPLIHACK_MEMORY_CONNECTION_STRING not set — using local event bus simulation"
        )
        _send_via_local_bus(events)

    logger.info("feed_content: finished sending %d LEARN_CONTENT events", len(events))

    # Send FEED_COMPLETE sentinel so agents know all content has been delivered
    if connection_string:
        _send_feed_complete(connection_string, topic_name, source_agent, len(events))


def _send_feed_complete(
    connection_string: str, topic_name: str, source_agent: str, total_turns: int
) -> None:
    """Publish a FEED_COMPLETE sentinel event after all content is sent."""
    import json

    from azure.servicebus import ServiceBusClient, ServiceBusMessage

    event = {
        "event_id": uuid.uuid4().hex,
        "event_type": "FEED_COMPLETE",
        "source_agent": source_agent,
        "timestamp": time.time(),
        "payload": {"total_turns": total_turns},
    }
    with ServiceBusClient.from_connection_string(connection_string) as client:
        with client.get_topic_sender(topic_name=topic_name) as sender:
            body = json.dumps(event, separators=(",", ":"))
            msg = ServiceBusMessage(
                body=body,
                application_properties={
                    "event_type": "FEED_COMPLETE",
                    "source_agent": source_agent,
                },
            )
            sender.send_messages(msg)
    logger.info("feed_content: sent FEED_COMPLETE sentinel (total_turns=%d)", total_turns)


def main() -> None:
    import warnings

    warnings.warn(
        "\n\nDEPRECATED: feed_content.py is superseded by the haymaker CLI extension.\n"
        "Use instead:  haymaker hive feed --deployment-id <ID> --turns <N>\n"
        "This script will be removed in a future release.\n",
        DeprecationWarning,
        stacklevel=1,
    )

    parser = argparse.ArgumentParser(
        description="[DEPRECATED] Feed learning content into the distributed hive via Service Bus. "
        "Use 'haymaker hive feed' instead."
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=100,
        help="Number of LEARN_CONTENT events to send (default: 100)",
    )
    parser.add_argument(
        "--topic",
        dest="topic_name",
        default=os.environ.get("AMPLIHACK_TOPIC_NAME", "hive-graph"),
        help="Service Bus topic name (default: hive-graph)",
    )
    parser.add_argument(
        "--source-agent",
        default=os.environ.get("AMPLIHACK_SOURCE_AGENT", "feed-content"),
        help="Source agent identifier (default: feed-content)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate events but do not send them",
    )
    args = parser.parse_args()

    try:
        run(
            turns=args.turns,
            topic_name=args.topic_name,
            source_agent=args.source_agent,
            dry_run=args.dry_run,
        )
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception:
        logger.exception("feed_content failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
