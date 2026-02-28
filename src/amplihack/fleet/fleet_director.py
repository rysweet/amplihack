"""Fleet Director — autonomous PERCEIVE→REASON→ACT→LEARN loop.

The director manages a fleet of VMs running coding agents. It:
1. PERCEIVE: Polls all VMs and tmux sessions for current state
2. REASON: Compares progress vs priorities, identifies actions needed
3. ACT: Starts agents, reassigns work, reports to human
4. LEARN: Tracks patterns (which VM/agent combos work best)

This is the central control plane for fleet orchestration.

Public API:
    FleetDirector: Autonomous fleet management agent
"""

from __future__ import annotations

import json
import logging
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from amplihack.fleet.fleet_auth import AuthPropagator
from amplihack.fleet.fleet_observer import FleetObserver
from amplihack.fleet.fleet_state import AgentStatus, FleetState, VMInfo
from amplihack.fleet.fleet_tasks import FleetTask, TaskPriority, TaskQueue, TaskStatus

__all__ = ["FleetDirector"]

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions the director can take."""

    START_AGENT = "start_agent"
    STOP_AGENT = "stop_agent"
    REASSIGN_TASK = "reassign_task"
    MARK_COMPLETE = "mark_complete"
    MARK_FAILED = "mark_failed"
    REPORT = "report"
    PROVISION_VM = "provision_vm"
    PROPAGATE_AUTH = "propagate_auth"


@dataclass
class DirectorAction:
    """A single action decided by the director."""

    action_type: ActionType
    task: Optional[FleetTask] = None
    vm_name: Optional[str] = None
    session_name: Optional[str] = None
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DirectorLog:
    """Record of director decisions and outcomes."""

    actions: list[dict] = field(default_factory=list)
    persist_path: Optional[Path] = None

    def record(self, action: DirectorAction, outcome: str) -> None:
        """Record an action and its outcome."""
        entry = {
            "timestamp": action.timestamp.isoformat(),
            "action": action.action_type.value,
            "vm": action.vm_name,
            "session": action.session_name,
            "task_id": action.task.id if action.task else None,
            "reason": action.reason,
            "outcome": outcome,
        }
        self.actions.append(entry)
        self._save()

    def _save(self) -> None:
        if self.persist_path:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            self.persist_path.write_text(json.dumps(self.actions, indent=2))


@dataclass
class FleetDirector:
    """Autonomous fleet management agent.

    Runs PERCEIVE→REASON→ACT→LEARN loop to manage VMs and agents.
    """

    task_queue: TaskQueue
    azlin_path: str = "/home/azureuser/src/azlin/.venv/bin/azlin"
    poll_interval_seconds: float = 60.0
    max_agents_per_vm: int = 3
    log_dir: Optional[Path] = None

    # Internal state
    _fleet_state: FleetState = field(default_factory=FleetState)
    _observer: FleetObserver = field(default_factory=FleetObserver)
    _auth: AuthPropagator = field(default_factory=AuthPropagator)
    _log: DirectorLog = field(default_factory=DirectorLog)
    _exclude_vms: set[str] = field(default_factory=set)
    _running: bool = False
    _cycle_count: int = 0

    def __post_init__(self):
        self._fleet_state.azlin_path = self.azlin_path
        self._observer.azlin_path = self.azlin_path
        self._auth.azlin_path = self.azlin_path

        if self.log_dir:
            self._log.persist_path = self.log_dir / "director_log.json"
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def exclude_vms(self, *vm_names: str) -> FleetDirector:
        """Mark VMs that should not be managed (user's existing VMs)."""
        self._exclude_vms.update(vm_names)
        self._fleet_state.exclude_vms(*vm_names)
        return self

    def run_once(self) -> list[DirectorAction]:
        """Execute one PERCEIVE→REASON→ACT cycle.

        Returns list of actions taken.
        """
        self._cycle_count += 1
        logger.info(f"Director cycle {self._cycle_count}")

        # PERCEIVE
        state = self.perceive()

        # REASON
        actions = self.reason(state)

        # ACT
        results = self.act(actions)

        # LEARN
        self.learn(results)

        return actions

    def run_loop(self, max_cycles: int = 0) -> None:
        """Run continuous director loop.

        Args:
            max_cycles: Max cycles before stopping (0 = unlimited)
        """
        self._running = True
        cycle = 0

        while self._running:
            cycle += 1
            if max_cycles and cycle > max_cycles:
                break

            try:
                self.run_once()
            except KeyboardInterrupt:
                logger.info("Director interrupted by user")
                break
            except Exception as e:
                logger.error(f"Director cycle error: {e}")

            # Check if all tasks are done
            if not self.task_queue.next_task() and not self.task_queue.active_tasks():
                logger.info("All tasks completed. Director stopping.")
                break

            time.sleep(self.poll_interval_seconds)

        self._running = False

    def stop(self) -> None:
        """Signal the director to stop after current cycle."""
        self._running = False

    def perceive(self) -> FleetState:
        """Poll all VMs and tmux sessions.

        Returns current fleet state with agent status classification.
        """
        logger.info("PERCEIVE: Refreshing fleet state")
        self._fleet_state.refresh()

        # Observe agent state in each managed session
        for vm in self._fleet_state.managed_vms():
            if not vm.is_running:
                continue
            for session in vm.tmux_sessions:
                obs = self._observer.observe_session(vm.name, session.session_name)
                session.agent_status = obs.status
                session.last_output = "\n".join(obs.last_output_lines)

        return self._fleet_state

    def reason(self, state: FleetState) -> list[DirectorAction]:
        """Decide what actions to take based on current state.

        Decision priorities:
        1. Handle completed agents (mark tasks done)
        2. Handle stuck/errored agents (reassign or fail)
        3. Assign queued tasks to idle VMs
        """
        actions: list[DirectorAction] = []

        # 1. Check active tasks against observed state
        for task in self.task_queue.active_tasks():
            if not task.assigned_vm or not task.assigned_session:
                continue

            vm = state.get_vm(task.assigned_vm)
            if not vm:
                continue

            # Find the session
            session = None
            for s in vm.tmux_sessions:
                if s.session_name == task.assigned_session:
                    session = s
                    break

            if not session:
                # Session gone — task likely completed or crashed
                actions.append(
                    DirectorAction(
                        action_type=ActionType.MARK_FAILED,
                        task=task,
                        vm_name=task.assigned_vm,
                        session_name=task.assigned_session,
                        reason="Session no longer exists",
                    )
                )
                continue

            if session.agent_status == AgentStatus.COMPLETED:
                actions.append(
                    DirectorAction(
                        action_type=ActionType.MARK_COMPLETE,
                        task=task,
                        vm_name=task.assigned_vm,
                        session_name=task.assigned_session,
                        reason="Agent completed successfully",
                    )
                )
            elif session.agent_status == AgentStatus.ERROR:
                actions.append(
                    DirectorAction(
                        action_type=ActionType.MARK_FAILED,
                        task=task,
                        vm_name=task.assigned_vm,
                        session_name=task.assigned_session,
                        reason=f"Agent error detected: {session.last_output[-200:]}",
                    )
                )
            elif session.agent_status == AgentStatus.STUCK:
                actions.append(
                    DirectorAction(
                        action_type=ActionType.REASSIGN_TASK,
                        task=task,
                        vm_name=task.assigned_vm,
                        session_name=task.assigned_session,
                        reason="Agent appears stuck (no output change)",
                    )
                )

        # 2. Assign queued tasks to available capacity
        next_task = self.task_queue.next_task()
        while next_task:
            target = self._find_best_vm(state)
            if not target:
                break  # No available capacity

            vm_name, session_name = target
            actions.append(
                DirectorAction(
                    action_type=ActionType.START_AGENT,
                    task=next_task,
                    vm_name=vm_name,
                    session_name=session_name,
                    reason=f"Assigning {next_task.priority.name} task to idle capacity",
                )
            )
            # Mark as assigned so next_task() skips it
            next_task.assign(vm_name, session_name)

            next_task = self.task_queue.next_task()

        return actions

    def act(self, actions: list[DirectorAction]) -> list[tuple[DirectorAction, str]]:
        """Execute decided actions.

        Returns list of (action, outcome) tuples.
        """
        results = []

        for action in actions:
            try:
                outcome = self._execute_action(action)
                self._log.record(action, outcome)
                results.append((action, outcome))
                logger.info(
                    f"ACT: {action.action_type.value} on {action.vm_name} — {outcome}"
                )
            except Exception as e:
                outcome = f"ERROR: {e}"
                self._log.record(action, outcome)
                results.append((action, outcome))
                logger.error(f"ACT failed: {action.action_type.value} — {e}")

        return results

    def learn(self, results: list[tuple[DirectorAction, str]]) -> None:
        """Update patterns based on action outcomes.

        For now, just log. Future: track success rates per VM/agent combo.
        """
        for action, outcome in results:
            if "ERROR" in outcome:
                logger.warning(
                    f"LEARN: Action {action.action_type.value} failed on {action.vm_name}: {outcome}"
                )

    def status_report(self) -> str:
        """Generate human-readable status report."""
        lines = [
            "=" * 60,
            f"Fleet Director Report — Cycle {self._cycle_count}",
            "=" * 60,
            "",
            self._fleet_state.summary(),
            "",
            self.task_queue.summary(),
            "",
            f"Director log: {len(self._log.actions)} actions recorded",
        ]
        return "\n".join(lines)

    def _execute_action(self, action: DirectorAction) -> str:
        """Execute a single action."""
        if action.action_type == ActionType.START_AGENT:
            return self._start_agent(action)
        elif action.action_type == ActionType.MARK_COMPLETE:
            return self._mark_complete(action)
        elif action.action_type == ActionType.MARK_FAILED:
            return self._mark_failed(action)
        elif action.action_type == ActionType.REASSIGN_TASK:
            return self._reassign_task(action)
        elif action.action_type == ActionType.PROPAGATE_AUTH:
            return self._propagate_auth(action)
        else:
            return f"Unknown action: {action.action_type}"

    def _start_agent(self, action: DirectorAction) -> str:
        """Start a coding agent in a tmux session on a VM."""
        task = action.task
        if not task:
            return "ERROR: No task provided"

        vm_name = action.vm_name
        session_name = action.session_name or f"fleet-{task.id}"

        # Build the tmux command to start an agent
        safe_session = shlex.quote(session_name)
        safe_prompt = shlex.quote(task.prompt)

        # Create tmux session and start agent
        setup_cmd = (
            f"tmux new-session -d -s {safe_session} 2>/dev/null || true && "
            f"tmux send-keys -t {safe_session} "
            f"'amplihack {task.agent_command} --{task.agent_mode} "
            f"--max-turns {task.max_turns} "
            f"-- -p {safe_prompt}' C-m"
        )

        try:
            result = subprocess.run(
                [self.azlin_path, "connect", vm_name, "--no-tmux", "--", setup_cmd],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                task.start()
                return f"Agent started: {session_name} on {vm_name}"
            else:
                return f"ERROR: Failed to start agent: {result.stderr[:200]}"

        except subprocess.TimeoutExpired:
            return "ERROR: Timeout starting agent"
        except subprocess.SubprocessError as e:
            return f"ERROR: {e}"

    def _mark_complete(self, action: DirectorAction) -> str:
        """Mark a task as completed."""
        if action.task:
            action.task.complete(result="Detected as completed by observer")
        return "Task marked complete"

    def _mark_failed(self, action: DirectorAction) -> str:
        """Mark a task as failed."""
        if action.task:
            action.task.fail(error=action.reason)
        return f"Task marked failed: {action.reason}"

    def _reassign_task(self, action: DirectorAction) -> str:
        """Stop stuck agent and requeue task."""
        if action.task and action.vm_name and action.session_name:
            # Kill the stuck session
            kill_cmd = f"tmux kill-session -t {shlex.quote(action.session_name)} 2>/dev/null || true"
            try:
                subprocess.run(
                    [self.azlin_path, "connect", action.vm_name, "--no-tmux", "--", kill_cmd],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass

            # Requeue the task
            action.task.status = TaskStatus.QUEUED
            action.task.assigned_vm = None
            action.task.assigned_session = None
            return f"Stuck agent killed, task requeued"

        return "ERROR: Missing task/vm/session for reassignment"

    def _propagate_auth(self, action: DirectorAction) -> str:
        """Propagate auth tokens to a VM."""
        if action.vm_name:
            results = self._auth.propagate_all(action.vm_name)
            success = sum(1 for r in results if r.success)
            return f"Auth propagated: {success}/{len(results)} services"
        return "ERROR: No VM specified"

    def _find_best_vm(self, state: FleetState) -> Optional[tuple[str, str]]:
        """Find the best VM and session name for a new task.

        Returns (vm_name, session_name) or None if no capacity.
        """
        managed = state.managed_vms()
        candidates = []

        for vm in managed:
            if not vm.is_running:
                continue

            active = vm.active_agents
            if active < self.max_agents_per_vm:
                # Score: prefer VMs with fewer active agents
                score = self.max_agents_per_vm - active
                candidates.append((score, vm.name))

        if not candidates:
            return None

        # Pick VM with most available capacity
        candidates.sort(reverse=True)
        best_vm = candidates[0][1]
        session_name = f"fleet-{int(time.time()) % 10000}"

        return best_vm, session_name
