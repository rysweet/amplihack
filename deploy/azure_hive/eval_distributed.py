#!/usr/bin/env python3
"""Distributed eval harness — identical grading to single-agent, questions answered locally on agents.

Sends EVAL_QUESTIONS batch events to agents via Service Bus. Each agent calls
answer_question() directly (same as single-agent eval). Collects answers from
a response topic. Grades with the same hybrid grader.

Usage:
    python deploy/azure_hive/eval_distributed.py \
        --connection-string "$SB_CONN" \
        --topic hive-events-amplihivev8 \
        --response-topic eval-responses-amplihivev8 \
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
import time
import uuid
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("eval_distributed")


def main():
    p = argparse.ArgumentParser(description="Distributed hive mind eval")
    p.add_argument("--connection-string", required=True, help="Service Bus connection string")
    p.add_argument("--topic", default="hive-events", help="Agent input topic")
    p.add_argument("--response-topic", default="eval-responses", help="Eval response topic")
    p.add_argument("--turns", type=int, default=300, help="Dialogue turns for question generation")
    p.add_argument("--questions", type=int, default=50, help="Number of questions")
    p.add_argument("--agents", type=int, default=100, help="Number of agents")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    p.add_argument("--grader-model", default="claude-haiku-4-5-20251001")
    p.add_argument("--answer-timeout", type=float, default=600, help="Seconds to wait for all answers")
    p.add_argument("--output", default="", help="Output JSON path")
    args = p.parse_args()

    # Step 1: Generate questions (same as single-agent eval)
    from amplihack_eval.data.long_horizon import generate_dialogue, generate_questions

    logger.info("Generating %d turns, %d questions (seed=%d)", args.turns, args.questions, args.seed)
    ground_truth = generate_dialogue(num_turns=args.turns, seed=args.seed)
    questions = generate_questions(ground_truth, num_questions=args.questions)
    logger.info(
        "Generated %d questions across %d categories",
        len(questions),
        len(set(q.category for q in questions)),
    )

    # Step 2: Distribute questions across agents (round-robin)
    batches: dict[int, list] = {}  # agent_index -> list of question dicts
    for i, q in enumerate(questions):
        agent_idx = i % args.agents
        if agent_idx not in batches:
            batches[agent_idx] = []
        event_id = uuid.uuid4().hex[:12]
        batches[agent_idx].append(
            {
                "question_id": q.question_id,
                "text": q.text,
                "event_id": event_id,
                "category": q.category,
                "expected_answer": q.expected_answer,
            }
        )

    logger.info("Distributed %d questions across %d agents", len(questions), len(batches))

    # Step 3: Send EVAL_QUESTIONS to each agent
    from azure.servicebus import ServiceBusClient, ServiceBusMessage

    sb_client = ServiceBusClient.from_connection_string(args.connection_string)
    sender = sb_client.get_topic_sender(topic_name=args.topic)

    batch_id = uuid.uuid4().hex[:8]
    sent_events = {}  # event_id -> question object

    # Send each question as a regular INPUT event (one per message).
    # The agent processes it through its full OODA loop (observe → orient →
    # decide → act). The event_id in the message body lets the AnswerPublisher
    # correlate the ANSWER stdout line with this specific question.
    for agent_idx, agent_questions in batches.items():
        for aq in agent_questions:
            msg_body = json.dumps({
                "event_type": "INPUT",
                "event_id": aq["event_id"],
                "source_agent": "eval-harness",
                "payload": {
                    "question": aq["text"],
                    "question_id": aq["question_id"],
                },
            })
            msg = ServiceBusMessage(msg_body, content_type="application/json")
            sender.send_messages(msg)
            sent_events[aq["event_id"]] = aq

        logger.info("Sent %d questions to agent-%d", len(agent_questions), agent_idx)

    sender.close()
    logger.info("All questions sent (batch_id=%s). Waiting for answers...", batch_id)

    # Step 4: Collect answers from response topic
    receiver = sb_client.get_subscription_receiver(
        topic_name=args.response_topic,
        subscription_name="eval-reader",
        max_wait_time=30,
    )

    answers = {}  # event_id -> answer string
    deadline = time.time() + args.answer_timeout

    while len(answers) < len(sent_events) and time.time() < deadline:
        messages = receiver.receive_messages(max_message_count=50, max_wait_time=10)
        for msg in messages:
            try:
                body = json.loads(str(msg))
                eid = body.get("event_id", "")
                if eid in sent_events and eid not in answers:
                    answers[eid] = body.get("answer", "")
                    logger.info(
                        "Received answer for %s from %s (%d/%d)",
                        body.get("question_id", "?"),
                        body.get("agent_id", "?"),
                        len(answers),
                        len(sent_events),
                    )
                receiver.complete_message(msg)
            except Exception as e:
                logger.warning("Failed to parse response: %s", e)
                receiver.complete_message(msg)

    receiver.close()
    sb_client.close()

    logger.info("Collected %d/%d answers", len(answers), len(sent_events))

    # Step 5: Grade answers (same hybrid grader as single-agent)
    from amplihack.eval.long_horizon_memory import EvalResult, _grade_multi_vote

    results = []
    q_map = {q.question_id: q for q in questions}

    for event_id, q_info in sent_events.items():
        q = q_map.get(q_info["question_id"])
        if not q:
            continue

        answer = answers.get(event_id, "No answer received (timeout)")

        dimensions = q.scoring_dimensions or ["factual_accuracy"]
        dim_scores = _grade_multi_vote(q, answer, dimensions, args.grader_model, num_votes=1)
        overall = sum(d.score for d in dim_scores) / len(dim_scores) if dim_scores else 0.0

        results.append(
            EvalResult(
                question_id=q.question_id,
                question_text=q.text,
                category=q.category,
                expected_answer=q.expected_answer,
                actual_answer=answer[:500] if isinstance(answer, str) else str(answer)[:500],
                dimensions=dim_scores,
                overall_score=overall,
            )
        )

        logger.info("  [%.2f] %s: %s", overall, q.question_id, q.text[:50])

    # Step 6: Report (same format as single-agent)
    overall_score = sum(r.overall_score for r in results) / len(results) if results else 0.0

    # Category breakdown
    from collections import defaultdict

    by_cat: dict[str, list[float]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r.overall_score)

    report = {
        "eval_type": "distributed",
        "num_agents": args.agents,
        "num_turns": args.turns,
        "num_questions": len(questions),
        "answers_received": len(answers),
        "answers_timeout": len(sent_events) - len(answers),
        "overall_score": round(overall_score, 4),
        "batch_id": batch_id,
        "grader_model": args.grader_model,
        "category_breakdown": [
            {
                "category": cat,
                "num_questions": len(scores),
                "avg_score": round(sum(scores) / len(scores), 4),
                "min_score": round(min(scores), 4),
                "max_score": round(max(scores), 4),
            }
            for cat, scores in sorted(by_cat.items())
        ],
        "results": [
            {
                "question_id": r.question_id,
                "question_text": r.question_text,
                "category": r.category,
                "expected_answer": r.expected_answer,
                "actual_answer": r.actual_answer,
                "overall_score": round(r.overall_score, 4),
            }
            for r in results
        ],
    }

    # Print summary
    print("\n" + "=" * 70)
    print(f"DISTRIBUTED EVAL — {args.agents} agents, {args.turns} turns, {len(questions)} questions")
    print(f"Answers received: {len(answers)}/{len(sent_events)}")
    print(f"OVERALL SCORE: {overall_score:.2%}")
    print("=" * 70)
    for cat, scores in sorted(by_cat.items()):
        avg = sum(scores) / len(scores)
        print(f"  {cat:<30s} {avg:.1%} ({len(scores)} q)")
    print()

    # Write output
    output_path = args.output or f"/tmp/distributed_eval_{batch_id}.json"
    Path(output_path).write_text(json.dumps(report, indent=2))
    logger.info("Report written to %s", output_path)

    return 0 if overall_score > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
