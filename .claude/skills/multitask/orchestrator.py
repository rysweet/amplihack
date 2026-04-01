#!/usr/bin/env python3
"""Parallel Workstream Orchestrator with Recipe Runner support.

Executes multiple independent development tasks in parallel using subprocess
isolation. Each workstream runs in a clean /tmp clone with its own execution
context.

Two execution modes:
  - recipe (default): Uses Recipe Runner for code-enforced step ordering
  - classic: Uses single Claude session with prompt-based workflow

Usage:
    python orchestrator.py workstreams.json
    python orchestrator.py workstreams.json --mode classic
    python orchestrator.py workstreams.json --recipe investigation-workflow
"""

import json
import logging
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Pre-compiled patterns for hot-path sanitization
_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_-]")
_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_]")

try:
    from amplihack.hooks.launcher_detector import LauncherDetector
except ImportError:
    LauncherDetector = None  # type: ignore[assignment,misc]

# Allowlist of valid delegate values (single source of truth for injection prevention).
# Only these exact strings may be used as subprocess delegates.
VALID_DELEGATES: frozenset[str] = frozenset(
    {
        "amplihack claude",
        "amplihack copilot",
        "amplihack amplifier",
    }
)

# Log size cap: prevent /tmp exhaustion from runaway subprocesses.
# Configurable via AMPLIHACK_MAX_LOG_BYTES env var.
MAX_LOG_BYTES: int = int(os.environ.get("AMPLIHACK_MAX_LOG_BYTES", str(100 * 1024 * 1024)))
DEFAULT_MAX_RUNTIME = 7200
INTERRUPT_PRESERVE_TIMEOUT_POLICY = "interrupt-preserve"
CONTINUE_PRESERVE_TIMEOUT_POLICY = "continue-preserve"
DEFAULT_TIMEOUT_POLICY = INTERRUPT_PRESERVE_TIMEOUT_POLICY
VALID_TIMEOUT_POLICIES: frozenset[str] = frozenset(
    {INTERRUPT_PRESERVE_TIMEOUT_POLICY, CONTINUE_PRESERVE_TIMEOUT_POLICY}
)
RESUMABLE_LIFECYCLE_STATES: frozenset[str] = frozenset(
    {"failed_resumable", "timed_out_resumable", "interrupted_resumable"}
)
CLEANUP_ELIGIBLE_LIFECYCLE_STATES: frozenset[str] = frozenset(
    {"completed", "failed_terminal", "abandoned"}
)

logger = logging.getLogger(__name__)


@dataclass
class Workstream:
    """A parallel workstream executing in a subprocess."""

    issue: int
    branch: str
    description: str
    task: str
    recipe: str = "default-workflow"
    work_dir: Path = field(default_factory=Path)
    log_file: Path = field(default_factory=Path)
    pid: int | None = None
    start_time: float | None = None
    end_time: float | None = None
    exit_code: int | None = None
    lifecycle_state: str = "pending"
    cleanup_eligible: bool = False
    state_file: Path = field(default_factory=Path)
    progress_file: Path = field(default_factory=Path)
    worktree_path: str = ""
    checkpoint_id: str = ""
    last_step: str = ""
    attempt: int = 0
    timeout_policy: str = DEFAULT_TIMEOUT_POLICY
    max_runtime: int | None = None
    resume_checkpoint: str = ""

    @property
    def is_running(self) -> bool:
        if self.pid is None:
            return False
        try:
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False

    @property
    def runtime_seconds(self) -> float | None:
        if self.start_time is None:
            return None
        end = self.end_time or time.time()
        return end - self.start_time


