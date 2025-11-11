"""
SharedStateManager: Thread-safe shared state for coordinated agents.

Provides thread-safe shared state storage, pub/sub communication,
persistence to .agent_state.json, and event logging for debugging.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import uuid

from ..models import SharedState, CoordinationMessage


class SharedStateManager:
    """Thread-safe shared state manager for multi-agent coordination."""

    def __init__(self, state_file: Optional[Path] = None):
        """
        Initialize shared state manager.

        Args:
            state_file: Path to persist state (default: .agent_state.json)

        Example:
            >>> manager = SharedStateManager()
            >>> manager.set("config.timeout", 30)
            >>> assert manager.get("config.timeout") == 30
        """
        self.state_file = state_file or Path(".agent_state.json")
        self._state: Dict[str, SharedState] = {}
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[Callable[[SharedState], None]]] = {}
        self._event_log: List[Dict[str, Any]] = []

        # Load existing state if file exists
        self._load_state()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from shared state.

        Args:
            key: State key
            default: Default value if key doesn't exist

        Returns:
            Value associated with key, or default

        Example:
            >>> manager = SharedStateManager()
            >>> manager.set("counter", 5)
            >>> assert manager.get("counter") == 5
            >>> assert manager.get("missing", 0) == 0
        """
        with self._lock:
            if key in self._state:
                return self._state[key].value
            return default

    def set(
        self,
        key: str,
        value: Any,
        owner_agent_id: Optional[uuid.UUID] = None,
    ) -> None:
        """
        Set value in shared state.

        Args:
            key: State key
            value: Value to store
            owner_agent_id: Agent that owns this state

        Side effects:
            Notifies subscribers of state change
            Logs event
            Persists to file

        Example:
            >>> manager = SharedStateManager()
            >>> agent_id = uuid.uuid4()
            >>> manager.set("status", "running", agent_id)
            >>> assert manager.get("status") == "running"
        """
        with self._lock:
            # Update or create state
            if key in self._state:
                old_value = self._state[key].value
                self._state[key].value = value
                self._state[key].updated_at = datetime.utcnow()
                self._state[key].version += 1
            else:
                old_value = None
                self._state[key] = SharedState(
                    key=key,
                    value=value,
                    owner_agent_id=owner_agent_id,
                    updated_at=datetime.utcnow(),
                    version=1,
                )

            # Log event
            self._log_event(
                event_type="state_set",
                data={
                    "key": key,
                    "old_value": str(old_value) if old_value is not None else None,
                    "new_value": str(value),
                    "owner_agent_id": str(owner_agent_id) if owner_agent_id else None,
                },
            )

            # Notify subscribers
            self._notify_subscribers(key, self._state[key])

            # Persist to file
            self._persist_state()

    def update(self, key: str, update_fn: Callable[[Any], Any]) -> None:
        """
        Atomically update state value.

        Args:
            key: State key
            update_fn: Function to transform current value

        Example:
            >>> manager = SharedStateManager()
            >>> manager.set("counter", 0)
            >>> manager.update("counter", lambda x: x + 1)
            >>> assert manager.get("counter") == 1
        """
        with self._lock:
            current = self.get(key)
            new_value = update_fn(current)
            self.set(key, new_value)

    def delete(self, key: str) -> None:
        """
        Delete key from shared state.

        Args:
            key: State key to delete

        Example:
            >>> manager = SharedStateManager()
            >>> manager.set("temp", "value")
            >>> manager.delete("temp")
            >>> assert manager.get("temp") is None
        """
        with self._lock:
            if key in self._state:
                del self._state[key]
                self._log_event(event_type="state_delete", data={"key": key})
                self._persist_state()

    def get_all(self) -> Dict[str, Any]:
        """
        Get all state values.

        Returns:
            Dictionary of all state key-value pairs

        Example:
            >>> manager = SharedStateManager()
            >>> manager.set("a", 1)
            >>> manager.set("b", 2)
            >>> state = manager.get_all()
            >>> assert state == {"a": 1, "b": 2}
        """
        with self._lock:
            return {key: state.value for key, state in self._state.items()}

    def clear(self) -> None:
        """
        Clear all state.

        Side effects:
            Removes all state
            Logs event
            Persists to file
        """
        with self._lock:
            self._state.clear()
            self._log_event(event_type="state_clear", data={})
            self._persist_state()

    def subscribe(self, key: str, callback: Callable[[SharedState], None]) -> None:
        """
        Subscribe to state changes for a key.

        Args:
            key: State key to watch
            callback: Function called when key changes

        Example:
            >>> manager = SharedStateManager()
            >>> changes = []
            >>> manager.subscribe("status", lambda s: changes.append(s.value))
            >>> manager.set("status", "running")
            >>> assert "running" in changes
        """
        with self._lock:
            if key not in self._subscribers:
                self._subscribers[key] = []
            self._subscribers[key].append(callback)

    def unsubscribe(self, key: str, callback: Callable[[SharedState], None]) -> None:
        """
        Unsubscribe from state changes.

        Args:
            key: State key
            callback: Callback to remove
        """
        with self._lock:
            if key in self._subscribers and callback in self._subscribers[key]:
                self._subscribers[key].remove(callback)

    def publish_message(self, message: CoordinationMessage) -> None:
        """
        Publish coordination message to interested agents.

        Args:
            message: Coordination message to publish

        Side effects:
            Logs event
            Stores message in state for retrieval

        Example:
            >>> manager = SharedStateManager()
            >>> msg = CoordinationMessage(
            ...     from_agent=uuid.uuid4(),
            ...     message_type="PhaseCompleted",
            ...     payload={"phase": "analyze"}
            ... )
            >>> manager.publish_message(msg)
        """
        with self._lock:
            # Store message in state
            messages_key = f"messages.{message.from_agent}"
            messages = self.get(messages_key, [])
            messages.append({
                "id": str(message.id),
                "to_agent": str(message.to_agent) if message.to_agent else None,
                "message_type": message.message_type,
                "payload": message.payload,
                "timestamp": message.timestamp.isoformat(),
            })
            self.set(messages_key, messages)

            # Log event
            self._log_event(
                event_type="message_published",
                data={
                    "message_id": str(message.id),
                    "from_agent": str(message.from_agent),
                    "to_agent": str(message.to_agent) if message.to_agent else "broadcast",
                    "message_type": message.message_type,
                },
            )

    def get_messages(
        self, agent_id: uuid.UUID, message_type: Optional[str] = None
    ) -> List[CoordinationMessage]:
        """
        Get messages for an agent.

        Args:
            agent_id: Agent ID
            message_type: Filter by message type (optional)

        Returns:
            List of coordination messages

        Example:
            >>> manager = SharedStateManager()
            >>> msg = CoordinationMessage(
            ...     from_agent=uuid.uuid4(),
            ...     to_agent=agent_id,
            ...     message_type="DataAvailable",
            ...     payload={"data": "test"}
            ... )
            >>> manager.publish_message(msg)
            >>> messages = manager.get_messages(agent_id)
            >>> assert len(messages) > 0
        """
        with self._lock:
            all_messages: List[CoordinationMessage] = []

            # Collect messages from all agents
            for key in self._state:
                if key.startswith("messages."):
                    messages_data = self.get(key, [])
                    for msg_data in messages_data:
                        # Check if message is for this agent (or broadcast)
                        to_agent = msg_data.get("to_agent")
                        if to_agent is None or to_agent == str(agent_id):
                            # Filter by type if specified
                            if message_type is None or msg_data["message_type"] == message_type:
                                # Reconstruct message
                                msg = CoordinationMessage(
                                    id=uuid.UUID(msg_data["id"]),
                                    from_agent=uuid.UUID(key.split(".")[1]),
                                    to_agent=uuid.UUID(to_agent) if to_agent else None,
                                    message_type=msg_data["message_type"],
                                    payload=msg_data["payload"],
                                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                                )
                                all_messages.append(msg)

            return all_messages

    def get_event_log(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get event log for debugging.

        Args:
            limit: Maximum number of events to return (most recent)

        Returns:
            List of event dictionaries

        Example:
            >>> manager = SharedStateManager()
            >>> manager.set("test", "value")
            >>> events = manager.get_event_log(limit=5)
            >>> assert len(events) > 0
            >>> assert events[-1]["event_type"] == "state_set"
        """
        with self._lock:
            if limit:
                return self._event_log[-limit:]
            return self._event_log.copy()

    def export_state(self) -> Dict[str, Any]:
        """
        Export current state as dictionary.

        Returns:
            Dictionary representation of state

        Example:
            >>> manager = SharedStateManager()
            >>> manager.set("key", "value")
            >>> exported = manager.export_state()
            >>> assert "state" in exported
            >>> assert exported["state"]["key"]["value"] == "value"
        """
        with self._lock:
            return {
                "state": {
                    key: {
                        "value": state.value,
                        "owner_agent_id": str(state.owner_agent_id) if state.owner_agent_id else None,
                        "updated_at": state.updated_at.isoformat(),
                        "version": state.version,
                    }
                    for key, state in self._state.items()
                },
                "event_log": self._event_log,
            }

    def import_state(self, state_data: Dict[str, Any]) -> None:
        """
        Import state from dictionary.

        Args:
            state_data: Dictionary representation of state

        Side effects:
            Replaces current state
            Persists to file
        """
        with self._lock:
            self._state.clear()

            if "state" in state_data:
                for key, state_dict in state_data["state"].items():
                    owner_id = state_dict.get("owner_agent_id")
                    self._state[key] = SharedState(
                        key=key,
                        value=state_dict["value"],
                        owner_agent_id=uuid.UUID(owner_id) if owner_id else None,
                        updated_at=datetime.fromisoformat(state_dict["updated_at"]),
                        version=state_dict["version"],
                    )

            if "event_log" in state_data:
                self._event_log = state_data["event_log"]

            self._persist_state()

    # Private methods

    def _notify_subscribers(self, key: str, state: SharedState) -> None:
        """Notify subscribers of state change."""
        if key in self._subscribers:
            for callback in self._subscribers[key]:
                try:
                    callback(state)
                except Exception as e:
                    self._log_event(
                        event_type="subscriber_error",
                        data={"key": key, "error": str(e)},
                    )

    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log event to event log."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": data,
        }
        self._event_log.append(event)

        # Keep log size reasonable (last 1000 events)
        if len(self._event_log) > 1000:
            self._event_log = self._event_log[-1000:]

    def _persist_state(self) -> None:
        """Persist state to file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.export_state(), f, indent=2, default=str)
        except Exception as e:
            self._log_event(event_type="persist_error", data={"error": str(e)})

    def _load_state(self) -> None:
        """Load state from file if it exists."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    state_data = json.load(f)
                    self.import_state(state_data)
            except Exception as e:
                self._log_event(event_type="load_error", data={"error": str(e)})
