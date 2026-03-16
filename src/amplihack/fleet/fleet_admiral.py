"""Fleet Admiral — autonomous PERCEIVE→REASON→ACT→LEARN loop.

The admiral manages a fleet of VMs running coding agents. It:
1. PERCEIVE: Polls all VMs and tmux sessions for current state
2. REASON: Compares progress vs priorities, identifies actions needed
3. ACT: Starts agents, reassigns work, reports to human
4. LEARN: Tracks patterns (which VM/agent combos work best)

This is the central control plane for fleet orchestration.

Public API:
    FleetAdmiral: Autonomous fleet management agent
    ActionType: Re-exported from _admiral_types
    DirectorAction: Re-exported from _admiral_types
    DirectorLog: Re-exported from _admiral_types
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from amplihack.fleet._admiral_actions import execute_action
from amplihack.fleet._admiral_types import ActionType, DirectorAction, DirectorLog
from amplihack.fleet._constants import (
    DEFAULT_MAX_AGENTS_PER_VM,
    DEFAULT_POLL_INTERVAL_SECONDS,
)
from amplihack.fleet._defaults import get_azlin_path
from amplihack.fleet.fleet_auth import AuthPropagator
from amplihack.fleet.fleet_observer import FleetObserver
from amplihack.fleet.fleet_state import FleetState
from amplihack.fleet.fleet_tasks import TaskQueue
from amplihack.utils.logging_utils import log_call

__all__ = ["FleetAdmiral", "ActionType", "DirectorAction", "DirectorLog"]

logger = logging.getLogger(__name__)


@dataclass
class FleetAdmiral:
    """Autonomous fleet management agent.

    Runs PERCEIVE→REASON→ACT→LEARN loop to manage VMs and agents.
    """

    task_queue: TaskQueue
    azlin_path: str = field(default_factory=get_azlin_path)
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS
    max_agents_per_vm: int = DEFAULT_MAX_AGENTS_PER_VM
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

    @log_call
    def __post_init__(self):
        # Lazy import to avoid circular dependency (fleet_reasoners imports from _admiral_types)
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

    @log_call
    def exclude_vms(self, *vm_names: str) -> FleetAdmiral:
        """Mark VMs that should not be managed (user's existing VMs)."""
        self._exclude_vms.update(vm_names)
        self._fleet_state.exclude_vms(*vm_names)
        return self

    @property
    @log_call
    def fleet_state(self) -> FleetState:
        """Public access to fleet state."""
        return self._fleet_state

    @property
    @log_call
    def observer(self) -> FleetObserver:
        """Public access to fleet observer for configuration."""
        return self._observer

    @log_call
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

    @log_call
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

    @log_call
    def stop(self) -> None:
        """Signal the admiral to stop after current cycle."""
        self._running = False

    @log_call
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

    @log_call
    def reason(self, state: FleetState) -> list[DirectorAction]:
        """Delegate to composable reasoner chain."""
        actions = self._reasoner_chain.reason(state, self.task_queue)
        self.task_queue.save()  # Persist any state mutations from reasoning
        return actions

    @log_call
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

    @log_call
    def _execute_action(self, action: DirectorAction) -> str:
        """Dispatch a single action to the appropriate executor."""
        return execute_action(action, self.azlin_path, self.task_queue, self._auth)

    @log_call
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
                from amplihack.memory.discoveries import store_discovery

                store_discovery(
                    content=f"Fleet action {action.action_type.value} failed on {action.vm_name}: {outcome}",
                    category="fleet-failure",
                    summary=f"{action.action_type.value} failed on {action.vm_name}",
                )
            else:
                self._stats["successes"] += 1

                # Persist success patterns for high-value actions
                if action.action_type.value in ("start_agent", "reassign_task"):
                    from amplihack.memory.discoveries import store_discovery

                    store_discovery(
                        content=f"Fleet action {action.action_type.value} succeeded on {action.vm_name}: {outcome}",
                        category="fleet-success",
                        summary=f"{action.action_type.value} on {action.vm_name} succeeded",
                    )

    @log_call
    def recall_learnings(self, limit: int = 5) -> list[dict]:
        """Retrieve recent fleet learnings from amplihack memory."""
        from amplihack.memory.discoveries import get_recent_discoveries

        return get_recent_discoveries(days=30, limit=limit)

    @log_call
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
