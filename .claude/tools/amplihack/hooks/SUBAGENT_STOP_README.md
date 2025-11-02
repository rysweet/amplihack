# SubagentStop Hook

## Overview

The SubagentStop hook tracks and logs metrics when subagent sessions terminate. It operates in observation mode, collecting data without interfering with the normal stop behavior.

## Purpose

- **Subagent Tracking**: Detect and log when subagent contexts end
- **Metric Collection**: Capture session metrics for analysis and monitoring
- **Non-Interference**: Never blocks or modifies stop behavior

## How It Works

### Subagent Detection

The hook detects subagent contexts through multiple methods:

1. **Environment Variable** (`CLAUDE_AGENT`): Set by parent when launching subagent
2. **Session ID Prefix**: Session IDs containing `agent-` or `subagent-`
3. **Input Metadata**: Explicit `agent_name` or `is_subagent` flags

### Metric Logging

When a subagent stop is detected, the hook logs:

- **Termination Details**: Agent name, detection method, session metrics
- **Count Metrics**: Simple counter for quick analysis

All metrics are written to `subagent_stop_metrics.jsonl` in JSONL format.

## Configuration

The hook is registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/subagent_stop.py",
            "timeout": 10000
          }
        ]
      }
    ]
  }
}
```

## Metrics Output

### Termination Metric

```json
{
  "timestamp": "2025-11-02T21:01:33.521908",
  "metric": "subagent_termination",
  "value": {
    "agent_name": "architect",
    "detection_method": "env",
    "session_id": "test-123",
    "turn_count": 3,
    "tool_use_count": 10,
    "error_count": 0,
    "duration_seconds": 120.5
  },
  "hook": "subagent_stop"
}
```

### Count Metric

```json
{
  "timestamp": "2025-11-02T21:01:33.536258",
  "metric": "subagent_stops",
  "value": 1,
  "hook": "subagent_stop",
  "metadata": {
    "agent_name": "architect"
  }
}
```

## Usage Examples

### Launching a Subagent with Tracking

```bash
# Set environment variable before launching subagent
export CLAUDE_AGENT=architect
claude-code --agent .claude/agents/amplihack/architect.md

# When the subagent stops, metrics are automatically logged
```

### Analyzing Subagent Metrics

```bash
# View all subagent terminations
cat .claude/runtime/metrics/subagent_stop_metrics.jsonl | grep subagent_termination

# Count stops by agent
cat .claude/runtime/metrics/subagent_stop_metrics.jsonl | \
  grep subagent_stops | \
  jq -r '.metadata.agent_name' | \
  sort | uniq -c

# Analyze session metrics
cat .claude/runtime/metrics/subagent_stop_metrics.jsonl | \
  grep subagent_termination | \
  jq '.value | {agent: .agent_name, turns: .turn_count, tools: .tool_use_count}'
```

## Testing

### Manual Testing

```bash
# Test with environment variable
export CLAUDE_AGENT=test-agent
echo '{"session_id": "test-123", "turn_count": 5}' | \
  python3 .claude/tools/amplihack/hooks/subagent_stop.py

# Test with session ID prefix
echo '{"session_id": "agent-builder-abc"}' | \
  python3 .claude/tools/amplihack/hooks/subagent_stop.py

# Test regular stop (no subagent)
echo '{"session_id": "regular-session"}' | \
  python3 .claude/tools/amplihack/hooks/subagent_stop.py
```

### Automated Tests

```bash
# Run unit tests
python3 test_subagent_stop_manual.py

# Run integration tests (if pytest available)
pytest tests/hooks/test_subagent_stop.py -v
```

## Implementation Details

### Architecture

```
SubagentStopHook
├── __init__(): Initialize with "subagent_stop" name
├── _detect_subagent_context(): Detect if running in subagent
├── _extract_session_metrics(): Extract metrics from input
└── process(): Main logic - detect, log, return {}
```

### Key Design Principles

1. **Zero-BS**: No stubs, fully functional implementation
2. **Non-Interference**: Always returns `{}` (never blocks)
3. **Defensive**: Handles missing data gracefully
4. **Observable**: Logs all actions for debugging

### Error Handling

The hook handles errors gracefully:

- Missing environment variables → No detection
- Invalid session IDs → No detection
- Missing metrics → Use default values (0, None)
- I/O errors → Logged but don't crash

## Integration with Other Hooks

The SubagentStop hook works alongside other Stop hooks:

1. **stop.py**: Handles lock checking and reflection triggering
2. **subagent_stop.py**: Observes and logs subagent terminations

Both hooks run independently and return their decisions separately.

## Performance

- **Overhead**: < 10ms per stop event
- **Timeout**: 10 seconds (configured in settings.json)
- **File I/O**: Append-only writes to JSONL (fast)

## Future Enhancements

Potential improvements (not implemented):

- Agent performance dashboards
- Anomaly detection (long-running agents, high error rates)
- Cost tracking per agent
- Integration with monitoring systems

## See Also

- `.claude/tools/amplihack/hooks/hook_processor.py`: Base class
- `.claude/tools/amplihack/hooks/stop.py`: Main stop hook
- `.claude/tools/amplihack/hooks/README.md`: General hook documentation
