"""Fleet Admiral — autonomous PERCEIVE→REASON→ACT→LEARN loop.

The admiral manages a fleet of VMs running coding agents. It:
1. PERCEIVE: Polls all VMs and tmux sessions for current state
2. REASON: Compares progress vs priorities, identifies actions needed
3. ACT: Starts agents, reassigns work, reports to human
4. LEARN: Tracks patterns (which VM/agent combos work best)

This is the central control plane for fleet orchestration.

Public API:
    FleetAdmiral: Autonomous fleet management agent
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

from amplihack.fleet._defaults import get_azlin_path
from amplihack.fleet._validation import validate_session_name, validate_vm_name
from amplihack.fleet.fleet_auth import AuthPropagator
from amplihack.fleet.fleet_observer import FleetObserver
from amplihack.fleet.fleet_state import FleetState
from amplihack.fleet.fleet_tasks import FleetTask, TaskQueue, TaskStatus

__all__ = ["FleetAdmiral"]

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions the admiral can take."""

    START_AGENT = "start_agent"
    STOP_AGENT = "stop_agent"
    REASSIGN_TASK = "reassign_task"
    MARK_COMPLETE = "mark_complete"
    MARK_FAILED = "mark_failed"
    REPORT = "report"
    PROPAGATE_AUTH = "propagate_auth"


@dataclass
class DirectorAction:
    """A single action decided by the admiral."""

    action_type: ActionType
    task: FleetTask | None = None
    vm_name: str | None = None
    session_name: str | None = None
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DirectorLog:
    """Record of admiral decisions and outcomes."""

    actions: list[dict] = field(default_factory=list)
    persist_path: Path | None = None

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
        # Cap action history to prevent unbounded growth
        if len(self.actions) > 1000:
            self.actions = self.actions[-1000:]
        self._save()

    def _save(self) -> None:
        if self.persist_path:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic write: temp file then rename
            tmp = self.persist_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.actions, indent=2))
            tmp.rename(self.persist_path)


