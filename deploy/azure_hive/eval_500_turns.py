#!/usr/bin/env python3
"""eval_500_turns.py -- End-to-end eval: feed 500 turns, query via LearningAgent.

Validates that the agent_entrypoint QUERY handler uses LearningAgent.answer_question
instead of raw keyword search.

Steps:
  1. Create a LearningAgent ("app-0") backed by a temp Kuzu DB.
  2. Feed 500 turns by storing facts directly into LearningAgent memory
     (mirrors how the entrypoint handles LEARN_CONTENT via memory.remember).
  3. Ask 10 Q&A questions via the _handle_event() QUERY dispatch path,
     confirming LearningAgent.answer_question is called (not memory.recall).
  4. Write a JSON report to eval_500_turns_report.json.

Usage:
    python eval_500_turns.py [--output path/to/report.json]
    ANTHROPIC_API_KEY=<key> python eval_500_turns.py
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
logger = logging.getLogger("eval_500_turns")

# ---------------------------------------------------------------------------
# Q&A test questions (security-analyst domain matching feed_content.py)
# ---------------------------------------------------------------------------

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
    """Load security content pool from feed_content.py."""
    feed_path = Path(__file__).parent / "feed_content.py"
    spec = importlib.util.spec_from_file_location("feed_content", feed_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._CONTENT_POOL


def _load_entrypoint():
    """Load agent_entrypoint module."""
    ep_path = Path(__file__).parent / "agent_entrypoint.py"
    spec = importlib.util.spec_from_file_location("agent_entrypoint", ep_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _extract_topic(content: str) -> str:
    """Derive a simple topic label from the first words of content."""
    words = content.split()[:4]
    return " ".join(words).rstrip(".,;:")


def run_eval(output_path: str) -> dict:
    """Run 500-turn eval and return report dict."""
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
        # Phase 1: feed 500 turns by storing facts directly (no LLM)
        # This mirrors the entrypoint LEARN_CONTENT handler:
        #   memory.remember(f"[LEARN_CONTENT turn={turn}] {content}")
        # ----------------------------------------------------------------
        logger.info("Phase 1: storing 500 facts into app-0 LearningAgent memory ...")
        t0 = time.time()
        errors_learn = 0
        for turn in range(500):
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
        learn_elapsed = time.time() - t0
        logger.info(
            "Phase 1 complete: 500 turns fed, %d errors, %.1fs elapsed",
            errors_learn,
            learn_elapsed,
        )

        # ----------------------------------------------------------------
        # Phase 2: answer 10 questions via _handle_event QUERY path.
        # This verifies:
        #  - LearningAgent.answer_question is called (not memory.recall)
        #  - Answers are returned and sent via memory.send_query_response
        # ----------------------------------------------------------------
        logger.info("Phase 2: querying via _handle_event QUERY dispatch ...")
        mock_memory = MagicMock()
        mock_memory.recall.return_value = []

        # Track whether answer_question is actually called (not recall)
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
                    answer = (
                        captured["results"][0].get("content", "") if captured["results"] else ""
                    )
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
        recall_calls = mock_memory.recall.call_count
        # recall() is also called in _ooda_tick's "recent context" step,
        # but NOT for query answering. Verify no QUERY answer used recall.
        recall_used_for_queries = any(
            call[0][0] == q["question"] and call[1].get("limit", 0) == 10
            for call in (mock_memory.recall.call_args_list or [])
            for q in _QUESTIONS
            if isinstance(call, tuple)
        )

        logger.info(
            "Phase 2 complete: %d/%d answered via LearningAgent, %d errors, "
            "answer_question called %d times, memory.recall-for-query=%s",
            passed_count,
            len(_QUESTIONS),
            errors_query,
            len(calls_to_answer_question),
            recall_used_for_queries,
        )

    report = {
        "agent_name": "app-0",
        "turns_fed": 500,
        "learn_errors": errors_learn,
        "learn_elapsed_s": round(learn_elapsed, 2),
        "questions_total": len(_QUESTIONS),
        "questions_passed": passed_count,
        "query_errors": errors_query,
        "answer_question_calls": len(calls_to_answer_question),
        "recall_used_for_queries": recall_used_for_queries,
        "qa_results": responses,
        "success": errors_learn == 0 and passed_count > 0 and not recall_used_for_queries,
    }

    with open(output_path, "w") as fh:
        json.dump(report, fh, indent=2)
    logger.info("Report written to: %s", output_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Feed 500 turns to app-0 and validate QUERY responses via LearningAgent."
    )
    parser.add_argument(
        "--output",
        default="eval_500_turns_report.json",
        help="Path for JSON report (default: eval_500_turns_report.json)",
    )
    args = parser.parse_args()

    report = run_eval(args.output)

    print()
    print("=" * 60)
    print("EVAL 500 TURNS — RESULTS")
    print("=" * 60)
    print(f"  Turns fed:            500 ({report['learn_errors']} errors)")
    print(f"  Learn elapsed:        {report['learn_elapsed_s']}s")
    print(f"  Questions answered:   {report['questions_passed']}/{report['questions_total']}")
    print(f"  answer_question calls:{report['answer_question_calls']}")
    print(f"  recall used for Q&A:  {report['recall_used_for_queries']}")
    print(f"  Query errors:         {report['query_errors']}")
    print(f"  Overall:              {'PASS' if report['success'] else 'FAIL'}")
    print("=" * 60)
    print(f"  Full report:          {args.output}")
    print()

    return 0 if report["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
