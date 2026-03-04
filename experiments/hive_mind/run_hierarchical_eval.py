#!/usr/bin/env python3
"""Evaluation script for Hierarchical Knowledge Graph with Promotion/Pull.

Creates 3 agents (infrastructure, security, performance), each learning
domain-specific facts. Agents promote their top-10 highest-confidence
facts to the hive, then pull relevant cross-domain knowledge.

Evaluates:
1. Promotion accuracy: Do high-quality facts get promoted?
2. Pull relevance: Are pulled facts actually useful to the pulling agent?
3. Combined eval: Can agents answer cross-domain questions better with hive?
4. Baseline comparison: Isolated agents vs hive-connected agents

Usage:
    python -m experiments.hive_mind.run_hierarchical_eval
    # or
    python experiments/hive_mind/run_hierarchical_eval.py
"""

from __future__ import annotations

import os
import sys

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from amplihack.agents.goal_seeking.hive_mind.hierarchical import (
    HierarchicalKnowledgeGraph,
    PromotionPolicy,
)

# ---------------------------------------------------------------------------
# Domain knowledge: 30 facts per agent
# ---------------------------------------------------------------------------

INFRASTRUCTURE_FACTS = [
    (
        "Servers typically listen on port 443 for HTTPS traffic",
        0.95,
        ["infrastructure", "networking"],
    ),
    (
        "Load balancers distribute incoming requests across multiple servers",
        0.92,
        ["infrastructure", "scaling"],
    ),
    (
        "Docker containers package applications with their dependencies",
        0.94,
        ["infrastructure", "containers"],
    ),
    (
        "Kubernetes orchestrates container deployment and scaling",
        0.93,
        ["infrastructure", "containers", "k8s"],
    ),
    (
        "DNS translates human-readable domain names to IP addresses",
        0.96,
        ["infrastructure", "networking", "dns"],
    ),
    (
        "CDNs cache content at edge locations closer to users",
        0.91,
        ["infrastructure", "performance", "cdn"],
    ),
    (
        "TCP provides reliable ordered delivery of data packets",
        0.94,
        ["infrastructure", "networking", "tcp"],
    ),
    (
        "UDP is faster than TCP but does not guarantee delivery",
        0.90,
        ["infrastructure", "networking", "udp"],
    ),
    (
        "Reverse proxies sit in front of web servers and forward requests",
        0.88,
        ["infrastructure", "networking"],
    ),
    (
        "Auto-scaling adjusts server count based on traffic demand",
        0.89,
        ["infrastructure", "scaling"],
    ),
    (
        "Virtual machines provide hardware-level isolation",
        0.87,
        ["infrastructure", "virtualization"],
    ),
    ("Subnets partition a network into smaller segments", 0.86, ["infrastructure", "networking"]),
    ("NAT translates private IP addresses to public ones", 0.85, ["infrastructure", "networking"]),
    (
        "BGP is the routing protocol that makes the internet work",
        0.84,
        ["infrastructure", "networking"],
    ),
    (
        "Object storage like S3 stores unstructured data at scale",
        0.90,
        ["infrastructure", "storage"],
    ),
    (
        "Block storage provides low-latency persistent volumes for VMs",
        0.83,
        ["infrastructure", "storage"],
    ),
    (
        "Service meshes manage communication between microservices",
        0.82,
        ["infrastructure", "microservices"],
    ),
    (
        "CIDR notation specifies IP address ranges efficiently",
        0.81,
        ["infrastructure", "networking"],
    ),
    (
        "Health checks verify that servers are responding correctly",
        0.88,
        ["infrastructure", "monitoring"],
    ),
    (
        "Ingress controllers manage external access to Kubernetes services",
        0.80,
        ["infrastructure", "k8s"],
    ),
    ("etcd stores Kubernetes cluster state as key-value pairs", 0.79, ["infrastructure", "k8s"]),
    (
        "Container registries store and distribute Docker images",
        0.83,
        ["infrastructure", "containers"],
    ),
    (
        "Infrastructure as Code defines servers using configuration files",
        0.91,
        ["infrastructure", "automation"],
    ),
    (
        "Blue-green deployments reduce downtime by running two environments",
        0.85,
        ["infrastructure", "deployment"],
    ),
    (
        "Canary deployments gradually roll out changes to a subset of users",
        0.86,
        ["infrastructure", "deployment"],
    ),
    (
        "gRPC uses HTTP/2 and protocol buffers for fast RPC communication",
        0.82,
        ["infrastructure", "networking"],
    ),
    (
        "Message queues decouple producers and consumers of data",
        0.87,
        ["infrastructure", "messaging"],
    ),
    (
        "Prometheus collects and stores time-series metrics from services",
        0.84,
        ["infrastructure", "monitoring"],
    ),
    (
        "Grafana visualizes metrics and creates monitoring dashboards",
        0.83,
        ["infrastructure", "monitoring"],
    ),
    (
        "Terraform manages cloud infrastructure through declarative config",
        0.90,
        ["infrastructure", "automation"],
    ),
]

