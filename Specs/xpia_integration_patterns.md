# XPIA Defense Integration Patterns

## Overview

This document defines integration patterns for XPIA Defense Agent within the amplihack framework, following the bricks & studs philosophy.

## Core Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Amplihack Framework                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Bash Tool   │  │ Agent Comm  │  │ User Input Handler  │  │
│  │             │  │             │  │                     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────────────┘  │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          │                                  │
├─────────────────────────┼─────────────────────────────────┤
│                         │                                  │
│      ┌─────────────────┼─────────────────────────────────┐ │
│      │                 ▼             XPIA Defense        │ │
│      │  ┌──────────────────────────────────────────────┐ │ │
│      │  │            Validation Engine                 │ │ │
│      │  │  ┌─────────┐ ┌─────────┐ ┌─────────────────┐ │ │ │
│      │  │  │ Content │ │  Bash   │ │ Agent Messages  │ │ │ │
│      │  │  │Validator│ │Validator│ │   Validator     │ │ │ │
│      │  │  └─────────┘ └─────────┘ └─────────────────┘ │ │ │
│      │  └──────────────────────────────────────────────┘ │ │
│      │  ┌──────────────────────────────────────────────┐ │ │
│      │  │              Hook System                     │ │ │
│      │  │  ┌─────────┐ ┌─────────┐ ┌─────────────────┐ │ │ │
│      │  │  │   Pre   │ │  Post   │ │     Threat      │ │ │ │
│      │  │  │  Hooks  │ │  Hooks  │ │   Detection     │ │ │ │
│      │  │  └─────────┘ └─────────┘ └─────────────────┘ │ │ │
│      │  └──────────────────────────────────────────────┘ │ │
│      │  ┌──────────────────────────────────────────────┐ │ │
│      │  │           Configuration Engine               │ │ │
│      │  │    ┌─────────────┐  ┌─────────────────────┐  │ │ │
│      │  │    │ Security    │  │ Runtime Settings    │  │ │ │
│      │  │    │ Policies    │  │ & Thresholds        │  │ │ │
│      │  │    └─────────────┘  └─────────────────────┘  │ │ │
│      │  └──────────────────────────────────────────────┘ │ │
│      └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Integration Pattern 1: Bash Tool Security Wrapper

### Pattern Description

Seamlessly integrate security validation into bash command execution without breaking existing interfaces.

### Implementation

```python
# Current bash tool usage
result = bash_tool.execute("rm -rf /tmp/data")

# With XPIA Defense integration
from xpia_defense import BashToolIntegration

secure_bash = BashToolIntegration(xpia_defense_client)
validation, result = await secure_bash.secure_execute("rm -rf /tmp/data")

if validation.should_block:
    print(f"Command blocked: {validation.risk_level}")
    for threat in validation.threats:
        print(f"  - {threat.description}")
else:
    print(f"Command executed safely: {result}")
```

### Configuration

```yaml
# .claude/config/xpia_bash.yaml
bash_integration:
  enabled: true
  security_level: medium
  block_threshold: high
  allowed_commands:
    - ls
    - cat
    - grep
  blocked_patterns:
    - "rm -rf /"
    - "chmod 777"
    - "sudo"
  validation_timeout: 5000 # milliseconds
```

## Integration Pattern 2: Agent Communication Security

### Pattern Description

Validate inter-agent communications to prevent malicious message injection or information leakage.

### Implementation

```python
# Agent-to-agent message sending
from xpia_defense import AgentCommunicationSecurity

secure_comm = AgentCommunicationSecurity(xpia_defense_client)

message = {
    "task": "analyze_code",
    "parameters": {"file_path": "/secure/data.py"},
    "priority": "high"
}

validation, sent = await secure_comm.secure_send_message(
    source_agent="orchestrator",
    target_agent="code_analyzer",
    message=message,
    message_type="task"
)

if not sent:
    logger.warning(f"Message blocked: {validation.risk_level}")
```

### Hook Integration

```python
# Register hook for threat detection
def threat_alert_hook(event_data):
    threat_info = event_data["validation_result"]
    if threat_info.risk_level == RiskLevel.CRITICAL:
        # Alert security team
        send_alert(f"Critical threat detected: {threat_info.threats}")
    return {"action": "log_and_continue"}

hook_id = xpia_defense.register_hook(HookRegistration(
    name="critical_threat_alert",
    hook_type=HookType.THREAT_DETECTED,
    callback=threat_alert_hook,
    conditions={"risk_levels": ["critical"]},
    priority=100
))
```

