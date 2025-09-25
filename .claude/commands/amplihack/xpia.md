# XPIA Security Command

XPIA (Cross-Platform Injection Attack) Defense system management and health monitoring.

## Usage

When you run `/amplihack:xpia [subcommand]`, the system will execute the corresponding XPIA operation.

## Available Subcommands

### health

Check XPIA security system health and configuration status.

**Usage**: `/amplihack:xpia health [--verbose]`

**What it does**:

- Checks if XPIA hooks are configured in settings.json
- Verifies XPIA hook files exist and are executable
- Tests XPIA log directory permissions
- Validates XPIA modules are importable
- Provides recommendations for fixing issues

**Example output**:

```
XPIA Security Health Check
==================================================
Overall Status: ✅ Healthy
Timestamp: 2025-01-23T10:30:45

Summary: 7/7 checks passed
```

### status

Show current XPIA security configuration and recent activity.

**Usage**: `/amplihack:xpia status`

**What it does**:

- Shows XPIA hook configuration status
- Displays recent security events from logs
- Reports threat detection statistics
- Shows current security level settings

### logs

Display XPIA security logs and threat detection history.

**Usage**: `/amplihack:xpia logs [--lines=50] [--today]`

**Options**:

- `--lines=N`: Show last N log entries (default: 50)
- `--today`: Show only today's logs
- `--threats`: Show only threat detections

### test

Run XPIA security system validation tests.

**Usage**: `/amplihack:xpia test`

**What it does**:

- Runs comprehensive XPIA security tests
- Validates threat detection capabilities
- Tests hook integration functionality
- Verifies performance requirements

## Implementation

When you use any of these commands, execute the following:

```bash
# For health check
python3 ~/.claude/src/amplihack/security/xpia_health.py --verbose

# For status check
python3 ~/.claude/tools/xpia/xpia_status.py

# For logs
python3 ~/.claude/tools/xpia/xpia_logs.py --lines=50

# For testing
python3 ~/.claude/tests/run_xpia_tests.py
```

## Security Features

XPIA Defense provides protection against:

1. **Prompt Injection Attacks** - System prompt override attempts
2. **Command Injection** - Malicious bash command execution
3. **Privilege Escalation** - Unauthorized permission elevation
4. **Data Exfiltration** - Attempts to extract sensitive information
5. **Resource Abuse** - Destructive or resource-intensive operations

## Hook Integration Points

XPIA security is integrated at these points:

- **SessionStart**: Initialize security monitoring
- **PreToolUse**: Validate commands before execution (Bash tool)
- **PostToolUse**: Monitor command results and log security events

## Troubleshooting

Common issues and solutions:

### "XPIA hooks not configured"

**Solution**: Re-run the installation with XPIA support:

```bash
~/.claude/tools/amplihack/install_with_xpia.sh
```

### "Hook files not executable"

**Solution**: Fix permissions:

```bash
chmod +x ~/.claude/tools/xpia/hooks/*.py
```

### "Log directory not writable"

**Solution**: Create and fix permissions:

```bash
mkdir -p ~/.claude/logs/xpia
chmod 755 ~/.claude/logs/xpia
```

### "XPIA modules not importable"

**Solution**: Verify installation includes Specs directory:

```bash
ls -la ~/.claude/Specs/xpia_defense_interface.py
```

## Configuration

XPIA security level can be configured in `~/.claude/config/xpia_security.yaml`:

```yaml
xpia_defense:
  security_level: medium # low, medium, high, strict
  block_threshold: high # none, low, medium, high, critical
  log_level: info # debug, info, warning, error

  validation_rules:
    bash_commands: true
    agent_communication: true
    content_scanning: true
```

## Security Levels

- **Low**: Basic threat detection, warnings only
- **Medium**: Standard protection, blocks high-risk operations
- **High**: Enhanced security, blocks medium and high-risk operations
- **Strict**: Maximum security, blocks all suspicious activity

## Log Location

XPIA security logs are stored in:

- `~/.claude/logs/xpia/security_YYYYMMDD.log` - Daily security event logs
- `~/.claude/logs/xpia/threats_YYYYMMDD.log` - Threat detection logs
- `~/.claude/logs/xpia/health_checks.log` - Health check history

## Integration with UVX

XPIA hooks are automatically configured during UVX installation when using the enhanced install script. The system is designed to work seamlessly with both local and UVX deployments.
