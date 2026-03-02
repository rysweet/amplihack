#!/usr/bin/env python3
"""Long-horizon eval against live Azure Container Apps agents.

Teaches the same long_horizon data to Azure agents via HTTP, waits for
Service Bus propagation, then queries each agent and scores responses.

Usage:
    # Run against deployed agents (auto-discovers from Azure CLI)
    uv run python experiments/hive_mind/run_azure_long_horizon_eval.py

    # Custom turns/questions
    uv run python experiments/hive_mind/run_azure_long_horizon_eval.py --turns 500 --questions 50

    # Custom resource group
    uv run python experiments/hive_mind/run_azure_long_horizon_eval.py --resource-group my-rg

    # Propagation wait time (seconds)
    uv run python experiments/hive_mind/run_azure_long_horizon_eval.py --propagation-wait 60
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from typing import Any

import httpx  # type: ignore[import-untyped]

# Path setup
_EVAL_PATH = "/home/azureuser/src/amplihack-agent-eval/src"
if _EVAL_PATH not in sys.path:
    sys.path.insert(0, _EVAL_PATH)

from amplihack_eval.data.long_horizon import (  # type: ignore[import-not-found]
    Question,
    generate_dialogue,
    generate_questions,
)


def score_question(question: Question, retrieved_texts: list[str]) -> float:
    """Score by checking rubric keywords against retrieved texts."""
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
# Azure agent discovery
# ---------------------------------------------------------------------------


def discover_agents(resource_group: str) -> dict[str, str]:
    """Discover agent URLs from Azure Container Apps."""
    result = subprocess.run(
        [
            "az",
            "containerapp",
            "list",
            "--resource-group",
            resource_group,
            "--query",
            "[].{name:name, fqdn:properties.configuration.ingress.fqdn}",
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"ERROR: az containerapp list failed: {result.stderr}")
        sys.exit(1)

    apps = json.loads(result.stdout)
    agents: dict[str, str] = {}
    for app in apps:
        name = app["name"]
        fqdn = app.get("fqdn", "")
        if not fqdn:
            continue
        # Extract agent_id from container name: hive-agent-biology-1 -> biology_1
        parts = name.replace("hive-agent-", "").rsplit("-", 1)
        if len(parts) == 2:
            agent_id = f"{parts[0]}_{parts[1]}"
        else:
            agent_id = parts[0]
        agents[agent_id] = f"https://{fqdn}"
    return agents


# ---------------------------------------------------------------------------
# HTTP operations
# ---------------------------------------------------------------------------


def teach_agent(
    client: httpx.Client,
    url: str,
    agent_id: str,
    facts: list[dict],
) -> int:
    """Teach facts to an agent via /learn_batch. Returns count stored."""
    try:
        resp = client.post(
            f"{url}/learn_batch",
            json={"facts": facts},
            timeout=30.0,
        )
        if resp.status_code == 200:
            return resp.json().get("count", 0)
        print(f"  WARN: {agent_id} learn_batch returned {resp.status_code}")
        return 0
    except Exception as e:
        print(f"  ERROR: {agent_id} learn_batch failed: {e}")
        return 0


def query_agent(
    client: httpx.Client,
    url: str,
    query: str,
    limit: int = 50,
) -> list[str]:
    """Query an agent and return fact content strings."""
    try:
        resp = client.post(
            f"{url}/query",
            json={"query": query, "limit": limit},
            timeout=30.0,
        )
        if resp.status_code == 200:
            return [r["content"] for r in resp.json().get("results", [])]
        return []
    except Exception:
        return []


def get_agent_stats(client: httpx.Client, url: str) -> dict:
    """Get agent stats."""
    try:
        resp = client.get(f"{url}/stats", timeout=10.0)
        if resp.status_code == 200:
            return resp.json().get("stats", {})
        return {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Eval
# ---------------------------------------------------------------------------


def run_azure_mode(
    mode: str,
    ground_truth: Any,
    questions: list,
    domain_agents: dict[str, str],
    client: httpx.Client,
    propagation_wait: int,
) -> dict:
    """Run a single eval mode against Azure agents.

    Modes:
        single: Teach ALL facts to 1 agent, query only that agent.
        flat: Teach round-robin to all agents, wait for SB propagation, query best-of-5.
        federated: 4 groups of 5 agents, facts only propagate within group,
                   query one agent per group and take best.
    """
    agent_ids = sorted(domain_agents.keys())
    print(f"\n  [{mode.upper()}] Running against {len(agent_ids)} Azure agents...")

    if mode == "single":
        # Teach everything to one agent, query only that agent
        target = agent_ids[0]
        target_url = domain_agents[target]
        print(f"    Target agent: {target}")

        all_facts: list[dict] = []
        for turn in ground_truth.turns:
            for fact in turn.facts:
                content = f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
                all_facts.append(
                    {"concept": turn.block_name, "content": content, "confidence": 0.9}
                )
            all_facts.append(
                {"concept": turn.block_name, "content": turn.content, "confidence": 0.85}
            )

        total = 0
        for i in range(0, len(all_facts), 50):
            total += teach_agent(client, target_url, target, all_facts[i : i + 50])
        print(f"    Taught {total} facts to {target}")

        # Query only this agent
        per_q: dict[str, float] = {}
        per_cat: dict[str, list[float]] = defaultdict(list)
        for q in questions:
            texts = query_agent(client, target_url, q.text, limit=50)
            s = score_question(q, texts)
            per_q[q.question_id] = s
            per_cat[q.category].append(s)

        overall = sum(per_q.values()) / len(per_q) if per_q else 0.0
        print(f"    Overall: {overall:.1%}")

        return {
            "mode": "azure-single",
            "agents": 1,
            "facts": total,
            "overall": round(overall, 4),
            "per_category": {c: round(sum(ss) / len(ss), 4) for c, ss in per_cat.items()},
            "per_question": {qid: round(v, 4) for qid, v in per_q.items()},
        }

    # Helper: build facts from turns
    def _turns_to_facts(turns: list) -> list[dict]:
        facts: list[dict] = []
        for turn in turns:
            for fact in turn.facts:
                content = f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
                facts.append({"concept": turn.block_name, "content": content, "confidence": 0.9})
            facts.append({"concept": turn.block_name, "content": turn.content, "confidence": 0.85})
        return facts

    # Helper: reset all agents to clean state
    def _reset_all() -> None:
        for aid in agent_ids:
            try:
                client.post(f"{domain_agents[aid]}/reset", timeout=10.0)
            except Exception:
                pass

    # Helper: set group on agents
    def _set_groups(groups: dict[str, list[str]]) -> None:
        for group_name, members in groups.items():
            for aid in members:
                if aid in domain_agents:
                    try:
                        client.post(
                            f"{domain_agents[aid]}/set_group",
                            json={"group": group_name},
                            timeout=10.0,
                        )
                    except Exception:
                        pass

    if mode == "flat":
        # Teach round-robin, wait for propagation, query best-of-5
        agent_facts_map: dict[str, list[dict]] = defaultdict(list)
        for i, turn in enumerate(ground_truth.turns):
            aid = agent_ids[i % len(agent_ids)]
            for fact in turn.facts:
                content = f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
                agent_facts_map[aid].append(
                    {"concept": turn.block_name, "content": content, "confidence": 0.9}
                )
            agent_facts_map[aid].append(
                {"concept": turn.block_name, "content": turn.content, "confidence": 0.85}
            )

        total = 0
        for aid in agent_ids:
            facts = agent_facts_map[aid]
            for i in range(0, len(facts), 50):
                total += teach_agent(client, domain_agents[aid], aid, facts[i : i + 50])
        print(f"    Taught {total} facts across {len(agent_ids)} agents")

        print(f"    Waiting {propagation_wait}s for propagation...")
        time.sleep(propagation_wait)

        for aid in agent_ids[:2]:
            stats = get_agent_stats(client, domain_agents[aid])
            own = len(agent_facts_map.get(aid, []))
            got = stats.get("fact_count", 0)
            print(f"    {aid}: own={own}, total={got}, via_bus={got - own}")

        per_q: dict[str, float] = {}
        per_cat: dict[str, list[float]] = defaultdict(list)
        for q in questions:
            best_score = 0.0
            for aid in agent_ids[:5]:
                texts = query_agent(client, domain_agents[aid], q.text, limit=50)
                s = score_question(q, texts)
                if s > best_score:
                    best_score = s
            per_q[q.question_id] = best_score
            per_cat[q.category].append(best_score)

        overall = sum(per_q.values()) / len(per_q) if per_q else 0.0
        print(f"    Overall: {overall:.1%}")

        return {
            "mode": "azure-flat",
            "agents": len(agent_ids),
            "facts": total,
            "overall": round(overall, 4),
            "per_category": {c: round(sum(ss) / len(ss), 4) for c, ss in per_cat.items()},
            "per_question": {qid: round(v, 4) for qid, v in per_q.items()},
        }

    if mode == "federated":
        # Split 20 agents into 4 groups of 5
        num_groups = 4
        group_size = len(agent_ids) // num_groups
        groups: dict[str, list[str]] = {}
        for g in range(num_groups):
            group_name = f"group_{g}"
            groups[group_name] = agent_ids[g * group_size : (g + 1) * group_size]
        print(f"    Groups: {num_groups} x {group_size} agents")
        for gn, members in groups.items():
            print(f"      {gn}: {members}")

        # Reset all agents and set groups
        print("    Resetting agents and setting groups...")
        _reset_all()
        time.sleep(2)
        _set_groups(groups)

        # Teach facts: distribute round-robin across ALL agents
        # but each agent's group determines which SB events it accepts
        agent_facts_map = defaultdict(list)
        for i, turn in enumerate(ground_truth.turns):
            aid = agent_ids[i % len(agent_ids)]
            for fact in turn.facts:
                content = f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
                agent_facts_map[aid].append(
                    {"concept": turn.block_name, "content": content, "confidence": 0.9}
                )
            agent_facts_map[aid].append(
                {"concept": turn.block_name, "content": turn.content, "confidence": 0.85}
            )

        total = 0
        for aid in agent_ids:
            facts = agent_facts_map[aid]
            for i in range(0, len(facts), 50):
                total += teach_agent(client, domain_agents[aid], aid, facts[i : i + 50])
        print(f"    Taught {total} facts across {len(agent_ids)} agents")

        print(f"    Waiting {propagation_wait}s for within-group propagation...")
        time.sleep(propagation_wait)

        # Check: agents should have facts from their group only
        for gn, members in list(groups.items())[:2]:
            aid = members[0]
            stats = get_agent_stats(client, domain_agents[aid])
            own = len(agent_facts_map.get(aid, []))
            got = stats.get("fact_count", 0)
            group_total = sum(len(agent_facts_map.get(m, [])) for m in members)
            print(f"    {aid} ({gn}): own={own}, total={got}, group_expected~={group_total}")

        # Query: ask one agent per group per question, take best across groups
        # This simulates cross-group federation: each group's representative answers
        per_q = {}
        per_cat = defaultdict(list)
        for q in questions:
            best_score = 0.0
            for gn, members in groups.items():
                # Query one representative from each group
                representative = members[0]
                texts = query_agent(client, domain_agents[representative], q.text, limit=50)
                s = score_question(q, texts)
                if s > best_score:
                    best_score = s
            per_q[q.question_id] = best_score
            per_cat[q.category].append(best_score)

        overall = sum(per_q.values()) / len(per_q) if per_q else 0.0
        print(f"    Overall: {overall:.1%}")

        return {
            "mode": "azure-federated",
            "agents": len(agent_ids),
            "groups": num_groups,
            "agents_per_group": group_size,
            "facts": total,
            "overall": round(overall, 4),
            "per_category": {c: round(sum(ss) / len(ss), 4) for c, ss in per_cat.items()},
            "per_question": {qid: round(v, 4) for qid, v in per_q.items()},
        }

    # Unknown mode
    return {"mode": mode, "error": f"Unknown mode: {mode}"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Azure long-horizon eval")
    parser.add_argument("--turns", type=int, default=1000)
    parser.add_argument("--questions", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--resource-group", type=str, default="hive-mind-eval-rg")
    parser.add_argument(
        "--mode", type=str, default="all", choices=["all", "single", "flat", "federated"]
    )
    parser.add_argument(
        "--propagation-wait",
        type=int,
        default=45,
        help="Seconds to wait for Service Bus propagation",
    )
    parser.add_argument(
        "--output", type=str, default="experiments/hive_mind/eval_results_azure_long_horizon.json"
    )
    args = parser.parse_args()

    # Generate data
    print(f"Generating {args.turns}-turn dialogue...")
    ground_truth = generate_dialogue(num_turns=args.turns, seed=args.seed)
    questions = generate_questions(ground_truth, num_questions=args.questions)
    print(f"  {len(ground_truth.turns)} turns, {len(questions)} questions")

    # Discover agents
    print(f"\nDiscovering agents in {args.resource_group}...")
    agents = discover_agents(args.resource_group)
    domain_agents = {k: v for k, v in agents.items() if k != "adversary"}
    print(f"  Found {len(domain_agents)} domain agents")

    if not domain_agents:
        print("ERROR: No agents found")
        sys.exit(1)

    agent_ids = sorted(domain_agents.keys())
    client = httpx.Client()

    # Health check
    print("\nHealth check...")
    healthy = 0
    for aid in agent_ids:
        try:
            resp = client.get(f"{domain_agents[aid]}/health", timeout=10.0)
            if resp.status_code == 200:
                healthy += 1
        except Exception:
            pass
    print(f"  {healthy}/{len(agent_ids)} healthy")

    # Run modes
    modes = ["single", "flat", "federated"] if args.mode == "all" else [args.mode]
    all_results = []

    for mode in modes:
        t0 = time.time()
        result = run_azure_mode(
            mode, ground_truth, questions, domain_agents, client, args.propagation_wait
        )
        result["elapsed_seconds"] = round(time.time() - t0, 1)
        all_results.append(result)

    # Print comparison
    categories = sorted(set(q.category for q in questions))
    print(f"\n{'=' * 60}")
    print("  AZURE LONG-HORIZON EVAL RESULTS")
    print(f"{'=' * 60}")

    print(f"\n  {'Mode':<20s} {'Agents':>7s} {'Overall':>9s}")
    print(f"  {'-' * 38}")
    for r in all_results:
        print(f"  {r['mode']:<20s} {r['agents']:>7d} {r['overall']:>8.1%}")

    print(f"\n  {'Category':<28s}", end="")
    for r in all_results:
        print(f" {r['mode'][:12]:>12s}", end="")
    print()
    print(f"  {'-' * (28 + 13 * len(all_results))}")
    for cat in categories:
        print(f"  {cat:<28s}", end="")
        for r in all_results:
            val = r["per_category"].get(cat, 0.0)
            print(f" {val:>11.1%}", end="")
        print()

    # Save
    output = {
        "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": "azure",
        "resource_group": args.resource_group,
        "config": {
            "turns": args.turns,
            "questions": args.questions,
            "seed": args.seed,
            "propagation_wait_seconds": args.propagation_wait,
        },
        "results": all_results,
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to: {args.output}")

    client.close()


if __name__ == "__main__":
    main()
