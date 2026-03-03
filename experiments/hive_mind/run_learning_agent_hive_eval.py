# pyright: reportMissingImports=false
#!/usr/bin/env python3
"""LearningAgent-based hive mind evaluation.

Uses REAL LLM-backed LearningAgent (not keyword matching) to evaluate
whether distributed hive mind sharing improves agent performance.

Three conditions:
  SINGLE     - 1 LearningAgent, own Kuzu DB, no hive
  HIVE_FLAT  - N LearningAgents, each with own Kuzu DB + shared InMemoryHiveGraph
  HIVE_FED   - N LearningAgents, M groups, federation tree

Each condition uses the amplihack-agent-eval framework:
  - Deterministic data generation (generate_dialogue / generate_questions)
  - Real LLM fact extraction (learn_from_content → 3 LLM calls per turn)
  - Real LLM answer synthesis (answer_question → 2 LLM calls per question)
  - Hybrid grading (deterministic rubric + LLM judgment)

Expected timing (100 turns, 20 questions, Sonnet):
  ~5-10 min per condition, ~15-30 min total for all 3 conditions.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Ensure paths
_MEMORY_LIB_PATH = os.environ.get("AMPLIHACK_MEMORY_LIB_PATH", "")
if _MEMORY_LIB_PATH and _MEMORY_LIB_PATH not in sys.path:
    sys.path.insert(0, _MEMORY_LIB_PATH)

_SRC_PATH = os.environ.get("AMPLIHACK_SRC_PATH", "")
if _SRC_PATH and _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

from amplihack_eval.adapters.base import AgentAdapter, AgentResponse
from amplihack_eval.core.runner import EvalReport, EvalRunner

from amplihack.agents.goal_seeking.hive_mind.hive_graph import InMemoryHiveGraph
from amplihack.agents.goal_seeking.learning_agent import LearningAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hive_eval")


# ---------------------------------------------------------------------------
# Adapter: wraps LearningAgent for EvalRunner compatibility
# ---------------------------------------------------------------------------


class HiveLearningAgentAdapter(AgentAdapter):
    """Wraps a LearningAgent with optional hive_store for eval harness."""

    def __init__(
        self,
        agent_name: str,
        model: str,
        storage_path: Path,
        hive_store: Any | None = None,
        prompt_variant: int | None = None,
    ):
        kwargs: dict[str, Any] = {}
        if prompt_variant is not None:
            kwargs["prompt_variant"] = prompt_variant
        self._agent = LearningAgent(
            agent_name=agent_name,
            model=model,
            storage_path=storage_path,
            use_hierarchical=True,
            hive_store=hive_store,
            **kwargs,
        )
        self._model = model

    def learn(self, content: str) -> None:
        self._agent.learn_from_content(content)

    def answer(self, question: str) -> AgentResponse:
        try:
            result = self._agent.answer_question(question)
            text = result[0] if isinstance(result, tuple) else result
            return AgentResponse(answer=str(text), metadata={"model": self._model})
        except Exception as e:
            logger.warning("Answer failed: %s", e)
            return AgentResponse(answer=f"Error: {e}")

    def reset(self) -> None:
        self.close()

    def close(self) -> None:
        if hasattr(self._agent, "close"):
            self._agent.close()

    def get_memory_stats(self) -> dict[str, Any]:
        try:
            return self._agent.get_memory_stats()
        except Exception:
            logger.debug("get_memory_stats failed", exc_info=True)
            return {}

    @property
    def name(self) -> str:
        return f"HiveLearningAgent({self._agent.agent_name})"


# ---------------------------------------------------------------------------
# Multi-agent adapter: distributes turns round-robin, queries best agent
# ---------------------------------------------------------------------------


class MultiAgentHiveAdapter(AgentAdapter):
    """N LearningAgents sharing a hive, presented as a single AgentAdapter.

    Learning: turns distributed round-robin across agents.
    Answering: queries ALL agents, returns the longest non-error answer
    (heuristic: longer = more synthesized = better).
    """

    def __init__(self, agents: list[LearningAgent], model: str):
        self._agents = agents
        self._model = model
        self._turn_idx = 0

    def learn(self, content: str) -> None:
        agent = self._agents[self._turn_idx % len(self._agents)]
        agent.learn_from_content(content)
        self._turn_idx += 1

    def answer(self, question: str) -> AgentResponse:
        best_answer = ""
        for agent in self._agents:
            try:
                result = agent.answer_question(question)
                text = result[0] if isinstance(result, tuple) else str(result)
                if len(text) > len(best_answer) and not text.startswith("Error:"):
                    best_answer = text
            except Exception as e:
                logger.debug("Agent %s failed: %s", agent.agent_name, e)
        if not best_answer:
            best_answer = "No agent could answer"
        return AgentResponse(answer=best_answer, metadata={"model": self._model})

    def reset(self) -> None:
        self.close()

    def close(self) -> None:
        for agent in self._agents:
            if hasattr(agent, "close"):
                agent.close()

    def get_memory_stats(self) -> dict[str, Any]:
        stats: dict[str, Any] = {}
        for agent in self._agents:
            try:
                s = agent.get_memory_stats()
                stats[agent.agent_name] = s
            except Exception:
                logger.debug("get_memory_stats failed for %s", agent.agent_name, exc_info=True)
        return stats

    @property
    def name(self) -> str:
        return f"MultiAgent({len(self._agents)} agents)"


# ---------------------------------------------------------------------------
# Condition runners
# ---------------------------------------------------------------------------


@dataclass
class ConditionResult:
    mode: str
    num_agents: int
    report: EvalReport
    elapsed_s: float
    hive_facts: int = 0


def run_single(
    model: str,
    num_turns: int,
    num_questions: int,
    seed: int,
    tmpdir: str,
    parallel_workers: int = 5,
    prompt_variant: int | None = None,
) -> ConditionResult:
    """Run SINGLE condition: 1 LearningAgent, no hive."""
    logger.info("=== SINGLE: 1 agent, no hive ===")
    t0 = time.time()

    storage = Path(tmpdir) / "single"
    adapter = HiveLearningAgentAdapter(
        agent_name="single_agent",
        model=model,
        storage_path=storage,
        prompt_variant=prompt_variant,
    )

    runner = EvalRunner(
        num_turns=num_turns,
        num_questions=num_questions,
        seed=seed,
        parallel_workers=parallel_workers,
    )
    report = runner.run(adapter, grader_model=model)
    elapsed = time.time() - t0

    adapter.close()
    logger.info("SINGLE done: %.2f%% in %.1fs", report.overall_score * 100, elapsed)
    return ConditionResult(mode="single", num_agents=1, report=report, elapsed_s=elapsed)


def run_flat(
    model: str,
    num_agents: int,
    num_turns: int,
    num_questions: int,
    seed: int,
    tmpdir: str,
    parallel_workers: int = 5,
    prompt_variant: int | None = None,
) -> ConditionResult:
    """Run HIVE_FLAT: N agents sharing a single InMemoryHiveGraph."""
    logger.info("=== HIVE_FLAT: %d agents, shared hive ===", num_agents)
    t0 = time.time()

    from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

    try:
        embedder = EmbeddingGenerator()
        if not embedder.available:
            embedder = None
    except Exception:
        logger.debug("EmbeddingGenerator init failed (flat)", exc_info=True)
        embedder = None

    hive = InMemoryHiveGraph(
        "flat-hive",
        embedding_generator=embedder,
        enable_gossip=True,
        enable_ttl=True,
    )

    agents: list[LearningAgent] = []
    for i in range(num_agents):
        name = f"flat_agent_{i}"
        hive.register_agent(name)
        kwargs: dict[str, Any] = {}
        if prompt_variant is not None:
            kwargs["prompt_variant"] = prompt_variant
        agent = LearningAgent(
            agent_name=name,
            model=model,
            storage_path=Path(tmpdir) / f"flat_{i}",
            use_hierarchical=True,
            hive_store=hive,
            **kwargs,
        )
        agents.append(agent)

    adapter = MultiAgentHiveAdapter(agents, model)

    runner = EvalRunner(
        num_turns=num_turns,
        num_questions=num_questions,
        seed=seed,
        parallel_workers=parallel_workers,
    )
    report = runner.run(adapter, grader_model=model)
    elapsed = time.time() - t0

    hive_stats = hive.get_stats()
    hive_facts = hive_stats.get("fact_count", 0)

    adapter.close()
    logger.info(
        "HIVE_FLAT done: %.2f%% in %.1fs (hive facts: %d)",
        report.overall_score * 100,
        elapsed,
        hive_facts,
    )
    return ConditionResult(
        mode="flat",
        num_agents=num_agents,
        report=report,
        elapsed_s=elapsed,
        hive_facts=hive_facts,
    )


def run_federated(
    model: str,
    num_agents: int,
    num_groups: int,
    num_turns: int,
    num_questions: int,
    seed: int,
    tmpdir: str,
    parallel_workers: int = 5,
    prompt_variant: int | None = None,
) -> ConditionResult:
    """Run HIVE_FEDERATED: N agents in M groups with federation tree."""
    logger.info("=== HIVE_FEDERATED: %d agents, %d groups ===", num_agents, num_groups)
    t0 = time.time()

    from amplihack.agents.goal_seeking.hive_mind.embeddings import EmbeddingGenerator

    try:
        embedder = EmbeddingGenerator()
        if not embedder.available:
            embedder = None
    except Exception:
        logger.debug("EmbeddingGenerator init failed (federated)", exc_info=True)
        embedder = None

    # Create federation tree: root hive with M group hives as children
    root_hive = InMemoryHiveGraph(
        "root-hive",
        embedding_generator=embedder,
        enable_gossip=True,
        enable_ttl=True,
    )
    group_hives: list[InMemoryHiveGraph] = []
    for g in range(num_groups):
        group_hive = InMemoryHiveGraph(
            f"group-{g}",
            embedding_generator=embedder,
            enable_gossip=True,
            enable_ttl=True,
        )
        group_hive.set_parent(root_hive)
        root_hive.add_child(group_hive)
        group_hives.append(group_hive)

    agents_per_group = max(1, num_agents // num_groups)
    agents: list[LearningAgent] = []
    agent_idx = 0

    for g, group_hive in enumerate(group_hives):
        n = agents_per_group if g < num_groups - 1 else num_agents - agent_idx
        for _ in range(n):
            name = f"fed_agent_{agent_idx}"
            group_hive.register_agent(name)
            kwargs: dict[str, Any] = {}
            if prompt_variant is not None:
                kwargs["prompt_variant"] = prompt_variant
            agent = LearningAgent(
                agent_name=name,
                model=model,
                storage_path=Path(tmpdir) / f"fed_{agent_idx}",
                use_hierarchical=True,
                hive_store=group_hive,
                **kwargs,
            )
            agents.append(agent)
            agent_idx += 1

    adapter = MultiAgentHiveAdapter(agents, model)

    runner = EvalRunner(
        num_turns=num_turns,
        num_questions=num_questions,
        seed=seed,
        parallel_workers=parallel_workers,
    )
    report = runner.run(adapter, grader_model=model)
    elapsed = time.time() - t0

    total_hive_facts = 0
    for hive in [root_hive, *group_hives]:
        stats = hive.get_stats()
        total_hive_facts += stats.get("fact_count", 0)

    adapter.close()
    logger.info(
        "HIVE_FEDERATED done: %.2f%% in %.1fs (total hive facts: %d)",
        report.overall_score * 100,
        elapsed,
        total_hive_facts,
    )
    return ConditionResult(
        mode="federated",
        num_agents=num_agents,
        report=report,
        elapsed_s=elapsed,
        hive_facts=total_hive_facts,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="LearningAgent-based hive mind evaluation")
    parser.add_argument("--turns", type=int, default=100, help="Dialogue turns")
    parser.add_argument("--questions", type=int, default=20, help="Quiz questions")
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("EVAL_MODEL", "claude-sonnet-4-5-20250929"),
        help="LLM model for agents and grading",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--agents", type=int, default=5, help="Number of agents for hive conditions"
    )
    parser.add_argument(
        "--groups", type=int, default=2, help="Number of groups for federated condition"
    )
    parser.add_argument(
        "--conditions",
        type=str,
        default="single,flat,federated",
        help="Comma-separated conditions to run",
    )
    parser.add_argument("--output", type=str, default="", help="Output JSON path")
    parser.add_argument(
        "--prompt-variant",
        type=int,
        default=None,
        help="Prompt variant number (1-5) for testing different system prompts",
    )
    parser.add_argument(
        "--parallel-workers",
        type=int,
        default=5,
        help="Parallel workers for Q&A grading",
    )
    args = parser.parse_args()

    conditions = [c.strip() for c in args.conditions.split(",")]

    logger.info("=" * 60)
    logger.info("LearningAgent Hive Mind Evaluation")
    logger.info(
        "Turns=%d, Questions=%d, Model=%s, Agents=%d, Groups=%d",
        args.turns,
        args.questions,
        args.model,
        args.agents,
        args.groups,
    )
    logger.info("Conditions: %s", conditions)
    logger.info("=" * 60)

    results: list[ConditionResult] = []

    with tempfile.TemporaryDirectory(prefix="hive_eval_") as tmpdir:
        if "single" in conditions:
            r = run_single(
                args.model,
                args.turns,
                args.questions,
                args.seed,
                tmpdir,
                args.parallel_workers,
                prompt_variant=args.prompt_variant,
            )
            results.append(r)

        if "flat" in conditions:
            r = run_flat(
                args.model,
                args.agents,
                args.turns,
                args.questions,
                args.seed,
                tmpdir,
                args.parallel_workers,
                prompt_variant=args.prompt_variant,
            )
            results.append(r)

        if "federated" in conditions:
            r = run_federated(
                args.model,
                args.agents,
                args.groups,
                args.turns,
                args.questions,
                args.seed,
                tmpdir,
                args.parallel_workers,
                prompt_variant=args.prompt_variant,
            )
            results.append(r)

    # Print summary
    print("\n" + "=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    print(f"{'Mode':<15} {'Agents':>7} {'Score':>8} {'Time':>8} {'Hive Facts':>11}")
    print("-" * 70)
    for r in results:
        print(
            f"{r.mode:<15} {r.num_agents:>7} "
            f"{r.report.overall_score:>7.1%} "
            f"{r.elapsed_s:>7.1f}s "
            f"{r.hive_facts:>11}"
        )
    print("=" * 70)

    # Category breakdown
    for r in results:
        print(f"\n--- {r.mode.upper()} Category Breakdown ---")
        for cb in r.report.category_breakdown:
            print(f"  {cb.category:<30} {cb.avg_score:>6.1%} ({cb.num_questions} qs)")

    # Save results
    output_path = args.output or f"eval_results_learning_agent_{int(time.time())}.json"
    output_data = {
        "config": {
            "turns": args.turns,
            "questions": args.questions,
            "model": args.model,
            "seed": args.seed,
            "agents": args.agents,
            "groups": args.groups,
            "prompt_variant": args.prompt_variant,
        },
        "results": [],
    }
    for r in results:
        output_data["results"].append(
            {
                "mode": r.mode,
                "num_agents": r.num_agents,
                "overall_score": round(r.report.overall_score, 4),
                "hive_facts": r.hive_facts,
                "elapsed_s": round(r.elapsed_s, 1),
                "learning_time_s": round(r.report.learning_time_s, 1),
                "questioning_time_s": round(r.report.questioning_time_s, 1),
                "grading_time_s": round(r.report.grading_time_s, 1),
                "category_breakdown": [
                    {
                        "category": cb.category,
                        "num_questions": cb.num_questions,
                        "avg_score": round(cb.avg_score, 4),
                    }
                    for cb in r.report.category_breakdown
                ],
                "per_question": [
                    {
                        "q": res.question_text[:100],
                        "expected": res.expected_answer[:100],
                        "actual": res.actual_answer[:200],
                        "score": round(res.overall_score, 4),
                    }
                    for res in r.report.results
                ],
            }
        )

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)
    logger.info("Results saved to %s", output_path)


if __name__ == "__main__":
    main()
