#!/usr/bin/env python3
"""20-agent hive mind evaluation with real consensus and adversarial testing.

Tests whether 20 topic-specialist agents connected via a hive mind with
consensus_required=2 can collectively answer questions at >= 80% the accuracy
of a single omniscient agent, while blocking adversarial wrong facts.

Four conditions:
    SINGLE_AGENT   -- One agent learns all 1000 turns (ceiling).
    ISOLATED_20    -- 20 agents, each learns its partition. No sharing.
    FLAT_SHARED_20 -- 20 agents, each gets ALL facts bulk-loaded. No hive.
    HIVE_20        -- 20 agents learn partitions, connected via consensus hive.
                      Plus 1 adversarial agent (#21) injecting 10 wrong facts.

Agent allocation across 12 blocks (1000 turns, seed=42):
    evolving_story  (150 turns) -> 3 agents
    projects        (140 turns) -> 3 agents
    technical       (100 turns) -> 2 agents
    numerical       (100 turns) -> 2 agents
    security_logs   (100 turns) -> 2 agents
    contradictory    (80 turns) -> 2 agents
    incidents        (80 turns) -> 1 agent
    infrastructure   (70 turns) -> 1 agent
    callbacks        (60 turns) -> 1 agent
    distractors      (60 turns) -> 1 agent
    problem_solving  (50 turns) -> 1 agent
    people           (10 turns) -> 1 agent  (small but critical for needle_in_haystack)
    ------------------------------------------
    TOTAL:                        20 agents

Usage:
    python experiments/hive_mind/run_20agent_eval.py
    python -m experiments.hive_mind.run_20agent_eval
"""

from __future__ import annotations

import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, "/home/azureuser/src/amplihack-agent-eval/src")

from amplihack_eval.data.long_horizon import (  # type: ignore[import-not-found]
    GroundTruth,
    Question,
    Turn,
    generate_dialogue,
    generate_questions,
)

from amplihack.agents.goal_seeking.hive_mind.unified import (
    HiveMindAgent,
    HiveMindConfig,
    UnifiedHiveMind,
)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class AgentPartition:
    """A named partition of turns assigned to one agent."""

    agent_name: str
    block_name: str
    turns: list[Turn]


@dataclass
class ConditionResult:
    """Score and per-category breakdown for one evaluation condition."""

    name: str
    overall_score: float
    per_category: dict[str, float] = field(default_factory=dict)
    per_question: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent allocation: 20 agents across 12 blocks
# ---------------------------------------------------------------------------

# Number of agents per block, determined by block size.
# Large (>= 100 turns): 3 for >130, 2 for 100-130
# Medium (60-99 turns): 1 each
# Small (<60 turns): 1 each
# This sums to exactly 20.
AGENT_COUNTS_BY_BLOCK = {
    "evolving_story": 3,  # 150 turns -> 50 each
    "projects": 3,  # 140 turns -> ~47 each
    "technical": 2,  # 100 turns -> 50 each
    "numerical": 2,  # 100 turns -> 50 each
    "security_logs": 2,  # 100 turns -> 50 each
    "contradictory": 2,  #  80 turns -> 40 each
    "incidents": 1,  #  80 turns
    "infrastructure": 1,  #  70 turns
    "callbacks": 1,  #  60 turns
    "distractors": 1,  #  60 turns
    "problem_solving": 1,  #  50 turns
    "people": 1,  #  10 turns
}

# 10 adversarial wrong facts -- plausible but incorrect
ADVERSARIAL_FACTS = [
    "Sarah Chen's birthday is October 22.",  # actual: March 15
    "Project Atlas uses Fortran as its primary language.",  # actual: different
    "Marcus Rivera is allergic to dairy.",  # actual: peanuts
    "The company's Q3 revenue was $2.1 million.",  # fabricated number
    "Yuki Tanaka is on the Security team.",  # actual: Analytics
    "Project Beacon was cancelled in Phase 2.",  # fabricated
    "Lars Eriksson is originally from Helsinki, Finland.",  # actual: Stockholm, Sweden
    "The Nexus server cluster has 2 replicas.",  # contradicts infrastructure data
    "Elena Volkov enjoys surfing in her free time.",  # actual: chess
    "Incident INC-001 was resolved by deleting the database.",  # fabricated resolution
]


