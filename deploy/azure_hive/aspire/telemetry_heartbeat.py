"""Keep the Aspire dashboard alive with a small stream of goal-runtime spans."""

from __future__ import annotations

import logging
import os
import signal
import time
from types import FrameType

from amplihack.observability import configure_otel, start_span

LOG = logging.getLogger("amplihack.aspire.telemetry_heartbeat")
_STOP = False


def _handle_signal(signum: int, _frame: FrameType | None) -> None:
    global _STOP
    LOG.info("telemetry heartbeat received signal=%s", signum)
    _STOP = True


def _sleep_until_next_tick(interval_seconds: float) -> None:
    deadline = time.monotonic() + interval_seconds
    while not _STOP and time.monotonic() < deadline:
        time.sleep(0.2)


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("AMPLIHACK_OTEL_HEARTBEAT_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    configure_otel(
        service_name=os.environ.get("OTEL_SERVICE_NAME", "amplihack.aspire.telemetry-heartbeat"),
        component="aspire-heartbeat",
    )

    interval_seconds = float(os.environ.get("AMPLIHACK_OTEL_HEARTBEAT_SECONDS", "15"))
    LOG.info(
        "telemetry heartbeat started protocol=%s endpoint=%s interval=%ss",
        os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", ""),
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
        interval_seconds,
    )

    tick = 0
    while not _STOP:
        with start_span(
            "aspire.telemetry_heartbeat",
            tracer_name=__name__,
            attributes={
                "amplihack.heartbeat.tick": tick,
                "amplihack.heartbeat.pid": os.getpid(),
            },
        ):
            LOG.info("telemetry heartbeat tick=%s", tick)
        tick += 1
        _sleep_until_next_tick(interval_seconds)

    LOG.info("telemetry heartbeat stopped")


if __name__ == "__main__":
    main()
