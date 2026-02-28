#!/usr/bin/env python3
"""Rigorous 5-Agent Hive Mind Evaluation.

Tests whether the hive mind ARCHITECTURE provides value beyond simple data
sharing. The original eval only proved sharing > isolation (obvious). This
eval adds the critical FLAT_SHARED baseline to answer: does the hive's
promotion/gossip/event machinery outperform just giving everyone all facts?

4 conditions:
    ISOLATED     -- each agent sees only its own 25 facts
    FLAT_SHARED  -- all agents get ALL 125 facts via bulk INSERT (no hive machinery)
    GOSSIP_ONLY  -- gossip rounds only, no promotion or events
    HIVE         -- full promotion + gossip + events

Additional tests:
    - ask() vs ask_local() comparison (does query layer add value?)
    - Adversarial resilience (do wrong facts propagate and corrupt answers?)
    - Precision under noise (distractor facts degrade signal?)
    - Precision/Recall/F1 scoring (not just keyword recall)

Usage:
    uv run python experiments/hive_mind/run_rigorous_eval.py
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

# ---------------------------------------------------------------------------
# Import fact data and questions from the original eval
# ---------------------------------------------------------------------------
from run_5agent_real_eval import (  # type: ignore[import-not-found]
    AGENT_DOMAINS,
    EVAL_QUESTIONS,
)

from amplihack.agents.goal_seeking.hive_mind.unified import (
    HiveMindAgent,
    HiveMindConfig,
    UnifiedHiveMind,
)

# All 125 facts as a flat list
ALL_FACTS: list[tuple[str, float, list[str]]] = []
for facts in AGENT_DOMAINS.values():
    ALL_FACTS.extend(facts)

# ---------------------------------------------------------------------------
# Adversarial facts: plausible but WRONG
# ---------------------------------------------------------------------------

ADVERSARIAL_FACTS: list[tuple[str, float, list[str], str]] = [
    (
        "PostgreSQL default port is 3306",
        0.92,
        ["storage", "postgresql"],
        "WRONG: 3306 is MySQL's port, PostgreSQL uses 5432",
    ),
    (
        "Redis stores data on disk by default and loads it into memory on demand",
        0.90,
        ["storage", "redis"],
        "WRONG: Redis stores data in memory by default",
    ),
    (
        "Kubernetes uses Docker as its default container runtime since version 1.24",
        0.91,
        ["compute", "kubernetes", "docker"],
        "WRONG: Kubernetes removed dockershim in 1.24, uses containerd",
    ),
    (
        "UDP provides reliable ordered delivery of data packets using acknowledgments",
        0.93,
        ["networking", "udp"],
        "WRONG: UDP is unreliable and unordered, this describes TCP",
    ),
    (
        "JWT tokens are encrypted by default to protect their claims from being read",
        0.89,
        ["security", "jwt"],
        "WRONG: JWT tokens are signed, not encrypted. Claims are base64-encoded and readable",
    ),
]

# Correct facts the adversarial facts contradict (for corruption detection)
ADVERSARIAL_CORRECT_KEYWORDS: list[tuple[str, list[str]]] = [
    # For each adversarial fact, the question and keywords that should NOT
    # return the wrong fact if the system is resilient
    ("What port does PostgreSQL use?", ["5432"]),
    ("How does Redis store data?", ["in-memory", "memory"]),
    ("What container runtime does Kubernetes use?", ["containerd"]),
    ("How does UDP handle data delivery?", ["connectionless", "not guarantee"]),
    ("Are JWT tokens encrypted?", ["signed", "digitally signed"]),
]

# 10 correct facts the adversarial agent also knows
ADVERSARIAL_CORRECT_FACTS: list[tuple[str, float, list[str]]] = [
    ("HTTP status code 404 means resource not found", 0.95, ["networking", "http"]),
    ("SSH uses port 22 for secure remote access", 0.94, ["networking", "ssh"]),
    ("JSON is a lightweight data interchange format", 0.92, ["storage", "json"]),
    ("YAML is commonly used for configuration files", 0.90, ["compute", "yaml"]),
    ("HTTPS uses port 443 for encrypted web traffic", 0.93, ["networking", "https"]),
    ("REST APIs use HTTP methods like GET POST PUT DELETE", 0.91, ["networking", "rest"]),
    ("Base64 encoding converts binary data to ASCII text", 0.88, ["security", "encoding"]),
    ("Cron syntax uses five fields for scheduling tasks", 0.87, ["compute", "cron"]),
    ("UTF-8 is the dominant character encoding on the web", 0.86, ["networking", "encoding"]),
    ("TCP uses a three-way handshake to establish connections", 0.94, ["networking", "tcp"]),
]

# ---------------------------------------------------------------------------
# Distractor facts: plausible, true, but irrelevant to any eval questions
# ---------------------------------------------------------------------------

DISTRACTOR_FACTS_PER_AGENT: dict[str, list[tuple[str, float, list[str]]]] = {
    "networking_agent": [
        (
            "The speed of light in vacuum is approximately 299792458 meters per second",
            0.95,
            ["physics"],
        ),
        ("The Mariana Trench is the deepest oceanic trench on Earth", 0.93, ["geography"]),
        (
            "Photosynthesis converts carbon dioxide and water into glucose and oxygen",
            0.94,
            ["biology"],
        ),
        ("The Great Wall of China is visible from low Earth orbit", 0.80, ["geography"]),
        ("Mitochondria are often called the powerhouse of the cell", 0.96, ["biology"]),
        ("Mount Everest is 8849 meters above sea level", 0.97, ["geography"]),
        ("The human body contains approximately 206 bones", 0.95, ["anatomy"]),
        (
            "Water freezes at 0 degrees Celsius at standard atmospheric pressure",
            0.99,
            ["chemistry"],
        ),
        ("The periodic table has 118 confirmed elements", 0.98, ["chemistry"]),
        ("Pi is approximately 3.14159265358979", 0.99, ["mathematics"]),
    ],
    "storage_agent": [
        (
            "The Amazon rainforest produces about 20 percent of the world's oxygen",
            0.88,
            ["ecology"],
        ),
        ("Diamond is the hardest naturally occurring material", 0.96, ["geology"]),
        ("The human genome contains approximately 3 billion base pairs", 0.94, ["genetics"]),
        ("Sound travels at approximately 343 meters per second in air", 0.95, ["physics"]),
        (
            "The Sahara Desert spans approximately 9.2 million square kilometers",
            0.93,
            ["geography"],
        ),
        ("Iron has the atomic number 26 on the periodic table", 0.98, ["chemistry"]),
        ("The moon orbits Earth at an average distance of 384400 kilometers", 0.96, ["astronomy"]),
        ("Copper is an excellent conductor of electricity", 0.95, ["physics"]),
        ("The Pacific Ocean is the largest ocean on Earth", 0.97, ["geography"]),
        ("Helium is the second lightest element in the periodic table", 0.98, ["chemistry"]),
    ],
    "compute_agent": [
        ("The Fibonacci sequence starts with 0 1 1 2 3 5 8 13", 0.99, ["mathematics"]),
        ("Jupiter is the largest planet in the solar system", 0.98, ["astronomy"]),
        ("The speed of sound increases with temperature", 0.93, ["physics"]),
        ("DNA has a double helix structure discovered by Watson and Crick", 0.95, ["biology"]),
        ("Gold has the chemical symbol Au from the Latin aurum", 0.97, ["chemistry"]),
        ("The Earth rotates on its axis approximately once every 24 hours", 0.99, ["astronomy"]),
        ("Absolute zero is 0 Kelvin or minus 273.15 degrees Celsius", 0.98, ["physics"]),
        ("The ozone layer absorbs most of the Sun's ultraviolet radiation", 0.94, ["ecology"]),
        ("Mercury is the smallest planet in the solar system", 0.97, ["astronomy"]),
        ("Chlorophyll gives plants their green color", 0.96, ["biology"]),
    ],
    "security_agent": [
        (
            "The Nile is traditionally considered the longest river in the world",
            0.92,
            ["geography"],
        ),
        ("Einstein published his theory of special relativity in 1905", 0.97, ["physics"]),
        ("Gravity on the Moon is about one-sixth of Earth's gravity", 0.96, ["physics"]),
        ("The boiling point of water decreases at higher altitudes", 0.94, ["chemistry"]),
        (
            "Venus is the hottest planet in the solar system due to its greenhouse effect",
            0.95,
            ["astronomy"],
        ),
        ("The human heart beats approximately 100000 times per day", 0.90, ["anatomy"]),
        ("Nitrogen makes up about 78 percent of Earth's atmosphere", 0.97, ["chemistry"]),
        (
            "The circumference of the Earth at the equator is about 40075 kilometers",
            0.96,
            ["geography"],
        ),
        ("Red blood cells carry oxygen to tissues throughout the body", 0.95, ["biology"]),
        ("Pluto was reclassified as a dwarf planet in 2006", 0.98, ["astronomy"]),
    ],
    "observability_agent": [
        ("The Atlantic Ocean is the second largest ocean", 0.96, ["geography"]),
        ("Carbon has four valence electrons and can form four bonds", 0.97, ["chemistry"]),
        ("The human brain contains approximately 86 billion neurons", 0.93, ["neuroscience"]),
        (
            "Mars has the tallest volcano in the solar system called Olympus Mons",
            0.95,
            ["astronomy"],
        ),
        (
            "Silk is produced by silkworms and is one of the strongest natural fibers",
            0.91,
            ["biology"],
        ),
        ("Aluminum is the most abundant metal in the Earth's crust", 0.96, ["geology"]),
        ("Saturn's rings are mostly made of ice particles and rocky debris", 0.94, ["astronomy"]),
        ("Insulin regulates blood sugar levels in the human body", 0.95, ["biology"]),
        (
            "The Bermuda Triangle is located in the western part of the North Atlantic",
            0.88,
            ["geography"],
        ),
        ("Sharks have been around for more than 400 million years", 0.93, ["biology"]),
    ],
}


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------


def score_recall(retrieved_contents: list[str], answer_keywords: list[str]) -> float:
    """Fraction of expected keywords found in retrieved text."""
    if not answer_keywords:
        return 1.0
    if not retrieved_contents:
        return 0.0
    combined = " ".join(retrieved_contents).lower()
    hits = sum(1 for kw in answer_keywords if kw.lower() in combined)
    return hits / len(answer_keywords)


def score_precision(retrieved_contents: list[str], answer_keywords: list[str]) -> float:
    """Fraction of retrieved facts that contain at least 1 expected keyword.

    Measures noise: if the retrieval returns 10 facts but only 3 are relevant,
    precision is 0.3. High precision means the retrieval is not flooding the
    agent with irrelevant information.
    """
    if not retrieved_contents:
        return 0.0
    if not answer_keywords:
        return 1.0
    keywords_lower = [kw.lower() for kw in answer_keywords]
    relevant = 0
    for content in retrieved_contents:
        content_lower = content.lower()
        if any(kw in content_lower for kw in keywords_lower):
            relevant += 1
    return relevant / len(retrieved_contents)


def score_f1(precision: float, recall: float) -> float:
    """Harmonic mean of precision and recall."""
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# Setup helpers for each condition
# ---------------------------------------------------------------------------


def _setup_isolated() -> dict[str, HiveMindAgent]:
    """ISOLATED: each agent sees only its own 25 facts. No sharing at all."""
    config = HiveMindConfig(
        promotion_confidence_threshold=1.0,
        promotion_consensus_required=99,
        enable_gossip=False,
        enable_events=False,
    )
    hive = UnifiedHiveMind(config=config)
    agents: dict[str, HiveMindAgent] = {}
    for agent_id in AGENT_DOMAINS:
        hive.register_agent(agent_id)
        agents[agent_id] = HiveMindAgent(agent_id, hive)
    for agent_id, facts in AGENT_DOMAINS.items():
        for content, conf, tags in facts:
            agents[agent_id].learn(content, conf, tags)
    return agents


def _setup_flat_shared() -> dict[str, HiveMindAgent]:
    """FLAT_SHARED: every agent gets ALL 125 facts bulk-inserted locally.

    No promotion, no gossip, no events. Just dump everything into each agent's
    local store. This is the critical baseline -- if hive can't beat this,
    the architecture adds no value over simple data replication.
    """
    config = HiveMindConfig(
        promotion_confidence_threshold=1.0,
        promotion_consensus_required=99,
        enable_gossip=False,
        enable_events=False,
    )
    hive = UnifiedHiveMind(config=config)
    agents: dict[str, HiveMindAgent] = {}
    for agent_id in AGENT_DOMAINS:
        hive.register_agent(agent_id)
        agents[agent_id] = HiveMindAgent(agent_id, hive)
    # Bulk insert ALL facts into EVERY agent's local store
    for agent_id in AGENT_DOMAINS:
        for content, conf, tags in ALL_FACTS:
            agents[agent_id].learn(content, conf, tags)
    return agents


def _setup_gossip_only() -> dict[str, HiveMindAgent]:
    """GOSSIP_ONLY: agents learn own facts, then gossip. No promotion, no events."""
    config = HiveMindConfig(
        promotion_confidence_threshold=1.0,  # never promote
        promotion_consensus_required=99,
        gossip_interval_rounds=5,
        gossip_top_k=10,
        gossip_fanout=3,
        enable_gossip=True,
        enable_events=False,
    )
    hive = UnifiedHiveMind(config=config)
    agents: dict[str, HiveMindAgent] = {}
    for agent_id in AGENT_DOMAINS:
        hive.register_agent(agent_id)
        agents[agent_id] = HiveMindAgent(agent_id, hive)
    for agent_id, facts in AGENT_DOMAINS.items():
        for content, conf, tags in facts:
            agents[agent_id].learn(content, conf, tags)
    # Run gossip rounds
    for _ in range(5):
        hive.run_gossip_round()
    return agents


def _setup_hive() -> tuple[dict[str, HiveMindAgent], UnifiedHiveMind]:
    """HIVE: full promotion + gossip + events (same as original eval)."""
    config = HiveMindConfig(
        promotion_confidence_threshold=0.5,
        promotion_consensus_required=1,
        gossip_interval_rounds=5,
        gossip_top_k=10,
        gossip_fanout=3,
        enable_gossip=True,
        enable_events=True,
    )
    hive = UnifiedHiveMind(config=config)
    agents: dict[str, HiveMindAgent] = {}
    for agent_id in AGENT_DOMAINS:
        hive.register_agent(agent_id)
        agents[agent_id] = HiveMindAgent(agent_id, hive)
    # Phase 1: Learn
    for agent_id, facts in AGENT_DOMAINS.items():
        for content, conf, tags in facts:
            agents[agent_id].learn(content, conf, tags)
    # Phase 2: Promote top-10 per agent
    for agent_id, facts in AGENT_DOMAINS.items():
        sorted_facts = sorted(facts, key=lambda f: -f[1])[:10]
        for content, conf, tags in sorted_facts:
            agents[agent_id].promote(content, conf, tags)
    # Phase 3: Gossip
    for _ in range(5):
        hive.run_gossip_round()
    # Phase 4: Event processing
    hive.process_events()
    return agents, hive


# ---------------------------------------------------------------------------
# Adversarial setup
# ---------------------------------------------------------------------------


def _setup_hive_with_adversary() -> tuple[dict[str, HiveMindAgent], UnifiedHiveMind]:
    """HIVE + adversarial agent with 10 correct and 5 wrong facts."""
    config = HiveMindConfig(
        promotion_confidence_threshold=0.5,
        promotion_consensus_required=1,
        gossip_interval_rounds=5,
        gossip_top_k=10,
        gossip_fanout=3,
        enable_gossip=True,
        enable_events=True,
    )
    hive = UnifiedHiveMind(config=config)
    agents: dict[str, HiveMindAgent] = {}

    # Register the 5 standard agents
    for agent_id in AGENT_DOMAINS:
        hive.register_agent(agent_id)
        agents[agent_id] = HiveMindAgent(agent_id, hive)

    # Register adversarial agent
    hive.register_agent("adversarial_agent")
    agents["adversarial_agent"] = HiveMindAgent("adversarial_agent", hive)

    # Standard agents learn their facts
    for agent_id, facts in AGENT_DOMAINS.items():
        for content, conf, tags in facts:
            agents[agent_id].learn(content, conf, tags)

    # Adversarial agent learns correct + wrong facts
    for content, conf, tags in ADVERSARIAL_CORRECT_FACTS:
        agents["adversarial_agent"].learn(content, conf, tags)
    for content, conf, tags, _reason in ADVERSARIAL_FACTS:
        agents["adversarial_agent"].learn(content, conf, tags)

    # Promote: standard agents promote top-10
    for agent_id, facts in AGENT_DOMAINS.items():
        sorted_facts = sorted(facts, key=lambda f: -f[1])[:10]
        for content, conf, tags in sorted_facts:
            agents[agent_id].promote(content, conf, tags)

    # Adversarial agent promotes ALL its facts (including wrong ones)
    for content, conf, tags in ADVERSARIAL_CORRECT_FACTS:
        agents["adversarial_agent"].promote(content, conf, tags)
    for content, conf, tags, _reason in ADVERSARIAL_FACTS:
        agents["adversarial_agent"].promote(content, conf, tags)

    # Gossip
    for _ in range(5):
        hive.run_gossip_round()

    # Events
    hive.process_events()

    return agents, hive


# ---------------------------------------------------------------------------
# Distractor setup
# ---------------------------------------------------------------------------


def _setup_hive_with_distractors() -> tuple[dict[str, HiveMindAgent], UnifiedHiveMind]:
    """HIVE + 10 distractor facts per agent (50 extra irrelevant facts)."""
    config = HiveMindConfig(
        promotion_confidence_threshold=0.5,
        promotion_consensus_required=1,
        gossip_interval_rounds=5,
        gossip_top_k=10,
        gossip_fanout=3,
        enable_gossip=True,
        enable_events=True,
    )
    hive = UnifiedHiveMind(config=config)
    agents: dict[str, HiveMindAgent] = {}
    for agent_id in AGENT_DOMAINS:
        hive.register_agent(agent_id)
        agents[agent_id] = HiveMindAgent(agent_id, hive)

    # Learn domain facts + distractors
    for agent_id, facts in AGENT_DOMAINS.items():
        for content, conf, tags in facts:
            agents[agent_id].learn(content, conf, tags)
        for content, conf, tags in DISTRACTOR_FACTS_PER_AGENT[agent_id]:
            agents[agent_id].learn(content, conf, tags)

    # Promote top-10 per agent (from domain facts only)
    for agent_id, facts in AGENT_DOMAINS.items():
        sorted_facts = sorted(facts, key=lambda f: -f[1])[:10]
        for content, conf, tags in sorted_facts:
            agents[agent_id].promote(content, conf, tags)

    # Gossip
    for _ in range(5):
        hive.run_gossip_round()

    # Events
    hive.process_events()

    return agents, hive


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------


def _evaluate_condition(
    agents: dict[str, HiveMindAgent],
    use_ask: bool = True,
) -> Any:
    """Run all 30 questions against a set of agents.

    Args:
        agents: Agent dict (must contain the 5 standard agent IDs).
        use_ask: If True, use ask() (all layers). If False, use ask_local().

    Returns:
        Dict with per-category lists of (recall, precision, f1) tuples.
    """
    results: dict[str, list[tuple[float, float, float]]] = {
        "single-domain": [],
        "cross-domain": [],
        "synthesis": [],
    }

    for agent_id, question, keywords, category in EVAL_QUESTIONS:
        if agent_id not in agents:
            continue
        if use_ask:
            retrieved = agents[agent_id].ask(question, limit=15)
        else:
            retrieved = agents[agent_id].ask_local(question, limit=15)
        contents = [r["content"] for r in retrieved]

        r = score_recall(contents, keywords)
        p = score_precision(contents, keywords)
        f = score_f1(p, r)
        results[category].append((r, p, f))

    return results


def _avg_metrics(
    results: Any,
) -> dict[str, tuple[float, float, float]]:
    """Average recall, precision, F1 per category and overall."""
    out: dict[str, tuple[float, float, float]] = {}
    all_scores: list[tuple[float, float, float]] = []

    for cat, scores in results.items():
        if not scores:
            out[cat] = (0.0, 0.0, 0.0)
            continue
        avg_r = sum(s[0] for s in scores) / len(scores)
        avg_p = sum(s[1] for s in scores) / len(scores)
        avg_f = sum(s[2] for s in scores) / len(scores)
        out[cat] = (avg_r, avg_p, avg_f)
        all_scores.extend(scores)

    if all_scores:
        out["overall"] = (
            sum(s[0] for s in all_scores) / len(all_scores),
            sum(s[1] for s in all_scores) / len(all_scores),
            sum(s[2] for s in all_scores) / len(all_scores),
        )
    else:
        out["overall"] = (0.0, 0.0, 0.0)

    return out


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------


def run_rigorous_evaluation() -> dict[str, Any]:
    """Run the rigorous 4-condition + adversarial + noise evaluation."""

    print("=" * 74)
    print("          RIGOROUS 5-AGENT HIVE MIND EVALUATION")
    print("=" * 74)
    print("Conditions: ISOLATED | FLAT_SHARED | GOSSIP_ONLY | HIVE")
    print("Agents: 5 | Facts/agent: 25 | Total: 125 | Questions: 30")
    print("Metrics: Recall, Precision, F1")
    print("=" * 74)

    t0 = time.perf_counter()

    # ---- Condition 1: ISOLATED ----
    print("\n--- Setting up ISOLATED condition ---")
    iso_agents = _setup_isolated()
    iso_results = _evaluate_condition(iso_agents, use_ask=False)
    iso_metrics = _avg_metrics(iso_results)
    print("  Done. (each agent: 25 local facts, no sharing)")

    # ---- Condition 2: FLAT_SHARED ----
    print("\n--- Setting up FLAT_SHARED condition ---")
    flat_agents = _setup_flat_shared()
    flat_results = _evaluate_condition(flat_agents, use_ask=False)
    flat_metrics = _avg_metrics(flat_results)
    print("  Done. (each agent: 125 local facts, bulk INSERT)")

    # ---- Condition 3: GOSSIP_ONLY ----
    print("\n--- Setting up GOSSIP_ONLY condition ---")
    gossip_agents = _setup_gossip_only()
    gossip_results = _evaluate_condition(gossip_agents, use_ask=True)
    gossip_metrics = _avg_metrics(gossip_results)
    print("  Done. (25 local + gossip, no promotion/events)")

    # ---- Condition 4: HIVE ----
    print("\n--- Setting up HIVE condition ---")
    hive_agents, hive_obj = _setup_hive()
    hive_results = _evaluate_condition(hive_agents, use_ask=True)
    hive_metrics = _avg_metrics(hive_results)
    print("  Done. (25 local + promote + gossip + events)")

    elapsed_baseline = time.perf_counter() - t0

    # ==================================================================
    # BASELINE COMPARISON TABLE
    # ==================================================================
    print("\n" + "=" * 74)
    print("--- BASELINE COMPARISON (the REAL test) ---")
    print("=" * 74)

    header = f"{'':20s} {'ISOLATED':>10s} {'FLAT_SHARED':>12s} {'GOSSIP_ONLY':>12s} {'HIVE':>10s}"
    print(header)
    print("-" * 66)

    for metric_name, idx in [("Recall", 0), ("Precision", 1), ("F1", 2)]:
        iso_v = iso_metrics["overall"][idx]
        flat_v = flat_metrics["overall"][idx]
        gossip_v = gossip_metrics["overall"][idx]
        hive_v = hive_metrics["overall"][idx]
        print(f"{metric_name:20s} {iso_v:>9.1%} {flat_v:>11.1%} {gossip_v:>11.1%} {hive_v:>9.1%}")

    # Category breakdown
    print()
    for cat_label, cat_key in [
        ("Single-domain", "single-domain"),
        ("Cross-domain", "cross-domain"),
        ("Synthesis", "synthesis"),
    ]:
        print(f"  {cat_label}:")
        for metric_name, idx in [("    Recall", 0), ("    Precision", 1), ("    F1", 2)]:
            iso_v = iso_metrics[cat_key][idx]
            flat_v = flat_metrics[cat_key][idx]
            gossip_v = gossip_metrics[cat_key][idx]
            hive_v = hive_metrics[cat_key][idx]
            print(
                f"{metric_name:20s} {iso_v:>9.1%} {flat_v:>11.1%} {gossip_v:>11.1%} {hive_v:>9.1%}"
            )
        print()

    # The critical delta
    hive_f1 = hive_metrics["overall"][2]
    flat_f1 = flat_metrics["overall"][2]
    delta_pp = (hive_f1 - flat_f1) * 100
    print(f"CRITICAL: Hive vs Flat-Shared F1 delta: {delta_pp:+.1f}pp", end="")
    if delta_pp > 0:
        print(" (>0 means hive architecture adds value)")
    elif delta_pp == 0:
        print(" (=0 means hive adds nothing over bulk sharing)")
    else:
        print(" (<0 means hive is WORSE than simple bulk sharing)")

    hive_recall = hive_metrics["overall"][0]
    flat_recall = flat_metrics["overall"][0]
    delta_recall_pp = (hive_recall - flat_recall) * 100
    print(f"CRITICAL: Hive vs Flat-Shared Recall delta: {delta_recall_pp:+.1f}pp")

    # ==================================================================
    # ask() vs ask_local() COMPARISON
    # ==================================================================
    print("\n" + "=" * 74)
    print("--- HIVE ask() vs ask_local() ---")
    print("=" * 74)

    hive_local_results = _evaluate_condition(hive_agents, use_ask=False)
    hive_local_metrics = _avg_metrics(hive_local_results)

    same_count = 0
    ask_better = 0
    local_better = 0

    for agent_id, question, keywords, category in EVAL_QUESTIONS:
        # ask() results
        ask_retrieved = hive_agents[agent_id].ask(question, limit=15)
        ask_contents = [r["content"] for r in ask_retrieved]
        ask_recall = score_recall(ask_contents, keywords)

        # ask_local() results
        local_retrieved = hive_agents[agent_id].ask_local(question, limit=15)
        local_contents = [r["content"] for r in local_retrieved]
        local_recall = score_recall(local_contents, keywords)

        if abs(ask_recall - local_recall) < 0.01:
            same_count += 1
        elif ask_recall > local_recall:
            ask_better += 1
        else:
            local_better += 1

    total_q = len(EVAL_QUESTIONS)
    print(f"Same results:      {same_count:2d}/{total_q} questions ({same_count / total_q:.0%})")
    print(f"ask() better:      {ask_better:2d}/{total_q} questions")
    print(f"ask_local() better: {local_better:2d}/{total_q} questions")

    ask_overall_f1 = hive_metrics["overall"][2]
    local_overall_f1 = hive_local_metrics["overall"][2]
    print(f"\nask() overall F1:       {ask_overall_f1:.1%}")
    print(f"ask_local() overall F1: {local_overall_f1:.1%}")
    print(f"Query layer delta:      {(ask_overall_f1 - local_overall_f1) * 100:+.1f}pp")

    if same_count == total_q:
        print("\nVerdict: ask() and ask_local() return identical results.")
        print("  Event propagation did all the work; the hive query layer adds nothing.")
    elif ask_better > local_better:
        print(f"\nVerdict: ask() outperforms ask_local() on {ask_better} questions.")
        print("  The hive query layer (hive+gossip search) provides additional value.")
    else:
        print(
            f"\nVerdict: ask_local() matches or beats ask() on {same_count + local_better} questions."
        )
        print("  The hive query layer may add noise rather than value.")

    # ==================================================================
    # ADVERSARIAL RESILIENCE
    # ==================================================================
    print("\n" + "=" * 74)
    print("--- ADVERSARIAL RESILIENCE ---")
    print("=" * 74)
    print("Adversarial agent: 10 correct + 5 WRONG facts")

    adv_agents, adv_hive = _setup_hive_with_adversary()

    # Check whether wrong facts propagated to other agents
    wrong_propagated = 0
    for wrong_content, _conf, _tags, reason in ADVERSARIAL_FACTS:
        wrong_lower = wrong_content.lower()
        # Check if any standard agent retrieves this wrong fact
        found_in_standard = False
        for agent_id in AGENT_DOMAINS:
            # Search with a broad query related to the wrong fact
            results = adv_agents[agent_id].ask(wrong_content[:40], limit=20)
            for r in results:
                if r["content"].lower() == wrong_lower:
                    found_in_standard = True
                    break
            if found_in_standard:
                break
        if found_in_standard:
            wrong_propagated += 1
            print(f"  PROPAGATED: {wrong_content[:60]}...")
            print(f"              ({reason})")
        else:
            print(f"  BLOCKED:    {wrong_content[:60]}...")

    # Check if correct answers got corrupted by wrong facts
    corrupted = 0
    for i, (question, correct_keywords) in enumerate(ADVERSARIAL_CORRECT_KEYWORDS):
        # Pick a relevant standard agent to ask
        # Use a rotating agent for variety
        agent_ids = list(AGENT_DOMAINS.keys())
        agent_id = agent_ids[i % len(agent_ids)]
        results = adv_agents[agent_id].ask(question, limit=15)
        contents = [r["content"] for r in results]
        combined = " ".join(contents).lower()

        # Check if any wrong fact appears in the results
        wrong_content = ADVERSARIAL_FACTS[i][0].lower()
        has_wrong = any(wrong_content == c.lower() for c in contents)

        # Check if correct keywords are still present
        has_correct = any(kw.lower() in combined for kw in correct_keywords)

        if has_wrong and not has_correct:
            corrupted += 1
            print(f"  CORRUPTED: Q='{question[:50]}...' -- wrong fact present, correct absent")
        elif has_wrong:
            print(
                f"  MIXED:     Q='{question[:50]}...' -- wrong fact present but correct also found"
            )

    total_wrong = len(ADVERSARIAL_FACTS)
    total_questions_check = len(ADVERSARIAL_CORRECT_KEYWORDS)
    resilience = 1.0 - (corrupted / total_questions_check) if total_questions_check > 0 else 1.0

    print(f"\nWrong facts propagated: {wrong_propagated}/{total_wrong}")
    print(f"Correct answers corrupted: {corrupted}/{total_questions_check}")
    print(f"Resilience score: {resilience:.0%}")

    # ==================================================================
    # PRECISION UNDER NOISE
    # ==================================================================
    print("\n" + "=" * 74)
    print("--- PRECISION UNDER NOISE ---")
    print("=" * 74)
    print("Adding 10 distractor facts per agent (50 irrelevant facts total)")

    noisy_agents, noisy_hive = _setup_hive_with_distractors()
    noisy_results = _evaluate_condition(noisy_agents, use_ask=True)
    noisy_metrics = _avg_metrics(noisy_results)

    clean_precision = hive_metrics["overall"][1]
    noisy_precision = noisy_metrics["overall"][1]
    precision_drop = (noisy_precision - clean_precision) * 100

    clean_recall = hive_metrics["overall"][0]
    noisy_recall = noisy_metrics["overall"][0]
    recall_drop = (noisy_recall - clean_recall) * 100

    print(f"Without distractors: {clean_precision:.1%} precision, {clean_recall:.1%} recall")
    print(f"With distractors:    {noisy_precision:.1%} precision, {noisy_recall:.1%} recall")
    print(f"Precision drop:      {precision_drop:+.1f}pp")
    print(f"Recall drop:         {recall_drop:+.1f}pp")

    if precision_drop < -5:
        print("WARNING: Significant precision degradation under noise")
    elif precision_drop < -1:
        print("Minor precision impact from distractor facts")
    else:
        print("Hive maintains precision under noise")

    # ==================================================================
    # PER-QUESTION DETAIL
    # ==================================================================
    print("\n" + "=" * 74)
    print("--- PER-QUESTION DETAIL (all 4 conditions) ---")
    print("=" * 74)
    print(
        f"{'#':>3s} {'Cat':6s} {'Agent':12s} {'Question':40s} "
        f"{'ISO':>5s} {'FLAT':>5s} {'GOS':>5s} {'HIVE':>5s}"
    )
    print("-" * 80)

    for i, (agent_id, question, keywords, category) in enumerate(EVAL_QUESTIONS, 1):
        tag = category[:6].upper()

        # ISOLATED
        iso_r = iso_agents[agent_id].ask_local(question, limit=15)
        iso_score = score_recall([r["content"] for r in iso_r], keywords)

        # FLAT_SHARED
        flat_r = flat_agents[agent_id].ask_local(question, limit=15)
        flat_score = score_recall([r["content"] for r in flat_r], keywords)

        # GOSSIP_ONLY
        gos_r = gossip_agents[agent_id].ask(question, limit=15)
        gos_score = score_recall([r["content"] for r in gos_r], keywords)

        # HIVE
        hive_r = hive_agents[agent_id].ask(question, limit=15)
        hive_score = score_recall([r["content"] for r in hive_r], keywords)

        print(
            f"{i:3d} {tag:6s} {agent_id[:12]:12s} {question[:40]:40s} "
            f"{iso_score:>4.0%} {flat_score:>5.0%} {gos_score:>5.0%} {hive_score:>4.0%}"
        )

    # ==================================================================
    # TIMING
    # ==================================================================
    total_elapsed = time.perf_counter() - t0
    print("\n--- Timing ---")
    print(f"Baseline conditions: {elapsed_baseline:.1f}s")
    print(f"Total evaluation:    {total_elapsed:.1f}s")

    # ==================================================================
    # HONEST SUMMARY
    # ==================================================================
    print("\n" + "=" * 74)
    print("--- HONEST SUMMARY ---")
    print("=" * 74)

    iso_f1 = iso_metrics["overall"][2]

    print(f"ISOLATED    F1: {iso_f1:.1%}")
    print(f"FLAT_SHARED F1: {flat_f1:.1%}  (delta vs isolated: {(flat_f1 - iso_f1) * 100:+.1f}pp)")
    print(
        f"GOSSIP_ONLY F1: {gossip_metrics['overall'][2]:.1%}  "
        f"(delta vs isolated: {(gossip_metrics['overall'][2] - iso_f1) * 100:+.1f}pp)"
    )
    print(f"HIVE        F1: {hive_f1:.1%}  (delta vs isolated: {(hive_f1 - iso_f1) * 100:+.1f}pp)")
    print()
    print("Key question: Does HIVE beat FLAT_SHARED?")
    print(f"  F1 delta: {delta_pp:+.1f}pp")

    if delta_pp > 5:
        print("  Answer: YES -- the hive architecture provides meaningful value")
        print("  beyond simple data sharing.")
    elif delta_pp > 0:
        print("  Answer: MARGINAL -- hive provides slight improvement over flat sharing.")
        print("  The architecture may not justify its complexity.")
    elif abs(delta_pp) < 1:
        print("  Answer: NO -- hive and flat sharing perform identically.")
        print("  The promotion/gossip/event machinery adds no measurable value.")
    else:
        print("  Answer: NEGATIVE -- hive performs WORSE than simple flat sharing.")
        print("  The architecture adds complexity that hurts performance.")

    print(f"\nAdversarial resilience: {resilience:.0%}")
    if wrong_propagated > 0:
        print(f"  {wrong_propagated}/{total_wrong} wrong facts propagated through the hive.")
        if corrupted > 0:
            print(f"  {corrupted} correct answers were corrupted.")
        else:
            print("  But correct answers were not corrupted (wrong facts get outranked).")
    else:
        print("  No wrong facts propagated to standard agents.")

    print(f"\nPrecision under noise: {precision_drop:+.1f}pp drop with 50 distractors")

    print("\n" + "=" * 74)

    return {
        "conditions": {
            "isolated": {
                k: {"recall": v[0], "precision": v[1], "f1": v[2]} for k, v in iso_metrics.items()
            },
            "flat_shared": {
                k: {"recall": v[0], "precision": v[1], "f1": v[2]} for k, v in flat_metrics.items()
            },
            "gossip_only": {
                k: {"recall": v[0], "precision": v[1], "f1": v[2]}
                for k, v in gossip_metrics.items()
            },
            "hive": {
                k: {"recall": v[0], "precision": v[1], "f1": v[2]} for k, v in hive_metrics.items()
            },
        },
        "hive_vs_flat_f1_delta_pp": delta_pp,
        "hive_vs_flat_recall_delta_pp": delta_recall_pp,
        "ask_vs_local": {
            "same": same_count,
            "ask_better": ask_better,
            "local_better": local_better,
        },
        "adversarial": {
            "wrong_propagated": wrong_propagated,
            "corrupted": corrupted,
            "resilience": resilience,
        },
        "noise": {
            "clean_precision": clean_precision,
            "noisy_precision": noisy_precision,
            "precision_drop_pp": precision_drop,
        },
    }


if __name__ == "__main__":
    results = run_rigorous_evaluation()
    sys.exit(0)
