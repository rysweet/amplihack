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


def main() -> None:
    parser = argparse.ArgumentParser(description="Azure long-horizon eval")
    parser.add_argument("--turns", type=int, default=1000)
    parser.add_argument("--questions", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--resource-group", type=str, default="hive-mind-eval-rg")
    parser.add_argument(
        "--propagation-wait",
        type=int,
        default=30,
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
    # Filter out adversary for teaching
    domain_agents = {k: v for k, v in agents.items() if k != "adversary"}
    print(f"  Found {len(domain_agents)} domain agents + adversary")

    if not domain_agents:
        print("ERROR: No agents found")
        sys.exit(1)

    agent_ids = sorted(domain_agents.keys())
    client = httpx.Client()

    # Phase 1: Health check
    print("\nPhase 1: Health check...")
    healthy = 0
    for aid in agent_ids:
        try:
            resp = client.get(f"{domain_agents[aid]}/health", timeout=10.0)
            if resp.status_code == 200:
                healthy += 1
        except Exception:
            pass
    print(f"  {healthy}/{len(agent_ids)} healthy")

    # Phase 2: Teach facts — distribute turns round-robin across agents
    print(f"\nPhase 2: Teaching {len(ground_truth.turns)} turns across {len(agent_ids)} agents...")
    t0 = time.time()
    total_taught = 0

    # Group turns by target agent
    agent_facts: dict[str, list[dict]] = defaultdict(list)
    for i, turn in enumerate(ground_truth.turns):
        aid = agent_ids[i % len(agent_ids)]
        # Structured facts
        for fact in turn.facts:
            content = (
                f"{fact.get('entity', '')}: {fact.get('attribute', '')} = {fact.get('value', '')}"
            )
            agent_facts[aid].append(
                {
                    "concept": turn.block_name,
                    "content": content,
                    "confidence": 0.9,
                }
            )
        # Raw turn content
        agent_facts[aid].append(
            {
                "concept": turn.block_name,
                "content": turn.content,
                "confidence": 0.85,
            }
        )

    # Send in batches
    for aid in agent_ids:
        facts = agent_facts[aid]
        if not facts:
            continue
        # Send in chunks of 50
        for i in range(0, len(facts), 50):
            chunk = facts[i : i + 50]
            count = teach_agent(client, domain_agents[aid], aid, chunk)
            total_taught += count

    elapsed = time.time() - t0
    print(f"  Taught {total_taught} facts in {elapsed:.1f}s")
    print("  Each fact published to Azure Service Bus for cross-agent propagation")

    # Phase 3: Wait for Service Bus propagation
    print(f"\nPhase 3: Waiting {args.propagation_wait}s for Service Bus propagation...")
    time.sleep(args.propagation_wait)

    # Check propagation by looking at stats
    print("  Checking propagation status...")
    for aid in agent_ids[:3]:  # Sample 3 agents
        stats = get_agent_stats(client, domain_agents[aid])
        own_facts = len(agent_facts.get(aid, []))
        total_facts = stats.get("fact_count", 0)
        received = total_facts - own_facts
        print(f"    {aid}: own={own_facts}, total={total_facts}, received_via_bus={received}")

    # Phase 4: Query all agents
    print(f"\nPhase 4: Querying {len(questions)} questions across agents...")
    t0 = time.time()

    per_q: dict[str, float] = {}
    per_cat: dict[str, list[float]] = defaultdict(list)

    for q in questions:
        # Query multiple agents and take best score (any agent can answer)
        best_score = 0.0
        for aid in agent_ids[:5]:  # Query 5 agents per question
            texts = query_agent(client, domain_agents[aid], q.text, limit=50)
            s = score_question(q, texts)
            if s > best_score:
                best_score = s

        per_q[q.question_id] = best_score
        per_cat[q.category].append(best_score)

    overall = sum(per_q.values()) / len(per_q) if per_q else 0.0
    cat_avg = {c: sum(ss) / len(ss) for c, ss in per_cat.items()}

    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.1f}s. Overall: {overall:.1%}")

    # Phase 5: Results
    categories = sorted(cat_avg.keys())
    print(f"\n{'=' * 60}")
    print("  AZURE LONG-HORIZON EVAL RESULTS")
    print(f"{'=' * 60}")
    print(f"  Agents: {len(agent_ids)}")
    print(f"  Facts taught: {total_taught}")
    print(f"  Questions: {len(questions)}")
    print(f"  Overall: {overall:.1%}")
    print(f"\n  {'Category':<28s} {'Score':>8s}")
    print(f"  {'-' * 38}")
    for cat in categories:
        print(f"  {cat:<28s} {cat_avg[cat]:>7.1%}")

    # Collect final stats
    all_stats = {}
    for aid in agent_ids:
        all_stats[aid] = get_agent_stats(client, domain_agents[aid])

    # Save results
    output = {
        "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": "azure",
        "resource_group": args.resource_group,
        "config": {
            "turns": args.turns,
            "questions": args.questions,
            "seed": args.seed,
            "agents": len(agent_ids),
            "propagation_wait_seconds": args.propagation_wait,
        },
        "results": {
            "overall": round(overall, 4),
            "per_category": {c: round(v, 4) for c, v in cat_avg.items()},
            "per_question": {qid: round(v, 4) for qid, v in per_q.items()},
        },
        "agent_stats": all_stats,
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to: {args.output}")

    client.close()


if __name__ == "__main__":
    main()
