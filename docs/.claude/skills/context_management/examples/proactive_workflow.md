# Proactive Context Management Workflow

Real-world examples of proactive context management patterns using this skill.

## Scenario 1: Long Feature Implementation

### Context

You're implementing a complex authentication system that requires multiple iterations and may exceed token limits.

### Workflow

```python
from context_management import check_status, create_snapshot, rehydrate_context

# === PHASE 1: Start Implementation ===
# Begin working on authentication feature
# [... initial implementation ...]

# Check token usage after initial work
status = check_status(current_tokens=500_000)
print(f"After initial implementation: {status['usage']['percentage']}% used")
# Output: "50% used" - All good

# === PHASE 2: Continue Development ===
# Add JWT validation, middleware, tests
# [... more implementation ...]

# Check again
status = check_status(current_tokens=750_000)
print(f"After JWT implementation: {status['usage']['percentage']}% used")
print(f"Recommendation: {status['usage']['recommendation']}")
# Output: "75% used" - "Consider creating snapshot soon"

# === PHASE 3: Approaching Threshold ===
# Add refresh token logic
# [... more implementation ...]

# Check again
status = check_status(current_tokens=870_000)
print(f"After refresh tokens: {status['usage']['percentage']}% used")
# Output: "87% used" - "Snapshot recommended"

# Create snapshot NOW
snapshot = create_snapshot(
    conversation_data=messages,
    name='auth-before-error-handling'
)
snapshot_id = snapshot['snapshot']['snapshot_id']
print(f"Snapshot created: {snapshot_id}")

# === PHASE 4: Continue Safely ===
# Continue with error handling implementation
# Let Claude manage context naturally
# If compaction happens, no problem - we have snapshot

# === PHASE 5: After Compaction ===
# If context was compacted, restore essentials
context = rehydrate_context(snapshot_id, level='essential')
print("Essential context restored. Continuing work...")
```

## Scenario 2: Context Switching Between Features

### Context

You need to switch between multiple features frequently without losing context.

### Workflow

```python
from context_management import create_snapshot, rehydrate_context, list_snapshots

# === Working on Feature A ===
# Implement payment processing
# [... implementation ...]

# Need to switch to urgent bug fix
# Save Feature A context
snapshot_a = create_snapshot(
    messages_a,
    name='feature-a-payment-processing'
)
feature_a_id = snapshot_a['snapshot']['snapshot_id']
print(f"Feature A saved: {feature_a_id}")

# === Switch to Bug Fix ===
# Start fresh conversation for bug fix
# [... bug fix work ...]

# Bug fixed, now need to switch to Feature B
# [... Feature B work ...]

# === Later: Resume Feature A ===
# List available snapshots
snapshots = list_snapshots()
for snap in snapshots['snapshots']:
    if 'payment' in snap['name'].lower():
        print(f"Found Feature A snapshot: {snap['id']}")

# Restore Feature A context
context = rehydrate_context(feature_a_id, level='standard')
print("Feature A context restored. Continuing where I left off...")
```

## Scenario 3: Preventive Snapshotting Before Risky Operations

### Context

You're about to perform a large refactoring that might use a lot of tokens for discussion.

### Workflow

```python
from context_management import check_status, create_snapshot

# === Before Refactoring ===
# Check current state
status = check_status(current_tokens=650_000)
print(f"Current usage: {status['usage']['percentage']}%")

# Even though we're only at 65%, create preventive snapshot
# because refactoring discussion will use many tokens
snapshot = create_snapshot(
    messages,
    name='before-large-refactoring'
)
snapshot_id = snapshot['snapshot']['snapshot_id']
print(f"Preventive snapshot created: {snapshot_id}")
print("Safe to proceed with refactoring discussion.")

# === During Refactoring ===
# Extensive discussion about refactoring approaches
# Multiple iterations, code reviews, adjustments
# [... large refactoring discussion ...]

# === Monitor Throughout ===
status = check_status(current_tokens=920_000)
if status['status'] == 'urgent':
    print("Token usage critical!")
    # Create another snapshot at this point
    snapshot2 = create_snapshot(
        messages,
        name='refactoring-in-progress'
    )
    print(f"Progress snapshot created: {snapshot2['snapshot']['snapshot_id']}")
```

## Scenario 4: Team Handoff

### Context

You need to hand off work to a teammate with full context.

### Workflow

```python
from context_management import create_snapshot

# === End of Your Work Session ===
# Create comprehensive snapshot for handoff
snapshot = create_snapshot(
    messages,
    name='handoff-to-alice-api-implementation'
)

# Share snapshot details
print(f"""
Handoff Package:
----------------
Snapshot ID: {snapshot['snapshot']['snapshot_id']}
Name: {snapshot['snapshot']['name']}
Location: {snapshot['snapshot']['file_path']}
Token Count: {snapshot['snapshot']['token_count']}

Components included:
- Original requirements
- Key architecture decisions
- Current implementation state
- Open items and blockers
- Tools/files modified

Alice can restore this with:
rehydrate_context('{snapshot['snapshot']['snapshot_id']}', level='comprehensive')
""")

# === Alice's Side (Later) ===
# Alice starts new session and restores context
from context_management import rehydrate_context

context = rehydrate_context(
    '20251116_143522',  # The snapshot ID you shared
    level='comprehensive'  # Full details for handoff
)

print("Full context restored. I can continue from where you left off.")
print(context['context'])
```

## Scenario 5: Milestone Snapshots

### Context

