# Session Management Toolkit

A comprehensive session management system for Claude Code that provides persistent sessions, structured logging, and defensive file operations following amplihack's ruthless simplicity philosophy.

## Features

- **ClaudeSession**: Enhanced session wrapper with timeout handling and lifecycle management
- **SessionManager**: Persistence and resume capabilities with automatic archiving
- **ToolkitLogger**: Structured logging with session integration and operation tracking
- **Defensive File I/O**: Retry logic, atomic operations, and integrity verification
- **Unified Interface**: Simple SessionToolkit that combines all components

## Quick Start

```python
from .session_toolkit import SessionToolkit

# Create toolkit
toolkit = SessionToolkit(auto_save=True)

# Use a session
with toolkit.session("my_task") as session:
    logger = toolkit.get_logger("component")

    logger.info("Starting task")
    result = session.execute_command("analyze", path="/project")
    logger.success("Task completed")
```

## Architecture

### Core Components

```
session/
├── claude_session.py      # Enhanced session wrapper
├── session_manager.py     # Persistence and lifecycle
├── toolkit_logger.py      # Structured logging
├── file_utils.py          # Defensive file operations
└── session_toolkit.py     # Unified interface
```

### Runtime Structure

```
.claude/runtime/
├── sessions/           # Session persistence
├── logs/              # Structured logs
├── metrics/           # Performance data
└── checkpoints/       # Session checkpoints
```

## API Reference

### SessionToolkit

The main interface for all session management operations.

```python
toolkit = SessionToolkit(
    runtime_dir=Path(".claude/runtime"),
    auto_save=True,
    log_level="INFO"
)

# Session management
session_id = toolkit.create_session("task_name", config=config)
session = toolkit.get_session(session_id)
session = toolkit.resume_session(session_id)

# Context manager usage
with toolkit.session("task") as session:
    # Work with session
    pass

# Logging
logger = toolkit.get_logger("component")
logger.info("Message", metadata={"key": "value"})

# Statistics and cleanup
stats = toolkit.get_toolkit_stats()
toolkit.cleanup_old_data()
```

### ClaudeSession

Enhanced session wrapper with timeout and error handling.

```python
from .claude_session import ClaudeSession, SessionConfig

config = SessionConfig(
    timeout=300.0,
    max_retries=3,
    heartbeat_interval=30.0
)

session = ClaudeSession(config)

with session:
    result = session.execute_command("command", arg="value")
    session.save_checkpoint()
    stats = session.get_statistics()
```

### ToolkitLogger

Structured logging with operation tracking.

```python
from .toolkit_logger import ToolkitLogger

logger = ToolkitLogger(
    session_id="session_123",
    component="analyzer"
)

# Basic logging
logger.info("Processing started")
logger.error("Error occurred", exc_info=True)
logger.success("Operation completed", duration=12.5)

# Operation tracking
with logger.operation("data_processing"):
    # Work happens here
    logger.info("Processing data")

# Child loggers
child = logger.create_child_logger("sub_component")
```

### File Operations

Defensive file I/O with retry logic and verification.

```python
from .file_utils import (
    safe_read_file, safe_write_file,
    safe_read_json, safe_write_json,
    retry_file_operation
)

# Safe file operations
content = safe_read_file("file.txt")
safe_write_file("file.txt", content, atomic=True, backup=True)

# JSON operations
data = safe_read_json("data.json", default={})
safe_write_json("data.json", data)

# Custom retry logic
@retry_file_operation(max_retries=5, delay=0.5)
def custom_operation():
    # Your file operation here
    pass
```

## Configuration

### SessionConfig

```python
from .claude_session import SessionConfig

config = SessionConfig(
    timeout=300.0,           # Command timeout in seconds
    max_retries=3,           # Maximum retry attempts
    retry_delay=1.0,         # Initial retry delay
    heartbeat_interval=30.0, # Heartbeat check interval
    enable_logging=True,     # Enable session logging
    log_level="INFO",        # Logging level
    auto_save_interval=60.0  # Auto-save interval
)
```

### Runtime Directory Structure

The toolkit creates and manages the following directory structure:

```
.claude/runtime/
├── sessions/
│   ├── registry.json         # Session metadata registry
│   ├── session_*.json        # Individual session files
│   └── archive/              # Archived sessions
├── logs/
│   ├── toolkit.log           # Main toolkit log
│   ├── session_*.log         # Session-specific logs
│   └── archive/              # Archived logs
├── metrics/
│   └── session_stats.json    # Performance metrics
├── checkpoints/
│   └── session_*/            # Session checkpoints
└── temp/                     # Temporary files
```

