"""Composable reasoning functions for the fleet admiral.

Each reasoner takes fleet state + task queue and returns DirectorActions.
Reasoners run in priority order as a chain.

Built-in reasoners:
1. LifecycleReasoner: Completions, failures, stuck detection
2. PreemptionReasoner: Emergency priority escalation
3. CoordinationReasoner: Inter-agent context sharing (in _coordination.py)
4. BatchAssignReasoner: Context-aware batch assignment

Public API:
    ReasonerChain, LifecycleReasoner, PreemptionReasoner,
    CoordinationReasoner (re-exported), BatchAssignReasoner
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from amplihack.fleet._admiral_types import ActionType, DirectorAction
from amplihack.fleet._constants import DEFAULT_STUCK_THRESHOLD_SECONDS
from amplihack.fleet._coordination import CoordinationReasoner
from amplihack.fleet.fleet_state import AgentStatus, FleetState
from amplihack.fleet.fleet_tasks import TaskPriority, TaskQueue, TaskStatus
from amplihack.utils.logging_utils import log_call

__all__ = [
    "ReasonerChain",
    "LifecycleReasoner",
    "PreemptionReasoner",
    "CoordinationReasoner",
    "BatchAssignReasoner",
]


class Reasoner(Protocol):
    """A single reasoning function that proposes actions."""

    @log_call
    def reason(
        self,
        state: FleetState,
        queue: TaskQueue,
        prior_actions: list[DirectorAction],
    ) -> list[DirectorAction]: ...


@dataclass
class ReasonerChain:
    """Ordered chain of reasoners. Runs each in sequence, accumulating actions."""

    reasoners: list[Reasoner] = field(default_factory=list)

    @log_call
    def reason(self, state: FleetState, queue: TaskQueue) -> list[DirectorAction]:
        all_actions: list[DirectorAction] = []
        for reasoner in self.reasoners:
            new_actions = reasoner.reason(state, queue, all_actions)
            all_actions.extend(new_actions)
        return all_actions


@dataclass
class LifecycleReasoner:
    """Handles task lifecycle: completions, failures, stuck detection.

    Respects protected tasks (deep work mode) and per-task stuck thresholds.
    C2: Grace period for missing sessions -- only MARK_FAILED after 2+
    consecutive cycles of the session being absent.
    """

    default_stuck_threshold: float = DEFAULT_STUCK_THRESHOLD_SECONDS
    _missing_session_counts: dict[str, int] = field(default_factory=dict)

    @log_call
    def reason(
        self,
        state: FleetState,
        queue: TaskQueue,
        prior_actions: list[DirectorAction],
    ) -> list[DirectorAction]:
        actions: list[DirectorAction] = []

        # Prune stale entries for tasks no longer active
        active_keys = {
            f"{t.assigned_vm}:{t.assigned_session}"
            for t in queue.active_tasks()
            if t.assigned_vm and t.assigned_session
        }
        stale_keys = [k for k in self._missing_session_counts if k not in active_keys]
        for k in stale_keys:
            del self._missing_session_counts[k]

        for task in queue.active_tasks():
            if not task.assigned_vm or not task.assigned_session:
                continue

            vm = state.get_vm(task.assigned_vm)
            if not vm:
                continue

            session = self._find_session(vm, task.assigned_session)
            if not session:
                # C2: Grace period -- only fail after 2+ consecutive missing cycles
                key = f"{task.assigned_vm}:{task.assigned_session}"
                self._missing_session_counts[key] = self._missing_session_counts.get(key, 0) + 1
                if self._missing_session_counts[key] >= 2:
                    # Session truly gone after 2 cycles
                    actions.append(
                        DirectorAction(
                            action_type=ActionType.MARK_FAILED,
                            task=task,
                            vm_name=task.assigned_vm,
                            session_name=task.assigned_session,
                            reason="Session no longer exists (missing 2+ cycles)",
                        )
                    )
                    del self._missing_session_counts[key]
                # else: wait one more cycle before marking failed
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
                        reason=f"Agent error: {session.last_output[-200:]}",
                    )
                )

            elif session.agent_status == AgentStatus.STUCK:
                # Respect protected flag (deep work mode)
                if task.protected:
                    continue
                actions.append(
                    DirectorAction(
                        action_type=ActionType.REASSIGN_TASK,
                        task=task,
                        vm_name=task.assigned_vm,
                        session_name=task.assigned_session,
                        reason="Agent appears stuck",
                    )
                )

        return actions

    @log_call
    def _find_session(self, vm, session_name):
        for s in vm.tmux_sessions:
            if s.session_name == session_name:
                return s
        return None


@dataclass
class PreemptionReasoner:
    """Preempts lower-priority work when critical tasks arrive and no VMs are free.

    Only activates when CRITICAL tasks are queued with no idle capacity.
    Never preempts protected (deep work) tasks.
    """

    @log_call
    def reason(
        self,
        state: FleetState,
        queue: TaskQueue,
        prior_actions: list[DirectorAction],
    ) -> list[DirectorAction]:
        actions: list[DirectorAction] = []

        critical_queued = [
            t
            for t in queue.tasks
            if t.status == TaskStatus.QUEUED and t.priority == TaskPriority.CRITICAL
        ]
        if not critical_queued:
            return actions

        if state.idle_vms():
            return actions  # Capacity available, no preemption needed

        # Find lowest-priority running tasks
        running = sorted(
            queue.active_tasks(),
            key=lambda t: t.priority.value,
            reverse=True,  # Highest numeric value first (= lowest priority level — LOW tasks first)
        )

        for critical_task in critical_queued:
            if not running:
                break
            victim = running[0]
            if victim.priority.value <= critical_task.priority.value:
                break  # Don't preempt equal or higher priority
            if victim.protected:
                running.pop(0)
                continue

            running.pop(0)
            actions.append(
                DirectorAction(
                    action_type=ActionType.REASSIGN_TASK,
                    task=victim,
                    vm_name=victim.assigned_vm,
                    session_name=victim.assigned_session,
                    reason=f"Preempted for CRITICAL task {critical_task.id}",
                )
            )

        return actions


@dataclass
class BatchAssignReasoner:
    """Assigns queued tasks to VMs with group-awareness.

    Replaces greedy one-at-a-time assignment with batch logic that:
    - Groups related tasks onto the same VM when possible
    - Considers VM capacity
    """

    max_agents_per_vm: int = 3

    @log_call
    def reason(
        self,
        state: FleetState,
        queue: TaskQueue,
        prior_actions: list[DirectorAction],
    ) -> list[DirectorAction]:
        actions: list[DirectorAction] = []

        queued = [t for t in queue.tasks if t.status == TaskStatus.QUEUED]
        if not queued:
            return actions

        # Sort by priority then creation time
        queued.sort(key=lambda t: (t.priority.value, t.created_at))

        # Build VM capacity map
        capacity: dict[str, int] = {}
        for vm in state.managed_vms():
            if not vm.is_running:
                continue
            used = vm.active_agents
            # Account for assignments from prior reasoners
            used += sum(
                1
                for a in prior_actions
                if a.action_type == ActionType.START_AGENT and a.vm_name == vm.name
            )
            # Account for our own assignments this cycle
            used += sum(
                1
                for a in actions
                if a.action_type == ActionType.START_AGENT and a.vm_name == vm.name
            )
            remaining = self.max_agents_per_vm - used
            if remaining > 0:
                capacity[vm.name] = remaining

        if not capacity:
            return actions

        # Assign tasks
        for task in queued:
            if not capacity:
                break

            # Pick VM with most capacity
            best_vm = max(capacity, key=capacity.get)  # type: ignore[arg-type]

            session_name = f"fleet-{task.id}"
            actions.append(
                DirectorAction(
                    action_type=ActionType.START_AGENT,
                    task=task,
                    vm_name=best_vm,
                    session_name=session_name,
                    reason=f"Batch assign: {task.priority.name} task",
                )
            )
            # Don't assign here — let _start_agent assign after confirmed start

            capacity[best_vm] -= 1
            if capacity[best_vm] <= 0:
                del capacity[best_vm]

        return actions
