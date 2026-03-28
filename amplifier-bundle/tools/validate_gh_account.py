#!/usr/bin/env python3
"""Validate that ``gh auth status`` matches the expected login and is usable for writes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from orch_helper import validate_gh_auth_status as _validate_gh_auth_status


def validate_gh_account(
    status_output: str,
    expected_account: str,
    status_exit_code: int = 0,
) -> dict[str, str]:
    return _validate_gh_auth_status(
        status_output,
        expected_account,
        command_exit_code=status_exit_code,
    )


validate_expected_gh_account = validate_gh_account
require_expected_gh_account = validate_gh_account


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) not in {1, 2}:
        print(
            "Usage: validate_gh_account.py EXPECTED_GH_ACCOUNT [GH_AUTH_STATUS_EXIT_CODE]",
            file=sys.stderr,
        )
        return 2

    expected_account = args[0]
    try:
        status_exit_code = int(args[1]) if len(args) == 2 else 0
    except ValueError:
        print("GH_AUTH_STATUS_EXIT_CODE must be an integer", file=sys.stderr)
        return 2
    status_output = sys.stdin.read()
    try:
        result = validate_gh_account(status_output, expected_account, status_exit_code)
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
