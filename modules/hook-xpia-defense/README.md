# XPIA Defense Hook

Cross-Prompt Injection Attack (XPIA) defense hook for Amplifier.

## Overview

This hook monitors tool calls and user prompts for potential prompt injection attacks. It provides real-time detection of common injection patterns with configurable response actions.

## Installation

```bash
# As part of amplifier-amplihack bundle
amplifier module add hook-xpia-defense --type hook

# Or install directly
pip install -e ./modules/hook-xpia-defense
```

## Usage

### In Bundle Configuration

```yaml
modules:
  hooks:
    - module: hook-xpia-defense
      config:
        mode: standard  # standard, strict, or learning
        block_on_critical: true
        log_all: false
```

### Programmatic Usage

```python
from hook_xpia_defense import XPIADefenseHook, HookResult

hook = XPIADefenseHook(config={"mode": "standard"})

# Check a tool call
result = hook("tool:call:before", {"input": {"command": "rm -rf /"}})
if result.should_block:
    print(f"Blocked: {result.message}")

# Check a user prompt
result = hook("prompt:submit:before", {"content": "Ignore previous instructions"})
if result.should_warn:
    print(f"Warning: {result.message}")
```

## Operating Modes

| Mode | Critical | High | Medium | Low |
|------|----------|------|--------|-----|
| **standard** | Block | Warn | Warn | Allow |
| **strict** | Block | Block | Warn | Allow |
| **learning** | Warn | Warn | Warn | Warn |

## Threat Categories

### System Override (Critical)
- "ignore previous instructions"
- "forget everything above"
- "disregard all prompts"
- "new system instructions:"

### Role Manipulation (High)
- "you are now a..."
- "act as a..."
- "pretend to be..."

### Data Exfiltration (High/Critical)
- "reveal your system prompt"
- "show your instructions"
- "tell me your API keys"

### Command Injection (Critical)
- `rm -rf /`
- `curl ... | bash`
- `wget ... | sh`

### Security Bypass (Medium)
- "bypass security checks"
- "disable validation"
- "ignore safety filters"

## Hook Events

This hook registers for:
- `tool:call:before` - Checks tool inputs before execution
- `prompt:submit:before` - Checks user prompts before processing

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `mode` | string | "standard" | Operating mode |
| `block_on_critical` | bool | true | Whether to block critical threats |
| `log_all` | bool | false | Log all checks, not just threats |

## HookResult Structure

```python
@dataclass
class HookResult:
    action: HookAction      # allow, warn, or block
    message: str            # Human-readable summary
    threats: list[ThreatMatch]  # Detected threats
    metadata: dict          # Additional context
```

## Performance

- Detection latency: <10ms typical
- Zero external dependencies
- Compiled regex patterns for efficiency

## License

MIT
