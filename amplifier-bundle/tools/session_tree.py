#!/usr/bin/env python3
"""
Session tree management for amplihack orchestration.

Prevents infinite recursion by tracking active sessions in a tree structure.
Enforces max depth and max concurrent session limits.

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
import re
import sys
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

DEFAULT_MAX_DEPTH = 3
DEFAULT_MAX_SESSIONS = 10
STATE_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "amplihack-session-trees"

# Per-process thread lock for intra-process mutual exclusion.
# The O_EXCL file lock handles cross-process serialization.
# Without this, threads in the same process can observe an empty lock file
# during the O_CREAT→write window (TOCTOU), take the ValueError/pass branch,
# sleep 50ms, wake AFTER the holder releases, and both acquire the file lock
# concurrently — causing lost writes.
_PROCESS_LOCK = threading.Lock()

# ─────────────────────────────────────────────────────────────────────────────
# Security: tree_id validation
# ─────────────────────────────────────────────────────────────────────────────

_TREE_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


def _validate_tree_id(tree_id: str) -> str:
    """Validate tree_id format. Pure function — no side effects.

    Raises ValueError if tree_id is invalid.
    """
    if not tree_id:
        raise ValueError("tree_id cannot be empty")
    if not _TREE_ID_RE.match(tree_id):
        raise ValueError(f"Invalid tree_id {tree_id!r}: must match [a-zA-Z0-9_-]{{1,64}}")
    return tree_id


def _ensure_state_dir() -> None:
    """Create state directory with restricted permissions (0o700)."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        STATE_DIR.chmod(0o700)
    except OSError:
        pass  # Non-fatal if chmod fails (e.g., different owner)


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


# ─────────────────────────────────────────────────────────────────────────────
# File I/O with locking
# ─────────────────────────────────────────────────────────────────────────────


def _state_path(tree_id: str) -> Path:
    _validate_tree_id(tree_id)
    _ensure_state_dir()
    # Belt-and-suspenders path traversal check
    candidate = (STATE_DIR / f"{tree_id}.json").resolve()
    state_resolved = STATE_DIR.resolve()
    if not str(candidate).startswith(str(state_resolved)):
        raise ValueError(f"Path traversal detected for tree_id {tree_id!r}")
    return STATE_DIR / f"{tree_id}.json"


def _lock_path(tree_id: str) -> Path:
    _validate_tree_id(tree_id)
    _ensure_state_dir()
    return STATE_DIR / f"{tree_id}.lock"


@contextmanager
def _locked(tree_id: str, timeout: float = 10.0):
    """Acquire exclusive access for one tree (thread-safe + process-safe).

    Two-layer locking:
    - _PROCESS_LOCK (threading.Lock): serializes threads within this process.
    - O_EXCL file lock: serializes access across OS processes.
    """
    with _PROCESS_LOCK:
        lock = _lock_path(tree_id)
        acquired_file = False
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                try:
                    fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    os.write(fd, str(os.getpid()).encode())
                    os.close(fd)
                    acquired_file = True
                    break
                except FileExistsError:
                    try:
                        lock_content = lock.read_text().strip()
                        pid = int(lock_content)
                        os.kill(pid, 0)
                    except ValueError:
                        pass
                    except OSError:
                        lock.unlink(missing_ok=True)
                    time.sleep(0.05)

            if not acquired_file:
                raise TimeoutError(
                    f"Could not acquire file lock for tree {tree_id!r} within {timeout}s"
                )

            yield
        finally:
            if acquired_file:
                lock.unlink(missing_ok=True)


def _load(tree_id: str) -> dict:
    p = _state_path(tree_id)
    if not p.exists():
        return {"sessions": {}}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as e:
        # Log corruption — do not silently discard state
        print(f"WARNING: session_tree: corrupted state for {tree_id!r}: {e}", file=sys.stderr)
        return {"sessions": {}}