## Examples

### Basic Usage

```python
from .session_toolkit import quick_session

# Quick session for simple tasks
with quick_session("analysis") as session:
    result = session.execute_command("analyze_code")
    print(f"Analysis result: {result}")
```

### Advanced Workflow

```python
from .session_toolkit import SessionToolkit
from .claude_session import SessionConfig

# Configure for long-running tasks
config = SessionConfig(timeout=1800.0, heartbeat_interval=60.0)
toolkit = SessionToolkit()

session_id = toolkit.create_session(
    "code_analysis",
    config=config,
    metadata={"project": "my_app", "version": "1.0"}
)

with toolkit.session(session_id) as session:
    logger = toolkit.get_logger("analyzer")

    # Multi-phase analysis
    with logger.operation("discovery"):
        session.execute_command("scan_project")
        session.save_checkpoint()

    with logger.operation("static_analysis"):
        session.execute_command("analyze_code")

    with logger.operation("security_scan"):
        session.execute_command("security_audit")

    logger.success("Analysis workflow completed")

# Export session for later analysis
toolkit.export_session_data(session_id, "analysis_export.json")
```

### Error Recovery

```python
with toolkit.session("error_recovery") as session:
    logger = toolkit.get_logger("processor")

    # Save checkpoint before risky operation
    session.save_checkpoint()

    try:
        session.execute_command("risky_operation")
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        # Restore to checkpoint
        session.restore_checkpoint()

        # Try alternative approach
        session.execute_command("safe_alternative")
```

### Batch Processing

```python
def process_batches(items):
    with toolkit.session("batch_processing") as session:
        logger = toolkit.get_logger("batch_processor")

        for i, batch in enumerate(items):
            with logger.operation(f"batch_{i}"):
                try:
                    result = session.execute_command("process_batch", data=batch)
                    logger.info(f"Batch {i} completed: {result['status']}")
                except Exception as e:
                    logger.error(f"Batch {i} failed: {e}")
                    continue

        logger.success(f"Processed {len(items)} batches")
```

## Testing

Run the test suite:

```bash
cd .claude/tools/amplihack/session
python -m pytest tests/ -v
```

Test coverage includes:

- Unit tests for all components
- Integration tests for complete workflows
- Error handling and edge cases
- Performance and concurrency testing

## Performance

The toolkit is designed for efficiency:

- **Lazy Loading**: Components are initialized only when needed
- **Batch Operations**: File operations are batched for efficiency
- **Automatic Cleanup**: Old sessions and logs are automatically archived
- **Memory Management**: Session state is persisted to disk, not held in memory

## Error Handling

Comprehensive error handling throughout:

- **Retry Logic**: Automatic retry with exponential backoff
- **Graceful Degradation**: Continues operation even with partial failures
- **State Recovery**: Checkpoint system allows rollback to known good states
- **Defensive Programming**: Input validation and bounds checking

## Integration

### With Claude Code

```python
# In your Claude Code workflow
from .claude.tools.amplihack.session import SessionToolkit

def claude_task_with_session():
    toolkit = SessionToolkit()

    with toolkit.session("claude_task") as session:
        logger = toolkit.get_logger("claude")

        # Your Claude Code logic here
        logger.info("Claude task starting")
        # ... work ...
        logger.success("Claude task completed")
```

### With Existing Systems

The toolkit integrates seamlessly with existing codebases:

- **Logging**: Structured logs can be consumed by log aggregation systems
- **Monitoring**: Session metrics are exported in standard formats
- **Backup**: Session data can be backed up to external storage
- **Analysis**: Session exports provide detailed audit trails

## Philosophy

This toolkit embodies amplihack's core principles:

- **Ruthless Simplicity**: Each component has one clear responsibility
- **Zero-BS Implementation**: No stubs, placeholders, or fake functionality
- **Regeneratable**: Any component can be rebuilt from its specification
- **Working Code Only**: Every function works or doesn't exist

## Support

For issues, questions, or contributions:

1. Check the examples in `examples/` directory
2. Review test cases in `tests/` directory
3. Consult the integration tests for complex scenarios

The Session Management Toolkit provides a solid foundation for building reliable, persistent workflows in Claude Code while maintaining the simplicity and clarity that makes code maintainable.
