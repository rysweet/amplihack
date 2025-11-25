# Agent Performance Dashboard Skill

A ruthlessly simple skill for tracking and reporting agent usage metrics.

## Overview

This skill provides visibility into which agents are being used, their success rates, and identifies underutilized agents that could improve workflow quality.

## Usage

### Trigger the Skill

The skill auto-activates when you mention:

```
"Show me agent performance"
"Generate agent metrics report"
"Which agents are underutilized?"
"Agent usage statistics"
```

### Manual Report Generation

To generate a report manually:

1. Read the workflow execution log
2. Aggregate agent invocation data
3. Compare against available agents
4. Output to metrics file

### Example Output

```yaml
# Agent Performance Report
# Period: Last 30 days

summary:
  total_invocations: 142
  unique_agents_used: 12
  avg_success_rate: 94.2%

top_agents:
  1. architect: 45 invocations (95.6% success)
  2. builder: 38 invocations (89.5% success)
  3. reviewer: 25 invocations (100% success)

underutilized:
  - database: 0 invocations
  - integration: 2 invocations
  - patterns: 3 invocations

recommendations:
  - Use database agent for schema-related work
  - Leverage patterns agent to identify reusable solutions
  - Consider integration agent for external service work
```

## Architecture

### Data Flow

```
workflow_tracker.log_agent_invocation()
         |
         v
  workflow_execution.jsonl
         |
         v
  skill aggregation
         |
         v
  agent_performance.yaml
```

### File Locations

| File                                                               | Purpose             |
| ------------------------------------------------------------------ | ------------------- |
| `.claude/runtime/logs/workflow_adherence/workflow_execution.jsonl` | Raw invocation logs |
| `.claude/runtime/metrics/agent_performance.yaml`                   | Aggregated metrics  |

## Integration

### With Workflow Tracker

The skill leverages the existing `workflow_tracker.py` which provides:

```python
log_agent_invocation(agent_name, purpose, step_number)
```

### With DEFAULT_WORKFLOW

Metrics help verify workflow adherence by tracking which agents are used at each step.

## Philosophy Compliance

- **No external dependencies**: Uses only built-in Python and existing infrastructure
- **File-based storage**: Simple YAML/JSONL, no database required
- **Minimal overhead**: Logging adds <5ms per invocation
- **Self-contained**: All skill logic in SKILL.md, uses existing tools
