"""Shared environment utilities for recipe adapters.

Centralizes child-process environment construction so that env
cleanup (stripping CLAUDECODE, propagating session tree vars) happens
in exactly one place.
"""

from __future__ import annotations

import os
import uuid

# Environment variables that are stripped from child processes.
_STRIPPED_VARS = frozenset({"CLAUDECODE"})


def build_child_env() -> dict[str, str]:
    """Build a clean environment dict for child processes.

    * Strips CLAUDECODE so nested ``claude`` invocations are not blocked.
    * Propagates session-tree env vars, incrementing depth by 1.
    * Generates a tree ID when none exists yet.
    """
    child_env = {k: v for k, v in os.environ.items() if k not in _STRIPPED_VARS}

    # Propagate session tree context (#2758)
    current_depth = int(os.environ.get("AMPLIHACK_SESSION_DEPTH", "0"))
    tree_id = os.environ.get("AMPLIHACK_TREE_ID") or uuid.uuid4().hex[:8]

    child_env["AMPLIHACK_TREE_ID"] = tree_id
    child_env["AMPLIHACK_SESSION_DEPTH"] = str(current_depth + 1)
    child_env["AMPLIHACK_MAX_DEPTH"] = os.environ.get("AMPLIHACK_MAX_DEPTH", "3")
    child_env["AMPLIHACK_MAX_SESSIONS"] = os.environ.get("AMPLIHACK_MAX_SESSIONS", "10")

    return child_env
