# Claude Code Hook System

This directory contains the hook system for Claude Code, which allows for customization and monitoring of the Claude Code runtime environment.

## Overview

The hook system uses a **unified HookProcessor** base class that provides common functionality for all hooks, reducing code duplication and improving maintainability.

## Hook Files

### Core Infrastructure

- **`hook_processor.py`** - Base class providing common functionality for all hooks
  - JSON input/output handling
  - Logging to `.claude/runtime/logs/`
  - Metrics collection
  - Error handling and graceful fallback
  - Session data management

### Active Hooks

- **`session_start.py`** - Runs when a Claude Code session starts
  - Adds project context to the conversation
  - Logs session start metrics

- **`stop.py`** - Runs when a session ends
  - Analyzes conversation for learnings
  - Saves session statistics
  - Creates session analysis files

- **`post_tool_use.py`** - Runs after each tool use
  - Tracks tool usage metrics
  - Validates tool execution results
  - Categorizes tool types for analytics

- **`stop_azure_continuation.py`** - Stop hook with DecisionControl for Azure OpenAI
  - Prevents premature stopping when using Azure OpenAI models through the proxy
  - Auto-activates when Azure OpenAI proxy is detected (via environment variables)
  - Decision Logic:
    - Continues if uncompleted TODO items exist
    - Continues if continuation phrases are detected
    - Continues if multi-part user request appears unfulfilled
    - Otherwise allows normal stop

### Testing

- **`test_hook_processor.py`** - Unit tests for the HookProcessor base class
- **`test_integration.py`** - Integration tests for the complete hook system
- **`test_stop_azure_continuation.py`** - Tests the Azure continuation hook

### Backup Files

- **`*.py.backup`** - Original implementations before refactoring (kept for reference)
- **`*_refactored.py`** - Initial refactored versions (can be removed)

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

- `message_count` - Total messages in conversation
- `tool_uses` - Number of tool invocations
- `errors` - Number of errors detected
- `potential_learnings` - Number of potential discoveries

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

## Environment Variables

### Azure OpenAI Integration

The Azure continuation hook (`stop_azure_continuation.py`) checks for these environment variables:

- `ANTHROPIC_BASE_URL` - Set to localhost when proxy is active
- `CLAUDE_CODE_PROXY_LAUNCHER` - Indicates proxy launcher usage
- `AZURE_OPENAI_KEY` - Azure OpenAI credentials
- `OPENAI_BASE_URL` - Azure OpenAI endpoint

## Benefits of Unified Processor

1. **Reduced Code Duplication** - Common functionality in one place
2. **Consistent Error Handling** - All hooks handle errors the same way
3. **Unified Logging** - Standardized logging across all hooks
4. **Easier Testing** - Base functionality tested once
5. **Simplified Maintenance** - Fix bugs in one place
6. **Better Metrics** - Consistent metric collection
7. **Easier Extension** - Simple to add new hooks

## Migration from Old Hooks

The refactored hooks maintain 100% backward compatibility:

- Same input/output format
- Same file locations
- Same functionality
- Additional features (metrics, better logging)

Original hooks are backed up as `*.backup` files and can be restored if needed.
