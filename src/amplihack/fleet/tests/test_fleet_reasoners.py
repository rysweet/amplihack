"""Tests for fleet_reasoners — composable director reasoning.

Testing pyramid:
- 60% Unit: LifecycleReasoner, PreemptionReasoner, BatchAssignReasoner decisions
- 30% Integration: ReasonerChain with multiple reasoners
- 10% E2E: full chain producing actions for realistic fleet state
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock

import pytest

from amplihack.fleet.fleet_director import ActionType, DirectorAction
from amplihack.fleet.fleet_state import AgentStatus, FleetState, TmuxSessionInfo, VMInfo
from amplihack.fleet.fleet_tasks import FleetTask, TaskPriority, TaskQueue, TaskStatus
from amplihack.fleet.fleet_reasoners import (
    BatchAssignReasoner,
    CoordinationReasoner,
    LifecycleReasoner,
    PreemptionReasoner,
    ReasonerChain,
)


# ────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────


def _make_vm(
    name: str,
    running: bool = True,
    sessions: list[TmuxSessionInfo] | None = None,
) -> VMInfo:
    """Build a VMInfo with optional tmux sessions."""
    return VMInfo(
        name=name,
        session_name=name,
        status="Running" if running else "Stopped",
        tmux_sessions=sessions or [],
    )


def _make_session(
    name: str,
    vm_name: str = "vm-01",
    status: AgentStatus = AgentStatus.RUNNING,
    last_output: str = "",
) -> TmuxSessionInfo:
    return TmuxSessionInfo(
        session_name=name,
        vm_name=vm_name,
        agent_status=status,
        last_output=last_output,
    )


def _make_task(
    task_id: str = "t1",
    status: TaskStatus = TaskStatus.RUNNING,
    priority: TaskPriority = TaskPriority.MEDIUM,
    vm: str | None = "vm-01",
    session: str | None = "sess-1",
    repo_url: str = "",
) -> FleetTask:
    task = FleetTask(
        id=task_id,
        prompt="Do something",
        priority=priority,
        status=status,
        repo_url=repo_url,
    )
    if vm:
        task.assigned_vm = vm
    if session:
        task.assigned_session = session
    return task


def _make_state(vms: list[VMInfo]) -> FleetState:
    state = FleetState(vms=vms)
    return state


def _make_queue(tasks: list[FleetTask]) -> TaskQueue:
    queue = TaskQueue()
    queue.tasks = tasks
    return queue


# ────────────────────────────────────────────
# UNIT TESTS (60%) — individual reasoners
# ────────────────────────────────────────────


class TestLifecycleReasoner:
    """Tests for task lifecycle detection."""

    def test_completed_session_marks_complete(self):
        session = _make_session("sess-1", status=AgentStatus.COMPLETED)
        vm = _make_vm("vm-01", sessions=[session])
        task = _make_task(vm="vm-01", session="sess-1")
        state = _make_state([vm])
        queue = _make_queue([task])

        reasoner = LifecycleReasoner()
        actions = reasoner.reason(state, queue, [])

        assert len(actions) == 1
        assert actions[0].action_type == ActionType.MARK_COMPLETE

    def test_error_session_marks_failed(self):
        session = _make_session("sess-1", status=AgentStatus.ERROR, last_output="OOM killed")
        vm = _make_vm("vm-01", sessions=[session])
        task = _make_task(vm="vm-01", session="sess-1")
        state = _make_state([vm])
        queue = _make_queue([task])

        reasoner = LifecycleReasoner()
        actions = reasoner.reason(state, queue, [])

        assert len(actions) == 1
        assert actions[0].action_type == ActionType.MARK_FAILED
        assert "OOM killed" in actions[0].reason

    def test_stuck_session_reassigns(self):
        session = _make_session("sess-1", status=AgentStatus.STUCK)
        vm = _make_vm("vm-01", sessions=[session])
        task = _make_task(vm="vm-01", session="sess-1")
        state = _make_state([vm])
        queue = _make_queue([task])

        reasoner = LifecycleReasoner()
        actions = reasoner.reason(state, queue, [])

        assert len(actions) == 1
        assert actions[0].action_type == ActionType.REASSIGN_TASK

    def test_protected_task_not_reassigned_when_stuck(self):
        session = _make_session("sess-1", status=AgentStatus.STUCK)
        vm = _make_vm("vm-01", sessions=[session])
        task = _make_task(vm="vm-01", session="sess-1")
        task.protected = True  # type: ignore[attr-defined]
        state = _make_state([vm])
        queue = _make_queue([task])

        reasoner = LifecycleReasoner()
        actions = reasoner.reason(state, queue, [])

        assert len(actions) == 0

    def test_missing_session_marks_failed(self):
        """C2: Missing session requires 2 consecutive cycles before MARK_FAILED."""
        vm = _make_vm("vm-01", sessions=[])  # no sessions
        task = _make_task(vm="vm-01", session="ghost-session")
        state = _make_state([vm])
        queue = _make_queue([task])

        reasoner = LifecycleReasoner()

        # First cycle: grace period, no actions
        actions = reasoner.reason(state, queue, [])
        assert len(actions) == 0

        # Second cycle: session still missing, now MARK_FAILED
        actions = reasoner.reason(state, queue, [])
        assert len(actions) == 1
        assert actions[0].action_type == ActionType.MARK_FAILED
        assert "no longer exists" in actions[0].reason

    def test_running_session_no_action(self):
        session = _make_session("sess-1", status=AgentStatus.RUNNING)
        vm = _make_vm("vm-01", sessions=[session])
        task = _make_task(vm="vm-01", session="sess-1")
        state = _make_state([vm])
        queue = _make_queue([task])

        reasoner = LifecycleReasoner()
        actions = reasoner.reason(state, queue, [])

        assert len(actions) == 0

    def test_task_without_vm_skipped(self):
        task = _make_task(vm=None, session=None)
        state = _make_state([])
        queue = _make_queue([task])

        reasoner = LifecycleReasoner()
        actions = reasoner.reason(state, queue, [])
        assert len(actions) == 0

    def test_task_with_missing_vm_skipped(self):
        task = _make_task(vm="nonexistent-vm", session="sess-1")
        state = _make_state([])
        queue = _make_queue([task])

        reasoner = LifecycleReasoner()
        actions = reasoner.reason(state, queue, [])
        assert len(actions) == 0


class TestPreemptionReasoner:
    """Tests for priority preemption logic."""

    def test_no_preemption_when_no_critical_tasks(self):
        task = _make_task(priority=TaskPriority.HIGH, status=TaskStatus.RUNNING)
        state = _make_state([_make_vm("vm-01")])
        queue = _make_queue([task])

        reasoner = PreemptionReasoner()
        actions = reasoner.reason(state, queue, [])
        assert len(actions) == 0

    def test_no_preemption_when_idle_vms_available(self):
        # One idle VM means capacity exists
        critical = _make_task(task_id="c1", priority=TaskPriority.CRITICAL, status=TaskStatus.QUEUED, vm=None, session=None)
        running = _make_task(task_id="r1", priority=TaskPriority.LOW, status=TaskStatus.RUNNING)
        idle_vm = _make_vm("vm-02", running=True, sessions=[])
        busy_vm = _make_vm("vm-01", running=True, sessions=[
            _make_session("sess-1", status=AgentStatus.RUNNING),
        ])
        state = _make_state([busy_vm, idle_vm])

        queue = _make_queue([critical, running])

        reasoner = PreemptionReasoner()
        actions = reasoner.reason(state, queue, [])
        assert len(actions) == 0

    def test_preempts_low_priority_for_critical(self):
        critical = _make_task(task_id="c1", priority=TaskPriority.CRITICAL, status=TaskStatus.QUEUED, vm=None, session=None)
        low = _make_task(task_id="low1", priority=TaskPriority.LOW, status=TaskStatus.RUNNING, vm="vm-01", session="sess-1")
        state = _make_state([])  # No idle VMs (empty list)

        queue = _make_queue([critical, low])

        reasoner = PreemptionReasoner()
        actions = reasoner.reason(state, queue, [])

        assert len(actions) == 1
        assert actions[0].action_type == ActionType.REASSIGN_TASK
        assert actions[0].task.id == "low1"

    def test_does_not_preempt_equal_priority(self):
        critical_queued = _make_task(task_id="c1", priority=TaskPriority.CRITICAL, status=TaskStatus.QUEUED, vm=None, session=None)
        critical_running = _make_task(task_id="c2", priority=TaskPriority.CRITICAL, status=TaskStatus.RUNNING, vm="vm-01", session="s")
        state = _make_state([])

        queue = _make_queue([critical_queued, critical_running])

        reasoner = PreemptionReasoner()
        actions = reasoner.reason(state, queue, [])
        assert len(actions) == 0

    def test_does_not_preempt_protected_tasks(self):
        critical = _make_task(task_id="c1", priority=TaskPriority.CRITICAL, status=TaskStatus.QUEUED, vm=None, session=None)
        protected = _make_task(task_id="p1", priority=TaskPriority.LOW, status=TaskStatus.RUNNING)
        protected.protected = True  # type: ignore[attr-defined]
        state = _make_state([])

        queue = _make_queue([critical, protected])

        reasoner = PreemptionReasoner()
        actions = reasoner.reason(state, queue, [])
        # Protected task skipped, no other victims
        assert len(actions) == 0


class TestBatchAssignReasoner:
    """Tests for batch task assignment."""

    def test_assigns_queued_task_to_idle_vm(self):
        task = _make_task(task_id="t1", status=TaskStatus.QUEUED, vm=None, session=None)
        vm = _make_vm("vm-01", sessions=[])
        state = _make_state([vm])
        queue = _make_queue([task])

        reasoner = BatchAssignReasoner(max_agents_per_vm=3)
        actions = reasoner.reason(state, queue, [])

        assert len(actions) == 1
        assert actions[0].action_type == ActionType.START_AGENT
        assert actions[0].vm_name == "vm-01"

    def test_no_assignment_when_no_capacity(self):
        # All VMs are stopped
        task = _make_task(task_id="t1", status=TaskStatus.QUEUED, vm=None, session=None)
        vm = _make_vm("vm-01", running=False)
        state = _make_state([vm])
        queue = _make_queue([task])

        reasoner = BatchAssignReasoner()
        actions = reasoner.reason(state, queue, [])
        assert len(actions) == 0

    def test_no_assignment_when_no_queued_tasks(self):
        vm = _make_vm("vm-01")
        state = _make_state([vm])
        queue = _make_queue([])

        reasoner = BatchAssignReasoner()
        actions = reasoner.reason(state, queue, [])
        assert len(actions) == 0

    def test_respects_max_agents_per_vm(self):
        # VM already has 3 agents running (max)
        sessions = [
            _make_session(f"s{i}", status=AgentStatus.RUNNING) for i in range(3)
        ]
        vm = _make_vm("vm-01", sessions=sessions)
        task = _make_task(task_id="t1", status=TaskStatus.QUEUED, vm=None, session=None)
        state = _make_state([vm])
        queue = _make_queue([task])

        reasoner = BatchAssignReasoner(max_agents_per_vm=3)
        actions = reasoner.reason(state, queue, [])
        assert len(actions) == 0

    def test_assigns_to_vm_with_most_capacity(self):
        # vm-01 has 2 agents, vm-02 has 0
        sessions_01 = [_make_session(f"s{i}", status=AgentStatus.RUNNING) for i in range(2)]
        vm1 = _make_vm("vm-01", sessions=sessions_01)
        vm2 = _make_vm("vm-02", sessions=[])
        task = _make_task(task_id="t1", status=TaskStatus.QUEUED, vm=None, session=None)
        state = _make_state([vm1, vm2])
        queue = _make_queue([task])

        reasoner = BatchAssignReasoner(max_agents_per_vm=3)
        actions = reasoner.reason(state, queue, [])

        assert len(actions) == 1
        assert actions[0].vm_name == "vm-02"

    def test_priority_ordering(self):
        high = _make_task(task_id="high", status=TaskStatus.QUEUED, priority=TaskPriority.HIGH, vm=None, session=None)
        low = _make_task(task_id="low", status=TaskStatus.QUEUED, priority=TaskPriority.LOW, vm=None, session=None)
        vm = _make_vm("vm-01")
        state = _make_state([vm])
        # Insert low first, high second — reasoner should sort
        queue = _make_queue([low, high])

        reasoner = BatchAssignReasoner(max_agents_per_vm=1)
        actions = reasoner.reason(state, queue, [])

        # Only 1 slot, should assign the higher priority task
        assert len(actions) == 1
        assert actions[0].task.id == "high"

    def test_assigns_queued_tasks(self):
        """Queued tasks get assigned when capacity is available."""
        dep = _make_task(task_id="dep", status=TaskStatus.RUNNING, vm="vm-01", session="s1")
        queued = _make_task(task_id="queued", status=TaskStatus.QUEUED, vm=None, session=None)
        vm = _make_vm("vm-02")
        state = _make_state([vm])
        queue = _make_queue([dep, queued])

        reasoner = BatchAssignReasoner(max_agents_per_vm=3)
        actions = reasoner.reason(state, queue, [])

        # queued task should be assigned since vm-02 has capacity
        assert any(a.task.id == "queued" for a in actions)


# ────────────────────────────────────────────
# INTEGRATION TESTS (30%) — ReasonerChain
# ────────────────────────────────────────────


class TestReasonerChain:
    def test_chain_accumulates_actions(self):
        # Lifecycle detects completion, then batch assigns a queued task
        completed_session = _make_session("sess-1", status=AgentStatus.COMPLETED)
        vm = _make_vm("vm-01", sessions=[completed_session])

        running_task = _make_task(task_id="done", status=TaskStatus.RUNNING, vm="vm-01", session="sess-1")
        queued_task = _make_task(task_id="next", status=TaskStatus.QUEUED, vm=None, session=None)

        state = _make_state([vm])
        queue = _make_queue([running_task, queued_task])

        chain = ReasonerChain(
            reasoners=[LifecycleReasoner(), BatchAssignReasoner(max_agents_per_vm=3)]
        )
        actions = chain.reason(state, queue)

        action_types = [a.action_type for a in actions]
        assert ActionType.MARK_COMPLETE in action_types
        assert ActionType.START_AGENT in action_types

    def test_empty_chain_no_actions(self):
        state = _make_state([])
        queue = _make_queue([])
        chain = ReasonerChain(reasoners=[])
        actions = chain.reason(state, queue)
        assert actions == []

    def test_prior_actions_passed_to_later_reasoners(self):
        """BatchAssignReasoner accounts for START_AGENT from prior reasoners."""
        vm = _make_vm("vm-01", sessions=[])
        t1 = _make_task(task_id="t1", status=TaskStatus.QUEUED, vm=None, session=None)
        t2 = _make_task(task_id="t2", status=TaskStatus.QUEUED, vm=None, session=None)
        state = _make_state([vm])
        queue = _make_queue([t1, t2])

        # Limit to 1 agent per VM: only 1 assignment should happen
        chain = ReasonerChain(
            reasoners=[BatchAssignReasoner(max_agents_per_vm=1)]
        )
        actions = chain.reason(state, queue)
        start_actions = [a for a in actions if a.action_type == ActionType.START_AGENT]
        assert len(start_actions) == 1


# ────────────────────────────────────────────
# E2E TESTS (10%) — realistic fleet scenario
# ────────────────────────────────────────────


class TestReasonerChainFullScenario:
    def test_realistic_fleet_scenario(self):
        """Full chain with lifecycle, preemption, and batch assignment."""
        # vm-01: has a completed task
        completed_sess = _make_session("sess-done", vm_name="vm-01", status=AgentStatus.COMPLETED)
        vm1 = _make_vm("vm-01", sessions=[completed_sess])

        # vm-02: running a low-priority task
        running_sess = _make_session("sess-low", vm_name="vm-02", status=AgentStatus.RUNNING)
        vm2 = _make_vm("vm-02", sessions=[running_sess])

        done_task = _make_task(task_id="done", status=TaskStatus.RUNNING, vm="vm-01", session="sess-done")
        low_task = _make_task(task_id="low", status=TaskStatus.RUNNING, priority=TaskPriority.LOW, vm="vm-02", session="sess-low")
        queued = _make_task(task_id="q1", status=TaskStatus.QUEUED, priority=TaskPriority.MEDIUM, vm=None, session=None)

        state = _make_state([vm1, vm2])
        queue = _make_queue([done_task, low_task, queued])

        chain = ReasonerChain(
            reasoners=[
                LifecycleReasoner(),
                PreemptionReasoner(),
                BatchAssignReasoner(max_agents_per_vm=3),
            ]
        )
        actions = chain.reason(state, queue)

        # Should detect completion of done_task
        complete_actions = [a for a in actions if a.action_type == ActionType.MARK_COMPLETE]
        assert len(complete_actions) == 1
        assert complete_actions[0].task.id == "done"

        # Should assign queued task (vm-01 has capacity after completion detected)
        start_actions = [a for a in actions if a.action_type == ActionType.START_AGENT]
        assert len(start_actions) >= 1
