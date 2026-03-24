"""Tests for fleet director — PERCEIVE→REASON→ACT→LEARN loop.

Mocks all external dependencies (azlin, subprocess).
"""

from unittest.mock import MagicMock, patch

from amplihack.fleet.fleet_admiral import (
    ActionType,
    DirectorAction,
)
from amplihack.fleet.fleet_admiral import (
    FleetAdmiral as FleetDirector,
)
from amplihack.fleet.fleet_state import AgentStatus, FleetState, TmuxSessionInfo, VMInfo
from amplihack.fleet.fleet_tasks import FleetTask, TaskPriority, TaskQueue, TaskStatus


class TestFleetDirectorReason:
    """Unit tests for director reasoning (decision-making)."""

    def _make_director(self, tasks=None):
        queue = TaskQueue()
        if tasks:
            for t in tasks:
                queue.add(t)
        return FleetDirector(task_queue=queue)

    def _make_state(self, vms):
        state = FleetState()
        state.vms = vms
        return state

    def test_assign_task_to_idle_vm(self):
        task = FleetTask(prompt="Build feature", priority=TaskPriority.HIGH)
        director = self._make_director(tasks=[task])

        vm = VMInfo(
            name="fleet-exp-1",
            session_name="fleet-exp-1",
            status="Running",
            region="westus3",
            tmux_sessions=[],
        )
        state = self._make_state([vm])

        actions = director.reason(state)
        assert len(actions) == 1
        assert actions[0].action_type == ActionType.START_AGENT
        assert actions[0].task.id == task.id

    def test_no_action_when_no_tasks(self):
        director = self._make_director(tasks=[])
        vm = VMInfo(name="vm-1", session_name="vm-1", status="Running")
        state = self._make_state([vm])

        actions = director.reason(state)
        assert len(actions) == 0

    def test_no_action_when_no_running_vms(self):
        task = FleetTask(prompt="Task")
        director = self._make_director(tasks=[task])

        vm = VMInfo(name="vm-1", session_name="vm-1", status="Stopped")
        state = self._make_state([vm])

        actions = director.reason(state)
        assert len(actions) == 0

    def test_detect_completed_agent(self):
        task = FleetTask(prompt="Test")
        task.assign("vm-1", "sess-1")
        task.start()

        director = self._make_director(tasks=[task])

        vm = VMInfo(
            name="vm-1",
            session_name="vm-1",
            status="Running",
            tmux_sessions=[
                TmuxSessionInfo(
                    session_name="sess-1",
                    vm_name="vm-1",
                    agent_status=AgentStatus.COMPLETED,
                )
            ],
        )
        state = self._make_state([vm])

        actions = director.reason(state)
        assert any(a.action_type == ActionType.MARK_COMPLETE for a in actions)

    def test_detect_stuck_agent(self):
        task = FleetTask(prompt="Test")
        task.assign("vm-1", "stuck-sess")
        task.start()

        director = self._make_director(tasks=[task])

        vm = VMInfo(
            name="vm-1",
            session_name="vm-1",
            status="Running",
            tmux_sessions=[
                TmuxSessionInfo(
                    session_name="stuck-sess",
                    vm_name="vm-1",
                    agent_status=AgentStatus.STUCK,
                )
            ],
        )
        state = self._make_state([vm])

        actions = director.reason(state)
        assert any(a.action_type == ActionType.REASSIGN_TASK for a in actions)

    def test_detect_errored_agent(self):
        task = FleetTask(prompt="Test")
        task.assign("vm-1", "err-sess")
        task.start()

        director = self._make_director(tasks=[task])

        vm = VMInfo(
            name="vm-1",
            session_name="vm-1",
            status="Running",
            tmux_sessions=[
                TmuxSessionInfo(
                    session_name="err-sess",
                    vm_name="vm-1",
                    agent_status=AgentStatus.ERROR,
                    last_output="Authentication failed",
                )
            ],
        )
        state = self._make_state([vm])

        actions = director.reason(state)
        assert any(a.action_type == ActionType.MARK_FAILED for a in actions)

    def test_detect_missing_session(self):
        """If assigned session no longer exists for 2+ cycles, mark failed (C2 grace period)."""
        task = FleetTask(prompt="Test")
        task.assign("vm-1", "gone-sess")
        task.start()

        director = self._make_director(tasks=[task])

        vm = VMInfo(
            name="vm-1",
            session_name="vm-1",
            status="Running",
            tmux_sessions=[],  # Session gone
        )
        state = self._make_state([vm])

        # First cycle: grace period, no MARK_FAILED yet
        actions = director.reason(state)
        assert not any(a.action_type == ActionType.MARK_FAILED for a in actions)

        # Second cycle: session still missing, now MARK_FAILED
        actions = director.reason(state)
        assert any(a.action_type == ActionType.MARK_FAILED for a in actions)

    def test_respects_max_agents_per_vm(self):
        tasks = [FleetTask(prompt=f"Task {i}", priority=TaskPriority.HIGH) for i in range(5)]
        queue = TaskQueue()
        for t in tasks:
            queue.add(t)
        director = FleetDirector(task_queue=queue, max_agents_per_vm=2)

        vm = VMInfo(
            name="vm-1",
            session_name="vm-1",
            status="Running",
            tmux_sessions=[
                TmuxSessionInfo(
                    session_name="existing-1",
                    vm_name="vm-1",
                    agent_status=AgentStatus.RUNNING,
                ),
                TmuxSessionInfo(
                    session_name="existing-2",
                    vm_name="vm-1",
                    agent_status=AgentStatus.RUNNING,
                ),
            ],
        )
        state = self._make_state([vm])

        actions = director.reason(state)
        # Should not assign — VM at capacity
        start_actions = [a for a in actions if a.action_type == ActionType.START_AGENT]
        assert len(start_actions) == 0

    def test_excludes_excluded_vms(self):
        task = FleetTask(prompt="Task")
        director = self._make_director(tasks=[task])
        director.exclude_vms("user-vm-1")

        vms = [
            VMInfo(name="user-vm-1", session_name="user-vm-1", status="Running"),
        ]
        state = self._make_state(vms)
        state.exclude_vms("user-vm-1")

        actions = director.reason(state)
        # Should not assign to excluded VM
        start_actions = [a for a in actions if a.action_type == ActionType.START_AGENT]
        assert len(start_actions) == 0


