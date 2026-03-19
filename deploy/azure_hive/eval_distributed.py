#!/usr/bin/env python3
"""Distributed eval — uses the EXACT same eval harness as single-agent.

Creates a RemoteAgentAdapter that forwards learn_from_content() and
answer_question() to deployed Azure Container Apps agents via Event Hubs.
Passes it to LongHorizonMemoryEval.run() — identical code path, grading,
and report format as single-agent eval.

The agent's OODA loop processes all inputs normally. The adapter is pure DI.

Usage:
    python deploy/azure_hive/eval_distributed.py \
        --connection-string "$EH_CONN" \
        --input-hub hive-events-amplihiveeval \
        --response-hub eval-responses-amplihiveeval \
        --turns 5000 --questions 50 \
        --agents 5 \
        --grader-model claude-haiku-4-5-20251001 \
        --output results.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("eval_distributed")


def _scale_aware_defaults(agents: int) -> dict:
    """Return scale-aware defaults for >=100 agent runs.

    At 100+ agents the distributed correctness requirements change:
    - PARALLEL_WORKERS=1: serialise question dispatch to avoid answer-to-wrong-question
      correlation races under high concurrency.
    - HIVE_MEMORY_QUERY_FANOUT=agents: fan out to ALL shards, not the default 5.
    - HIVE_SHARD_QUERY_TIMEOUT_SECONDS=0: infinite shard wait so slow shards don't
      silently produce partial-hive answers (EventHubsShardTransport converts 0→None).
    - answer_timeout=0: no eval-level answer timeout so late answers aren't discarded.
    - question_failover_retries=2: 3 total attempts covering transport misses and
      semantic abstentions on the wrong shard.
    - replicate_learn_to_all_agents=True: every agent learns every turn so any agent
      can answer any question (no shard-miss silent failures).
    """
    if agents >= 100:
        return {
            "parallel_workers": 1,
            "hive_fanout": agents,
            "hive_shard_timeout": 0,
            "answer_timeout": 0,
            "question_failover_retries": 2,
            "replicate_learn_to_all_agents": True,
        }
    if agents >= 50:
        return {
            "parallel_workers": 2,
            "hive_fanout": agents,
            "hive_shard_timeout": 0,
            "answer_timeout": 0,
            "question_failover_retries": 2,
            "replicate_learn_to_all_agents": True,
        }
    return {
        "parallel_workers": 4,
        "hive_fanout": agents,
        "hive_shard_timeout": 30,
        "answer_timeout": 0,
        "question_failover_retries": 1,
        "replicate_learn_to_all_agents": False,
    }


def main():
    p = argparse.ArgumentParser(
        description="Distributed eval — same harness as single-agent, remote agents via Event Hubs"
    )
    p.add_argument(
        "--connection-string", required=True, help="Event Hubs namespace connection string"
    )
    p.add_argument("--input-hub", default="hive-events", help="Agent input Event Hub name")
    p.add_argument("--response-hub", default="eval-responses", help="Eval response Event Hub name")
    p.add_argument("--turns", type=int, default=300, help="Dialogue turns")
    p.add_argument("--questions", type=int, default=50, help="Number of questions")
    p.add_argument("--agents", type=int, default=5, help="Number of deployed agents")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    p.add_argument("--grader-model", default="claude-haiku-4-5-20251001")
    p.add_argument("--resource-group", default="", help="Azure resource group (optional, unused)")
    p.add_argument(
        "--answer-timeout",
        type=int,
        default=None,
        help="Seconds to wait per answer (0=no timeout; default: scale-aware per --agents)",
    )
    p.add_argument("--output", default="", help="Output JSON path")
    p.add_argument(
        "--replicate-learn-to-all-agents",
        action="store_true",
        default=None,
        help=(
            "Replicate each learn_from_content call to ALL agents (default: True for >=50 agents)"
        ),
    )
    p.add_argument(
        "--question-failover-retries",
        type=int,
        default=None,
        help="Number of failover retries for unanswered/abstention questions (default: scale-aware)",
    )
    args = p.parse_args()

    # Apply scale-aware defaults — CLI flags override when explicitly supplied
    defaults = _scale_aware_defaults(args.agents)
    answer_timeout = (
        args.answer_timeout if args.answer_timeout is not None else defaults["answer_timeout"]
    )
    replicate = (
        args.replicate_learn_to_all_agents
        if args.replicate_learn_to_all_agents is not None
        else defaults["replicate_learn_to_all_agents"]
    )
    failover_retries = (
        args.question_failover_retries
        if args.question_failover_retries is not None
        else defaults["question_failover_retries"]
    )

    # Propagate hive settings via environment so AppHost agents pick them up
    if "HIVE_MEMORY_QUERY_FANOUT" not in os.environ:
        os.environ["HIVE_MEMORY_QUERY_FANOUT"] = str(defaults["hive_fanout"])
    if "HIVE_SHARD_QUERY_TIMEOUT_SECONDS" not in os.environ:
        os.environ["HIVE_SHARD_QUERY_TIMEOUT_SECONDS"] = str(defaults["hive_shard_timeout"])
    if "PARALLEL_WORKERS" not in os.environ:
        os.environ["PARALLEL_WORKERS"] = str(defaults["parallel_workers"])

    logger.info(
        "Scale-aware defaults for %d agents: PARALLEL_WORKERS=%s, HIVE_MEMORY_QUERY_FANOUT=%s, "
        "HIVE_SHARD_QUERY_TIMEOUT_SECONDS=%s, answer_timeout=%s, failover_retries=%s, replicate=%s",
        args.agents,
        os.environ["PARALLEL_WORKERS"],
        os.environ["HIVE_MEMORY_QUERY_FANOUT"],
        os.environ["HIVE_SHARD_QUERY_TIMEOUT_SECONDS"],
        answer_timeout,
        failover_retries,
        replicate,
    )

    # Import the adapter and the eval harness
    from remote_agent_adapter import RemoteAgentAdapter

    from amplihack.eval.long_horizon_memory import LongHorizonMemoryEval, _print_report

    # Create the remote adapter — same interface as LearningAgent
    adapter = RemoteAgentAdapter(
        connection_string=args.connection_string,
        input_hub=args.input_hub,
        response_hub=args.response_hub,
        agent_count=args.agents,
        resource_group=args.resource_group,
        answer_timeout=answer_timeout,
        replicate_learning_to_all_agents=replicate,
        question_failover_retries=failover_retries,
    )

    # Create the eval harness — IDENTICAL to single-agent
    eval_harness = LongHorizonMemoryEval(
        num_turns=args.turns,
        num_questions=args.questions,
        seed=args.seed,
    )

    # Run — same code path as: python -m amplihack.eval.long_horizon_memory
    try:
        report = eval_harness.run(adapter, grader_model=args.grader_model)
    finally:
        adapter.close()

    # Print report (same format)
    _print_report(report)

    # Write output
    output_path = args.output or f"/tmp/distributed_eval_{args.seed}.json"
    report_dict = report.to_dict()
    report_dict["eval_type"] = "distributed"
    report_dict["agent_count"] = args.agents
    report_dict["input_hub"] = args.input_hub
    Path(output_path).write_text(json.dumps(report_dict, indent=2))
    logger.info("Report written to %s", output_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
