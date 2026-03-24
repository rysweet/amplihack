#!/usr/bin/env python3
"""Compatibility wrapper for distributed eval now living in amplihack-agent-eval."""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Mapping, Sequence

_ENV_DEFAULTS = (
    ("--connection-string", "EH_CONN"),
    ("--input-hub", "AMPLIHACK_EH_INPUT_HUB"),
    ("--response-hub", "AMPLIHACK_EH_RESPONSE_HUB"),
)


def _flag_is_present(argv: Sequence[str], flag: str) -> bool:
    flag_prefix = f"{flag}="
    return any(
        token == flag or token.startswith(flag_prefix)
        for token in argv[1:]
        if token.startswith("--")
    )


def _inject_env_defaults(argv: Sequence[str], env: Mapping[str, str] | None = None) -> list[str]:
    env_values = env or os.environ
    updated = list(argv)
    for flag, env_key in _ENV_DEFAULTS:
        if _flag_is_present(updated, flag):
            continue
        value = str(env_values.get(env_key, "")).strip()
        if value:
            updated.extend([flag, value])
    return updated


def main() -> int:
    upstream_main = importlib.import_module("amplihack_eval.azure.eval_distributed").main
    original_argv = sys.argv[:]
    try:
        sys.argv = _inject_env_defaults(original_argv)
        return upstream_main()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    raise SystemExit(main())