class TestFleetDirectorAct:
    """Tests for action execution with mocked subprocess."""

    @patch("amplihack.fleet._admiral_actions.subprocess.run")
    def test_start_agent_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        queue = TaskQueue()
        task = queue.add_task(prompt="Build feature")
        task.assign("vm-1", "fleet-001")

        director = FleetDirector(task_queue=queue)
        action = DirectorAction(
            action_type=ActionType.START_AGENT,
            task=task,
            vm_name="vm-1",
            session_name="fleet-001",
        )

        result = director._execute_action(action)
        assert "started" in result.lower()
        assert task.status == TaskStatus.RUNNING

    @patch("amplihack.fleet._admiral_actions.subprocess.run")
    def test_start_agent_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Connection refused")

        queue = TaskQueue()
        task = queue.add_task(prompt="Test")
        task.assign("vm-1", "sess-1")

        director = FleetDirector(task_queue=queue)
        action = DirectorAction(
            action_type=ActionType.START_AGENT,
            task=task,
            vm_name="vm-1",
            session_name="sess-1",
        )

        result = director._execute_action(action)
        assert "ERROR" in result

    def test_mark_complete(self):
        queue = TaskQueue()
        task = queue.add_task(prompt="Test")
        task.start()

        director = FleetDirector(task_queue=queue)
        action = DirectorAction(action_type=ActionType.MARK_COMPLETE, task=task)

        director._execute_action(action)
        assert task.status == TaskStatus.COMPLETED

    def test_mark_failed(self):
        queue = TaskQueue()
        task = queue.add_task(prompt="Test")
        task.start()

        director = FleetDirector(task_queue=queue)
        action = DirectorAction(
            action_type=ActionType.MARK_FAILED,
            task=task,
            reason="Timeout",
        )

        director._execute_action(action)
        assert task.status == TaskStatus.FAILED

    @patch("amplihack.fleet._admiral_actions.subprocess.run")
    def test_reassign_stuck_task(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        queue = TaskQueue()
        task = queue.add_task(prompt="Stuck task")
        task.assign("vm-1", "stuck-sess")
        task.start()

        director = FleetDirector(task_queue=queue)
        action = DirectorAction(
            action_type=ActionType.REASSIGN_TASK,
            task=task,
            vm_name="vm-1",
            session_name="stuck-sess",
            reason="Stuck",
        )

        director._execute_action(action)
        assert task.status == TaskStatus.QUEUED
        assert task.assigned_vm is None


class TestFleetDirectorE2E:
    """End-to-end test of one director cycle."""

    @patch("amplihack.fleet._admiral_actions.subprocess.run")
    @patch.object(FleetState, "refresh")
    def test_single_cycle(self, mock_refresh, mock_run):
        """Complete PERCEIVE→REASON→ACT cycle with mocked state."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        # Setup fleet state
        vm = VMInfo(
            name="fleet-exp-1",
            session_name="fleet-exp-1",
            status="Running",
            region="westus3",
            tmux_sessions=[],
        )

        queue = TaskQueue()
        queue.add_task(prompt="Build authentication", priority=TaskPriority.HIGH)

        director = FleetDirector(task_queue=queue)
        director._fleet_state.vms = [vm]

        # Mock refresh to keep our state
        def keep_state():
            director._fleet_state.vms = [vm]
            return director._fleet_state

        mock_refresh.side_effect = keep_state

        # Run one cycle
        actions = director.run_once()

        # Should have started an agent
        assert len(actions) >= 1
        assert any(a.action_type == ActionType.START_AGENT for a in actions)
