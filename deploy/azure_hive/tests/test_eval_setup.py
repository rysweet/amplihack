from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path
from unittest.mock import patch


_EVAL_SETUP_PATH = Path(__file__).parent.parent / "eval_setup.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("eval_setup", _EVAL_SETUP_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_check_event_hub_namespace_fails_when_sdk_missing():
    mod = _load_module()
    original_import = builtins.__import__

    def _missing_eventhub(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "azure.eventhub":
            raise ImportError("azure-eventhub missing")
        return original_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=_missing_eventhub):
        ok, input_hub, response_hub = mod.check_event_hub_namespace(
            "Endpoint=sb://example.servicebus.windows.net/",
            "test-hive",
        )

    assert ok is False
    assert input_hub == "hive-events-test-hive"
    assert response_hub == "eval-responses-test-hive"


def test_ensure_response_consumer_groups_check_only_reports_missing_without_creating():
    mod = _load_module()

    with patch.object(mod, "_az", return_value=(True, '["$Default"]')) as az_mock:
        ok = mod._ensure_response_consumer_groups(
            "Endpoint=sb://example.servicebus.windows.net/;SharedAccessKeyName=x;SharedAccessKey=y",
            "eval-responses-test",
            check_only=True,
        )

    assert ok is False
    assert az_mock.call_count == 1


def test_ensure_response_consumer_groups_fails_when_list_command_fails():
    mod = _load_module()

    with patch.object(mod, "_az", return_value=(False, "")):
        ok = mod._ensure_response_consumer_groups(
            "Endpoint=sb://example.servicebus.windows.net/;SharedAccessKeyName=x;SharedAccessKey=y",
            "eval-responses-test",
        )

    assert ok is False
