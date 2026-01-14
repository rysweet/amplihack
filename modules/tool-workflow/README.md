# Workflow Tool for Amplifier

Workflow tracking and transcript management for Amplifier sessions.

## Features

### Workflow Tracking

Track workflow step execution with minimal overhead (<5ms per log entry):

- **Step execution logging** with timing
- **Skip tracking** with reason
- **Agent invocation logging**
- **Violation detection** and logging
- **Workflow statistics** and analytics

### Transcript Management

Manage conversation transcripts:

- **List sessions** with transcripts
- **Session summaries** with metadata
- **Context restoration** for interrupted sessions
- **Checkpoints** for save points

## Installation

```bash
pip install -e .
```

## Usage

### As Amplifier Tool

```json
// Start workflow tracking
{"operation": "workflow_start", "name": "DEFAULT", "task": "Add authentication feature"}

// Log step execution
{"operation": "workflow_step", "step": 1, "name": "Clarify Requirements", "agent": "prompt-writer", "duration_ms": 150}

// Log skipped step
{"operation": "workflow_skip", "step": 8, "name": "Local Testing", "reason": "Simple config change"}

// Log agent invocation
{"operation": "workflow_agent", "agent": "architect", "purpose": "Design API structure", "step": 3}

// Log violation
{"operation": "workflow_violation", "type": "missing_agent", "description": "No agent used for step 5"}

// End workflow
{"operation": "workflow_end", "success": true, "total_steps": 15, "skipped_steps": 1}

// Get statistics
{"operation": "workflow_stats", "limit": 100}

// List sessions
{"operation": "list_sessions"}

// Get session summary
{"operation": "session_summary", "session_id": "20250101_120000"}

// Restore context
{"operation": "restore_context", "session_id": "20250101_120000"}

// Save checkpoint
{"operation": "save_checkpoint", "session_id": "20250101_120000", "name": "pre-refactor"}

// List checkpoints
{"operation": "list_checkpoints", "session_id": "20250101_120000"}
```

### Programmatic API

```python
from amplifier_tool_workflow import (
    WorkflowTracker,
    TranscriptManager,
    StepTimer,
    log_workflow_start,
    log_step,
    log_workflow_end,
)

# Start workflow
log_workflow_start("DEFAULT", "Add authentication feature")

# Log steps (with timing context manager)
with StepTimer(1, "Clarify Requirements", "prompt-writer"):
    # Execute step
    pass

# Or manual logging
log_step(2, "Architecture Design", "architect", duration_ms=250)

# End workflow
log_workflow_end(success=True, total_steps=15, skipped_steps=1)

# Transcript management
manager = TranscriptManager()
sessions = manager.list_sessions()
summary = manager.get_summary("20250101_120000")
context = manager.restore_context("20250101_120000")
```

## Log Format

Workflow events are stored in JSONL format:

```jsonl
{"timestamp": "2025-01-01T12:00:00", "event": "workflow_start", "workflow": "DEFAULT", "task": "..."}
{"timestamp": "2025-01-01T12:00:01", "event": "step_executed", "step": 1, "name": "...", "agent": "..."}
{"timestamp": "2025-01-01T12:00:05", "event": "step_skipped", "step": 8, "name": "...", "reason": "..."}
{"timestamp": "2025-01-01T12:00:10", "event": "workflow_end", "success": true, "total_steps": 15}
```

## Configuration

### In bundle.yaml

```yaml
tools:
  - module: amplifier_tool_workflow
    config:
      logs_dir: ~/.amplifier/runtime/logs
```

## Performance

- <5ms overhead per log entry
- Append-only JSONL format (no seeking)
- No locks (single-threaded assumed)
- Immediate write (no buffering)

## License

MIT
