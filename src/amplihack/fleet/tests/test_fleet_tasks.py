"""Tests for fleet task queue — 60% unit tests, 30% integration, 10% E2E.

Tests the TaskQueue and FleetTask without any external dependencies.
"""

import json

from amplihack.fleet.fleet_tasks import FleetTask, TaskPriority, TaskQueue, TaskStatus

# ============ UNIT TESTS (60%) ============


class TestFleetTask:
    """Unit tests for FleetTask dataclass."""

    def test_create_task_defaults(self):
        task = FleetTask(prompt="Fix the bug")
        assert task.prompt == "Fix the bug"
        assert task.priority == TaskPriority.MEDIUM
        assert task.status == TaskStatus.QUEUED
        assert task.agent_command == "claude"
        assert task.agent_mode == "auto"
        assert task.id  # Should have auto-generated ID
        assert len(task.id) == 12

    def test_assign_task(self):
        task = FleetTask(prompt="Test")
        task.assign("vm-1", "session-1")
        assert task.status == TaskStatus.ASSIGNED
        assert task.assigned_vm == "vm-1"
        assert task.assigned_session == "session-1"
        assert task.assigned_at is not None

    def test_start_task(self):
        task = FleetTask(prompt="Test")
        task.assign("vm-1", "session-1")
        task.start()
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

    def test_complete_task(self):
        task = FleetTask(prompt="Test")
        task.start()
        task.complete(result="Done", pr_url="https://github.com/org/repo/pull/1")
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "Done"
        assert task.pr_url == "https://github.com/org/repo/pull/1"
        assert task.completed_at is not None

    def test_fail_task(self):
        task = FleetTask(prompt="Test")
        task.start()
        task.fail(error="Timeout")
        assert task.status == TaskStatus.FAILED
        assert task.error == "Timeout"
        assert task.completed_at is not None

    def test_serialization_roundtrip(self):
        task = FleetTask(
            prompt="Build feature",
            repo_url="https://github.com/org/repo",
            priority=TaskPriority.HIGH,
            agent_command="amplifier",
            max_turns=30,
        )
        task.assign("vm-1", "session-1")
        task.start()

        data = task.to_dict()
        restored = FleetTask.from_dict(data)

        assert restored.id == task.id
        assert restored.prompt == task.prompt
        assert restored.repo_url == task.repo_url
        assert restored.priority == TaskPriority.HIGH
        assert restored.status == TaskStatus.RUNNING
        assert restored.agent_command == "amplifier"
        assert restored.max_turns == 30
        assert restored.assigned_vm == "vm-1"

    def test_serialization_with_completion(self):
        task = FleetTask(prompt="Test")
        task.complete(result="ok", pr_url="https://example.com/pr/1")

        data = task.to_dict()
        restored = FleetTask.from_dict(data)

        assert restored.status == TaskStatus.COMPLETED
        assert restored.result == "ok"
        assert restored.pr_url == "https://example.com/pr/1"


class TestTaskQueue:
    """Unit tests for TaskQueue."""

    def test_add_and_get(self):
        queue = TaskQueue()
        task = queue.add_task(prompt="Task 1")
        assert len(queue.tasks) == 1
        assert queue.get_task(task.id) == task

    def test_next_task_priority_order(self):
        queue = TaskQueue()
        queue.add_task(prompt="Low priority", priority=TaskPriority.LOW)
        queue.add_task(prompt="High priority", priority=TaskPriority.HIGH)
        queue.add_task(prompt="Critical", priority=TaskPriority.CRITICAL)

        next_task = queue.next_task()
        assert next_task is not None
        assert next_task.prompt == "Critical"

    def test_next_task_fifo_within_priority(self):
        queue = TaskQueue()
        t1 = queue.add_task(prompt="First medium")
        queue.add_task(prompt="Second medium")

        next_task = queue.next_task()
        assert next_task is not None
        assert next_task.id == t1.id

    def test_next_task_skips_assigned(self):
        queue = TaskQueue()
        t1 = queue.add_task(prompt="First")
        t2 = queue.add_task(prompt="Second")
        t1.assign("vm-1", "sess-1")

        next_task = queue.next_task()
        assert next_task is not None
        assert next_task.id == t2.id

    def test_next_task_empty_queue(self):
        queue = TaskQueue()
        assert queue.next_task() is None

    def test_active_tasks(self):
        queue = TaskQueue()
        t1 = queue.add_task(prompt="Running")
        t2 = queue.add_task(prompt="Assigned")
        queue.add_task(prompt="Queued")

        t1.start()
        t2.assign("vm", "sess")

        active = queue.active_tasks()
        assert len(active) == 2

    def test_completed_tasks(self):
        queue = TaskQueue()
        t1 = queue.add_task(prompt="Done")
        t2 = queue.add_task(prompt="Failed")
        queue.add_task(prompt="Still queued")

        t1.complete()
        t2.fail("error")

        completed = queue.completed_tasks()
        assert len(completed) == 2

    def test_summary(self):
        queue = TaskQueue()
        queue.add_task(prompt="Task 1", priority=TaskPriority.HIGH)
        queue.add_task(prompt="Task 2", priority=TaskPriority.LOW)

        summary = queue.summary()
        assert "Task Queue (2 tasks)" in summary
        assert "QUEUED (2):" in summary
        assert "Task 1" in summary


