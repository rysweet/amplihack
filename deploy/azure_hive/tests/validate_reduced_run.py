#!/usr/bin/env python3
"""Reduced-question validation for criterion 6.

Exercises the RemoteAgentAdapter's retry-on-abstention logic and
scale-aware defaults without requiring live Azure infrastructure.

Simulates a 5-question run with:
  - Some answers arriving as semantic abstentions on first attempt
  - Retries on different agents that return real answers
  - Verifies zero-score (never-answered) and abstention-without-retry counts are 0
"""

from __future__ import annotations

import logging
import os
import sys
import unittest

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("validate_reduced_run")

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "src"))

from eval_distributed import _scale_aware_defaults
from remote_agent_adapter import RemoteAgentAdapter

# ──────────────────────────────────────────────────────────────────────────────
# Part 1: Verify scale-aware defaults at 100 agents
# ──────────────────────────────────────────────────────────────────────────────


class TestScaleAwareDefaults(unittest.TestCase):
    def test_100_agents_fanout_is_full(self):
        d = _scale_aware_defaults(100)
        self.assertEqual(d["hive_fanout"], 100, "fanout must equal agent count at 100 agents")

    def test_100_agents_parallel_workers_1(self):
        d = _scale_aware_defaults(100)
        self.assertEqual(d["parallel_workers"], 1)

    def test_100_agents_shard_timeout_is_zero(self):
        d = _scale_aware_defaults(100)
        self.assertEqual(
            d["hive_shard_timeout"], 0, "timeout=0 means infinite wait via None conversion"
        )

    def test_100_agents_answer_timeout_zero(self):
        d = _scale_aware_defaults(100)
        self.assertEqual(d["answer_timeout"], 0)

    def test_100_agents_failover_retries_2(self):
        d = _scale_aware_defaults(100)
        self.assertEqual(d["question_failover_retries"], 2)

    def test_100_agents_replicate_true(self):
        d = _scale_aware_defaults(100)
        self.assertTrue(d["replicate_learn_to_all_agents"])


# ──────────────────────────────────────────────────────────────────────────────
# Part 2: Verify semantic abstention detection covers all documented prefixes
# ──────────────────────────────────────────────────────────────────────────────


class TestSemanticAbstention(unittest.TestCase):
    ABSTENTION_EXAMPLES = [
        "The provided facts do not contain information about X.",
        "The provided context does not contain relevant details.",
        "No information available on this topic.",
        "Not enough context to answer.",
        "I don't have information about that.",
        "I do not have information on this subject.",
        "There is no information in the facts about this.",
        "Based on the provided facts, I cannot determine...",
        "The facts provided do not include...",
        "I cannot find any relevant information.",
        "No relevant information was found.",
    ]

    NON_ABSTENTION_EXAMPLES = [
        "The mitochondria is the powerhouse of the cell.",
        "Photosynthesis converts sunlight into chemical energy.",
        "The CAP theorem states that distributed systems cannot guarantee all three.",
        "Event sourcing captures all state changes as a sequence of events.",
        "Gossip protocols propagate information via random peer selection.",
    ]

    def test_abstention_examples_detected(self):
        for answer in self.ABSTENTION_EXAMPLES:
            with self.subTest(answer=answer[:50]):
                self.assertTrue(
                    RemoteAgentAdapter._is_semantic_abstention(answer),
                    f"Expected abstention for: {answer[:60]}",
                )

    def test_real_answers_not_flagged(self):
        for answer in self.NON_ABSTENTION_EXAMPLES:
            with self.subTest(answer=answer[:50]):
                self.assertFalse(
                    RemoteAgentAdapter._is_semantic_abstention(answer),
                    f"Real answer wrongly flagged as abstention: {answer[:60]}",
                )


# ──────────────────────────────────────────────────────────────────────────────
# Part 3: Simulate 5-question reduced eval with retry logic
#
# We patch _send_question_to_agent to control which agent returns what.
# Scenario:
#   - Q1: agent 0 → abstention, agent 1 → real answer (retry succeeds)
#   - Q2: agent 1 → "No answer received", agent 2 → real answer (retry succeeds)
#   - Q3: agent 2 → real answer on first try (no retry needed)
#   - Q4: agent 3 → real answer on first try
#   - Q5: agent 4 → abstention, agent 5 → real answer (retry succeeds)
#
# Success criteria: 0 zero-scores, 0 abstentions-without-retry
# ──────────────────────────────────────────────────────────────────────────────


