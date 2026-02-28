#!/usr/bin/env python3
"""Experiment 1 evaluation: Shared Blackboard via Kuzu Graph.

Hypothesis: Adding a shared HiveMemory table to Kuzu improves
cross-agent knowledge retrieval by >30%.

Setup:
- 3 agents, each learning domain-specific content:
  - Agent A: Infrastructure (servers, ports, replicas, load balancers)
  - Agent B: Security (encryption, TLS, authentication, access control)
  - Agent C: Performance (latency, throughput, caching, optimization)
- After learning, each agent is asked questions that require knowledge
  from OTHER agents' domains.
- Baseline: each agent queries only its own local memory
- Hive: each agent promotes facts to hive, then queries hive for answers

Metrics:
- Cross-agent recall accuracy (% of cross-domain questions answered correctly)
- Query latency (time per query)
- Deduplication effectiveness (unique facts vs total stored)
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

# Add source to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from amplihack.agents.goal_seeking.hive_mind.blackboard import (
    HiveMemoryStore,
    MultiAgentHive,
)

# ---------------------------------------------------------------------------
# Domain knowledge for each agent
# ---------------------------------------------------------------------------

INFRASTRUCTURE_FACTS = [
    ("Infrastructure", "The primary PostgreSQL database runs on port 5432 with 3 read replicas"),
    ("Infrastructure", "The load balancer distributes traffic across 4 application servers"),
    ("Infrastructure", "Redis cache cluster runs on port 6379 with 16GB memory per node"),
    ("Infrastructure", "The message queue uses RabbitMQ on port 5672 for async processing"),
    ("Infrastructure", "Kubernetes cluster has 12 worker nodes across 3 availability zones"),
    ("Infrastructure", "The CDN edge servers are deployed in 8 global regions"),
    ("Infrastructure", "Database backups run every 6 hours with 30-day retention"),
    ("Infrastructure", "The monitoring stack uses Prometheus on port 9090 and Grafana on 3000"),
    ("Infrastructure", "Service mesh uses Istio for inter-service communication"),
    ("Infrastructure", "The CI/CD pipeline uses GitHub Actions with self-hosted runners"),
]

SECURITY_FACTS = [
    ("Security", "All external connections require TLS 1.3 with AES-256-GCM encryption"),
    ("Security", "Authentication uses OAuth 2.0 with PKCE flow for all client applications"),
    ("Security", "API rate limiting is set to 1000 requests per minute per API key"),
    (
        "Security",
        "Database connections use mutual TLS with client certificate rotation every 90 days",
    ),
    ("Security", "All secrets are stored in HashiCorp Vault with auto-rotation enabled"),
    ("Security", "Web application firewall blocks SQL injection and XSS attack patterns"),
    ("Security", "RBAC policy requires minimum 2 approvals for production deployments"),
    ("Security", "Security audit logs are retained for 1 year in immutable storage"),
    (
        "Security",
        "Container images are scanned for CVEs before deployment with zero-critical policy",
    ),
    ("Security", "Network segmentation isolates production from staging via VPC peering rules"),
]

PERFORMANCE_FACTS = [
    ("Performance", "P99 API response latency is 47ms measured at the load balancer"),
    ("Performance", "Redis cache hit rate averages 94.7% across all cached endpoints"),
    ("Performance", "Database query P95 is 12ms with connection pooling of 50 connections"),
    ("Performance", "The CDN serves 89% of static assets from edge cache with 200ms TTL"),
    (
        "Performance",
        "Horizontal auto-scaling triggers at 70% CPU utilization with 2-minute cooldown",
    ),
    ("Performance", "The message queue processes 50,000 messages per second at peak"),
    ("Performance", "Memory usage per application pod averages 512MB with 1GB limit"),
    ("Performance", "Garbage collection pauses average 3ms with G1GC collector"),
    ("Performance", "Network throughput between services is 8 Gbps within the same AZ"),
    ("Performance", "Database write throughput is 5,000 transactions per second"),
]

# Cross-domain questions that require knowledge from other agents
CROSS_DOMAIN_QUESTIONS = [
    {
        "question": "What port does the PostgreSQL database run on?",
        "answer_keywords": ["5432"],
        "source_domain": "Infrastructure",
        "asking_agent": "security_agent",
    },
    {
        "question": "What encryption standard is used for external connections?",
        "answer_keywords": ["TLS 1.3", "AES-256"],
        "source_domain": "Security",
        "asking_agent": "infra_agent",
    },
    {
        "question": "What is the P99 API response latency?",
        "answer_keywords": ["47ms", "47"],
        "source_domain": "Performance",
        "asking_agent": "infra_agent",
    },
    {
        "question": "How many read replicas does the primary database have?",
        "answer_keywords": ["3"],
        "source_domain": "Infrastructure",
        "asking_agent": "perf_agent",
    },
    {
        "question": "What is the Redis cache hit rate?",
        "answer_keywords": ["94.7%", "94.7"],
        "source_domain": "Performance",
        "asking_agent": "security_agent",
    },
    {
        "question": "How often do client certificates rotate?",
        "answer_keywords": ["90 days", "90"],
        "source_domain": "Security",
        "asking_agent": "perf_agent",
    },
    {
        "question": "What message queue system is used for async processing?",
        "answer_keywords": ["RabbitMQ"],
        "source_domain": "Infrastructure",
        "asking_agent": "security_agent",
    },
    {
        "question": "What is the API rate limit per API key?",
        "answer_keywords": ["1000"],
        "source_domain": "Security",
        "asking_agent": "infra_agent",
    },
    {
        "question": "What CPU threshold triggers auto-scaling?",
        "answer_keywords": ["70%", "70"],
        "source_domain": "Performance",
        "asking_agent": "security_agent",
    },
    {
        "question": "How many Kubernetes worker nodes are there?",
        "answer_keywords": ["12"],
        "source_domain": "Infrastructure",
        "asking_agent": "perf_agent",
    },
    {
        "question": "Where are secrets stored?",
        "answer_keywords": ["HashiCorp Vault", "Vault"],
        "source_domain": "Security",
        "asking_agent": "infra_agent",
    },
    {
        "question": "What is the database write throughput?",
        "answer_keywords": ["5,000", "5000"],
        "source_domain": "Performance",
        "asking_agent": "infra_agent",
    },
]


def _check_answer(retrieved_facts: list[dict], answer_keywords: list[str]) -> bool:
    """Check if any retrieved fact contains at least one expected keyword."""
    for fact in retrieved_facts:
        text = f"{fact.get('outcome', '')} {fact.get('context', '')}".lower()
        for kw in answer_keywords:
            if kw.lower() in text:
                return True
    return False


def run_baseline_eval(tmp_dir: Path) -> dict:
    """Run baseline evaluation: each agent only has its own facts.

    In the baseline, agent A only has infrastructure facts, agent B only
    security facts, and agent C only performance facts. Cross-domain
    questions cannot be answered.
    """
    print("\n=== BASELINE: Isolated Agent Memory ===\n")

    # Create isolated stores per agent
    stores = {}
    agent_facts = {
        "infra_agent": INFRASTRUCTURE_FACTS,
        "security_agent": SECURITY_FACTS,
        "perf_agent": PERFORMANCE_FACTS,
    }

    for agent_id, facts in agent_facts.items():
        store = HiveMemoryStore(tmp_dir / f"baseline_{agent_id}")
        for concept, content in facts:
            store.store_shared_fact(content, agent_id, 0.9, concept=concept)
        stores[agent_id] = store

    # Test cross-domain questions
    correct = 0
    total = len(CROSS_DOMAIN_QUESTIONS)
    latencies: list[float] = []

    for q in CROSS_DOMAIN_QUESTIONS:
        asking = q["asking_agent"]
        # Baseline: agent can only query its OWN store
        start = time.perf_counter()
        results = stores[asking].query_shared_facts(q["question"], limit=10)
        latency = time.perf_counter() - start
        latencies.append(latency)

        fact_dicts = [{"outcome": f.content, "context": f.concept} for f in results]
        hit = _check_answer(fact_dicts, q["answer_keywords"])
        status = "HIT" if hit else "MISS"
        if hit:
            correct += 1

        print(f"  [{status}] {asking} asks: {q['question'][:60]}...")
        print(f"         Source domain: {q['source_domain']}, Retrieved: {len(results)} facts")

    accuracy = (correct / total) * 100 if total else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    print("\n  Baseline Results:")
    print(f"    Cross-agent recall: {correct}/{total} ({accuracy:.1f}%)")
    print(f"    Avg query latency:  {avg_latency * 1000:.2f}ms")

    return {
        "correct": correct,
        "total": total,
        "accuracy": accuracy,
        "avg_latency_ms": avg_latency * 1000,
    }


def run_hive_eval(tmp_dir: Path) -> dict:
    """Run hive evaluation: all agents share facts via the shared blackboard.

    All agents promote their facts to a shared hive. Cross-domain
    questions query the shared hive, which contains facts from all agents.
    """
    print("\n=== HIVE: Shared Blackboard Memory ===\n")

    hive = MultiAgentHive(tmp_dir / "shared_hive_db")

    agent_facts = {
        "infra_agent": INFRASTRUCTURE_FACTS,
        "security_agent": SECURITY_FACTS,
        "perf_agent": PERFORMANCE_FACTS,
    }

    # Register agents and broadcast their facts to the hive
    total_stored = 0
    for agent_id, facts in agent_facts.items():
        hive.register_agent(agent_id)
        for concept, content in facts:
            hive.broadcast_fact(content, agent_id, 0.9, concept=concept)
            total_stored += 1

    stats = hive.get_statistics()
    unique_facts = stats["total_facts"]
    print(f"  Facts stored: {total_stored} total, {unique_facts} unique")
    print(f"  Agents: {stats['registered_agents']}")
    print(f"  Per-agent: {stats['facts_per_agent']}")

    # Test cross-domain questions
    correct = 0
    total = len(CROSS_DOMAIN_QUESTIONS)
    latencies: list[float] = []

    for q in CROSS_DOMAIN_QUESTIONS:
        asking = q["asking_agent"]
        start = time.perf_counter()
        results = hive.query_hive(q["question"], asking, limit=10)
        latency = time.perf_counter() - start
        latencies.append(latency)

        hit = _check_answer(results, q["answer_keywords"])
        status = "HIT" if hit else "MISS"
        if hit:
            correct += 1

        source_agents = set(r["metadata"]["source_agent_id"] for r in results)
        print(f"  [{status}] {asking} asks: {q['question'][:60]}...")
        print(
            f"         Source domain: {q['source_domain']}, "
            f"Retrieved: {len(results)} facts from {source_agents}"
        )

    accuracy = (correct / total) * 100 if total else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    print("\n  Hive Results:")
    print(f"    Cross-agent recall: {correct}/{total} ({accuracy:.1f}%)")
    print(f"    Avg query latency:  {avg_latency * 1000:.2f}ms")
    print(f"    Dedup ratio:        {unique_facts}/{total_stored} unique")

    return {
        "correct": correct,
        "total": total,
        "accuracy": accuracy,
        "avg_latency_ms": avg_latency * 1000,
        "unique_facts": unique_facts,
        "total_stored": total_stored,
    }


def main():
    """Run the full blackboard evaluation."""
    print("=" * 70)
    print("Experiment 1: Shared Blackboard via Kuzu Graph")
    print("Hypothesis: Shared HiveMemory improves cross-agent retrieval >30%")
    print("=" * 70)

    with tempfile.TemporaryDirectory(prefix="hive_eval_") as tmp:
        tmp_dir = Path(tmp)

        baseline = run_baseline_eval(tmp_dir)
        hive = run_hive_eval(tmp_dir)

        # Compare results
        print("\n" + "=" * 70)
        print("COMPARISON")
        print("=" * 70)

        baseline_acc = baseline["accuracy"]
        hive_acc = hive["accuracy"]
        improvement = hive_acc - baseline_acc

        print("\n  Cross-Agent Recall Accuracy:")
        print(f"    Baseline (isolated):  {baseline_acc:.1f}%")
        print(f"    Hive (shared):        {hive_acc:.1f}%")
        print(f"    Improvement:          +{improvement:.1f}pp")

        print("\n  Query Latency:")
        print(f"    Baseline:  {baseline['avg_latency_ms']:.2f}ms")
        print(f"    Hive:      {hive['avg_latency_ms']:.2f}ms")

        if hive.get("unique_facts") and hive.get("total_stored"):
            dedup_pct = (1 - hive["unique_facts"] / hive["total_stored"]) * 100
            print("\n  Deduplication:")
            print(
                f"    Unique: {hive['unique_facts']}/{hive['total_stored']} "
                f"({dedup_pct:.1f}% dedup)"
            )

        # Hypothesis check
        print("\n  HYPOTHESIS: Shared HiveMemory improves retrieval by >30%")
        if improvement >= 30:
            print(f"  RESULT: CONFIRMED (+{improvement:.1f}pp >= 30pp threshold)")
        else:
            print(f"  RESULT: NOT MET (+{improvement:.1f}pp < 30pp threshold)")
            if hive_acc > baseline_acc:
                print(f"          However, there IS improvement (+{improvement:.1f}pp)")

        print("\n" + "=" * 70)
        return {
            "baseline": baseline,
            "hive": hive,
            "improvement_pp": improvement,
            "hypothesis_confirmed": improvement >= 30,
        }


if __name__ == "__main__":
    results = main()
    sys.exit(0)
