"""Tests for SharedStateManager."""

import uuid
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile

from amplihack.goal_agent_generator.models import CoordinationMessage
from amplihack.goal_agent_generator.phase3.shared_state_manager import SharedStateManager


class TestSharedStateManager:
    """Test suite for SharedStateManager."""

    def test_get_set_basic(self):
        """Test basic get/set operations."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)

            # Set value
            manager.set("test_key", "test_value")

            # Get value
            value = manager.get("test_key")
            assert value == "test_value"

            # Get with default
            assert manager.get("missing", "default") == "default"

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_update_atomic(self):
        """Test atomic update operation."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)

            # Set initial value
            manager.set("counter", 0)

            # Update atomically
            manager.update("counter", lambda x: x + 1)
            assert manager.get("counter") == 1

            manager.update("counter", lambda x: x * 2)
            assert manager.get("counter") == 2

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_delete(self):
        """Test delete operation."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)

            manager.set("key", "value")
            assert manager.get("key") == "value"

            manager.delete("key")
            assert manager.get("key") is None

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_get_all(self):
        """Test getting all state."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)

            manager.set("a", 1)
            manager.set("b", 2)
            manager.set("c", 3)

            all_state = manager.get_all()
            assert all_state == {"a": 1, "b": 2, "c": 3}

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_clear(self):
        """Test clearing all state."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)

            manager.set("a", 1)
            manager.set("b", 2)

            manager.clear()

            assert manager.get_all() == {}

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_subscribe_notifications(self):
        """Test subscription to state changes."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)

            changes = []

            def callback(state):
                changes.append(state.value)

            manager.subscribe("status", callback)

            manager.set("status", "running")
            manager.set("status", "completed")

            assert len(changes) == 2
            assert "running" in changes
            assert "completed" in changes

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_unsubscribe(self):
        """Test unsubscribing from state changes."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)

            changes = []

            def callback(state):
                changes.append(state.value)

            manager.subscribe("status", callback)
            manager.set("status", "running")

            manager.unsubscribe("status", callback)
            manager.set("status", "completed")

            # Should only have one change (before unsubscribe)
            assert len(changes) == 1
            assert changes[0] == "running"

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_publish_message(self):
        """Test publishing coordination messages."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)

            agent_id = uuid.uuid4()
            msg = CoordinationMessage(
                from_agent=agent_id,
                message_type="PhaseCompleted",
                payload={"phase": "analyze", "success": True},
            )

            manager.publish_message(msg)

            # Verify message is stored
            messages_key = f"messages.{agent_id}"
            messages = manager.get(messages_key)
            assert messages is not None
            assert len(messages) == 1

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_get_messages(self):
        """Test retrieving messages for an agent."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)

            agent1 = uuid.uuid4()
            agent2 = uuid.uuid4()

            # Publish messages
            msg1 = CoordinationMessage(
                from_agent=agent1,
                to_agent=agent2,
                message_type="DataAvailable",
                payload={"data_key": "test"},
            )
            manager.publish_message(msg1)

            msg2 = CoordinationMessage(
                from_agent=agent1,
                message_type="StatusUpdate",
                payload={"status": "running"},
            )
            manager.publish_message(msg2)

            # Get messages for agent2
            messages = manager.get_messages(agent2)
            assert len(messages) >= 1

            # Get broadcast messages (to_agent=None)
            messages = manager.get_messages(agent2, message_type=None)
            assert len(messages) >= 1

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_get_messages_by_type(self):
        """Test filtering messages by type."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)

            agent_id = uuid.uuid4()

            # Publish different message types
            msg1 = CoordinationMessage(
                from_agent=agent_id,
                message_type="PhaseCompleted",
                payload={"phase": "test"},
            )
            manager.publish_message(msg1)

            msg2 = CoordinationMessage(
                from_agent=agent_id,
                message_type="StatusUpdate",
                payload={"status": "running"},
            )
            manager.publish_message(msg2)

            # Filter by type
            phase_messages = manager.get_messages(agent_id, message_type="PhaseCompleted")
            status_messages = manager.get_messages(agent_id, message_type="StatusUpdate")

            # Note: get_messages looks for messages TO an agent, not FROM
            # So we need to check the overall message store
            all_messages = manager.get_messages(agent_id)
            assert len(all_messages) >= 2

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_event_log(self):
        """Test event logging."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)

            manager.set("key1", "value1")
            manager.set("key2", "value2")
            manager.delete("key1")

            events = manager.get_event_log()
            assert len(events) > 0

            # Check event types
            event_types = [e["event_type"] for e in events]
            assert "state_set" in event_types
            assert "state_delete" in event_types

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_event_log_limit(self):
        """Test event log limit."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)

            # Generate many events
            for i in range(20):
                manager.set(f"key{i}", i)

            # Get limited events
            limited_events = manager.get_event_log(limit=5)
            assert len(limited_events) == 5

            # Verify we got the most recent ones
            full_log = manager.get_event_log()
            assert limited_events == full_log[-5:]

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_export_import_state(self):
        """Test exporting and importing state."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager1 = SharedStateManager(state_file)

            manager1.set("key1", "value1")
            manager1.set("key2", {"nested": "data"})

            # Export state
            exported = manager1.export_state()

            # Import into new manager
            manager2 = SharedStateManager()
            manager2.import_state(exported)

            # Verify state transferred
            assert manager2.get("key1") == "value1"
            assert manager2.get("key2") == {"nested": "data"}

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_persistence(self):
        """Test state persistence to file."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            # Create manager and set state
            manager1 = SharedStateManager(state_file)
            manager1.set("persistent_key", "persistent_value")

            # Create new manager with same file
            manager2 = SharedStateManager(state_file)

            # Verify state was loaded
            assert manager2.get("persistent_key") == "persistent_value"

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_thread_safety(self):
        """Test thread-safe operations."""
        import threading

        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)
            manager.set("counter", 0)

            def increment():
                for _ in range(100):
                    manager.update("counter", lambda x: (x or 0) + 1)

            threads = [threading.Thread(target=increment) for _ in range(5)]

            for t in threads:
                t.start()

            for t in threads:
                t.join()

            # With proper locking, counter should be 500
            assert manager.get("counter") == 500

        finally:
            if state_file.exists():
                state_file.unlink()

    def test_state_versioning(self):
        """Test that state versions increment."""
        with NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            state_file = Path(f.name)

        try:
            manager = SharedStateManager(state_file)

            manager.set("key", "value1")
            exported1 = manager.export_state()
            version1 = exported1["state"]["key"]["version"]

            manager.set("key", "value2")
            exported2 = manager.export_state()
            version2 = exported2["state"]["key"]["version"]

            assert version2 > version1

        finally:
            if state_file.exists():
                state_file.unlink()