class ParallelOrchestrator:
    """Orchestrates parallel workstream execution with Recipe Runner support."""

    def __init__(
        self,
        repo_url: str,
        tmp_base: str = "/tmp/amplihack-workstreams",
        mode: str = "recipe",
    ):
        self.repo_url = repo_url
        self.tmp_base = Path(tmp_base)
        self.state_dir = self.tmp_base / "state"
        self.mode = mode
        self.workstreams: list[Workstream] = []
        self._processes: dict[int, subprocess.Popen] = {}
        self._cleaned_up: set[int] = set()  # Track cleaned workstream issues
        self._freed_bytes: int = 0  # Track total disk freed by auto-cleanup
        self._stdout_lock = threading.Lock()  # Serialize concurrent stdout writes
        self._tail_threads: dict[int, threading.Thread] = {}  # Per-workstream tailing threads
        self._max_log_bytes: int = MAX_LOG_BYTES
        self._json_cache: dict[Path, tuple[int, int, dict[str, Any]]] = {}
        self._default_branch: str | None = None
        self.default_max_runtime = self._resolve_max_runtime(
            os.environ.get("AMPLIHACK_MAX_RUNTIME")
        )
        self.default_timeout_policy = self._resolve_timeout_policy(
            os.environ.get("AMPLIHACK_TIMEOUT_POLICY")
        )

    def setup(self) -> None:
        """Prepare the persistent runtime directories and check disk space."""
        self.tmp_base.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Check disk space and warn if low
        self._check_disk_space()

    def _stdout_write(self, msg: str) -> None:
        """Write msg to stdout under _stdout_lock to prevent interleaving."""
        with self._stdout_lock:
            sys.stdout.write(msg)
            sys.stdout.flush()

    def _emit_stderr_event(self, event: dict[str, object]) -> None:
        """Emit a compact JSONL liveness event to stderr."""
        print(json.dumps(event, separators=(",", ":")), file=sys.stderr, flush=True)

    def _safe_log_path(self, issue_id: object) -> Path:
        """Return a log file path guaranteed to be within tmp_base.

        Sanitizes issue_id to prevent path traversal attacks.
        """
        safe_id = _SAFE_ID_RE.sub("_", str(issue_id))
        candidate = (self.tmp_base / f"log-{safe_id}.txt").resolve()
        if not str(candidate).startswith(str(self.tmp_base.resolve())):
            raise ValueError(f"Unsafe log path detected for issue_id={issue_id!r}")
        return candidate

    def _detect_delegate(self) -> str:
        """Detect the active amplihack delegate for subprocess propagation.

        Resolution order:
        1. AMPLIHACK_DELEGATE env var (if set and in VALID_DELEGATES)
        2. LauncherDetector.detect() → map launcher type to delegate
        3. Fall back to "amplihack claude" with a warning

        Returns:
            A member of VALID_DELEGATES.
        """
        env_delegate = os.environ.get("AMPLIHACK_DELEGATE")
        if env_delegate is not None:
            if env_delegate in VALID_DELEGATES:
                return env_delegate
            # Reject invalid env var (injection prevention) and fall through to detection
            warnings.warn(
                f"AMPLIHACK_DELEGATE={env_delegate!r} is not in VALID_DELEGATES. "
                "Falling back to LauncherDetector.",
                stacklevel=2,
            )

        # Try LauncherDetector
        if LauncherDetector is not None:
            try:
                launcher_info = LauncherDetector()
                detected = launcher_info.detect()
                # detect() returns a LauncherInfo or a string (mocked in tests)
                launcher_type = detected if isinstance(detected, str) else detected.launcher_type
                candidate = f"amplihack {launcher_type}"
                if candidate in VALID_DELEGATES:
                    return candidate
            except Exception:
                pass

        # Final fallback
        warnings.warn(
            "Could not detect amplihack delegate — defaulting to 'amplihack claude'. "
            "Set AMPLIHACK_DELEGATE to suppress this warning.",
            stacklevel=2,
        )
        return "amplihack claude"

    def _timestamp(self) -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def _resolve_max_runtime(self, raw: object | None) -> int:
        if raw in (None, ""):
            return DEFAULT_MAX_RUNTIME
        try:
            value = int(raw)
        except (TypeError, ValueError):
            warnings.warn(
                f"Invalid max_runtime value {raw!r}; using default {DEFAULT_MAX_RUNTIME}s.",
                stacklevel=2,
            )
            return DEFAULT_MAX_RUNTIME
        if value < 0:
            warnings.warn(
                f"Negative max_runtime value {value!r}; using default {DEFAULT_MAX_RUNTIME}s.",
                stacklevel=2,
            )
            return DEFAULT_MAX_RUNTIME
        return value

    def _resolve_timeout_policy(self, raw: object | None) -> str:
        if raw in (None, ""):
            return DEFAULT_TIMEOUT_POLICY
        value = str(raw).strip()
        if value in VALID_TIMEOUT_POLICIES:
            return value
        warnings.warn(
            f"Invalid timeout_policy value {raw!r}; using default {DEFAULT_TIMEOUT_POLICY!r}.",
            stacklevel=2,
        )
        return DEFAULT_TIMEOUT_POLICY

    def _safe_state_path(self, issue_id: object) -> Path:
        safe_id = _SAFE_ID_RE.sub("_", str(issue_id))
        candidate = (self.state_dir / f"ws-{safe_id}.json").resolve()
        if not str(candidate).startswith(str(self.state_dir.resolve())):
            raise ValueError(f"Unsafe state path detected for issue_id={issue_id!r}")
        return candidate

    def _safe_progress_sidecar_path(self, issue_id: object) -> Path:
        safe_id = _SAFE_ID_RE.sub("_", str(issue_id))
        candidate = (self.state_dir / f"ws-{safe_id}.progress.json").resolve()
        if not str(candidate).startswith(str(self.state_dir.resolve())):
            raise ValueError(f"Unsafe progress path detected for issue_id={issue_id!r}")
        return candidate

    def _read_json_file(self, path: Path) -> dict[str, Any]:
        try:
            stat_result = path.stat()
        except OSError:
            self._json_cache.pop(path, None)
            return {}
        cached = self._json_cache.get(path)
        signature = (stat_result.st_mtime_ns, stat_result.st_size)
        if cached is not None and cached[:2] == signature:
            return cached[2]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload: dict[str, Any] = {}
        else:
            payload = data if isinstance(data, dict) else {}
        self._json_cache[path] = (signature[0], signature[1], payload)
        return payload

    def _write_json_file(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        tmp_path.chmod(0o600)
        tmp_path.replace(path)
        try:
            stat_result = path.stat()
        except OSError:
            self._json_cache.pop(path, None)
        else:
            self._json_cache[path] = (stat_result.st_mtime_ns, stat_result.st_size, payload)

    def _load_state(self, issue: int) -> dict[str, Any]:
        return self._read_json_file(self._safe_state_path(issue))

    def _find_matching_saved_state(self, *, branch: str, description: str) -> dict[str, Any]:
        if not self.state_dir.exists():
            return {}
        for state_file in sorted(self.state_dir.glob("ws-*.json")):
            payload = self._read_json_file(state_file)
            if not payload:
                continue
            if payload.get("cleanup_eligible"):
                continue
            if payload.get("branch") == branch or payload.get("description") == description:
                return payload
        return {}

    def _derive_cleanup_eligible(self, lifecycle_state: str) -> bool:
        return lifecycle_state in CLEANUP_ELIGIBLE_LIFECYCLE_STATES

    def _coerce_int(self, raw: object, *, default: int | None = None) -> int | None:
        if raw in (None, ""):
            return default
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default

    def _new_workstream(
        self,
        *,
        issue: int,
        branch: str,
        description: str,
        task: str,
        recipe: str,
    ) -> Workstream:
        ws = Workstream(
            issue=issue,
            branch=branch,
            description=description,
            task=task,
            recipe=recipe,
            lifecycle_state="pending",
            cleanup_eligible=False,
        )
        ws.work_dir = self.tmp_base / f"ws-{issue}"
        ws.log_file = self._safe_log_path(issue)
        ws.state_file = self._safe_state_path(issue)
        ws.progress_file = self._safe_progress_sidecar_path(issue)
        ws.max_runtime = self.default_max_runtime
        ws.timeout_policy = self.default_timeout_policy
        return ws

    def _apply_runtime_overrides(
        self,
        ws: Workstream,
        *,
        max_runtime: int | None = None,
        timeout_policy: str | None = None,
    ) -> None:
        if max_runtime is not None:
            ws.max_runtime = self._resolve_max_runtime(max_runtime)
        if timeout_policy is not None:
            ws.timeout_policy = self._resolve_timeout_policy(timeout_policy)

    def _apply_saved_state(self, ws: Workstream, payload: dict[str, Any]) -> None:
        if not payload:
            return
        ws.branch = str(payload.get("branch") or ws.branch)
        ws.description = str(payload.get("description") or ws.description)
        ws.lifecycle_state = str(payload.get("lifecycle_state") or ws.lifecycle_state)
        ws.cleanup_eligible = bool(
            payload.get("cleanup_eligible", self._derive_cleanup_eligible(ws.lifecycle_state))
        )
        ws.worktree_path = str(payload.get("worktree_path") or ws.worktree_path)
        checkpoint_id = str(payload.get("checkpoint_id") or ws.checkpoint_id)
        if checkpoint_id:
            ws.checkpoint_id = checkpoint_id
            ws.resume_checkpoint = checkpoint_id
        ws.last_step = str(payload.get("current_step") or ws.last_step)
        ws.attempt = self._coerce_int(payload.get("attempt"), default=ws.attempt) or 0
        ws.max_runtime = self._resolve_max_runtime(
            payload["max_runtime"] if payload.get("max_runtime") is not None else ws.max_runtime
        )
        ws.timeout_policy = self._resolve_timeout_policy(
            payload["timeout_policy"]
            if payload.get("timeout_policy") is not None
            else ws.timeout_policy
        )
        ws.pid = self._coerce_int(payload.get("last_pid"), default=ws.pid)
        if ws.exit_code is None or payload.get("last_exit_code") is not None:
            ws.exit_code = self._coerce_int(payload.get("last_exit_code"), default=ws.exit_code)
        work_dir = payload.get("work_dir")
        if work_dir:
            ws.work_dir = Path(str(work_dir))
        log_file = payload.get("log_file")
        if log_file:
            ws.log_file = Path(str(log_file))

    def _load_state_into_workstream(self, ws: Workstream) -> dict[str, Any]:
        if str(ws.state_file) in {"", "."}:
            return {}
        state = self._read_json_file(ws.state_file)
        self._apply_saved_state(ws, state)
        return state

    def _read_progress_payload(self, ws: Workstream) -> dict[str, Any]:
        candidates: list[Path] = []
        if str(ws.progress_file) not in {"", "."}:
            candidates.append(ws.progress_file)
        if ws.pid is not None:
            safe_name = _SAFE_NAME_RE.sub("_", ws.recipe)[:64]
            candidates.append(
                Path(tempfile.gettempdir()) / f"amplihack-progress-{safe_name}-{ws.pid}.json"
            )
        for candidate in candidates:
            payload = self._read_json_file(candidate)
            if payload:
                return payload
        return {}

    def _sync_progress_to_workstream(self, ws: Workstream) -> dict[str, Any]:
        payload = self._read_progress_payload(ws)
        if not payload:
            return {}
        ws.last_step = str(payload.get("step_name") or payload.get("current_step") or ws.last_step)
        checkpoint_id = payload.get("checkpoint_id")
        if checkpoint_id:
            ws.checkpoint_id = str(checkpoint_id)
            ws.resume_checkpoint = str(checkpoint_id)
        worktree_path = payload.get("worktree_path")
        if worktree_path:
            ws.worktree_path = str(worktree_path)
        return payload

    def _persist_workstream_state(
        self,
        ws: Workstream,
        *,
        lifecycle_state: str | None = None,
        exit_code: int | None = None,
        sync_progress: bool = True,
    ) -> None:
        if sync_progress:
            self._sync_progress_to_workstream(ws)
        if lifecycle_state is not None:
            ws.lifecycle_state = lifecycle_state
        if exit_code is not None:
            ws.exit_code = exit_code
        ws.cleanup_eligible = self._derive_cleanup_eligible(ws.lifecycle_state)
        if str(ws.state_file) in {"", "."}:
            return
        previous = self._read_json_file(ws.state_file)
        created_at = previous.get("created_at", self._timestamp())
        payload: dict[str, Any] = {
            "issue": ws.issue,
            "branch": ws.branch,
            "description": ws.description,
            "task": ws.task,
            "recipe": ws.recipe,
            "lifecycle_state": ws.lifecycle_state,
            "cleanup_eligible": ws.cleanup_eligible,
            "attempt": ws.attempt,
            "last_pid": ws.pid,
            "last_exit_code": ws.exit_code,
            "current_step": ws.last_step or "unknown",
            "checkpoint_id": ws.checkpoint_id,
            "work_dir": str(ws.work_dir),
            "worktree_path": ws.worktree_path,
            "log_file": str(ws.log_file),
            "progress_sidecar": str(ws.progress_file),
            "max_runtime": ws.max_runtime or self.default_max_runtime,
            "timeout_policy": ws.timeout_policy,
            "created_at": created_at,
            "updated_at": self._timestamp(),
        }
        resume_context = previous.get("resume_context")
        if isinstance(resume_context, dict):
            payload["resume_context"] = resume_context
        self._write_json_file(ws.state_file, payload)

    def _terminate_process(self, proc: subprocess.Popen) -> None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)

    def _close_active_workstream(
        self,
        ws: Workstream,
        *,
        proc: subprocess.Popen,
        lifecycle_state: str,
    ) -> None:
        ws.end_time = time.time()
        ws.exit_code = proc.returncode if proc.returncode is not None else -15
        self._finalize_workstream_with_lifecycle(ws, lifecycle_state)
        self._processes.pop(ws.issue, None)
        self._tail_threads.pop(ws.issue, None)

    def _finalize_finished_process(
        self,
        ws: Workstream,
        proc: subprocess.Popen,
        *,
        returncode: int | None = None,
    ) -> bool:
        if returncode is None:
            returncode = proc.poll()
        if returncode is None:
            return False
        self._finalize_workstream(ws, returncode)
        self._processes.pop(ws.issue, None)
        self._tail_threads.pop(ws.issue, None)
        return True

    def _finalize_workstream(self, ws: Workstream, returncode: int) -> None:
        if ws.end_time is None:
            ws.end_time = time.time()
        ws.exit_code = returncode
        progress = self._sync_progress_to_workstream(ws)
        if ws.lifecycle_state == "interrupted_resumable":
            self._persist_workstream_state(ws, sync_progress=False)
            return
        if (
            ws.lifecycle_state == "timed_out_resumable"
            and ws.timeout_policy == INTERRUPT_PRESERVE_TIMEOUT_POLICY
        ):
            self._persist_workstream_state(ws, sync_progress=False)
            return
        if returncode == 0:
            ws.lifecycle_state = "completed"
        elif ws.checkpoint_id or progress:
            ws.lifecycle_state = "failed_resumable"
        else:
            ws.lifecycle_state = "failed_terminal"
        self._persist_workstream_state(ws, sync_progress=False)

    def _timed_out(self, ws: Workstream, budget: int) -> None:
        proc = self._processes.get(ws.issue)
        if proc is None:
            return
        returncode = proc.poll()
        if returncode is not None:
            self._finalize_finished_process(ws, proc, returncode=returncode)
            return
        if ws.timeout_policy == INTERRUPT_PRESERVE_TIMEOUT_POLICY:
            print(f"[{ws.issue}] Timed out after {budget}s, marking workstream timed_out_resumable")
            if self._finalize_finished_process(ws, proc):
                return
            self._terminate_process(proc)
            self._close_active_workstream(ws, proc=proc, lifecycle_state="timed_out_resumable")
            return
        print(
            f"[{ws.issue}] Timed out after {budget}s, marking workstream timed_out_resumable "
            "without interrupting subprocess"
        )
        self._persist_workstream_state(ws, lifecycle_state="timed_out_resumable")

    def _interrupt_workstream(self, ws: Workstream) -> None:
        proc = self._processes.get(ws.issue)
        if proc is None or proc.poll() is not None:
            return
        print(f"[{ws.issue}] Terminating PID {ws.pid}...")
        self._terminate_process(proc)
        self._close_active_workstream(ws, proc=proc, lifecycle_state="interrupted_resumable")

    def _finalize_workstream_with_lifecycle(self, ws: Workstream, lifecycle_state: str) -> None:
        self._sync_progress_to_workstream(ws)
        ws.lifecycle_state = lifecycle_state
        self._persist_workstream_state(ws, sync_progress=False)

    def _resolve_default_branch(self) -> str:
        if self._default_branch is not None:
            return self._default_branch
        default_branch = "main"
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--symref", self.repo_url, "HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            self._default_branch = default_branch
            return default_branch
        for line in result.stdout.splitlines():
            if line.startswith("ref: refs/heads/"):
                default_branch = line.split("refs/heads/")[1].split("\t")[0].strip()
                break
        self._default_branch = default_branch
        return default_branch

    def _resume_context(self, ws: Workstream) -> dict[str, Any]:
        state_payload = (
            self._read_json_file(ws.state_file) if str(ws.state_file) not in {"", "."} else {}
        )
        context: dict[str, Any] = {
            "task_description": ws.task,
            "repo_path": ".",
            "issue_number": ws.issue,
            "workstream_state_file": str(ws.state_file),
            "workstream_progress_file": str(ws.progress_file),
        }
        resume_payload = state_payload.get("resume_context")
        if isinstance(resume_payload, dict):
            context.update(resume_payload)
        if ws.resume_checkpoint:
            context["resume_checkpoint"] = ws.resume_checkpoint
        if ws.worktree_path:
            context["worktree_setup"] = {
                "worktree_path": ws.worktree_path,
                "branch_name": ws.branch,
                "created": False,
            }
            context["resume_worktree_path"] = ws.worktree_path
            context["resume_branch_name"] = ws.branch
        return context

    def _workstream_summary(self, ws: Workstream, status: str) -> dict[str, Any]:
        if status != "running":
            self._load_state_into_workstream(ws)
        self._sync_progress_to_workstream(ws)
        summary: dict[str, Any] = {
            "issue": ws.issue,
            "status": status,
            "step": ws.last_step or "unknown",
            "elapsed_s": int(ws.runtime_seconds or 0),
        }
        if (
            ws.lifecycle_state in RESUMABLE_LIFECYCLE_STATES
            or ws.checkpoint_id
            or ws.worktree_path
            or (ws.lifecycle_state and ws.lifecycle_state not in {"pending", "completed"})
        ):
            summary.update(
                {
                    "lifecycle_state": ws.lifecycle_state or "pending",
                    "checkpoint_id": ws.checkpoint_id,
                    "worktree_path": ws.worktree_path,
                    "log_path": str(ws.log_file),
                    "cleanup_eligible": ws.cleanup_eligible,
                }
            )
        return summary

    def _cleanup_allowed(self, ws: Workstream) -> bool:
        return ws.cleanup_eligible

    def add_workstream(
        self,
        issue: int,
        branch: str,
        description: str,
        task: str,
        recipe: str = "default-workflow",
    ) -> Workstream:
        """Create a workstream with its directory without cloning a repository."""
        ws = self._new_workstream(
            issue=issue,
            branch=branch,
            description=description,
            task=task,
            recipe=recipe,
        )
        ws.work_dir.mkdir(parents=True, exist_ok=True)
        return ws

    def add(
        self,
        issue: int | str,
        branch: str,
        description: str,
        task: str,
        recipe: str = "default-workflow",
        *,
        max_runtime: int | None = None,
        timeout_policy: str | None = None,
    ) -> Workstream:
        """Add a workstream. Clones from main and prepares execution files.

        If issue is "TBD", auto-creates a GitHub issue using gh CLI.
        """
        saved_state: dict[str, Any] = {}
        # Auto-create issue if TBD
        if str(issue).upper() == "TBD":
            saved_state = self._find_matching_saved_state(branch=branch, description=description)
            if saved_state:
                issue = int(saved_state["issue"])
                print(f"[{issue}] Reusing preserved resumable workstream")
            else:
                print(f"[TBD] Creating GitHub issue for: {description}...")
                result = subprocess.run(
                    ["gh", "issue", "create", "--title", description, "--body", task],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    # Extract issue number from URL like https://github.com/.../issues/123
                    url = result.stdout.strip()
                    issue = int(url.rstrip("/").split("/")[-1])
                    print(f"[{issue}] Created issue: {url}")
                else:
                    # Fallback: use timestamp-based ID
                    issue = int(time.time()) % 100000
                    print(f"[{issue}] Could not create issue, using fallback ID")

        # Validate issue is a positive integer to prevent path/shell injection
        try:
            issue = int(issue)
            if issue <= 0:
                raise ValueError(f"issue must be positive, got {issue}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid issue number in workstream config: {issue!r}") from e

        ws = self._new_workstream(
            issue=issue,
            branch=branch,
            description=description,
            task=task,
            recipe=recipe,
        )
        if not saved_state:
            saved_state = self._load_state(issue)
        self._apply_saved_state(ws, saved_state)
        self._apply_runtime_overrides(
            ws,
            max_runtime=max_runtime,
            timeout_policy=timeout_policy,
        )

        reuse_existing = bool(saved_state) and not ws.cleanup_eligible and ws.work_dir.exists()
        if not reuse_existing and ws.work_dir.exists():
            shutil.rmtree(ws.work_dir)

        default_branch = self._resolve_default_branch()

        if reuse_existing:
            print(f"[{issue}] Reusing preserved work dir {ws.work_dir}")
        else:
            print(f"[{issue}] Cloning default branch '{default_branch}' from remote...")
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth=1",
                    f"--branch={default_branch}",
                    self.repo_url,
                    str(ws.work_dir),
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
            # Note: The workflow Step 4 will create the feature branch

        ws.work_dir.mkdir(parents=True, exist_ok=True)

        # Write execution files based on mode
        if self.mode == "recipe":
            self._write_recipe_launcher(ws)
        else:
            self._write_classic_launcher(ws)

        self._persist_workstream_state(ws)
        self.workstreams.append(ws)
        return ws

    def _write_recipe_launcher(self, ws: Workstream) -> None:
        """Write launcher files for recipe-based execution.

        Creates a Python script that uses run_recipe_by_name() via the Rust
        recipe runner, and a shell wrapper that sets session tree vars.
        """
        launcher_py = ws.work_dir / "launcher.py"
        # Use json.dumps for proper escaping of all special characters
        import json

        safe_recipe = json.dumps(ws.recipe)
        safe_context = json.dumps(self._resume_context(ws))
        launcher_py.write_text(
            textwrap.dedent(f"""\
            #!/usr/bin/env python3
            \"\"\"Workstream launcher - Rust recipe runner execution.\"\"\"
            import sys
            import json
            import logging
            from pathlib import Path

            repo_root = Path(__file__).resolve().parent
            src_path = repo_root / "src"
            if src_path.exists():
                sys.path.insert(0, str(src_path))

            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            )

            try:
                from amplihack.recipes import run_recipe_by_name
            except ImportError:
                print("ERROR: amplihack package not importable. Falling back to classic mode.")
                sys.exit(2)

            user_context = json.loads({json.dumps(safe_context)})
            result = run_recipe_by_name(
                {safe_recipe},
                user_context=user_context,
                progress=True,
            )

            print()
            print("=" * 60)
            print("RECIPE EXECUTION RESULTS")
            print("=" * 60)
            for sr in result.step_results:
                print(f"  [{{sr.status.value:>9}}] {{sr.step_id}}")
            print(f"\\nOverall: {{'SUCCESS' if result.success else 'FAILED'}}")
            sys.exit(0 if result.success else 1)
            """)
        )
        launcher_py.chmod(0o755)

        # Shell wrapper: propagate session tree context
        # AMPLIHACK_TREE_ID and AMPLIHACK_SESSION_DEPTH are inherited from the
        # parent environment (set by the recipe that invoked this orchestrator).
        # This ensures the session tree depth limit is enforced in child recipes.
        import uuid

        current_depth = int(os.environ.get("AMPLIHACK_SESSION_DEPTH", "0"))
        tree_id = os.environ.get("AMPLIHACK_TREE_ID") or uuid.uuid4().hex[:8]

        # Detect delegate at generation time (S2: bake in value, prevent injection)
        delegate = self._detect_delegate()

        safe_work_dir = shlex.quote(str(ws.work_dir))
        safe_tree = shlex.quote(tree_id)
        safe_depth = shlex.quote(str(current_depth + 1))
        safe_max_depth = shlex.quote(os.environ.get("AMPLIHACK_MAX_DEPTH", "3"))
        safe_max_sessions = shlex.quote(os.environ.get("AMPLIHACK_MAX_SESSIONS", "10"))
        safe_delegate = shlex.quote(delegate)
        safe_workstream_issue = shlex.quote(str(ws.issue))
        safe_progress_file = shlex.quote(str(ws.progress_file))
        safe_state_file = shlex.quote(str(ws.state_file))
        safe_worktree_path = shlex.quote(ws.worktree_path)

        run_sh = ws.work_dir / "run.sh"
        run_sh.write_text(
            textwrap.dedent(f"""\
            #!/bin/bash
            cd {safe_work_dir}
            # Propagate session tree context so child recipes obey depth limits
            export AMPLIHACK_TREE_ID={safe_tree}
            export AMPLIHACK_SESSION_DEPTH={safe_depth}
            export AMPLIHACK_MAX_DEPTH={safe_max_depth}
            export AMPLIHACK_MAX_SESSIONS={safe_max_sessions}
            # Bake in the detected delegate so nested ClaudeProcess inherits it (S2)
            export AMPLIHACK_DELEGATE={safe_delegate}
            export AMPLIHACK_WORKSTREAM_ISSUE={safe_workstream_issue}
            export AMPLIHACK_WORKSTREAM_PROGRESS_FILE={safe_progress_file}
            export AMPLIHACK_WORKSTREAM_STATE_FILE={safe_state_file}
            export AMPLIHACK_WORKTREE_PATH={safe_worktree_path}
            # Unbuffered stdout/stderr is required so the parent multitask
            # orchestrator can stream nested recipe progress live.
            exec python3 -u launcher.py
            """)
        )
        run_sh.chmod(0o755)

    def _write_classic_launcher(self, ws: Workstream) -> None:
        """Write launcher for classic single-session execution."""
        # Task file
        task_md = ws.work_dir / "TASK.md"
        task_md.write_text(
            f"# Issue #{ws.issue}\n\n{ws.task}\n\n"
            f"Follow DEFAULT_WORKFLOW.md autonomously. "
            f"NO QUESTIONS. Work through Steps 0-22. Create PR when complete."
        )

        # Shell launcher
        import uuid as _uuid

        _depth = int(os.environ.get("AMPLIHACK_SESSION_DEPTH", "0"))
        _tree = os.environ.get("AMPLIHACK_TREE_ID") or _uuid.uuid4().hex[:8]

        # Detect delegate at generation time and bake it into run.sh (S2: prevents env var injection)
        _delegate = self._detect_delegate()

        _safe_work_dir = shlex.quote(str(ws.work_dir))
        _safe_tree = shlex.quote(_tree)
        _safe_depth = shlex.quote(str(_depth + 1))
        _safe_max_depth = shlex.quote(os.environ.get("AMPLIHACK_MAX_DEPTH", "3"))
        _safe_max_sessions = shlex.quote(os.environ.get("AMPLIHACK_MAX_SESSIONS", "10"))
        _safe_delegate = shlex.quote(_delegate)

        run_sh = ws.work_dir / "run.sh"
        run_sh.write_text(
            textwrap.dedent(f"""\
            #!/bin/bash
            cd {_safe_work_dir}
            export AMPLIHACK_TREE_ID={_safe_tree}
            export AMPLIHACK_SESSION_DEPTH={_safe_depth}
            export AMPLIHACK_MAX_DEPTH={_safe_max_depth}
            export AMPLIHACK_MAX_SESSIONS={_safe_max_sessions}
            {_safe_delegate} --subprocess-safe -- -p "@TASK.md Execute task autonomously following DEFAULT_WORKFLOW.md. NO QUESTIONS. Work through all steps. Create PR when complete."
            """)
        )
        run_sh.chmod(0o755)

    def _tail_output(self, pipe: object, log_file: Path, issue_id: int) -> None:
        """Daemon thread: read from pipe, tee to log file + prefixed stdout.

        Lines are written raw to the log file and with a ``[ws:{issue_id}]`` prefix
        to stdout.  Writing stops when ``_max_log_bytes`` is reached.
        Log file is created with 0o600 permissions (owner-only) to protect secrets.
        """
        log_bytes_written = 0
        log_fd = os.open(str(log_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(log_fd, "w") as log_fh:
            for line in iter(pipe.readline, ""):  # type: ignore[union-attr]
                if log_bytes_written < self._max_log_bytes:
                    encoded_len = len(line.encode("utf-8", errors="replace"))
                    if log_bytes_written + encoded_len <= self._max_log_bytes:
                        log_fh.write(line)
                        log_fh.flush()
                        log_bytes_written += encoded_len
                self._stdout_write(f"[ws:{issue_id}] {line}")

    def launch(self, ws: Workstream, *, delegate: str | None = None) -> None:
        """Launch a single workstream subprocess.

        Args:
            ws: Workstream to launch.
            delegate: Pre-detected delegate string (from launch_all). If None,
                AMPLIHACK_DELEGATE is taken from the current environment.
        """
        launch_env = {**os.environ}
        if delegate is not None:
            launch_env["AMPLIHACK_DELEGATE"] = delegate

        proc = subprocess.Popen(
            [str(ws.work_dir / "run.sh")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=ws.work_dir,
            env=launch_env,
            text=True,
        )
        ws.pid = proc.pid
        ws.start_time = time.time()
        ws.end_time = None
        ws.exit_code = None
        ws.lifecycle_state = "running"
        ws.cleanup_eligible = False
        ws.attempt = (ws.attempt or 0) + 1
        self._processes[ws.issue] = proc
        self._persist_workstream_state(ws)

        # Start a daemon thread to tee stdout → log file + prefixed console output
        tail_thread = threading.Thread(
            target=self._tail_output,
            args=(proc.stdout, ws.log_file, ws.issue),
            daemon=True,
        )
        tail_thread.start()
        self._tail_threads[ws.issue] = tail_thread

        print(f"[{ws.issue}] Launched PID {ws.pid} ({self.mode} mode)")

    def launch_all(self) -> None:
        """Launch all workstreams in parallel."""
        delegate = self._detect_delegate()
        for ws in self.workstreams:
            self.launch(ws, delegate=delegate)
        print(f"\n{len(self.workstreams)} workstreams launched in parallel ({self.mode} mode)")

    def get_status(self) -> dict[str, set[int]]:
        """Get current status of all workstreams."""
        status: dict[str, set[int]] = {"running": set(), "completed": set(), "failed": set()}

        for ws in self.workstreams:
            proc = self._processes.get(ws.issue)
            returncode = proc.poll() if proc else None
            if proc and returncode is None:
                if not (
                    ws.lifecycle_state == "timed_out_resumable"
                    and ws.timeout_policy == CONTINUE_PRESERVE_TIMEOUT_POLICY
                ):
                    ws.lifecycle_state = "running"
                status["running"].add(ws.issue)
            elif proc:
                self._finalize_finished_process(ws, proc, returncode=returncode)
                if ws.lifecycle_state == "completed":
                    status["completed"].add(ws.issue)
                else:
                    status["failed"].add(ws.issue)
            else:
                if ws.exit_code == 0 or ws.lifecycle_state == "completed":
                    status["completed"].add(ws.issue)
                else:
                    status["failed"].add(ws.issue)

        return status

    def _cleanup_workstream_dir(self, ws: Workstream) -> None:
        """Remove a completed workstream's work directory to free disk space.

        Log files are preserved (they live in tmp_base, not work_dir).
        This is the key fix for issue #2527 — without auto-cleanup, 60
        workstreams consume ~90GB (1.5GB each) and fill the disk.
        """
        if ws.issue in self._cleaned_up:
            return
        if not self._cleanup_allowed(ws):
            return
        if not ws.work_dir.exists():
            self._cleaned_up.add(ws.issue)
            return

        # Measure size using os.scandir (avoids separate stat syscalls on
        # platforms where DirEntry caches inode data from readdir).
        dir_bytes = 0
        dirs_to_scan = [ws.work_dir]
        while dirs_to_scan:
            current = dirs_to_scan.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        try:
                            if entry.is_file(follow_symlinks=False):
                                dir_bytes += entry.stat(follow_symlinks=False).st_size
                            elif entry.is_dir(follow_symlinks=False):
                                dirs_to_scan.append(entry.path)
                        except OSError:
                            pass
            except OSError:
                pass

        shutil.rmtree(ws.work_dir, ignore_errors=True)
        self._cleaned_up.add(ws.issue)
        self._freed_bytes += dir_bytes
        freed_mb = dir_bytes / (1024**2)
        print(
            f"[{ws.issue}] Cleaned up work dir ({freed_mb:.0f}MB freed, log preserved at {ws.log_file})"
        )

    def _workstream_runtime_budget(self, ws: Workstream, default_budget: int) -> int:
        """Resolve the runtime budget for a single workstream.

        ``monitor(max_runtime=...)`` provides the run-wide default budget, while
        ``ws.max_runtime`` remains the authoritative per-workstream override.
        """
        if ws.max_runtime is not None:
            return self._resolve_max_runtime(ws.max_runtime)
        return self._resolve_max_runtime(default_budget)

    def _enforce_running_timeouts(self, default_budget: int) -> None:
        """Transition over-budget running workstreams into resumable timeout state."""
        now = time.time()
        for ws in self.workstreams:
            proc = self._processes.get(ws.issue)
            if proc is None or proc.poll() is not None:
                continue
            if (
                ws.lifecycle_state == "timed_out_resumable"
                and ws.timeout_policy == CONTINUE_PRESERVE_TIMEOUT_POLICY
            ):
                continue
            budget = self._workstream_runtime_budget(ws, default_budget)
            started_at = ws.start_time if ws.start_time is not None else now
            if now - started_at >= budget:
                self._timed_out(ws, budget)

    def monitor(self, check_interval: int = 10, max_runtime: int | None = None) -> None:
        """Monitor all workstreams until they complete or hit their runtime budgets.

        ``max_runtime`` provides the run-wide default timeout budget. Individual
        workstreams can override that default via ``ws.max_runtime`` and are
        timed out independently while monitoring continues for the rest.
        """
        start = time.time()
        runtime_budget = self._resolve_max_runtime(
            self.default_max_runtime if max_runtime is None else max_runtime
        )

        while True:
            self._enforce_running_timeouts(runtime_budget)
            status = self.get_status()

            now = datetime.now().strftime("%H:%M:%S")
            elapsed = int(time.time() - start)
            self._stdout_write(
                f"\n[{now}] Status (elapsed: {elapsed}s):\n"
                f"  Running:   {len(status['running'])} {sorted(status['running'])}\n"
                f"  Completed: {len(status['completed'])} {sorted(status['completed'])}\n"
                f"  Failed:    {len(status['failed'])} {sorted(status['failed'])}\n"
            )

            # Emit machine-readable JSONL heartbeat
            ws_summaries = []
            for ws in self.workstreams:
                if ws.issue in status["running"]:
                    ws_status = "running"
                elif ws.issue in status["completed"]:
                    ws_status = "completed"
                elif ws.issue in status["failed"]:
                    ws_status = "failed"
                else:
                    ws_status = "unknown"
                ws_summaries.append(self._workstream_summary(ws, ws_status))
            heartbeat = {
                "type": "heartbeat",
                "ts": time.time(),
                "elapsed_seconds": elapsed,
                "elapsed_s": elapsed,
                "summary": {
                    "running": len(status["running"]),
                    "completed": len(status["completed"]),
                    "failed": len(status["failed"]),
                    "total": len(self.workstreams),
                },
                "workstreams": ws_summaries,
            }
            parent_step = os.environ.get("AMPLIHACK_PARENT_STEP")
            if parent_step:
                heartbeat["parent_step"] = parent_step
            self._emit_stderr_event(heartbeat)

            # Auto-cleanup completed and failed workstream directories
            for ws in self.workstreams:
                if ws.issue not in self._cleaned_up and ws.exit_code is not None:
                    self._cleanup_workstream_dir(ws)

            if not status["running"]:
                break

            time.sleep(check_interval)

    def report(self) -> str:
        """Generate final report."""
        lines = [
            "",
            "=" * 70,
            "PARALLEL WORKSTREAM REPORT",
            f"Mode: {self.mode}",
            "=" * 70,
        ]

        succeeded = 0
        failed = 0

        for ws in self.workstreams:
            runtime = f"{ws.runtime_seconds:.0f}s" if ws.runtime_seconds else "N/A"
            status = "OK" if ws.exit_code == 0 else f"FAILED (exit {ws.exit_code})"
            if ws.exit_code == 0:
                succeeded += 1
            else:
                failed += 1

            lines.extend(
                [
                    f"\n[{ws.issue}] {ws.description}",
                    f"  Branch:  {ws.branch}",
                    f"  Status:  {status}",
                    f"  Lifecycle: {ws.lifecycle_state or 'pending'}",
                    f"  Runtime: {runtime}",
                    f"  Checkpoint: {ws.checkpoint_id or 'n/a'}",
                    f"  Worktree: {ws.worktree_path or 'n/a'}",
                    f"  Log:     {ws.log_file}",
                    f"  Cleanup eligible: {ws.cleanup_eligible}",
                ]
            )

        # Calculate remaining disk usage (after auto-cleanup)
        disk_usage_gb, ws_count = self._calculate_disk_usage()
        freed_gb = self._freed_bytes / (1024**3)

        lines.extend(
            [
                "",
                "-" * 70,
                f"Total: {len(self.workstreams)} | Succeeded: {succeeded} | Failed: {failed}",
                "",
                "DISK MANAGEMENT:",
                f"  Auto-cleaned: {len(self._cleaned_up)} workstream dirs ({freed_gb:.2f}GB freed)",
                f"  Remaining on disk: {ws_count} dirs ({disk_usage_gb:.2f}GB)",
                f"  Log files preserved at: {self.tmp_base}/log-*.txt",
                "=" * 70,
            ]
        )

        report_text = "\n".join(lines)
        print(report_text)

        # Write report to file
        report_file = self.tmp_base / "REPORT.md"
        report_file.write_text(report_text)
        print(f"\nReport saved to: {report_file}")

        return report_text

    def _check_disk_space(self, min_free_gb: float = 5.0) -> None:
        """Check available disk space and abort if critically low.

        Threshold lowered from 10GB to 5GB because shallow clones (--depth=1)
        use ~50MB each instead of ~1.5GB. Auto-cleanup reclaims space as
        workstreams complete.
        """
        usage = shutil.disk_usage(self.tmp_base)
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
        used_percent = (usage.used / usage.total) * 100

        print("\nDisk Space Check:")
        print(f"  Location: {self.tmp_base}")
        print(f"  Free: {free_gb:.1f}GB / {total_gb:.1f}GB ({100 - used_percent:.1f}% available)")

        if free_gb < min_free_gb:
            # Non-interactive: fail loudly if disk is low, don't prompt
            print(f"\n⚠  WARNING: Only {free_gb:.1f}GB free (threshold: {min_free_gb}GB)")
            print("  Each shallow clone requires ~50MB. Clean up old workstreams to proceed:")
            print(f"    rm -rf {self.tmp_base}/ws-*")
            print("  Or set AMPLIHACK_SKIP_DISK_CHECK=1 to bypass this check.")
            print()

            if os.environ.get("AMPLIHACK_SKIP_DISK_CHECK") == "1":
                print("Disk check bypassed via AMPLIHACK_SKIP_DISK_CHECK=1")
                return

            # In a TTY, prompt. In non-interactive context, abort.
            if sys.stdin.isatty():
                try:
                    response = input("Continue anyway? (y/N): ").strip().lower()
                    if response != "y":
                        print("Aborted by user.")
                        sys.exit(0)
                except (EOFError, KeyboardInterrupt):
                    print("\nAborted.")
                    sys.exit(1)  # Exit code 1 (not 0) so recipe runner detects failure
            else:
                print("Non-interactive environment: aborting due to low disk space.")
                print("Set AMPLIHACK_SKIP_DISK_CHECK=1 to proceed anyway.")
                sys.exit(1)  # Exit code 1 so recipe runner step fails loudly

    def _calculate_disk_usage(self) -> tuple[float, int]:
        """Calculate total disk usage of all workstream directories.

        Returns:
            (total_size_gb, workstream_count)
        """
        total_bytes = 0
        ws_count = 0

        if not self.tmp_base.exists():
            return (0.0, 0)

        for item in self.tmp_base.iterdir():
            if item.is_dir() and item.name.startswith("ws-"):
                ws_count += 1
                for dirpath, _dirnames, filenames in os.walk(item):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_bytes += os.path.getsize(filepath)
                        except OSError:
                            pass  # File disappeared or inaccessible

        total_gb = total_bytes / (1024**3)
        return (total_gb, ws_count)

    def cleanup_running(self) -> None:
        """Terminate all running workstreams."""
        for ws in self.workstreams:
            self._interrupt_workstream(ws)

    def cleanup_merged(self, config_path: str, dry_run: bool = False) -> None:
        """Clean up workstreams whose PRs have been merged.

        Args:
            config_path: Path to original workstreams config file
            dry_run: If True, only show what would be deleted without deleting
        """
        config = json.loads(Path(config_path).read_text())
        deleted_count = 0
        freed_gb = 0.0

        print("\nChecking PR status for workstream cleanup...")

        for item in config:
            issue = item["issue"]
            if str(issue).upper() == "TBD":
                continue

            # Check PR status using gh CLI
            try:
                result = subprocess.run(
                    ["gh", "pr", "list", "--search", f"#{issue}", "--json", "number,state,merged"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    prs = json.loads(result.stdout)
                    pr_merged = any(pr.get("merged") or pr.get("state") == "MERGED" for pr in prs)

                    if pr_merged:
                        ws_dir = self.tmp_base / f"ws-{issue}"
                        state = self._load_state(int(issue))
                        cleanup_eligible = bool(
                            state.get(
                                "cleanup_eligible",
                                self._derive_cleanup_eligible(
                                    str(state.get("lifecycle_state", "failed_terminal"))
                                ),
                            )
                        )
                        if not cleanup_eligible:
                            print(f"  [SKIP] ws-{issue} (preserved resumable state)")
                            continue
                        if ws_dir.exists():
                            # Calculate size before deleting
                            dir_size = 0
                            for dirpath, _dirs, files in os.walk(ws_dir):
                                for f in files:
                                    fp = os.path.join(dirpath, f)
                                    try:
                                        dir_size += os.path.getsize(fp)
                                    except OSError:
                                        pass
                            size_gb = dir_size / (1024**3)

                            if dry_run:
                                print(f"  [DRY RUN] Would delete ws-{issue} ({size_gb:.2f}GB)")
                            else:
                                shutil.rmtree(ws_dir)
                                print(f"  ✓ Deleted ws-{issue} (PR merged, freed {size_gb:.2f}GB)")
                                deleted_count += 1
                                freed_gb += size_gb
                    else:
                        print(f"  [SKIP] ws-{issue} (PR not merged yet)")
                else:
                    print(f"  [ERROR] Could not check PR status for #{issue}")
            except Exception as e:
                print(f"  [ERROR] Failed to process #{issue}: {e}")

        print(f"\n{'DRY RUN ' if dry_run else ''}Summary:")
        print(f"  Workstreams {'would be ' if dry_run else ''}deleted: {deleted_count}")
        print(f"  Disk space {'would be ' if dry_run else ''}freed: {freed_gb:.2f}GB")

        if dry_run and deleted_count > 0:
            print("\nRun without --dry-run to actually delete these workstreams.")


def run(
    config_path: str,
    mode: str = "recipe",
    recipe: str = "default-workflow",
    *,
    max_runtime: int | None = None,
    timeout_policy: str | None = None,
) -> str:
    """Main entry point for the orchestrator.

    Args:
        config_path: Path to JSON config file with workstream definitions.
        mode: Execution mode - "recipe" (default) or "classic".
        recipe: Recipe name for recipe mode (default: "default-workflow").

    Returns:
        Report text.
    """
    config = json.loads(Path(config_path).read_text())

    # Detect repo URL from git remote
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    repo_url = result.stdout.strip() if result.returncode == 0 else ""
    if not repo_url:
        # Fall back to env var from recipe, then to cwd (valid local clone source)
        repo_url = os.environ.get("AMPLIHACK_REPO_PATH", "") or os.getcwd()
        print(f"WARNING: No git remote 'origin'; using local path: {repo_url}")

    orchestrator = ParallelOrchestrator(repo_url=repo_url, mode=mode)
    run_max_runtime = orchestrator._resolve_max_runtime(
        orchestrator.default_max_runtime if max_runtime is None else max_runtime
    )
    run_timeout_policy = orchestrator._resolve_timeout_policy(
        timeout_policy or orchestrator.default_timeout_policy
    )
    orchestrator.setup()

    for item in config:
        orchestrator.add(
            issue=item["issue"],
            branch=item["branch"],
            description=item.get("description", f"Issue #{item['issue']}"),
            task=item["task"],
            recipe=item.get("recipe", recipe),
            max_runtime=item.get("max_runtime", run_max_runtime),
            timeout_policy=item.get("timeout_policy", run_timeout_policy),
        )

    # Handle SIGINT gracefully
    def signal_handler(sig, frame):
        print("\nInterrupted! Cleaning up workstreams...")
        orchestrator.cleanup_running()
        sys.exit(130)

    signal.signal(signal.SIGINT, signal_handler)

    orchestrator.launch_all()
    orchestrator.monitor(max_runtime=run_max_runtime)
    return orchestrator.report()


def cleanup(config_path: str, dry_run: bool = False) -> None:
    """Clean up workstreams with merged PRs.

    Args:
        config_path: Path to JSON config file with workstream definitions
        dry_run: If True, show what would be deleted without deleting
    """
    # Detect repo URL
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    repo_url = result.stdout.strip() if result.returncode == 0 else ""

    orchestrator = ParallelOrchestrator(repo_url=repo_url)
    orchestrator.cleanup_merged(config_path, dry_run=dry_run)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parallel Workstream Orchestrator")
    parser.add_argument("config", help="Path to workstreams JSON config file")
    parser.add_argument(
        "--mode",
        choices=["recipe", "classic"],
        default="recipe",
        help="Execution mode (default: recipe)",
    )
    parser.add_argument(
        "--recipe",
        default="default-workflow",
        help="Recipe name for recipe mode (default: default-workflow)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up workstreams with merged PRs instead of running tasks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting (use with --cleanup)",
    )
    parser.add_argument(
        "--max-runtime",
        type=int,
        default=None,
        help=f"Override the workstream runtime budget in seconds (default: {DEFAULT_MAX_RUNTIME})",
    )
    parser.add_argument(
        "--timeout-policy",
        default=None,
        help=f"Timeout policy for active workstreams (default: {DEFAULT_TIMEOUT_POLICY})",
    )
    args = parser.parse_args()

    if args.cleanup:
        cleanup(args.config, dry_run=args.dry_run)
    else:
        if args.dry_run:
            print("WARNING: --dry-run only works with --cleanup, ignoring")
        run(
            args.config,
            mode=args.mode,
            recipe=args.recipe,
            max_runtime=args.max_runtime,
            timeout_policy=args.timeout_policy,
        )
