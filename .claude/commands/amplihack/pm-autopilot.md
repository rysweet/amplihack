# /pm:autopilot Command

**PM Architect Phase 4 (Autonomy) - Autonomous work selection and execution**

## Purpose

Enable autonomous decision-making where PM Architect analyzes current state, selects work, and optionally executes actions without human intervention.

## Usage

```bash
/pm:autopilot [mode] [schedule]
```

### Modes

- **dry-run** (default): Show decisions without executing
  - Safe mode for review
  - See what autopilot would do
  - No changes made to state

- **execute**: Actually take actions
  - Start new workstreams
  - Escalate stalled work
  - Flag conflicts

### Schedule

- **on-demand** (default): Run once now
- **hourly**: Run every hour automatically
- **daily**: Run once per day

## Examples

### Safe preview (dry-run)
```bash
/pm:autopilot
/pm:autopilot dry-run
```

Shows what autopilot would do without making changes.

### Execute actions
```bash
/pm:autopilot execute
```

Actually starts work, escalates issues, etc.

### Set up recurring runs
```bash
/pm:autopilot execute hourly
/pm:autopilot dry-run daily
```

## What Autopilot Does

### 1. Check for Stalled Workstreams
- Detects work with no progress > 30 minutes
- Escalates to human for attention
- Flags missing process IDs

### 2. Start New Work (if capacity available)
- Uses recommendation engine
- Only starts if confidence >= 70%
- Selects highest-priority ready items
- Documents rationale for selection

### 3. Monitor for Conflicts
- Detects overlapping workstreams
- Escalates conflicts to human
- Prevents problematic parallel work

## Decision Transparency

All decisions include:
- **Action taken**: What autopilot did
- **Rationale**: Why this decision
- **Alternatives**: Other options considered
- **Confidence**: How certain (0-100%)
- **Override**: How to reverse decision

View details:
```bash
/pm:explain <decision-id>
/pm:explain recent
```

## Safety Features

1. **Dry-run default**: Must explicitly choose execute
2. **Max actions**: Limited to 3 actions per run
3. **Confidence threshold**: Only acts when >= 70% confident
4. **Override capability**: User can reverse most decisions
5. **Escalation**: Human judgment required for conflicts

## Requirements

- PM must be initialized (`/pm:init`)
- Backlog items must exist
- For new work: capacity available (< 5 concurrent)

## Output

Shows:
- Mode and schedule
- Decisions made with rationale
- Alternatives considered
- Override commands
- Execution outcomes (if execute mode)

## Integration

Works with:
- `/pm:status` - Current state
- `/pm:suggest` - Recommendations used for selection
- `/pm:coordinate` - Conflict detection
- `/pm:explain` - Decision transparency

## Learning

Phase 4 includes learning from outcomes:
- Tracks estimation accuracy
- Identifies risk patterns
- Improves recommendations over time
- Adapts to project patterns

See Phase 4 documentation for learning details.
