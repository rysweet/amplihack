# Control Mechanisms

## Purpose

Define all ways to enable/disable power-steering mode.

## Three-Layer Control System

### Layer 1: Configuration File (Persistent)

- **File**: `~/.amplihack/.claude/tools/amplihack/.power_steering_config`
- **Format**: JSON
- **Scope**: Project-wide, persists across sessions
- **Priority**: Lowest (overridden by env var and semaphore)

### Layer 2: Environment Variable (Session)

- **Variable**: `AMPLIHACK_SKIP_POWER_STEERING`
- **Values**: Any non-empty value disables
- **Scope**: Current session only
- **Priority**: Medium (overrides config, overridden by semaphore)

### Layer 3: Semaphore File (Runtime)

- **File**: `~/.amplihack/.claude/runtime/power-steering/.disabled`
- **Format**: Empty file (existence check only)
- **Scope**: Project-wide, persists until removed
- **Priority**: Highest (overrides everything)

## Slash Commands

### /amplihack:disable-power-steering

**Purpose**: Disable power-steering by creating semaphore file

**Implementation**:

```markdown
---
description: Disable power-steering mode for session stop checks
---

Disabling power-steering mode...

This will create a semaphore file that prevents power-steering from running on session stops.
```

**Action**: Create `~/.amplihack/.claude/runtime/power-steering/.disabled` file

**Code** (Claude Code handles via simple Write tool):

```python
disabled_file = Path(".claude/runtime/power-steering/.disabled")
disabled_file.parent.mkdir(parents=True, exist_ok=True)
disabled_file.touch()
```

### /amplihack:enable-power-steering

**Purpose**: Enable power-steering by removing semaphore file

**Implementation**:

```markdown
---
description: Enable power-steering mode for session stop checks
---

Enabling power-steering mode...

This will remove the semaphore file that disables power-steering.
```

**Action**: Remove `~/.amplihack/.claude/runtime/power-steering/.disabled` file

**Code** (Claude Code handles via simple Bash tool):

```python
disabled_file = Path(".claude/runtime/power-steering/.disabled")
if disabled_file.exists():
    disabled_file.unlink()
```

### /amplihack:power-steering-status

**Purpose**: Show current power-steering status and configuration

**Implementation**:

```markdown
---
description: Show power-steering mode status and configuration
---

Checking power-steering status...

Please display:

1. Current enabled/disabled state
2. Which control mechanism is active (config/env/semaphore)
3. Configuration values
4. Statistics (if available):
   - Times blocked
   - Times approved
   - Times skipped
```

**Output Example**:

```
Power-Steering Status
=====================

Status: DISABLED (via semaphore file)

Control Mechanisms:
  • Semaphore: .claude/runtime/power-steering/.disabled EXISTS ❌
  • Environment: AMPLIHACK_SKIP_POWER_STEERING not set ✓
  • Config: {"enabled": true} ✓

Configuration:
  • enabled: true
  • skip_qa_sessions: true
  • timeout_seconds: 30
  • summary_enabled: true

Statistics (last 30 days):
  • Blocked: 12
  • Approved: 45
  • Skipped (Q&A): 8
  • Errors: 0

To enable power-steering, run: /amplihack:enable-power-steering
```

## CLI Flag Integration

### Option A: New Claude Code CLI flag

**Flag**: `--no-power-steering`

**Usage**:

```bash
claude --no-power-steering
claude code --no-power-steering
```

**Implementation**:
Sets environment variable before starting session:

```python
if args.no_power_steering:
    os.environ["AMPLIHACK_SKIP_POWER_STEERING"] = "1"
```

**Location**: Modify Claude Code CLI argument parser (if we have access)

### Option B: Environment variable (if CLI modification not possible)

**Usage**:

```bash
AMPLIHACK_SKIP_POWER_STEERING=1 claude
```

**Note**: This is already supported by reading environment variable in stop.py

## Configuration File Management

