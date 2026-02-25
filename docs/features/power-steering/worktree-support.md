# Power Steering Worktree Support

Power Steering now works seamlessly across git worktrees, providing consistent workflow validation and counter persistence regardless of where you work in your repository structure.

## What Changed

Previously, Power Steering had issues when working in git worktrees:

- `.disabled` file detection failed (only checked current directory)
- Block counters reset on every invocation (no shared state)
- No hard maximum enforcement (potential infinite loops)
- Confusing error messages

These issues are now resolved. Power Steering works identically in worktrees and standard repositories.

## Quick Start

### Using Power Steering in Worktrees

Power Steering automatically detects worktree environments and uses shared state directories. No configuration changes required.

```bash
# Create a worktree
git worktree add ../feature-branch feature-branch

# Work in the worktree
cd ../feature-branch

# Power Steering works normally
# - Block counter persists across invocations
# - .disabled file detection works from any location
# - Hard maximum prevents infinite loops
```

### Disabling Power Steering

Create a `.disabled` file in any of these locations (checked in order):

1. **Current working directory**: `touch .disabled`
2. **Shared Git directory**: `touch $(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled`
3. **Project root**: `cd $(git rev-parse --show-toplevel) && touch .disabled`

Power Steering checks all three locations automatically.

```bash
# Example: Disable from worktree
cd /path/to/worktree
touch .disabled

# Or disable globally for all worktrees
touch "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled"
```

## Features

### Worktree Detection

Power Steering automatically detects git worktrees using `git rev-parse --git-common-dir`:

```python
from amplihack.tools.amplihack.git_utils import (
    get_common_git_dir,
    is_worktree
)

# Check if current directory is a worktree
if is_worktree():
    print("Working in a worktree")

# Get shared Git directory
common_dir = get_common_git_dir()
# Returns: /path/to/main/repo/.git
```

### Shared State Persistence

Counter state persists across all worktrees using a shared runtime directory:

- **State location**: `$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/`
- **Counter file**: `workflow_classification_block_counter.json`
- **Shared across**: All worktrees and main repository

```json
{
  "count": 3,
  "last_updated": "2026-02-25T10:30:45Z",
  "hard_maximum": 10
}
```

### Hard Maximum Enforcement

After 10 consecutive blocks, Power Steering automatically approves to prevent infinite loops:

```
POWER STEERING: Classification blocked 10 times (hard maximum reached)
Automatically approving to prevent infinite loop.

CRITICAL: This indicates a systematic problem.
File an issue: https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues
```

### Multi-Path .disabled Check

Power Steering checks three locations for the `.disabled` file:

1. Current working directory (most convenient)
2. Shared Git directory (affects all worktrees)
3. Project root (backward compatible)

```python
# Example: Multi-path check
from amplihack.tools.amplihack.git_utils import find_disabled_file

disabled_file = find_disabled_file()
if disabled_file:
    print(f"Power Steering disabled via: {disabled_file}")
```

## Common Workflows

### Working Across Multiple Worktrees

```bash
# Main branch
cd /path/to/main-repo
# Counter: 0

# Create feature worktree
git worktree add ../feature-a feature-a
cd ../feature-a
# Counter: 0 (shared state)

# Block classification
# Counter: 1 (persisted to shared location)

# Switch to different worktree
git worktree add ../feature-b feature-b
cd ../feature-b
# Counter: 1 (reads shared state)

# Block again
# Counter: 2 (updates shared state)
```

### Disabling Globally vs Locally

```bash
# Disable for current worktree only
touch .disabled

# Disable for all worktrees (main repo + all worktrees)
touch "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled"

# Remove global disable
rm "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled"
```

## Backward Compatibility

Power Steering remains fully compatible with non-worktree repositories:

- Standard repos use `.git/` directory normally
- `.disabled` file still works in project root
- Counter persistence works identically
- No configuration changes required

## Troubleshooting

### Counter Not Persisting

**Problem**: Block counter resets on every invocation

**Solution**: Check shared state directory exists

```bash
# Verify shared directory
echo "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/"

# Create if missing
mkdir -p "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/"
```

### .disabled File Not Detected

**Problem**: Power Steering still blocks despite `.disabled` file

**Solution**: Check file location

```bash
# Show all checked locations
python3 << 'EOF'
from amplihack.tools.amplihack.git_utils import find_disabled_file
result = find_disabled_file()
if result:
    print(f"Found: {result}")
else:
    print("Not found in any checked location")
EOF
```

### Hard Maximum Triggered

**Problem**: Hit 10-block limit and auto-approved

**Action**: This indicates a bug. File an issue with:

1. Session logs showing repeated blocks
2. Classification attempts and reasons
3. Worktree configuration details

**Temporary workaround**: Reset counter manually

```bash
rm "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/workflow_classification_block_counter.json"
```

## Related Documentation

- [Power Steering Overview](./README.md) - Core concepts and philosophy
- [Configuration Guide](./configuration.md) - Complete configuration options
- [Troubleshooting Guide](./troubleshooting.md) - Fix common issues
- [Migration Guide v0.9.1](./migration-v0.9.1.md) - Upgrade from earlier versions
