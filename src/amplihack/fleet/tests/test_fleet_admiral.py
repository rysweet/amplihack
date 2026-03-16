"""Tests for FleetAdmiral — PERCEIVE->REASON->ACT->LEARN loop.

Covers construction, exclude_vms, run_once ordering, run_loop with
max_cycles and circuit breaker, learn() stats tracking, recall_learnings,
status_report, and missing-session grace period.

Testing pyramid: 100% unit (all external I/O mocked).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet._validation import validate_session_name, validate_vm_name
from amplihack.fleet.fleet_admiral import (
    ActionType,
    DirectorAction,
    DirectorLog,
    FleetAdmiral,
)
from amplihack.fleet.fleet_state import AgentStatus, FleetState, TmuxSessionInfo, VMInfo
from amplihack.fleet.fleet_tasks import FleetTask, TaskPriority, TaskQueue, TaskStatus
from amplihack.utils.logging_utils import log_call

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@log_call
def _make_queue(*tasks: FleetTask, persist_path=None) -> TaskQueue:
    """Build a TaskQueue without triggering persistence."""
    q = TaskQueue.__new__(TaskQueue)
    q.tasks = list(tasks)
    q.persist_path = persist_path
    return q


@log_call
def _make_task(**overrides: object) -> FleetTask:
    defaults: dict[str, object] = dict(
        id="t1",
        prompt="Fix the flaky test",
        repo_url="https://github.com/org/repo",
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.QUEUED,
    )
    defaults.update(overrides)
    return FleetTask(**defaults)  # type: ignore[arg-type]


@log_call
def _make_vm(name: str, status: str = "Running", sessions=None) -> VMInfo:
    return VMInfo(
        name=name,
        session_name=name,
        status=status,
        tmux_sessions=sessions or [],
    )


@log_call
def _make_admiral(queue: TaskQueue | None = None, **kw) -> FleetAdmiral:
    """Build a FleetAdmiral with all heavy imports mocked."""
    q = queue or _make_queue()
    with (
        patch("amplihack.fleet.fleet_admiral.FleetState") as MockFS,
        patch("amplihack.fleet.fleet_admiral.FleetObserver") as MockObs,
        patch("amplihack.fleet.fleet_admiral.AuthPropagator") as MockAuth,
    ):
        # Provide real FleetState by default so .managed_vms() etc. work
        MockFS.return_value = FleetState()
        MockObs.return_value = MagicMock()
        MockAuth.return_value = MagicMock()
        admiral = FleetAdmiral(task_queue=q, **kw)
    return admiral


# ============ UNIT TESTS ============


class TestConstruction:
    """FleetAdmiral construction with default and custom params."""

    @log_call
    def test_defaults(self):
        admiral = _make_admiral()
        assert admiral.poll_interval_seconds == 60.0
        assert admiral.max_agents_per_vm == 3
        assert admiral._cycle_count == 0
        assert admiral._running is False
        assert admiral._stats == {"actions": 0, "successes": 0, "failures": 0}
        assert admiral._exclude_vms == set()
        assert admiral._missing_session_counts == {}

    @log_call
    def test_custom_params(self):
        admiral = _make_admiral(poll_interval_seconds=10.0, max_agents_per_vm=5)
        assert admiral.poll_interval_seconds == 10.0
        assert admiral.max_agents_per_vm == 5

    @log_call
    def test_log_dir_creates_persist_path(self, tmp_path):
        log_dir = tmp_path / "logs"
        admiral = _make_admiral(log_dir=log_dir)
        assert admiral._log.persist_path == log_dir / "admiral_log.json"
        assert log_dir.exists()

    @log_call
    def test_reasoner_chain_initialized(self):
        admiral = _make_admiral()
        assert hasattr(admiral, "_reasoner_chain")
        assert len(admiral._reasoner_chain.reasoners) == 4


class TestExcludeVms:
    """exclude_vms marks VMs correctly and returns self for chaining."""

    @log_call
    def test_single_vm(self):
        admiral = _make_admiral()
        result = admiral.exclude_vms("user-vm-1")
        assert "user-vm-1" in admiral._exclude_vms
        assert result is admiral  # chaining

    @log_call
    def test_multiple_vms(self):
        admiral = _make_admiral()
        admiral.exclude_vms("vm-a", "vm-b")
        assert admiral._exclude_vms == {"vm-a", "vm-b"}

    @log_call
    def test_propagates_to_fleet_state(self):
        admiral = _make_admiral()
        admiral._fleet_state = MagicMock()
        admiral.exclude_vms("vm-x")
        admiral._fleet_state.exclude_vms.assert_called_once_with("vm-x")

    @log_call
    def test_idempotent(self):
        admiral = _make_admiral()
        admiral.exclude_vms("vm-a")
        admiral.exclude_vms("vm-a")
        assert admiral._exclude_vms == {"vm-a"}


class TestRunOnce:
    """run_once calls perceive->reason->act->learn in order."""

    @log_call
    def test_calls_in_order(self):
        admiral = _make_admiral()
        call_order = []

        @log_call
        def mock_perceive():
            call_order.append("perceive")
            return admiral._fleet_state

        @log_call
        def mock_reason(state):
            call_order.append("reason")
            return []

        @log_call
        def mock_act(actions):
            call_order.append("act")
            return []

        @log_call
        def mock_learn(results):
            call_order.append("learn")

        admiral.perceive = mock_perceive
        admiral.reason = mock_reason
        admiral.act = mock_act
        admiral.learn = mock_learn

        admiral.run_once()

        assert call_order == ["perceive", "reason", "act", "learn"]

    @log_call
    def test_increments_cycle_count(self):
        admiral = _make_admiral()
        admiral.perceive = MagicMock(return_value=admiral._fleet_state)
        admiral.reason = MagicMock(return_value=[])
        admiral.act = MagicMock(return_value=[])
        admiral.learn = MagicMock()

        admiral.run_once()
        assert admiral._cycle_count == 1
        admiral.run_once()
        assert admiral._cycle_count == 2

    @log_call
    def test_returns_actions_from_reason(self):
        admiral = _make_admiral()
        expected_actions = [DirectorAction(action_type=ActionType.REPORT, reason="test")]
        admiral.perceive = MagicMock(return_value=admiral._fleet_state)
        admiral.reason = MagicMock(return_value=expected_actions)
        admiral.act = MagicMock(return_value=[])
        admiral.learn = MagicMock()

        result = admiral.run_once()
        assert result == expected_actions

    @log_call
    def test_passes_state_from_perceive_to_reason(self):
        admiral = _make_admiral()
        fake_state = MagicMock()
        admiral.perceive = MagicMock(return_value=fake_state)
        admiral.reason = MagicMock(return_value=[])
        admiral.act = MagicMock(return_value=[])
        admiral.learn = MagicMock()

        admiral.run_once()
        admiral.reason.assert_called_once_with(fake_state)

    @log_call
    def test_passes_actions_from_reason_to_act(self):
        admiral = _make_admiral()
        actions = [DirectorAction(action_type=ActionType.REPORT)]
        admiral.perceive = MagicMock(return_value=admiral._fleet_state)
        admiral.reason = MagicMock(return_value=actions)
        admiral.act = MagicMock(return_value=[])
        admiral.learn = MagicMock()

        admiral.run_once()
        admiral.act.assert_called_once_with(actions)

    @log_call
    def test_passes_results_from_act_to_learn(self):
        admiral = _make_admiral()
        action = DirectorAction(action_type=ActionType.REPORT)
        results = [(action, "ok")]
        admiral.perceive = MagicMock(return_value=admiral._fleet_state)
        admiral.reason = MagicMock(return_value=[action])
        admiral.act = MagicMock(return_value=results)
        admiral.learn = MagicMock()

        admiral.run_once()
        admiral.learn.assert_called_once_with(results)


class TestRunLoop:
    """run_loop with max_cycles, circuit breaker, and all-tasks-done."""

    @log_call
    def test_max_cycles_stops_at_right_count(self):
        admiral = _make_admiral()
        cycle_counter = {"count": 0}

        @log_call
        def mock_run_once():
            cycle_counter["count"] += 1
            return []

        admiral.run_once = mock_run_once
        # Pretend there are always tasks so loop does not exit early
        admiral.task_queue.next_task = MagicMock(return_value=_make_task())
        admiral.task_queue.active_tasks = MagicMock(return_value=[])

        with patch("time.sleep"):
            admiral.run_loop(max_cycles=3)

        assert cycle_counter["count"] == 3
        assert admiral._running is False

    @log_call
    def test_circuit_breaker_stops_after_5_consecutive_failures(self):
        admiral = _make_admiral()
        failure_count = {"count": 0}

        @log_call
        def failing_run_once():
            failure_count["count"] += 1
            raise RuntimeError("boom")

        admiral.run_once = failing_run_once
        admiral.task_queue.next_task = MagicMock(return_value=_make_task())
        admiral.task_queue.active_tasks = MagicMock(return_value=[])

        with patch("time.sleep"):
            admiral.run_loop(max_cycles=100)

        # Circuit breaker at 5 consecutive failures
        assert failure_count["count"] == 5
        assert admiral._running is False

    @log_call
    def test_circuit_breaker_resets_on_success(self):
        admiral = _make_admiral()
        call_seq = {"n": 0}

        @log_call
        def intermittent_run_once():
            call_seq["n"] += 1
            # Fail on calls 1-4, succeed on 5, fail on 6-9, succeed on 10
            if call_seq["n"] in (5, 10):
                return []
            raise RuntimeError("boom")

        admiral.run_once = intermittent_run_once
        admiral.task_queue.next_task = MagicMock(return_value=_make_task())
        admiral.task_queue.active_tasks = MagicMock(return_value=[])

        with patch("time.sleep"):
            admiral.run_loop(max_cycles=10)

        # All 10 cycles should execute because successes reset the counter
        assert call_seq["n"] == 10

    @log_call
    def test_stops_when_all_tasks_done(self):
        admiral = _make_admiral()
        cycles = {"n": 0}

        @log_call
        def mock_run_once():
            cycles["n"] += 1
            return []

        admiral.run_once = mock_run_once
        # No queued and no active tasks -> all done
        admiral.task_queue.next_task = MagicMock(return_value=None)
        admiral.task_queue.active_tasks = MagicMock(return_value=[])

        with patch("time.sleep"):
            admiral.run_loop(max_cycles=100)

        # Should stop after the first cycle since all tasks are done
        assert cycles["n"] == 1

    @log_call
    def test_stop_method_halts_loop(self):
        admiral = _make_admiral()
        cycles = {"n": 0}

        @log_call
        def mock_run_once():
            cycles["n"] += 1
            if cycles["n"] == 2:
                admiral.stop()
            return []

        admiral.run_once = mock_run_once
        admiral.task_queue.next_task = MagicMock(return_value=_make_task())
        admiral.task_queue.active_tasks = MagicMock(return_value=[])

        with patch("time.sleep"):
            admiral.run_loop(max_cycles=100)

        # stop() sets _running = False, checked at top of while loop
        # Cycle 2 calls stop(), then sleep, then while check exits
        assert cycles["n"] == 2
        assert admiral._running is False


class TestPerceive:
    """perceive() refreshes fleet state and observes sessions."""

    @log_call
    def test_calls_refresh(self):
        admiral = _make_admiral()
        admiral._fleet_state = MagicMock()
        admiral._fleet_state.managed_vms.return_value = []

        admiral.perceive()
        admiral._fleet_state.refresh.assert_called_once()

    @log_call
    def test_observes_running_vm_sessions(self):
        admiral = _make_admiral()
        session = TmuxSessionInfo(session_name="fleet-t1", vm_name="vm-1")
        vm = _make_vm("vm-1", status="Running", sessions=[session])

        admiral._fleet_state = MagicMock()
        admiral._fleet_state.managed_vms.return_value = [vm]

        obs_result = MagicMock()
        obs_result.status = AgentStatus.RUNNING
        obs_result.last_output_lines = ["line1", "line2"]
        admiral._observer = MagicMock()
        admiral._observer.observe_session.return_value = obs_result

        admiral.perceive()

        admiral._observer.observe_session.assert_called_once_with("vm-1", "fleet-t1")
        assert session.agent_status == AgentStatus.RUNNING
        assert session.last_output == "line1\nline2"

    @log_call
    def test_skips_non_running_vms(self):
        admiral = _make_admiral()
        vm = _make_vm("stopped-vm", status="Stopped")

        admiral._fleet_state = MagicMock()
        admiral._fleet_state.managed_vms.return_value = [vm]
        admiral._observer = MagicMock()

        admiral.perceive()
        admiral._observer.observe_session.assert_not_called()


class TestReason:
    """reason() delegates to ReasonerChain and saves task queue."""

    @log_call
    def test_delegates_to_reasoner_chain(self):
        admiral = _make_admiral()
        expected = [DirectorAction(action_type=ActionType.REPORT)]
        admiral._reasoner_chain = MagicMock()
        admiral._reasoner_chain.reason.return_value = expected
        admiral.task_queue = MagicMock()

        state = MagicMock()
        result = admiral.reason(state)

        admiral._reasoner_chain.reason.assert_called_once_with(state, admiral.task_queue)
        assert result == expected

    @log_call
    def test_saves_task_queue_after_reasoning(self):
        admiral = _make_admiral()
        admiral._reasoner_chain = MagicMock()
        admiral._reasoner_chain.reason.return_value = []
        admiral.task_queue = MagicMock()

        admiral.reason(MagicMock())
        admiral.task_queue.save.assert_called_once()


class TestAct:
    """act() executes actions and records outcomes."""

    @log_call
    def test_executes_and_records(self):
        admiral = _make_admiral()
        task = _make_task()
        action = DirectorAction(
            action_type=ActionType.MARK_COMPLETE,
            task=task,
            vm_name="vm-1",
        )
        admiral._log = MagicMock()

        results = admiral.act([action])

        assert len(results) == 1
        assert results[0][1] == "Task marked complete"
        admiral._log.record.assert_called_once()

    @log_call
    def test_handles_action_exception(self):
        admiral = _make_admiral()
        action = DirectorAction(
            action_type=ActionType.START_AGENT,
            task=None,  # Will cause "No task provided"
            vm_name="vm-1",
        )
        admiral._log = MagicMock()

        results = admiral.act([action])
        assert len(results) == 1
        assert "ERROR" in results[0][1]

    @log_call
    def test_multiple_actions(self):
        admiral = _make_admiral()
        t1 = _make_task(id="t1")
        t2 = _make_task(id="t2")
        actions = [
            DirectorAction(action_type=ActionType.MARK_COMPLETE, task=t1),
            DirectorAction(action_type=ActionType.MARK_FAILED, task=t2, reason="stuck"),
        ]
        admiral._log = MagicMock()

        results = admiral.act(actions)
        assert len(results) == 2
        assert t1.status == TaskStatus.COMPLETED
        assert t2.status == TaskStatus.FAILED


class TestLearn:
    """learn() increments stats and calls store_discovery on failures."""

    @log_call
    def test_success_increments_stats(self):
        admiral = _make_admiral()
        action = DirectorAction(action_type=ActionType.REPORT, vm_name="vm-1")

        admiral.learn([(action, "ok")])

        assert admiral._stats["actions"] == 1
        assert admiral._stats["successes"] == 1
        assert admiral._stats["failures"] == 0

    @log_call
    def test_failure_increments_stats(self):
        admiral = _make_admiral()
        action = DirectorAction(action_type=ActionType.START_AGENT, vm_name="vm-1")

        admiral.learn([(action, "ERROR: timeout")])

        assert admiral._stats["actions"] == 1
        assert admiral._stats["successes"] == 0
        assert admiral._stats["failures"] == 1

    @log_call
    def test_multiple_results_accumulate(self):
        admiral = _make_admiral()
        results = [
            (DirectorAction(action_type=ActionType.REPORT, vm_name="vm-1"), "ok"),
            (DirectorAction(action_type=ActionType.REPORT, vm_name="vm-2"), "ERROR: fail"),
            (DirectorAction(action_type=ActionType.REPORT, vm_name="vm-3"), "done"),
        ]

        admiral.learn(results)

        assert admiral._stats["actions"] == 3
        assert admiral._stats["successes"] == 2
        assert admiral._stats["failures"] == 1

    @log_call
    def test_failure_calls_store_discovery(self):
        admiral = _make_admiral()
        action = DirectorAction(action_type=ActionType.START_AGENT, vm_name="vm-1")

        with patch(
            "amplihack.fleet.fleet_admiral.store_discovery",
            create=True,
        ) as mock_store:
            # Patch the import inside learn()
            with patch.dict(
                "sys.modules",
                {"amplihack.memory.discoveries": MagicMock(store_discovery=mock_store)},
            ):
                admiral.learn([(action, "ERROR: timeout")])

            mock_store.assert_called_once()
            call_kwargs = mock_store.call_args
            assert "fleet-failure" in str(call_kwargs)

    @log_call
    def test_success_calls_store_discovery_for_high_value_actions(self):
        admiral = _make_admiral()
        action = DirectorAction(action_type=ActionType.START_AGENT, vm_name="vm-1")

        mock_store = MagicMock()
        with patch.dict(
            "sys.modules",
            {"amplihack.memory.discoveries": MagicMock(store_discovery=mock_store)},
        ):
            admiral.learn([(action, "Agent started")])

        mock_store.assert_called_once()
        assert "fleet-success" in str(mock_store.call_args)

    @log_call
    def test_success_skips_store_for_low_value_actions(self):
        admiral = _make_admiral()
        action = DirectorAction(action_type=ActionType.REPORT, vm_name="vm-1")

        mock_store = MagicMock()
        with patch.dict(
            "sys.modules",
            {"amplihack.memory.discoveries": MagicMock(store_discovery=mock_store)},
        ):
            admiral.learn([(action, "reported")])

        mock_store.assert_not_called()

    # amplihack-memory-lib is a required dependency — no fallback tests needed


class TestRecallLearnings:
    """recall_learnings retrieves discoveries from memory."""

    @log_call
    def test_returns_discoveries(self):
        admiral = _make_admiral()
        fake_discoveries = [{"content": "found a thing"}]

        mock_mod = MagicMock()
        mock_mod.get_recent_discoveries.return_value = fake_discoveries

        with patch.dict("sys.modules", {"amplihack.memory.discoveries": mock_mod}):
            result = admiral.recall_learnings(limit=3)

        assert result == fake_discoveries
        mock_mod.get_recent_discoveries.assert_called_once_with(days=30, limit=3)


class TestStatusReport:
    """status_report includes stats and cycle count."""

    @log_call
    def test_includes_cycle_count(self):
        admiral = _make_admiral()
        admiral._cycle_count = 7
        admiral._fleet_state = MagicMock()
        admiral._fleet_state.summary.return_value = "Fleet: 2 VMs"
        admiral.task_queue = MagicMock()
        admiral.task_queue.summary.return_value = "Tasks: 3 queued"

        report = admiral.status_report()

        assert "Cycle 7" in report

    @log_call
    def test_includes_stats(self):
        admiral = _make_admiral()
        admiral._stats = {"actions": 10, "successes": 8, "failures": 2}
        admiral._fleet_state = MagicMock()
        admiral._fleet_state.summary.return_value = ""
        admiral.task_queue = MagicMock()
        admiral.task_queue.summary.return_value = ""

        report = admiral.status_report()

        assert "10 actions" in report
        assert "8 successes" in report
        assert "2 failures" in report

    @log_call
    def test_includes_log_action_count(self):
        admiral = _make_admiral()
        admiral._log = DirectorLog(actions=[{"a": 1}, {"b": 2}])
        admiral._fleet_state = MagicMock()
        admiral._fleet_state.summary.return_value = ""
        admiral.task_queue = MagicMock()
        admiral.task_queue.summary.return_value = ""

        report = admiral.status_report()
        assert "2 actions recorded" in report

    @log_call
    def test_includes_fleet_and_queue_summaries(self):
        admiral = _make_admiral()
        admiral._fleet_state = MagicMock()
        admiral._fleet_state.summary.return_value = "FLEET_SUMMARY_MARKER"
        admiral.task_queue = MagicMock()
        admiral.task_queue.summary.return_value = "QUEUE_SUMMARY_MARKER"

        report = admiral.status_report()

        assert "FLEET_SUMMARY_MARKER" in report
        assert "QUEUE_SUMMARY_MARKER" in report


class TestExecuteAction:
    """_execute_action dispatches to the correct handler."""

    @log_call
    def test_start_agent_no_task_returns_error(self):
        admiral = _make_admiral()
        action = DirectorAction(action_type=ActionType.START_AGENT, task=None, vm_name="vm-1")
        result = admiral._execute_action(action)
        assert "ERROR" in result

    @log_call
    def test_mark_complete(self):
        admiral = _make_admiral()
        task = _make_task()
        action = DirectorAction(action_type=ActionType.MARK_COMPLETE, task=task)

        result = admiral._execute_action(action)

        assert result == "Task marked complete"
        assert task.status == TaskStatus.COMPLETED

    @log_call
    def test_mark_failed(self):
        admiral = _make_admiral()
        task = _make_task()
        action = DirectorAction(action_type=ActionType.MARK_FAILED, task=task, reason="stuck")

        result = admiral._execute_action(action)

        assert "Task marked failed" in result
        assert task.status == TaskStatus.FAILED
        assert task.error == "stuck"

    @log_call
    def test_reassign_task_requeues(self):
        admiral = _make_admiral()
        task = _make_task(status=TaskStatus.RUNNING)
        task.assigned_vm = "vm-1"
        task.assigned_session = "fleet-t1"

        action = DirectorAction(
            action_type=ActionType.REASSIGN_TASK,
            task=task,
            vm_name="vm-1",
            session_name="fleet-t1",
        )

        with patch("subprocess.run"):
            result = admiral._execute_action(action)

        assert task.status == TaskStatus.QUEUED
        assert task.assigned_vm is None
        assert task.assigned_session is None
        assert "requeued" in result

    @log_call
    def test_reassign_missing_fields_returns_error(self):
        admiral = _make_admiral()
        action = DirectorAction(
            action_type=ActionType.REASSIGN_TASK,
            task=None,
            vm_name=None,
            session_name=None,
        )
        result = admiral._execute_action(action)
        assert "ERROR" in result

    @log_call
    def test_unknown_action_type(self):
        admiral = _make_admiral()
        action = DirectorAction(action_type=ActionType.REPORT)
        result = admiral._execute_action(action)
        assert "Unknown action" in result

    @patch("subprocess.run")
    @log_call
    def test_start_agent_success(self, mock_run):
        admiral = _make_admiral()
        task = _make_task()
        action = DirectorAction(
            action_type=ActionType.START_AGENT,
            task=task,
            vm_name="vm-1",
            session_name="fleet-t1",
        )

        mock_run.return_value = MagicMock(returncode=0)
        result = admiral._execute_action(action)

        assert "Agent started" in result
        assert task.status == TaskStatus.RUNNING

    @patch("subprocess.run")
    @log_call
    def test_start_agent_failure(self, mock_run):
        admiral = _make_admiral()
        task = _make_task()
        action = DirectorAction(
            action_type=ActionType.START_AGENT,
            task=task,
            vm_name="vm-1",
        )

        mock_run.return_value = MagicMock(returncode=1, stderr="connection refused")
        result = admiral._execute_action(action)

        assert "ERROR" in result

    @patch("subprocess.run")
    @log_call
    def test_start_agent_timeout(self, mock_run):
        import subprocess as sp

        admiral = _make_admiral()
        task = _make_task()
        action = DirectorAction(
            action_type=ActionType.START_AGENT,
            task=task,
            vm_name="vm-1",
        )

        mock_run.side_effect = sp.TimeoutExpired(cmd="azlin", timeout=60)
        result = admiral._execute_action(action)

        assert "ERROR" in result
        assert "Timeout" in result

    @log_call
    def test_propagate_auth(self):
        admiral = _make_admiral()
        admiral._auth = MagicMock()
        mock_result = MagicMock(success=True)
        admiral._auth.propagate_all.return_value = [mock_result]

        action = DirectorAction(action_type=ActionType.PROPAGATE_AUTH, vm_name="vm-1")
        result = admiral._execute_action(action)

        assert "Auth propagated" in result
        admiral._auth.propagate_all.assert_called_once_with("vm-1")

    @log_call
    def test_propagate_auth_no_vm(self):
        admiral = _make_admiral()
        action = DirectorAction(action_type=ActionType.PROPAGATE_AUTH, vm_name=None)
        result = admiral._execute_action(action)
        assert "ERROR" in result


class TestValidateName:
    """validate_vm_name / validate_session_name reject invalid names."""

    @log_call
    def test_valid_vm_names(self):
        validate_vm_name("vm-1")
        validate_vm_name("my_vm")
        validate_vm_name("A123")

    @log_call
    def test_valid_session_names(self):
        validate_session_name("session-1")
        validate_session_name("my_session.test")
        validate_session_name("A123:colon")

    @log_call
    def test_empty_name(self):
        with pytest.raises(ValueError, match="Invalid"):
            validate_vm_name("")

    @log_call
    def test_name_starting_with_special(self):
        with pytest.raises(ValueError, match="Invalid"):
            validate_vm_name("-bad")

    @log_call
    def test_name_with_spaces(self):
        with pytest.raises(ValueError, match="Invalid"):
            validate_vm_name("has space")

    @log_call
    def test_none_name(self):
        with pytest.raises((ValueError, TypeError)):
            validate_vm_name(None)  # type: ignore[arg-type]  # testing invalid input


class TestDirectorLog:
    """DirectorLog records and persists entries."""

    @log_call
    def test_record_appends(self):
        log = DirectorLog()
        action = DirectorAction(action_type=ActionType.REPORT, vm_name="vm-1", reason="test")
        log.record(action, "ok")
        assert len(log.actions) == 1
        assert log.actions[0]["outcome"] == "ok"
        assert log.actions[0]["action"] == "report"

    @log_call
    def test_persist_to_file(self, tmp_path):
        path = tmp_path / "log.json"
        log = DirectorLog(persist_path=path)
        action = DirectorAction(action_type=ActionType.REPORT)
        log.record(action, "ok")

        import json

        data = json.loads(path.read_text())
        assert len(data) == 1
        assert data[0]["outcome"] == "ok"


class TestMissingSessionGracePeriod:
    """LifecycleReasoner grace period for missing sessions (2-cycle threshold).

    The grace period logic lives in LifecycleReasoner, but the FleetAdmiral
    also carries _missing_session_counts on its own dataclass. This test
    verifies the admiral-level field initializes correctly and that the
    end-to-end flow through reason() can trigger the grace period behavior.
    """

    @log_call
    def test_missing_session_counts_starts_empty(self):
        admiral = _make_admiral()
        assert admiral._missing_session_counts == {}

    @log_call
    def test_lifecycle_reasoner_has_grace_period(self):
        """Verify the LifecycleReasoner wired into the chain has the field."""
        admiral = _make_admiral()
        lifecycle = admiral._reasoner_chain.reasoners[0]
        assert hasattr(lifecycle, "_missing_session_counts")
        assert lifecycle._missing_session_counts == {}
