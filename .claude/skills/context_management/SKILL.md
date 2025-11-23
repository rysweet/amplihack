---
name: context-management
version: 1.0.0
description: |
  Proactive context window management via token monitoring, intelligent extraction, and selective rehydration.
  Use when approaching token limits or needing to preserve essential context.
  Provides status checks, snapshot creation, and configurable rehydration (essential/standard/comprehensive).
  Complements /transcripts and PreCompact hook with proactive optimization.
---

# Context Management Skill

## Purpose

This skill enables proactive management of Claude Code's context window through intelligent token monitoring, context extraction, and selective rehydration. Instead of reactive recovery after compaction, this skill helps users preserve essential context before hitting limits and restore it efficiently when needed.

## When to Use This Skill

- **Token monitoring**: Check current usage and get recommendations
- **Approaching limits**: Create snapshots at 70-85% usage
- **After compaction**: Restore essential context without full conversation
- **Long sessions**: Preserve key decisions and state proactively
- **Complex tasks**: Keep requirements and progress accessible
- **Context switching**: Save state when pausing work
- **Team handoffs**: Package context for others to continue

## Core Concepts

### Proactive vs Reactive Management

**Reactive (existing tools)**:

- PreCompact hook: Saves everything when Claude decides to compact
- /transcripts: Restores full conversation after compaction

**Proactive (this skill)**:

- Monitor usage before hitting limits
- Extract only essential context (not full dumps)
- Rehydrate at appropriate detail level
- User controls when and what to preserve

### Four Component Bricks

1. **TokenMonitor**: Tracks usage against thresholds (50%, 70%, 85%, 95%)
2. **ContextExtractor**: Intelligently extracts requirements, decisions, state
3. **ContextRehydrator**: Restores context at configurable detail levels
4. **Orchestrator**: Coordinates components for skill actions

### Three Detail Levels

- **Essential** (smallest): Requirements + current state only
- **Standard** (balanced): + key decisions + open items
- **Comprehensive** (complete): + full decisions + tools used + metadata

## Skill Actions

### Action: `status`

Check current token usage and get recommendations.

**Parameters:**

- `current_tokens` (int): Current token count

**Returns:**

```python
{
  'status': 'ok' | 'consider' | 'recommended' | 'urgent',
  'usage': {
    'current_tokens': 500000,
    'max_tokens': 1000000,
    'percentage': 50.0,
    'threshold_status': 'ok',
    'recommendation': 'Context is healthy. No action needed.'
  }
}
```

**Example:**

```python
result = context_management_skill('status', current_tokens=750000)
# Returns: status='consider', percentage=75.0
```

### Action: `snapshot`

Create intelligent context snapshot.

**Parameters:**

- `conversation_data` (list): Conversation messages
- `name` (str, optional): Human-readable snapshot name

**Returns:**

```python
{
  'status': 'success',
  'snapshot': {
    'snapshot_id': '20251116_143522',
    'name': 'auth-feature',
    'file_path': '.claude/runtime/context-snapshots/20251116_143522.json',
    'token_count': 1250,
    'components': ['requirements', 'decisions', 'state', 'open_items', 'tools_used']
  },
  'recommendation': 'Snapshot created successfully...'
}
```

**Example:**

```python
result = context_management_skill(
    'snapshot',
    conversation_data=messages,
    name='auth-implementation'
)
```

### Action: `rehydrate`

Restore context from snapshot at specified detail level.

**Parameters:**

- `snapshot_id` (str): Snapshot ID (format: YYYYMMDD_HHMMSS)
- `level` (str): 'essential' | 'standard' | 'comprehensive'

**Returns:**

```python
{
  'status': 'success',
  'context': '# Restored Context: auth-implementation\n\n...',
  'snapshot_id': '20251116_143522',
  'level': 'essential'
}
```

**Example:**

```python
result = context_management_skill(
    'rehydrate',
    snapshot_id='20251116_143522',
    level='essential'
)
print(result['context'])
```

### Action: `list`

List all available context snapshots.

**Parameters:** None

**Returns:**

```python
{
  'status': 'success',
  'snapshots': [
    {
      'id': '20251116_143522',
      'name': 'auth-feature',
      'timestamp': '2025-11-16 14:35:22',
      'size': '15KB',
      'token_count': 1250
    }
  ],
  'count': 1,
  'total_size': '15KB'
}
```

