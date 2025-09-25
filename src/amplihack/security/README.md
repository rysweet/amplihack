# XPIA Defense System

Cross-Prompt Injection Attack (XPIA) defense system for amplihack, providing comprehensive security validation for WebFetch and other tool operations.

## Overview

The XPIA Defense System protects against prompt injection attacks, command injection, data exfiltration attempts, and other security threats in AI-assisted development workflows. It integrates seamlessly with Claude Code's hook system to provide real-time security validation.

## Features

- **Comprehensive Pattern Detection**: 15+ attack pattern categories with 40+ specific patterns
- **WebFetch Security**: Specialized validation for URL and prompt combinations
- **Bash Command Validation**: Protection against dangerous commands and injection attempts
- **Configurable Security Levels**: STRICT, HIGH, MODERATE, LENIENT, LOW
- **Claude Code Hook Integration**: Seamless PreToolUse and PostToolUse validation
- **Domain Whitelist/Blacklist**: Customizable URL filtering
- **Rich CLI Interface**: Interactive validation testing and configuration

## Installation

The XPIA Defense System is included with amplihack. No additional installation required.

## Quick Start

### Environment Configuration

Set up your security preferences via environment variables:

```bash
# Enable XPIA Defense
export XPIA_ENABLED=true

# Set security level (STRICT, HIGH, MODERATE, LENIENT, LOW)
export XPIA_SECURITY_LEVEL=MODERATE

# Configure blocking behavior
export XPIA_BLOCK_HIGH_RISK=true
export XPIA_BLOCK_CRITICAL=true

# Enable verbose feedback
export XPIA_VERBOSE_FEEDBACK=false
```

### Basic Usage

#### CLI Validation

```bash
# Validate a WebFetch request
amplihack xpia validate --url "https://example.com" --prompt "Get data"

# Validate a Bash command
amplihack xpia validate-bash --command "ls -la"

# Check system health
amplihack xpia health

# View current configuration
amplihack xpia config

# List all attack patterns
amplihack xpia patterns
```

#### Python Integration

```python
from amplihack.security import WebFetchXPIADefender

# Create defender instance
defender = WebFetchXPIADefender()

# Validate WebFetch request
result = await defender.validate_webfetch_request(
    url="https://example.com",
    prompt="Fetch and process data"
)

if result.is_valid:
    print(f"Request is safe (Risk: {result.risk_level.value})")
else:
    print(f"Request blocked: {result.risk_level.value}")
    for threat in result.threats:
        print(f"  - {threat.description}")
```

#### Hook Integration

The XPIA system automatically integrates with Claude Code's hook system:

```python
from amplihack.security import xpia_hook

# Hooks are automatically registered when imported
# They intercept WebFetch and Bash tool calls

# Manual validation through hooks
context = {
    "tool_name": "WebFetch",
    "parameters": {
        "url": "https://github.com",
        "prompt": "Get repository data"
    }
}

result = xpia_hook.pre_tool_use(context)
if result["allow"]:
    # Proceed with tool execution
    pass
else:
    print(f"Blocked: {result['message']}")
```

## Security Levels

### STRICT

- Blocks all suspicious patterns
- Flags encoding attempts
- Restricts to whitelisted domains only
- Recommended for production environments

### HIGH

- Blocks high and critical threats
- Allows moderate risks with warnings
- Suitable for staging environments

### MODERATE (Default)

- Balanced security and usability
- Blocks critical threats
- Warns on high risks
- Recommended for development

### LENIENT/LOW

- Minimal restrictions
- Only blocks critical security threats
- Suitable for testing and experimentation

## Attack Pattern Categories

1. **Prompt Override**: Attempts to ignore or override previous instructions
2. **Instruction Injection**: System prompt or assistant role injection
3. **Context Manipulation**: Hidden instructions, context overflow
4. **Data Exfiltration**: Credential requests, file access attempts
5. **System Escape**: Command injection, path traversal
6. **Role Hijacking**: Jailbreak attempts, role reversal
7. **Encoding Bypass**: Base64, Unicode encoding attempts
8. **Chain Attacks**: Multi-stage attack sequences

## Configuration

### Environment Variables

