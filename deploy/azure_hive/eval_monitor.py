#!/usr/bin/env python3
"""Compatibility wrapper for EvalMonitor now living in amplihack-agent-eval."""

from __future__ import annotations

import argparse
import os
import signal
import sys
from typing import Any

from amplihack_eval.azure.eval_monitor import EvalMonitor


def main() -> int:
    p = argparse.ArgumentParser(description="Real-time distributed eval monitoring via Event Hubs")
    p.add_argument("--connection-string", default=os.environ.get("EH_CONN", ""))
    p.add_argument(
        "--response-hub",
        default=os.environ.get(
            "AMPLIHACK_EH_RESPONSE_HUB",
            f"eval-responses-{os.environ.get('HIVE_NAME', 'amplihive')}",
        ),
    )
    p.add_argument(
        "--consumer-group",
        default=os.environ.get("AMPLIHACK_EVAL_MONITOR_CONSUMER_GROUP", "eval-monitor"),
    )
    p.add_argument(
        "--agents",
        type=int,
        default=int(os.environ.get("HIVE_AGENT_COUNT", "100")),
    )
    p.add_argument("--output", default="eval_monitor_progress.json")
    p.add_argument("--wait-for-online", type=int, default=0)
    p.add_argument("--wait-for-ready", type=int, default=0)
    p.add_argument("--wait-for-progress", type=int, default=0)
    p.add_argument("--wait-for-answers", type=int, default=0)
    p.add_argument("--max-wait-seconds", type=int, default=0)
    args = p.parse_args()

    if not args.connection_string:
        print("--connection-string or EH_CONN is required", file=sys.stderr)
        return 1

    monitor = EvalMonitor(
        connection_string=args.connection_string,
        response_hub=args.response_hub,
        consumer_group=args.consumer_group,
        agent_count=args.agents,
        output_path=args.output,
    )

    def _sigterm(*_: Any) -> None:
        monitor.stop()

    signal.signal(signal.SIGTERM, _sigterm)
    if any(
        (args.wait_for_online, args.wait_for_ready, args.wait_for_progress, args.wait_for_answers)
    ):
        max_wait_seconds = args.max_wait_seconds or 120
        return monitor.wait_for_criteria(
            min_online=args.wait_for_online,
            min_ready=args.wait_for_ready,
            min_progress_agents=args.wait_for_progress,
            min_answers=args.wait_for_answers,
            max_wait_seconds=max_wait_seconds,
        )

    monitor.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