@dataclass
class FleetAdmiral:
    """Autonomous fleet management agent.

    Runs PERCEIVE→REASON→ACT→LEARN loop to manage VMs and agents.
    """

    task_queue: TaskQueue
    azlin_path: str = field(default_factory=get_azlin_path)
    poll_interval_seconds: float = 60.0
    max_agents_per_vm: int = 3
    log_dir: Path | None = None

    # Internal state
    _fleet_state: FleetState = field(default_factory=FleetState)
    _observer: FleetObserver = field(default_factory=FleetObserver)
    _auth: AuthPropagator = field(default_factory=AuthPropagator)
    _log: DirectorLog = field(default_factory=DirectorLog)
    _exclude_vms: set[str] = field(default_factory=set)
    _running: bool = False
    _cycle_count: int = 0
    _missing_session_counts: dict[str, int] = field(default_factory=dict)
    _stats: dict[str, int] = field(
        default_factory=lambda: {"actions": 0, "successes": 0, "failures": 0}
    )

    def __post_init__(self):
        # Lazy import to avoid circular dependency (fleet_reasoners imports from fleet_admiral)
        from amplihack.fleet.fleet_reasoners import (
            BatchAssignReasoner,
            CoordinationReasoner,
            LifecycleReasoner,
            PreemptionReasoner,
            ReasonerChain,
        )

        self._fleet_state.azlin_path = self.azlin_path
        self._observer.azlin_path = self.azlin_path
        self._auth.azlin_path = self.azlin_path
        self._reasoner_chain = ReasonerChain(
            reasoners=[
                LifecycleReasoner(),
                PreemptionReasoner(),
                CoordinationReasoner(),
                BatchAssignReasoner(max_agents_per_vm=self.max_agents_per_vm),
            ]
        )

        if self.log_dir:
            self._log.persist_path = self.log_dir / "admiral_log.json"
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def exclude_vms(self, *vm_names: str) -> FleetAdmiral:
        """Mark VMs that should not be managed (user's existing VMs)."""
        self._exclude_vms.update(vm_names)
        self._fleet_state.exclude_vms(*vm_names)
        return self

    @property
    def fleet_state(self) -> FleetState:
        """Public access to fleet state (avoids _fleet_state private access)."""
        return self._fleet_state

    def run_once(self) -> list[DirectorAction]:
        """Execute one PERCEIVE→REASON→ACT cycle.

        Returns list of actions taken.
        """
        self._cycle_count += 1
        logger.info(f"Admiral cycle {self._cycle_count}")

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
        """Run continuous admiral loop.

        Args:
            max_cycles: Max cycles before stopping (0 = unlimited)
        """
        self._running = True
        cycle = 0
        consecutive_failures = 0
        MAX_CONSECUTIVE_FAILURES = 5

        while self._running:
            cycle += 1
            if max_cycles and cycle > max_cycles:
                break

            try:
                self.run_once()
                consecutive_failures = 0  # Reset on success
            except KeyboardInterrupt:
                logger.info("Admiral interrupted by user")
                break
            except Exception as e:
                consecutive_failures += 1
                logger.error(
                    f"Admiral cycle error ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}): {e}"
                )
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error(
                        f"CIRCUIT BREAKER: {MAX_CONSECUTIVE_FAILURES} consecutive failures. Stopping admiral."
                    )
                    break

            # Check if all tasks are done
            if not self.task_queue.next_task() and not self.task_queue.active_tasks():
                logger.info("All tasks completed. Admiral stopping.")
                break

            time.sleep(self.poll_interval_seconds)

        self._running = False

    def stop(self) -> None:
        """Signal the admiral to stop after current cycle."""
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
        """Delegate to composable reasoner chain."""
        actions = self._reasoner_chain.reason(state, self.task_queue)
        self.task_queue.save()  # Persist any state mutations from reasoning
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
                logger.info(f"ACT: {action.action_type.value} on {action.vm_name} — {outcome}")
            except Exception as e:
                outcome = f"ERROR: {e}"
                self._log.record(action, outcome)
                results.append((action, outcome))
                logger.error(f"ACT failed: {action.action_type.value} — {e}")

        return results

    def learn(self, results: list[tuple[DirectorAction, str]]) -> None:
        """Track action outcomes and persist learnings to amplihack memory.

        Stores discoveries about:
        - What task types succeed/fail on which VMs
        - Common error patterns and their resolutions
        - Effective strategies for different session states
        """
        for action, outcome in results:
            self._stats["actions"] += 1

            if outcome.startswith("ERROR"):
                self._stats["failures"] += 1
                logger.warning(
                    f"LEARN: {action.action_type.value} failed on {action.vm_name}: {outcome}"
                )

                # Persist failure learning to amplihack memory
                try:
                    from amplihack.memory.discoveries import store_discovery

                    store_discovery(
                        content=f"Fleet action {action.action_type.value} failed on {action.vm_name}: {outcome}",
                        category="fleet-failure",
                        summary=f"{action.action_type.value} failed on {action.vm_name}",
                    )
                except ImportError:
                    pass  # Memory lib not available — graceful degradation
            else:
                self._stats["successes"] += 1

                # Persist success patterns for high-value actions
                if action.action_type.value in ("start_agent", "reassign_task"):
                    try:
                        from amplihack.memory.discoveries import store_discovery

                        store_discovery(
                            content=f"Fleet action {action.action_type.value} succeeded on {action.vm_name}: {outcome}",
                            category="fleet-success",
                            summary=f"{action.action_type.value} on {action.vm_name} succeeded",
                        )
                    except ImportError:
                        pass

    def recall_learnings(self, limit: int = 5) -> list[dict]:
        """Retrieve recent fleet learnings from amplihack memory."""
        try:
            from amplihack.memory.discoveries import get_recent_discoveries

            return get_recent_discoveries(days=30, limit=limit)
        except ImportError:
            return []

    def status_report(self) -> str:
        """Generate human-readable status report."""
        lines = [
            "=" * 60,
            f"Fleet Admiral Report — Cycle {self._cycle_count}",
            "=" * 60,
            "",
            self._fleet_state.summary(),
            "",
            self.task_queue.summary(),
            "",
            f"Admiral log: {len(self._log.actions)} actions recorded",
            "",
            f"Stats: {self._stats['actions']} actions, "
            f"{self._stats['successes']} successes, "
            f"{self._stats['failures']} failures",
        ]
        return "\n".join(lines)

    def _execute_action(self, action: DirectorAction) -> str:
        """Execute a single action."""
        if action.action_type == ActionType.START_AGENT:
            return self._start_agent(action)
        if action.action_type == ActionType.MARK_COMPLETE:
            return self._mark_complete(action)
        if action.action_type == ActionType.MARK_FAILED:
            return self._mark_failed(action)
        if action.action_type == ActionType.REASSIGN_TASK:
            return self._reassign_task(action)
        if action.action_type == ActionType.PROPAGATE_AUTH:
            return self._propagate_auth(action)
        return f"Unknown action: {action.action_type}"

    def _start_agent(self, action: DirectorAction) -> str:
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

        # Create tmux session and start agent
        setup_cmd = (
            f"tmux new-session -d -s {safe_session} && "
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
            return f"ERROR: Failed to start agent: {result.stderr[:200]}"

        except subprocess.TimeoutExpired:
            return "ERROR: Timeout starting agent"
        except (subprocess.SubprocessError, FileNotFoundError) as e:
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
            validate_vm_name(action.vm_name)
            # Kill the stuck session
            kill_cmd = (
                f"tmux kill-session -t {shlex.quote(action.session_name)} 2>/dev/null || true"
            )
            try:
                subprocess.run(
                    [self.azlin_path, "connect", action.vm_name, "--no-tmux", "--", kill_cmd],
                    capture_output=True,
                    text=True,
                    timeout=30,
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
            return "Stuck agent killed, task requeued"

        return "ERROR: Missing task/vm/session for reassignment"

    def _propagate_auth(self, action: DirectorAction) -> str:
        """Propagate auth tokens to a VM."""
        if action.vm_name:
            results = self._auth.propagate_all(action.vm_name)
            success = sum(1 for r in results if r.success)
            return f"Auth propagated: {success}/{len(results)} services"
        return "ERROR: No VM specified"
