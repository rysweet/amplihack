#!/usr/bin/env python3
"""Distributed eval monitoring pipeline.

Connects to the response Event Hub and streams per-agent and aggregate
progress metrics in real time during an eval run.  Emits structured OTel
spans for each agent lifecycle event so the Aspire dashboard (or any OTLP
backend) shows a live view.

Also writes a JSON progress file that eval_report.py can consume.

Usage:
    # Stream live metrics to terminal (Ctrl-C to stop)
    python deploy/azure_hive/eval_monitor.py \\
        --connection-string "$EH_CONN" \\
        --response-hub eval-responses-amplihive \\
        --agents 100 \\
        --output monitor_progress.json

    # Bounded telemetry spotcheck: prove remote agents are processing work
    python deploy/azure_hive/eval_monitor.py \\
        --connection-string "$EH_CONN" \\
        --response-hub eval-responses-amplihive \\
        --agents 100 \\
        --wait-for-online 100 \\
        --wait-for-progress 100 \\
        --max-wait-seconds 180

    # With OTel (Aspire dashboard):
    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \\
        OTEL_EXPORTER_OTLP_PROTOCOL=grpc \\
        AMPLIHACK_OTEL_ENABLED=true \\
        python deploy/azure_hive/eval_monitor.py ...

Environment:
    EH_CONN                    Event Hubs namespace connection string
    AMPLIHACK_EH_RESPONSE_HUB  Response hub name override
    AMPLIHACK_EVAL_MONITOR_CONSUMER_GROUP  Response-hub consumer group
    HIVE_AGENT_COUNT           Expected agent count
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [eval_monitor] %(levelname)s: %(message)s",
)
logger = logging.getLogger("eval_monitor")

# Add repo src to path for observability imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

try:
    from amplihack.observability import configure_otel, start_span  # type: ignore[assignment]
except ImportError:  # pragma: no cover
    # Graceful degradation — monitoring still works without OTel.
    # These stubs match the signatures in amplihack.observability so that
    # callers can use them unconditionally.
    import contextlib as _contextlib

    def configure_otel(  # type: ignore[misc]
        service_name: str, *, component: str = "", attributes: Any = None
    ) -> bool:
        return False

    def start_span(  # type: ignore[misc]
        name: str, *, tracer_name: str, attributes: Any = None
    ) -> Any:
        return _contextlib.nullcontext()


# ---------------------------------------------------------------------------
# Per-agent state tracker
# ---------------------------------------------------------------------------


class AgentStats:
    __slots__ = (
        "answer_count",
        "last_event_ts",
        "online",
        "phases_seen",
        "progress_count",
        "ready",
    )

    def __init__(self) -> None:
        self.online: bool = False
        self.ready: bool = False
        self.progress_count: int = 0
        self.answer_count: int = 0
        self.last_event_ts: float = 0.0
        self.phases_seen: list[str] = []


class EvalMonitor:
    def __init__(
        self,
        connection_string: str,
        response_hub: str,
        consumer_group: str,
        agent_count: int,
        output_path: str,
    ) -> None:
        self._conn = connection_string
        self._hub = response_hub
        self._consumer_group = consumer_group
        self._agent_count = agent_count
        self._output_path = output_path

        self._lock = threading.Lock()
        self._agents: dict[str, AgentStats] = defaultdict(AgentStats)
        self._answer_count = 0
        self._start_time = time.time()
        self._shutdown = threading.Event()
        self._consumer: Any | None = None

        # OTel
        configure_otel(
            service_name=os.environ.get("OTEL_SERVICE_NAME", "amplihack.eval-monitor"),
            component="eval-monitor",
            attributes={"amplihack.agent_count": agent_count},
        )

    def _handle_event(self, body: dict[str, Any]) -> None:
        event_type = body.get("event_type", "")
        agent_id = body.get("agent_id", "")
        ts = time.time()

        with self._lock:
            if event_type == "AGENT_ONLINE":
                self._agents[agent_id].online = True
                self._agents[agent_id].last_event_ts = ts
                self._emit_otel_event("agent.online", agent_id, body)

            elif event_type == "AGENT_READY":
                self._agents[agent_id].ready = True
                self._agents[agent_id].last_event_ts = ts
                self._emit_otel_event("agent.ready", agent_id, body)

            elif event_type == "AGENT_PROGRESS":
                stats = self._agents[agent_id]
                count = int(body.get("processed_count", 0) or 0)
                stats.progress_count = max(stats.progress_count, count)
                stats.last_event_ts = ts
                phase = body.get("phase", "")
                if phase and phase not in stats.phases_seen:
                    stats.phases_seen.append(phase)
                self._emit_otel_event("agent.progress", agent_id, body)

            elif event_type == "EVAL_ANSWER":
                self._answer_count += 1
                if agent_id:
                    self._agents[agent_id].answer_count += 1
                    self._agents[agent_id].last_event_ts = ts
                self._emit_otel_event("agent.answer", agent_id, body)

            elif event_type == "AGENT_SHUTDOWN":
                self._emit_otel_event("agent.shutdown", agent_id, body)
                logger.warning(
                    "AGENT_SHUTDOWN from %s: reason=%s detail=%s",
                    agent_id,
                    body.get("reason", ""),
                    body.get("detail", ""),
                )

    def _emit_otel_event(self, span_name: str, agent_id: str, body: dict[str, Any]) -> None:
        """Fire-and-forget OTel span for the event (no-op without OTel)."""
        try:
            with start_span(
                span_name,
                tracer_name=__name__,
                attributes={
                    "amplihack.agent_id": agent_id,
                    "amplihack.event_type": body.get("event_type", ""),
                    "amplihack.processed_count": int(body.get("processed_count", 0) or 0),
                    "amplihack.phase": body.get("phase", ""),
                },
            ):
                pass  # span recorded on context exit
        except Exception:
            pass  # never let OTel break monitoring

    def _print_status(self) -> None:
        """Print a one-line live status update."""
        with self._lock:
            online = sum(1 for s in self._agents.values() if s.online)
            ready = sum(1 for s in self._agents.values() if s.ready)
            total_progress = sum(s.progress_count for s in self._agents.values())
            answers = self._answer_count

        elapsed = time.time() - self._start_time
        h, rem = divmod(int(elapsed), 3600)
        m, s = divmod(rem, 60)
        elapsed_str = f"{h:02d}:{m:02d}:{s:02d}"

        print(
            f"\r[{elapsed_str}] "
            f"online={online}/{self._agent_count} "
            f"ready={ready}/{self._agent_count} "
            f"progress={total_progress} turns processed "
            f"answers={answers}          ",
            end="",
            flush=True,
        )

    def _snapshot(self) -> dict[str, Any]:
        """Build a JSON-serialisable progress snapshot."""
        with self._lock:
            agents_summary = {
                agent_id: {
                    "online": s.online,
                    "ready": s.ready,
                    "progress_count": s.progress_count,
                    "answer_count": s.answer_count,
                    "phases_seen": list(s.phases_seen),
                    "last_event_age_s": round(time.time() - s.last_event_ts, 1)
                    if s.last_event_ts
                    else None,
                }
                for agent_id, s in self._agents.items()
            }
            return {
                "elapsed_s": round(time.time() - self._start_time, 1),
                "agent_count": self._agent_count,
                "agents_online": sum(1 for s in self._agents.values() if s.online),
                "agents_ready": sum(1 for s in self._agents.values() if s.ready),
                "total_progress_count": sum(s.progress_count for s in self._agents.values()),
                "total_answers": self._answer_count,
                "agents": agents_summary,
            }

    def _write_snapshot(self) -> None:
        """Persist progress snapshot to disk."""
        if not self._output_path:
            return
        try:
            snapshot = self._snapshot()
            Path(self._output_path).write_text(json.dumps(snapshot, indent=2))
        except Exception:
            pass  # never crash on write

    def _checkpoint_event(self, partition_context: Any, event: Any) -> None:
        update_checkpoint = getattr(partition_context, "update_checkpoint", None)
        if callable(update_checkpoint):
            update_checkpoint(event)

    def stop(self) -> None:
        self._shutdown.set()
        consumer = self._consumer
        if consumer is None:
            return
        try:
            consumer.close()
        except Exception:
            logger.exception("Failed to close eval monitor consumer cleanly")

    def _status_counts(self) -> dict[str, int]:
        snapshot = self._snapshot()
        progress_agents = sum(
            1 for agent in snapshot["agents"].values() if int(agent["progress_count"]) > 0
        )
        return {
            "online": int(snapshot["agents_online"]),
            "ready": int(snapshot["agents_ready"]),
            "progress_agents": progress_agents,
            "answers": int(snapshot["total_answers"]),
        }

    def criteria_status(
        self,
        *,
        min_online: int = 0,
        min_ready: int = 0,
        min_progress_agents: int = 0,
        min_answers: int = 0,
    ) -> tuple[bool, list[str], dict[str, int]]:
        counts = self._status_counts()
        unmet: list[str] = []
        requirements = (
            ("online", min_online),
            ("ready", min_ready),
            ("progress_agents", min_progress_agents),
            ("answers", min_answers),
        )
        for key, required in requirements:
            if required > counts[key]:
                unmet.append(f"{key} {counts[key]}/{required}")
        return not unmet, unmet, counts

    def _consume_event(self, partition_context: Any, event: Any) -> None:
        if event is None:
            return

        raw_body = event.body_as_str()
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            logger.warning(
                "Skipping malformed eval monitor event on partition %s: %s",
                getattr(partition_context, "partition_id", "?"),
                exc,
            )
            self._checkpoint_event(partition_context, event)
            return

        try:
            self._handle_event(body)
        except Exception:
            logger.exception(
                "Failed to process eval monitor event_type=%s agent_id=%s",
                body.get("event_type", ""),
                body.get("agent_id", ""),
            )
        finally:
            self._checkpoint_event(partition_context, event)

    def wait_for_criteria(
        self,
        *,
        min_online: int = 0,
        min_ready: int = 0,
        min_progress_agents: int = 0,
        min_answers: int = 0,
        max_wait_seconds: int = 120,
        poll_interval_seconds: float = 1.0,
    ) -> int:
        if max_wait_seconds <= 0:
            raise ValueError("max_wait_seconds must be > 0 for telemetry spotchecks")

        monitor_thread = threading.Thread(target=self.run, daemon=True)
        monitor_thread.start()

        deadline = time.time() + max_wait_seconds
        try:
            while time.time() < deadline:
                satisfied, _, counts = self.criteria_status(
                    min_online=min_online,
                    min_ready=min_ready,
                    min_progress_agents=min_progress_agents,
                    min_answers=min_answers,
                )
                if satisfied:
                    logger.info(
                        "Telemetry spotcheck passed: online=%d ready=%d progress_agents=%d answers=%d",
                        counts["online"],
                        counts["ready"],
                        counts["progress_agents"],
                        counts["answers"],
                    )
                    return 0
                time.sleep(poll_interval_seconds)
        finally:
            self.stop()
            monitor_thread.join(timeout=10)
            self._write_snapshot()

        _, unmet, counts = self.criteria_status(
            min_online=min_online,
            min_ready=min_ready,
            min_progress_agents=min_progress_agents,
            min_answers=min_answers,
        )
        logger.error(
            "Telemetry spotcheck timed out after %ds: %s (online=%d ready=%d progress_agents=%d answers=%d)",
            max_wait_seconds,
            ", ".join(unmet),
            counts["online"],
            counts["ready"],
            counts["progress_agents"],
            counts["answers"],
        )
        return 2

    def run(self) -> None:
        """Start listening and printing until interrupted."""
        try:
            from azure.eventhub import EventHubConsumerClient  # type: ignore[import-unresolved]
        except ImportError:
            logger.error("azure-eventhub not installed. Run: pip install azure-eventhub")
            sys.exit(1)

        def _on_event(partition_context: Any, event: Any) -> None:
            self._consume_event(partition_context, event)

        consumer = EventHubConsumerClient.from_connection_string(
            self._conn,
            consumer_group=self._consumer_group,
            eventhub_name=self._hub,
        )
        self._consumer = consumer

        logger.info("Monitoring eval run on hub '%s'...", self._hub)
        logger.info("Press Ctrl-C to stop.")

        snapshot_interval = 30  # seconds
        last_snapshot = time.time()

        # Status printer runs on a separate thread
        def _status_loop() -> None:
            while not self._shutdown.is_set():
                self._print_status()
                time.sleep(1)

        status_thread = threading.Thread(target=_status_loop, daemon=True)
        status_thread.start()

        # Periodic snapshot writer
        def _snapshot_loop() -> None:
            nonlocal last_snapshot
            while not self._shutdown.is_set():
                now = time.time()
                if now - last_snapshot >= snapshot_interval:
                    self._write_snapshot()
                    last_snapshot = now
                time.sleep(5)

        snapshot_thread = threading.Thread(target=_snapshot_loop, daemon=True)
        snapshot_thread.start()

        try:
            consumer.receive(
                on_event=_on_event,
                starting_position="@latest",
            )
        except KeyboardInterrupt:
            pass
        finally:
            self._shutdown.set()
            try:
                consumer.close()
            except Exception:
                pass
            self._consumer = None
            print()  # newline after status line
            self._write_snapshot()

        # Final summary
        snapshot = self._snapshot()
        print(f"\n{'=' * 60}")
        print(f"  Monitoring summary ({snapshot['elapsed_s']:.0f}s elapsed)")
        print(f"  Agents online:   {snapshot['agents_online']}/{self._agent_count}")
        print(f"  Agents ready:    {snapshot['agents_ready']}/{self._agent_count}")
        print(f"  Total progress:  {snapshot['total_progress_count']} turns")
        print(f"  Total answers:   {snapshot['total_answers']}")
        if self._output_path:
            print(f"  Progress file:   {self._output_path}")
        print(f"{'=' * 60}\n")


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
        default=os.environ.get("AMPLIHACK_EVAL_MONITOR_CONSUMER_GROUP", "eval-reader"),
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
        logger.error("--connection-string or EH_CONN is required")
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
        (
            args.wait_for_online,
            args.wait_for_ready,
            args.wait_for_progress,
            args.wait_for_answers,
        )
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
