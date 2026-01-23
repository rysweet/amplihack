# Configuration: .power_steering_config

## Purpose

Stores power-steering configuration settings.

## Location

`~/.amplihack/.claude/tools/amplihack/.power_steering_config`

## Format

JSON file with the following structure:

```json
{
  "enabled": true,
  "skip_qa_sessions": true,
  "considerations_file": "default.json",
  "summary_enabled": true,
  "timeout_seconds": 30
}
```

## Fields

### enabled

- **Type**: boolean
- **Default**: true
- **Description**: Master switch for power-steering. If false, never run.

### skip_qa_sessions

- **Type**: boolean
- **Default**: true
- **Description**: Skip power-steering for detected Q&A sessions.

### considerations_file

- **Type**: string
- **Default**: "default.json"
- **Description**: Name of considerations file in `~/.amplihack/.claude/tools/amplihack/considerations/`

### summary_enabled

- **Type**: boolean
- **Default**: true
- **Description**: Generate and display session summary on approval.

### timeout_seconds

- **Type**: integer
- **Default**: 30
- **Description**: Maximum time for power-steering analysis. After timeout, approve (fail-open).

## Disable Methods

Power-steering can be disabled via three methods (checked in order):

### 1. Configuration File

```json
{
  "enabled": false
}
```

### 2. Environment Variable

```bash
export AMPLIHACK_SKIP_POWER_STEERING=1
```

### 3. Semaphore File

```bash
touch .claude/runtime/power-steering/.disabled
```

## Slash Commands

### /amplihack:disable-power-steering

Creates semaphore file at `~/.amplihack/.claude/runtime/power-steering/.disabled`

### /amplihack:enable-power-steering

Removes semaphore file

## CLI Flag

Add to Claude Code CLI:

```bash
claude --no-power-steering
```

Sets environment variable `AMPLIHACK_SKIP_POWER_STEERING=1`

## Default Behavior

If config file doesn't exist, use these defaults:

```json
{
  "enabled": true,
  "skip_qa_sessions": true,
  "considerations_file": "default.json",
  "summary_enabled": true,
  "timeout_seconds": 30
}
```

## Implementation Notes

- Config file is optional (use defaults if missing)
- Environment variable takes precedence over config file
- Semaphore file takes precedence over both
- Never fail if config is malformed - use defaults and log warning
