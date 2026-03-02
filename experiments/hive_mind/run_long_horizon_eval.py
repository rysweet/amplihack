#!/usr/bin/env python3
"""Long-horizon eval for single agent, flat hive, and federated hive.

Uses the same long_horizon data (1000 turns, 12 categories, 100 questions)
from amplihack-agent-eval. Three modes:

  single   -- 1 agent learns all 1000 turns (ceiling/baseline)
  flat     -- 20 agents, all share one InMemoryHiveGraph (flat, no federation)
  federated -- 100 agents in 5 groups of 20, federation tree

The federated topology:
    Root Hive
    ├── Group 0 (20 agents -> 1 group hive)
    ├── Group 1 (20 agents -> 1 group hive)
    ├── Group 2 (20 agents -> 1 group hive)
    ├── Group 3 (20 agents -> 1 group hive)
    └── Group 4 (20 agents -> 1 group hive)

Usage:
    # Run all 3 modes
    uv run python experiments/hive_mind/run_long_horizon_eval.py

    # Run specific mode
    uv run python experiments/hive_mind/run_long_horizon_eval.py --mode single
    uv run python experiments/hive_mind/run_long_horizon_eval.py --mode flat
    uv run python experiments/hive_mind/run_long_horizon_eval.py --mode federated

    # Custom turns/questions
    uv run python experiments/hive_mind/run_long_horizon_eval.py --turns 500 --questions 50

    # Save results
    uv run python experiments/hive_mind/run_long_horizon_eval.py --output results.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict

# Path setup
_EVAL_PATH = "/home/azureuser/src/amplihack-agent-eval/src"
if _EVAL_PATH not in sys.path:
    sys.path.insert(0, _EVAL_PATH)
_AMPLIHACK_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "src")
if _AMPLIHACK_PATH not in sys.path:
    sys.path.insert(0, os.path.abspath(_AMPLIHACK_PATH))

from amplihack_eval.data.long_horizon import (  # type: ignore[import-not-found]
    GroundTruth,
    Question,
    Turn,
    generate_dialogue,
    generate_questions,
)

from amplihack.agents.goal_seeking.hive_mind.hive_graph import (  # type: ignore[import-not-found]
    HiveFact,
    InMemoryHiveGraph,
)


def score_question(question: Question, retrieved_texts: list[str]) -> float:
    """Score by checking rubric keywords against retrieved texts.

    Returns fraction [0.0, 1.0] of required keywords found.
    Copied from run_distributed_eval.py to avoid importing unified.py.
    """
    import re

    corpus = " ".join(retrieved_texts).lower()

    keywords: list[str] = []
    paraphrases: list[str] = []
    incorrect: list[str] = []

    if question.rubric and question.rubric.required_keywords:
        keywords = question.rubric.required_keywords
        paraphrases = question.rubric.acceptable_paraphrases or []
        incorrect = question.rubric.incorrect_patterns or []
    elif question.rubric and question.rubric.acceptable_paraphrases:
        for p in question.rubric.acceptable_paraphrases:
            if p.lower() in corpus:
                return 1.0
        return 0.0
    else:
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
# Helpers
# ---------------------------------------------------------------------------


def _learn_turns_into_hive(
    hive: InMemoryHiveGraph,
    agent_id: str,
    turns: list[Turn],
) -> int:
    """Store all facts from turns into a hive graph. Returns fact count."""
    count = 0
    for turn in turns:
        for fact in turn.facts:
            content = (
                f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
            )
            hive.promote_fact(
                agent_id,
                HiveFact(
                    fact_id="",
                    content=content,
                    concept=turn.block_name,
                    confidence=0.9,
                ),
            )
            count += 1
        hive.promote_fact(
            agent_id,
            HiveFact(
                fact_id="",
                content=turn.content,
                concept=turn.block_name,
                confidence=0.85,
            ),
        )
        count += 1
    return count


def _query_hive(hive: InMemoryHiveGraph, query: str, limit: int = 50) -> list[str]:
    """Query a hive and return fact content strings."""
    results = hive.query_facts(query, limit=limit)
    return [f.content for f in results]


def _query_federated(hive: InMemoryHiveGraph, query: str, limit: int = 50) -> list[str]:
    """Query a hive using federation and return fact content strings."""
    results = hive.query_federated(query, limit=limit)
    return [f.content for f in results]


# ---------------------------------------------------------------------------
# Mode 1: Single Agent
# ---------------------------------------------------------------------------


def run_single(
    ground_truth: GroundTruth,
    questions: list[Question],
) -> dict:
    """One agent, one hive, all 1000 turns. The ceiling."""
    print("\n  [SINGLE] 1 agent, all turns...")
    t0 = time.time()

    hive = InMemoryHiveGraph("single")
    hive.register_agent("single_agent")
    fact_count = _learn_turns_into_hive(hive, "single_agent", ground_truth.turns)
    print(f"    Learned {fact_count} facts")

    per_q: dict[str, float] = {}
    per_cat: dict[str, list[float]] = defaultdict(list)

    for q in questions:
        texts = _query_hive(hive, q.text, limit=50)
        s = score_question(q, texts)
        per_q[q.question_id] = s
        per_cat[q.category].append(s)

    overall = sum(per_q.values()) / len(per_q) if per_q else 0.0
    cat_avg = {c: sum(ss) / len(ss) for c, ss in per_cat.items()}

    elapsed = time.time() - t0
    print(f"    Done in {elapsed:.1f}s. Overall: {overall:.1%}")

    return {
        "mode": "single",
        "agents": 1,
        "facts": fact_count,
        "overall": round(overall, 4),
        "per_category": {c: round(v, 4) for c, v in cat_avg.items()},
        "per_question": {qid: round(v, 4) for qid, v in per_q.items()},
        "elapsed_seconds": round(elapsed, 1),
    }


# ---------------------------------------------------------------------------
# Mode 2: Flat Hive (20 agents, one shared hive)
# ---------------------------------------------------------------------------


def run_flat(
    ground_truth: GroundTruth,
    questions: list[Question],
    num_agents: int = 20,
) -> dict:
    """N agents, turns distributed round-robin, all in one flat hive."""
    print(f"\n  [FLAT] {num_agents} agents, 1 shared hive...")
    t0 = time.time()

    hive = InMemoryHiveGraph("flat")
    agent_ids = [f"agent_{i:03d}" for i in range(num_agents)]
    for aid in agent_ids:
        hive.register_agent(aid, domain=f"domain_{aid}")

    # Distribute turns round-robin
    total_facts = 0
    for i, turn in enumerate(ground_truth.turns):
        aid = agent_ids[i % num_agents]
        total_facts += _learn_turns_into_hive(hive, aid, [turn])

    print(f"    {total_facts} facts across {num_agents} agents in 1 hive")

    per_q: dict[str, float] = {}
    per_cat: dict[str, list[float]] = defaultdict(list)

    for q in questions:
        texts = _query_hive(hive, q.text, limit=50)
        s = score_question(q, texts)
        per_q[q.question_id] = s
        per_cat[q.category].append(s)

    overall = sum(per_q.values()) / len(per_q) if per_q else 0.0
    cat_avg = {c: sum(ss) / len(ss) for c, ss in per_cat.items()}

    elapsed = time.time() - t0
    print(f"    Done in {elapsed:.1f}s. Overall: {overall:.1%}")

    return {
        "mode": "flat",
        "agents": num_agents,
        "facts": total_facts,
        "overall": round(overall, 4),
        "per_category": {c: round(v, 4) for c, v in cat_avg.items()},
        "per_question": {qid: round(v, 4) for qid, v in per_q.items()},
        "elapsed_seconds": round(elapsed, 1),
    }


# ---------------------------------------------------------------------------
# Mode 3: Federated Hive (100 agents, 5 groups of 20)
# ---------------------------------------------------------------------------


def run_federated(
    ground_truth: GroundTruth,
    questions: list[Question],
    num_groups: int = 5,
    agents_per_group: int = 20,
) -> dict:
    """N groups x M agents, federation tree with root + group hives."""
    total_agents = num_groups * agents_per_group
    print(f"\n  [FEDERATED] {total_agents} agents in {num_groups} groups of {agents_per_group}...")
    t0 = time.time()

    # Build federation tree
    root = InMemoryHiveGraph("root")
    groups: list[InMemoryHiveGraph] = []
    all_agent_ids: list[str] = []

    for g in range(num_groups):
        group_hive = InMemoryHiveGraph(f"group_{g}")
        root.add_child(group_hive)
        group_hive.set_parent(root)
        groups.append(group_hive)

        for a in range(agents_per_group):
            aid = f"g{g}_agent_{a:03d}"
            group_hive.register_agent(aid, domain=f"group_{g}")
            all_agent_ids.append(aid)

    print(f"    Federation: root -> {num_groups} groups -> {agents_per_group} agents each")

    # Distribute turns round-robin across ALL agents
    total_facts = 0
    for i, turn in enumerate(ground_truth.turns):
        group_idx = i % num_groups
        agent_idx = (i // num_groups) % agents_per_group
        aid = f"g{group_idx}_agent_{agent_idx:03d}"
        total_facts += _learn_turns_into_hive(groups[group_idx], aid, [turn])

    print(f"    {total_facts} facts distributed across {total_agents} agents")

    per_q: dict[str, float] = {}
    per_cat: dict[str, list[float]] = defaultdict(list)

    for q in questions:
        # Query through federation from the root
        texts = _query_federated(root, q.text, limit=50)
        s = score_question(q, texts)
        per_q[q.question_id] = s
        per_cat[q.category].append(s)

    overall = sum(per_q.values()) / len(per_q) if per_q else 0.0
    cat_avg = {c: sum(ss) / len(ss) for c, ss in per_cat.items()}

    elapsed = time.time() - t0
    print(f"    Done in {elapsed:.1f}s. Overall: {overall:.1%}")
    print(f"    Root stats: {root.get_stats()}")

    return {
        "mode": "federated",
        "agents": total_agents,
        "groups": num_groups,
        "agents_per_group": agents_per_group,
        "facts": total_facts,
        "overall": round(overall, 4),
        "per_category": {c: round(v, 4) for c, v in cat_avg.items()},
        "per_question": {qid: round(v, 4) for qid, v in per_q.items()},
        "elapsed_seconds": round(elapsed, 1),
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_report(results: list[dict], questions: list[Question]) -> None:
    """Print comparison table across all modes."""
    categories = sorted(set(q.category for q in questions))

    print(f"\n{'=' * 70}")
    print("  LONG-HORIZON EVAL RESULTS")
    print(f"{'=' * 70}")
    print(f"  Turns: {len(questions)} questions from 1000-turn dialogue")
    print()

    # Overall table
    print(f"  {'Mode':<15s} {'Agents':>7s} {'Overall':>9s} {'vs Single':>10s}")
    print(f"  {'-' * 43}")
    single_score = results[0]["overall"] if results else 0.0
    for r in results:
        vs = ""
        if r["mode"] != "single" and single_score > 0:
            ratio = r["overall"] / single_score
            vs = f"{ratio:.1%}"
        else:
            vs = "--"
        print(f"  {r['mode']:<15s} {r['agents']:>7d} {r['overall']:>8.1%} {vs:>10s}")
    print()

    # Per-category
    print(f"  {'Category':<28s}", end="")
    for r in results:
        print(f" {r['mode'][:10]:>10s}", end="")
    print()
    print(f"  {'-' * (28 + 11 * len(results))}")

    for cat in categories:
        print(f"  {cat:<28s}", end="")
        for r in results:
            val = r["per_category"].get(cat, 0.0)
            print(f" {val:>9.1%}", end="")
        print()
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Long-horizon eval: single vs flat vs federated hive mind"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="all",
        choices=["all", "single", "flat", "federated"],
        help="Which mode(s) to run (default: all)",
    )
    parser.add_argument("--turns", type=int, default=1000, help="Number of dialogue turns")
    parser.add_argument("--questions", type=int, default=100, help="Number of questions")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--flat-agents", type=int, default=20, help="Agents for flat mode")
    parser.add_argument("--fed-groups", type=int, default=5, help="Groups for federated mode")
    parser.add_argument(
        "--fed-agents-per-group", type=int, default=20, help="Agents per group for federated"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="experiments/hive_mind/eval_results_long_horizon.json",
        help="Output JSON file",
    )
    args = parser.parse_args()

    print(f"Generating {args.turns}-turn dialogue with seed={args.seed}...")
    t0 = time.time()

    ground_truth = generate_dialogue(num_turns=args.turns, seed=args.seed)
    questions = generate_questions(ground_truth, num_questions=args.questions)

    print(
        f"  {len(ground_truth.turns)} turns, {len(questions)} questions in {time.time() - t0:.1f}s"
    )

    # Count per block
    blocks: dict[str, int] = defaultdict(int)
    for t in ground_truth.turns:
        blocks[t.block_name] += 1
    for b, c in sorted(blocks.items(), key=lambda x: -x[1]):
        print(f"    {b:<20s}: {c:4d} turns")

    # Count per category
    cats: dict[str, int] = defaultdict(int)
    for q in questions:
        cats[q.category] += 1
    print("\n  Questions by category:")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {c:<28s}: {n}")

    # Run modes
    results: list[dict] = []
    modes = ["single", "flat", "federated"] if args.mode == "all" else [args.mode]

    for mode in modes:
        if mode == "single":
            results.append(run_single(ground_truth, questions))
        elif mode == "flat":
            results.append(run_flat(ground_truth, questions, num_agents=args.flat_agents))
        elif mode == "federated":
            results.append(
                run_federated(
                    ground_truth,
                    questions,
                    num_groups=args.fed_groups,
                    agents_per_group=args.fed_agents_per_group,
                )
            )

    # Report
    print_report(results, questions)

    # Save
    output = {
        "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "config": {
            "turns": args.turns,
            "questions": args.questions,
            "seed": args.seed,
        },
        "results": results,
    }
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Results saved to: {args.output}")


if __name__ == "__main__":
    main()