```bash
# Core Settings
XPIA_ENABLED=true                    # Enable/disable XPIA
XPIA_SECURITY_LEVEL=MODERATE         # Security level
XPIA_VERBOSE_FEEDBACK=false          # Detailed error messages

# Blocking Thresholds
XPIA_BLOCK_HIGH_RISK=true           # Block high risk requests
XPIA_BLOCK_CRITICAL=true            # Block critical threats

# Feature Flags
XPIA_VALIDATE_WEBFETCH=true         # Validate WebFetch calls
XPIA_VALIDATE_BASH=true             # Validate Bash commands
XPIA_VALIDATE_AGENTS=true           # Validate agent communication

# Logging
XPIA_LOG_EVENTS=true                # Log security events
XPIA_LOG_FILE=/var/log/xpia.log     # Log file path

# Domain Lists
XPIA_WHITELIST_DOMAINS=github.com,microsoft.com
XPIA_BLACKLIST_DOMAINS=malware.com,phishing.net
XPIA_WHITELIST_FILE=.xpia_whitelist
XPIA_BLACKLIST_FILE=.xpia_blacklist

# Limits
XPIA_MAX_PROMPT_LENGTH=10000        # Maximum prompt length
XPIA_MAX_URL_LENGTH=2048            # Maximum URL length
```

### Domain Lists

Create `.xpia_whitelist` and `.xpia_blacklist` files:

```
# .xpia_whitelist
github.com
microsoft.com
stackoverflow.com
python.org

# .xpia_blacklist
malware.com
phishing.net
suspicious-site.tk
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/test_xpia_defender.py tests/test_xpia_hooks.py -v

# Run specific test categories
pytest tests/test_xpia_defender.py::TestXPIADefender -v
pytest tests/test_xpia_hooks.py::TestIntegrationScenarios -v
```

## Examples

See `examples/webfetch_integration.py` for comprehensive examples:

```python
# Run examples
python src/amplihack/security/examples/webfetch_integration.py
```

## Architecture

```
XPIA Defense System
├── xpia_defender.py       # Core validation logic
├── xpia_patterns.py       # Attack pattern definitions
├── xpia_hooks.py          # Claude Code hook integration
├── config.py              # Configuration management
├── cli.py                 # CLI commands
└── examples/              # Integration examples
```

## Security Best Practices

1. **Start with MODERATE**: Begin with moderate security and adjust based on needs
2. **Review Logs**: Regularly review security events to identify patterns
3. **Maintain Lists**: Keep whitelist/blacklist updated
4. **Test Thoroughly**: Validate security settings don't block legitimate operations
5. **Monitor Performance**: Track validation times and adjust patterns if needed

## Troubleshooting

### Request Blocked Unexpectedly

1. Check security level: `amplihack xpia config`
2. Review specific patterns: `amplihack xpia patterns`
3. Test with verbose output: `--verbose` flag
4. Consider adding to whitelist if domain is trusted

### Performance Issues

1. Reduce pattern complexity in LENIENT mode
2. Disable unused validation features
3. Use async validation for batch operations

### False Positives

1. Adjust security level
2. Whitelist trusted domains
3. Report patterns for refinement

## API Reference

### WebFetchXPIADefender

```python
class WebFetchXPIADefender:
    async def validate_webfetch_request(
        url: str,
        prompt: str,
        context: Optional[ValidationContext] = None
    ) -> ValidationResult
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    is_valid: bool              # Whether request should proceed
    risk_level: RiskLevel       # NONE, LOW, MEDIUM, HIGH, CRITICAL
    threats: List[ThreatDetection]  # Detected threats
    recommendations: List[str]  # Security recommendations
    metadata: Dict[str, Any]    # Additional information
```

### ClaudeCodeXPIAHook

```python
class ClaudeCodeXPIAHook:
    def pre_tool_use(context: Dict[str, Any]) -> Dict[str, Any]
    def post_tool_use(context: Dict[str, Any]) -> Dict[str, Any]
    def get_stats() -> Dict[str, Any]
```

## Contributing

To add new attack patterns:

1. Add pattern to `xpia_patterns.py`
2. Include test cases in `test_xpia_defender.py`
3. Update documentation

## License

Part of the amplihack framework - see main LICENSE file.

## Support

For issues or questions:

- Check examples in `examples/webfetch_integration.py`
- Review test cases for usage patterns
- Consult CLI help: `amplihack xpia --help`
