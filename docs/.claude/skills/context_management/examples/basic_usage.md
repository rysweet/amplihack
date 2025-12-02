# Basic Usage Examples

Simple examples showing how to use the context-management skill for common tasks.

## Example 1: Check Token Usage

```python
from context_management import check_status

# Check current token usage
status = check_status(current_tokens=500_000)

print(f"Status: {status['status']}")
print(f"Percentage: {status['usage']['percentage']}%")
print(f"Recommendation: {status['usage']['recommendation']}")
```

**Output:**

```
Status: ok
Percentage: 50.0%
Recommendation: Context is healthy. No action needed.
```

## Example 2: Create a Snapshot

```python
from context_management import create_snapshot

# Sample conversation data
messages = [
    {'role': 'user', 'content': 'Build a JWT authentication system'},
    {'role': 'assistant', 'content': 'I decided to use RS256 encryption...'},
    {'role': 'tool_use', 'tool_name': 'Write', 'parameters': {}}
]

# Create snapshot
result = create_snapshot(
    conversation_data=messages,
    name='auth-implementation'
)

print(f"Snapshot ID: {result['snapshot']['snapshot_id']}")
print(f"Name: {result['snapshot']['name']}")
print(f"Token count: {result['snapshot']['token_count']}")
print(f"File: {result['snapshot']['file_path']}")
```

**Output:**

```
Snapshot ID: 20251116_143522
Name: auth-implementation
Token count: 1250
File: .claude/runtime/context-snapshots/20251116_143522.json
```

## Example 3: List All Snapshots

```python
from context_management import list_snapshots

# Get all snapshots
result = list_snapshots()

print(f"Total snapshots: {result['count']}")
print(f"Total size: {result['total_size']}")

for snapshot in result['snapshots']:
    print(f"\nID: {snapshot['id']}")
    print(f"Name: {snapshot['name']}")
    print(f"Created: {snapshot['timestamp']}")
    print(f"Size: {snapshot['size']}")
```

**Output:**

```
Total snapshots: 3
Total size: 55KB

ID: 20251116_143522
Name: auth-implementation
Created: 2025-11-16 14:35:22
Size: 15KB

ID: 20251116_092315
Name: database-migration
Created: 2025-11-16 09:23:15
Size: 22KB

ID: 20251115_163045
Name: frontend-redesign
Created: 2025-11-15 16:30:45
Size: 18KB
```

## Example 4: Rehydrate Context

```python
from context_management import rehydrate_context

# Rehydrate at essential level
result = rehydrate_context(
    snapshot_id='20251116_143522',
    level='essential'
)

if result['status'] == 'success':
    print(result['context'])
else:
    print(f"Error: {result['error']}")
```

**Output:**

```
# Restored Context: auth-implementation

*Snapshot created: 2025-11-16 14:35:22*

## Original Requirements

Build a JWT authentication system for API endpoints...

## Current State

JWT handler created, middleware integration in progress
Tests: 12/15 passing
```

## Example 5: Progressive Detail Levels

```python
from context_management import rehydrate_context

snapshot_id = '20251116_143522'

# Start with essential
print("=== ESSENTIAL LEVEL ===")
result = rehydrate_context(snapshot_id, level='essential')
print(f"Tokens: ~200")
print(result['context'][:200], "...\n")

# Upgrade to standard
print("=== STANDARD LEVEL ===")
result = rehydrate_context(snapshot_id, level='standard')
print(f"Tokens: ~800")
print(result['context'][:200], "...\n")

# Get comprehensive
print("=== COMPREHENSIVE LEVEL ===")
result = rehydrate_context(snapshot_id, level='comprehensive')
print(f"Tokens: ~1250")
print(result['context'][:200], "...")
```

## Example 6: Error Handling

```python
from context_management import (
    create_snapshot,
    rehydrate_context,
    list_snapshots
)

# Handle missing conversation data
result = create_snapshot(conversation_data=None, name='test')
if result['status'] == 'error':
    print(f"Error: {result['error']}")
    # Output: Error: conversation_data is required for snapshot action

# Handle non-existent snapshot
result = rehydrate_context('nonexistent_id')
if result['status'] == 'error':
    print(f"Error: {result['error']}")
    # Output: Error: Snapshot not found: nonexistent_id

    # List valid snapshots
    snapshots = list_snapshots()
    print(f"Valid snapshot IDs:")
    for snap in snapshots['snapshots']:
        print(f"  - {snap['id']}: {snap['name']}")
```

## Example 7: Using Main Skill Function

```python
from context_management import context_management_skill

# All actions through single function

# Status
result = context_management_skill('status', current_tokens=750_000)

# Snapshot
result = context_management_skill(
    'snapshot',
    conversation_data=messages,
    name='my-feature'
)

# Rehydrate
result = context_management_skill(
    'rehydrate',
    snapshot_id='20251116_143522',
    level='standard'
)

# List
result = context_management_skill('list')
```

## Example 8: Custom Configuration

```python
from pathlib import Path
from context_management import context_management_skill

# Custom snapshot directory
custom_dir = Path('/tmp/my-snapshots')

# Create snapshot in custom location
result = context_management_skill(
    'snapshot',
    conversation_data=messages,
    snapshot_dir=custom_dir,
    name='custom-location'
)

# List from custom location
result = context_management_skill('list', snapshot_dir=custom_dir)

# Custom max tokens
result = context_management_skill(
    'status',
    current_tokens=400_000,
    max_tokens=500_000  # 500k context window instead of 1M
)
```

## Example 9: Complete Workflow

```python
from context_management import (
    check_status,
    create_snapshot,
    rehydrate_context,
    list_snapshots
)

# Step 1: Monitor token usage
current_tokens = 850_000
status = check_status(current_tokens)

print(f"Current usage: {status['usage']['percentage']}%")
print(f"Status: {status['status']}")
print(f"Recommendation: {status['usage']['recommendation']}")

# Step 2: Create snapshot if recommended
if status['status'] in ['recommended', 'urgent']:
    print("\nCreating snapshot...")
    snapshot = create_snapshot(
        conversation_data=messages,
        name='high-usage-snapshot'
    )
    snapshot_id = snapshot['snapshot']['snapshot_id']
    print(f"Created: {snapshot_id}")

# Step 3: Continue working...
# [... Claude may compact context ...]

# Step 4: After compaction, rehydrate
print(f"\nRestoring context from {snapshot_id}...")
context = rehydrate_context(snapshot_id, level='essential')

if context['status'] == 'success':
    print("Context restored successfully!")
    print(f"\nRestored content preview:")
    print(context['context'][:300], "...")
```

## Tips

1. **Start Simple**: Use `essential` level first, upgrade if needed
2. **Name Descriptively**: Use clear names like 'auth-feature' not 'snapshot-1'
3. **Monitor Regularly**: Check status at natural breakpoints
4. **Handle Errors**: Always check `result['status']` before using data
5. **Clean Up**: Periodically review and remove old snapshots

## Next Steps

- See `proactive_workflow.md` for proactive context management patterns
- See `rehydration_levels.md` for when to use each detail level
- See `SKILL.md` for complete documentation