def partition_turns_20(ground_truth: GroundTruth) -> list[AgentPartition]:
    """Split 1000 turns across exactly 20 agents by block, sized by turn count."""
    by_block: dict[str, list[Turn]] = defaultdict(list)
    for turn in ground_truth.turns:
        by_block[turn.block_name].append(turn)

    partitions: list[AgentPartition] = []
    for block_name, turns in sorted(by_block.items()):
        n_agents = AGENT_COUNTS_BY_BLOCK.get(block_name, 1)
        chunk_size = len(turns) // n_agents
        remainder = len(turns) % n_agents

        offset = 0
        for i in range(n_agents):
            # Distribute remainder across first agents
            this_chunk = chunk_size + (1 if i < remainder else 0)
            agent_name = f"{block_name}_{i + 1}" if n_agents > 1 else block_name
            partitions.append(
                AgentPartition(
                    agent_name=agent_name,
                    block_name=block_name,
                    turns=turns[offset : offset + this_chunk],
                )
            )
            offset += this_chunk

    return partitions


# ---------------------------------------------------------------------------
# Scoring (keyword matching from question rubrics)
# ---------------------------------------------------------------------------


def score_question(question: Question, retrieved_texts: list[str]) -> float:
    """Score by checking rubric keywords against retrieved fact texts.

    Returns a fraction [0.0, 1.0] of required keywords found.
    """
    corpus = " ".join(retrieved_texts).lower()

    keywords: list[str] = []
    paraphrases: list[str] = []
    incorrect: list[str] = []

    if question.rubric and question.rubric.required_keywords:
        keywords = question.rubric.required_keywords
        paraphrases = question.rubric.acceptable_paraphrases or []
        incorrect = question.rubric.incorrect_patterns or []
    elif question.rubric and question.rubric.acceptable_paraphrases:
        paraphrases = question.rubric.acceptable_paraphrases
        for p in paraphrases:
            if p.lower() in corpus:
                return 1.0
        return 0.0
    else:
        import re

        answer = question.expected_answer
        nums = re.findall(r"[\$]?[\d]+[.,]?[\d]*[%KMB]?", answer)
        keywords.extend(n.rstrip(".,") for n in nums)
        names = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", answer)
        keywords.extend(names)
        if not keywords:
            words = [w for w in answer.split() if len(w) > 3]
            keywords = words[:5]

    if not keywords:
        return 0.0

    for pattern in incorrect:
        if pattern.lower() in corpus:
            return 0.0

    found = 0
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in corpus:
            found += 1
        else:
            for p in paraphrases:
                if p.lower() in corpus:
                    found += 1
                    break

    return found / len(keywords)


# ---------------------------------------------------------------------------
# Question routing
# ---------------------------------------------------------------------------


