#!/usr/bin/env python3
"""Distributed learning eval: topic-specialist agents vs 1 generalist.

Tests whether a hive mind enables collective intelligence where specialists
who each know ~8% of the knowledge can collectively answer questions at
>= 80% the accuracy of a single agent that knows 100%.

Four conditions:
    SINGLE_AGENT   -- One agent learns all 1000 turns (ceiling).
    ISOLATED       -- N agents, each learns its block. No sharing.
    FLAT_SHARED    -- N agents, each gets ALL facts bulk-loaded. No hive.
    HIVE_COLLECTIVE -- N agents learn their blocks, connected via hive mind.

Usage:
    python -m experiments.hive_mind.run_distributed_eval
    python experiments/hive_mind/run_distributed_eval.py
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
# Partitioning
# ---------------------------------------------------------------------------


def partition_turns(
    ground_truth: GroundTruth, large_block_threshold: int = 100
) -> list[AgentPartition]:
    """Split turns by block_name. Large blocks get 2 agents."""
    by_block: dict[str, list[Turn]] = defaultdict(list)
    for turn in ground_truth.turns:
        by_block[turn.block_name].append(turn)

    partitions: list[AgentPartition] = []
    for block_name, turns in sorted(by_block.items()):
        if len(turns) > large_block_threshold:
            mid = len(turns) // 2
            partitions.append(
                AgentPartition(
                    agent_name=f"{block_name}_1",
                    block_name=block_name,
                    turns=turns[:mid],
                )
            )
            partitions.append(
                AgentPartition(
                    agent_name=f"{block_name}_2",
                    block_name=block_name,
                    turns=turns[mid:],
                )
            )
        else:
            partitions.append(
                AgentPartition(
                    agent_name=block_name,
                    block_name=block_name,
                    turns=turns,
                )
            )
    return partitions


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_question(question: Question, retrieved_texts: list[str]) -> float:
    """Score a question by checking rubric keywords against retrieved fact texts.

    Returns a fraction [0.0, 1.0] of required keywords found.
    Falls back to expected_answer keyword extraction when rubric is absent.
    """
    # Build a single searchable corpus from retrieved texts
    corpus = " ".join(retrieved_texts).lower()

    # Determine keywords to check
    keywords: list[str] = []
    paraphrases: list[str] = []
    incorrect: list[str] = []

    if question.rubric and question.rubric.required_keywords:
        keywords = question.rubric.required_keywords
        paraphrases = question.rubric.acceptable_paraphrases or []
        incorrect = question.rubric.incorrect_patterns or []
    elif question.rubric and question.rubric.acceptable_paraphrases:
        # No required_keywords but has paraphrases (e.g., distractor_03)
        paraphrases = question.rubric.acceptable_paraphrases
        # Score is 1.0 if any paraphrase found, 0.0 otherwise
        for p in paraphrases:
            if p.lower() in corpus:
                return 1.0
        return 0.0
    else:
        # Fallback: extract keywords from expected_answer
        import re

        answer = question.expected_answer
        nums = re.findall(r"[\$]?[\d]+[.,]?[\d]*[%KMB]?", answer)
        keywords.extend(n.rstrip(".,") for n in nums)
        names = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", answer)
        keywords.extend(names)
        if not keywords:
            # Last resort: split expected_answer into significant words
            words = [w for w in answer.split() if len(w) > 3]
            keywords = words[:5]

    if not keywords:
        return 0.0

    # Check for incorrect patterns first -- if any match, score 0
    for pattern in incorrect:
        if pattern.lower() in corpus:
            return 0.0

    # Count how many keywords are found (keyword or its paraphrase)
    found = 0
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in corpus:
            found += 1
        else:
            # Check paraphrases for this keyword
            for p in paraphrases:
                if p.lower() in corpus:
                    found += 1
                    break

    return found / len(keywords)


def _get_relevant_block_for_question(question: Question, ground_truth: GroundTruth) -> str | None:
    """Determine which block_name is most relevant for a question.

    Uses relevant_turns if available, otherwise does keyword matching.
    """
    # If relevant_turns are specified and non-empty, use those
    if question.relevant_turns:
        turn_map = {t.turn_number: t for t in ground_truth.turns}
        block_counts: dict[str, int] = defaultdict(int)
        for tn in question.relevant_turns:
            if tn in turn_map:
                block_counts[turn_map[tn].block_name] += 1
        if block_counts:
            return max(block_counts, key=block_counts.get)  # type: ignore[arg-type]

    # Keyword-based heuristic: match question text against block content
    q_lower = question.text.lower()

    # Category to block mapping (many questions clearly belong to a block)
    category_block_map = {
        "needle_in_haystack": None,  # could be any block
        "temporal_evolution": "evolving_story",
        "numerical_precision": "numerical",
        "source_attribution": "contradictory",
        "cross_reference": None,  # spans blocks
        "distractor_resistance": None,  # various
        "meta_memory": None,  # meta
        "security_log_analysis": "security_logs",
        "incident_tracking": "incidents",
        "infrastructure_knowledge": "infrastructure",
        "problem_solving": "problem_solving",
        "multi_hop_reasoning": None,  # spans blocks
    }

    # Try category-based mapping first
    mapped = category_block_map.get(question.category)
    if mapped:
        return mapped

    # For needle_in_haystack: detect by question content
    # People-related questions
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

    # Project-related questions
    project_names = ["atlas", "beacon", "cascade", "delta", "echo"]
    for pname in project_names:
        if f"project {pname}" in q_lower:
            return "projects"

    # Technical questions
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

    # Security
    if any(kw in q_lower for kw in ["cvss", "vulnerability", "cve", "security audit"]):
        return "security_logs"

    # Default: pick the block with the most turns (evolving_story)
    return "evolving_story"


# ---------------------------------------------------------------------------
# Evaluation conditions
# ---------------------------------------------------------------------------


def run_single_agent(
    ground_truth: GroundTruth,
    questions: list[Question],
) -> ConditionResult:
    """Condition 1: One agent learns all turns. The ceiling."""
    print("  Running SINGLE_AGENT condition...")
    t0 = time.time()

    config = HiveMindConfig(
        promotion_confidence_threshold=0.5,
        promotion_consensus_required=1,
        gossip_interval_rounds=50,  # infrequent for single agent
        enable_gossip=False,
        enable_events=False,
    )
    hive = UnifiedHiveMind(config)
    hive.register_agent("generalist")
    agent = HiveMindAgent("generalist", hive)

    # Learn all facts from all turns
    fact_count = 0
    for turn in ground_truth.turns:
        for fact in turn.facts:
            content = (
                f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
            )
            agent.learn(content, 0.9, [turn.block_name])
            fact_count += 1
        # Also store the raw turn content as a fact
        agent.learn(turn.content, 0.85, [turn.block_name, f"turn_{turn.turn_number}"])

    print(f"    Learned {fact_count} structured facts + {len(ground_truth.turns)} turn contents")

    # Answer questions
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
    print(f"    Done in {elapsed:.1f}s. Overall: {overall:.1%}")
    return ConditionResult(
        name="SINGLE_AGENT", overall_score=overall, per_category=cat_avg, per_question=per_question
    )


def run_isolated(
    ground_truth: GroundTruth,
    questions: list[Question],
    partitions: list[AgentPartition],
) -> ConditionResult:
    """Condition 2: N agents, each learns its block. No sharing."""
    print("  Running ISOLATED condition...")
    t0 = time.time()

    config = HiveMindConfig(
        enable_gossip=False,
        enable_events=False,
    )

    # Build one hive per agent (truly isolated)
    agents: dict[str, HiveMindAgent] = {}
    block_to_agents: dict[str, list[str]] = defaultdict(list)

    for part in partitions:
        hive = UnifiedHiveMind(config)
        hive.register_agent(part.agent_name)
        agent = HiveMindAgent(part.agent_name, hive)

        for turn in part.turns:
            for fact in turn.facts:
                content = f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
                agent.learn(content, 0.9, [turn.block_name])
            agent.learn(turn.content, 0.85, [turn.block_name, f"turn_{turn.turn_number}"])

        agents[part.agent_name] = agent
        block_to_agents[part.block_name].append(part.agent_name)

    print(f"    Created {len(agents)} isolated agents")

    # Answer questions -- route each to the most relevant agent
    per_question: dict[str, float] = {}
    per_category: dict[str, list[float]] = defaultdict(list)

    for q in questions:
        relevant_block = _get_relevant_block_for_question(q, ground_truth)

        # Find agents for that block
        candidate_agents = []
        if relevant_block and relevant_block in block_to_agents:
            candidate_agents = [agents[n] for n in block_to_agents[relevant_block]]
        if not candidate_agents:
            # Fallback: try all agents, pick best
            candidate_agents = list(agents.values())

        # Query each candidate, take the best results
        best_texts: list[str] = []
        best_score = -1.0
        for agent in candidate_agents:
            results = agent.ask(q.text, limit=50)
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
    print(f"    Done in {elapsed:.1f}s. Overall: {overall:.1%}")
    return ConditionResult(
        name="ISOLATED", overall_score=overall, per_category=cat_avg, per_question=per_question
    )


def run_flat_shared(
    ground_truth: GroundTruth,
    questions: list[Question],
    partitions: list[AgentPartition],
) -> ConditionResult:
    """Condition 3: N agents, each gets ALL facts. Flat sharing baseline."""
    print("  Running FLAT_SHARED condition...")
    t0 = time.time()

    config = HiveMindConfig(
        enable_gossip=False,
        enable_events=False,
    )

    # Collect all facts once
    all_facts: list[tuple[str, float, list[str]]] = []
    for turn in ground_truth.turns:
        for fact in turn.facts:
            content = (
                f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
            )
            all_facts.append((content, 0.9, [turn.block_name]))
        all_facts.append((turn.content, 0.85, [turn.block_name, f"turn_{turn.turn_number}"]))

    # Create N agents, each with ALL facts
    agents: dict[str, HiveMindAgent] = {}
    block_to_agents: dict[str, list[str]] = defaultdict(list)

    for part in partitions:
        hive = UnifiedHiveMind(config)
        hive.register_agent(part.agent_name)
        agent = HiveMindAgent(part.agent_name, hive)

        for content, confidence, tags in all_facts:
            agent.learn(content, confidence, tags)

        agents[part.agent_name] = agent
        block_to_agents[part.block_name].append(part.agent_name)

    print(f"    Created {len(agents)} agents, each with {len(all_facts)} facts")

    # Answer questions -- use any agent (they all have the same knowledge)
    # Use first agent for all questions
    coordinator = list(agents.values())[0]

    per_question: dict[str, float] = {}
    per_category: dict[str, list[float]] = defaultdict(list)

    for q in questions:
        results = coordinator.ask(q.text, limit=50)
        texts = [r["content"] for r in results]
        s = score_question(q, texts)
        per_question[q.question_id] = s
        per_category[q.category].append(s)

    overall = sum(per_question.values()) / len(per_question) if per_question else 0.0
    cat_avg = {cat: sum(scores) / len(scores) for cat, scores in per_category.items()}

    elapsed = time.time() - t0
    print(f"    Done in {elapsed:.1f}s. Overall: {overall:.1%}")
    return ConditionResult(
        name="FLAT_SHARED", overall_score=overall, per_category=cat_avg, per_question=per_question
    )


def run_hive_collective(
    ground_truth: GroundTruth,
    questions: list[Question],
    partitions: list[AgentPartition],
) -> ConditionResult:
    """Condition 4: N agents, each learns its block, connected via hive mind."""
    print("  Running HIVE_COLLECTIVE condition...")
    t0 = time.time()

    config = HiveMindConfig(
        promotion_confidence_threshold=0.5,
        promotion_consensus_required=1,
        gossip_interval_rounds=5,
        gossip_top_k=20,
        gossip_fanout=3,
        event_relevance_threshold=0.2,
        enable_gossip=True,
        enable_events=True,
    )

    hive = UnifiedHiveMind(config)
    agents: dict[str, HiveMindAgent] = {}
    block_to_agents: dict[str, list[str]] = defaultdict(list)

    # Register all agents first
    for part in partitions:
        hive.register_agent(part.agent_name)
        agents[part.agent_name] = HiveMindAgent(part.agent_name, hive)
        block_to_agents[part.block_name].append(part.agent_name)

    print(f"    Registered {len(agents)} agents in shared hive")

    # Phase 1: Each agent learns its own block's turns
    total_facts = 0
    for part in partitions:
        agent = agents[part.agent_name]
        for turn in part.turns:
            for fact in turn.facts:
                content = f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
                agent.learn(content, 0.9, [turn.block_name])
                total_facts += 1
            agent.learn(turn.content, 0.85, [turn.block_name, f"turn_{turn.turn_number}"])
            total_facts += 1

    print(f"    Phase 1: Learned {total_facts} facts across agents")

    # Phase 2: Each agent promotes all its facts to the hive
    promoted = 0
    for part in partitions:
        agent = agents[part.agent_name]
        for turn in part.turns:
            for fact in turn.facts:
                content = f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
                agent.promote(content, 0.9, [turn.block_name])
                promoted += 1
            agent.promote(turn.content, 0.85, [turn.block_name, f"turn_{turn.turn_number}"])
            promoted += 1

    print(f"    Phase 2: Promoted {promoted} facts to hive")

    # Phase 3: Run multiple gossip rounds
    gossip_rounds = 5
    for i in range(gossip_rounds):
        stats = hive.run_gossip_round()
    print(f"    Phase 3: Ran {gossip_rounds} gossip rounds")

    # Phase 4: Process all events
    event_stats = hive.process_events()
    total_events = sum(event_stats.values())
    print(f"    Phase 4: Processed {total_events} events across agents")

    # Phase 5: Answer questions using query_all (local + hive + gossip)
    # Use a designated coordinator agent, but any agent can answer
    coordinator_name = list(agents.keys())[0]

    per_question: dict[str, float] = {}
    per_category: dict[str, list[float]] = defaultdict(list)

    for q in questions:
        # Try the most relevant agent first, then coordinator
        relevant_block = _get_relevant_block_for_question(q, ground_truth)

        candidate_names = []
        if relevant_block and relevant_block in block_to_agents:
            candidate_names.extend(block_to_agents[relevant_block])
        # Always also try coordinator
        if coordinator_name not in candidate_names:
            candidate_names.append(coordinator_name)

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
    print(f"    Done in {elapsed:.1f}s. Overall: {overall:.1%}")

    # Print hive stats
    stats = hive.get_stats()
    print(
        f"    Hive stats: {stats['agent_count']} agents, "
        f"{stats['graph']['hive_facts']} hive facts, "
        f"{stats['events']['total_events']} total events"
    )

    return ConditionResult(
        name="HIVE_COLLECTIVE",
        overall_score=overall,
        per_category=cat_avg,
        per_question=per_question,
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_results(
    results: list[ConditionResult],
    questions: list[Question],
    partitions: list[AgentPartition],
) -> None:
    """Print the comparison table and hypothesis results."""
    single = results[0]

    print()
    print("=" * 60)
    print("=== DISTRIBUTED LEARNING EVALUATION ===")
    print("=" * 60)
    print(f"Turns: 1000 | Questions: {len(questions)} | Agents: {len(partitions)}")
    print()

    # Agent partition summary
    print("--- AGENT PARTITIONS ---")
    for p in partitions:
        print(f"  {p.agent_name:25s}  block={p.block_name:20s}  turns={len(p.turns)}")
    print()

    # Overall results table
    print("--- RESULTS ---")
    print(f"{'Condition':25s} {'Score':>8s} {'vs Single':>10s}")
    print("-" * 45)
    for r in results:
        vs_single = ""
        if r.name != "SINGLE_AGENT":
            if single.overall_score > 0:
                ratio = r.overall_score / single.overall_score
                vs_single = f"{ratio:.1%}"
            else:
                vs_single = "N/A"
        else:
            vs_single = "--"
        print(f"{r.name:25s} {r.overall_score:>7.1%} {vs_single:>10s}")
    print()

    # Per-category breakdown
    all_categories = sorted(set(q.category for q in questions))
    print("--- PER-CATEGORY BREAKDOWN ---")
    header = f"{'Category':30s}"
    for r in results:
        header += f" {r.name[:8]:>8s}"
    print(header)
    print("-" * (30 + 9 * len(results)))

    for cat in all_categories:
        row = f"{cat:30s}"
        for r in results:
            val = r.per_category.get(cat, 0.0)
            row += f" {val:>7.1%}"
        print(row)
    print()

    # Hypothesis testing
    print("--- HYPOTHESIS ---")
    hive_result = results[3]  # HIVE_COLLECTIVE
    flat_result = results[2]  # FLAT_SHARED
    isolated_result = results[1]  # ISOLATED

    # H1: Collective >= 80% of Single
    if single.overall_score > 0:
        h1_ratio = hive_result.overall_score / single.overall_score
        h1_pass = h1_ratio >= 0.80
        print(
            f"H1: Collective >= 80% of Single?  "
            f"[{'PASS' if h1_pass else 'FAIL'}]  "
            f"({h1_ratio:.1%} of single)"
        )
    else:
        print("H1: Cannot evaluate (single agent score is 0)")

    # H2: Hive > Flat-Shared
    h2_pass = hive_result.overall_score > flat_result.overall_score
    h2_diff = hive_result.overall_score - flat_result.overall_score
    print(
        f"H2: Hive > Flat-Shared?          "
        f"[{'PASS' if h2_pass else 'FAIL'}]  "
        f"(diff = {h2_diff:+.1%})"
    )

    # H3 (bonus): Hive > Isolated
    h3_pass = hive_result.overall_score > isolated_result.overall_score
    h3_diff = hive_result.overall_score - isolated_result.overall_score
    print(
        f"H3: Hive > Isolated?             "
        f"[{'PASS' if h3_pass else 'FAIL'}]  "
        f"(diff = {h3_diff:+.1%})"
    )
    print()

    # Per-question detail for interesting differences
    print("--- NOTABLE PER-QUESTION DIFFERENCES (Hive vs Single) ---")
    diffs = []
    for q in questions:
        single_s = single.per_question.get(q.question_id, 0.0)
        hive_s = hive_result.per_question.get(q.question_id, 0.0)
        diff = hive_s - single_s
        diffs.append((q.question_id, q.category, single_s, hive_s, diff))

    # Show worst 5 drops
    diffs.sort(key=lambda x: x[4])
    print("  Biggest drops (hive < single):")
    for qid, cat, ss, hs, d in diffs[:5]:
        if d < 0:
            print(f"    {qid:20s} {cat:25s}  single={ss:.0%}  hive={hs:.0%}  diff={d:+.0%}")

    # Show best 5 gains
    print("  Biggest gains (hive > single):")
    diffs.sort(key=lambda x: -x[4])
    for qid, cat, ss, hs, d in diffs[:5]:
        if d > 0:
            print(f"    {qid:20s} {cat:25s}  single={ss:.0%}  hive={hs:.0%}  diff={d:+.0%}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the distributed learning evaluation."""
    print("Generating dialogue and questions...")
    t0 = time.time()

    ground_truth = generate_dialogue(num_turns=1000, seed=42)
    questions = generate_questions(ground_truth, num_questions=100)

    print(
        f"  {len(ground_truth.turns)} turns, {len(questions)} questions generated in {time.time() - t0:.1f}s"
    )

    # Partition turns across agents
    partitions = partition_turns(ground_truth, large_block_threshold=100)
    print(f"  {len(partitions)} agent partitions created")

    # Block distribution summary
    blocks_summary = defaultdict(int)
    for p in partitions:
        blocks_summary[p.block_name] += len(p.turns)
    for block, count in sorted(blocks_summary.items(), key=lambda x: -x[1]):
        agent_names = [p.agent_name for p in partitions if p.block_name == block]
        print(f"    {block:20s}: {count:4d} turns -> {agent_names}")
    print()

    # Run all 4 conditions
    print("Running evaluation conditions...")
    results: list[ConditionResult] = []

    results.append(run_single_agent(ground_truth, questions))
    results.append(run_isolated(ground_truth, questions, partitions))
    results.append(run_flat_shared(ground_truth, questions, partitions))
    results.append(run_hive_collective(ground_truth, questions, partitions))

    # Print results
    print_results(results, questions, partitions)


if __name__ == "__main__":
    main()