## Integration Pattern 3: Decorator-Based Security

### Pattern Description

Apply security validation transparently using decorators for existing functions.

### Implementation

```python
from xpia_defense import SecurityDecorator

@SecurityDecorator(xpia_defense_client, ContentType.CODE)
async def process_user_code(code: str) -> str:
    """Process user-submitted code with automatic security validation"""
    # Code processing logic here
    return processed_code

# Usage - validation happens automatically
try:
    result = await process_user_code(user_submitted_code)
except ValidationError as e:
    print(f"Code rejected: {e}")
```

## Integration Pattern 4: Middleware Security Layer

### Pattern Description

Add security validation as middleware in request/response processing pipelines.

### Implementation

```python
from xpia_defense import SecurityMiddleware

class AmplihackSecurityMiddleware:
    def __init__(self, xpia_defense: XPIADefenseInterface):
        self.security = SecurityMiddleware(xpia_defense)

    async def process_user_input(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        # Validate user input
        validation = await self.security.process_request(user_input)

        if validation and validation.should_block:
            return {
                "error": "Input blocked for security reasons",
                "risk_level": validation.risk_level.value,
                "threats": [t.description for t in validation.threats]
            }

        # Process input normally
        return await self._process_input(user_input)
```

## Integration Pattern 5: Configuration-Driven Security

### Pattern Description

Use configuration files to define security policies without code changes.

### Configuration Structure

```yaml
# .claude/config/xpia_security.yaml
xpia_defense:
  global:
    security_level: medium
    enabled: true

  validation_rules:
    bash_commands:
      enabled: true
      block_threshold: high
      patterns:
        dangerous:
          - "rm -rf /"
          - "chmod 777"
          - "sudo rm"
        suspicious:
          - "curl.*|.*sh"
          - "wget.*|.*sh"

    agent_communication:
      enabled: true
      validate_payloads: true
      max_message_size: 1048576 # 1MB

    content_validation:
      enabled: true
      scan_code: true
      scan_data: true
      max_content_size: 10485760 # 10MB

  thresholds:
    block_threshold: high
    alert_threshold: medium

  integrations:
    bash_tool: true
    agent_framework: true
    logging: true

  hooks:
    - name: "security_logger"
      type: "threat_detected"
      endpoint: "http://localhost:8080/security/alerts"
      conditions:
        risk_levels: ["medium", "high", "critical"]
```

## Integration Pattern 6: Emergency Bypass System

### Pattern Description

Provide emergency bypass mechanisms for critical operations while maintaining audit trail.

### Implementation

```python
# Emergency bypass with justification
emergency_context = ValidationContext(
    source="admin",
    session_id="emergency_2023_12_01",
    agent_id="system_recovery"
)

validation, result = await secure_bash.secure_execute(
    "sudo systemctl restart critical_service",
    bypass_validation=True,  # Emergency bypass
    context=emergency_context
)

# Log emergency bypass
logger.critical(f"Emergency bypass used: {emergency_context.session_id}")
```

## Integration Pattern 7: Real-time Monitoring Integration

### Pattern Description

Integrate with monitoring systems for real-time threat detection and response.

### Implementation

```python
class XPIAMonitoringIntegration:
    def __init__(self, xpia_defense: XPIADefenseInterface, metrics_client):
        self.xpia_defense = xpia_defense
        self.metrics = metrics_client

        # Register monitoring hooks
        self._register_monitoring_hooks()

    def _register_monitoring_hooks(self):
        # Metrics collection hook
        self.xpia_defense.register_hook(HookRegistration(
            name="metrics_collector",
            hook_type=HookType.POST_VALIDATION,
            callback=self._collect_metrics,
            priority=10
        ))

        # Threat alerting hook
        self.xpia_defense.register_hook(HookRegistration(
            name="threat_alerter",
            hook_type=HookType.THREAT_DETECTED,
            callback=self._send_alert,
            conditions={"risk_levels": ["high", "critical"]},
            priority=90
        ))

    def _collect_metrics(self, event_data):
        validation = event_data["validation_result"]
        self.metrics.increment("xpia.validations.total")
        self.metrics.increment(f"xpia.validations.{validation.risk_level.value}")

        if validation.threats:
            for threat in validation.threats:
                self.metrics.increment(f"xpia.threats.{threat.threat_type.value}")

    def _send_alert(self, event_data):
        validation = event_data["validation_result"]
        alert = {
            "timestamp": validation.timestamp.isoformat(),
            "risk_level": validation.risk_level.value,
            "threats": [t.description for t in validation.threats],
            "content_type": event_data.get("content_type", "unknown")
        }
        self.metrics.send_alert("xpia_threat_detected", alert)
```