**Example:**

```python
result = context_management_skill('list')
for snapshot in result['snapshots']:
    print(f"{snapshot['name']}: {snapshot['size']}")
```

## Proactive Usage Workflow

### Step 1: Monitor Token Usage

```python
# Periodically check status
status = context_management_skill('status', current_tokens=current)

if status['status'] == 'consider':
    # Usage at 70%+ - consider creating snapshot
    pass
elif status['status'] == 'recommended':
    # Usage at 85%+ - snapshot recommended
    create_snapshot(...)
elif status['status'] == 'urgent':
    # Usage at 95%+ - create snapshot immediately
    create_snapshot(...)
```

### Step 2: Create Snapshot at Threshold

```python
# When 70-85% threshold reached
result = context_management_skill(
    'snapshot',
    conversation_data=messages,
    name='descriptive-name'
)

# Save snapshot ID for later rehydration
snapshot_id = result['snapshot']['snapshot_id']
```

### Step 3: Continue Working

After snapshot creation:

- Continue conversation naturally
- Let Claude Code compact if needed
- Use `/transcripts` for full history if desired
- PreCompact hook saves everything automatically

### Step 4: Rehydrate After Compaction

```python
# After compaction, restore essential context
result = context_management_skill(
    'rehydrate',
    snapshot_id='20251116_143522',
    level='essential'  # Start minimal
)

# Claude now has requirements + current state
# If more context needed, rehydrate at higher level
```

### Step 5: Adjust Detail Level as Needed

```python
# If essential isn't enough, upgrade to standard
result = context_management_skill(
    'rehydrate',
    snapshot_id='20251116_143522',
    level='standard'  # Adds decisions + open items
)

# For complete context, use comprehensive
result = context_management_skill(
    'rehydrate',
    snapshot_id='20251116_143522',
    level='comprehensive'  # Everything
)
```

## Integration with Existing Systems

### vs. PreCompact Hook

**PreCompact Hook** (automatic safety net):

- Triggered by Claude Code before compaction
- Saves complete conversation transcript
- Automatic, no user action needed
- Full conversation export to markdown

**Context Skill** (proactive optimization):

- Triggered by user when monitoring indicates
- Saves intelligent context extraction
- User-initiated, deliberate choice
- Essential context only, not full dump

**Relationship**: Complementary, not competing. Hook = safety net, Skill = optimization.

### vs. /transcripts Command

**/transcripts** (reactive restoration):

- Restores full conversation after compaction
- Complete history, all messages
- Used when you need everything back
- Reactive recovery tool

**Context Skill** (proactive preservation):

- Preserves essential context before compaction
- Selective rehydration, not full history
- Used when you want efficient context
- Proactive optimization tool

**Relationship**: Transcripts for full recovery, skill for efficient management.

### Storage Locations

- **Snapshots**: `.claude/runtime/context-snapshots/` (JSON)
- **Transcripts**: `.claude/runtime/logs/<session_id>/CONVERSATION_TRANSCRIPT.md`
- **No conflicts**: Different directories, different purposes

## Philosophy Alignment

### Ruthless Simplicity

- Four single-purpose bricks, no complex abstractions
- On-demand invocation, no background processes
- Standard library only, no external dependencies
- Clear contracts between components

### Single Responsibility

- TokenMonitor: ONLY tracks usage and thresholds
- ContextExtractor: ONLY extracts and snapshots context
- ContextRehydrator: ONLY restores from snapshots
- Orchestrator: ONLY coordinates components

### Zero-BS Implementation

- No stubs or placeholders
- All functions work completely
- Real token estimation, not fake
- Actual file operations, not simulated

### Trust in Emergence

- User decides when to snapshot, not automatic
- User chooses detail level, not system
- Proactive choice, not reactive automation
- Philosophy: empower, don't automate

## Convenience Functions

For simpler invocation:

```python
from context_management import (
    check_status,
    create_snapshot,
    rehydrate_context,
    list_snapshots
)

# Check status
status = check_status(current_tokens=750000)

# Create snapshot
snapshot = create_snapshot(
    conversation_data=messages,
    name='feature-name'
)

# Rehydrate context
context = rehydrate_context(
    snapshot_id='20251116_143522',
    level='standard'
)

# List snapshots
snapshots = list_snapshots()
```

## Usage Examples

### Example 1: Basic Proactive Workflow

