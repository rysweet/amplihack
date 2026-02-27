#!/usr/bin/env python3
"""
Session tree management for amplihack orchestration.

Prevents infinite recursion by tracking active sessions in a tree structure.
Enforces max depth and max concurrent session limits with FIFO queueing.

Environment variables:
  AMPLIHACK_TREE_ID        - shared ID for this orchestration tree (auto-generated at root)
  AMPLIHACK_SESSION_DEPTH  - current depth (0 at root, incremented by orchestrator)
  AMPLIHACK_MAX_DEPTH      - max allowed depth (default: 3)
  AMPLIHACK_MAX_SESSIONS   - max concurrent active sessions per tree (default: 10)

State file: /tmp/amplihack-session-trees/{tree_id}.json
Lock file:  /tmp/amplihack-session-trees/{tree_id}.lock

CLI Usage:
  # Check if a new child session can be spawned
  python3 session_tree.py check
  # Output: ALLOWED or BLOCKED:<reason>

  # Register current session
  python3 session_tree.py register <session_id> [parent_id]
  # Output: TREE_ID=<id> DEPTH=<n>

  # Mark session complete
  python3 session_tree.py complete <session_id>

  # Show tree status
  python3 session_tree.py status
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

DEFAULT_MAX_DEPTH = 3
DEFAULT_MAX_SESSIONS = 10
STATE_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "amplihack-session-trees"


# ─────────────────────────────────────────────────────────────────────────────
# Environment helpers
# ─────────────────────────────────────────────────────────────────────────────


def get_tree_context() -> dict:
    """Read current session tree context from environment."""
    return {
        "tree_id": os.environ.get("AMPLIHACK_TREE_ID", ""),
        "session_id": os.environ.get("AMPLIHACK_SESSION_ID", ""),
        "depth": int(os.environ.get("AMPLIHACK_SESSION_DEPTH", "0")),
        "max_depth": int(os.environ.get("AMPLIHACK_MAX_DEPTH", str(DEFAULT_MAX_DEPTH))),
        "max_sessions": int(
            os.environ.get("AMPLIHACK_MAX_SESSIONS", str(DEFAULT_MAX_SESSIONS))
        ),
    }


def env_for_child(tree_id: str, depth: int) -> dict[str, str]:
    """Return environment variables to pass to child subprocesses."""
    return {
        "AMPLIHACK_TREE_ID": tree_id,
        "AMPLIHACK_SESSION_DEPTH": str(depth + 1),
        "AMPLIHACK_MAX_DEPTH": str(
            int(os.environ.get("AMPLIHACK_MAX_DEPTH", str(DEFAULT_MAX_DEPTH)))
        ),
        "AMPLIHACK_MAX_SESSIONS": str(
            int(os.environ.get("AMPLIHACK_MAX_SESSIONS", str(DEFAULT_MAX_SESSIONS)))
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# File I/O with locking
# ─────────────────────────────────────────────────────────────────────────────


def _state_path(tree_id: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{tree_id}.json"


def _lock_path(tree_id: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{tree_id}.lock"


@contextmanager
def _locked(tree_id: str, timeout: float = 10.0):
    """Acquire a file-based lock (atomic O_EXCL create) with timeout."""
    lock = _lock_path(tree_id)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            break
        except FileExistsError:
            # Check for stale lock (> 30s old)
            try:
                age = time.time() - lock.stat().st_mtime
                if age > 30:
                    lock.unlink(missing_ok=True)
            except OSError:
                pass
            time.sleep(0.05)
    else:
        # Timed out — remove stale lock and proceed
        lock.unlink(missing_ok=True)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def _load(tree_id: str) -> dict:
    p = _state_path(tree_id)
    if not p.exists():
        return {"sessions": {}, "queue": []}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {"sessions": {}, "queue": []}


def _save(tree_id: str, state: dict) -> None:
    _state_path(tree_id).write_text(json.dumps(state, indent=2))


# ─────────────────────────────────────────────────────────────────────────────
# Core operations
# ─────────────────────────────────────────────────────────────────────────────


def check_can_spawn(tree_id: Optional[str] = None, depth: int = -1) -> dict:
    """
    Check whether a new child session can be spawned right now.

    Returns:
        {
          "allowed": bool,
          "reason": str,
          "queued_count": int,
          "active_count": int,
          "depth": int,
        }
    """
    ctx = get_tree_context()
    tree_id = tree_id or ctx["tree_id"]
    depth = depth if depth >= 0 else ctx["depth"]
    max_depth = ctx["max_depth"]
    max_sessions = ctx["max_sessions"]
    child_depth = depth + 1

    if child_depth > max_depth:
        return {
            "allowed": False,
            "reason": f"max_depth={max_depth} exceeded at depth={depth}",
            "queued_count": 0,
            "active_count": 0,
            "depth": depth,
        }

    if not tree_id:
        # Root session creating first tree — always allowed
        return {
            "allowed": True,
            "reason": "new_tree",
            "queued_count": 0,
            "active_count": 0,
            "depth": 0,
        }

    state = _load(tree_id)
    active = [s for s in state["sessions"].values() if s.get("status") == "active"]
    queued = state.get("queue", [])

    if len(active) >= max_sessions:
        return {
            "allowed": False,
            "reason": f"max_sessions={max_sessions} reached ({len(active)} active, {len(queued)} queued)",
            "queued_count": len(queued),
            "active_count": len(active),
            "depth": depth,
        }

    return {
        "allowed": True,
        "reason": "ok",
        "queued_count": len(queued),
        "active_count": len(active),
        "depth": depth,
    }


def register_session(
    session_id: str,
    tree_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    depth: int = -1,
) -> dict:
    """
    Register a session in the tree. Creates tree if it doesn't exist.

    Returns: {"tree_id": str, "depth": int, "session_id": str}
    """
    ctx = get_tree_context()
    tree_id = tree_id or ctx["tree_id"] or uuid.uuid4().hex[:8]
    depth = depth if depth >= 0 else ctx["depth"]

    with _locked(tree_id):
        state = _load(tree_id)
        state["sessions"][session_id] = {
            "depth": depth,
            "parent": parent_id,
            "status": "active",
            "started_at": time.time(),
            "children": [],
        }
        if parent_id and parent_id in state["sessions"]:
            state["sessions"][parent_id].setdefault("children", []).append(session_id)
        _save(tree_id, state)

    return {"tree_id": tree_id, "depth": depth, "session_id": session_id}


def enqueue_session(workstream_spec: dict, tree_id: str) -> None:
    """Add a workstream spec to the FIFO queue for later execution."""
    with _locked(tree_id):
        state = _load(tree_id)
        state.setdefault("queue", []).append(
            {"spec": workstream_spec, "queued_at": time.time()}
        )
        _save(tree_id, state)


def dequeue_ready(tree_id: str, max_sessions: int) -> list[dict]:
    """
    Pop items from the queue that can now be executed (active < max_sessions).
    Returns list of workstream specs that should now be started.
    """
    with _locked(tree_id):
        state = _load(tree_id)
        active = [s for s in state["sessions"].values() if s.get("status") == "active"]
        slots = max_sessions - len(active)
        if slots <= 0:
            return []
        ready, remaining = state.get("queue", [])[:slots], state.get("queue", [])[slots:]
        state["queue"] = remaining
        _save(tree_id, state)
    return [item["spec"] for item in ready]


def complete_session(session_id: str, tree_id: Optional[str] = None) -> None:
    """Mark a session as completed and process any queued items."""
    ctx = get_tree_context()
    tree_id = tree_id or ctx["tree_id"]
    if not tree_id:
        return

    with _locked(tree_id):
        state = _load(tree_id)
        if session_id in state["sessions"]:
            state["sessions"][session_id]["status"] = "completed"
            state["sessions"][session_id]["completed_at"] = time.time()
        _save(tree_id, state)


def get_status(tree_id: str) -> dict:
    """Return current tree status summary."""
    state = _load(tree_id)
    sessions = state.get("sessions", {})
    active = [sid for sid, s in sessions.items() if s.get("status") == "active"]
    completed = [sid for sid, s in sessions.items() if s.get("status") == "completed"]
    return {
        "tree_id": tree_id,
        "active": active,
        "completed": completed,
        "queued": len(state.get("queue", [])),
        "depths": {sid: s.get("depth", 0) for sid, s in sessions.items()},
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1

    cmd = argv[1]

    if cmd == "check":
        result = check_can_spawn()
        if result["allowed"]:
            print("ALLOWED")
        else:
            print(f"BLOCKED:{result['reason']}")
        return 0

    if cmd == "register":
        session_id = argv[2] if len(argv) > 2 else uuid.uuid4().hex[:8]
        parent_id = argv[3] if len(argv) > 3 else None
        result = register_session(session_id, parent_id=parent_id)
        print(f"TREE_ID={result['tree_id']} DEPTH={result['depth']}")
        return 0

    if cmd == "complete":
        session_id = argv[2] if len(argv) > 2 else ""
        complete_session(session_id)
        return 0

    if cmd == "status":
        ctx = get_tree_context()
        tree_id = argv[2] if len(argv) > 2 else ctx["tree_id"]
        if not tree_id:
            print("No AMPLIHACK_TREE_ID set")
            return 1
        status = get_status(tree_id)
        print(json.dumps(status, indent=2))
        return 0

    if cmd == "env-for-child":
        ctx = get_tree_context()
        tree_id = ctx["tree_id"] or uuid.uuid4().hex[:8]
        depth = ctx["depth"]
        for k, v in env_for_child(tree_id, depth).items():
            print(f"export {k}={v}")
        return 0

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