SECURITY_FACTS = [
    (
        "TLS encrypts data in transit between client and server",
        0.96,
        ["security", "encryption", "tls"],
    ),
    (
        "SQL injection inserts malicious SQL through user input",
        0.95,
        ["security", "vulnerability", "sql"],
    ),
    ("CORS controls which origins can access web resources", 0.90, ["security", "web"]),
    (
        "OAuth2 delegates authorization without sharing credentials",
        0.93,
        ["security", "authentication"],
    ),
    (
        "JWT tokens carry signed claims for stateless authentication",
        0.92,
        ["security", "authentication", "jwt"],
    ),
    (
        "XSS attacks inject malicious scripts into web pages",
        0.94,
        ["security", "vulnerability", "xss"],
    ),
    ("CSRF tricks users into performing unwanted actions", 0.91, ["security", "vulnerability"]),
    ("Rate limiting prevents abuse by capping request frequency", 0.89, ["security", "defense"]),
    ("Content Security Policy restricts resource loading in browsers", 0.87, ["security", "web"]),
    (
        "Principle of least privilege limits access to minimum needed",
        0.93,
        ["security", "access-control"],
    ),
    ("Secrets management stores API keys and passwords securely", 0.90, ["security", "secrets"]),
    (
        "Hashing passwords with bcrypt prevents plaintext exposure",
        0.94,
        ["security", "authentication"],
    ),
    (
        "Two-factor authentication adds a second verification step",
        0.91,
        ["security", "authentication"],
    ),
    ("WAF filters and monitors HTTP traffic to web applications", 0.86, ["security", "defense"]),
    (
        "Penetration testing simulates attacks to find vulnerabilities",
        0.88,
        ["security", "testing"],
    ),
    ("SSRF tricks servers into accessing internal resources", 0.85, ["security", "vulnerability"]),
    ("Certificate pinning prevents man-in-the-middle attacks", 0.84, ["security", "tls"]),
    ("Input validation rejects malformed data before processing", 0.92, ["security", "defense"]),
    ("RBAC assigns permissions based on user roles", 0.89, ["security", "access-control"]),
    ("Audit logging records security-relevant events for review", 0.87, ["security", "monitoring"]),
    (
        "DDoS attacks overwhelm services with massive traffic volume",
        0.90,
        ["security", "vulnerability"],
    ),
    ("VPNs create encrypted tunnels for secure remote access", 0.88, ["security", "networking"]),
    (
        "Zero trust architecture verifies every request regardless of source",
        0.86,
        ["security", "architecture"],
    ),
    (
        "Container scanning detects vulnerabilities in Docker images",
        0.83,
        ["security", "containers"],
    ),
    (
        "API gateways enforce authentication and rate limiting centrally",
        0.87,
        ["security", "infrastructure"],
    ),
    (
        "Encryption at rest protects stored data from unauthorized access",
        0.91,
        ["security", "encryption"],
    ),
    ("SIEM systems aggregate and analyze security event data", 0.82, ["security", "monitoring"]),
    ("Threat modeling identifies potential attack vectors early", 0.85, ["security", "design"]),
    (
        "Network segmentation limits lateral movement after a breach",
        0.88,
        ["security", "networking"],
    ),
    ("Dependency scanning finds known vulnerabilities in libraries", 0.84, ["security", "testing"]),
]

