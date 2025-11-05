# Module: Ultra-Think Performance Metrics

## Purpose

Capture timestamped checkpoints and performance metrics for Ultra-Think sessions to enable data-driven workflow optimization, bottleneck identification, and performance tracking over time.

## Problem Statement

Currently, there's no visibility into which phases of Ultra-Think tasks consume the most messages or time. Without metrics, it's impossible to identify bottlenecks, measure efficiency, or optimize the workflow.

## Solution Design

### Phase 1: Timestamped Checkpoints (TodoWrite Metrics)

Enhance the `post_tool_use.py` hook to capture TodoWrite task transitions:

**Data Captured:**

- Message number when task marked `in_progress`
- Timestamp when task marked `in_progress`
- Message number when task marked `completed`
- Timestamp when task marked `completed`
- Task content/description
- Task activeForm

**Storage Format:**

```json
{
  "timestamp": "2025-11-05T10:30:45.123456",
  "metric": "todo_transition",
  "value": "in_progress",
  "hook": "post_tool_use",
  "metadata": {
    "task_content": "Step 1: Use prompt-writer agent...",
    "task_active_form": "Using prompt-writer agent...",
    "message_number": 15,
    "session_id": "20251105_103045"
  }
}
```

### Phase 2: Performance Reporting

Create a reporting module that generates efficiency summaries:

**Module:** `.claude/tools/amplihack/performance_report.py`

**Capabilities:**

- Parse TodoWrite metrics from JSONL files
- Calculate duration and message count per task
- Generate formatted performance summary
- Compare to baseline metrics (if available)

**Report Format:**

```
Ultra-Think Performance Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase 1 (Requirements):   12 messages, ~4min
Phase 2 (Architecture):   18 messages, ~6min
Phase 3 (Implementation): 25 messages, ~8min
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total:                    55 messages, 18min

Comparison to baseline (development tasks):
  Messages: 55 vs 45 expected (+22%)
  Duration: 18min vs 15min expected (+20%)
```

### Phase 3: Baseline Metrics

**Storage:** `.claude/runtime/metrics/baselines.json`

**Structure:**

```json
{
  "investigation": {
    "avg_messages": 35,
    "avg_duration_minutes": 12,
    "sample_count": 5
  },
  "development": {
    "avg_messages": 45,
    "avg_duration_minutes": 15,
    "sample_count": 8
  },
  "debugging": {
    "avg_messages": 28,
    "avg_duration_minutes": 10,
    "sample_count": 3
  }
}
```

## Contract

### Inputs

- **post_tool_use hook**: TodoWrite tool use events from Claude Code
- **performance_report.py**: Session ID or metrics file path

### Outputs

- **Metrics files**: JSONL format in `.claude/runtime/metrics/`
- **Report**: Formatted text output to stdout
- **Baselines**: JSON file with aggregated statistics

### Side Effects

- Creates/updates metrics files in `.claude/runtime/metrics/`
- Creates `.claude/runtime/metrics/baselines.json` if missing
- Logs activity to hook log files

## Dependencies

- **Existing**: `hook_processor.py` base class
- **Existing**: `post_tool_use.py` hook
- **Python stdlib**: json, datetime, pathlib, argparse
- **Optional**: Rich library for enhanced terminal output (graceful fallback)

## Implementation Notes

### Key Design Decisions

1. **Hook-based capture**: Use post_tool_use hook for zero-latency metrics collection
2. **JSONL storage**: Append-only format for reliability and ease of parsing
3. **Session tracking**: Use message numbers to track relative progress within session
4. **Graceful degradation**: Report works even without baselines
5. **Modular design**: Each phase is independent and can be deployed separately

### TodoWrite Detection Logic

The post_tool_use hook will:

1. Check if tool_name == "TodoWrite"
2. Parse the todos array from tool input
3. Identify state transitions (pending → in_progress, in_progress → completed)
4. Save metrics with task metadata and current message number

### Message Number Tracking

Message numbers come from Claude Code's conversation context. The hook will:

- Extract message count from input_data if available
- Fall back to timestamp-based ordering if not available
- Store both for maximum flexibility

## Test Requirements

### Unit Tests

- Test TodoWrite event parsing
- Test metric saving logic
- Test report generation with sample data
- Test baseline calculation
- Test missing data handling

### Integration Tests

- Test hook integration with Claude Code
- Test end-to-end metric capture during actual TodoWrite usage
- Test report generation from real session data

### Manual Tests

- Run UltraThink task and verify metrics captured
- Generate report and verify accuracy
- Update baselines and verify calculations

## Success Criteria

1. **Data Capture**: All TodoWrite transitions captured with timestamps and message numbers
2. **Reporting**: Report generates accurately from captured metrics
3. **Baselines**: Baseline metrics accumulate and update correctly
4. **Performance**: No noticeable impact on Claude Code responsiveness
5. **Reliability**: Graceful failure handling if metrics unavailable

## Implementation Plan

### Step 1: Enhance post_tool_use.py

- Add TodoWrite detection logic
- Extract task state transitions
- Save metrics with full context

### Step 2: Create performance_report.py

- Parse JSONL metrics files
- Calculate durations and message counts
- Generate formatted output
- Handle missing baselines gracefully

### Step 3: Create baseline management

- Initialize baselines.json
- Update baselines after sessions
- Categorize tasks by type

### Step 4: Testing

- Unit tests for all modules
- Integration tests with real TodoWrite events
- Manual validation

### Step 5: Documentation

- Update hook README
- Add usage examples
- Document baseline categories

## Migration Strategy

- Phase 1 can be deployed immediately (metrics capture)
- Phase 2 can be used ad-hoc (reporting)
- Phase 3 requires multiple sessions to build baselines

No breaking changes to existing functionality.
