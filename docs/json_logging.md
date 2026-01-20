# Structured JSON Logging for Auto-Mode

## Overview

Auto-mode now includes structured JSONL (JSON Lines) logging alongside the existing text logs. This provides machine-readable event data for programmatic analysis, monitoring, and debugging.

## Log File Location

The structured log is written to:

```
.claude/runtime/logs/<session_id>/auto.jsonl
```

Where `<session_id>` is the unique identifier for the auto-mode session (e.g., `auto_claude_1234567890`).

## Event Schema

Each line in `auto.jsonl` is a standalone JSON object with the following base structure:

```json
{
  "timestamp": "2026-01-20T00:14:09.680139+00:00",
  "level": "INFO",
  "event": "turn_start",
  ...additional fields...
}
```

### Common Fields

- `timestamp`: ISO 8601 formatted timestamp with timezone (UTC)
- `level`: Log level (`INFO`, `WARNING`, `ERROR`)
- `event`: Event type (see Event Types below)

### Event Types

#### 1. `turn_start`

Logged at the beginning of each turn.

```json
{
  "timestamp": "2026-01-20T00:14:09.680139+00:00",
  "level": "INFO",
  "event": "turn_start",
  "turn": 1,
  "phase": "clarifying",
  "max_turns": 20
}
```

**Fields:**
- `turn`: Current turn number (1-indexed)
- `phase`: Current phase (`clarifying`, `planning`, `executing`, `evaluating`, `summarizing`)
- `max_turns`: Maximum turns configured for the session

#### 2. `turn_complete`

Logged when a turn finishes execution.

```json
{
  "timestamp": "2026-01-20T00:14:11.815309+00:00",
  "level": "INFO",
  "event": "turn_complete",
  "turn": 1,
  "duration_sec": 23.42,
  "success": true
}
```

**Fields:**
- `turn`: Turn number that completed
- `duration_sec`: Duration of the turn in seconds (rounded to 2 decimal places)
- `success`: Boolean indicating if the turn succeeded (exit code 0)

#### 3. `agent_invoked`

Logged when an agent or tool is invoked during execution.

```json
{
  "timestamp": "2026-01-20T00:15:32.480478+00:00",
  "level": "INFO",
  "event": "agent_invoked",
  "agent": "TodoWrite",
  "turn": 5
}
```

**Fields:**
- `agent`: Name of the agent/tool invoked (e.g., `TodoWrite`, `builder`, `tester`)
- `turn`: Turn number during which the agent was invoked

#### 4. `error`

Logged when an error occurs during execution.

```json
{
  "timestamp": "2026-01-20T00:20:15.680583+00:00",
  "level": "ERROR",
  "event": "error",
  "turn": 4,
  "error_type": "timeout",
  "message": "Turn 4 timed out after 600.0s (limit: 600.0s). Try reducing task complexity or increasing --query-timeout-minutes."
}
```

**Fields:**
- `turn`: Turn number when the error occurred
- `error_type`: Type of error (e.g., `timeout`, `TimeoutError`, `ValueError`)
- `message`: Human-readable error message

## Usage Examples

### Reading Events with Python

```python
import json
from pathlib import Path

# Read all events from a session
log_file = Path(".claude/runtime/logs/auto_claude_1234567890/auto.jsonl")

with open(log_file) as f:
    events = [json.loads(line) for line in f]

# Filter by event type
turn_starts = [e for e in events if e["event"] == "turn_start"]
errors = [e for e in events if e["event"] == "error"]

# Calculate total duration
turn_completes = [e for e in events if e["event"] == "turn_complete"]
total_duration = sum(e["duration_sec"] for e in turn_completes)
```

### Analyzing with jq

```bash
# Count events by type
cat auto.jsonl | jq -s 'group_by(.event) | map({event: .[0].event, count: length})'

# Get all errors
cat auto.jsonl | jq 'select(.event == "error")'

# Calculate average turn duration
cat auto.jsonl | jq -s '[.[] | select(.event == "turn_complete") | .duration_sec] | add / length'

# List all agents invoked
cat auto.jsonl | jq -s '[.[] | select(.event == "agent_invoked") | .agent] | unique'
```

### Monitoring Session Progress

```python
import json
from pathlib import Path

def monitor_session(log_file: Path):
    """Monitor auto-mode session progress in real-time."""
    current_turn = 0
    total_duration = 0.0

    with open(log_file) as f:
        for line in f:
            event = json.loads(line)

            if event["event"] == "turn_start":
                current_turn = event["turn"]
                print(f"Turn {current_turn}/{event['max_turns']} started ({event['phase']})")

            elif event["event"] == "turn_complete":
                total_duration += event["duration_sec"]
                print(f"Turn {event['turn']} completed in {event['duration_sec']}s (success: {event['success']})")

            elif event["event"] == "agent_invoked":
                print(f"  Agent invoked: {event['agent']}")

            elif event["event"] == "error":
                print(f"  ERROR: {event['message']}")

    print(f"\nTotal session duration: {total_duration:.2f}s")
```

## Benefits

1. **Programmatic Analysis**: Parse events with standard JSON tools
2. **Monitoring**: Track session progress and performance metrics
3. **Debugging**: Quickly identify errors and bottlenecks
4. **Metrics Collection**: Calculate turn durations, success rates, agent usage
5. **Integration**: Easy to integrate with log aggregation systems (Splunk, ELK, etc.)

## Implementation Details

- Events are written immediately (not buffered) for real-time monitoring
- File I/O errors are logged to stderr but don't crash the session
- Uses UTC timestamps for consistency across timezones
- JSONL format allows easy streaming and appending
- Each event is self-contained (no dependencies on previous events)

## Future Enhancements

Potential future additions:

- Session metadata (SDK version, Python version, OS)
- Resource usage metrics (memory, CPU)
- Git context (branch, commit, remote)
- Fork events (when sessions are forked for long-running tasks)
- Network events (API calls, retries, rate limits)