def _save(tree_id: str, state: dict, max_age_hours: float = 24.0, active_max_age_hours: float = 4.0) -> None:
    """Write state atomically. Prunes stale sessions before saving.

    Pruning rules:
    - Completed sessions older than max_age_hours (default 24h) are removed.
    - Active sessions older than active_max_age_hours (default 4h) are treated
      as leaked (process died without calling complete) and pruned.
    """
    now = time.time()
    completed_cutoff = now - (max_age_hours * 3600)
    active_cutoff = now - (active_max_age_hours * 3600)

    # started_at defaults to 0 (epoch): sessions with no start time are treated
    #   as maximally old and always pruned when their slot would otherwise be leaked.
    # completed_at defaults to float("inf"): sessions with no completion time are
    #   treated as never completed and are preserved (safe default: don't prune).
    pruned = {}
    for sid, s in state["sessions"].items():
        if s.get("status") == "completed" and s.get("completed_at", float("inf")) < completed_cutoff:
            continue  # prune old completed session
        if s.get("status") == "active" and s.get("started_at", 0) < active_cutoff:
            print(
                f"WARNING: session_tree: pruning leaked active session {sid!r} "
                f"(started {(now - s.get('started_at', now)) / 3600:.1f}h ago)",
                file=sys.stderr
            )
            continue  # prune leaked active session
        pruned[sid] = s
    state["sessions"] = pruned

    # Atomic write via temp file + rename
    target = _state_path(tree_id)
    content = json.dumps(state, indent=2)
    fd, tmp = tempfile.mkstemp(dir=str(STATE_DIR), prefix=f".{tree_id}-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, str(target))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Core operations
# ─────────────────────────────────────────────────────────────────────────────


def check_can_spawn(tree_id: Optional[str] = None, depth: int = -1) -> dict:
    """
    ADVISORY CHECK ONLY — not atomic. For atomic admission control, use register_session().

    This function reads state WITHOUT holding the lock. By the time the caller
    acts on the result, the state may have changed. Use this only for informational
    purposes (displaying capacity to a user). For actual session admission control,
    call register_session() directly and handle RuntimeError for capacity exceeded.

    Returns:
        {"allowed": bool, "reason": str, "active_count": int, "depth": int}
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
            "active_count": 0,
            "depth": depth,
        }

    if not tree_id:
        # Root session creating first tree — always allowed
        return {
            "allowed": True,
            "reason": "new_tree",
            "active_count": 0,
            "depth": 0,
        }

    _validate_tree_id(tree_id)
    state = _load(tree_id)
    active = [s for s in state["sessions"].values() if s.get("status") == "active"]

    if len(active) >= max_sessions:
        return {
            "allowed": False,
            "reason": f"max_sessions={max_sessions} reached ({len(active)} active)",
            "active_count": len(active),
            "depth": depth,
        }

    return {
        "allowed": True,
        "reason": "ok",
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
    Atomically checks capacity and depth limits while holding the lock.

    Returns: {"tree_id": str, "depth": int, "session_id": str}
    """
    ctx = get_tree_context()
    tree_id = _validate_tree_id(tree_id or ctx["tree_id"] or uuid.uuid4().hex[:8])
    depth = depth if depth >= 0 else ctx["depth"]
    max_sessions = ctx["max_sessions"]
    max_depth = ctx["max_depth"]

    with _locked(tree_id):
        state = _load(tree_id)

        # Atomic capacity and depth check (fixes TOCTOU from check_can_spawn)
        active = [s for s in state["sessions"].values() if s.get("status") == "active"]
        if len(active) >= max_sessions:
            raise RuntimeError(
                f"max_sessions={max_sessions} reached ({len(active)} active)"
            )
        if depth > max_depth:
            raise RuntimeError(
                f"depth={depth} exceeds max_depth={max_depth}"
            )

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


def complete_session(session_id: str, tree_id: Optional[str] = None) -> None:
    """Mark a session as completed."""
    ctx = get_tree_context()
    tree_id = tree_id or ctx["tree_id"]
    if not tree_id:
        return

    _validate_tree_id(tree_id)
    with _locked(tree_id):
        state = _load(tree_id)
        if session_id in state["sessions"]:
            state["sessions"][session_id]["status"] = "completed"
            state["sessions"][session_id]["completed_at"] = time.time()
        _save(tree_id, state)


def get_status(tree_id: str) -> dict:
    """Return current tree status summary."""
    _validate_tree_id(tree_id)
    state = _load(tree_id)
    sessions = state.get("sessions", {})
    active = [sid for sid, s in sessions.items() if s.get("status") == "active"]
    completed = [sid for sid, s in sessions.items() if s.get("status") == "completed"]
    return {
        "tree_id": tree_id,
        "active": active,
        "completed": completed,
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
        try:
            result = register_session(session_id, parent_id=parent_id)
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
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
        _validate_tree_id(tree_id)
        status = get_status(tree_id)
        print(json.dumps(status, indent=2))
        return 0

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
