# Ultra-Think Performance Metrics

Performance tracking system for Ultra-Think sessions that captures timestamped checkpoints and generates efficiency reports.

## Overview

This system provides visibility into Ultra-Think task performance by:

1. Capturing TodoWrite task transitions (in_progress, completed) with timestamps and message numbers
2. Generating performance reports showing time and message counts per task
3. Maintaining baseline metrics for different task types
4. Comparing sessions against baselines to identify efficiency trends

## Components

### 1. Metrics Capture (post_tool_use.py hook)

Automatically captures TodoWrite transitions in the `post_tool_use` hook:

- Detects when tasks are marked `in_progress` or `completed`
- Records timestamp, message number, and task metadata
- Stores metrics in `.claude/runtime/metrics/post_tool_use_metrics.jsonl`

**No configuration required** - works automatically when TodoWrite is used.

### 2. Performance Report Generator (performance_report.py)

Command-line tool for generating performance reports from captured metrics.

**Usage:**

```bash
# Generate report for current/latest session
python .claude/tools/amplihack/performance_report.py

# Generate report for specific session (by date)
python .claude/tools/amplihack/performance_report.py --session 2025-11-05

# Generate report with specific task type for baseline comparison
python .claude/tools/amplihack/performance_report.py --task-type development

# Update baseline metrics with current session data
python .claude/tools/amplihack/performance_report.py --update-baselines

# Update baselines for specific session
python .claude/tools/amplihack/performance_report.py --session 2025-11-05 --update-baselines
```

**Report Format:**

```
Ultra-Think Performance Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Step 1: Requirements clarification              15 msgs, ~5.0min
✓ Step 2: Architecture design                     19 msgs, ~6.8min
⋯ Step 3: Implementation                          12 msgs, ~4.2min
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total:                                             46 msgs, 16.0min

Comparison to baseline (development tasks):
  Messages: 46 vs 45 expected (+2%)
  Duration: 16.0min vs 15.0min expected (+7%)
```

### 3. Baseline Management (baselines.json)

Stores aggregated metrics for different task types:

- investigation
- development
- debugging
- refactoring

**Location:** `.claude/runtime/metrics/baselines.json`

**Format:**

```json
{
  "development": {
    "avg_messages": 45,
    "avg_duration_minutes": 15.2,
    "sample_count": 8
  },
  "investigation": {
    "avg_messages": 35,
    "avg_duration_minutes": 12.5,
    "sample_count": 5
  }
}
```

## Installation

No installation required - the system is integrated into the Claude Code hooks.

## Usage Workflow

### 1. Automatic Capture

Simply use TodoWrite in your Ultra-Think sessions as normal. Metrics are captured automatically.

### 2. Generate Reports

After a session, generate a performance report:

```bash
cd /path/to/project
python .claude/tools/amplihack/performance_report.py
```

### 3. Build Baselines

After multiple sessions, update baselines to establish expected performance:

```bash
python .claude/tools/amplihack/performance_report.py --update-baselines
```

### 4. Compare Future Sessions

Future reports will automatically compare against baselines to show efficiency trends.

## Task Type Categories

The system automatically categorizes tasks based on content:

- **investigation**: Tasks containing "investigate", "analyze"
- **debugging**: Tasks containing "debug", "fix"
- **refactoring**: Tasks containing "refactor"
- **development**: Default category for other tasks

Override with `--task-type` flag if needed.

## Benefits

1. **Data-Driven Optimization**: Identify which workflow phases consume most resources
2. **Bottleneck Detection**: Find where agents or processes are inefficient
3. **Trend Analysis**: Track whether changes improve or hurt performance
4. **Clear Expectations**: Users know how long tasks should take
5. **Reflection Input**: Provides concrete data for reflection analysis

## Troubleshooting

### No metrics found

If you see "No TodoWrite metrics found":

- Ensure you're running from the project root or use `--metrics-dir`
- Check that `.claude/runtime/metrics/post_tool_use_metrics.jsonl` exists
- Verify that TodoWrite was actually called in the session

### Message numbers are 0

If message numbers show as 0:

- This can happen if Claude Code doesn't provide message numbers in context
- Reports will still work using timestamps for ordering

### Baselines not showing

If baseline comparisons don't appear:

- Run with `--update-baselines` to create initial baselines
- Ensure you have at least one complete session recorded
- Check that `.claude/runtime/metrics/baselines.json` exists

## Testing

Run unit tests to verify the system:

```bash
pytest tests/unit/test_performance_metrics.py -v
```

## Implementation Details

- **Storage format**: JSONL (one JSON object per line) for append-only reliability
- **Graceful degradation**: System works even without baselines or incomplete data
- **Zero latency**: Metrics capture adds no noticeable overhead
- **Modular design**: Each component can be used independently

## Future Enhancements

Potential improvements:

- Web dashboard for visualizing trends over time
- Anomaly detection for unusually slow tasks
- Per-agent performance breakdowns
- Automatic optimization suggestions
- Integration with reflection system

## Related

- See `Specs/UltraThinkPerformanceMetrics.md` for full technical specification
- See `.claude/tools/amplihack/hooks/README.md` for hook system documentation
- See GitHub issue #1098 for original feature request
