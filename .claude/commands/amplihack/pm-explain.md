# /pm:explain Command

**PM Architect Phase 4 (Autonomy) - Explain autopilot decisions**

## Purpose

Provide full transparency for autonomous decisions made by PM Architect autopilot, including rationale, alternatives, and override options.

## Usage

```bash
/pm:explain [decision-id]
/pm:explain recent
```

### Arguments

- **decision-id**: Specific decision to explain (e.g., "autopilot-a3b2c1d4")
- **recent**: Show recent decisions (last 24 hours)
- *no argument*: Same as "recent"

## Examples

### View recent decisions
```bash
/pm:explain
/pm:explain recent
```

Shows list of decisions from last 24 hours with:
- Decision ID
- Timestamp
- Action taken
- Confidence level
- Outcome (success/failure/pending)

### Explain specific decision
```bash
/pm:explain autopilot-a3b2c1d4
```

Shows full details:
- Decision ID and timestamp
- Decision type (start_work, escalate_stalled, etc.)
- Action taken
- Complete rationale
- Confidence level
- Alternatives considered (with reasoning)
- Outcome
- Override command (if available)
- Additional context

## Decision Types

Autopilot makes these types of decisions:

1. **start_work**
   - Selected backlog item to work on
   - Rationale based on recommendation engine
   - Can override by pausing workstream

2. **escalate_stalled**
   - Flagged stalled workstream
   - Requires human attention
   - Cannot override (needs judgment)

3. **escalate_conflict**
   - Detected conflicting workstreams
   - Requires human resolution
   - Cannot override (needs judgment)

## What You See

### For Recent List
```
✅ autopilot-a3b2c1d4
   Time: 2025-11-21 10:30
   Action: Start work on BL-003: Add API endpoint
   Confidence: 85%
```

### For Detailed Explanation
```
Decision ID: autopilot-a3b2c1d4
Timestamp: 2025-11-21T10:30:00Z
Type: start_work

Action Taken:
  Start work on BL-003: Add API endpoint

Rationale:
  High priority item with clear requirements and no blockers.
  Estimated 4 hours, unblocks 2 other items.

Confidence: 85%

Alternatives Considered:
  1. BL-005: Refactor auth module (score: 72.1, confidence: 0.78)
  2. BL-007: Update docs (score: 68.5, confidence: 0.82)

Outcome: ✅ success

Override Available:
  /pm:pause BL-003

Additional Context:
  backlog_id: BL-003
  score: 85.3
  complexity: medium
  blocking_count: 2
  workstream_id: ws-004
```

## Override Decisions

Some decisions can be overridden:
- **start_work**: Pause the workstream
- **escalate_stalled**: Resume manually
- **escalate_conflict**: Cannot override (needs human judgment)

Override commands shown in decision details.

## Learning Integration

Decisions feed into Phase 4 learning:
- Tracks outcomes (success/failure)
- Measures estimation accuracy
- Identifies patterns
- Improves future decisions

## Requirements

- PM must be initialized (`/pm:init`)
- Autopilot must have made decisions (`/pm:autopilot`)

## Use Cases

### After autopilot run
```bash
/pm:autopilot dry-run
/pm:explain recent  # Review what it would do
```

### Understanding a specific decision
```bash
/pm:status  # See decision IDs in output
/pm:explain autopilot-xyz123
```

### Auditing autonomous actions
```bash
/pm:explain recent  # Review last 24 hours
```

### Before overriding
```bash
/pm:explain <decision-id>  # Understand why
# Then use override command if appropriate
```

## Integration

Works with:
- `/pm:autopilot` - Makes decisions to explain
- `/pm:status` - Shows decision IDs
- Learning system - Tracks outcomes

## Philosophy

**Decision Transparency is Critical**

Every autonomous decision must be:
1. **Explainable**: Clear rationale provided
2. **Reversible**: Override commands when appropriate
3. **Auditable**: Full history maintained
4. **Learnable**: Outcomes tracked for improvement

This ensures:
- User trust in autonomy
- Ability to learn from mistakes
- No "black box" decisions
- Clear accountability
