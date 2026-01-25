# Claude Code Hook System

This directory contains the hook system for Claude Code, which allows for customization and monitoring of the Claude Code runtime environment.

## Overview

The hook system uses a **unified HookProcessor** base class that provides common functionality for all hooks, reducing code duplication and improving maintainability.

## Hook Files

### Core Infrastructure

- **`hook_processor.py`** - Base class providing common functionality for all hooks
  - JSON input/output handling
  - Logging to `~/.amplihack/.claude/runtime/logs/`
  - Metrics collection
  - Error handling and graceful fallback
  - Session data management

### Active Hooks (Configured in .claude/settings.json)

- **`session_start.py`** - Runs when a Claude Code session starts
  - Adds project context to the conversation
  - Reads and applies user preferences from USER_PREFERENCES.md
  - Logs session start metrics

- **`stop.py`** - Runs when a session ends
  - Checks for lock flag (`~/.amplihack/.claude/tools/amplihack/.lock_active`)
  - Blocks stop if continuous work mode is enabled (lock active)
  - Logs stop attempts and lock status

- **`post_tool_use.py`** - Runs after each tool use
  - Tracks tool usage metrics
  - Validates tool execution results
  - Categorizes tool types for analytics

- **`pre_compact.py`** - Runs before context compaction
  - Manages context and prepares for compaction
  - Logs pre-compact events

## Architecture

```
┌─────────────────┐
│  Claude Code    │
└────────┬────────┘
         │ JSON input
         ▼
┌─────────────────┐
│  Hook Script    │
├─────────────────┤
│ HookProcessor   │ ◄── Base class
│   - read_input  │
│   - process     │ ◄── Implemented by subclass
│   - write_output│
│   - logging     │
│   - metrics     │
└────────┬────────┘
         │ JSON output
         ▼
┌─────────────────┐
│  Claude Code    │
└─────────────────┘
```

## Creating a New Hook

To create a new hook, extend the `HookProcessor` class:

```python
#!/usr/bin/env python3
"""Your hook description."""

from typing import Any, Dict
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class YourHook(HookProcessor):
    """Your hook processor."""

    def __init__(self):
        super().__init__("your_hook_name")

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the hook input.

        Args:
            input_data: Input from Claude Code

        Returns:
            Output to return to Claude Code
        """
        # Your processing logic here
        self.log("Processing something")
        self.save_metric("metric_name", value)

        return {"result": "success"}


def main():
    """Entry point."""
    hook = YourHook()
    hook.run()


if __name__ == "__main__":
    main()
```

## Data Storage

The hook system creates and manages several directories:

```
.claude/runtime/
├── logs/           # Log files for each hook
│   ├── session_start.log
│   ├── stop.log
│   └── post_tool_use.log
├── metrics/        # Metrics in JSONL format
│   ├── session_start_metrics.jsonl
│   ├── stop_metrics.jsonl
│   └── post_tool_use_metrics.jsonl
└── analysis/       # Session analysis files
    └── session_YYYYMMDD_HHMMSS.json
```

## Testing

Run tests to verify the hook system:

```bash
# Unit tests for HookProcessor
python -m pytest test_hook_processor.py -v

# Integration tests for all hooks
python test_integration.py

# Test Azure continuation hook
python test_stop_azure_continuation.py

# Test individual hooks manually
echo '{"prompt": "test"}' | python session_start.py
```

## Metrics Collected

### session_start

- `prompt_length` - Length of the initial prompt

### stop

- `lock_blocks` - Count of stop attempts blocked by lock flag

### post_tool_use

- `tool_usage` - Name of tool used (with optional duration)
- `bash_commands` - Count of Bash executions
- `file_operations` - Count of file operations (Read/Write/Edit)
- `search_operations` - Count of search operations (Grep/Glob)

## Error Handling

All hooks implement graceful error handling:

1. **Invalid JSON input** - Returns error message in output
2. **Processing exceptions** - Logs error, returns empty dict
3. **File system errors** - Logs warning, continues operation
4. **Missing fields** - Uses defaults, continues processing

This ensures that hook failures never break the Claude Code chain.

## Hook Configuration

Hooks are configured in `~/.amplihack/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/session_start.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/stop.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/post_tool_use.py"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/pre_compact.py"
          }
        ]
      }
    ]
  }
}
```

## Benefits of Unified Processor

1. **Reduced Code Duplication** - Common functionality in one place
2. **Consistent Error Handling** - All hooks handle errors the same way
3. **Unified Logging** - Standardized logging across all hooks
4. **Easier Testing** - Base functionality tested once
5. **Simplified Maintenance** - Fix bugs in one place
6. **Better Metrics** - Consistent metric collection
7. **Easier Extension** - Simple to add new hooks

## Continuous Work Mode (Lock System)

The stop hook supports continuous work mode via a lock flag:

- **Lock file**: `~/.amplihack/.claude/tools/amplihack/.lock_active`
- **Enable**: Use `/amplihack:lock` slash command
- **Disable**: Use `/amplihack:unlock` slash command
- **Behavior**: When locked, Claude continues working through all TODOs without stopping

This enables autonomous operation for complex multi-step tasks.
