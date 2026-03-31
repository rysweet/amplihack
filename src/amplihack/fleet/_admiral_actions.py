"""Action executors for the fleet admiral.

Standalone functions that execute DirectorActions on behalf of FleetAdmiral.
Each function takes the components it needs (azlin_path, task_queue, auth)
rather than the entire admiral, keeping coupling minimal.

Public API:
    execute_action: Dispatch a DirectorAction to the appropriate executor
    start_agent: Start a coding agent in a tmux session on a VM
    mark_complete: Mark a task as completed
    mark_failed: Mark a task as failed
    reassign_task: Stop stuck agent and requeue task
    propagate_auth: Propagate auth tokens to a VM
"""

from __future__ import annotations

import logging
import shlex
import subprocess

from amplihack.fleet._admiral_types import ActionType, DirectorAction
from amplihack.fleet._constants import (
    SUBPROCESS_TIMEOUT_KILL_SECONDS,
    SUBPROCESS_TIMEOUT_SECONDS,
)
from amplihack.fleet._error_sanitizer import sanitize_external_error_detail
from amplihack.fleet._validation import validate_session_name, validate_vm_name
from amplihack.fleet.fleet_auth import AuthPropagator
from amplihack.fleet.fleet_tasks import TaskQueue, TaskStatus

__all__ = [
    "execute_action",
    "start_agent",
    "mark_complete",
    "mark_failed",
    "reassign_task",
    "propagate_auth",
]

logger = logging.getLogger(__name__)


def execute_action(
    action: DirectorAction,
    azlin_path: str,
    task_queue: TaskQueue,
    auth: AuthPropagator,
) -> str:
    """Dispatch a single action to the appropriate executor."""
    if action.action_type == ActionType.START_AGENT:
        return start_agent(action, azlin_path, task_queue)
    if action.action_type == ActionType.MARK_COMPLETE:
        return mark_complete(action, task_queue)
    if action.action_type == ActionType.MARK_FAILED:
        return mark_failed(action, task_queue)
    if action.action_type == ActionType.REASSIGN_TASK:
        return reassign_task(action, azlin_path, task_queue)
    if action.action_type == ActionType.PROPAGATE_AUTH:
        return propagate_auth(action, auth)
    return f"Unknown action: {action.action_type}"


def start_agent(
    action: DirectorAction,
    azlin_path: str,
    task_queue: TaskQueue,
) -> str:
    """Start a coding agent in a tmux session on a VM."""
    task = action.task
    if not task:
        return "ERROR: No task provided"

    vm_name = action.vm_name
    if not vm_name:
        return "ERROR: No VM name provided"
    session_name = action.session_name or f"fleet-{task.id}"
    validate_vm_name(vm_name)
    validate_session_name(session_name)

    # Validate agent command and mode against allowlist (security: prevent injection)
    valid_agents = {"claude", "amplifier", "copilot"}
    valid_modes = {"auto", "ultrathink"}
    if task.agent_command not in valid_agents:
        return f"ERROR: Invalid agent command: {task.agent_command!r}"
    if task.agent_mode not in valid_modes:
        return f"ERROR: Invalid agent mode: {task.agent_mode!r}"
    if not isinstance(task.max_turns, int) or task.max_turns < 1 or task.max_turns > 1000:
        return f"ERROR: Invalid max_turns: {task.max_turns!r}"

    # Build the tmux command to start an agent
    safe_session = shlex.quote(session_name)
    safe_prompt = shlex.quote(task.prompt)
    safe_agent = shlex.quote(task.agent_command)
    safe_mode = shlex.quote(task.agent_mode)
    safe_turns = shlex.quote(str(int(task.max_turns)))

    # Create tmux session and start agent
    setup_cmd = (
        f"tmux new-session -d -s {safe_session} && "
        f"tmux send-keys -t {safe_session} "
        f"'amplihack {safe_agent} --{safe_mode} "
        f"--max-turns {safe_turns} "
        f"-- -p {safe_prompt}' C-m"
    )

    try:
        result = subprocess.run(
            [azlin_path, "connect", vm_name, "--no-tmux", "--", setup_cmd],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )

        if result.returncode == 0:
            task.assign(vm_name, session_name)
            task.start()
            task_queue.save()
            return f"Agent started: {session_name} on {vm_name}"
        detail = sanitize_external_error_detail(result.stderr)
        return f"ERROR: Failed to start agent: {detail}"

    except subprocess.TimeoutExpired:
        return "ERROR: Timeout starting agent"
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        detail = sanitize_external_error_detail(str(e))
        return f"ERROR: {detail}"


def mark_complete(action: DirectorAction, task_queue: TaskQueue) -> str:
    """Mark a task as completed."""
    if action.task:
        action.task.complete(result="Detected as completed by observer")
    task_queue.save()
    return "Task marked complete"


def mark_failed(action: DirectorAction, task_queue: TaskQueue) -> str:
    """Mark a task as failed."""
    if action.task:
        action.task.fail(error=action.reason)
    task_queue.save()
    return f"Task marked failed: {action.reason}"


def reassign_task(
    action: DirectorAction,
    azlin_path: str,
    task_queue: TaskQueue,
) -> str:
    """Stop stuck agent and requeue task."""
    if action.task and action.vm_name and action.session_name:
        validate_vm_name(action.vm_name)
        # Kill the stuck session
        kill_cmd = f"tmux kill-session -t {shlex.quote(action.session_name)} 2>/dev/null || true"
        try:
            subprocess.run(
                [azlin_path, "connect", action.vm_name, "--no-tmux", "--", kill_cmd],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT_KILL_SECONDS,
            )
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(
                "Failed to kill stuck session %s on %s: %s",
                action.session_name,
                action.vm_name,
                e,
            )

        # Requeue the task
        action.task.status = TaskStatus.QUEUED
        action.task.assigned_vm = None
        action.task.assigned_session = None
        task_queue.save()
        return "Stuck agent killed, task requeued"

    return "ERROR: Missing task/vm/session for reassignment"


def propagate_auth(action: DirectorAction, auth: AuthPropagator) -> str:
    """Propagate auth tokens to a VM."""
    if action.vm_name:
        results = auth.propagate_all(action.vm_name)
        success = sum(1 for r in results if r.success)
        return f"Auth propagated: {success}/{len(results)} services"
    return "ERROR: No VM specified"
