#!/usr/bin/env python3
"""Focused distributed retrieval smoke for Azure Event Hubs agents.

Learns one synthetic fact per agent via ``RemoteAgentAdapter.learn_from_content``
and then asks one cross-shard question per agent. Each question is routed to a
specific target agent but asks about a different agent's fact, so successful
answers require distributed retrieval rather than local-only memory.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Allow running from repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from amplihack.observability import configure_otel, start_span

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("eval_retrieval_smoke")


def _default_agent_count() -> int:
    raw = os.environ.get("AMPLIHACK_AGENT_COUNT") or os.environ.get("HIVE_AGENT_COUNT")
    if raw:
        try:
            return int(raw)
        except ValueError:
            logger.warning("Ignoring invalid agent count override: %s", raw)

    return 10 if os.environ.get("HIVE_DEPLOYMENT_PROFILE", "").strip() == "smoke-10" else 100


@dataclass(frozen=True)
class RetrievalSmokeCase:
    target_agent: int
    subject_agent: int
    expected_codename: str
    learn_text: str
    question: str


def build_retrieval_smoke_cases(agent_count: int, question_offset: int) -> list[RetrievalSmokeCase]:
    """Create one learn + cross-agent question case per agent."""
    if agent_count < 2:
        raise ValueError("agent_count must be at least 2 for distributed retrieval smoke")

    offset = question_offset % agent_count
    if offset == 0:
        offset = 1

    cases: list[RetrievalSmokeCase] = []
    for target_agent in range(agent_count):
        subject_agent = (target_agent + offset) % agent_count
        expected_codename = f"ORBIT-{subject_agent}"
        verification_token = f"CIPHER-{target_agent}"
        learn_text = (
            f"Retrieval smoke fact for agent {target_agent}. "
            f"The codename for smoke record {target_agent} is ORBIT-{target_agent}. "
            f"The verifier token for smoke record {target_agent} is {verification_token}. "
            "Remember these values exactly."
        )
        question = f"What is the codename for retrieval smoke record {subject_agent}?"
        cases.append(
            RetrievalSmokeCase(
                target_agent=target_agent,
                subject_agent=subject_agent,
                expected_codename=expected_codename,
                learn_text=learn_text,
                question=question,
            )
        )
    return cases


def answer_contains_expected(answer: str, expected_codename: str) -> bool:
    """Return whether the answer contains the expected codename."""
    return expected_codename.casefold() in answer.casefold()


def main() -> int:
    p = argparse.ArgumentParser(
        description="Focused distributed retrieval smoke against Azure hive agents"
    )
    p.add_argument(
        "--connection-string", required=True, help="Event Hubs namespace connection string"
    )
    p.add_argument("--input-hub", default="hive-events", help="Agent input Event Hub name")
    p.add_argument("--response-hub", default="eval-responses", help="Eval response Event Hub name")
    p.add_argument(
        "--agents", type=int, default=_default_agent_count(), help="Number of deployed agents"
    )
    p.add_argument("--resource-group", default="", help="Azure resource group (optional)")
    p.add_argument("--answer-timeout", type=int, default=120, help="Seconds to wait per answer")
    p.add_argument(
        "--question-offset",
        type=int,
        default=3,
        help="Offset between target agent and subject agent fact (0 auto-normalizes to 1)",
    )
    p.add_argument("--output", default="", help="Output JSON path")
    args = p.parse_args()

    configure_otel(
        service_name=os.environ.get("OTEL_SERVICE_NAME", "").strip()
        or "amplihack.azure-retrieval-smoke",
        component="eval-retrieval-smoke",
        attributes={
            "amplihack.agent_count": args.agents,
            "amplihack.question_offset": args.question_offset,
        },
    )

    from remote_agent_adapter import RemoteAgentAdapter

    cases = build_retrieval_smoke_cases(args.agents, args.question_offset)
    adapter = RemoteAgentAdapter(
        connection_string=args.connection_string,
        input_hub=args.input_hub,
        response_hub=args.response_hub,
        agent_count=args.agents,
        resource_group=args.resource_group,
        answer_timeout=args.answer_timeout,
    )

    results: list[dict[str, object]] = []
    try:
        with start_span(
            "azure_eval.run_retrieval_smoke",
            tracer_name=__name__,
            attributes={
                "amplihack.agent_count": args.agents,
                "amplihack.question_offset": args.question_offset,
            },
        ):
            for case in cases:
                adapter.learn_from_content(case.learn_text)

            for case in cases:
                with start_span(
                    "azure_eval.retrieval_smoke_question",
                    tracer_name=__name__,
                    attributes={
                        "amplihack.target_agent": case.target_agent,
                        "amplihack.subject_agent": case.subject_agent,
                    },
                ):
                    answer = adapter.answer_question(case.question, target_agent=case.target_agent)
                passed = answer_contains_expected(answer, case.expected_codename)
                results.append(
                    {
                        **asdict(case),
                        "answer": answer,
                        "passed": passed,
                    }
                )
    finally:
        adapter.close()

    passed_count = sum(1 for result in results if result["passed"])
    summary = {
        "agent_count": args.agents,
        "question_offset": args.question_offset,
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "all_passed": passed_count == len(results),
        "results": results,
    }

    output_path = args.output or "/tmp/azure_retrieval_smoke.json"
    Path(output_path).write_text(json.dumps(summary, indent=2))
    logger.info(
        "Retrieval smoke complete: %d/%d passed (output=%s)",
        passed_count,
        len(results),
        output_path,
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["all_passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