### Reading Config

```python
def load_config() -> Dict:
    """Load power-steering config with defaults."""
    config_path = Path(".claude/tools/amplihack/.power_steering_config")

    defaults = {
        "enabled": True,
        "skip_qa_sessions": True,
        "considerations_file": "default.json",
        "summary_enabled": True,
        "timeout_seconds": 30
    }

    if not config_path.exists():
        return defaults

    try:
        with open(config_path) as f:
            config = json.load(f)
            # Merge with defaults (config overrides)
            return {**defaults, **config}
    except Exception as e:
        logger.warning(f"Failed to load config: {e}, using defaults")
        return defaults
```

### Writing Config

```python
def update_config(key: str, value: Any):
    """Update single config value."""
    config_path = Path(".claude/tools/amplihack/.power_steering_config")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = load_config()
    config[key] = value

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
```

### Command: /amplihack:power-steering-config

**Purpose**: Manage configuration values

**Usage**:

```bash
/amplihack:power-steering-config show
/amplihack:power-steering-config set enabled false
/amplihack:power-steering-config set timeout_seconds 60
/amplihack:power-steering-config reset
```

**Implementation**:

```markdown
---
description: Manage power-steering configuration
---

Managing power-steering configuration...

Arguments: {show|set|reset} [key] [value]

Actions:

- show: Display current configuration
- set <key> <value>: Update configuration value
- reset: Restore default configuration
```

## Control Flow Decision Tree

```
Is power-steering enabled?
├─ Check 1: Does .disabled semaphore exist?
│  ├─ YES → SKIP (highest priority)
│  └─ NO → Continue
├─ Check 2: Is AMPLIHACK_SKIP_POWER_STEERING set?
│  ├─ YES → SKIP (medium priority)
│  └─ NO → Continue
├─ Check 3: Is config.enabled = false?
│  ├─ YES → SKIP (lowest priority)
│  └─ NO → Continue
└─ RUN power-steering
```

## User Experience

### Scenario 1: Disable for one session

```bash
AMPLIHACK_SKIP_POWER_STEERING=1 claude
```

### Scenario 2: Disable permanently for project

```bash
# Option A: Use slash command
/amplihack:disable-power-steering

# Option B: Edit config
/amplihack:power-steering-config set enabled false
```

### Scenario 3: Disable globally for all projects

```bash
# Add to shell profile (.bashrc, .zshrc)
export AMPLIHACK_SKIP_POWER_STEERING=1
```

### Scenario 4: Temporarily enable when globally disabled

```bash
# Remove semaphore if exists
/amplihack:enable-power-steering

# Unset environment variable for this session
unset AMPLIHACK_SKIP_POWER_STEERING
```

## File Locations Summary

```
.claude/
├── tools/amplihack/
│   └── .power_steering_config              # Config file (Layer 1)
└── runtime/power-steering/
    ├── .disabled                            # Semaphore file (Layer 3)
    └── .{session_id}_completed              # Per-session semaphore

Environment:
└── AMPLIHACK_SKIP_POWER_STEERING            # Environment variable (Layer 2)
```

## Implementation Priority

1. **Phase 1 (MVP)**:
   - Semaphore file (Layer 3)
   - Environment variable (Layer 2)
   - Slash commands: disable/enable

2. **Phase 2 (Enhancement)**:
   - Config file support (Layer 1)
   - Status command
   - Config management command
   - CLI flag (if possible)

## Testing Requirements

### Unit Tests

- Each control mechanism independently
- Priority ordering (semaphore > env > config)
- Default behavior when nothing set

### Integration Tests

- Slash commands create/remove files correctly
- Config file parsing with invalid JSON
- Environment variable detection
- Multiple control mechanisms active simultaneously

### Edge Cases

- Config file doesn't exist
- Malformed JSON in config
- Semaphore file has content (should still work)
- Permission errors creating semaphore
- Race condition: multiple sessions checking simultaneously
