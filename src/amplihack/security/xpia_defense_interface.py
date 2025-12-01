"""
XPIA Defense Agent Interface Specification

This module defines the core interface contracts for XPIA Defense integration
with the amplihack framework. Following the bricks & studs philosophy:

- Brick: Self-contained security validation module
- Stud: Public interface contracts for threat detection
- Regeneratable: Can be rebuilt from this specification
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class SecurityLevel(Enum):
    """Security validation levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    STRICT = "strict"


class RiskLevel(Enum):
    """Risk assessment levels"""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(Enum):
    """Types of security threats"""

    INJECTION = "injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    MALICIOUS_CODE = "malicious_code"
    SOCIAL_ENGINEERING = "social_engineering"
    RESOURCE_ABUSE = "resource_abuse"


class ContentType(Enum):
    """Content types for validation"""

    TEXT = "text"
    CODE = "code"
    COMMAND = "command"
    DATA = "data"
    USER_INPUT = "user_input"


@dataclass
class ValidationContext:
    """Context information for validation requests"""

    source: str  # "user", "agent", "system"
    session_id: str | None = None
    agent_id: str | None = None
    working_directory: str | None = None
    environment: dict[str, str] | None = None


@dataclass
class ThreatDetection:
    """Individual threat detection result"""

    threat_type: ThreatType
    severity: RiskLevel
    description: str
    location: dict[str, int] | None = None  # line, column, offset
    mitigation: str | None = None


@dataclass
class ValidationResult:
    """Result of security validation"""

    is_valid: bool
    risk_level: RiskLevel
    threats: list[ThreatDetection]
    recommendations: list[str]
    metadata: dict[str, Any]
    timestamp: datetime

    @property
    def should_block(self) -> bool:
        """Whether content should be blocked based on risk level"""
        return self.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    @property
    def should_alert(self) -> bool:
        """Whether an alert should be generated"""
        return self.risk_level != RiskLevel.NONE


@dataclass
class SecurityConfiguration:
    """XPIA Defense configuration settings"""

    security_level: SecurityLevel = SecurityLevel.MEDIUM
    enabled: bool = True

    # Rule configurations
    bash_validation: bool = True
    agent_communication: bool = True
    content_scanning: bool = True
    real_time_monitoring: bool = False

    # Threshold configurations
    block_threshold: RiskLevel = RiskLevel.HIGH
    alert_threshold: RiskLevel = RiskLevel.MEDIUM

    # Integration settings
    bash_tool_integration: bool = True
    agent_framework_integration: bool = True
    logging_enabled: bool = True


# Hook System Types
HookCallback = Callable[[dict[str, Any]], dict[str, Any]]


class HookType(Enum):
    """Types of security hooks"""

    PRE_VALIDATION = "pre_validation"
    POST_VALIDATION = "post_validation"
    THREAT_DETECTED = "threat_detected"
    CONFIG_CHANGED = "config_changed"


@dataclass
class HookRegistration:
    """Hook registration configuration"""

    name: str
    hook_type: HookType
    callback: str | HookCallback  # URL or function
    conditions: dict[str, Any] | None = None
    priority: int = 50


# Core Interface Contracts


class XPIADefenseInterface:
    """
    Core interface for XPIA Defense Agent

    This is the main "stud" - the stable contract that other modules connect to.
    All implementations must conform to this interface.
    """

    async def validate_content(
        self,
        content: str,
        content_type: ContentType,
        context: ValidationContext | None = None,
        security_level: SecurityLevel | None = None,
    ) -> ValidationResult:
        """
        Validate arbitrary content for security threats

        Args:
            content: Content to validate
            content_type: Type of content being validated
            context: Additional context for validation
            security_level: Override default security level

        Returns:
            ValidationResult with threat assessment
        """
        raise NotImplementedError

    async def validate_bash_command(
        self,
        command: str,
        arguments: list[str] | None = None,
        context: ValidationContext | None = None,
    ) -> ValidationResult:
        """
        Validate bash commands for security threats

        Args:
            command: Bash command to validate
            arguments: Command arguments
            context: Execution context

        Returns:
            ValidationResult with command safety assessment
        """
        raise NotImplementedError

    async def validate_agent_communication(
        self,
        source_agent: str,
        target_agent: str,
        message: dict[str, Any],
        message_type: str = "task",
    ) -> ValidationResult:
        """
        Validate inter-agent communication for security

        Args:
            source_agent: Source agent identifier
            target_agent: Target agent identifier
            message: Message payload
            message_type: Type of message

        Returns:
            ValidationResult with communication safety assessment
        """
        raise NotImplementedError

    def get_configuration(self) -> SecurityConfiguration:
        """Get current security configuration"""
        raise NotImplementedError

    async def update_configuration(self, config: SecurityConfiguration) -> bool:
        """Update security configuration"""
        raise NotImplementedError

    def register_hook(self, registration: HookRegistration) -> str:
        """Register a security hook, returns hook ID"""
        raise NotImplementedError

    def unregister_hook(self, hook_id: str) -> bool:
        """Unregister a security hook"""
        raise NotImplementedError

    async def health_check(self) -> dict[str, Any]:
        """Perform health check and return status"""
        raise NotImplementedError


