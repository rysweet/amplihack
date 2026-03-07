#!/usr/bin/env python3
"""query_hive.py -- Query the live Azure Hive Mind with security analyst Q&A evaluation.

Sends a network_graph.search_query event to the live Azure hive agents via
Azure Service Bus and collects their network_graph.search_response replies.

Uses amplihack_eval to generate security analyst scenario questions (via
generate_dialogue and generate_questions) and grade answers semantically
(via grade_answer).

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
    # Seed the live hive and run security analyst Q&A eval
    python experiments/hive_mind/query_hive.py --seed --run-eval --output results.json

    # Single query (after seeding)
    python experiments/hive_mind/query_hive.py --query "What CVE was used in the supply chain attack?"

    # Demo mode: run eval locally with DistributedHiveGraph (no Azure needed)
    python experiments/hive_mind/query_hive.py --demo

    # Live diagnostic: connect, query, show what the live hive returns
    python experiments/hive_mind/query_hive.py --run-eval

    # Run eval 3 times and report median + stddev of scores
    python experiments/hive_mind/query_hive.py --run-eval --repeats 3

Environment Variables
---------------------
    HIVE_CONNECTION_STRING  Azure Service Bus connection string (required)
    HIVE_TOPIC              Topic name (default: hive-graph)
    HIVE_SUBSCRIPTION       Subscription name for receiving responses
                            (default: eval-query-agent)
    HIVE_TIMEOUT            Response wait timeout in seconds (default: 10)
    ANTHROPIC_API_KEY       Required for grade_answer semantic grading

Prerequisites
-------------
    pip install azure-servicebus amplihack-agent-eval anthropic
    export HIVE_CONNECTION_STRING="Endpoint=sb://..."
    export ANTHROPIC_API_KEY="sk-ant-..."
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
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
# Security analyst fact corpus (for seeding the hive)
# Dynamically loaded from amplihack_eval.data.generate_dialogue security blocks
# so that seeded facts match the eval questions generated from the same corpus.
# ---------------------------------------------------------------------------

_FACT_CORPUS_FALLBACK: list[dict[str, str]] = [
    # Security incidents and CVEs (static fallback when amplihack_eval unavailable)
    {"concept": "log4shell", "content": "The Log4Shell vulnerability (CVE-2021-44228) had a CVSS score of 10.0."},
    {"concept": "solarwinds", "content": "The SolarWinds attack compromised 18,000 organizations in 2020."},
    {"concept": "supply_chain", "content": "Supply chain attacks increased 742% between 2019 and 2022."},
    {"concept": "brute_force", "content": "Brute force attack detected from 192.168.1.45: 847 failed SSH login attempts targeting admin accounts over 12 minutes."},
    {"concept": "c2_traffic", "content": "C2 beacon traffic detected from 172.16.0.100 (svc_backup) to 185.220.101.45 on port 443 using HTTPS tunneling."},
    {"concept": "supply_chain_attack", "content": "Supply chain attack detected: malicious npm package event-stream@5.0.0 with crypto-mining payload found in CI pipeline."},
    {"concept": "xz_backdoor", "content": "CVE-2024-3094 (xz-utils/sshd backdoor) detected on build servers; attacker used DNS tunneling via *.tunnel.attacker.net."},
    {"concept": "insider_threat", "content": "Insider threat indicator: bulk download of 15,234 sensitive documents by user jsmith detected; DLP policy triggered."},
    {"concept": "inc_2024_001", "content": "INC-2024-001: Ransomware attack on production database servers; 3 servers encrypted; status: contained; CVE-2024-21626 involved."},
    {"concept": "inc_2024_002", "content": "INC-2024-002: Data exfiltration via C2 server 185.220.101.45; 2.3GB exfiltrated; breach notification sent to 15,000 customers; status: remediated."},
    {"concept": "inc_2024_003", "content": "INC-2024-003: APT29 (state-sponsored) supply chain attack; TTPs matched APT29; involved event-stream npm package, crypto mining on CI server, DNS tunneling, and xz-utils backdoor (CVE-2024-3094)."},
    {"concept": "apt29", "content": "APT29 (Cozy Bear) is a Russian state-sponsored threat actor known for supply chain attacks and stealthy long-term persistence."},
    {"concept": "ransomware_response", "content": "Ransomware incident response playbook: isolate affected systems, preserve evidence, notify stakeholders, restore from clean backups, patch vulnerabilities."},
    {"concept": "ioc_correlation", "content": "IOC correlation links 192.168.1.45 (SSH brute force), 185.220.101.45 (C2 server), event-stream@5.0.0 (malicious npm), and tunnel.attacker.net (DNS C2)."},
]


def _build_eval_seed_facts() -> list[dict[str, str]]:
    """Build seed facts from amplihack_eval security/incident dialogue turns.

    Uses the same generate_dialogue(num_turns=300, seed=42) call that generates
    eval questions, ensuring seeded facts match what the questions ask about.

    Returns:
        List of fact dicts with 'concept' and 'content' keys, one per dialogue turn,
        falling back to _FACT_CORPUS_FALLBACK if amplihack_eval is unavailable.
    """
    try:
        from amplihack_eval.data import generate_dialogue
    except ImportError:
        logger.warning("amplihack_eval not available; using fallback seed corpus")
        return list(_FACT_CORPUS_FALLBACK)

    ground_truth = generate_dialogue(num_turns=300, seed=42)
    security_turns = [
        t for t in ground_truth.turns
        if t.block_name in ("security_logs", "incidents") and t.content
    ]
    if not security_turns:
        logger.warning("generate_dialogue returned no security turns; using fallback seed corpus")
        return list(_FACT_CORPUS_FALLBACK)

    facts: list[dict[str, str]] = []
    for idx, turn in enumerate(security_turns):
        # Derive a concept key from the block and turn index
        concept = f"{turn.block_name}_{idx:03d}"
        facts.append({
            "concept": concept,
            "content": turn.content,
            "confidence": "0.95",
        })

    logger.info(
        "Built %d seed facts from amplihack_eval generate_dialogue (security_logs + incidents)",
        len(facts),
    )
    return facts


# Lazy-loaded seed facts (populated on first use of --seed)
_FACT_CORPUS: list[dict[str, str]] | None = None


def _get_fact_corpus() -> list[dict[str, str]]:
    """Return cached seed facts, building them from eval on first call."""
    global _FACT_CORPUS
    if _FACT_CORPUS is None:
        _FACT_CORPUS = _build_eval_seed_facts()
    return _FACT_CORPUS

# ---------------------------------------------------------------------------
# Security analyst Q&A evaluation dataset
# Generated dynamically from amplihack_eval.data.generate_dialogue/generate_questions
# ---------------------------------------------------------------------------

def _load_security_questions() -> list[Any]:
    """Load security analyst scenario questions from amplihack_eval.

    Uses generate_dialogue (300 turns) to produce a security-rich dialogue
    covering security_logs (turns ~210-240) and incidents (turns ~240-264).
    Then uses generate_questions to extract questions and filters to
    security-relevant categories (seclog_*, incident_*).

    Returns:
        List of amplihack_eval Question objects with text and expected_answer.
    """
    try:
        from amplihack_eval.data import generate_dialogue, generate_questions
    except ImportError:
        logger.warning("amplihack_eval not available; using built-in security questions")
        return []

    ground_truth = generate_dialogue(num_turns=300, seed=42)
    all_questions = generate_questions(ground_truth, num_questions=100)

    # Filter to security analyst scenario questions
    security_prefixes = ("seclog_", "incident_")
    return [
        q for q in all_questions
        if any(q.question_id.startswith(pfx) for pfx in security_prefixes)
    ]


# Lazy-loaded security questions (populated on first use)
_SECURITY_QUESTIONS: list[Any] | None = None


def _get_security_questions() -> list[Any]:
    """Return cached security questions, loading them on first call."""
    global _SECURITY_QUESTIONS
    if _SECURITY_QUESTIONS is None:
        _SECURITY_QUESTIONS = _load_security_questions()
    return _SECURITY_QUESTIONS


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

        corpus = facts if facts is not None else _get_fact_corpus()
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
        max_retries: int = 2,
        retry_backoff: float = 2.0,
    ) -> list[dict[str, Any]]:
        """Query the live hive for facts matching `text`.

        Publishes a search_query event and waits up to self._timeout seconds
        for agent responses. Retries up to max_retries times with exponential
        backoff if 0 results are returned.

        Args:
            text: The search query text.
            table: Graph table to search (default: hive_facts).
            limit: Max results per agent.
            max_retries: Number of retry attempts when 0 results returned.
            retry_backoff: Base backoff in seconds between retries (doubled each attempt).

        Returns:
            Deduplicated list of matching fact dicts, sorted by confidence.
        """
        attempt = 0
        backoff = retry_backoff
        while True:
            results = self._query_once(text=text, table=table, limit=limit)
            if results or attempt >= max_retries:
                if attempt > 0 and not results:
                    logger.warning(
                        "Query returned 0 results after %d retries: %r", attempt, text
                    )
                return results
            attempt += 1
            logger.debug(
                "Query returned 0 results (attempt %d/%d), retrying in %.1fs: %r",
                attempt, max_retries, backoff, text,
            )
            time.sleep(backoff)
            backoff *= 2

    def _query_once(
        self,
        text: str,
        table: str = "hive_facts",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Execute a single query round-trip to the hive.

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
    """Run the security analyst Q&A eval against a local in-memory DistributedHiveGraph.

    Populates the hive with security analyst facts from _FACT_CORPUS, then
    evaluates security scenario questions from amplihack_eval using grade_answer.
    This demonstrates the hive query protocol without Azure connectivity.

    Args:
        output_path: Optional path to write JSON results.

    Returns:
        Results dict.
    """
    security_questions = _get_security_questions()
    print("=" * 70)
    print("HIVE SECURITY ANALYST Q&A EVAL (DEMO — local DistributedHiveGraph)")
    fact_corpus = _get_fact_corpus()
    print(f"Facts in corpus: {len(fact_corpus)}")
    print(f"Security questions: {len(security_questions)}")
    print("=" * 70)
    print()

    if not security_questions:
        print("WARNING: No security questions loaded from amplihack_eval.")
        print("Ensure amplihack-agent-eval is installed: pip install amplihack-agent-eval")
        return {}

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
        hive.register_agent(f"agent-{i}", domain="security")

    # Seed security facts into the hive
    for fact_dict in fact_corpus:
        fact = HiveFact(
            fact_id="",
            content=fact_dict["content"],
            concept=fact_dict["concept"],
            confidence=0.95,
            source_agent="eval-seed",
        )
        hive.promote_fact("agent-0", fact)

    t0 = time.time()
    results: list[dict[str, Any]] = []
    by_category: dict[str, list[float]] = {}

    print(f"{'Category':20s} {'Score':6s} {'Results':8s} | Question")
    print("-" * 70)

    for q in security_questions:
        facts = hive.query_facts(q.text, limit=10)
        result_dicts = [
            {"content": f.content, "concept": f.concept, "confidence": f.confidence}
            for f in facts
        ]
        actual = _format_hive_results(result_dicts)
        grade = _grade_hive_answer(q.text, q.expected_answer, actual)
        score = grade["score"]
        by_category.setdefault(q.category, []).append(score)

        print(
            f"  {q.category[:18]:18s} {score:.2f}  {len(facts):3d} results"
            f" | {q.text[:42]}"
        )

        results.append(
            {
                "question_id": q.question_id,
                "category": q.category,
                "question": q.text,
                "expected_answer": q.expected_answer,
                "actual_answer": actual,
                "score": score,
                "reasoning": grade["reasoning"],
                "result_count": len(facts),
                "top_results": result_dicts[:3],
            }
        )

    elapsed = time.time() - t0
    total = len(results)
    avg_score = sum(r["score"] for r in results) / total if total else 0.0

    category_scores = {
        c: {"avg_score": round(sum(v) / len(v), 3), "count": len(v)}
        for c, v in by_category.items()
    }

    print("-" * 70)
    print()
    print("=" * 70)
    print("RESULTS (DEMO MODE — Security Analyst Eval)")
    print("=" * 70)
    print(f"  Overall avg score: {avg_score:.3f} ({total} questions)")
    print()
    print("  By category:")
    for c, s in sorted(category_scores.items()):
        print(f"    {c:20s}: avg={s['avg_score']:.3f} ({s['count']} questions)")
    print(f"\n  Total time: {elapsed:.2f}s")
    print("=" * 70)

    output = {
        "mode": "demo_local_security",
        "summary": {
            "total_questions": total,
            "avg_score": round(avg_score, 3),
            "elapsed_s": round(elapsed, 2),
            "hive_type": "DistributedHiveGraph (local)",
            "agents": 5,
            "facts_seeded": len(fact_corpus),
        },
        "category_scores": category_scores,
        "questions": results,
    }

    if output_path:
        with open(output_path, "w") as fh:
            json.dump(output, fh, indent=2)
        print(f"\nResults written to: {output_path}")

    hive.close()
    return output


# ---------------------------------------------------------------------------
# Grading helpers
# ---------------------------------------------------------------------------


def _format_hive_results(results: list[dict[str, Any]]) -> str:
    """Format hive search results into a text answer for grading."""
    if not results:
        return ""
    parts = []
    for r in results[:10]:
        content = r.get("content", r.get("outcome", ""))
        concept = r.get("concept", r.get("context", ""))
        if content:
            parts.append(f"{content} [{concept}]" if concept else content)
    return " | ".join(parts)


def _keyword_fallback_grade(expected: str, actual: str) -> dict[str, Any]:
    """Keyword/entity overlap fallback grader when LLM grading is unavailable.

    Combines entity-level recall (CVE IDs, IP addresses, incident IDs, version
    strings) with keyword-level recall using fixed tokenization. Entity recall
    is given higher weight (0.6) since named entities are the most discriminative
    signals for security analyst questions.

    Args:
        expected: Expected answer string.
        actual: Actual answer from hive results.

    Returns:
        Dict with 'score' (0.0-1.0) and 'reasoning' string.
    """
    import re as _re

    _STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "what", "which",
        "who", "where", "when", "why", "how", "i", "you", "he", "she", "it",
        "we", "they", "me", "him", "her", "us", "them", "this", "that",
        "these", "those", "and", "but", "or", "for", "yet", "so", "if",
        "then", "at", "by", "from", "in", "of", "on", "to", "up", "with",
        "about", "after", "as", "before", "between", "during", "into",
        "like", "over", "through", "under", "until", "via", "not", "no",
        "yes", "any", "all", "some", "each", "every", "more", "most",
        "other", "than", "too", "very", "just", "also", "back", "once",
        "out", "there", "here", "detected", "log", "security", "severity",
        "user", "high", "medium", "critical", "report", "incident", "status",
        "update", "changed", "detail", "timeline", "affected", "systems",
        "iocs", "none", "identified", "active", "contained", "investigating",
        "remediated", "closed",
    }

    def _extract_entities(text: str) -> set:
        entities: set = set()
        entities.update(_re.findall(r"CVE-\d{4}-\d+", text, _re.IGNORECASE))
        entities.update(_re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", text))
        entities.update(_re.findall(r"INC-\d{4}-\d+", text, _re.IGNORECASE))
        entities.update(_re.findall(r"[a-zA-Z][\w.-]*@[\d.]+", text))
        return {e.lower() for e in entities}

    def _tokenize(text: str) -> set:
        raw = _re.findall(r"[A-Za-z0-9][A-Za-z0-9._@/-]*", text.lower())
        result = set()
        for t in raw:
            t = _re.sub(r"[._-]+$", "", t)
            if t and t not in _STOP_WORDS and len(t) >= 2:
                result.add(t)
        return result

    exp_entities = _extract_entities(expected)
    act_entities = _extract_entities(actual)
    entity_score = (
        len(exp_entities & act_entities) / len(exp_entities)
        if exp_entities else None
    )

    exp_tokens = _tokenize(expected)
    act_tokens = _tokenize(actual)
    kw_score = (
        len(exp_tokens & act_tokens) / len(exp_tokens)
        if exp_tokens else 1.0
    )

    if entity_score is not None:
        score = 0.6 * entity_score + 0.4 * kw_score
    else:
        score = kw_score

    reasoning = (
        f"Keyword/entity fallback: entity_score={entity_score:.2f}, "
        f"kw_score={kw_score:.2f}, combined={score:.2f}"
        if entity_score is not None
        else f"Keyword fallback: kw_score={kw_score:.2f}"
    )
    return {"score": round(score, 3), "reasoning": reasoning}


def _grade_hive_answer(question: str, expected: str, actual: str) -> dict[str, Any]:
    """Grade a hive answer using amplihack_eval.core.grader.grade_answer (LLM grading).

    Uses semantic LLM grading via grade_answer (requires ANTHROPIC_API_KEY).
    Falls back to keyword/entity overlap scoring when the API key is unavailable.

    Args:
        question: The question asked.
        expected: Expected answer string.
        actual: Actual answer from hive results.

    Returns:
        Dict with 'score' (0.0-1.0) and 'reasoning' string.
    """
    if not actual:
        return {"score": 0.0, "reasoning": "No results returned by hive"}

    try:
        from amplihack_eval.core.grader import grade_answer
        result = grade_answer(
            question=question,
            expected=expected,
            actual=actual,
            level="L1",
        )
        return {"score": result.score, "reasoning": result.reasoning}
    except Exception as exc:
        logger.warning("grade_answer failed: %s", exc)
        logger.info("Falling back to keyword/entity overlap grader")
        return _keyword_fallback_grade(expected, actual)


# ---------------------------------------------------------------------------
# Live eval runner (Service Bus mode)
# ---------------------------------------------------------------------------


def run_eval(
    client: HiveQueryClient,
    table: str = "hive_facts",
    output_path: str | None = None,
) -> dict[str, Any]:
    """Run the security analyst Q&A eval against the live hive.

    Loads security scenario questions from amplihack_eval (generate_dialogue +
    generate_questions), queries the live hive for each, and grades responses
    using amplihack_eval.grade_answer for semantic scoring.

    Args:
        client: Connected HiveQueryClient instance.
        table: Table name to query (must match what was seeded).
        output_path: Optional path to write JSON results.

    Returns:
        Results dict with per-question scores and aggregate summary.
    """
    security_questions = _get_security_questions()

    print("=" * 70)
    print("LIVE AZURE HIVE — SECURITY ANALYST Q&A EVAL")
    print(f"Hive: hive-sb-dj2qo2w7vu5zi / topic: {client._topic_name}")
    print(f"Table: {table}")
    print(f"Security questions: {len(security_questions)}")
    print(f"Timeout per query: {client._timeout}s")
    print("=" * 70)
    print()

    if not security_questions:
        print("WARNING: No security questions loaded from amplihack_eval.")
        print("Ensure amplihack-agent-eval is installed.")
        return {}

    t0 = time.time()
    results: list[dict[str, Any]] = []
    by_category: dict[str, list[float]] = {}

    print(f"{'Category':20s} {'Score':6s} {'Results':8s} | Question")
    print("-" * 70)

    for q in security_questions:
        t_q = time.time()
        hive_results = client.query(q.text, table=table, limit=10)
        actual = _format_hive_results(hive_results)
        grade = _grade_hive_answer(q.text, q.expected_answer, actual)
        score = grade["score"]
        elapsed_q = time.time() - t_q

        by_category.setdefault(q.category, []).append(score)

        print(
            f"  {q.category[:18]:18s} {score:.2f}  {len(hive_results):3d} results"
            f" | {q.text[:42]}"
        )
        logger.debug(
            "Q: %r → %d results in %.2fs, score=%.2f",
            q.text,
            len(hive_results),
            elapsed_q,
            score,
        )

        results.append(
            {
                "question_id": q.question_id,
                "category": q.category,
                "question": q.text,
                "expected_answer": q.expected_answer,
                "actual_answer": actual,
                "score": score,
                "reasoning": grade["reasoning"],
                "result_count": len(hive_results),
                "top_results": hive_results[:3],
                "elapsed_s": round(elapsed_q, 2),
            }
        )

    elapsed = time.time() - t0
    total = len(results)
    avg_score = sum(r["score"] for r in results) / total if total else 0.0

    category_scores = {
        c: {"avg_score": round(sum(v) / len(v), 3), "count": len(v)}
        for c, v in by_category.items()
    }

    print("-" * 70)
    print()
    print("=" * 70)
    print("RESULTS (LIVE HIVE — Security Analyst Eval)")
    print("=" * 70)
    print(f"  Overall avg score: {avg_score:.3f} ({total} questions)")
    print()
    print("  By category:")
    for c, s in sorted(category_scores.items()):
        print(f"    {c:20s}: avg={s['avg_score']:.3f} ({s['count']} questions)")
    print(f"\n  Total time: {elapsed:.2f}s")
    print("=" * 70)

    if avg_score == 0.0:
        print()
        print("NOTE: Score 0.0 — likely the hive has not been seeded yet.")
        print("Run with --seed first:")
        print("  python experiments/hive_mind/query_hive.py --seed --run-eval")

    output = {
        "mode": "live_security",
        "summary": {
            "total_questions": total,
            "avg_score": round(avg_score, 3),
            "elapsed_s": round(elapsed, 2),
            "hive_namespace": "hive-sb-dj2qo2w7vu5zi",
            "topic": client._topic_name,
            "timeout_s": client._timeout,
            "table": table,
        },
        "category_scores": category_scores,
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

  # Seed live hive with security facts then run security analyst eval:
  python query_hive.py --seed --run-eval --output results.json

  # Single security query against live hive (after seeding):
  python query_hive.py --query "What CVE was used in the supply chain attack?"

  # Diagnose live hive (may return low scores if not seeded):
  python query_hive.py --run-eval

  # Run eval 3 times and report median + stddev:
  python query_hive.py --run-eval --repeats 3
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
    p.add_argument(
        "--repeats",
        type=int,
        default=1,
        metavar="N",
        help="Run the eval N times and report median and stddev of scores (default: 1).",
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
        n = args.repeats
        if n > 1:
            scores = []
            all_outputs = []
            for i in range(n):
                print(f"\n--- Repeat {i + 1}/{n} ---")
                out = run_demo_eval(output_path=None)
                avg = out.get("summary", {}).get("avg_score", 0.0)
                scores.append(avg)
                all_outputs.append(out)
            med = statistics.median(scores)
            std = statistics.stdev(scores) if len(scores) > 1 else 0.0
            print(f"\n{'=' * 70}")
            print(f"REPEATS SUMMARY ({n} runs)")
            print(f"{'=' * 70}")
            for i, s in enumerate(scores, 1):
                print(f"  Run {i}: avg_score={s:.3f}")
            print(f"  Median: {med:.3f}  StdDev: {std:.3f}")
            print(f"{'=' * 70}")
            if args.output:
                summary_output = {
                    "mode": "demo_repeats",
                    "repeats": n,
                    "scores": scores,
                    "median": round(med, 3),
                    "stddev": round(std, 3),
                    "runs": all_outputs,
                }
                with open(args.output, "w") as fh:
                    json.dump(summary_output, fh, indent=2)
                print(f"\nResults written to: {args.output}")
        else:
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
            seed_corpus = _get_fact_corpus()
            print(f"Seeding {len(seed_corpus)} security analyst facts into live hive (table={args.table})...")
            n = client.seed_facts(facts=seed_corpus, table=args.table)
            print(f"Seeded {n} security facts. Waiting 5s for propagation...")
            time.sleep(5)

        if args.run_eval:
            n = args.repeats
            if n > 1:
                scores = []
                all_outputs = []
                for i in range(n):
                    print(f"\n--- Repeat {i + 1}/{n} ---")
                    out = run_eval(client, table=args.table, output_path=None)
                    avg = out.get("summary", {}).get("avg_score", 0.0)
                    scores.append(avg)
                    all_outputs.append(out)
                med = statistics.median(scores)
                std = statistics.stdev(scores) if len(scores) > 1 else 0.0
                print(f"\n{'=' * 70}")
                print(f"REPEATS SUMMARY ({n} runs)")
                print(f"{'=' * 70}")
                for i, s in enumerate(scores, 1):
                    print(f"  Run {i}: avg_score={s:.3f}")
                print(f"  Median: {med:.3f}  StdDev: {std:.3f}")
                print(f"{'=' * 70}")
                if args.output:
                    summary_output = {
                        "mode": "live_repeats",
                        "repeats": n,
                        "scores": scores,
                        "median": round(med, 3),
                        "stddev": round(std, 3),
                        "runs": all_outputs,
                    }
                    with open(args.output, "w") as fh:
                        json.dump(summary_output, fh, indent=2)
                    print(f"\nResults written to: {args.output}")
            else:
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