PERFORMANCE_FACTS = [
    (
        "Caching reduces latency by storing frequently accessed data",
        0.95,
        ["performance", "caching"],
    ),
    ("Database indexing speeds up query lookups dramatically", 0.94, ["performance", "database"]),
    (
        "Connection pooling reuses database connections to reduce overhead",
        0.92,
        ["performance", "database"],
    ),
    (
        "Lazy loading defers initialization until data is needed",
        0.89,
        ["performance", "optimization"],
    ),
    (
        "Compression reduces payload size for faster network transfer",
        0.91,
        ["performance", "networking"],
    ),
    (
        "Async processing prevents blocking during I/O operations",
        0.93,
        ["performance", "concurrency"],
    ),
    ("Memory leaks gradually consume resources until crash", 0.88, ["performance", "debugging"]),
    (
        "Profiling identifies hotspots where code spends most time",
        0.90,
        ["performance", "debugging"],
    ),
    (
        "Batch processing groups operations to reduce per-item overhead",
        0.87,
        ["performance", "optimization"],
    ),
    (
        "Read replicas offload read queries from the primary database",
        0.91,
        ["performance", "database", "scaling"],
    ),
    (
        "Sharding distributes data across multiple database nodes",
        0.90,
        ["performance", "database", "scaling"],
    ),
    ("Redis provides sub-millisecond in-memory caching", 0.93, ["performance", "caching", "redis"]),
    (
        "HTTP/2 multiplexes multiple requests over a single connection",
        0.86,
        ["performance", "networking"],
    ),
    ("Pagination limits query results to manageable page sizes", 0.85, ["performance", "api"]),
    (
        "Denormalization trades storage for faster read performance",
        0.84,
        ["performance", "database"],
    ),
    (
        "Thread pools limit concurrent threads to prevent resource exhaustion",
        0.87,
        ["performance", "concurrency"],
    ),
    ("Tail latency at P99 reveals worst-case user experience", 0.82, ["performance", "monitoring"]),
    (
        "Circuit breakers prevent cascading failures in distributed systems",
        0.89,
        ["performance", "resilience"],
    ),
    (
        "Horizontal scaling adds more machines to handle increased load",
        0.91,
        ["performance", "scaling"],
    ),
    ("Vertical scaling adds more resources to a single machine", 0.86, ["performance", "scaling"]),
    (
        "Write-ahead logging ensures database durability after crashes",
        0.83,
        ["performance", "database"],
    ),
    (
        "Event-driven architecture decouples components for better throughput",
        0.85,
        ["performance", "architecture"],
    ),
    (
        "CDN caching serves static assets from edge servers near users",
        0.90,
        ["performance", "caching", "cdn"],
    ),
    (
        "Query optimization rewrites SQL for better execution plans",
        0.88,
        ["performance", "database"],
    ),
    (
        "Prefetching loads anticipated data before it is requested",
        0.81,
        ["performance", "optimization"],
    ),
    (
        "Bloom filters quickly check set membership with minimal memory",
        0.80,
        ["performance", "data-structures"],
    ),
    (
        "Object pooling reuses expensive objects instead of creating new ones",
        0.82,
        ["performance", "optimization"],
    ),
    (
        "Load shedding drops low-priority requests under extreme load",
        0.84,
        ["performance", "resilience"],
    ),
    (
        "Adaptive throttling adjusts rate limits based on system health",
        0.83,
        ["performance", "resilience"],
    ),
    (
        "JIT compilation optimizes frequently executed code paths at runtime",
        0.87,
        ["performance", "optimization"],
    ),
]

# ---------------------------------------------------------------------------
# Evaluation questions
# ---------------------------------------------------------------------------

# (question, answer_keywords, requires_hive: bool)
# requires_hive=True means the answering agent needs cross-domain knowledge
EVAL_QUESTIONS = [
    # Local-only questions (agent should answer from own domain)
    (
        "infra",
        "How does Kubernetes manage container deployment?",
        ["kubernetes", "orchestrate", "container", "deployment", "scaling"],
        False,
    ),
    (
        "security",
        "What is SQL injection and how does it work?",
        ["sql", "injection", "malicious", "input"],
        False,
    ),
    (
        "performance",
        "How does database indexing improve query performance?",
        ["index", "query", "lookup", "speed"],
        False,
    ),
    # Cross-domain questions (need hive knowledge)
    (
        "infra",
        "How can TLS and encryption protect server communications?",
        ["tls", "encrypt", "traffic", "server"],
        True,  # infra agent needs security knowledge
    ),
    (
        "security",
        "How does caching at the CDN edge improve both security and performance?",
        ["caching", "cdn", "edge", "performance"],
        True,  # security agent needs performance/infra knowledge
    ),
    (
        "performance",
        "How do load balancers help with horizontal scaling?",
        ["load", "balancer", "distribute", "scaling"],
        True,  # performance agent needs infra knowledge
    ),
    # Combined questions (need both local + hive)
    (
        "infra",
        "What security measures should be applied to container deployments?",
        ["container", "security", "scanning", "vulnerability"],
        True,
    ),
    (
        "security",
        "How do rate limiting and circuit breakers prevent service degradation?",
        ["rate", "limit", "circuit", "breaker", "cascading"],
        True,
    ),
    (
        "performance",
        "What role do API gateways play in managing service performance?",
        ["api", "gateway", "authentication", "rate", "limiting"],
        True,
    ),
]