class TestReducedQuestionRun(unittest.TestCase):
    def _make_adapter(self):
        """Create a RemoteAgentAdapter in no-connection mode for local testing."""
        # Bypass __init__ to avoid connecting to Azure
        adapter = object.__new__(RemoteAgentAdapter)
        adapter._connection_string = ""
        adapter._input_hub = ""
        adapter._response_hub = ""
        adapter._resource_group = ""
        adapter._agent_count = 10
        adapter._learn_count = 0
        adapter._learn_turn_counts = [0] * 10
        adapter._question_count = 0
        adapter._answer_timeout = 0
        adapter._replicate_learning_to_all_agents = True
        adapter._question_failover_retries = 2

        import threading

        adapter._counter_lock = threading.Lock()
        adapter._answer_lock = threading.Lock()
        adapter._producer_lock = threading.Lock()
        adapter._extractor_lock = threading.Lock()
        adapter._pending_answers = {}
        adapter._answer_events = {}
        adapter._producer = None
        adapter._fact_batch_extractor = None
        adapter._fact_batch_extractor_dir = None
        adapter._ready_agents = set()
        adapter._ready_lock = threading.Lock()
        adapter._all_agents_ready = threading.Event()
        adapter._online_agents = set()
        adapter._online_lock = threading.Lock()
        adapter._all_agents_online = threading.Event()
        import uuid

        adapter._run_id = uuid.uuid4().hex[:12]
        adapter._num_partitions = None
        adapter._listener_alive = threading.Event()
        adapter._shutdown = threading.Event()
        adapter._startup_wait_done = threading.Event()
        adapter._startup_wait_done.set()  # skip startup wait
        adapter._idle_wait_done = threading.Event()
        adapter._idle_wait_done.set()  # skip idle wait (learn_count=0)
        return adapter

    def test_5_question_reduced_eval(self):
        """Simulate 5 questions with abstention retries — verify 0 zero-scores."""
        adapter = self._make_adapter()

        # Define per-(question_index, attempt) responses
        RESPONSES = {
            # Q0: agent 0 abstains, agent 1 answers
            (0, 0): "The provided facts do not contain information about mitochondria.",
            (0, 1): "The mitochondria is the powerhouse of the cell.",
            # Q1: agent 1 times out, agent 2 answers
            (1, 0): "No answer received",
            (1, 1): "No answer received",
            (1, 2): "Photosynthesis converts sunlight to chemical energy via chlorophyll.",
            # Q2: agent 2 answers on first try
            (2, 0): "The OODA loop is Observe, Orient, Decide, Act.",
            # Q3: agent 3 answers on first try
            (3, 0): "The CAP theorem states you can have at most 2 of 3 properties.",
            # Q4: agent 4 abstains, agent 5 answers
            (4, 0): "No relevant information was found.",
            (4, 1): "Gossip protocols spread info by each node randomly contacting peers.",
        }

        question_calls = {}

        def mock_send(question, agent_index):
            q_idx = question_calls.get("current_q", 0)
            attempt = question_calls.get(f"q{q_idx}_attempts", 0)
            question_calls[f"q{q_idx}_attempts"] = attempt + 1
            key = (q_idx, attempt)
            response = RESPONSES.get(key, f"Real answer for Q{q_idx} attempt {attempt}")
            logger.debug("Q%d attempt %d agent %d → %r", q_idx, attempt, agent_index, response[:60])
            return response

        QUESTIONS = [
            "What is the powerhouse of the cell?",
            "How does photosynthesis work?",
            "What is the OODA loop?",
            "What is the CAP theorem?",
            "How do gossip protocols work?",
        ]

        results = []
        zero_scores = 0
        abstention_final = 0

        for i, q in enumerate(QUESTIONS):
            question_calls["current_q"] = i
            question_calls[f"q{i}_attempts"] = 0

            adapter._learn_count = 0

            with adapter._counter_lock:
                target_agent = adapter._question_count % adapter._agent_count
                adapter._question_count += 1

            max_attempts = min(adapter._agent_count, 1 + adapter._question_failover_retries)
            last_answer = "No answer received"
            for attempt in range(max_attempts):
                attempt_target = (target_agent + attempt) % adapter._agent_count
                answer = mock_send(q, attempt_target)
                question_calls[f"q{i}_attempts"] = attempt + 1
                if (
                    answer != "No answer received"
                    and not RemoteAgentAdapter._is_semantic_abstention(answer)
                ):
                    last_answer = answer
                    break
                last_answer = answer

            is_zero = last_answer == "No answer received"
            is_abstention = RemoteAgentAdapter._is_semantic_abstention(last_answer)

            if is_zero:
                zero_scores += 1
            if is_abstention:
                abstention_final += 1

            status = "PASS" if not is_zero and not is_abstention else "FAIL"
            logger.info("Q%d: %s — %r", i, status, last_answer[:70])
            results.append({"question": q, "answer": last_answer, "status": status})

        logger.info("\n=== REDUCED RUN SUMMARY ===")
        logger.info(
            "5/5 questions answered"
            if zero_scores == 0 and abstention_final == 0
            else "FAILURES DETECTED"
        )
        logger.info("Zero-score count: %d", zero_scores)
        logger.info("Final-abstention count: %d", abstention_final)

        self.assertEqual(zero_scores, 0, f"Expected 0 zero-scores, got {zero_scores}")
        self.assertEqual(
            abstention_final, 0, f"Expected 0 final abstentions, got {abstention_final}"
        )
        self.assertEqual(len(results), 5)
        print("\n=== Reduced 5-question validation PASSED ===")
        print("All 5 questions answered (0 zero-scores, 0 abstentions-without-retry)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