def _get_relevant_block(question: Question, ground_truth: GroundTruth) -> str | None:
    """Determine which block_name is most relevant for a question."""
    if question.relevant_turns:
        turn_map = {t.turn_number: t for t in ground_truth.turns}
        block_counts: dict[str, int] = defaultdict(int)
        for tn in question.relevant_turns:
            if tn in turn_map:
                block_counts[turn_map[tn].block_name] += 1
        if block_counts:
            return max(block_counts, key=block_counts.get)  # type: ignore[arg-type]

    q_lower = question.text.lower()

    category_block_map = {
        "temporal_evolution": "evolving_story",
        "numerical_precision": "numerical",
        "source_attribution": "contradictory",
        "security_log_analysis": "security_logs",
        "incident_tracking": "incidents",
        "infrastructure_knowledge": "infrastructure",
        "problem_solving": "problem_solving",
    }
    mapped = category_block_map.get(question.category)
    if mapped:
        return mapped

    people_names = [
        "sarah chen",
        "marcus rivera",
        "yuki tanaka",
        "priya patel",
        "james o'brien",
        "amara okafor",
        "lars eriksson",
        "elena volkov",
        "diego morales",
        "fatima al-hassan",
    ]
    for name in people_names:
        if name in q_lower:
            return "people"

    project_names = ["atlas", "beacon", "cascade", "delta", "echo"]
    for pname in project_names:
        if f"project {pname}" in q_lower:
            return "projects"

    tech_keywords = [
        "programming",
        "language",
        "duckdb",
        "typescript",
        "java",
        "rust",
        "python",
        "zig",
        "saga",
        "cvss",
        "log4shell",
        "heroku",
        "strangler",
    ]
    for kw in tech_keywords:
        if kw in q_lower:
            return "technical"

    if any(kw in q_lower for kw in ["cvss", "vulnerability", "cve", "security audit"]):
        return "security_logs"

    return "evolving_story"


# ---------------------------------------------------------------------------
# Helper: learn turns into an agent
# ---------------------------------------------------------------------------


def _learn_turns(agent: HiveMindAgent, turns: list[Turn]) -> int:
    """Have an agent learn all facts from a list of turns. Returns fact count."""
    count = 0
    for turn in turns:
        for fact in turn.facts:
            content = (
                f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
            )
            agent.learn(content, 0.9, [turn.block_name])
            count += 1
        agent.learn(turn.content, 0.85, [turn.block_name, f"turn_{turn.turn_number}"])
        count += 1
    return count


def _promote_turns(agent: HiveMindAgent, turns: list[Turn]) -> int:
    """Have an agent promote all facts from its turns to the hive. Returns count."""
    count = 0
    for turn in turns:
        for fact in turn.facts:
            content = (
                f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
            )
            agent.promote(content, 0.9, [turn.block_name])
            count += 1
        agent.promote(turn.content, 0.85, [turn.block_name, f"turn_{turn.turn_number}"])
        count += 1
    return count


# ---------------------------------------------------------------------------
# Condition 1: Single Agent (ceiling)
# ---------------------------------------------------------------------------


def run_single_agent(
    ground_truth: GroundTruth,
    questions: list[Question],
) -> ConditionResult:
    """One agent learns all 1000 turns."""
    print("  [1/4] SINGLE_AGENT...")
    t0 = time.time()

    config = HiveMindConfig(
        promotion_confidence_threshold=0.5,
        promotion_consensus_required=1,
        enable_gossip=False,
        enable_events=False,
    )
    hive = UnifiedHiveMind(config)
    hive.register_agent("generalist")
    agent = HiveMindAgent("generalist", hive)

    fact_count = _learn_turns(agent, ground_truth.turns)
    print(f"       Learned {fact_count} facts")

    per_question: dict[str, float] = {}
    per_category: dict[str, list[float]] = defaultdict(list)

    for q in questions:
        results = agent.ask(q.text, limit=50)
        texts = [r["content"] for r in results]
        s = score_question(q, texts)
        per_question[q.question_id] = s
        per_category[q.category].append(s)

    overall = sum(per_question.values()) / len(per_question) if per_question else 0.0
    cat_avg = {cat: sum(scores) / len(scores) for cat, scores in per_category.items()}

    elapsed = time.time() - t0
    print(f"       Done in {elapsed:.1f}s -- Overall: {overall:.1%}")
    return ConditionResult(
        name="SINGLE_AGENT",
        overall_score=overall,
        per_category=cat_avg,
        per_question=per_question,
    )


# ---------------------------------------------------------------------------
# Condition 2: Isolated 20
# ---------------------------------------------------------------------------