## Integration Pattern 8: Testing and Validation

### Pattern Description

Comprehensive testing patterns for XPIA Defense integration.

### Test Structure

```python
import pytest
from xpia_defense import create_xpia_defense_client, ValidationContext

class TestXPIAIntegration:
    @pytest.fixture
    async def xpia_client(self):
        return await create_xpia_defense_client("http://test-api:8080")

    async def test_bash_command_validation(self, xpia_client):
        # Test safe command
        result = await xpia_client.validate_bash_command("ls -la")
        assert result.is_valid
        assert result.risk_level == RiskLevel.NONE

        # Test dangerous command
        result = await xpia_client.validate_bash_command("rm -rf /")
        assert not result.is_valid
        assert result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert any(t.threat_type == ThreatType.RESOURCE_ABUSE for t in result.threats)

    async def test_agent_communication_validation(self, xpia_client):
        safe_message = {"task": "analyze", "file": "test.py"}
        result = await xpia_client.validate_agent_communication(
            "orchestrator", "analyzer", safe_message
        )
        assert result.is_valid

        # Test suspicious message
        suspicious_message = {"task": "execute", "command": "rm -rf /"}
        result = await xpia_client.validate_agent_communication(
            "orchestrator", "executor", suspicious_message
        )
        assert not result.is_valid or result.risk_level != RiskLevel.NONE

    async def test_configuration_management(self, xpia_client):
        config = xpia_client.get_configuration()
        assert isinstance(config, SecurityConfiguration)

        # Update configuration
        new_config = SecurityConfiguration(security_level=SecurityLevel.STRICT)
        success = await xpia_client.update_configuration(new_config)
        assert success

        updated_config = xpia_client.get_configuration()
        assert updated_config.security_level == SecurityLevel.STRICT
```

## Best Practices

### 1. Graceful Degradation

- Always provide fallback behavior when XPIA Defense is unavailable
- Log security events even when validation is bypassed
- Maintain system functionality during security service outages

### 2. Performance Considerations

- Cache validation results for identical content
- Use async/await for non-blocking validation
- Implement timeout mechanisms for validation requests
- Consider validation result TTL for repeated operations

### 3. Security Configuration

- Use environment-specific security levels
- Regularly review and update threat patterns
- Implement security policy versioning
- Maintain audit trails for all security decisions

### 4. Error Handling

- Distinguish between validation failures and system errors
- Provide meaningful error messages for blocked content
- Implement retry mechanisms for transient failures
- Log all security events for analysis

### 5. Integration Testing

- Test all integration points regularly
- Validate security policy effectiveness
- Monitor false positive/negative rates
- Conduct security integration reviews

## Security Considerations

1. **API Authentication**: All XPIA Defense API calls must be authenticated
2. **Transport Security**: Use TLS for all communications
3. **Input Sanitization**: Validate all inputs to XPIA Defense
4. **Audit Logging**: Log all security decisions and bypass operations
5. **Configuration Security**: Protect security configuration files
6. **Emergency Procedures**: Maintain documented emergency bypass procedures

## Deployment Patterns

### Development Environment

```yaml
xpia_defense:
  security_level: low
  enabled: true
  real_time_monitoring: false
  block_threshold: critical
```

### Staging Environment

```yaml
xpia_defense:
  security_level: medium
  enabled: true
  real_time_monitoring: true
  block_threshold: high
```

### Production Environment

```yaml
xpia_defense:
  security_level: high
  enabled: true
  real_time_monitoring: true
  block_threshold: medium
  emergency_bypass_enabled: true
```

This integration pattern ensures seamless security without disrupting the amplihack framework's core functionality while providing comprehensive threat protection.