```
User: Check my token usage
Assistant: *checks status*
Current usage: 720,000 tokens (72%)
Status: Consider creating snapshot soon

User: Create a snapshot named "api-auth-implementation"
Assistant: *creates snapshot*
Snapshot created: 20251116_143522
Components: requirements, decisions, state, open items, tools
Token count: 1,250
You can continue working. I'll manage context naturally.

[... much later, after compaction ...]

User: Restore context from that auth snapshot
Assistant: *rehydrates at essential level*
# Restored Context: api-auth-implementation

## Original Requirements
Implement JWT authentication for API endpoints...

## Current State
JWT handler created, middleware integration in progress
Tests: 12/15 passing
```

### Example 2: Progressive Detail Levels

```
User: Restore snapshot 20251116_143522 at essential level
Assistant: *rehydrates essential context*
Restored requirements and current state (250 tokens)

User: I need more context, upgrade to standard
Assistant: *rehydrates standard level*
Now including key decisions and open items (800 tokens)

User: Give me everything, comprehensive level
Assistant: *rehydrates comprehensive*
Full context including all decisions, tools, and metadata (1,250 tokens)
```

### Example 3: Multiple Snapshots

```
User: List my snapshots
Assistant:
1. 20251116_143522 - "api-auth" - 15KB - 2025-11-16 14:35
2. 20251116_092315 - "database-migration" - 22KB - 2025-11-16 09:23
3. 20251115_163045 - "frontend-redesign" - 18KB - 2025-11-15 16:30

Total: 3 snapshots, 55KB

User: Restore the database migration one at standard level
Assistant: *rehydrates database snapshot*
[... restored context ...]
```

## Common Patterns

### Pattern 1: Preventive Snapshotting

```python
# Check before long operation
status = check_status(current_tokens=current)

if status['status'] in ['recommended', 'urgent']:
    # Create snapshot before proceeding
    create_snapshot(messages, name='before-refactoring')
```

### Pattern 2: Context Switching

```python
# Pausing work on Feature A
create_snapshot(messages, name='feature-a-paused')

# Start Feature B
# [... new conversation ...]

# Resume Feature A later
context = rehydrate_context('feature-a-snapshot-id', level='standard')
```

### Pattern 3: Team Handoff

```python
# Create comprehensive snapshot for teammate
snapshot = create_snapshot(
    messages,
    name='handoff-to-alice-api-work'
)

# Share snapshot ID with teammate
# Alice can rehydrate and continue work
```

## Quality Checks

After using this skill, verify:

- [ ] Token monitoring provides accurate recommendations
- [ ] Snapshots capture essential context (not full dumps)
- [ ] Rehydration levels produce appropriate detail
- [ ] Files stored in `.claude/runtime/context-snapshots/`
- [ ] Snapshot IDs follow YYYYMMDD_HHMMSS format
- [ ] Token estimates are reasonable (~1 token per 4 chars)
- [ ] No conflicts with transcripts or PreCompact hook

## Success Criteria

This skill successfully helps users:

- [ ] Monitor context usage proactively
- [ ] Create snapshots before hitting limits
- [ ] Restore context efficiently after compaction
- [ ] Choose appropriate detail levels
- [ ] Manage multiple snapshots
- [ ] Integrate with existing tools seamlessly
- [ ] Maintain clean context hygiene

## Tips for Effective Context Management

1. **Monitor regularly**: Check status at natural breakpoints
2. **Snapshot strategically**: At 70-85% or before long operations
3. **Start minimal**: Use essential level first, upgrade if needed
4. **Name descriptively**: Use clear snapshot names for later reference
5. **List periodically**: Review and clean old snapshots
6. **Combine tools**: Use with /transcripts for full recovery option
7. **Trust emergence**: Don't over-snapshot, let context flow naturally

## Resources

- **Specification**: `Specs/context-management-skill.md`
- **Implementation**: `.claude/skills/context-management/`
- **Tests**: `.claude/skills/context-management/tests/`
- **Examples**: `.claude/skills/context-management/examples/`
- **Philosophy**: `.claude/context/PHILOSOPHY.md`

## Remember

This skill provides proactive context management without automatic behavior. You control when to snapshot and what detail to restore. It complements existing tools (PreCompact hook, /transcripts) rather than replacing them. Use it to maintain clean, efficient context throughout long sessions.
