# Context Management Skill - Quick Start

One-page reference for the context-management skill.

## Four Actions

| Action      | Purpose           | Key Parameters                         |
| ----------- | ----------------- | -------------------------------------- |
| `status`    | Check token usage | `current_tokens`                       |
| `snapshot`  | Save context      | `conversation_data`, `name` (optional) |
| `rehydrate` | Restore context   | `snapshot_id`, `level`                 |
| `list`      | Show snapshots    | none                                   |

## Basic Usage

```python
from context_management import context_management_skill

# 1. Check status
result = context_management_skill('status', current_tokens=750000)
# Returns: {'status': 'consider', 'usage': {...}}

# 2. Create snapshot
result = context_management_skill(
    'snapshot',
    conversation_data=messages,
    name='feature-name'
)
# Returns: {'status': 'success', 'snapshot': {'snapshot_id': '...'}}

# 3. Rehydrate context
result = context_management_skill(
    'rehydrate',
    snapshot_id='20251116_143522',
    level='essential'
)
# Returns: {'status': 'success', 'context': '# Restored Context...'}

# 4. List snapshots
result = context_management_skill('list')
# Returns: {'snapshots': [...], 'count': N}
```

## Convenience Functions

```python
from context_management import (
    check_status,
    create_snapshot,
    rehydrate_context,
    list_snapshots
)

# Simpler API
status = check_status(current_tokens=750000)
snapshot = create_snapshot(messages, name='my-feature')
context = rehydrate_context('20251116_143522', level='standard')
snapshots = list_snapshots()
```

## Token Thresholds

| Percentage | Status        | Recommendation        |
| ---------- | ------------- | --------------------- |
| 0-50%      | `ok`          | No action needed      |
| 70-85%     | `consider`    | Consider snapshotting |
| 85-95%     | `recommended` | Snapshot recommended  |
| 95-100%    | `urgent`      | Snapshot immediately  |

## Rehydration Levels

| Level           | Contains                  | Tokens | Use When         |
| --------------- | ------------------------- | ------ | ---------------- |
| `essential`     | Requirements + state      | ~200   | Just need basics |
| `standard`      | + decisions + open items  | ~800   | Normal usage     |
| `comprehensive` | + full details + metadata | ~1250  | Need everything  |

## Typical Workflow

```python
# 1. Monitor usage
status = check_status(current_tokens=850000)

# 2. If recommended, create snapshot
if status['status'] == 'recommended':
    snapshot = create_snapshot(messages, name='current-work')
    snapshot_id = snapshot['snapshot']['snapshot_id']

# 3. Continue working...
# [Claude may compact context naturally]

# 4. After compaction, rehydrate
context = rehydrate_context(snapshot_id, level='essential')
# Claude now has essential context restored
```

## Quick Examples

### Example 1: Preventive Snapshot

```python
# Before starting risky operation
status = check_status(current_tokens=current)
if status['status'] != 'ok':
    create_snapshot(messages, name='before-refactor')
```

### Example 2: Context Switching

```python
# Pause feature A
snap_a = create_snapshot(messages, name='feature-a')

# Work on feature B...

# Resume feature A
context = rehydrate_context(snap_a['snapshot']['snapshot_id'])
```

### Example 3: Progressive Restoration

```python
# Start minimal
context = rehydrate_context(snapshot_id, level='essential')

# Need more? Upgrade
context = rehydrate_context(snapshot_id, level='standard')

# Still need more? Go comprehensive
context = rehydrate_context(snapshot_id, level='comprehensive')
```

## Common Patterns

### Pattern: Monitor-Snapshot-Rehydrate

```
1. check_status() → If 70%+, create snapshot
2. create_snapshot() → Save current context
3. Continue working → Let Claude manage naturally
4. rehydrate_context() → Restore after compaction
```

### Pattern: Snapshot at Milestones

```
# After completing major tasks
create_snapshot(messages, name='api-completed')
create_snapshot(messages, name='tests-passing')
create_snapshot(messages, name='ready-for-review')
```

## Error Handling

```python
# Status always succeeds
status = check_status(current_tokens=current)

# Snapshot requires conversation_data
result = create_snapshot(messages, name='my-feature')
if result['status'] == 'error':
    print(result['error'])

# Rehydrate requires valid snapshot_id
result = rehydrate_context('invalid_id')
if result['status'] == 'error':
    # Snapshot not found - list to find valid IDs
    snapshots = list_snapshots()

# List always succeeds (returns empty list if none)
result = list_snapshots()
```

## File Locations

| What         | Where                                                          |
| ------------ | -------------------------------------------------------------- |
| Snapshots    | `.claude/runtime/context-snapshots/*.json`                     |
| Transcripts  | `.claude/runtime/logs/<session_id>/CONVERSATION_TRANSCRIPT.md` |
| Session logs | `.claude/runtime/logs/<session_id>/`                           |

## Integration

| Tool                | Purpose        | When                        |
| ------------------- | -------------- | --------------------------- |
| **PreCompact Hook** | Safety net     | Automatic before compaction |
| **/transcripts**    | Full recovery  | After compaction            |
| **Context Skill**   | Proactive mgmt | User-initiated              |

All three are complementary.

## Configuration Options

```python
# Custom snapshot directory
context_management_skill(
    'snapshot',
    conversation_data=messages,
    snapshot_dir='/custom/path'
)

# Custom max tokens
context_management_skill(
    'status',
    current_tokens=current,
    max_tokens=500_000
)
```

## Testing

```bash
# Run all tests
pytest .claude/skills/context-management/tests/

# Run with coverage
pytest --cov=context_management tests/
```

## Troubleshooting

| Problem            | Solution                                 |
| ------------------ | ---------------------------------------- |
| Snapshot not found | Use `list_snapshots()` to find valid IDs |
| Corrupted snapshot | Create new snapshot with fresh data      |
| Token estimate off | Expected - uses rough approximation      |

## Philosophy

- **Proactive**: User decides when to snapshot
- **Selective**: Extract essentials, not full dump
- **Flexible**: Three detail levels for rehydration
- **Simple**: Four bricks, clear contracts
- **Standard library**: No external dependencies

## Remember

1. Monitor usage periodically
2. Snapshot at 70-85% threshold
3. Start with `essential` level
4. Upgrade detail level if needed
5. Name snapshots descriptively
6. Clean old snapshots occasionally

## More Information

- **Complete docs**: See `SKILL.md`
- **Architecture**: See `README.md`
- **Specification**: See `Specs/context-management-skill.md`
- **Examples**: See `examples/` directory
