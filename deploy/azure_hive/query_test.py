#!/usr/bin/env python3
"""query_test.py -- Send 10 QUERY events to the hive and verify QUERY_RESPONSE replies.

Tests the QUERY event handler added to agent_entrypoint and NetworkGraphStore.
Sends 10 questions via Azure Service Bus (or local bus for dry-run) and collects
QUERY_RESPONSE events from agents.

Environment variables:
    AMPLIHACK_MEMORY_CONNECTION_STRING -- Azure Service Bus connection string
    AMPLIHACK_TOPIC_NAME               -- Service Bus topic (default: hive-graph)
    AMPLIHACK_SOURCE_AGENT             -- sender identity (default: query-test-client)
    QUERY_RESPONSE_SUBSCRIPTION        -- subscription for responses (default: eval-query-agent)
    QUERY_TIMEOUT                      -- seconds to wait per query (default: 15)

Usage:
    # Live Azure test:
    python query_test.py

    # Dry-run (no Azure required):
    python query_test.py --dry-run

    # Verbose output:
    python query_test.py --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
import uuid
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("query_test")

# ---------------------------------------------------------------------------
# Test questions
# ---------------------------------------------------------------------------

_TEST_QUESTIONS: list[str] = [
    "What is the powerhouse of the cell?",
    "How does photosynthesis work?",
    "What is the OODA loop?",
    "What is the CAP theorem in distributed systems?",
    "How do gossip protocols propagate information?",
    "What is the transformer architecture in machine learning?",
    "What is retrieval-augmented generation (RAG)?",
    "What are CRDTs and how do they enable eventual consistency?",
    "What is consistent hashing and why is it useful?",
    "How does the hive mind architecture distribute agent memory?",
]


def _build_query_event(question: str, source_agent: str) -> dict:
    """Construct a QUERY event dict."""
    return {
        "event_id": uuid.uuid4().hex,
        "event_type": "QUERY",
        "source_agent": source_agent,
        "timestamp": time.time(),
        "payload": {
            "query_id": uuid.uuid4().hex,
            "question": question,
            "text": question,
        },
    }


# ---------------------------------------------------------------------------
# Local bus test (dry-run / unit mode)
# ---------------------------------------------------------------------------


def run_local_test(questions: list[str]) -> dict[str, Any]:
    """Run the QUERY test using a local in-process bus (no Azure needed).

    Creates a NetworkGraphStore with local transport, seeds a few facts,
    then sends QUERY events and checks that receive_query_events() drains them.

    Returns:
        Results dict with pass/fail per question.
    """
    print("=" * 70)
    print("QUERY EVENT TEST (local bus mode)")
    print(f"Questions: {len(questions)}")
    print("=" * 70)
    print()

    try:
        from amplihack.memory.network_store import NetworkGraphStore
        from amplihack.memory.memory_store import InMemoryGraphStore
    except ImportError:
        print("ERROR: amplihack package not available. Install with: pip install -e .")
        return {"mode": "local", "error": "import failed"}

    store = NetworkGraphStore(
        agent_id="test-agent",
        local_store=InMemoryGraphStore(),
        transport="local",
    )

    results = []
    passed = 0

    try:
        for i, question in enumerate(questions, 1):
            # Simulate a QUERY event arriving on the bus by constructing one directly
            # and pushing it into the store's internal queue (mimicking bus delivery)
            try:
                from amplihack.agents.goal_seeking.hive_mind.event_bus import BusEvent
                event = BusEvent(
                    event_id=uuid.uuid4().hex,
                    event_type="QUERY",
                    source_agent="test-client",
                    timestamp=time.time(),
                    payload={
                        "query_id": uuid.uuid4().hex,
                        "question": question,
                        "text": question,
                    },
                )
                # Directly invoke handle_event to simulate bus delivery
                store._handle_event(event)
            except Exception as exc:
                logger.debug("Failed to simulate event: %s", exc, exc_info=True)
                results.append({"question": question, "passed": False, "error": str(exc)})
                print(f"  Q{i:2d}: FAIL (simulation error) — {question[:50]}")
                continue

            # Drain query events
            drained = store.receive_query_events()
            ok = len(drained) > 0
            if ok:
                passed += 1
            status = "PASS" if ok else "FAIL"
            print(f"  Q{i:2d}: {status} — {question[:55]}")
            results.append({"question": question, "passed": ok, "drained": len(drained)})
    finally:
        store.close()

    print()
    print(f"Results: {passed}/{len(questions)} passed")

    return {
        "mode": "local",
        "passed": passed,
        "total": len(questions),
        "questions": results,
    }


# ---------------------------------------------------------------------------
# Azure Service Bus test
# ---------------------------------------------------------------------------


class QueryTestClient:
    """Send QUERY events and collect QUERY_RESPONSE replies via Azure Service Bus."""

    def __init__(
        self,
        connection_string: str,
        topic_name: str,
        subscription_name: str,
        timeout: float,
        source_agent: str,
    ) -> None:
        from azure.servicebus import ServiceBusClient as _SBClient

        self._connection_string = connection_string
        self._topic_name = topic_name
        self._subscription_name = subscription_name
        self._timeout = timeout
        self._source_agent = source_agent

        self._client = _SBClient.from_connection_string(connection_string)
        self._sender = self._client.get_topic_sender(topic_name=topic_name)
        self._receiver = self._client.get_subscription_receiver(
            topic_name=topic_name,
            subscription_name=subscription_name,
        )

        # Pending queries: query_id -> {event, results}
        self._pending: dict[str, dict[str, Any]] = {}
        self._pending_lock = threading.Lock()

        self._running = True
        self._thread = threading.Thread(
            target=self._receive_loop,
            daemon=True,
            name="query-test-receiver",
        )
        self._thread.start()

    def send_query(self, question: str) -> list[dict[str, Any]]:
        """Send a single QUERY event and wait for responses."""
        from azure.servicebus import ServiceBusMessage

        query_id = uuid.uuid4().hex
        event_obj = threading.Event()
        collected: list[dict[str, Any]] = []

        with self._pending_lock:
            self._pending[query_id] = {"event": event_obj, "results": collected}

        payload = {
            "event_id": uuid.uuid4().hex,
            "event_type": "QUERY",
            "source_agent": self._source_agent,
            "timestamp": time.time(),
            "payload": {
                "query_id": query_id,
                "question": question,
                "text": question,
            },
        }

        try:
            msg = ServiceBusMessage(
                body=json.dumps(payload, separators=(",", ":")),
                application_properties={
                    "event_type": "QUERY",
                    "source_agent": self._source_agent,
                },
            )
            self._sender.send_messages(msg)
            logger.debug("Sent QUERY id=%s: %r", query_id, question)
        except Exception:
            logger.exception("Failed to send QUERY event")
            with self._pending_lock:
                self._pending.pop(query_id, None)
            return []

        event_obj.wait(timeout=self._timeout)

        with self._pending_lock:
            self._pending.pop(query_id, None)

        return collected

    def close(self) -> None:
        self._running = False
        try:
            self._receiver.close()
        except Exception:
            pass
        try:
            self._sender.close()
        except Exception:
            pass
        try:
            self._client.close()
        except Exception:
            pass
        if self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def _receive_loop(self) -> None:
        while self._running:
            try:
                messages = self._receiver.receive_messages(
                    max_message_count=50, max_wait_time=1
                )
                for msg in messages:
                    try:
                        self._handle_message(msg)
                        self._receiver.complete_message(msg)
                    except Exception:
                        logger.debug("Error handling message", exc_info=True)
                        try:
                            self._receiver.abandon_message(msg)
                        except Exception:
                            pass
            except Exception:
                if self._running:
                    logger.debug("Error in receive loop", exc_info=True)
                time.sleep(0.5)

    def _handle_message(self, msg: Any) -> None:
        try:
            body = b"".join(msg.body) if hasattr(msg.body, "__iter__") else msg.body
            if isinstance(body, (bytes, bytearray)):
                body = body.decode("utf-8")
            data = json.loads(body)
        except Exception:
            logger.debug("Failed to parse message body", exc_info=True)
            return

        event_type = data.get("event_type", "")
        if event_type != "QUERY_RESPONSE":
            return

        inner = data.get("payload", {})
        query_id = inner.get("query_id", "")

        with self._pending_lock:
            pending = self._pending.get(query_id)

        if pending is None:
            return

        responder = inner.get("responder", data.get("source_agent", "?"))
        results = inner.get("results", [])
        pending["results"].extend(results)
        pending["event"].set()
        logger.debug(
            "Received QUERY_RESPONSE from %s for query_id=%s (%d results)",
            responder,
            query_id,
            len(results),
        )


def run_azure_test(
    questions: list[str],
    connection_string: str,
    topic_name: str,
    subscription_name: str,
    timeout: float,
    source_agent: str,
) -> dict[str, Any]:
    """Run 10 QUERY events against the live Azure hive and report results."""
    print("=" * 70)
    print("QUERY EVENT TEST (Azure Service Bus mode)")
    print(f"Topic: {topic_name}")
    print(f"Subscription: {subscription_name}")
    print(f"Questions: {len(questions)}")
    print(f"Timeout per query: {timeout}s")
    print("=" * 70)
    print()

    client = QueryTestClient(
        connection_string=connection_string,
        topic_name=topic_name,
        subscription_name=subscription_name,
        timeout=timeout,
        source_agent=source_agent,
    )

    results = []
    passed = 0

    try:
        for i, question in enumerate(questions, 1):
            if i > 1:
                time.sleep(3)  # Brief pause between queries to avoid Service Bus throttling
            t0 = time.time()
            responses = client.send_query(question)
            elapsed = time.time() - t0
            ok = len(responses) > 0
            if ok:
                passed += 1
            status = "PASS" if ok else "FAIL"
            top = responses[0].get("content", "") if responses else ""
            print(
                f"  Q{i:2d}: {status} ({len(responses):2d} results, {elapsed:.1f}s)"
                f" — {question[:45]}"
            )
            if top:
                print(f"        top: {top[:70]}")
            results.append(
                {
                    "question": question,
                    "passed": ok,
                    "response_count": len(responses),
                    "elapsed_s": round(elapsed, 2),
                    "top_result": top,
                }
            )
    finally:
        client.close()

    print()
    print(f"Results: {passed}/{len(questions)} passed")

    return {
        "mode": "azure_service_bus",
        "topic": topic_name,
        "passed": passed,
        "total": len(questions),
        "questions": results,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send 10 QUERY events to the hive and verify QUERY_RESPONSE replies."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use local in-process bus (no Azure required)",
    )
    parser.add_argument(
        "--topic",
        default=os.environ.get("AMPLIHACK_TOPIC_NAME", "hive-graph"),
        help="Service Bus topic name (default: hive-graph)",
    )
    parser.add_argument(
        "--subscription",
        default=os.environ.get("QUERY_RESPONSE_SUBSCRIPTION", "eval-query-agent"),
        help="Subscription for receiving responses (default: eval-query-agent)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("QUERY_TIMEOUT", "15")),
        help="Seconds to wait per query (default: 15)",
    )
    parser.add_argument(
        "--source-agent",
        default=os.environ.get("AMPLIHACK_SOURCE_AGENT", "query-test-client"),
        help="Source agent identifier (default: query-test-client)",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Path to write JSON results",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.dry_run:
        results = run_local_test(_TEST_QUESTIONS)
    else:
        connection_string = os.environ.get("AMPLIHACK_MEMORY_CONNECTION_STRING", "")
        if not connection_string:
            logger.error(
                "AMPLIHACK_MEMORY_CONNECTION_STRING env var is required for live test.\n"
                "Use --dry-run for local testing."
            )
            return 1
        results = run_azure_test(
            questions=_TEST_QUESTIONS,
            connection_string=connection_string,
            topic_name=args.topic,
            subscription_name=args.subscription,
            timeout=args.timeout,
            source_agent=args.source_agent,
        )

    if args.output:
        with open(args.output, "w") as fh:
            json.dump(results, fh, indent=2)
        print(f"\nResults written to: {args.output}")

    passed = results.get("passed", 0)
    total = results.get("total", len(_TEST_QUESTIONS))
    return 0 if passed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
