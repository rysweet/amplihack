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
# Sample learning content — varied facts for hive ingestion
# ---------------------------------------------------------------------------
_CONTENT_POOL = [
    "The mitochondria is the powerhouse of the cell, producing ATP via oxidative phosphorylation.",
    "Photosynthesis converts light energy into chemical energy stored as glucose.",
    "DNA encodes genetic information using four nucleotide bases: A, T, C, G.",
    "RNA polymerase transcribes DNA into messenger RNA during gene expression.",
    "The human brain contains approximately 86 billion neurons.",
    "Neurons communicate via electrochemical signals across synaptic junctions.",
    "The speed of light in a vacuum is approximately 299,792,458 metres per second.",
    "General relativity describes gravity as the curvature of spacetime caused by mass.",
    "Quantum entanglement allows correlated measurement outcomes regardless of distance.",
    "The Heisenberg uncertainty principle limits simultaneous precision of position and momentum.",
    "Water has a specific heat capacity of 4,186 J/(kg·K), making it an excellent thermal buffer.",
    "The boiling point of water at sea level is 100 °C (212 °F).",
    "Plate tectonics explains the movement of Earth's lithospheric plates.",
    "The Cambrian explosion approximately 541 million years ago saw rapid diversification of life.",
    "CRISPR-Cas9 is a molecular tool for precise genome editing in living cells.",
    "The blockchain is an append-only distributed ledger secured by cryptographic hashes.",
    "Neural networks learn by adjusting synaptic weights via gradient descent.",
    "The transformer architecture underpins most modern large language models.",
    "Attention mechanisms allow models to weigh the relevance of different input tokens.",
    "Retrieval-augmented generation (RAG) combines external knowledge retrieval with LLM generation.",
    "The Turing test evaluates a machine's ability to exhibit human-like conversation.",
    "Von Neumann architecture separates memory from processing units.",
    "Moore's Law historically described a doubling of transistor density every ~18 months.",
    "TCP/IP is the fundamental protocol suite for internet communication.",
    "TLS encrypts network traffic to prevent eavesdropping and tampering.",
    "The CAP theorem states that distributed systems can guarantee only two of: Consistency, Availability, Partition tolerance.",
    "Consistent hashing distributes load across nodes while minimising redistribution on topology changes.",
    "Bloom filters provide probabilistic set membership testing with controllable false-positive rates.",
    "CRDTs (Conflict-free Replicated Data Types) enable eventual consistency without coordination.",
    "The OODA loop (Observe, Orient, Decide, Act) models rapid iterative decision-making.",
    "Distributed hash tables (DHTs) enable decentralised key-value lookups across peer networks.",
    "Gossip protocols propagate information in O(log N) rounds through random peer exchange.",
    "The Byzantine fault tolerance problem addresses consensus in the presence of malicious nodes.",
    "Raft is a consensus algorithm designed to be more understandable than Paxos.",
    "Azure Service Bus provides reliable cloud messaging with at-least-once delivery guarantees.",
    "Azure Container Apps simplifies deployment of containerised microservices with built-in scaling.",
    "Kuzu is an embeddable graph database optimised for in-process analytical workloads.",
    "Knowledge graphs represent entities as nodes and relationships as typed edges.",
    "Semantic similarity can be measured by the cosine distance between embedding vectors.",
    "Reciprocal Rank Fusion (RRF) merges ranked lists from multiple retrieval sources.",
    "The six-type cognitive memory model maps to human memory: sensory, working, episodic, semantic, procedural, prospective.",
    "Episodic memory records autobiographical events with temporal context.",
    "Semantic memory stores distilled, language-independent knowledge.",
    "Working memory has bounded capacity and holds the currently active task context.",
    "Prospective memory encodes future-oriented trigger-action pairs.",
    "Procedural memory captures reusable step-by-step procedures.",
    "Agent specialisation improves recall by routing queries to domain-expert nodes.",
    "The hive mind architecture allows multiple AI agents to share a distributed memory graph.",
    "Federation organises agents into groups, each with its own DHT, connected by a root hive.",
    "Replication factor R=3 ensures fact availability even if two hive nodes fail simultaneously.",
]


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Feed learning content into the distributed hive via Service Bus."
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
