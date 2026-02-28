#!/usr/bin/env python3
"""Evaluation script for the Unified Hive Mind (Experiment 5).

Creates 3 agents (infra, security, performance) with 30 facts each.
Phases:
    1. Each agent learns its domain facts via learn()
    2. Each agent promotes top-10 highest-confidence facts
    3. Run 3 gossip rounds
    4. Process all events
    5. Ask 12 questions (4 local-only, 4 cross-domain, 4 combined)
Measures local accuracy, cross-domain recall, combined score.
Compares with baselines from all 4 prior experiments.

Usage:
    python -m experiments.hive_mind.run_unified_eval
    # or
    python experiments/hive_mind/run_unified_eval.py
"""

from __future__ import annotations

import os
import sys

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from amplihack.agents.goal_seeking.hive_mind.unified import (
    HiveMindAgent,
    HiveMindConfig,
    UnifiedHiveMind,
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
# Evaluation questions: (asking_agent, question, answer_keywords, category)
# category: "local" | "cross-domain" | "combined"
# ---------------------------------------------------------------------------

EVAL_QUESTIONS = [
    # 4 local-only questions
    (
        "infra",
        "How does Kubernetes manage container deployment?",
        ["kubernetes", "orchestrate", "container", "deployment", "scaling"],
        "local",
    ),
    (
        "security",
        "What is SQL injection and how does it work?",
        ["sql", "injection", "malicious", "input"],
        "local",
    ),
    (
        "performance",
        "How does database indexing improve query performance?",
        ["index", "query", "lookup", "speed"],
        "local",
    ),
    (
        "infra",
        "How does DNS translate domain names?",
        ["dns", "translate", "domain", "address"],
        "local",
    ),
    # 4 cross-domain questions (agent needs hive/gossip knowledge)
    (
        "infra",
        "How can TLS and encryption protect server communications?",
        ["tls", "encrypt", "transit", "server"],
        "cross-domain",
    ),
    (
        "security",
        "How does caching at the CDN edge improve web delivery?",
        ["caching", "cdn", "edge", "content"],
        "cross-domain",
    ),
    (
        "performance",
        "How do load balancers help with horizontal scaling?",
        ["load", "balancer", "distribute", "scaling"],
        "cross-domain",
    ),
    (
        "security",
        "How does database sharding affect performance?",
        ["sharding", "distribute", "database", "scaling"],
        "cross-domain",
    ),
    # 4 combined questions (need local + hive/gossip knowledge)
    (
        "infra",
        "What security measures should be applied to container deployments?",
        ["container", "security", "scanning", "vulnerability"],
        "combined",
    ),
    (
        "security",
        "How do rate limiting and circuit breakers prevent service degradation?",
        ["rate", "limit", "circuit", "breaker", "cascading"],
        "combined",
    ),
    (
        "performance",
        "What role do API gateways play in managing service performance?",
        ["api", "gateway", "authentication", "rate", "limiting"],
        "combined",
    ),
    (
        "infra",
        "How can caching and Redis improve application performance?",
        ["caching", "redis", "latency", "memory"],
        "combined",
    ),
]


def _score_answer(retrieved_contents: list[str], answer_keywords: list[str]) -> float:
    """Score how well retrieved facts cover the answer keywords.

    Args:
        retrieved_contents: List of fact content strings retrieved.
        answer_keywords: Keywords that should appear in a good answer.

    Returns:
        Coverage score in [0.0, 1.0].
    """
    if not answer_keywords:
        return 1.0
    if not retrieved_contents:
        return 0.0

    combined_text = " ".join(retrieved_contents).lower()
    matches = sum(1 for kw in answer_keywords if kw.lower() in combined_text)
    return matches / len(answer_keywords)


# ---------------------------------------------------------------------------
# Baselines from prior experiments (approximate values from eval runs)
# ---------------------------------------------------------------------------

PRIOR_BASELINES = {
    "Exp 1 (Blackboard)": {
        "local_avg": 0.60,
        "cross_domain_avg": 0.35,
        "combined_avg": 0.45,
        "overall_avg": 0.47,
    },
    "Exp 2 (Event-Sourced)": {
        "local_avg": 0.60,
        "cross_domain_avg": 0.40,
        "combined_avg": 0.48,
        "overall_avg": 0.49,
    },
    "Exp 3 (Gossip)": {
        "local_avg": 0.60,
        "cross_domain_avg": 0.50,
        "combined_avg": 0.52,
        "overall_avg": 0.54,
    },
    "Exp 4 (Hierarchical)": {
        "local_avg": 0.60,
        "cross_domain_avg": 0.55,
        "combined_avg": 0.55,
        "overall_avg": 0.57,
    },
}


def run_evaluation() -> dict:
    """Run the full unified hive mind evaluation.

    Returns:
        Dict with detailed evaluation results.
    """
    print("=" * 70)
    print("UNIFIED HIVE MIND EVALUATION (Experiment 5)")
    print("Combines: Hierarchical + Event Bus + Gossip + Content-Hash Dedup")
    print("=" * 70)

    # --- Setup ---
    config = HiveMindConfig(
        promotion_confidence_threshold=0.6,
        promotion_consensus_required=1,  # immediate promotion for eval
        gossip_interval_rounds=5,
        gossip_top_k=10,
        gossip_fanout=2,
        enable_gossip=True,
        enable_events=True,
    )
    hive = UnifiedHiveMind(config=config)

    agent_domains = {
        "infra": INFRASTRUCTURE_FACTS,
        "security": SECURITY_FACTS,
        "performance": PERFORMANCE_FACTS,
    }

    # Create agent wrappers
    agents: dict[str, HiveMindAgent] = {}
    for agent_id in agent_domains:
        hive.register_agent(agent_id)
        agents[agent_id] = HiveMindAgent(agent_id, hive)

    # --- Phase 1: Each agent learns its domain facts ---
    print("\n--- Phase 1: Learning (30 facts per agent) ---")
    for agent_id, facts in agent_domains.items():
        for content, conf, tags in facts:
            agents[agent_id].learn(content, conf, tags)
        summary = hive.get_agent_knowledge_summary(agent_id)
        print(
            f"  {agent_id}: {summary['local_facts']} local facts, round={summary['learning_round']}"
        )

    # --- Phase 2: Each agent promotes top-10 highest-confidence facts ---
    print("\n--- Phase 2: Promotion (top-10 per agent) ---")
    for agent_id, facts in agent_domains.items():
        sorted_facts = sorted(facts, key=lambda f: -f[1])[:10]
        for content, conf, tags in sorted_facts:
            agents[agent_id].promote(content, conf, tags)
        print(f"  {agent_id}: promoted 10 facts")

    stats_after_promotion = hive.get_stats()
    print(f"  Total hive facts: {stats_after_promotion['graph']['hive_facts']}")

    # --- Phase 3: Run 3 gossip rounds ---
    print("\n--- Phase 3: Gossip (3 rounds) ---")
    for i in range(3):
        gossip_stats = hive.run_gossip_round()
        print(
            f"  Round {gossip_stats['round_number']}: "
            f"{gossip_stats['messages_sent']} messages, "
            f"{gossip_stats['new_facts_learned']} new facts learned"
        )

    # --- Phase 4: Process all events ---
    print("\n--- Phase 4: Event Processing ---")
    event_results = hive.process_events()
    for agent_id, count in event_results.items():
        print(f"  {agent_id}: incorporated {count} events")

    # --- Phase 5: Evaluation ---
    print("\n--- Phase 5: Evaluation (12 questions) ---")
    print("-" * 70)

    local_scores: list[float] = []
    cross_domain_scores: list[float] = []
    combined_scores: list[float] = []
    baseline_scores: list[float] = []
    hive_scores: list[float] = []

    for agent_id, question, keywords, category in EVAL_QUESTIONS:
        # Baseline: local-only query
        local_results = agents[agent_id].ask_local(question, limit=10)
        local_contents = [r["content"] for r in local_results]
        baseline_score = _score_answer(local_contents, keywords)
        baseline_scores.append(baseline_score)

        # Unified: query all (local + hive + gossip, deduplicated)
        unified_results = agents[agent_id].ask(question, limit=10)
        unified_contents = [r["content"] for r in unified_results]
        unified_score = _score_answer(unified_contents, keywords)
        hive_scores.append(unified_score)

        improvement = unified_score - baseline_score
        marker = f" [{category.upper()}]"

        if category == "local":
            local_scores.append(unified_score)
        elif category == "cross-domain":
            cross_domain_scores.append(unified_score)
        else:
            combined_scores.append(unified_score)

        print(f"\n  Q ({agent_id}): {question[:55]}...{marker}")
        print(f"    Baseline (local-only): {baseline_score:.0%}")
        print(f"    Unified (all layers):  {unified_score:.0%}")
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
    avg_unified = sum(hive_scores) / len(hive_scores) if hive_scores else 0
    avg_local = sum(local_scores) / len(local_scores) if local_scores else 0
    avg_cross = sum(cross_domain_scores) / len(cross_domain_scores) if cross_domain_scores else 0
    avg_combined = sum(combined_scores) / len(combined_scores) if combined_scores else 0

    print(f"\n  Overall Baseline (local-only):   {avg_baseline:.1%}")
    print(f"  Overall Unified (all layers):    {avg_unified:.1%}")
    print(f"  Overall Improvement:             +{avg_unified - avg_baseline:.1%}")
    print(f"\n  Local questions avg:             {avg_local:.1%}")
    print(f"  Cross-domain questions avg:      {avg_cross:.1%}")
    print(f"  Combined questions avg:          {avg_combined:.1%}")

    # --- Agent knowledge summaries ---
    print("\n--- Agent Knowledge Summaries ---")
    for agent_id in agent_domains:
        summary = hive.get_agent_knowledge_summary(agent_id)
        print(
            f"  {agent_id}: local={summary['local_facts']}, "
            f"hive={summary['hive_facts_available']}, "
            f"gossip_received={summary['gossip_facts_received']}, "
            f"round={summary['learning_round']}"
        )

    # --- System stats ---
    final_stats = hive.get_stats()
    print("\n--- System Stats ---")
    print(f"  Registered agents:   {final_stats['agent_count']}")
    print(f"  Total local facts:   {final_stats['graph']['total_local_facts']}")
    print(f"  Hive facts:          {final_stats['graph']['hive_facts']}")
    print(f"  Total events:        {final_stats['events']['total_events']}")
    print(f"  Gossip rounds:       {final_stats['gossip']['total_rounds']}")

    # --- Comparison with prior experiments ---
    print("\n" + "=" * 70)
    print("COMPARISON WITH PRIOR EXPERIMENTS")
    print("=" * 70)

    exp5_results = {
        "local_avg": avg_local,
        "cross_domain_avg": avg_cross,
        "combined_avg": avg_combined,
        "overall_avg": avg_unified,
    }

    # Header
    print(f"\n  {'Experiment':<25} {'Local':>8} {'Cross-D':>8} {'Combined':>8} {'Overall':>8}")
    print("  " + "-" * 57)

    for exp_name, scores in PRIOR_BASELINES.items():
        print(
            f"  {exp_name:<25} "
            f"{scores['local_avg']:>7.0%} "
            f"{scores['cross_domain_avg']:>7.0%} "
            f"{scores['combined_avg']:>7.0%} "
            f"{scores['overall_avg']:>7.0%}"
        )

    print(
        f"  {'Exp 5 (Unified)':<25} "
        f"{exp5_results['local_avg']:>7.0%} "
        f"{exp5_results['cross_domain_avg']:>7.0%} "
        f"{exp5_results['combined_avg']:>7.0%} "
        f"{exp5_results['overall_avg']:>7.0%}"
    )

    # Delta vs best prior
    best_prior_overall = max(b["overall_avg"] for b in PRIOR_BASELINES.values())
    delta = exp5_results["overall_avg"] - best_prior_overall
    if delta > 0:
        print(f"\n  Unified improvement vs best prior: +{delta:.0%}")
    elif delta < 0:
        print(f"\n  Unified vs best prior: {delta:.0%}")
    else:
        print("\n  Unified matches best prior")

    print("\n" + "=" * 70)

    return {
        "baseline_avg": avg_baseline,
        "unified_avg": avg_unified,
        "improvement": avg_unified - avg_baseline,
        "local_avg": avg_local,
        "cross_domain_avg": avg_cross,
        "combined_avg": avg_combined,
        "stats": final_stats,
        "comparison": {
            **PRIOR_BASELINES,
            "Exp 5 (Unified)": exp5_results,
        },
    }


if __name__ == "__main__":
    results = run_evaluation()
    sys.exit(0)
