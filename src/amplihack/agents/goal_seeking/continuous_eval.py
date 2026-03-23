#!/usr/bin/env python3
"""continuous_eval.py — Single-agent eval using the event-driven OODA loop.

Feeds a list of dialogue turns into a GoalSeekingAgent via ListInputSource,
then answers a set of eval questions in a tight loop — no artificial delays.

This is the single-agent counterpart to the distributed hive eval in
``experiments/hive_mind/query_hive.py``.  Both paths share the same
GoalSeekingAgent / run_ooda_loop code; only the InputSource differs:

    Single agent:   ListInputSource(turns)
    Distributed:    ServiceBusInputSource(conn_str, agent_name)

Usage:
    python -m amplihack.agents.goal_seeking.continuous_eval
    python -m amplihack.agents.goal_seeking.continuous_eval --turns 5000 \\
        --output /tmp/hive_eval_v4.json --repeats 3
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default eval content (security analyst domain)
# ---------------------------------------------------------------------------

_DEFAULT_CONTENT = [
    "Log4Shell (CVE-2021-44228) is a critical RCE vulnerability in Apache Log4j 2.x with a CVSS score of 10.0.",
    "The Midnight Blizzard (APT29) threat actor is linked to the Russian SVR intelligence service.",
    "Incident INC-2024-001: Ransomware encrypted 500 files on corp-server-01. Encrypted files restored from backup.",
    "The insider threat incident involved jsmith downloading 2,847 documents before account suspension.",
    "CVE-2021-44228 affects Apache Log4j versions 2.0-beta9 through 2.14.1.",
    "A malicious npm package 'event-stream' was used in a supply chain attack targeting cryptocurrency wallets.",
    "Incident INC-2024-002: C2 beacon to 185.220.101.45 detected from workstation WS-047.",
    "DNS tunneling uses DNS protocol to exfiltrate data by encoding payloads in DNS queries.",
    "Security improvement after INC-2024-001: mandatory MFA enforced for all privileged accounts.",
    "APT29 uses spearphishing and DNS tunneling for initial access and C2 communications.",
    "Zero-day exploit CVE-2023-23397 targets Microsoft Outlook with no user interaction required.",
    "Lateral movement via pass-the-hash attack detected using Mimikatz credential dumping tool.",
    "The MITRE ATT&CK framework documents 14 tactics used by adversaries in cyber attacks.",
    "Ransomware operators increasingly use double extortion: encrypt data AND threaten to leak it.",
    "SIEM correlation rule triggered: 50+ failed logins followed by successful login from new IP.",
]

_DEFAULT_QUESTIONS = [
    ("What CVE is associated with the Log4Shell vulnerability?", "CVE-2021-44228"),
    ("Which threat actor is associated with APT29?", "Midnight Blizzard"),
    ("What happened in incident INC-2024-001?", "Ransomware encrypted 500 files"),
    ("How many documents did jsmith download?", "2,847"),
    ("What was the CVSS score of CVE-2021-44228?", "10.0"),
    ("Which malicious npm package was used in the supply chain attack?", "event-stream"),
    ("What IP address was the C2 server in INC-2024-002?", "185.220.101.45"),
    ("How were the encrypted files restored after INC-2024-001?", "restored from backup"),
    ("What is DNS tunneling used for in the APT29 campaign?", "exfiltrate data"),
    ("What security improvement was enforced after INC-2024-001?", "MFA"),
]


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------


def _grade_answer(question: str, expected: str, actual: str) -> float:
    """Simple substring-based grading (0.0 or 1.0)."""
    if not actual:
        return 0.0
    actual_lower = actual.lower()
    expected_lower = expected.lower()
    # Any expected keyword found in the answer
    keywords = [w for w in expected_lower.split() if len(w) > 3]
    if not keywords:
        return 1.0 if expected_lower in actual_lower else 0.0
    hits = sum(1 for kw in keywords if kw in actual_lower)
    return hits / len(keywords)


# ---------------------------------------------------------------------------
# Main eval runner
# ---------------------------------------------------------------------------


def run_eval(
    turns: int = 100,
    repeats: int = 1,
    output: str | None = None,
    content_pool: list[str] | None = None,
    questions: list[tuple[str, str]] | None = None,
    storage_path: str | None = None,
) -> dict:
    """Run single-agent continuous eval with ListInputSource.

    Args:
        turns:        Number of content turns to feed.
        repeats:      Number of eval repetitions (results averaged).
        output:       Optional path to write JSON results.
        content_pool: Override the default content pool.
        questions:    Override the default eval questions.
        storage_path: Override the agent storage directory.

    Returns:
        Results dict with per-question scores and summary stats.
    """
    from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent
    from amplihack.agents.goal_seeking.input_source import ListInputSource

    pool = content_pool or _DEFAULT_CONTENT
    qs = questions or _DEFAULT_QUESTIONS
    all_results = []

    for rep in range(repeats):
        logger.info("--- Repeat %d/%d ---", rep + 1, repeats)

        with tempfile.TemporaryDirectory() as tmpdir:
            sp = Path(storage_path or tmpdir) / f"eval-agent-rep{rep}"
            sp.mkdir(parents=True, exist_ok=True)

            agent = GoalSeekingAgent(
                agent_name="eval-agent",
                storage_path=sp,
                use_hierarchical=False,
            )

            # Phase 1: feed content turns via ListInputSource (tight loop — no sleep)
            content_turns = [pool[i % len(pool)] for i in range(turns)]
            src = ListInputSource(content_turns)

            t0 = time.time()
            agent.run_ooda_loop(src)
            learn_elapsed = time.time() - t0
            logger.info(
                "Rep %d: fed %d turns in %.2fs (%.0f turns/s)",
                rep + 1,
                turns,
                learn_elapsed,
                turns / learn_elapsed if learn_elapsed > 0 else float("inf"),
            )

            # Phase 2: answer eval questions
            q_results = []
            for question, expected in qs:
                t_q = time.time()
                # Create a single-item ListInputSource for the question
                q_src = ListInputSource([question])
                # Capture answer via process() directly
                answer = agent.process(question) or ""
                score = _grade_answer(question, expected, answer)
                q_results.append(
                    {
                        "question": question,
                        "expected": expected,
                        "answer": answer[:200],
                        "score": score,
                        "elapsed_s": round(time.time() - t_q, 2),
                    }
                )
                logger.info(
                    "  Q: %s -> score=%.2f (%.2fs)",
                    question[:60],
                    score,
                    time.time() - t_q,
                )

            all_results.append(
                {
                    "repeat": rep + 1,
                    "turns": turns,
                    "learn_elapsed_s": round(learn_elapsed, 2),
                    "learn_throughput": round(turns / learn_elapsed, 1) if learn_elapsed > 0 else 0,
                    "questions": q_results,
                    "avg_score": round(
                        sum(r["score"] for r in q_results) / len(q_results), 3
                    )
                    if q_results
                    else 0.0,
                }
            )

            agent.close()

    summary = {
        "eval": "continuous_eval",
        "turns": turns,
        "repeats": repeats,
        "results": all_results,
        "aggregate": {
            "avg_score": round(
                sum(r["avg_score"] for r in all_results) / len(all_results), 3
            )
            if all_results
            else 0.0,
            "avg_learn_throughput": round(
                sum(r["learn_throughput"] for r in all_results) / len(all_results), 1
            )
            if all_results
            else 0.0,
        },
    }

    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(summary, indent=2))
        logger.info("Results written to %s", output)
    else:
        print(json.dumps(summary, indent=2))

    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Single-agent continuous eval via ListInputSource (no polling sleep)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--turns", type=int, default=100, help="Number of content turns to feed")
    parser.add_argument("--repeats", type=int, default=1, help="Number of eval repetitions")
    parser.add_argument("--output", "-o", type=str, help="Path to write JSON results")
    parser.add_argument("--storage-path", type=str, help="Override agent storage directory")
    args = parser.parse_args(argv)

    run_eval(
        turns=args.turns,
        repeats=args.repeats,
        output=args.output,
        storage_path=args.storage_path,
    )


if __name__ == "__main__":
    main()
