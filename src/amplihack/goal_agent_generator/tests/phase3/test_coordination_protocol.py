"""Tests for CoordinationProtocol."""

import uuid
import pytest
from datetime import datetime

from amplihack.goal_agent_generator.phase3.coordination_protocol import (
    CoordinationProtocol,
    MessageType,
)


class TestCoordinationProtocol:
    """Test suite for CoordinationProtocol."""

    def test_create_message_valid(self):
        """Test creating a valid message."""
        protocol = CoordinationProtocol()
        agent_id = uuid.uuid4()

        payload = {
            "agent_id": str(agent_id),
            "agent_name": "test-agent",
            "timestamp": datetime.utcnow().isoformat(),
        }

        msg = protocol.create_message(
            MessageType.AGENT_STARTED, agent_id, payload
        )

        assert msg.message_type == MessageType.AGENT_STARTED
        assert msg.from_agent == agent_id
        assert msg.payload == payload

    def test_create_message_invalid_type(self):
        """Test creating message with invalid type."""
        protocol = CoordinationProtocol()
        agent_id = uuid.uuid4()

        with pytest.raises(ValueError, match="Unknown message type"):
            protocol.create_message(
                "InvalidType", agent_id, {}
            )

    def test_validate_payload_required_fields(self):
        """Test payload validation for required fields."""
        protocol = CoordinationProtocol()

        # Missing required field
        payload = {
            "agent_id": str(uuid.uuid4()),
            # Missing "agent_name" and "timestamp"
        }

        result = protocol.validate_payload(MessageType.AGENT_STARTED, payload)

        assert result["valid"] is False
        assert len(result["errors"]) >= 2
        assert any("agent_name" in error for error in result["errors"])

    def test_validate_payload_field_types(self):
        """Test payload validation for field types."""
        protocol = CoordinationProtocol()

        # Wrong type for field
        payload = {
            "agent_id": str(uuid.uuid4()),
            "agent_name": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "capabilities": "should-be-list",  # Wrong type
        }

        result = protocol.validate_payload(MessageType.AGENT_STARTED, payload)

        assert result["valid"] is False
        assert any("capabilities" in error for error in result["errors"])

    def test_validate_payload_unknown_fields(self):
        """Test payload validation warns about unknown fields."""
        protocol = CoordinationProtocol()

        payload = {
            "agent_id": str(uuid.uuid4()),
            "agent_name": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "unknown_field": "value",
        }

        result = protocol.validate_payload(MessageType.AGENT_STARTED, payload)

        # Should be valid but with warning
        assert result["valid"] is True
        assert len(result["warnings"]) >= 1
        assert any("unknown_field" in warning for warning in result["warnings"])

    def test_get_schema(self):
        """Test getting schema for message type."""
        protocol = CoordinationProtocol()

        schema = protocol.get_schema(MessageType.PHASE_COMPLETED)

        assert schema is not None
        assert "phase_name" in schema.required_fields
        assert "success" in schema.required_fields

    def test_list_message_types(self):
        """Test listing all message types."""
        protocol = CoordinationProtocol()

        types = protocol.list_message_types()

        assert MessageType.AGENT_STARTED in types
        assert MessageType.PHASE_COMPLETED in types
        assert MessageType.DATA_AVAILABLE in types
        assert MessageType.HELP_NEEDED in types

    def test_create_agent_started(self):
        """Test convenience method for AgentStarted."""
        agent_id = uuid.uuid4()

        msg = CoordinationProtocol.create_agent_started(
            agent_id, "test-agent", "worker", ["cap1", "cap2"]
        )

        assert msg.message_type == MessageType.AGENT_STARTED
        assert msg.payload["agent_name"] == "test-agent"
        assert msg.payload["role"] == "worker"
        assert msg.payload["capabilities"] == ["cap1", "cap2"]

    def test_create_phase_completed(self):
        """Test convenience method for PhaseCompleted."""
        agent_id = uuid.uuid4()

        msg = CoordinationProtocol.create_phase_completed(
            agent_id,
            "analyze",
            True,
            outputs={"result": "success"},
            duration_seconds=10.5,
        )

        assert msg.message_type == MessageType.PHASE_COMPLETED
        assert msg.payload["phase_name"] == "analyze"
        assert msg.payload["success"] is True
        assert msg.payload["outputs"] == {"result": "success"}
        assert msg.payload["duration_seconds"] == 10.5

    def test_create_data_available(self):
        """Test convenience method for DataAvailable."""
        agent_id = uuid.uuid4()

        msg = CoordinationProtocol.create_data_available(
            agent_id,
            "phase.analyze.output",
            "dict",
            metadata={"size": 1024},
        )

        assert msg.message_type == MessageType.DATA_AVAILABLE
        assert msg.payload["data_key"] == "phase.analyze.output"
        assert msg.payload["data_type"] == "dict"
        assert msg.payload["metadata"] == {"size": 1024}

    def test_create_help_needed(self):
        """Test convenience method for HelpNeeded."""
        agent_id = uuid.uuid4()

        msg = CoordinationProtocol.create_help_needed(
            agent_id,
            "Cannot access database",
            "high",
            context={"db": "postgres"},
        )

        assert msg.message_type == MessageType.HELP_NEEDED
        assert msg.payload["problem"] == "Cannot access database"
        assert msg.payload["severity"] == "high"
        assert msg.payload["context"] == {"db": "postgres"}

    def test_create_agent_completed(self):
        """Test convenience method for AgentCompleted."""
        agent_id = uuid.uuid4()

        msg = CoordinationProtocol.create_agent_completed(
            agent_id,
            "success",
            "All phases completed",
            outputs={"total": 100},
        )

        assert msg.message_type == MessageType.AGENT_COMPLETED
        assert msg.payload["status"] == "success"
        assert msg.payload["result"] == "All phases completed"
        assert msg.payload["outputs"] == {"total": 100}

    def test_all_message_types_have_schemas(self):
        """Test that all MessageType constants have schemas."""
        protocol = CoordinationProtocol()

        message_types = [
            MessageType.AGENT_STARTED,
            MessageType.AGENT_COMPLETED,
            MessageType.AGENT_FAILED,
            MessageType.PHASE_STARTED,
            MessageType.PHASE_COMPLETED,
            MessageType.PHASE_FAILED,
            MessageType.DATA_AVAILABLE,
            MessageType.HELP_NEEDED,
            MessageType.STATUS_UPDATE,
            MessageType.HEARTBEAT,
        ]

        for msg_type in message_types:
            schema = protocol.get_schema(msg_type)
            assert schema is not None
            assert schema.message_type == msg_type
            assert len(schema.required_fields) > 0

    def test_message_broadcast(self):
        """Test creating broadcast message (to_agent=None)."""
        protocol = CoordinationProtocol()
        agent_id = uuid.uuid4()

        payload = {
            "agent_id": str(agent_id),
            "status": "running",
            "timestamp": datetime.utcnow().isoformat(),
        }

        msg = protocol.create_message(
            MessageType.STATUS_UPDATE,
            agent_id,
            payload,
            to_agent=None,  # Broadcast
        )

        assert msg.to_agent is None

    def test_message_directed(self):
        """Test creating directed message (to_agent specified)."""
        protocol = CoordinationProtocol()
        from_agent = uuid.uuid4()
        to_agent = uuid.uuid4()

        payload = {
            "agent_id": str(from_agent),
            "data_key": "test.data",
            "timestamp": datetime.utcnow().isoformat(),
        }

        msg = protocol.create_message(
            MessageType.DATA_AVAILABLE,
            from_agent,
            payload,
            to_agent=to_agent,
        )

        assert msg.to_agent == to_agent

    def test_phase_failed_message(self):
        """Test creating phase failed message."""
        agent_id = uuid.uuid4()

        payload = {
            "agent_id": str(agent_id),
            "phase_name": "analyze",
            "timestamp": datetime.utcnow().isoformat(),
            "error": "Database connection failed",
            "retry_count": 2,
            "will_retry": False,
        }

        msg = CoordinationProtocol.create_message(
            MessageType.PHASE_FAILED,
            agent_id,
            payload,
        )

        assert msg.message_type == MessageType.PHASE_FAILED
        assert msg.payload["error"] == "Database connection failed"
        assert msg.payload["will_retry"] is False

    def test_heartbeat_message(self):
        """Test creating heartbeat message."""
        agent_id = uuid.uuid4()

        payload = {
            "agent_id": str(agent_id),
            "timestamp": datetime.utcnow().isoformat(),
            "health_status": "healthy",
        }

        msg = CoordinationProtocol.create_message(
            MessageType.HEARTBEAT,
            agent_id,
            payload,
        )

        assert msg.message_type == MessageType.HEARTBEAT
        assert msg.payload["health_status"] == "healthy"

    def test_protocol_version(self):
        """Test that messages include protocol version."""
        protocol = CoordinationProtocol()
        agent_id = uuid.uuid4()

        payload = {
            "agent_id": str(agent_id),
            "agent_name": "test",
            "timestamp": datetime.utcnow().isoformat(),
        }

        msg = protocol.create_message(
            MessageType.AGENT_STARTED,
            agent_id,
            payload,
        )

        assert msg.protocol_version == "v1"

    def test_schema_descriptions(self):
        """Test that all schemas have descriptions."""
        protocol = CoordinationProtocol()

        for msg_type in protocol.list_message_types():
            schema = protocol.get_schema(msg_type)
            assert schema.description
            assert len(schema.description) > 0
