#!/usr/bin/env python3
"""Validate and emit the canonical workflow-owned execution_root contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from orch_helper import validate_execution_root as _validate_execution_root

validate_execution_root = _validate_execution_root
setup_execution_root = _validate_execution_root


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or len(args) > 2:
        print(
            "Usage: setup_execution_root.py EXECUTION_ROOT [AUTHORITATIVE_REPO]",
            file=sys.stderr,
        )
        return 2

    execution_root = args[0]
    authoritative_repo = args[1] if len(args) == 2 else None
    try:
        result = validate_execution_root(
            execution_root,
            authoritative_repo=authoritative_repo,
        )
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
