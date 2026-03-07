#!/usr/bin/env python3
"""query_hive.py -- Query the live Azure Hive Mind for Q&A evaluation.

Sends a network_graph.search_query event to the live Azure hive agents via
Azure Service Bus and collects their network_graph.search_response replies.

The live hive runs 20 Container App agents (agent-0 .. agent-19) that each
hold a shard of the distributed knowledge graph. This script acts as an
external query client: it publishes a search query and fans in responses.

Architecture
------------
    query_hive.py
        │
        │  publishes network_graph.search_query
        ▼
    Azure Service Bus (topic: hive-graph)
        │
        ├─► agent-0 subscription → agent-0 (Container App) → search_response
        ├─► agent-1 subscription → agent-1 (Container App) → search_response
        │   ...
        └─► agent-N subscription → agent-N (Container App) → search_response
        │
        └─► eval-query-agent subscription ← responses collected here

Live Hive Architecture Notes
-----------------------------
The live hive agents each run:
    Memory(topology="distributed", transport="azure_service_bus")

This creates:
 1. A CognitiveAdapter backed by Kuzu at /data/agent-N/  -- holds LEARN_CONTENT facts
 2. A NetworkGraphStore backed by Kuzu at /data/agent-N/graph_store/ -- handles search protocol

Facts ingested via LEARN_CONTENT events go into the CognitiveAdapter's DB.
The NetworkGraphStore's DB is populated only via create_node replication events
from other NetworkGraphStore instances.

This means: search_query against the live hive will return results IF data
was ingested into the NetworkGraphStore via the network replication protocol.
Use --seed to populate via the Service Bus before running --run-eval.

Usage
-----
    # Seed the live hive and run Q&A eval
    python experiments/hive_mind/query_hive.py --seed --run-eval --output results.json

    # Single query (after seeding)
    python experiments/hive_mind/query_hive.py --query "What is Newton's second law?"

    # Demo mode: run eval locally with DistributedHiveGraph (no Azure needed)
    python experiments/hive_mind/query_hive.py --demo

    # Live diagnostic: connect, query, show what the live hive returns
    python experiments/hive_mind/query_hive.py --run-eval

Environment Variables
---------------------
    HIVE_CONNECTION_STRING  Azure Service Bus connection string (required)
    HIVE_TOPIC              Topic name (default: hive-graph)
    HIVE_SUBSCRIPTION       Subscription name for receiving responses
                            (default: eval-query-agent)
    HIVE_TIMEOUT            Response wait timeout in seconds (default: 10)

Prerequisites
-------------
    pip install azure-servicebus
    export HIVE_CONNECTION_STRING="Endpoint=sb://..."
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
import uuid
from typing import Any

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)
logger = logging.getLogger("query_hive")

# ---------------------------------------------------------------------------
# Constants / defaults
# ---------------------------------------------------------------------------

_DEFAULT_CONNECTION_STRING = os.environ.get("HIVE_CONNECTION_STRING", "")
_DEFAULT_TOPIC = os.environ.get("HIVE_TOPIC", "hive-graph")
_DEFAULT_SUBSCRIPTION = os.environ.get("HIVE_SUBSCRIPTION", "eval-query-agent")
_DEFAULT_TIMEOUT = float(os.environ.get("HIVE_TIMEOUT", "10"))

# Event type constants (must match NetworkGraphStore)
_OP_SEARCH_QUERY = "network_graph.search_query"
_OP_SEARCH_RESPONSE = "network_graph.search_response"
_OP_CREATE_NODE = "network_graph.create_node"

# ---------------------------------------------------------------------------
# Fact corpus: matches feed_content.py + classic science facts
# (used for both seeding and demo mode)
# ---------------------------------------------------------------------------

_FACT_CORPUS: list[dict[str, str]] = [
    # Biology
    {"concept": "cells", "content": "Cells are the fundamental units of life and contain organelles."},
    {"concept": "dna", "content": "DNA encodes genetic information using four nucleotide bases: A, T, C, G."},
    {"concept": "proteins", "content": "Proteins are chains of amino acids and act as biological catalysts called enzymes."},
    {"concept": "photosynthesis", "content": "Photosynthesis converts CO2 and water into glucose using light energy stored as chemical energy."},
    {"concept": "cells", "content": "The mitochondria is the powerhouse of the cell producing ATP via oxidative phosphorylation."},
    # Chemistry
    {"concept": "water", "content": "Water molecule is H2O with bent geometry and high specific heat capacity."},
    {"concept": "bonds", "content": "Covalent bonds share electron pairs between atoms; ionic bonds form between oppositely charged ions."},
    {"concept": "acids", "content": "pH measures hydrogen ion concentration on a log scale; acids donate protons per Bronsted-Lowry theory."},
    {"concept": "water", "content": "Water boiling point at sea level is 100 degrees Celsius or 212 Fahrenheit."},
    {"concept": "bonds", "content": "Hydrogen bonds are weak intermolecular forces important in protein and DNA structure."},
    # Physics
    {"concept": "mechanics", "content": "Newton second law states F equals ma where F is force mass times acceleration."},
    {"concept": "waves", "content": "The speed of light in a vacuum is approximately 299792458 metres per second."},
    {"concept": "relativity", "content": "E equals mc squared relates mass and energy via the speed of light squared."},
    {"concept": "gravity", "content": "Gravitational force is proportional to mass product; Earth surface gravity is approximately 9.81 m per s squared."},
    {"concept": "quantum", "content": "Heisenberg uncertainty principle limits simultaneous precision of position and momentum."},
    # Mathematics
    {"concept": "geometry", "content": "Pythagorean theorem states a squared plus b squared equals c squared for right triangles."},
    {"concept": "calculus", "content": "Derivatives measure instantaneous rate of change; integrals compute area under curves."},
    {"concept": "geometry", "content": "Pi is the ratio of circumference to diameter of a circle approximately 3.14159."},
    {"concept": "statistics", "content": "Mean is the sum of values divided by count; standard deviation measures spread around the mean."},
    {"concept": "number_theory", "content": "There are infinitely many prime numbers; every integer has a unique prime factorization."},
    # Computer Science
    {"concept": "algorithms", "content": "Binary search runs in O log n time by halving the search space each iteration."},
    {"concept": "databases", "content": "ACID properties ensure transaction reliability: Atomicity Consistency Isolation Durability."},
    {"concept": "distributed", "content": "CAP theorem states distributed systems can guarantee only two of Consistency Availability Partition tolerance."},
    {"concept": "data_structures", "content": "Hash tables provide O 1 average lookup time using hash functions for key-value storage."},
    {"concept": "distributed", "content": "Consistent hashing distributes load across nodes while minimising redistribution on topology changes."},
    # Hive mind (from feed_content.py)
    {"concept": "hive", "content": "The hive mind architecture allows multiple AI agents to share a distributed memory graph."},
    {"concept": "gossip", "content": "Gossip protocols propagate information in O log N rounds through random peer exchange."},
    {"concept": "dht", "content": "Distributed hash tables DHTs enable decentralised key-value lookups across peer networks."},
    {"concept": "bloom", "content": "Bloom filters provide probabilistic set membership testing with controllable false-positive rates."},
    {"concept": "raft", "content": "Raft is a consensus algorithm designed to be more understandable than Paxos."},
]

# ---------------------------------------------------------------------------
# Q&A evaluation dataset
# ---------------------------------------------------------------------------

# Each entry: (domain, question, expected_keywords)
QA_EVAL_DATASET: list[tuple[str, str, list[str]]] = [
    # Biology
    ("biology", "What are cells made of?", ["unit", "life"]),
    ("biology", "How does DNA store information?", ["nucleotide", "genetic"]),
    ("biology", "What do enzymes do?", ["catalyst", "protein"]),
    # Chemistry
    ("chemistry", "What is the structure of water?", ["H2O", "bent"]),
    ("chemistry", "How do covalent bonds work?", ["electron", "share"]),
    ("chemistry", "What does pH measure?", ["hydrogen", "concentration"]),
    # Physics
    ("physics", "What is Newton's second law?", ["F", "ma"]),
    ("physics", "What is the speed of light?", ["299792"]),
    ("physics", "What does E=mc^2 mean?", ["mass", "energy"]),
    # Mathematics
    ("mathematics", "What is the Pythagorean theorem?", ["a squared", "b squared", "c squared"]),
    ("mathematics", "What does a derivative measure?", ["rate", "change"]),
    ("mathematics", "What is Pi?", ["circumference", "diameter"]),
    # Computer Science
    ("computer_science", "What is the time complexity of binary search?", ["log", "n"]),
    ("computer_science", "What are ACID properties?", ["transaction", "reliab"]),
    ("computer_science", "What does CAP theorem state?", ["consistency", "partition"]),
]


# ---------------------------------------------------------------------------
# HiveQueryClient — live Azure Service Bus query client
# ---------------------------------------------------------------------------


class HiveQueryClient:
    """Client for querying the live Azure hive via Service Bus.

    Publishes network_graph.search_query events and collects
    network_graph.search_response replies from live agents.

    Also supports seeding facts into the NetworkGraphStore via
    network_graph.create_node events for subsequent querying.

    Args:
        connection_string: Azure Service Bus connection string.
        topic_name: Service Bus topic name (default: hive-graph).
        subscription_name: Subscription to receive responses on.
        timeout: Max seconds to wait for agent responses.
        agent_id: Identity used as source_agent in published events.
    """

    def __init__(
        self,
        connection_string: str = _DEFAULT_CONNECTION_STRING,
        topic_name: str = _DEFAULT_TOPIC,
        subscription_name: str = _DEFAULT_SUBSCRIPTION,
        timeout: float = _DEFAULT_TIMEOUT,
        agent_id: str = "eval-query-agent",
    ) -> None:
        try:
            from azure.servicebus import ServiceBusClient as _SBClient
        except ImportError as exc:
            raise ImportError(
                "azure-servicebus is required. Install with: pip install azure-servicebus"
            ) from exc

        self._connection_string = connection_string
        self._topic_name = topic_name
        self._subscription_name = subscription_name
        self._timeout = timeout
        self._agent_id = agent_id

        self._client = _SBClient.from_connection_string(connection_string)
        self._sender = self._client.get_topic_sender(topic_name=topic_name)
        self._receiver = self._client.get_subscription_receiver(
            topic_name=topic_name,
            subscription_name=subscription_name,
        )

        # Pending queries: query_id -> {event, results}
        self._pending: dict[str, dict[str, Any]] = {}
        self._pending_lock = threading.Lock()

        # Start background receiver thread
        self._running = True
        self._thread = threading.Thread(
            target=self._receive_loop,
            daemon=True,
            name="hive-query-receiver",
        )
        self._thread.start()
        logger.info(
            "HiveQueryClient connected to %s (subscription: %s)",
            topic_name,
            subscription_name,
        )

    def seed_facts(
        self,
        facts: list[dict[str, str]] | None = None,
        table: str = "hive_facts",
    ) -> int:
        """Seed facts into the live hive's NetworkGraphStore via create_node events.

        Publishes network_graph.create_node events to the Service Bus topic.
        Each live agent's NetworkGraphStore will receive and store these nodes
        in its local Kuzu DB, making them searchable via search_query.

        Args:
            facts: List of fact dicts with 'concept' and 'content' keys.
                   Defaults to _FACT_CORPUS.
            table: Table name for the facts (default: hive_facts).

        Returns:
            Number of facts seeded.
        """
        from azure.servicebus import ServiceBusMessage

        corpus = facts or _FACT_CORPUS
        count = 0
        for fact in corpus:
            node_id = uuid.uuid4().hex[:12]
            payload = {
                "event_id": uuid.uuid4().hex,
                "event_type": _OP_CREATE_NODE,
                "source_agent": self._agent_id,
                "timestamp": time.time(),
                "payload": {
                    "table": table,
                    "node_id": node_id,
                    "properties": {
                        "node_id": node_id,
                        "concept": fact.get("concept", ""),
                        "content": fact.get("content", ""),
                        "confidence": fact.get("confidence", "0.95"),
                        "source": "eval-seed",
                    },
                },
            }
            try:
                msg = ServiceBusMessage(
                    body=json.dumps(payload, separators=(",", ":")),
                    application_properties={
                        "event_type": _OP_CREATE_NODE,
                        "source_agent": self._agent_id,
                    },
                )
                self._sender.send_messages(msg)
                count += 1
            except Exception:
                logger.debug("Failed to seed fact: %s", fact.get("content", ""), exc_info=True)

        logger.info("Seeded %d facts into table=%s", count, table)
        return count

    def query(
        self,
        text: str,
        table: str = "hive_facts",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Query the live hive for facts matching `text`.

        Publishes a search_query event and waits up to self._timeout seconds
        for agent responses.

        Args:
            text: The search query text.
            table: Graph table to search (default: hive_facts).
            limit: Max results per agent.

        Returns:
            Deduplicated list of matching fact dicts, sorted by confidence.
        """
        from azure.servicebus import ServiceBusMessage

        query_id = uuid.uuid4().hex
        event = threading.Event()
        collected: list[dict[str, Any]] = []

        with self._pending_lock:
            self._pending[query_id] = {"event": event, "results": collected}

        # Build and publish the search query event
        payload = {
            "event_id": uuid.uuid4().hex,
            "event_type": _OP_SEARCH_QUERY,
            "source_agent": self._agent_id,
            "timestamp": time.time(),
            "payload": {
                "query_id": query_id,
                "table": table,
                "text": text,
                "fields": None,
                "limit": limit,
            },
        }

        try:
            msg = ServiceBusMessage(
                body=json.dumps(payload, separators=(",", ":")),
                application_properties={
                    "event_type": _OP_SEARCH_QUERY,
                    "source_agent": self._agent_id,
                },
            )
            self._sender.send_messages(msg)
            logger.debug("Published search_query id=%s text=%r", query_id, text)
        except Exception:
            logger.exception("Failed to publish search query")
            with self._pending_lock:
                self._pending.pop(query_id, None)
            return []

        # Wait for responses
        event.wait(timeout=self._timeout)

        with self._pending_lock:
            self._pending.pop(query_id, None)

        return self._deduplicate(collected)

    def close(self) -> None:
        """Close the client and release resources."""
        self._running = False
        try:
            self._receiver.close()
        except Exception:
            pass
        try:
            self._sender.close()
        except Exception:
            pass
        try:
            self._client.close()
        except Exception:
            pass
        if self._thread.is_alive():
            self._thread.join(timeout=3.0)

    # ------------------------------------------------------------------
    # Background receiver
    # ------------------------------------------------------------------

    def _receive_loop(self) -> None:
        """Background thread: drain subscription and dispatch responses."""
        while self._running:
            try:
                messages = self._receiver.receive_messages(
                    max_message_count=50, max_wait_time=1
                )
                for msg in messages:
                    try:
                        self._handle_message(msg)
                        self._receiver.complete_message(msg)
                    except Exception:
                        logger.debug("Error handling message", exc_info=True)
                        try:
                            self._receiver.abandon_message(msg)
                        except Exception:
                            pass
            except Exception:
                if self._running:
                    logger.debug("Error in receive loop", exc_info=True)
                time.sleep(0.5)

    def _handle_message(self, msg: Any) -> None:
        """Parse a Service Bus message and dispatch to waiting queries."""
        try:
            body = b"".join(msg.body) if hasattr(msg.body, "__iter__") else msg.body
            if isinstance(body, (bytes, bytearray)):
                body = body.decode("utf-8")
            data = json.loads(body)
        except Exception:
            logger.debug("Failed to parse message body", exc_info=True)
            return

        event_type = data.get("event_type", "")
        if event_type != _OP_SEARCH_RESPONSE:
            return

        inner = data.get("payload", {})
        query_id = inner.get("query_id", "")
        results = inner.get("results", [])

        with self._pending_lock:
            pending = self._pending.get(query_id)

        if pending is None:
            return

        pending["results"].extend(results)
        pending["event"].set()
        logger.debug(
            "Received %d results for query_id=%s from %s",
            len(results),
            query_id,
            data.get("source_agent", "?"),
        )

    @staticmethod
    def _deduplicate(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate results by content, sort by confidence descending."""
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for r in results:
            content = r.get("content", r.get("outcome", ""))
            if content and content not in seen:
                seen.add(content)
                deduped.append(r)
        try:
            deduped.sort(
                key=lambda r: float(r.get("confidence", 0.0)),
                reverse=True,
            )
        except (TypeError, ValueError):
            pass
        return deduped


# ---------------------------------------------------------------------------
# Demo mode: local DistributedHiveGraph (no Azure needed)
# ---------------------------------------------------------------------------


def run_demo_eval(output_path: str | None = None) -> dict[str, Any]:
    """Run the Q&A eval against a local in-memory DistributedHiveGraph.

    Populates the hive with _FACT_CORPUS, then scores QA_EVAL_DATASET.
    This demonstrates the hive query protocol without Azure connectivity.

    Args:
        output_path: Optional path to write JSON results.

    Returns:
        Results dict.
    """
    print("=" * 70)
    print("HIVE Q&A EVAL (DEMO — local DistributedHiveGraph)")
    print(f"Facts in corpus: {len(_FACT_CORPUS)}")
    print(f"Questions: {len(QA_EVAL_DATASET)}")
    print("=" * 70)
    print()

    # Import hive mind components
    try:
        from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
            DistributedHiveGraph,
        )
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import HiveFact
    except ImportError as exc:
        print(f"ERROR: Could not import amplihack: {exc}")
        print("Install with: pip install -e /path/to/amplihack")
        return {}

    # Build a 5-agent distributed hive
    hive = DistributedHiveGraph(hive_id="demo-eval", replication_factor=3, query_fanout=5)
    for i in range(5):
        hive.register_agent(f"agent-{i}", domain="general")

    # Seed facts into the hive
    for fact_dict in _FACT_CORPUS:
        fact = HiveFact(
            fact_id="",
            content=fact_dict["content"],
            concept=fact_dict["concept"],
            confidence=0.95,
            source_agent="eval-seed",
        )
        # Distribute across agents round-robin
        for i in range(5):
            hive.promote_fact(f"agent-{i}", fact)
            break  # just one agent per fact for DHT routing

    t0 = time.time()
    results: list[dict[str, Any]] = []
    by_domain: dict[str, list[bool]] = {}

    print(f"{'Domain':20s} {'Hit':5s} {'Results':8s} | Question")
    print("-" * 70)

    for domain, question, keywords in QA_EVAL_DATASET:
        facts = hive.query_facts(question, limit=10)
        result_dicts = [
            {"content": f.content, "concept": f.concept, "confidence": f.confidence}
            for f in facts
        ]
        hit = _score_response(result_dicts, keywords)
        by_domain.setdefault(domain, []).append(hit)

        status = "HIT " if hit else "MISS"
        print(
            f"  {domain:18s} {status} {len(facts):3d} results"
            f" | {question[:42]}"
        )

        results.append(
            {
                "domain": domain,
                "question": question,
                "expected_keywords": keywords,
                "hit": hit,
                "result_count": len(facts),
                "top_results": result_dicts[:3],
            }
        )

    elapsed = time.time() - t0
    total = len(results)
    hits = sum(1 for r in results if r["hit"])

    domain_scores = {
        d: {"hits": sum(v), "total": len(v), "pct": 100 * sum(v) / len(v)}
        for d, v in by_domain.items()
    }

    print("-" * 70)
    print()
    print("=" * 70)
    print("RESULTS (DEMO MODE)")
    print("=" * 70)
    print(f"  Overall:   {hits}/{total} ({100 * hits / total:.1f}%)")
    print()
    print("  By domain:")
    for d, s in sorted(domain_scores.items()):
        print(f"    {d:20s}: {s['hits']}/{s['total']} ({s['pct']:.0f}%)")
    print(f"\n  Total time: {elapsed:.2f}s")
    print("=" * 70)

    output = {
        "mode": "demo_local",
        "summary": {
            "total_questions": total,
            "hits": hits,
            "accuracy_pct": round(100 * hits / total, 2),
            "elapsed_s": round(elapsed, 2),
            "hive_type": "DistributedHiveGraph (local)",
            "agents": 5,
            "facts_seeded": len(_FACT_CORPUS),
        },
        "domain_scores": domain_scores,
        "questions": results,
    }

    if output_path:
        with open(output_path, "w") as fh:
            json.dump(output, fh, indent=2)
        print(f"\nResults written to: {output_path}")

    hive.close()
    return output


# ---------------------------------------------------------------------------
# Keyword scoring helper
# ---------------------------------------------------------------------------


def _score_response(results: list[dict[str, Any]], keywords: list[str]) -> bool:
    """Return True if any result contains all expected keywords (case-insensitive)."""
    for r in results:
        content = (
            r.get("content", r.get("outcome", r.get("concept", ""))) + " "
            + r.get("concept", "")
        ).lower()
        if all(kw.lower() in content for kw in keywords):
            return True
    return False


# ---------------------------------------------------------------------------
# Live eval runner (Service Bus mode)
# ---------------------------------------------------------------------------


def run_eval(
    client: HiveQueryClient,
    table: str = "hive_facts",
    output_path: str | None = None,
) -> dict[str, Any]:
    """Run the Q&A eval dataset against the live hive.

    Queries each question in QA_EVAL_DATASET, scores the response using
    keyword matching, and reports accuracy per domain and overall.

    Args:
        client: Connected HiveQueryClient instance.
        table: Table name to query (must match what was seeded).
        output_path: Optional path to write JSON results.

    Returns:
        Results dict with per-question and aggregate scores.
    """
    print("=" * 70)
    print("LIVE AZURE HIVE Q&A EVAL")
    print(f"Hive: hive-sb-dj2qo2w7vu5zi / topic: {client._topic_name}")
    print(f"Table: {table}")
    print(f"Questions: {len(QA_EVAL_DATASET)}")
    print(f"Timeout per query: {client._timeout}s")
    print("=" * 70)
    print()

    t0 = time.time()
    results: list[dict[str, Any]] = []
    by_domain: dict[str, list[bool]] = {}

    print(f"{'Domain':20s} {'Hit':5s} {'Results':8s} | Question")
    print("-" * 70)

    for domain, question, keywords in QA_EVAL_DATASET:
        t_q = time.time()
        hive_results = client.query(question, table=table, limit=10)
        hit = _score_response(hive_results, keywords)
        elapsed_q = time.time() - t_q

        by_domain.setdefault(domain, []).append(hit)

        status = "HIT " if hit else "MISS"
        print(
            f"  {domain:18s} {status} {len(hive_results):3d} results"
            f" | {question[:42]}"
        )
        logger.debug(
            "Q: %r → %d results in %.2fs, hit=%s",
            question,
            len(hive_results),
            elapsed_q,
            hit,
        )

        results.append(
            {
                "domain": domain,
                "question": question,
                "expected_keywords": keywords,
                "hit": hit,
                "result_count": len(hive_results),
                "top_results": hive_results[:3],
                "elapsed_s": round(elapsed_q, 2),
            }
        )

    elapsed = time.time() - t0
    total = len(results)
    hits = sum(1 for r in results if r["hit"])

    domain_scores = {
        d: {"hits": sum(v), "total": len(v), "pct": 100 * sum(v) / len(v)}
        for d, v in by_domain.items()
    }

    print("-" * 70)
    print()
    print("=" * 70)
    print("RESULTS (LIVE HIVE)")
    print("=" * 70)
    print(f"  Overall:   {hits}/{total} ({100 * hits / total:.1f}%)")
    print()
    print("  By domain:")
    for d, s in sorted(domain_scores.items()):
        print(f"    {d:20s}: {s['hits']}/{s['total']} ({s['pct']:.0f}%)")
    print(f"\n  Total time: {elapsed:.2f}s")
    print("=" * 70)

    if hits == 0:
        print()
        print("NOTE: 0 results from live hive. This typically means agents'")
        print("NetworkGraphStore has not been seeded. Run with --seed first:")
        print("  python experiments/hive_mind/query_hive.py --seed --run-eval")

    output = {
        "mode": "live",
        "summary": {
            "total_questions": total,
            "hits": hits,
            "accuracy_pct": round(100 * hits / total, 2),
            "elapsed_s": round(elapsed, 2),
            "hive_namespace": "hive-sb-dj2qo2w7vu5zi",
            "topic": client._topic_name,
            "timeout_s": client._timeout,
            "table": table,
        },
        "domain_scores": domain_scores,
        "questions": results,
    }

    if output_path:
        with open(output_path, "w") as fh:
            json.dump(output, fh, indent=2)
        print(f"\nResults written to: {output_path}")

    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="query_hive",
        description="Query the live Azure Hive Mind for Q&A evaluation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Demo mode (local, no Azure needed):
  python query_hive.py --demo

  # Seed live hive then run eval:
  python query_hive.py --seed --run-eval --output results.json

  # Single query against live hive (after seeding):
  python query_hive.py --query "What is Newton's second law?"

  # Diagnose live hive (may return 0 if not seeded):
  python query_hive.py --run-eval
""",
    )
    p.add_argument(
        "--query", "-q",
        default="",
        help="A single query to send to the hive.",
    )
    p.add_argument(
        "--run-eval",
        action="store_true",
        help="Run the built-in Q&A eval dataset against the live hive.",
    )
    p.add_argument(
        "--seed",
        action="store_true",
        help="Seed the live hive with the built-in fact corpus before querying.",
    )
    p.add_argument(
        "--demo",
        action="store_true",
        help="Run eval locally using DistributedHiveGraph (no Azure needed).",
    )
    p.add_argument(
        "--output", "-o",
        default="",
        help="Path to write eval results JSON (with --run-eval or --demo).",
    )
    p.add_argument(
        "--table",
        default="hive_facts",
        help="Graph table to query/seed (default: hive_facts).",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max results per query (default: 10).",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=_DEFAULT_TIMEOUT,
        help=f"Response wait timeout in seconds (default: {_DEFAULT_TIMEOUT}).",
    )
    p.add_argument(
        "--connection-string",
        default=_DEFAULT_CONNECTION_STRING,
        help="Azure Service Bus connection string (overrides HIVE_CONNECTION_STRING).",
    )
    p.add_argument(
        "--topic",
        default=_DEFAULT_TOPIC,
        help=f"Service Bus topic name (default: {_DEFAULT_TOPIC}).",
    )
    p.add_argument(
        "--subscription",
        default=_DEFAULT_SUBSCRIPTION,
        help=f"Subscription for receiving responses (default: {_DEFAULT_SUBSCRIPTION}).",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.verbose:
        logging.getLogger("query_hive").setLevel(logging.DEBUG)

    if not args.query and not args.run_eval and not args.seed and not args.demo:
        _build_parser().print_help()
        return 0

    # Demo mode — no Azure needed
    if args.demo:
        run_demo_eval(output_path=args.output or None)
        return 0

    # All other modes need a live client
    client = HiveQueryClient(
        connection_string=args.connection_string,
        topic_name=args.topic,
        subscription_name=args.subscription,
        timeout=args.timeout,
    )

    try:
        if args.seed:
            print(f"Seeding {len(_FACT_CORPUS)} facts into live hive (table={args.table})...")
            n = client.seed_facts(table=args.table)
            print(f"Seeded {n} facts. Waiting 5s for propagation...")
            time.sleep(5)

        if args.run_eval:
            run_eval(client, table=args.table, output_path=args.output or None)
            return 0

        if args.query:
            print(f"Querying live hive: {args.query!r}")
            print(f"Table: {args.table}, Timeout: {args.timeout}s\n")
            results = client.query(args.query, table=args.table, limit=args.limit)
            if not results:
                print("No results returned.")
                print("Tip: Run with --seed first to populate the NetworkGraphStore.")
                return 0
            print(f"Results ({len(results)}):")
            for i, r in enumerate(results, 1):
                content = r.get("content", r.get("outcome", ""))
                concept = r.get("concept", r.get("context", ""))
                conf = r.get("confidence", 0.0)
                source = r.get("source", r.get("source_agent", ""))
                print(f"  {i:2d}. [{conf}] {content[:80]}")
                if concept:
                    print(f"       concept: {concept}")
                if source:
                    print(f"       source:  {source}")
            return 0

    finally:
        client.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
