from __future__ import annotations

import importlib.util
from pathlib import Path

_AZURE_DIR = Path(__file__).resolve().parents[1]


def _load_wrapper(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, _AZURE_DIR / filename)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wrapper_injects_env_defaults_when_flags_are_missing():
    env = {
        "EH_CONN": "Endpoint=sb://example/",
        "AMPLIHACK_EH_INPUT_HUB": "hive-events-test",
        "AMPLIHACK_EH_RESPONSE_HUB": "eval-responses-test",
    }

    for filename, module_name in [
        ("eval_distributed.py", "eval_distributed_wrapper"),
        ("eval_distributed_security.py", "eval_distributed_security_wrapper"),
        ("eval_retrieval_smoke.py", "eval_retrieval_smoke_wrapper"),
    ]:
        module = _load_wrapper(filename, module_name)
        argv = [filename, "--agents", "100"]
        assert module._inject_env_defaults(argv, env) == [
            filename,
            "--agents",
            "100",
            "--connection-string",
            "Endpoint=sb://example/",
            "--input-hub",
            "hive-events-test",
            "--response-hub",
            "eval-responses-test",
        ]


def test_wrapper_does_not_override_explicit_flags():
    env = {
        "EH_CONN": "Endpoint=sb://example/",
        "AMPLIHACK_EH_INPUT_HUB": "hive-events-test",
        "AMPLIHACK_EH_RESPONSE_HUB": "eval-responses-test",
    }

    for filename, module_name in [
        ("eval_distributed.py", "eval_distributed_wrapper_explicit"),
        ("eval_distributed_security.py", "eval_distributed_security_wrapper_explicit"),
        ("eval_retrieval_smoke.py", "eval_retrieval_smoke_wrapper_explicit"),
    ]:
        module = _load_wrapper(filename, module_name)
        argv = [
            filename,
            "--connection-string",
            "explicit-conn",
            "--input-hub",
            "explicit-input",
            "--response-hub",
            "explicit-response",
        ]
        assert module._inject_env_defaults(argv, env) == argv


def test_wrapper_respects_equals_style_flags():
    env = {
        "EH_CONN": "Endpoint=sb://example/",
        "AMPLIHACK_EH_INPUT_HUB": "hive-events-test",
        "AMPLIHACK_EH_RESPONSE_HUB": "eval-responses-test",
    }

    for filename, module_name in [
        ("eval_distributed.py", "eval_distributed_wrapper_equals"),
        ("eval_distributed_security.py", "eval_distributed_security_wrapper_equals"),
        ("eval_retrieval_smoke.py", "eval_retrieval_smoke_wrapper_equals"),
    ]:
        module = _load_wrapper(filename, module_name)
        argv = [
            filename,
            "--connection-string=explicit-conn",
            "--input-hub=explicit-input",
            "--response-hub=explicit-response",
        ]
        assert module._inject_env_defaults(argv, env) == argv
