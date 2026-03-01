"""Composable reasoning functions for the fleet director.

Each reasoner takes fleet state + task queue and returns DirectorActions.
Reasoners run in priority order as a chain. This replaces the monolithic
`reason()` method with pluggable, testable decision functions.

Four built-in reasoners:
1. LifecycleReasoner: Completions, failures, stuck detection (with protected tasks)
2. PreemptionReasoner: Emergency priority escalation
3. CoordinationReasoner: Shared context for investigation tasks
4. BatchAssignReasoner: Context-aware batch assignment (replaces greedy 1-at-a-time)

Adding a new reasoner: implement the 3-arg reason() method and append to the chain.

Public API:
    ReasonerChain: Ordered chain of reasoners
    LifecycleReasoner: Task lifecycle management
    PreemptionReasoner: Priority preemption for emergencies
    CoordinationReasoner: Inter-agent context sharing
    BatchAssignReasoner: Smart batch task assignment
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol

from amplihack.fleet.fleet_director import ActionType, DirectorAction
from amplihack.fleet.fleet_state import AgentStatus, FleetState
from amplihack.fleet.fleet_tasks import FleetTask, TaskPriority, TaskQueue, TaskStatus

__all__ = [
    "ReasonerChain",
    "LifecycleReasoner",
    "PreemptionReasoner",
    "CoordinationReasoner",
    "BatchAssignReasoner",
]


class Reasoner(Protocol):
    """A single reasoning function that proposes actions."""

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

    default_stuck_threshold: float = 300.0
    _missing_session_counts: dict[str, int] = field(default_factory=dict)

    def reason(
        self,
        state: FleetState,
        queue: TaskQueue,
        prior_actions: list[DirectorAction],
    ) -> list[DirectorAction]:
        actions: list[DirectorAction] = []

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
                    actions.append(DirectorAction(
                        action_type=ActionType.MARK_FAILED,
                        task=task,
                        vm_name=task.assigned_vm,
                        session_name=task.assigned_session,
                        reason="Session no longer exists (missing 2+ cycles)",
                    ))
                    del self._missing_session_counts[key]
                # else: wait one more cycle before marking failed
                continue

            if session.agent_status == AgentStatus.COMPLETED:
                actions.append(DirectorAction(
                    action_type=ActionType.MARK_COMPLETE,
                    task=task,
                    vm_name=task.assigned_vm,
                    session_name=task.assigned_session,
                    reason="Agent completed successfully",
                ))

            elif session.agent_status == AgentStatus.ERROR:
                actions.append(DirectorAction(
                    action_type=ActionType.MARK_FAILED,
                    task=task,
                    vm_name=task.assigned_vm,
                    session_name=task.assigned_session,
                    reason=f"Agent error: {session.last_output[-200:]}",
                ))

            elif session.agent_status == AgentStatus.STUCK:
                # Respect protected flag (deep work mode)
                if task.protected:
                    continue
                actions.append(DirectorAction(
                    action_type=ActionType.REASSIGN_TASK,
                    task=task,
                    vm_name=task.assigned_vm,
                    session_name=task.assigned_session,
                    reason="Agent appears stuck",
                ))

        return actions

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

    def reason(
        self,
        state: FleetState,
        queue: TaskQueue,
        prior_actions: list[DirectorAction],
    ) -> list[DirectorAction]:
        actions: list[DirectorAction] = []

        critical_queued = [
            t for t in queue.tasks
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
            reverse=True,  # Lowest priority first
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
            actions.append(DirectorAction(
                action_type=ActionType.REASSIGN_TASK,
                task=victim,
                vm_name=victim.assigned_vm,
                session_name=victim.assigned_session,
                reason=f"Preempted for CRITICAL task {critical_task.id}",
            ))

        return actions


@dataclass
class CoordinationReasoner:
    """Manages shared context for agents working on related tasks.

    Writes coordination files so agents investigating the same codebase
    can see what others are working on and avoid duplication.

    Note: Coordination files are designed to be read by agents via shared
    NFS mount. This is not dead code -- it is infrastructure for multi-agent
    awareness across VMs.
    """

    coordination_dir: Path = field(
        default_factory=lambda: Path.home() / ".amplihack" / "fleet" / "coordination"
    )

    def reason(
        self,
        state: FleetState,
        queue: TaskQueue,
        prior_actions: list[DirectorAction],
    ) -> list[DirectorAction]:
        self.coordination_dir.mkdir(parents=True, exist_ok=True)

        # Group active tasks by repo (lightweight context sharing)
        repo_groups: dict[str, list[FleetTask]] = {}
        for task in queue.active_tasks():
            if task.repo_url:
                repo_groups.setdefault(task.repo_url, []).append(task)

        # Write coordination files for repos with multiple active agents
        for repo_url, tasks in repo_groups.items():
            if len(tasks) < 2:
                continue

            safe_key = repo_url.split("/")[-1].replace(".git", "")
            coord_file = self.coordination_dir / f"{safe_key}.json"
            coord_data = {
                "repo": repo_url,
                "active_agents": [
                    {
                        "task_id": t.id,
                        "prompt": t.prompt[:200],
                        "vm": t.assigned_vm,
                        "session": t.assigned_session,
                    }
                    for t in tasks
                ],
                "updated_at": datetime.now().isoformat(),
            }
            coord_file.write_text(json.dumps(coord_data, indent=2))

        return []  # Side-effect only — no director actions


@dataclass
class BatchAssignReasoner:
    """Assigns queued tasks to VMs with group-awareness and dependency checking.

    Replaces greedy one-at-a-time assignment with batch logic that:
    - Groups related tasks onto the same VM when possible
    - Respects task dependencies (depends_on)
    - Considers VM capacity
    """

    max_agents_per_vm: int = 3

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

        # Check dependency satisfaction
        completed_ids = {t.id for t in queue.tasks if t.status == TaskStatus.COMPLETED}
        depends_on_fn = lambda t: getattr(t, "depends_on", [])
        ready = [
            t for t in queued
            if all(dep in completed_ids for dep in depends_on_fn(t))
        ]

        if not ready:
            return actions

        # Sort by priority then creation time
        ready.sort(key=lambda t: (t.priority.value, t.created_at))

        # Build VM capacity map
        capacity: dict[str, int] = {}
        for vm in state.managed_vms():
            if not vm.is_running:
                continue
            used = vm.active_agents
            # Account for assignments from prior reasoners
            used += sum(
                1 for a in prior_actions
                if a.action_type == ActionType.START_AGENT and a.vm_name == vm.name
            )
            # Account for our own assignments this cycle
            used += sum(
                1 for a in actions
                if a.action_type == ActionType.START_AGENT and a.vm_name == vm.name
            )
            remaining = self.max_agents_per_vm - used
            if remaining > 0:
                capacity[vm.name] = remaining

        if not capacity:
            return actions

        # Assign tasks
        for task in ready:
            if not capacity:
                break

            # Pick VM with most capacity
            best_vm = max(capacity, key=capacity.get)  # type: ignore[arg-type]

            session_name = f"fleet-{task.id}"
            actions.append(DirectorAction(
                action_type=ActionType.START_AGENT,
                task=task,
                vm_name=best_vm,
                session_name=session_name,
                reason=f"Batch assign: {task.priority.name} task",
            ))
            task.assign(best_vm, session_name)

            capacity[best_vm] -= 1
            if capacity[best_vm] <= 0:
                del capacity[best_vm]

        return actions
