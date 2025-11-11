"""
CoordinationProtocol: Communication contracts between coordinated agents.

Defines message types, schema validation, and versioned protocol for
inter-agent communication in multi-agent systems.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from ..models import CoordinationMessage


# Protocol version
PROTOCOL_VERSION = "v1"


# Message type definitions
class MessageType:
    """Standard message types for agent coordination."""

    AGENT_STARTED = "AgentStarted"
    AGENT_COMPLETED = "AgentCompleted"
    AGENT_FAILED = "AgentFailed"
    PHASE_STARTED = "PhaseStarted"
    PHASE_COMPLETED = "PhaseCompleted"
    PHASE_FAILED = "PhaseFailed"
    DATA_AVAILABLE = "DataAvailable"
    HELP_NEEDED = "HelpNeeded"
    STATUS_UPDATE = "StatusUpdate"
    HEARTBEAT = "Heartbeat"


@dataclass
class MessageSchema:
    """Schema definition for message payload validation."""

    message_type: str
    required_fields: List[str]
    optional_fields: List[str]
    field_types: Dict[str, type]
    description: str


class CoordinationProtocol:
    """Protocol for coordinating communication between agents."""

    # Message schemas for validation
    SCHEMAS: Dict[str, MessageSchema] = {
        MessageType.AGENT_STARTED: MessageSchema(
            message_type=MessageType.AGENT_STARTED,
            required_fields=["agent_id", "agent_name", "timestamp"],
            optional_fields=["role", "capabilities"],
            field_types={
                "agent_id": str,
                "agent_name": str,
                "timestamp": str,
                "role": str,
                "capabilities": list,
            },
            description="Sent when agent starts execution",
        ),
        MessageType.AGENT_COMPLETED: MessageSchema(
            message_type=MessageType.AGENT_COMPLETED,
            required_fields=["agent_id", "timestamp", "status"],
            optional_fields=["result", "metrics", "outputs"],
            field_types={
                "agent_id": str,
                "timestamp": str,
                "status": str,
                "result": str,
                "metrics": dict,
                "outputs": dict,
            },
            description="Sent when agent completes successfully",
        ),
        MessageType.AGENT_FAILED: MessageSchema(
            message_type=MessageType.AGENT_FAILED,
            required_fields=["agent_id", "timestamp", "error"],
            optional_fields=["error_details", "recovery_possible"],
            field_types={
                "agent_id": str,
                "timestamp": str,
                "error": str,
                "error_details": dict,
                "recovery_possible": bool,
            },
            description="Sent when agent encounters unrecoverable error",
        ),
        MessageType.PHASE_STARTED: MessageSchema(
            message_type=MessageType.PHASE_STARTED,
            required_fields=["agent_id", "phase_name", "timestamp"],
            optional_fields=["phase_index", "total_phases"],
            field_types={
                "agent_id": str,
                "phase_name": str,
                "timestamp": str,
                "phase_index": int,
                "total_phases": int,
            },
            description="Sent when phase begins execution",
        ),
        MessageType.PHASE_COMPLETED: MessageSchema(
            message_type=MessageType.PHASE_COMPLETED,
            required_fields=["agent_id", "phase_name", "timestamp", "success"],
            optional_fields=["outputs", "duration_seconds", "metrics"],
            field_types={
                "agent_id": str,
                "phase_name": str,
                "timestamp": str,
                "success": bool,
                "outputs": dict,
                "duration_seconds": float,
                "metrics": dict,
            },
            description="Sent when phase completes",
        ),
        MessageType.PHASE_FAILED: MessageSchema(
            message_type=MessageType.PHASE_FAILED,
            required_fields=["agent_id", "phase_name", "timestamp", "error"],
            optional_fields=["retry_count", "will_retry"],
            field_types={
                "agent_id": str,
                "phase_name": str,
                "timestamp": str,
                "error": str,
                "retry_count": int,
                "will_retry": bool,
            },
            description="Sent when phase fails",
        ),
        MessageType.DATA_AVAILABLE: MessageSchema(
            message_type=MessageType.DATA_AVAILABLE,
            required_fields=["agent_id", "data_key", "timestamp"],
            optional_fields=["data_type", "data_size", "metadata"],
            field_types={
                "agent_id": str,
                "data_key": str,
                "timestamp": str,
                "data_type": str,
                "data_size": int,
                "metadata": dict,
            },
            description="Sent when data is available for other agents",
        ),
        MessageType.HELP_NEEDED: MessageSchema(
            message_type=MessageType.HELP_NEEDED,
            required_fields=["agent_id", "problem", "timestamp"],
            optional_fields=["severity", "context", "suggested_resolution"],
            field_types={
                "agent_id": str,
                "problem": str,
                "timestamp": str,
                "severity": str,
                "context": dict,
                "suggested_resolution": str,
            },
            description="Sent when agent needs assistance",
        ),
        MessageType.STATUS_UPDATE: MessageSchema(
            message_type=MessageType.STATUS_UPDATE,
            required_fields=["agent_id", "status", "timestamp"],
            optional_fields=["progress_percentage", "current_activity", "eta"],
            field_types={
                "agent_id": str,
                "status": str,
                "timestamp": str,
                "progress_percentage": float,
                "current_activity": str,
                "eta": str,
            },
            description="Sent periodically to update status",
        ),
        MessageType.HEARTBEAT: MessageSchema(
            message_type=MessageType.HEARTBEAT,
            required_fields=["agent_id", "timestamp"],
            optional_fields=["health_status"],
            field_types={
                "agent_id": str,
                "timestamp": str,
                "health_status": str,
            },
            description="Sent periodically to indicate agent is alive",
        ),
    }

    @classmethod
    def create_message(
        cls,
        message_type: str,
        from_agent: uuid.UUID,
        payload: Dict[str, Any],
        to_agent: Optional[uuid.UUID] = None,
    ) -> CoordinationMessage:
        """
        Create a coordination message with validation.

        Args:
            message_type: Type of message (use MessageType constants)
            from_agent: Sending agent ID
            payload: Message payload
            to_agent: Receiving agent ID (None for broadcast)

        Returns:
            Validated CoordinationMessage

        Raises:
            ValueError: If message fails validation

        Example:
            >>> protocol = CoordinationProtocol()
            >>> msg = protocol.create_message(
            ...     MessageType.PHASE_COMPLETED,
            ...     from_agent=uuid.uuid4(),
            ...     payload={
            ...         "agent_id": str(uuid.uuid4()),
            ...         "phase_name": "analyze",
            ...         "timestamp": datetime.utcnow().isoformat(),
            ...         "success": True
            ...     }
            ... )
            >>> assert msg.message_type == MessageType.PHASE_COMPLETED
        """
        # Validate message type
        if message_type not in cls.SCHEMAS:
            raise ValueError(f"Unknown message type: {message_type}")

        # Validate payload
        validation_result = cls.validate_payload(message_type, payload)
        if not validation_result["valid"]:
            raise ValueError(
                f"Invalid payload for {message_type}: {validation_result['errors']}"
            )

        # Create message
        return CoordinationMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload,
            timestamp=datetime.utcnow(),
            protocol_version=PROTOCOL_VERSION,
        )

    @classmethod
    def validate_payload(cls, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate message payload against schema.

        Args:
            message_type: Type of message
            payload: Payload to validate

        Returns:
            Dictionary with validation result:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str]
            }

        Example:
            >>> protocol = CoordinationProtocol()
            >>> result = protocol.validate_payload(
            ...     MessageType.AGENT_STARTED,
            ...     {"agent_id": "123", "agent_name": "test", "timestamp": "2024-01-01T00:00:00"}
            ... )
            >>> assert result["valid"] is True
        """
        if message_type not in cls.SCHEMAS:
            return {
                "valid": False,
                "errors": [f"Unknown message type: {message_type}"],
                "warnings": [],
            }

        schema = cls.SCHEMAS[message_type]
        errors: List[str] = []
        warnings: List[str] = []

        # Check required fields
        for field in schema.required_fields:
            if field not in payload:
                errors.append(f"Missing required field: {field}")

        # Check field types
        for field, value in payload.items():
            if field in schema.field_types:
                expected_type = schema.field_types[field]
                if not isinstance(value, expected_type):
                    errors.append(
                        f"Field '{field}' has wrong type: expected {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )

            # Warn about unknown fields
            if (
                field not in schema.required_fields
                and field not in schema.optional_fields
            ):
                warnings.append(f"Unknown field: {field}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    @classmethod
    def get_schema(cls, message_type: str) -> Optional[MessageSchema]:
        """
        Get schema for message type.

        Args:
            message_type: Type of message

        Returns:
            MessageSchema or None if type unknown

        Example:
            >>> protocol = CoordinationProtocol()
            >>> schema = protocol.get_schema(MessageType.PHASE_COMPLETED)
            >>> assert schema is not None
            >>> assert "phase_name" in schema.required_fields
        """
        return cls.SCHEMAS.get(message_type)

    @classmethod
    def list_message_types(cls) -> List[str]:
        """
        List all supported message types.

        Returns:
            List of message type names

        Example:
            >>> protocol = CoordinationProtocol()
            >>> types = protocol.list_message_types()
            >>> assert MessageType.AGENT_STARTED in types
        """
        return list(cls.SCHEMAS.keys())

    @classmethod
    def create_agent_started(
        cls,
        agent_id: uuid.UUID,
        agent_name: str,
        role: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
    ) -> CoordinationMessage:
        """
        Create AgentStarted message.

        Args:
            agent_id: Agent ID
            agent_name: Agent name
            role: Agent role (optional)
            capabilities: Agent capabilities (optional)

        Returns:
            CoordinationMessage

        Example:
            >>> msg = CoordinationProtocol.create_agent_started(
            ...     uuid.uuid4(), "data-processor", "worker", ["data-processing"]
            ... )
            >>> assert msg.message_type == MessageType.AGENT_STARTED
        """
        payload = {
            "agent_id": str(agent_id),
            "agent_name": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if role:
            payload["role"] = role
        if capabilities:
            payload["capabilities"] = capabilities

        return cls.create_message(MessageType.AGENT_STARTED, agent_id, payload)

    @classmethod
    def create_phase_completed(
        cls,
        agent_id: uuid.UUID,
        phase_name: str,
        success: bool,
        outputs: Optional[Dict[str, Any]] = None,
        duration_seconds: Optional[float] = None,
    ) -> CoordinationMessage:
        """
        Create PhaseCompleted message.

        Args:
            agent_id: Agent ID
            phase_name: Phase name
            success: Whether phase succeeded
            outputs: Phase outputs (optional)
            duration_seconds: Phase duration (optional)

        Returns:
            CoordinationMessage

        Example:
            >>> msg = CoordinationProtocol.create_phase_completed(
            ...     uuid.uuid4(), "analyze", True, {"result": "success"}
            ... )
            >>> assert msg.payload["success"] is True
        """
        payload = {
            "agent_id": str(agent_id),
            "phase_name": phase_name,
            "timestamp": datetime.utcnow().isoformat(),
            "success": success,
        }
        if outputs:
            payload["outputs"] = outputs
        if duration_seconds is not None:
            payload["duration_seconds"] = duration_seconds

        return cls.create_message(MessageType.PHASE_COMPLETED, agent_id, payload)

    @classmethod
    def create_data_available(
        cls,
        agent_id: uuid.UUID,
        data_key: str,
        data_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CoordinationMessage:
        """
        Create DataAvailable message.

        Args:
            agent_id: Agent ID
            data_key: Key where data is stored
            data_type: Type of data (optional)
            metadata: Additional metadata (optional)

        Returns:
            CoordinationMessage

        Example:
            >>> msg = CoordinationProtocol.create_data_available(
            ...     uuid.uuid4(), "phase.analyze.output", "dict"
            ... )
            >>> assert msg.payload["data_key"] == "phase.analyze.output"
        """
        payload = {
            "agent_id": str(agent_id),
            "data_key": data_key,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if data_type:
            payload["data_type"] = data_type
        if metadata:
            payload["metadata"] = metadata

        return cls.create_message(MessageType.DATA_AVAILABLE, agent_id, payload)

    @classmethod
    def create_help_needed(
        cls,
        agent_id: uuid.UUID,
        problem: str,
        severity: Literal["low", "medium", "high", "critical"] = "medium",
        context: Optional[Dict[str, Any]] = None,
    ) -> CoordinationMessage:
        """
        Create HelpNeeded message.

        Args:
            agent_id: Agent ID
            problem: Description of problem
            severity: Problem severity
            context: Additional context (optional)

        Returns:
            CoordinationMessage

        Example:
            >>> msg = CoordinationProtocol.create_help_needed(
            ...     uuid.uuid4(), "Cannot access database", "high"
            ... )
            >>> assert msg.payload["severity"] == "high"
        """
        payload = {
            "agent_id": str(agent_id),
            "problem": problem,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": severity,
        }
        if context:
            payload["context"] = context

        return cls.create_message(MessageType.HELP_NEEDED, agent_id, payload)

    @classmethod
    def create_agent_completed(
        cls,
        agent_id: uuid.UUID,
        status: Literal["success", "failed", "partial"] = "success",
        result: Optional[str] = None,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> CoordinationMessage:
        """
        Create AgentCompleted message.

        Args:
            agent_id: Agent ID
            status: Completion status
            result: Result description (optional)
            outputs: Agent outputs (optional)

        Returns:
            CoordinationMessage

        Example:
            >>> msg = CoordinationProtocol.create_agent_completed(
            ...     uuid.uuid4(), "success", "All phases completed"
            ... )
            >>> assert msg.payload["status"] == "success"
        """
        payload = {
            "agent_id": str(agent_id),
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
        }
        if result:
            payload["result"] = result
        if outputs:
            payload["outputs"] = outputs

        return cls.create_message(MessageType.AGENT_COMPLETED, agent_id, payload)