class BashToolIntegration:
    """
    Integration interface for bash tool security

    This provides the specific contract for bash tool integration,
    following the decorator pattern for seamless integration.
    """

    def __init__(self, xpia_defense: XPIADefenseInterface):
        self.xpia_defense = xpia_defense

    async def secure_execute(
        self,
        command: str,
        arguments: list[str] | None = None,
        context: ValidationContext | None = None,
        bypass_validation: bool = False,
    ) -> "tuple[ValidationResult | None, Any | None]":
        """
        Execute bash command with security validation

        Args:
            command: Command to execute
            arguments: Command arguments
            context: Execution context
            bypass_validation: Skip validation (for emergency use)

        Returns:
            Tuple of (validation_result, execution_result)
            execution_result is None if validation failed
        """
        validation = None
        if not bypass_validation:
            validation = await self.xpia_defense.validate_bash_command(command, arguments, context)
            if validation.should_block:
                return validation, None

        # Execute command (implementation-specific)
        # This would integrate with the actual bash tool
        result = await self._execute_command(command, arguments, context)
        return validation, result

    async def _execute_command(
        self, command: str, arguments: list[str] | None, context: ValidationContext | None
    ) -> Any:
        """Implementation-specific command execution"""
        raise NotImplementedError


class AgentCommunicationSecurity:
    """
    Integration interface for agent communication security

    Provides security layer for inter-agent communications.
    """

    def __init__(self, xpia_defense: XPIADefenseInterface):
        self.xpia_defense = xpia_defense

    async def secure_send_message(
        self,
        source_agent: str,
        target_agent: str,
        message: dict[str, Any],
        message_type: str = "task",
    ) -> "tuple[ValidationResult, bool]":
        """
        Send message with security validation

        Returns:
            Tuple of (validation_result, message_sent)
        """
        validation = await self.xpia_defense.validate_agent_communication(
            source_agent, target_agent, message, message_type
        )

        if validation.should_block:
            return validation, False

        # Send message (implementation-specific)
        await self._send_message(source_agent, target_agent, message, message_type)
        return validation, True

    async def _send_message(
        self, source_agent: str, target_agent: str, message: dict[str, Any], message_type: str
    ) -> None:
        """Implementation-specific message sending"""
        raise NotImplementedError


# Utility Functions for Integration


def create_validation_context(
    source: str = "system",
    session_id: str | None = None,
    agent_id: str | None = None,
    **kwargs,
) -> ValidationContext:
    """Create a validation context with sensible defaults"""
    return ValidationContext(source=source, session_id=session_id, agent_id=agent_id, **kwargs)


def is_threat_critical(validation_result: ValidationResult) -> bool:
    """Check if validation result contains critical threats"""
    return any(threat.severity == RiskLevel.CRITICAL for threat in validation_result.threats)


def get_threat_summary(validation_result: ValidationResult) -> str:
    """Get human-readable threat summary"""
    if not validation_result.threats:
        return "No threats detected"

    threat_counts = {}
    for threat in validation_result.threats:
        threat_counts[threat.severity] = threat_counts.get(threat.severity, 0) + 1

    summary_parts = []
    for severity, count in threat_counts.items():
        summary_parts.append(f"{count} {severity.value}")

    return f"Threats detected: {', '.join(summary_parts)}"


# Exception Classes


class XPIADefenseError(Exception):
    """Base exception for XPIA Defense errors"""


class ValidationError(XPIADefenseError):
    """Error during validation process"""


class ConfigurationError(XPIADefenseError):
    """Error in security configuration"""


class HookError(XPIADefenseError):
    """Error in hook system"""


# Factory Functions


def create_default_configuration() -> SecurityConfiguration:
    """Create default security configuration"""
    return SecurityConfiguration()


async def create_xpia_defense_client(
    api_base_url: str, api_key: str | None = None, timeout: int = 30
) -> XPIADefenseInterface:
    """
    Factory function to create XPIA Defense client

    Args:
        api_base_url: Base URL for XPIA Defense API
        api_key: API key for authentication
        timeout: Request timeout in seconds

    Returns:
        XPIADefenseInterface implementation
    """
    # This would return a concrete implementation
    # e.g., HTTPXPIADefenseClient(api_base_url, api_key, timeout)
    raise NotImplementedError("Implementation-specific factory")


# Integration Helper Classes


class SecurityDecorator:
    """
    Decorator for adding security validation to functions

    Usage:
        @SecurityDecorator(xpia_defense, ContentType.CODE)
        def process_code(code: str) -> str:
            # Process code
            return processed_code
    """

    def __init__(
        self,
        xpia_defense: XPIADefenseInterface,
        content_type: ContentType,
        security_level: SecurityLevel | None = None,
    ):
        self.xpia_defense = xpia_defense
        self.content_type = content_type
        self.security_level = security_level

    def __call__(self, func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Extract content to validate (implementation-specific)
            content = self._extract_content(args, kwargs)

            validation = await self.xpia_defense.validate_content(
                content, self.content_type, security_level=self.security_level
            )

            if validation.should_block:
                raise ValidationError(f"Content blocked: {get_threat_summary(validation)}")

            return await func(*args, **kwargs)

        return wrapper

    def _extract_content(self, args: tuple, kwargs: dict) -> str:
        """Extract content from function arguments"""
        # Implementation-specific content extraction
        raise NotImplementedError


class SecurityMiddleware:
    """
    Middleware for request/response security validation

    Can be integrated into web frameworks or agent communication layers.
    """

    def __init__(self, xpia_defense: XPIADefenseInterface):
        self.xpia_defense = xpia_defense

    async def process_request(self, request: dict[str, Any]) -> ValidationResult | None:
        """
        Process incoming request for security validation

        Returns None if request should proceed, ValidationResult if blocked
        """
        content = self._extract_request_content(request)
        if not content:
            return None

        validation = await self.xpia_defense.validate_content(content, ContentType.USER_INPUT)

        return validation if validation.should_block else None

    def _extract_request_content(self, request: dict[str, Any]) -> str | None:
        """Extract content from request"""
        # Implementation-specific content extraction
        return request.get("content")
