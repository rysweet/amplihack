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
        --agents 100 \
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

from amplihack.observability import configure_otel, start_span

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("eval_distributed")


def _default_agent_count() -> int:
    raw = os.environ.get("AMPLIHACK_AGENT_COUNT") or os.environ.get("HIVE_AGENT_COUNT")
    if raw:
        try:
            return int(raw)
        except ValueError:
            logger.warning("Ignoring invalid agent count override: %s", raw)

    return 10 if os.environ.get("HIVE_DEPLOYMENT_PROFILE", "").strip() == "smoke-10" else 100


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
    p.add_argument(
        "--agents", type=int, default=_default_agent_count(), help="Number of deployed agents"
    )
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    p.add_argument("--grader-model", default="claude-haiku-4-5-20251001")
    p.add_argument("--resource-group", default="", help="Azure resource group (optional, unused)")
    p.add_argument(
        "--answer-timeout", type=int, default=0, help="Seconds to wait per answer (0=no timeout)"
    )
    p.add_argument("--output", default="", help="Output JSON path")
    p.add_argument(
        "--replicate-learn-to-all-agents",
        action="store_true",
        default=False,
        help="Replicate each learn_from_content call to ALL agents (not just one per round-robin)",
    )
    p.add_argument(
        "--question-failover-retries",
        type=int,
        default=0,
        help="Number of failover retries for unanswered questions (retry on next agent)",
    )
    args = p.parse_args()

    configure_otel(
        service_name=os.environ.get("OTEL_SERVICE_NAME", "").strip()
        or "amplihack.azure-eval-harness",
        component="eval-distributed",
        attributes={
            "amplihack.agent_count": args.agents,
            "amplihack.turns": args.turns,
            "amplihack.questions": args.questions,
        },
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
        answer_timeout=args.answer_timeout,
        replicate_learning_to_all_agents=args.replicate_learn_to_all_agents,
        question_failover_retries=args.question_failover_retries,
    )

    # Create the eval harness — IDENTICAL to single-agent
    eval_harness = LongHorizonMemoryEval(
        num_turns=args.turns,
        num_questions=args.questions,
        seed=args.seed,
    )

    # Run — same code path as: python -m amplihack.eval.long_horizon_memory
    try:
        with start_span(
            "azure_eval.run_long_horizon",
            tracer_name=__name__,
            attributes={
                "amplihack.agent_count": args.agents,
                "amplihack.turns": args.turns,
                "amplihack.questions": args.questions,
            },
        ):
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