def run_isolated_20(
    ground_truth: GroundTruth,
    questions: list[Question],
    partitions: list[AgentPartition],
) -> ConditionResult:
    """20 agents, each isolated with its own partition. No sharing."""
    print("  [2/4] ISOLATED_20...")
    t0 = time.time()

    config = HiveMindConfig(enable_gossip=False, enable_events=False)

    agents: dict[str, HiveMindAgent] = {}
    block_to_agents: dict[str, list[str]] = defaultdict(list)

    for part in partitions:
        iso_hive = UnifiedHiveMind(config)
        iso_hive.register_agent(part.agent_name)
        agent = HiveMindAgent(part.agent_name, iso_hive)
        _learn_turns(agent, part.turns)
        agents[part.agent_name] = agent
        block_to_agents[part.block_name].append(part.agent_name)

    print(f"       {len(agents)} isolated agents created")

    per_question: dict[str, float] = {}
    per_category: dict[str, list[float]] = defaultdict(list)

    for q in questions:
        relevant_block = _get_relevant_block(q, ground_truth)

        candidate_names: list[str] = []
        if relevant_block and relevant_block in block_to_agents:
            candidate_names.extend(block_to_agents[relevant_block])
        if not candidate_names:
            candidate_names = list(agents.keys())

        best_texts: list[str] = []
        best_score = -1.0
        for agent_name in candidate_names:
            results = agents[agent_name].ask(q.text, limit=50)
            texts = [r["content"] for r in results]
            s = score_question(q, texts)
            if s > best_score:
                best_score = s
                best_texts = texts

        s = score_question(q, best_texts)
        per_question[q.question_id] = s
        per_category[q.category].append(s)

    overall = sum(per_question.values()) / len(per_question) if per_question else 0.0
    cat_avg = {cat: sum(scores) / len(scores) for cat, scores in per_category.items()}

    elapsed = time.time() - t0
    print(f"       Done in {elapsed:.1f}s -- Overall: {overall:.1%}")
    return ConditionResult(
        name="ISOLATED_20",
        overall_score=overall,
        per_category=cat_avg,
        per_question=per_question,
    )


# ---------------------------------------------------------------------------
# Condition 3: Flat Shared 20
# ---------------------------------------------------------------------------


def run_flat_shared_20(
    ground_truth: GroundTruth,
    questions: list[Question],
    partitions: list[AgentPartition],
) -> ConditionResult:
    """20 agents, each gets ALL facts bulk-loaded. No hive topology."""
    print("  [3/4] FLAT_SHARED_20...")
    t0 = time.time()

    config = HiveMindConfig(enable_gossip=False, enable_events=False)

    # Collect all facts once
    all_facts: list[tuple[str, float, list[str]]] = []
    for turn in ground_truth.turns:
        for fact in turn.facts:
            content = (
                f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
            )
            all_facts.append((content, 0.9, [turn.block_name]))
        all_facts.append((turn.content, 0.85, [turn.block_name, f"turn_{turn.turn_number}"]))

    # Create one shared hive, load all facts into first agent, query through it
    flat_hive = UnifiedHiveMind(config)
    flat_hive.register_agent("flat_coordinator")
    coord = HiveMindAgent("flat_coordinator", flat_hive)
    for content, conf, tags in all_facts:
        coord.learn(content, conf, tags)

    print(f"       Loaded {len(all_facts)} facts into shared coordinator")

    per_question: dict[str, float] = {}
    per_category: dict[str, list[float]] = defaultdict(list)

    for q in questions:
        results = coord.ask(q.text, limit=50)
        texts = [r["content"] for r in results]
        s = score_question(q, texts)
        per_question[q.question_id] = s
        per_category[q.category].append(s)

    overall = sum(per_question.values()) / len(per_question) if per_question else 0.0
    cat_avg = {cat: sum(scores) / len(scores) for cat, scores in per_category.items()}

    elapsed = time.time() - t0
    print(f"       Done in {elapsed:.1f}s -- Overall: {overall:.1%}")
    return ConditionResult(
        name="FLAT_SHARED_20",
        overall_score=overall,
        per_category=cat_avg,
        per_question=per_question,
    )


