"""Tests for eval_monitor.py."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_MONITOR_PATH = Path(__file__).parent.parent / "eval_monitor.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("eval_monitor", _MONITOR_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestEvalMonitor:
    def test_main_defaults_consumer_group_to_eval_reader(self, monkeypatch):
        monkeypatch.setenv(
            "EH_CONN",
            "Endpoint=sb://fake.servicebus.windows.net/;SharedAccessKeyName=x;SharedAccessKey=y",
        )
        monkeypatch.delenv("AMPLIHACK_EVAL_MONITOR_CONSUMER_GROUP", raising=False)
        mod = _load_module()

        with (
            patch.object(mod, "EvalMonitor") as monitor_cls,
            patch.object(mod.signal, "signal"),
        ):
            monitor_instance = monitor_cls.return_value
            monitor_instance.run.return_value = None
            monkeypatch.setattr(sys, "argv", ["eval_monitor.py"])

            assert mod.main() == 0

        assert monitor_cls.call_args.kwargs["consumer_group"] == "eval-reader"

    def test_run_uses_configured_consumer_group(self):
        mod = _load_module()
        monitor = mod.EvalMonitor(
            connection_string="Endpoint=sb://fake.servicebus.windows.net/;SharedAccessKeyName=x;SharedAccessKey=y",
            response_hub="eval-responses",
            consumer_group="eval-reader",
            agent_count=100,
            output_path="",
        )
        fake_consumer = MagicMock()
        fake_thread = MagicMock()

        with (
            patch("azure.eventhub.EventHubConsumerClient", create=True) as consumer_cls,
            patch.object(mod.threading, "Thread", return_value=fake_thread),
        ):
            consumer_cls.from_connection_string.return_value = fake_consumer
            monitor.run()

        consumer_cls.from_connection_string.assert_called_once_with(
            "Endpoint=sb://fake.servicebus.windows.net/;SharedAccessKeyName=x;SharedAccessKey=y",
            consumer_group="eval-reader",
            eventhub_name="eval-responses",
        )

    def test_consume_event_logs_malformed_json_and_checkpoints(self, caplog):
        mod = _load_module()
        monitor = mod.EvalMonitor(
            connection_string="conn",
            response_hub="hub",
            consumer_group="eval-reader",
            agent_count=10,
            output_path="",
        )
        partition_context = MagicMock()
        partition_context.partition_id = "5"
        event = MagicMock()
        event.body_as_str.return_value = "{not-json"

        with caplog.at_level(logging.WARNING):
            monitor._consume_event(partition_context, event)

        partition_context.update_checkpoint.assert_called_once_with(event)
        assert any(
            "Skipping malformed eval monitor event on partition 5" in record.message
            for record in caplog.records
        )

    def test_consume_event_logs_handler_failure_and_checkpoints(self, caplog):
        mod = _load_module()
        monitor = mod.EvalMonitor(
            connection_string="conn",
            response_hub="hub",
            consumer_group="eval-reader",
            agent_count=10,
            output_path="",
        )
        partition_context = MagicMock()
        partition_context.partition_id = "7"
        event = MagicMock()
        event.body_as_str.return_value = '{"event_type":"AGENT_ONLINE","agent_id":"agent-7"}'

        with (
            patch.object(monitor, "_handle_event", side_effect=RuntimeError("boom")),
            caplog.at_level(logging.ERROR),
        ):
            monitor._consume_event(partition_context, event)

        partition_context.update_checkpoint.assert_called_once_with(event)
        assert any(
            "Failed to process eval monitor event_type=AGENT_ONLINE agent_id=agent-7"
            in record.message
            for record in caplog.records
        )
