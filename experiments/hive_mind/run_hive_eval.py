#!/usr/bin/env python3
"""Hive Mind Evaluation — Uses amplihack-agent-eval framework.

Runs all 5 predefined hive mind scenarios from the eval library:
1. hive_infra: Infrastructure team (networking, storage, compute, security, monitoring)
2. hive_arch: Software architecture team (frontend, backend, database, devops, testing)
3. hive_incident: Incident response (timeline, logs, metrics, code, comms)
4. hive_research: Research synthesis (5 papers on same topic)
5. hive_adversarial: Resilience test (4 correct + 1 misleading agent)

Each scenario: 20 facts per agent x 5 agents = 100 facts, 15 questions
(5 single-domain, 5 cross-domain, 5 synthesis).

Scoring dimensions (from hive_mind_scoring.py):
- cross_domain_accuracy (30%): Can agents answer cross-domain questions?
- knowledge_coverage (20%): What % of total knowledge does each agent access?
- collaboration_efficiency (15%): How many rounds needed for coverage?
- adversarial_resilience (15%): Does the hive suppress bad data?
- no_regression (20%): Do agents maintain own-domain accuracy?

Usage:
    uv run python experiments/hive_mind/run_hive_eval.py
    uv run python experiments/hive_mind/run_hive_eval.py --scenarios hive_infra,hive_adversarial
    uv run python experiments/hive_mind/run_hive_eval.py --output results.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

# Path setup
_EVAL_PATH = "/home/azureuser/src/amplihack-agent-eval/src"
if _EVAL_PATH not in sys.path:
    sys.path.insert(0, _EVAL_PATH)
_AMPLIHACK_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "src")
if _AMPLIHACK_PATH not in sys.path:
    sys.path.insert(0, os.path.abspath(_AMPLIHACK_PATH))

from amplihack_eval.adapters.base import (  # type: ignore[import-not-found]
    AgentAdapter,
    AgentResponse,
)
from amplihack_eval.adapters.hive_mind_adapter import (  # type: ignore[import-not-found]
    HiveMindGroupAdapter,
    InMemorySharedStore,
)
from amplihack_eval.data.hive_mind_scenarios import (  # type: ignore[import-not-found]
    ALL_HIVE_MIND_SCENARIOS,
    HiveMindScenario,
    get_scenario_by_id,
)
from amplihack_eval.levels.hive_mind_scoring import (  # type: ignore[import-not-found]
    score_hive_mind_scenario,
)

from amplihack.agents.goal_seeking.hive_mind.hive_graph import (  # type: ignore[import-not-found]
    HiveFact,
    InMemoryHiveGraph,
    _tokenize,
)

# ---------------------------------------------------------------------------
# HiveGraph-backed SharedMemoryStore
# ---------------------------------------------------------------------------


class HiveGraphSharedStore:
    """SharedMemoryStore backed by InMemoryHiveGraph with federation.

    Creates a federation tree: root hive with one child per agent domain.
    Facts stored by an agent go into that agent's child hive. Queries use
    query_federated to search across the entire tree.
    """

    def __init__(self) -> None:
        self._root = InMemoryHiveGraph("root")
        self._children: dict[str, InMemoryHiveGraph] = {}
        self._facts: dict[str, list[str]] = {}

    def store(self, agent_id: str, fact: str, metadata: dict | None = None) -> None:
        if agent_id not in self._children:
            child = InMemoryHiveGraph(f"hive-{agent_id}")
            child.register_agent(agent_id, domain=agent_id)
            self._root.add_child(child)
            child.set_parent(self._root)
            self._children[agent_id] = child

        child = self._children[agent_id]
        child.promote_fact(
            agent_id,
            HiveFact(
                fact_id="",
                content=fact,
                concept=agent_id,
                confidence=0.9,
            ),
        )

        if agent_id not in self._facts:
            self._facts[agent_id] = []
        self._facts[agent_id].append(fact)

    def query(self, question: str, requesting_agent: str | None = None) -> list[str]:
        results = self._root.query_federated(question, limit=50)
        return [f.content for f in results]

    def get_all_facts(self, agent_id: str | None = None) -> list[str]:
        if agent_id is not None:
            return list(self._facts.get(agent_id, []))
        return [f for facts in self._facts.values() for f in facts]

    def get_agent_ids(self) -> list[str]:
        return list(self._facts.keys())

    def clear(self) -> None:
        self._root = InMemoryHiveGraph("root")
        self._children.clear()
        self._facts.clear()


# ---------------------------------------------------------------------------
# Simple keyword-based AgentAdapter (no LLM needed)
# ---------------------------------------------------------------------------


class KeywordAgent(AgentAdapter):
    """Agent that stores facts and answers by returning matching facts.

    No LLM involved — answers are the concatenation of stored facts that
    keyword-match the question. This is appropriate for the eval since
    scoring is keyword-based (does the answer contain expected keywords?).
    """

    def __init__(self, agent_id: str) -> None:
        self._agent_id = agent_id
        self._facts: list[str] = []

    def learn(self, content: str) -> None:
        self._facts.append(content)

    def answer(self, question: str) -> AgentResponse:
        # Return facts that share keywords with the question
        query_words = _tokenize(question)
        scored = []
        for fact in self._facts:
            fact_words = _tokenize(fact)
            hits = len(query_words & fact_words)
            if hits > 0:
                scored.append((hits, fact))

        scored.sort(key=lambda x: -x[0])
        matched = [f for _, f in scored[:20]]

        if not matched:
            # Fall back to all facts
            matched = self._facts[:20]

        answer = "\n".join(matched)
        return AgentResponse(answer=answer)

    def reset(self) -> None:
        self._facts.clear()

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Run evaluation
# ---------------------------------------------------------------------------


def run_scenario(
    scenario: HiveMindScenario,
    use_federation: bool = True,
) -> dict:
    """Run a single scenario and return the eval report as a dict.

    Args:
        scenario: The hive mind scenario to evaluate
        use_federation: If True, use HiveGraphSharedStore (federated).
                       If False, use InMemorySharedStore (flat keyword).
    """
    print(f"\n{'=' * 60}")
    print(f"  Scenario: {scenario.scenario_id}")
    print(f"  Agents: {scenario.num_agents}")
    print(f"  Questions: {len(scenario.questions)}")
    print(f"  Store: {'HiveGraph federation' if use_federation else 'InMemory flat'}")
    print(f"{'=' * 60}")

    agent_ids = list(scenario.agent_domains.keys())

    # --- Baseline: isolated agents (no shared store) ---
    print("\n  [1/4] Running baseline (isolated agents)...")
    baseline_agents = {aid: KeywordAgent(aid) for aid in agent_ids}
    # Each agent only learns its own facts
    for aid, facts in scenario.agent_domains.items():
        for fact in facts:
            baseline_agents[aid].learn(fact)

    baseline_responses: dict[str, dict[str, AgentResponse]] = {}
    for aid in agent_ids:
        baseline_responses[aid] = {}
        for q in scenario.questions:
            baseline_responses[aid][q.question_id] = baseline_agents[aid].answer(q.text)

    # --- Hive: agents with shared store ---
    print("  [2/4] Running hive (shared store)...")
    shared_store = HiveGraphSharedStore() if use_federation else InMemorySharedStore()
    hive_agents = {aid: KeywordAgent(aid) for aid in agent_ids}
    hive = HiveMindGroupAdapter(
        agents=hive_agents,
        shared_store=shared_store,
        propagation_rounds=3,
    )

    # Distributed learning
    learn_result = hive.learn_distributed(scenario.agent_domains)
    total_facts = sum(learn_result.values())
    print(f"    Facts learned: {total_facts}")

    # Propagation
    print("  [3/4] Propagating knowledge...")
    prop = hive.propagate_knowledge()
    print(f"    Rounds: {prop.rounds_executed}, Facts propagated: {prop.facts_propagated}")

    # Collect hive responses
    print("  [4/4] Evaluating queries...")
    hive_responses: dict[str, dict[str, AgentResponse]] = {}
    for aid in agent_ids:
        hive_responses[aid] = {}
        for q in scenario.questions:
            hive_responses[aid][q.question_id] = hive.ask_agent(aid, q.text)

    # Score
    coverage = hive.get_coverage_stats()
    report = score_hive_mind_scenario(
        scenario=scenario,
        responses=hive_responses,
        baseline_responses=baseline_responses,
        coverage_stats=coverage,
        propagation_rounds=prop.rounds_executed,
        max_propagation_rounds=3,
        total_facts_propagated=prop.facts_propagated,
    )

    # Print results
    print(f"\n  Results for {scenario.scenario_id}:")
    print(f"  {'Dimension':<30s} {'Score':>8s}")
    print(f"  {'-' * 40}")
    for dim in report.dimensions:
        print(f"  {dim.dimension:<30s} {dim.score:>7.1%}")
    print(f"  {'-' * 40}")
    print(f"  {'OVERALL':<30s} {report.overall_score:>7.1%}")
    print(f"  {'Hive vs Baseline delta':<30s} {report.hive_vs_baseline_delta:>+7.1%}")
    print("\n  Per-difficulty:")
    for diff, score in report.per_difficulty_scores.items():
        print(f"    {diff:<20s} {score:>7.1%}")

    # Per-question detail
    print("\n  Per-question results:")
    for qr in report.question_results:
        delta = qr.hive_score - qr.baseline_score
        status = "+" if delta > 0 else ("=" if delta == 0 else "-")
        print(
            f"    [{status}] {qr.question_id}: "
            f"hive={qr.hive_score:.0%} baseline={qr.baseline_score:.0%} "
            f"({qr.difficulty}) found={len(qr.keywords_found)}/{len(qr.keywords_found) + len(qr.keywords_missing)}"
        )

    hive.close()
    for a in baseline_agents.values():
        a.close()

    return report.to_dict()


def main():
    parser = argparse.ArgumentParser(description="Hive Mind Evaluation")
    parser.add_argument(
        "--scenarios",
        type=str,
        default="",
        help="Comma-separated scenario IDs (default: all 5)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="experiments/hive_mind/eval_results_hive.json",
        help="Output JSON file path",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Use flat InMemorySharedStore instead of HiveGraph federation",
    )
    args = parser.parse_args()

    # Select scenarios
    if args.scenarios:
        scenario_ids = [s.strip() for s in args.scenarios.split(",")]
        scenarios = []
        for sid in scenario_ids:
            s = get_scenario_by_id(sid)
            if s is None:
                print(f"ERROR: Unknown scenario '{sid}'")
                print(f"Available: {[s.scenario_id for s in ALL_HIVE_MIND_SCENARIOS]}")
                sys.exit(1)
            scenarios.append(s)
    else:
        scenarios = list(ALL_HIVE_MIND_SCENARIOS)

    print(f"Running {len(scenarios)} hive mind scenarios...")
    print(f"Store: {'flat InMemory' if args.flat else 'HiveGraph federation'}")

    start = time.time()
    all_results = []

    for scenario in scenarios:
        result = run_scenario(scenario, use_federation=not args.flat)
        all_results.append(result)

    elapsed = time.time() - start

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  FINAL SUMMARY ({len(scenarios)} scenarios, {elapsed:.1f}s)")
    print(f"{'=' * 60}")
    print(f"  {'Scenario':<25s} {'Overall':>8s} {'Cross-Domain':>13s} {'Delta':>8s}")
    print(f"  {'-' * 55}")

    for r in all_results:
        cross = next(
            (d["score"] for d in r["dimensions"] if d["dimension"] == "cross_domain_accuracy"),
            0.0,
        )
        print(
            f"  {r['scenario_id']:<25s} "
            f"{r['overall_score']:>7.1%} "
            f"{cross:>12.1%} "
            f"{r['hive_vs_baseline_delta']:>+7.1%}"
        )

    avg_overall = sum(r["overall_score"] for r in all_results) / len(all_results)
    avg_delta = sum(r["hive_vs_baseline_delta"] for r in all_results) / len(all_results)
    print(f"  {'-' * 55}")
    print(f"  {'AVERAGE':<25s} {avg_overall:>7.1%} {'':>13s} {avg_delta:>+7.1%}")

    # Save results
    output = {
        "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "store_type": "flat" if args.flat else "hive_graph_federation",
        "num_scenarios": len(all_results),
        "elapsed_seconds": round(elapsed, 1),
        "average_overall_score": round(avg_overall, 4),
        "average_hive_vs_baseline_delta": round(avg_delta, 4),
        "scenarios": all_results,
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to: {args.output}")


if __name__ == "__main__":
    main()
