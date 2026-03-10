#!/usr/bin/env python3
"""Distributed eval — uses the EXACT same eval harness as single-agent.

Creates a RemoteAgentAdapter that forwards learn_from_content() and
answer_question() to deployed Azure Container Apps agents via Service Bus.
Passes it to LongHorizonMemoryEval.run() — identical code path, grading,
and report format as single-agent eval.

The agent's OODA loop processes all inputs normally. The adapter is pure DI.

Usage:
    python deploy/azure_hive/eval_distributed.py \
        --connection-string "$SB_CONN" \
        --input-topic hive-events-amplihivev8 \
        --response-topic eval-responses-amplihivev8 \
        --turns 5000 --questions 50 \
        --agents 100 \
        --grader-model claude-haiku-4-5-20251001 \
        --output results.json
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("eval_distributed")


def main():
    p = argparse.ArgumentParser(
        description="Distributed eval — same harness as single-agent, remote agents via Service Bus"
    )
    p.add_argument("--connection-string", required=True, help="Service Bus connection string")
    p.add_argument("--input-topic", default="hive-events", help="Agent input topic")
    p.add_argument("--response-topic", default="eval-responses", help="Eval response topic")
    p.add_argument("--turns", type=int, default=300, help="Dialogue turns")
    p.add_argument("--questions", type=int, default=50, help="Number of questions")
    p.add_argument("--agents", type=int, default=100, help="Number of deployed agents")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    p.add_argument("--grader-model", default="claude-haiku-4-5-20251001")
    p.add_argument("--answer-timeout", type=float, default=600, help="Seconds to wait per answer")
    p.add_argument("--output", default="", help="Output JSON path")
    args = p.parse_args()

    # Import the adapter and the eval harness
    from remote_agent_adapter import RemoteAgentAdapter
    from amplihack.eval.long_horizon_memory import LongHorizonMemoryEval, _print_report

    # Create the remote adapter — same interface as LearningAgent
    adapter = RemoteAgentAdapter(
        connection_string=args.connection_string,
        input_topic=args.input_topic,
        response_topic=args.response_topic,
        agent_count=args.agents,
        answer_timeout=args.answer_timeout,
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
    import json
    from pathlib import Path
    report_dict = report.to_dict()
    report_dict["eval_type"] = "distributed"
    report_dict["agent_count"] = args.agents
    report_dict["input_topic"] = args.input_topic
    Path(output_path).write_text(json.dumps(report_dict, indent=2))
    logger.info("Report written to %s", output_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