def _score_answer(retrieved_contents: list[str], answer_keywords: list[str]) -> float:
    """Score how well retrieved facts cover the answer keywords.

    Args:
        retrieved_contents: List of fact content strings retrieved
        answer_keywords: Keywords that should appear in a good answer

    Returns:
        Coverage score in [0.0, 1.0]
    """
    if not answer_keywords:
        return 1.0
    if not retrieved_contents:
        return 0.0

    combined_text = " ".join(retrieved_contents).lower()
    matches = sum(1 for kw in answer_keywords if kw.lower() in combined_text)
    return matches / len(answer_keywords)


def run_evaluation() -> dict:
    """Run the full hierarchical knowledge graph evaluation.

    Returns:
        Dict with detailed evaluation results
    """
    print("=" * 70)
    print("HIERARCHICAL KNOWLEDGE GRAPH EVALUATION")
    print("Experiment 4: Two-level graph with promotion/pull mechanics")
    print("=" * 70)

    # --- Setup: Build the graph ---
    policy = PromotionPolicy(confidence_threshold=0.6, consensus_required=2)
    hkg = HierarchicalKnowledgeGraph(promotion_policy=policy)

    agent_domains = {
        "infra": INFRASTRUCTURE_FACTS,
        "security": SECURITY_FACTS,
        "performance": PERFORMANCE_FACTS,
    }
    for agent_id in agent_domains:
        hkg.register_agent(agent_id)

    # --- Phase 1: Each agent learns 30 facts locally ---
    print("\n--- Phase 1: Learning (30 facts per agent) ---")
    for agent_id, facts in agent_domains.items():
        for content, conf, tags in facts:
            hkg.store_local_fact(agent_id, content, conf, tags)
        print(f"  {agent_id}: stored {len(facts)} local facts")

    stats_after_learning = hkg.get_stats()
    print(f"  Total local facts: {stats_after_learning['total_local_facts']}")

    # --- Phase 2: Each agent promotes top-10 highest-confidence facts ---
    print("\n--- Phase 2: Promotion (top-10 per agent, consensus=2) ---")
    promotion_results = {"proposed": 0, "promoted": 0, "pending": 0}

    for agent_id, facts in agent_domains.items():
        # Sort by confidence descending, take top 10
        sorted_facts = sorted(facts, key=lambda f: -f[1])[:10]
        for content, conf, tags in sorted_facts:
            hkg.promote_fact(agent_id, content, conf, tags)
            promotion_results["proposed"] += 1

    # Now each agent votes on the other agents' pending promotions
    pending = hkg.get_pending_promotions()
    print(f"  Pending after proposals: {len(pending)}")

    for pp in list(pending):
        # Each non-proposer agent votes based on relevance
        for voter_id in agent_domains:
            if voter_id == pp.proposer_agent_id:
                continue
            # Simple heuristic: approve if confidence > 0.8
            try:
                result = hkg.vote_on_promotion(voter_id, pp.fact_id, pp.confidence > 0.8)
                if result is not None:
                    promotion_results["promoted"] += 1
            except ValueError:
                pass  # Already voted (can happen if promotion auto-triggered)

    # Count any that were immediately promoted (consensus=2, proposer is 1)
    # The second voter triggers promotion
    remaining_pending = hkg.get_pending_promotions()
    promotion_results["pending"] = len(remaining_pending)

    # Count actually promoted
    stats_after_promotion = hkg.get_stats()
    promotion_results["promoted"] = stats_after_promotion["hive_facts"]

    print(f"  Proposed: {promotion_results['proposed']}")
    print(f"  Promoted to hive: {promotion_results['promoted']}")
    print(f"  Still pending: {promotion_results['pending']}")
    print(f"  Promotion rate: {stats_after_promotion['promotion_rate']:.1%}")

    # --- Phase 3: Agents pull relevant cross-domain facts ---
    print("\n--- Phase 3: Pull (agents pull cross-domain knowledge) ---")
    pull_counts = {}
    for agent_id in agent_domains:
        # Query hive for facts outside own domain
        other_domains = [d for d in agent_domains if d != agent_id]
        for domain in other_domains:
            results = hkg.query_hive(domain, limit=5)
            for hf in results:
                hkg.pull_hive_fact(agent_id, hf.fact_id)

        pulled = hkg.get_stats()["local_facts_per_agent"][agent_id] - 30
        pull_counts[agent_id] = pulled
        print(f"  {agent_id}: pulled {pulled} hive facts")

    # --- Phase 4: Evaluation ---
    print("\n--- Phase 4: Evaluation ---")
    print("-" * 70)

    baseline_scores = []
    hive_scores = []
    local_only_scores = []
    cross_domain_scores = []

    for agent_id, question, keywords, requires_hive in EVAL_QUESTIONS:
        # Baseline: local-only query
        local_results = hkg.query_local(agent_id, question, limit=10)
        local_contents = [lf.content for lf in local_results]
        baseline_score = _score_answer(local_contents, keywords)
        baseline_scores.append(baseline_score)

        # Hive-enhanced: combined query
        combined_results = hkg.query_combined(agent_id, question, limit=10)
        combined_contents = [r["content"] for r in combined_results]
        hive_score = _score_answer(combined_contents, keywords)
        hive_scores.append(hive_score)

        improvement = hive_score - baseline_score
        marker = " [CROSS-DOMAIN]" if requires_hive else " [LOCAL]"

        if requires_hive:
            cross_domain_scores.append((baseline_score, hive_score))
        else:
            local_only_scores.append((baseline_score, hive_score))

        print(f"\n  Q ({agent_id}): {question[:60]}...{marker}")
        print(f"    Baseline (local-only): {baseline_score:.0%}")
        print(f"    Hive-enhanced:         {hive_score:.0%}")
        if improvement > 0:
            print(f"    Improvement:           +{improvement:.0%}")
        elif improvement < 0:
            print(f"    Regression:            {improvement:.0%}")
        else:
            print("    No change")

    # --- Summary ---
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)

    avg_baseline = sum(baseline_scores) / len(baseline_scores) if baseline_scores else 0
    avg_hive = sum(hive_scores) / len(hive_scores) if hive_scores else 0

    print(f"\n  Overall Baseline (local-only):  {avg_baseline:.1%}")
    print(f"  Overall Hive-enhanced:          {avg_hive:.1%}")
    print(f"  Overall Improvement:            +{avg_hive - avg_baseline:.1%}")

    if local_only_scores:
        avg_local_baseline = sum(s[0] for s in local_only_scores) / len(local_only_scores)
        avg_local_hive = sum(s[1] for s in local_only_scores) / len(local_only_scores)
        print("\n  Local-only questions:")
        print(
            f"    Baseline: {avg_local_baseline:.1%}  |  Hive: {avg_local_hive:.1%}  |  Delta: {avg_local_hive - avg_local_baseline:+.1%}"
        )

    if cross_domain_scores:
        avg_cross_baseline = sum(s[0] for s in cross_domain_scores) / len(cross_domain_scores)
        avg_cross_hive = sum(s[1] for s in cross_domain_scores) / len(cross_domain_scores)
        print("\n  Cross-domain questions (hive knowledge needed):")
        print(
            f"    Baseline: {avg_cross_baseline:.1%}  |  Hive: {avg_cross_hive:.1%}  |  Delta: {avg_cross_hive - avg_cross_baseline:+.1%}"
        )

    final_stats = hkg.get_stats()
    print("\n  Knowledge Graph Stats:")
    print(f"    Registered agents:   {final_stats['registered_agents']}")
    print(f"    Total local facts:   {final_stats['total_local_facts']}")
    print(f"    Hive facts:          {final_stats['hive_facts']}")
    print(f"    Pending promotions:  {final_stats['pending_promotions']}")
    print(f"    Promotion rate:      {final_stats['promotion_rate']:.1%}")

    print("\n" + "=" * 70)

    return {
        "promotion": promotion_results,
        "baseline_avg": avg_baseline,
        "hive_avg": avg_hive,
        "improvement": avg_hive - avg_baseline,
        "local_only_scores": local_only_scores,
        "cross_domain_scores": cross_domain_scores,
        "stats": final_stats,
    }


if __name__ == "__main__":
    results = run_evaluation()
    sys.exit(0)