Create snapshots at key milestones for easy rollback or reference.

### Workflow

```python
from context_management import create_snapshot

# === Milestone 1: Basic Implementation Complete ===
snapshot1 = create_snapshot(
    messages,
    name='milestone-01-basic-auth-complete'
)
print(f"Milestone 1 saved: {snapshot1['snapshot']['snapshot_id']}")

# Continue to next phase
# [... add middleware integration ...]

# === Milestone 2: Middleware Integration Complete ===
snapshot2 = create_snapshot(
    messages,
    name='milestone-02-middleware-complete'
)
print(f"Milestone 2 saved: {snapshot2['snapshot']['snapshot_id']}")

# Continue to next phase
# [... add tests ...]

# === Milestone 3: Tests Passing ===
snapshot3 = create_snapshot(
    messages,
    name='milestone-03-tests-passing'
)
print(f"Milestone 3 saved: {snapshot3['snapshot']['snapshot_id']}")

# Now you have snapshots at each major milestone
# Can restore to any point if needed
```

## Scenario 6: Progressive Detail Restoration

### Context

Start with minimal context, progressively add more as needed.

### Workflow

```python
from context_management import rehydrate_context

snapshot_id = '20251116_143522'

# === Phase 1: Quick Refresh ===
# Start with just the essentials
print("=== Quick Refresh (Essential) ===")
context = rehydrate_context(snapshot_id, level='essential')
print(f"Restored: Requirements + Current State")
print(f"Token cost: ~200 tokens")

# Try to continue work
# [... working ...]

# Realize you need to know the decisions made
print("\n=== Need More Context (Standard) ===")
context = rehydrate_context(snapshot_id, level='standard')
print(f"Now have: + Key Decisions + Open Items")
print(f"Token cost: ~800 tokens")

# Continue work
# [... working ...]

# Need full context for complex debugging
print("\n=== Need Everything (Comprehensive) ===")
context = rehydrate_context(snapshot_id, level='comprehensive')
print(f"Now have: Everything + Metadata")
print(f"Token cost: ~1250 tokens")

# Now have full context for debugging
```

## Scenario 7: Automated Monitoring Loop

### Context

Integrate token monitoring into your workflow.

### Workflow

```python
from context_management import check_status, create_snapshot

class ContextManager:
    """Helper class for automated monitoring."""

    def __init__(self):
        self.last_snapshot_id = None
        self.snapshots_created = 0

    def check_and_snapshot(self, current_tokens, messages, task_name=None):
        """Check usage and create snapshot if recommended."""
        status = check_status(current_tokens)

        print(f"Token usage: {status['usage']['percentage']}%")
        print(f"Status: {status['status']}")

        if status['status'] in ['recommended', 'urgent']:
            print(f"Creating snapshot (threshold reached)...")

            snapshot_name = task_name or f'auto-snapshot-{self.snapshots_created + 1}'
            result = create_snapshot(messages, name=snapshot_name)

            if result['status'] == 'success':
                self.last_snapshot_id = result['snapshot']['snapshot_id']
                self.snapshots_created += 1
                print(f"Snapshot created: {self.last_snapshot_id}")
                return self.last_snapshot_id

        return None

# Usage in workflow
manager = ContextManager()

# Check periodically throughout work
manager.check_and_snapshot(500_000, messages, 'initial-implementation')
# Output: "Token usage: 50%, Status: ok"

manager.check_and_snapshot(750_000, messages, 'middleware-added')
# Output: "Token usage: 75%, Status: consider"

manager.check_and_snapshot(880_000, messages, 'tests-added')
# Output: "Token usage: 88%, Status: recommended"
# "Creating snapshot... Snapshot created: 20251116_143522"
```

## Best Practices

### 1. Monitor Regularly

```python
# Check at natural breakpoints
# - After completing a module
# - Before starting complex discussions
# - Every hour in long sessions
status = check_status(current_tokens=current)
```

### 2. Name Descriptively

```python
# Good naming
create_snapshot(messages, name='auth-jwt-validation-complete')
create_snapshot(messages, name='before-database-refactoring')
create_snapshot(messages, name='handoff-to-bob-frontend-work')

# Bad naming
create_snapshot(messages, name='snapshot1')
create_snapshot(messages, name='temp')
create_snapshot(messages, name='test')
```

### 3. Create Snapshots Proactively

```python
# Don't wait for 95% - snapshot at 70-85%
if status['status'] in ['consider', 'recommended']:
    create_snapshot(messages, name=f'{current_task}-snapshot')
```

### 4. Start Minimal on Restoration

```python
# Always start with essential
context = rehydrate_context(snapshot_id, level='essential')

# Only upgrade if needed
if need_more_context:
    context = rehydrate_context(snapshot_id, level='standard')
```

### 5. Clean Up Old Snapshots

```python
from context_management import list_snapshots

# Periodically review snapshots
snapshots = list_snapshots()
print(f"You have {snapshots['count']} snapshots using {snapshots['total_size']}")

# Manually delete old snapshots from .claude/runtime/context-snapshots/
# Keep only active work and important milestones
```

## Remember

- **Proactive > Reactive**: Create snapshots before problems
- **Monitor Often**: Check token usage regularly
- **Name Well**: Descriptive names help later
- **Start Small**: Use essential level first
- **Trust System**: Let Claude manage context naturally

## Next Steps

- See `rehydration_levels.md` for detail level guidance
- See `basic_usage.md` for syntax examples
- See `SKILL.md` for complete documentation
