# Lock Tool Module

A tool module for Amplifier that enables "continuous work mode" - where the agent keeps working until explicitly unlocked.

## Purpose

The lock tool provides a simple mechanism to signal that the agent should continue working autonomously without stopping for confirmation. This is useful for:

- Long-running tasks that require multiple steps
- Batch operations where you want the agent to proceed until completion
- Exploratory work where the agent should keep investigating

## Installation

### Via Amplifier CLI

```bash
amplifier module add tool-lock --type tool --source file:///path/to/tool-lock
```

### In Bundle/Profile

```yaml
modules:
  tools:
    - module: tool-lock
```

## Usage

The tool exposes three operations:

### Lock (Enable Continuous Work Mode)

```json
{
  "operation": "lock",
  "message": "Keep working on the refactoring until all tests pass"
}
```

### Unlock (Disable Continuous Work Mode)

```json
{
  "operation": "unlock"
}
```

### Check (Query Lock Status)

```json
{
  "operation": "check"
}
```

## Schema

```json
{
  "type": "object",
  "properties": {
    "operation": {
      "type": "string",
      "enum": ["lock", "unlock", "check"],
      "description": "Operation to perform"
    },
    "message": {
      "type": "string",
      "description": "Custom instruction when locking (optional)"
    }
  },
  "required": ["operation"]
}
```

## Lock File Location

Lock files are stored in the project's `.amplifier/runtime/locks/` directory:

- `.lock_active` - Presence indicates lock is active
- `.lock_message` - Optional custom message/instruction

The project root is determined by:
1. `AMPLIFIER_PROJECT_DIR` environment variable
2. `CLAUDE_PROJECT_DIR` environment variable (backward compatibility)
3. Current working directory (fallback)

## Integration with Hooks

This tool is designed to work with a prompt-submit hook that checks for the lock file and injects a reminder to continue working. See the amplihack collection for the complete integration pattern.

## API

### LockTool Class

```python
from amplifier_tool_lock import LockTool

tool = LockTool()
result = await tool.execute({"operation": "check"})
print(result.message)  # "Lock is NOT active."
```

### Module Entry Point

```python
from amplifier_tool_lock import mount

# Called by Amplifier during session initialization
await mount(coordinator, config={})
```

## License

MIT
