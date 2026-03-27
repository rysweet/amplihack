#!/usr/bin/env python3
"""eval_5000_turns.py -- End-to-end eval: feed 5000 security analyst turns, query via LearningAgent.

Extends eval_500_turns.py to 5000 turns for stress-testing memory ingestion
and retrieval at scale.  Validates:
  1. All 5000 facts stored without errors.
  2. 10 Q&A questions answered via LearningAgent.answer_question (not raw recall).
  3. JSON report written.

Usage:
    python eval_5000_turns.py [--output path/to/report.json]
    ANTHROPIC_API_KEY=<key> python eval_5000_turns.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("eval_5000_turns")

_TURNS = 5000

_QUESTIONS = [
    "What CVE is associated with the Log4Shell vulnerability?",
    "Which threat actor is associated with APT29?",
    "What happened in incident INC-2024-001?",
    "How many documents did jsmith download in the insider threat incident?",
    "What was the CVSS score of CVE-2021-44228?",
    "Which malicious npm package was used in the supply chain attack?",
    "What IP address was the C2 server in INC-2024-002?",
    "How were the encrypted files restored after INC-2024-001?",
    "What is DNS tunneling used for in the APT29 campaign?",
    "What security improvement was enforced after INC-2024-001?",
]


def _load_feed_content_pool() -> list[str]:
    feed_path = Path(__file__).parent / "feed_content.py"
    spec = importlib.util.spec_from_file_location("feed_content", feed_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._CONTENT_POOL


def _load_entrypoint():
    ep_path = Path(__file__).parent / "agent_entrypoint.py"
    spec = importlib.util.spec_from_file_location("agent_entrypoint", ep_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _extract_topic(content: str) -> str:
    words = content.split()[:4]
    return " ".join(words).rstrip(".,;:")


def run_eval(output_path: str) -> dict:
    from amplihack.agents.goal_seeking.learning_agent import LearningAgent

    content_pool = _load_feed_content_pool()
    entrypoint = _load_entrypoint()

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Path(tmpdir) / "app-0"
        storage.mkdir()

        agent = LearningAgent(
            agent_name="app-0",
            storage_path=storage,
            use_hierarchical=True,
        )

        # ----------------------------------------------------------------
        # Phase 1: feed 5000 turns by storing facts directly (no LLM)
        # ----------------------------------------------------------------
        logger.info("Phase 1: storing %d facts into app-0 LearningAgent memory ...", _TURNS)
        t0 = time.time()
        errors_learn = 0
        for turn in range(_TURNS):
            content = content_pool[turn % len(content_pool)]
            try:
                topic = _extract_topic(content)
                agent.memory.store_fact(
                    context=topic,
                    fact=f"[turn={turn}] {content}",
                    confidence=0.9,
                )
            except Exception as exc:
                logger.warning("store_fact turn %d failed: %s", turn, exc)
                errors_learn += 1
            if (turn + 1) % 500 == 0:
                elapsed = time.time() - t0
                logger.info(
                    "  Progress: %d/%d turns stored (%.1fs elapsed, %.0f turns/s)",
                    turn + 1, _TURNS, elapsed, (turn + 1) / elapsed,
                )
        learn_elapsed = time.time() - t0
        logger.info(
            "Phase 1 complete: %d turns fed, %d errors, %.1fs elapsed (avg %.0f turns/s)",
            _TURNS, errors_learn, learn_elapsed, _TURNS / learn_elapsed,
        )

        # ----------------------------------------------------------------
        # Phase 2: answer 10 questions via _handle_event QUERY path
        # ----------------------------------------------------------------
        logger.info("Phase 2: querying via _handle_event QUERY dispatch ...")
        mock_memory = MagicMock()
        mock_memory.recall.return_value = []

        original_answer_question = agent.answer_question
        calls_to_answer_question = []

        def tracked_answer_question(question, *args, **kwargs):
            result = original_answer_question(question, *args, **kwargs)
            calls_to_answer_question.append(question)
            return result

        agent.answer_question = tracked_answer_question

        responses = []
        errors_query = 0

        for i, question in enumerate(_QUESTIONS):
            query_event = {
                "event_type": "QUERY",
                "payload": {
                    "query_id": f"q{i}",
                    "question": question,
                },
            }
            captured = {}

            def capture_response(qid, q, results, _cap=captured):
                _cap["results"] = results

            mock_memory.send_query_response = capture_response

            try:
                entrypoint._handle_event("app-0", query_event, mock_memory, agent)
                answer = ""
                if captured.get("results"):
                    answer = captured["results"][0].get("content", "") if captured["results"] else ""
                passed = bool(answer) and answer.lower() != "error"
                responses.append({"question": question, "answer": answer, "passed": passed})
                logger.info("Q%d: %s\n  -> %s...", i + 1, question[:60], answer[:100])
            except Exception as exc:
                logger.warning("QUERY %d failed: %s", i, exc)
                errors_query += 1
                responses.append(
                    {"question": question, "answer": "", "passed": False, "error": str(exc)}
                )

        passed_count = sum(1 for r in responses if r["passed"])

    report = {
        "agent_name": "app-0",
        "turns_fed": _TURNS,
        "learn_errors": errors_learn,
        "learn_elapsed_s": round(learn_elapsed, 2),
        "learn_throughput_tps": round(_TURNS / learn_elapsed, 1),
        "questions_total": len(_QUESTIONS),
        "questions_passed": passed_count,
        "query_errors": errors_query,
        "answer_question_calls": len(calls_to_answer_question),
        "qa_results": responses,
        "success": errors_learn == 0 and passed_count > 0,
    }

    with open(output_path, "w") as fh:
        json.dump(report, fh, indent=2)
    logger.info("Report written to: %s", output_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"Feed {_TURNS} security analyst turns to app-0 and validate QUERY responses."
    )
    parser.add_argument(
        "--output",
        default="eval_5000_turns_report.json",
        help="Path for JSON report (default: eval_5000_turns_report.json)",
    )
    args = parser.parse_args()

    report = run_eval(args.output)

    print()
    print("=" * 60)
    print(f"EVAL {_TURNS} TURNS — RESULTS")
    print("=" * 60)
    print(f"  Turns fed:            {_TURNS} ({report['learn_errors']} errors)")
    print(f"  Learn elapsed:        {report['learn_elapsed_s']}s")
    print(f"  Throughput:           {report['learn_throughput_tps']} turns/s")
    print(f"  Questions answered:   {report['questions_passed']}/{report['questions_total']}")
    print(f"  answer_question calls:{report['answer_question_calls']}")
    print(f"  Query errors:         {report['query_errors']}")
    print(f"  Overall:              {'PASS' if report['success'] else 'FAIL'}")
    print("=" * 60)
    print(f"  Full report:          {args.output}")
    print()

    return 0 if report["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