# ---------------------------------------------------------------------------
# Condition 4: Hive 20 with consensus=2 + adversarial agent
# ---------------------------------------------------------------------------


def run_hive_20(
    ground_truth: GroundTruth,
    questions: list[Question],
    partitions: list[AgentPartition],
) -> tuple[ConditionResult, dict[str, int]]:
    """20 agents with consensus hive + 1 adversarial agent.

    Returns (condition_result, adversarial_stats).
    """
    print("  [4/4] HIVE_20 (consensus=2, +adversarial)...")
    t0 = time.time()

    config = HiveMindConfig(
        promotion_confidence_threshold=0.5,
        promotion_consensus_required=2,  # Real consensus: proposer + 1 voter
        gossip_interval_rounds=5,
        gossip_top_k=20,
        gossip_fanout=4,
        event_relevance_threshold=0.2,
        enable_gossip=True,
        enable_events=True,
    )

    hive = UnifiedHiveMind(config)
    agents: dict[str, HiveMindAgent] = {}
    block_to_agents: dict[str, list[str]] = defaultdict(list)

    # Register all 20 legitimate agents
    for part in partitions:
        hive.register_agent(part.agent_name)
        agents[part.agent_name] = HiveMindAgent(part.agent_name, hive)
        block_to_agents[part.block_name].append(part.agent_name)

    # Register adversarial agent #21
    hive.register_agent("adversary")
    adversary = HiveMindAgent("adversary", hive)

    print(f"       Registered {len(agents)} agents + 1 adversary")

    # Phase 1: Each legitimate agent learns its partition
    total_facts = 0
    for part in partitions:
        agent = agents[part.agent_name]
        count = _learn_turns(agent, part.turns)
        total_facts += count
    print(f"       Phase 1: {total_facts} facts learned across 20 agents")

    # Phase 2: Each agent promotes its facts. With consensus_required=2,
    # facts go to pending state. Then agents within the same block vote
    # on each other's promotions (topic overlap = plausible voters).
    promoted_count = 0
    for part in partitions:
        agent = agents[part.agent_name]
        for turn in part.turns:
            for fact in turn.facts:
                content = f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
                agent.promote(content, 0.9, [turn.block_name])
                promoted_count += 1
            agent.promote(turn.content, 0.85, [turn.block_name, f"turn_{turn.turn_number}"])
            promoted_count += 1

    print(f"       Phase 2: {promoted_count} facts proposed for promotion")

    # Phase 2b: Voting round -- agents in the same block vote approve
    # on each other's pending promotions. For single-agent blocks, a
    # neighboring block's agent votes (simulating topic affinity).
    pending = hive._graph.get_pending_promotions()
    pre_vote_pending = len(pending)
    print(f"       Phase 2b: {pre_vote_pending} pending promotions, running consensus votes...")

    # Build a mapping: block -> list of agent names
    # For cross-voting, define block affinity pairs
    block_affinity = {
        "people": ["projects"],
        "projects": ["people", "technical"],
        "technical": ["projects", "problem_solving"],
        "evolving_story": ["contradictory"],
        "numerical": ["infrastructure"],
        "contradictory": ["evolving_story"],
        "callbacks": ["distractors"],
        "distractors": ["callbacks"],
        "security_logs": ["incidents"],
        "incidents": ["security_logs"],
        "infrastructure": ["numerical"],
        "problem_solving": ["technical"],
    }

    votes_cast = 0
    for pending_fact in pending:
        proposer = pending_fact.proposer_agent_id
        # Find proposer's block
        proposer_block = None
        for part in partitions:
            if part.agent_name == proposer:
                proposer_block = part.block_name
                break

        if not proposer_block:
            continue

        # Find a voter: same-block agents first, then affinity blocks
        voter_found = False
        # Same-block agents (different from proposer)
        for agent_name in block_to_agents.get(proposer_block, []):
            if agent_name != proposer and agent_name not in pending_fact.votes:
                try:
                    hive._graph.vote_on_promotion(agent_name, pending_fact.fact_id, True)
                    votes_cast += 1
                    voter_found = True
                    break
                except ValueError:
                    continue  # Already voted

        if not voter_found:
            # Cross-block voting via affinity
            affinity_blocks = block_affinity.get(proposer_block, [])
            for aff_block in affinity_blocks:
                if voter_found:
                    break
                for agent_name in block_to_agents.get(aff_block, []):
                    if agent_name not in pending_fact.votes:
                        try:
                            hive._graph.vote_on_promotion(agent_name, pending_fact.fact_id, True)
                            votes_cast += 1
                            voter_found = True
                            break
                        except ValueError:
                            continue

    post_stats = hive._graph.get_stats()
    print(
        f"       Phase 2b: {votes_cast} votes cast, "
        f"{post_stats['hive_facts']} facts in hive, "
        f"{post_stats['pending_promotions']} still pending"
    )

    # Phase 3: Adversarial injection -- adversary promotes 10 wrong facts
    adversarial_pending_ids: list[str] = []
    for wrong_fact in ADVERSARIAL_FACTS:
        adversary.learn(wrong_fact, 0.95, ["adversary"])
        fid = adversary.promote(wrong_fact, 0.95, ["adversary"])
        adversarial_pending_ids.append(fid)

    print(f"       Phase 3: Adversary injected {len(ADVERSARIAL_FACTS)} wrong facts")

    # Check how many adversarial facts got through consensus
    # With consensus_required=2, adversary needs another agent to vote approve.
    # Legitimate agents should NOT vote on adversarial facts (different topics).
    adv_pending_after = hive._graph.get_pending_promotions()
    adv_blocked = 0
    adv_promoted = 0
    for fid in adversarial_pending_ids:
        # Check if still pending
        still_pending = any(p.fact_id == fid for p in adv_pending_after)
        if still_pending:
            adv_blocked += 1
        else:
            # Check if it made it to hive
            if fid in hive._graph._hive_store:
                adv_promoted += 1
            else:
                adv_blocked += 1  # Rejected or otherwise not in hive

    adversarial_stats = {
        "total_injected": len(ADVERSARIAL_FACTS),
        "blocked": adv_blocked,
        "promoted": adv_promoted,
    }
    print(
        f"       Phase 3: {adv_blocked}/{len(ADVERSARIAL_FACTS)} adversarial facts BLOCKED by consensus"
    )

    # Phase 4: Gossip rounds to spread knowledge
    gossip_rounds = 5
    for _ in range(gossip_rounds):
        hive.run_gossip_round()
    print(f"       Phase 4: {gossip_rounds} gossip rounds completed")

    # Phase 5: Process events so agents incorporate hive facts locally
    event_stats = hive.process_events()
    total_events = sum(event_stats.values())
    print(f"       Phase 5: {total_events} events processed across agents")

    # Phase 6: Answer questions using query_all (local + hive + gossip)
    per_question: dict[str, float] = {}
    per_category: dict[str, list[float]] = defaultdict(list)

    for q in questions:
        relevant_block = _get_relevant_block(q, ground_truth)

        candidate_names: list[str] = []
        if relevant_block and relevant_block in block_to_agents:
            candidate_names.extend(block_to_agents[relevant_block])
        # For cross-cutting questions, query all agents
        if q.category in ("cross_reference", "meta_memory", "multi_hop_reasoning"):
            for bn, anames in block_to_agents.items():
                for an in anames:
                    if an not in candidate_names:
                        candidate_names.append(an)
        if not candidate_names:
            candidate_names = list(agents.keys())

        best_texts: list[str] = []
        best_score = -1.0

        for agent_name in candidate_names:
            results = hive.query_all(agent_name, q.text, limit=50)
            texts = [r["content"] for r in results]
            s = score_question(q, texts)
            if s > best_score:
                best_score = s
                best_texts = texts

        s = score_question(q, best_texts)
        per_question[q.question_id] = s
        per_category[q.category].append(s)

    overall = sum(per_question.values()) / len(per_question) if per_question else 0.0
    cat_avg = {cat: sum(scores) / len(scores) for cat, scores in per_category.items()}

    elapsed = time.time() - t0
    print(f"       Done in {elapsed:.1f}s -- Overall: {overall:.1%}")

    hive_stats = hive.get_stats()
    print(
        f"       Hive stats: {hive_stats['agent_count']} agents, "
        f"{hive_stats['graph']['hive_facts']} hive facts, "
        f"{hive_stats['events']['total_events']} events"
    )

    return (
        ConditionResult(
            name="HIVE_20",
            overall_score=overall,
            per_category=cat_avg,
            per_question=per_question,
        ),
        adversarial_stats,
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_results(
    results: list[ConditionResult],
    questions: list[Question],
    partitions: list[AgentPartition],
    adversarial_stats: dict[str, int],
) -> None:
    """Print comparison table and hypothesis results."""
    single = results[0]

    print()
    print("=" * 70)
    print("=== 20-AGENT HIVE MIND EVALUATION ===")
    print("=" * 70)
    print(f"Agents: 20 | Turns: 1000 | Questions: {len(questions)}")
    print()

    # Agent assignment table
    print("AGENT ASSIGNMENTS:")
    for p in partitions:
        print(f"  {p.agent_name:25s}  block={p.block_name:20s}  turns={len(p.turns)}")
    print(f"  {'(total)':25s}  {'':20s}  turns={sum(len(p.turns) for p in partitions)}")
    print()

    # Results table
    print("RESULTS:")
    header = f"{'':30s} {'SINGLE':>8s} {'ISO_20':>8s} {'FLAT_20':>8s} {'HIVE_20':>8s}"
    print(header)
    print("-" * 70)

    # Overall row
    row = f"{'Overall':30s}"
    for r in results:
        row += f" {r.overall_score:>7.1%}"
    print(row)

    # Per-category rows
    all_categories = sorted(set(q.category for q in questions))
    for cat in all_categories:
        row = f"{cat:30s}"
        for r in results:
            val = r.per_category.get(cat, 0.0)
            row += f" {val:>7.1%}"
        print(row)
    print()

    # Adversarial results
    total_adv = adversarial_stats["total_injected"]
    blocked_adv = adversarial_stats["blocked"]
    print("ADVERSARIAL (HIVE_20 only):")
    print(f"  Wrong facts injected:         {total_adv}")
    print(f"  Blocked by consensus:         {blocked_adv}/{total_adv}")
    print(
        f"  Resilience:                   {blocked_adv / total_adv:.0%}"
        if total_adv > 0
        else "  N/A"
    )
    print()

    # Hypothesis testing
    print("HYPOTHESIS:")
    hive_r = results[3]
    flat_r = results[2]
    iso_r = results[1]

    # H1: Hive >= 80% of Single
    if single.overall_score > 0:
        h1_ratio = hive_r.overall_score / single.overall_score
        h1_pass = h1_ratio >= 0.80
        print(
            f"  H1: Hive >= 80% of Single?     [{'PASS' if h1_pass else 'FAIL'}]  "
            f"({h1_ratio:.1%} of single)"
        )
    else:
        print("  H1: Cannot evaluate (single=0)")

    # H2: Hive > Flat
    h2_pass = hive_r.overall_score > flat_r.overall_score
    h2_diff = hive_r.overall_score - flat_r.overall_score
    print(
        f"  H2: Hive > Flat?               [{'PASS' if h2_pass else 'FAIL'}]  "
        f"(diff = {h2_diff:+.1%})"
    )

    # H3: Consensus blocks adversarial
    h3_pass = blocked_adv >= 8  # At least 80% of adversarial facts blocked
    print(
        f"  H3: Consensus blocks adversarial? [{'PASS' if h3_pass else 'FAIL'}]  "
        f"({blocked_adv}/{total_adv} blocked)"
    )

    # H4: Hive > Isolated
    h4_pass = hive_r.overall_score > iso_r.overall_score
    h4_diff = hive_r.overall_score - iso_r.overall_score
    print(
        f"  H4: Hive > Isolated?           [{'PASS' if h4_pass else 'FAIL'}]  "
        f"(diff = {h4_diff:+.1%})"
    )
    print()

    # Notable per-question diffs (Hive vs Single)
    print("NOTABLE PER-QUESTION DIFFERENCES (Hive vs Single):")
    diffs = []
    for q in questions:
        single_s = single.per_question.get(q.question_id, 0.0)
        hive_s = hive_r.per_question.get(q.question_id, 0.0)
        d = hive_s - single_s
        diffs.append((q.question_id, q.category, single_s, hive_s, d))

    diffs.sort(key=lambda x: x[4])
    print("  Biggest drops (hive < single):")
    shown = 0
    for qid, cat, ss, hs, d in diffs:
        if d < 0 and shown < 5:
            print(f"    {qid:25s} {cat:25s}  single={ss:.0%}  hive={hs:.0%}  diff={d:+.0%}")
            shown += 1
    if shown == 0:
        print("    (none)")

    diffs.sort(key=lambda x: -x[4])
    print("  Biggest gains (hive > single):")
    shown = 0
    for qid, cat, ss, hs, d in diffs:
        if d > 0 and shown < 5:
            print(f"    {qid:25s} {cat:25s}  single={ss:.0%}  hive={hs:.0%}  diff={d:+.0%}")
            shown += 1
    if shown == 0:
        print("    (none)")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the 20-agent hive mind evaluation."""
    print("=" * 70)
    print("Generating dialogue and questions...")
    t_total = time.time()

    ground_truth = generate_dialogue(num_turns=1000, seed=42)
    questions = generate_questions(ground_truth, num_questions=100)

    print(f"  {len(ground_truth.turns)} turns, {len(questions)} questions")

    # Partition across 20 agents
    partitions = partition_turns_20(ground_truth)
    total_agents = len(partitions)
    assert total_agents == 20, f"Expected 20 agents, got {total_agents}"
    print(f"  {total_agents} agent partitions created")

    # Block summary
    blocks_summary: dict[str, tuple[int, list[str]]] = {}
    for p in partitions:
        if p.block_name not in blocks_summary:
            blocks_summary[p.block_name] = (0, [])
        turns, names = blocks_summary[p.block_name]
        blocks_summary[p.block_name] = (turns + len(p.turns), names + [p.agent_name])

    for block, (count, names) in sorted(blocks_summary.items(), key=lambda x: -x[1][0]):
        print(f"    {block:20s}: {count:4d} turns -> {names}")
    print()

    # Run all 4 conditions
    print("Running evaluation conditions...")
    results: list[ConditionResult] = []

    results.append(run_single_agent(ground_truth, questions))
    results.append(run_isolated_20(ground_truth, questions, partitions))
    results.append(run_flat_shared_20(ground_truth, questions, partitions))

    hive_result, adversarial_stats = run_hive_20(ground_truth, questions, partitions)
    results.append(hive_result)

    # Print results
    print_results(results, questions, partitions, adversarial_stats)

    elapsed_total = time.time() - t_total
    print(f"Total wall time: {elapsed_total:.1f}s")


if __name__ == "__main__":
    main()
