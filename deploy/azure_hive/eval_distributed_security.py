#!/usr/bin/env python3
"""Distributed security log eval — MDE telemetry across 100 agents.

Same interface as eval_distributed.py but uses SecurityLogEval instead
of LongHorizonMemoryEval. The RemoteAgentAdapter transparently distributes
events across agents via Event Hubs.

Usage:
    python deploy/azure_hive/eval_distributed_security.py \
        --connection-string "$EH_CONN" \
        --input-hub hive-events-amplihive100 \
        --response-hub eval-responses-amplihive100 \
        --turns 50000 --questions 100 --campaigns 12 \
        --agents 100 --output results.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# Suppress EH noise
for name in ["azure", "azure.eventhub", "azure.eventhub._pyamqp", "uamqp"]:
    logging.getLogger(name).setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("eval_distributed_security")


def main():
    p = argparse.ArgumentParser(description="Distributed MDE security log eval")
    p.add_argument("--connection-string", required=True)
    p.add_argument("--input-hub", default="hive-events")
    p.add_argument("--response-hub", default="eval-responses")
    p.add_argument("--turns", type=int, default=50000)
    p.add_argument("--questions", type=int, default=100)
    p.add_argument("--campaigns", type=int, default=12)
    p.add_argument("--agents", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--answer-timeout", type=int, default=0)
    p.add_argument("--replicate-learn-to-all-agents", action="store_true")
    p.add_argument("--question-failover-retries", type=int, default=0)
    p.add_argument("--output", default="")
    args = p.parse_args()

    from remote_agent_adapter import RemoteAgentAdapter

    from amplihack.eval.security_log_eval import SecurityLogEval

    adapter = RemoteAgentAdapter(
        connection_string=args.connection_string,
        input_hub=args.input_hub,
        response_hub=args.response_hub,
        agent_count=args.agents,
        answer_timeout=args.answer_timeout,
        replicate_learning_to_all_agents=args.replicate_learn_to_all_agents,
        question_failover_retries=args.question_failover_retries,
    )

    eval_harness = SecurityLogEval(
        num_turns=args.turns,
        num_questions=args.questions,
        num_campaigns=args.campaigns,
        seed=args.seed,
    )

    try:
        report = eval_harness.run(adapter)
    finally:
        adapter.close()

    output_path = args.output or f"/tmp/security_eval_distributed_{args.seed}.json"
    report_dict = report.to_dict()
    report_dict["agent_count"] = args.agents
    report_dict["input_hub"] = args.input_hub
    report_dict["replicate_learn_to_all_agents"] = args.replicate_learn_to_all_agents
    report_dict["question_failover_retries"] = args.question_failover_retries
    Path(output_path).write_text(json.dumps(report_dict, indent=2))
    logger.info("Report written to %s", output_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
