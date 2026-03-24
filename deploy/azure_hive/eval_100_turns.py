#!/usr/bin/env python3
"""eval_100_turns.py -- Update feed 100-turn eval via the refactored agent_entrypoint.

Validates that the refactored agent_entrypoint uses LearningAgent for BOTH
learning (LEARN_CONTENT events) and answering (QUERY events), with no
memory.remember() or memory.recall() calls.

Steps:
  1. Create a LearningAgent ("app-0") backed by a temp Kuzu DB.
  2. Feed 100 turns via _handle_event() LEARN_CONTENT dispatch path,
     confirming learning_agent.learn_from_content() is called (not memory.remember).
  3. Ask 10 Q&A questions via _handle_event() QUERY dispatch path,
     confirming learning_agent.answer_question() is called (not memory.recall).
  4. Write a JSON report to eval_100_turns_report.json.

Usage:
    python eval_100_turns.py [--output path/to/report.json]
    ANTHROPIC_API_KEY=<key> python eval_100_turns.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("eval_100_turns")

_TURNS = 100

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
        # Phase 1: feed 100 turns via _handle_event LEARN_CONTENT path.
        # This exercises the full entrypoint path and verifies:
        #   - learning_agent.learn_from_content() is called (not memory.remember)
        #   - memory.remember is never invoked
        # ----------------------------------------------------------------
        logger.info("Phase 1: feeding %d LEARN_CONTENT events via _handle_event ...", _TURNS)
        mock_memory = MagicMock()

        calls_to_learn_from_content = []
        original_learn = agent.learn_from_content

        def tracked_learn(content, *args, **kwargs):
            result = original_learn(content, *args, **kwargs)
            calls_to_learn_from_content.append(content[:80])
            return result

        agent.learn_from_content = tracked_learn

        t0 = time.time()
        errors_learn = 0
        for turn in range(_TURNS):
            content = content_pool[turn % len(content_pool)]
            learn_event = {
                "event_type": "LEARN_CONTENT",
                "payload": {"turn": turn, "content": content},
            }
            try:
                entrypoint._handle_event("app-0", learn_event, mock_memory, agent)
            except Exception as exc:
                logger.warning("LEARN_CONTENT turn %d failed: %s", turn, exc)
                errors_learn += 1

        learn_elapsed = time.time() - t0
        remember_calls = mock_memory.remember.call_count

        logger.info(
            "Phase 1 complete: %d turns fed via _handle_event, %d errors, %.1fs elapsed",
            _TURNS,
            errors_learn,
            learn_elapsed,
        )
        logger.info(
            "  learn_from_content called: %d times, memory.remember called: %d times",
            len(calls_to_learn_from_content),
            remember_calls,
        )

        # ----------------------------------------------------------------
        # Phase 2: answer 10 questions via _handle_event QUERY path.
        # This verifies:
        #   - learning_agent.answer_question() is called (not memory.recall)
        #   - memory.recall is never invoked
        # ----------------------------------------------------------------
        logger.info("Phase 2: querying via _handle_event QUERY dispatch ...")
        mock_memory.reset_mock()

        calls_to_answer_question = []
        original_answer = agent.answer_question

        def tracked_answer(question, *args, **kwargs):
            result = original_answer(question, *args, **kwargs)
            calls_to_answer_question.append(question)
            return result

        agent.answer_question = tracked_answer

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
                    answer = (
                        captured["results"][0].get("content", "") if captured["results"] else ""
                    )
                passed = bool(answer) and not answer.lower().startswith("error")
                responses.append({"question": question, "answer": answer, "passed": passed})
                logger.info("Q%d: %s\n  -> %s...", i + 1, question[:60], answer[:100])
            except Exception as exc:
                logger.warning("QUERY %d failed: %s", i, exc)
                errors_query += 1
                responses.append(
                    {"question": question, "answer": "", "passed": False, "error": str(exc)}
                )

        passed_count = sum(1 for r in responses if r["passed"])
        recall_calls = mock_memory.recall.call_count

        logger.info(
            "Phase 2 complete: %d/%d answered via LearningAgent, %d errors, "
            "answer_question called %d times, memory.recall called %d times",
            passed_count,
            len(_QUESTIONS),
            errors_query,
            len(calls_to_answer_question),
            recall_calls,
        )

    # Success criteria:
    #   - No learn errors
    #   - learn_from_content was called for all turns (no memory.remember)
    #   - At least one question answered
    #   - memory.recall never called (LearningAgent handles all answering)
    success = (
        errors_learn == 0
        and len(calls_to_learn_from_content) == _TURNS
        and remember_calls == 0
        and passed_count > 0
        and recall_calls == 0
    )

    report = {
        "agent_name": "app-0",
        "turns_fed": _TURNS,
        "learn_errors": errors_learn,
        "learn_elapsed_s": round(learn_elapsed, 2),
        "learn_from_content_calls": len(calls_to_learn_from_content),
        "memory_remember_calls": remember_calls,
        "questions_total": len(_QUESTIONS),
        "questions_passed": passed_count,
        "query_errors": errors_query,
        "answer_question_calls": len(calls_to_answer_question),
        "memory_recall_calls": recall_calls,
        "qa_results": responses,
        "success": success,
    }

    with open(output_path, "w") as fh:
        json.dump(report, fh, indent=2)
    logger.info("Report written to: %s", output_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            f"Feed {_TURNS} LEARN_CONTENT events and 10 QUERY events via "
            "agent_entrypoint._handle_event to validate LearningAgent refactor."
        )
    )
    parser.add_argument(
        "--output",
        default="eval_100_turns_report.json",
        help="Path for JSON report (default: eval_100_turns_report.json)",
    )
    args = parser.parse_args()

    report = run_eval(args.output)

    print()
    print("=" * 65)
    print(f"EVAL {_TURNS} TURNS (UPDATE FEED) — RESULTS")
    print("=" * 65)
    print(f"  Turns fed via LEARN_CONTENT: {_TURNS} ({report['learn_errors']} errors)")
    print(f"  learn_from_content calls:    {report['learn_from_content_calls']}")
    print(f"  memory.remember calls:       {report['memory_remember_calls']} (must be 0)")
    print(f"  Learn elapsed:               {report['learn_elapsed_s']}s")
    print(
        f"  Questions answered:          {report['questions_passed']}/{report['questions_total']}"
    )
    print(f"  answer_question calls:       {report['answer_question_calls']}")
    print(f"  memory.recall calls:         {report['memory_recall_calls']} (must be 0)")
    print(f"  Query errors:                {report['query_errors']}")
    print(f"  Overall:                     {'PASS' if report['success'] else 'FAIL'}")
    print("=" * 65)
    print(f"  Full report:                 {args.output}")
    print()

    return 0 if report["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
