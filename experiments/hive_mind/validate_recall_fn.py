#!/usr/bin/env python3
"""Validate the recall_fn fix: 5 agents, 100 turns, query_hive with 10 questions.

Tests the dual-storage fix end-to-end using a local event bus (no Azure needed).
Directly constructs NetworkGraphStore + CognitiveAdapter instances and wires
recall_fn the same way facade.py does, then validates the search_query path
routes through CognitiveAdapter's Kuzu (which holds LEARN_CONTENT facts).

Steps:
  1. Build 5 (NetworkGraphStore + CognitiveAdapter) pairs with local bus
  2. Wire recall_fn = adapter.search on each NetworkGraphStore
  3. Feed 100 turns via CognitiveAdapter.store_fact() (simulates LEARN_CONTENT)
  4. Run query_hive with 10 questions via recall(), assert all results > 0

Usage:
    uv run python experiments/hive_mind/validate_recall_fn.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from typing import Any

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter
from amplihack.memory.memory_store import InMemoryGraphStore
from amplihack.memory.network_store import NetworkGraphStore

# ---------------------------------------------------------------------------
# 100-turn content corpus (same pool as feed_content.py)
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
    "Water has a specific heat capacity of 4,186 J/(kg*K), making it an excellent thermal buffer.",
    "The boiling point of water at sea level is 100 degrees C.",
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
    "Moore's Law historically described a doubling of transistor density every 18 months.",
    "TCP/IP is the fundamental protocol suite for internet communication.",
    "TLS encrypts network traffic to prevent eavesdropping and tampering.",
    "The CAP theorem states distributed systems can guarantee only two of: Consistency, Availability, Partition tolerance.",
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
    "The six-type cognitive memory model maps to: sensory, working, episodic, semantic, procedural, prospective.",
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


def _make_concept_from_content(content: str) -> str:
    """Extract a simple concept keyword from content."""
    words = content.split()
    return words[1] if len(words) > 1 else "general"


class HiveAgent:
    """Simulates one deployed agent: NetworkGraphStore + CognitiveAdapter with recall_fn wired."""

    def __init__(self, agent_id: str, db_path: str) -> None:
        self.agent_id = agent_id
        # NetworkGraphStore with local bus (mirrors production with azure_service_bus)
        self.graph_store = NetworkGraphStore(
            agent_id=agent_id,
            local_store=InMemoryGraphStore(),
            transport="local",
        )
        # CognitiveAdapter: the "real" Kuzu store holding LEARN_CONTENT facts
        self.adapter = CognitiveAdapter(
            agent_name=agent_id,
            db_path=db_path,
        )
        # Wire recall_fn — this is the fix: search_query routes through Kuzu
        self.graph_store.recall_fn = self.adapter.search

    def remember(self, content: str) -> None:
        """Store content in CognitiveAdapter (simulates LEARN_CONTENT handling)."""
        concept = _make_concept_from_content(content)
        self.adapter.store_fact(concept, content)

    def recall(self, question: str, limit: int = 10) -> list[dict[str, Any]]:
        """Recall via CognitiveAdapter (simulates memory.recall())."""
        return self.adapter.search(question, limit=limit)

    def simulate_search_query(self, question: str) -> list[dict[str, Any]]:
        """Simulate what _handle_query_event does when search_query arrives.

        This is the path that was broken: without recall_fn it searched the
        empty local InMemoryGraphStore; with recall_fn it queries Kuzu.
        """
        results: list[dict[str, Any]] = []
        # Primary path: delegate to recall_fn (the fix)
        if self.graph_store.recall_fn is not None:
            try:
                cognitive_hits = self.graph_store.recall_fn(question, 10)
                for r in cognitive_hits:
                    content = r.get("outcome") or r.get("content") or r.get("fact") or ""
                    if content:
                        results.append(
                            {
                                "content": content,
                                "concept": r.get("context") or r.get("concept") or "",
                                "confidence": r.get("confidence", 0.8),
                            }
                        )
            except Exception as e:
                print(f"  WARN: recall_fn failed: {e}")
        return results

    def close(self) -> None:
        self.graph_store.close()
        self.adapter.close()


# ---------------------------------------------------------------------------
# 10 evaluation questions
# ---------------------------------------------------------------------------

EVAL_QUESTIONS = [
    "What is the powerhouse of the cell?",
    "How does photosynthesis work?",
    "What is the speed of light?",
    "How do neural networks learn?",
    "What is the transformer architecture?",
    "What does the CAP theorem state?",
    "What is CRISPR-Cas9?",
    "How does gossip protocol work?",
    "What is the Kuzu database?",
    "What is cognitive memory?",
]


def main() -> int:
    print("=" * 60)
    print("validate_recall_fn.py — dual-storage path fix validation")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: Build 5 agents
        print("\n[1] Building 5 agents (NetworkGraphStore + CognitiveAdapter)...")
        agents = []
        for i in range(5):
            db_path = os.path.join(tmpdir, f"agent-{i}")
            os.makedirs(db_path, exist_ok=True)
            agents.append(HiveAgent(f"agent-{i}", db_path))
        print(f"  [OK] Built {len(agents)} agents")

        # Step 2: Verify recall_fn is wired
        print("\n[2] Verifying recall_fn wired on NetworkGraphStore...")
        for agent in agents:
            assert agent.graph_store.recall_fn is not None, (
                f"{agent.agent_id}: recall_fn is None — wiring failed!"
            )
        print(f"  [OK] recall_fn wired on all {len(agents)} agents")

        # Step 3: Feed 100 turns
        print("\n[3] Feeding 100 turns of LEARN_CONTENT...")
        t0 = time.time()
        for turn in range(100):
            agent = agents[turn % len(agents)]
            content = _CONTENT_POOL[turn % len(_CONTENT_POOL)]
            agent.remember(f"[turn={turn}] {content}")
        print(f"  [OK] Fed 100 turns in {time.time() - t0:.2f}s")

        # Step 4a: Query via recall() (normal path)
        print("\n[4a] query_hive via recall() — normal QUERY event path...")
        recall_results: dict[str, int] = {}
        for q in EVAL_QUESTIONS:
            total = sum(len(a.recall(q)) for a in agents)
            recall_results[q] = total

        # Step 4b: Query via simulate_search_query() — the fixed search_query path
        print("\n[4b] query_hive via search_query handler (recall_fn path)...")
        sq_results: dict[str, int] = {}
        for q in EVAL_QUESTIONS:
            total = sum(len(a.simulate_search_query(q)) for a in agents)
            sq_results[q] = total

        # Cleanup
        for agent in agents:
            try:
                agent.close()
            except Exception:
                pass

    # Report results
    print()
    print("=" * 60)
    print("Results:")
    print(f"  {'Q#':>3}  {'recall()':>8}  {'search_query':>12}  Question")
    print("  " + "-" * 56)

    failed_recall = []
    failed_sq = []
    for i, q in enumerate(EVAL_QUESTIONS):
        rc = recall_results[q]
        sq = sq_results[q]
        r_ok = "OK" if rc > 0 else "FAIL"
        s_ok = "OK" if sq > 0 else "FAIL"
        print(f"  Q{i + 1:>2}  [{r_ok}]{rc:>4}    [{s_ok}]{sq:>4}        {q[:40]}")
        if rc == 0:
            failed_recall.append(q)
        if sq == 0:
            failed_sq.append(q)

    print()
    if failed_recall or failed_sq:
        if failed_recall:
            print(f"FAILED (recall): {len(failed_recall)} questions returned 0 results")
        if failed_sq:
            print(f"FAILED (search_query): {len(failed_sq)} questions returned 0 results")
        print("=" * 60)
        return 1
    total_recall = sum(recall_results.values())
    total_sq = sum(sq_results.values())
    print(f"PASSED: All {len(EVAL_QUESTIONS)} questions returned results > 0")
    print(f"  recall()      total: {total_recall} results")
    print(f"  search_query  total: {total_sq} results (via recall_fn → Kuzu)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