# ============ INTEGRATION TESTS (30%) ============


class TestTaskQueuePersistence:
    """Integration tests for queue persistence."""

    def test_persist_and_load(self, tmp_path):
        path = tmp_path / "queue.json"

        # Create and populate queue
        queue = TaskQueue(persist_path=path)
        queue.add_task(prompt="Persistent task 1", priority=TaskPriority.HIGH)
        queue.add_task(prompt="Persistent task 2", priority=TaskPriority.LOW)

        # Load in new queue instance
        queue2 = TaskQueue(persist_path=path)
        assert len(queue2.tasks) == 2
        assert queue2.tasks[0].prompt == "Persistent task 1"
        assert queue2.tasks[0].priority == TaskPriority.HIGH

    def test_persist_updates_on_mutation(self, tmp_path):
        path = tmp_path / "queue.json"
        queue = TaskQueue(persist_path=path)
        task = queue.add_task(prompt="Test")

        # File should exist after add
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data) == 1
        assert data[0]["prompt"] == "Test"

    def test_handle_corrupt_file(self, tmp_path):
        path = tmp_path / "queue.json"
        path.write_text("not valid json{{{")

        queue = TaskQueue(persist_path=path)
        assert len(queue.tasks) == 0  # Graceful degradation

    def test_full_lifecycle_persisted(self, tmp_path):
        path = tmp_path / "queue.json"
        queue = TaskQueue(persist_path=path)

        task = queue.add_task(prompt="Full lifecycle")
        task.assign("vm-1", "sess-1")
        task.start()
        task.complete(result="Done", pr_url="https://example.com/pr/1")
        queue.save()  # Persist after mutations

        # Reload and verify
        queue2 = TaskQueue(persist_path=path)
        t = queue2.get_task(task.id)
        assert t is not None
        assert t.status == TaskStatus.COMPLETED
        assert t.pr_url == "https://example.com/pr/1"


# ============ E2E TESTS (10%) ============


class TestTaskQueueE2E:
    """End-to-end task queue workflow."""

    def test_full_priority_dispatch_workflow(self, tmp_path):
        """Simulate a real fleet dispatch scenario."""
        queue = TaskQueue(persist_path=tmp_path / "queue.json")

        # User adds tasks with different priorities
        critical = queue.add_task(
            prompt="Fix production outage",
            priority=TaskPriority.CRITICAL,
            agent_command="claude",
        )
        high = queue.add_task(
            prompt="Add authentication",
            repo_url="https://github.com/org/api",
            priority=TaskPriority.HIGH,
        )
        medium = queue.add_task(
            prompt="Refactor utils",
            priority=TaskPriority.MEDIUM,
        )

        # Director dispatches highest priority first
        next_t = queue.next_task()
        assert next_t is not None
        assert next_t.id == critical.id
        next_t.assign("vm-1", "fleet-001")
        next_t.start()

        # Director dispatches next
        next_t = queue.next_task()
        assert next_t is not None
        assert next_t.id == high.id
        next_t.assign("vm-2", "fleet-002")
        next_t.start()

        # Critical completes
        critical.complete(pr_url="https://github.com/org/repo/pull/99")

        # Medium is now dispatched
        next_t = queue.next_task()
        assert next_t is not None
        assert next_t.id == medium.id

        # Verify state
        assert len(queue.active_tasks()) == 1  # high still running
        assert len(queue.completed_tasks()) == 1  # critical done

        # Verify persistence survived the full workflow
        queue2 = TaskQueue(persist_path=tmp_path / "queue.json")
        assert len(queue2.tasks) == 3
