# Migration Guide: Power Steering Worktree Support

Guide for users upgrading from pre-worktree Power Steering to the worktree-aware version.

## What's New

Power Steering now includes full git worktree support with:

1. **Shared state persistence** - Counter works across all worktrees
2. **Multi-path .disabled detection** - Check current dir, shared dir, and project root
3. **Hard maximum enforcement** - Automatic approval after 10 blocks
4. **Clear error messages** - Actionable instructions for fixes

## Do You Need to Migrate?

Check if you're affected:

```bash
# Are you using git worktrees?
git worktree list

# If this shows multiple entries, you'll benefit from the upgrade
```

If you see multiple worktrees, the upgrade fixes:

- Counter resetting in worktrees (now persists)
- .disabled file not working (now checks multiple locations)
- Potential infinite loops (now has hard maximum)

## Migration Steps

### Step 1: Backup Current State

```bash
# Backup existing counter (if in main repo)
if [ -f .git/.claude/runtime/power-steering/workflow_classification_block_counter.json ]; then
    cp .git/.claude/runtime/power-steering/workflow_classification_block_counter.json \
       /tmp/power-steering-backup.json
    echo "Backed up counter state"
fi
```

### Step 2: Upgrade amplihack

```bash
# Pull latest changes
git pull origin main

# Or reinstall via uvx
uvx --from git+https://github.com/rysweet/amplihack amplihack --reinstall
```

### Step 3: Verify Installation

```bash
# Check git_utils module exists
python3 << 'EOF'
try:
    from amplihack.tools.amplihack.git_utils import (
        is_worktree,
        get_common_git_dir,
        find_disabled_file
    )
    print("✓ git_utils module installed")
except ImportError as e:
    print(f"✗ git_utils not found: {e}")
EOF
```

### Step 4: Migrate State (Automatic)

The new version automatically handles state migration:

**Before** (pre-worktree):

```
.git/.claude/runtime/power-steering/
└── workflow_classification_block_counter.json
```

**After** (worktree-aware):

```
$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/
└── workflow_classification_block_counter.json
```

In standard repos, these are the same location. No action required.

### Step 5: Migrate .disabled Files

If you had .disabled files in worktrees, move them to shared location:

```bash
# Check for .disabled files in worktrees
git worktree list | awk '{print $1}' | while read worktree; do
    if [ -f "$worktree/.disabled" ]; then
        echo "Found .disabled in: $worktree"
        # Move to shared location
        touch "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled"
        echo "Migrated to shared location"
        rm "$worktree/.disabled"
    fi
done
```

### Step 6: Test Worktree Functionality

```bash
# Create test worktree
git worktree add /tmp/test-worktree-migration main

# Test counter persistence
cd /tmp/test-worktree-migration
python3 << 'EOF'
from amplihack.tools.amplihack.git_utils import get_common_git_dir
from pathlib import Path
import json

common_dir = get_common_git_dir()
counter_file = Path(common_dir) / ".claude" / "runtime" / "power-steering" / "workflow_classification_block_counter.json"

# Write test counter
counter_file.parent.mkdir(parents=True, exist_ok=True)
counter_file.write_text(json.dumps({"count": 3}))

print(f"Counter written to: {counter_file}")
print(f"Count: {json.loads(counter_file.read_text())['count']}")
EOF

# Cleanup
cd -
git worktree remove /tmp/test-worktree-migration
```

## Configuration Changes

### No Configuration Required

The upgrade is **backward compatible**. No configuration changes needed.

### Optional: Centralize .disabled File

For worktree users, centralize .disabled file:

```bash
# Old: .disabled in each worktree (still works)
# New: .disabled in shared location (recommended)

# Create shared .disabled
touch "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled"

# Remove individual worktree .disabled files
git worktree list | awk '{print $1}' | while read worktree; do
    rm -f "$worktree/.disabled"
done
```

## Breaking Changes

### None

This release has **no breaking changes**. All existing functionality works identically.

### Behavior Changes

1. **Counter persists across worktrees** (previously reset)
2. **.disabled file checked in 3 locations** (previously only CWD and root)
3. **Hard maximum enforced** (new feature, prevents infinite loops)

## Rollback Plan

If you encounter issues, rollback to previous version:

```bash
# Restore from backup
if [ -f /tmp/power-steering-backup.json ]; then
    cp /tmp/power-steering-backup.json \
       .git/.claude/runtime/power-steering/workflow_classification_block_counter.json
fi

# Revert amplihack
git checkout <previous-version-tag>

# Or reinstall specific version
uvx --from git+https://github.com/rysweet/amplihack@<version> amplihack
```

## Verification Checklist

After migration, verify these work:

- [ ] Counter persists in main repo
- [ ] Counter persists in worktrees
- [ ] Counter shared across all worktrees
- [ ] .disabled file works in current directory
- [ ] .disabled file works in shared location
- [ ] .disabled file works in project root
- [ ] Hard maximum triggers after 10 blocks
- [ ] Error messages are clear

Run this verification script:

```bash
python3 << 'EOF'
import subprocess
from pathlib import Path
import json

print("=== Power Steering Migration Verification ===\n")

# Test 1: Worktree detection
from amplihack.tools.amplihack.git_utils import is_worktree, get_common_git_dir
print(f"✓ Worktree detection: {is_worktree()}")
print(f"✓ Common dir: {get_common_git_dir()}")

# Test 2: State directory
state_dir = Path(get_common_git_dir()) / ".claude" / "runtime" / "power-steering"
state_dir.mkdir(parents=True, exist_ok=True)
print(f"✓ State directory: {state_dir}")

# Test 3: Counter persistence
counter_file = state_dir / "workflow_classification_block_counter.json"
counter_file.write_text(json.dumps({"count": 5}))
assert json.loads(counter_file.read_text())["count"] == 5
print(f"✓ Counter persistence works")

# Test 4: .disabled detection
from amplihack.tools.amplihack.git_utils import find_disabled_file
test_disabled = state_dir / ".disabled"
test_disabled.touch()
assert find_disabled_file() is not None
test_disabled.unlink()
print(f"✓ .disabled detection works")

print("\n=== All Tests Passed ===")
EOF
```

## Common Migration Issues

### Issue: Module Not Found

**Symptom**: `ImportError: No module named 'amplihack.tools.amplihack.git_utils'`

**Solution**: Reinstall amplihack

```bash
uvx --from git+https://github.com/rysweet/amplihack amplihack --reinstall
```

### Issue: Counter Not Migrating

**Symptom**: Counter reset to 0 after upgrade

**Solution**: Manually migrate counter

```bash
# Copy old counter to new location
OLD_COUNTER=".git/.claude/runtime/power-steering/workflow_classification_block_counter.json"
NEW_COUNTER="$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/workflow_classification_block_counter.json"

if [ -f "$OLD_COUNTER" ] && [ "$OLD_COUNTER" != "$NEW_COUNTER" ]; then
    mkdir -p "$(dirname "$NEW_COUNTER")"
    cp "$OLD_COUNTER" "$NEW_COUNTER"
    echo "Counter migrated"
fi
```

### Issue: .disabled File Not Working

**Symptom**: Created .disabled but Power Steering still blocks

**Solution**: Check file location

```bash
# Verify .disabled file location
python3 << 'EOF'
from amplihack.tools.amplihack.git_utils import find_disabled_file
result = find_disabled_file()
if result:
    print(f"Found: {result}")
else:
    print("Not found. Create in one of:")
    print("  1. ./.disabled")
    print("  2. $(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled")
    print("  3. $(git rev-parse --show-toplevel)/.disabled")
EOF
```

## Getting Help

If you encounter migration issues:

1. **Run diagnostic**: See [Troubleshooting Guide](../../howto/power-steering-worktree-troubleshooting.md)
2. **Check logs**: `~/.claude/runtime/logs/power-steering-*.log`
3. **File issue**: [GitHub Issues](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)

Include this diagnostic output:

```bash
# Generate diagnostic report
python3 << 'EOF'
import subprocess
from amplihack.tools.amplihack.git_utils import is_worktree, get_common_git_dir, find_disabled_file

print("=== Migration Diagnostic ===")
print(f"amplihack version: {subprocess.check_output(['amplihack', '--version'], text=True).strip()}")
print(f"Is worktree: {is_worktree()}")
print(f"Common dir: {get_common_git_dir()}")
print(f"Disabled file: {find_disabled_file()}")
print("=== End Diagnostic ===")
EOF
```

## Related Documentation

- [Power Steering Worktree Support](./worktree-support.md) - Feature overview
- [How to Troubleshoot Worktrees](../../howto/power-steering-worktree-troubleshooting.md) - Fix common issues
- [Git Utils API Reference](../../reference/git-utils-api.md) - Technical documentation
- [Power Steering Configuration](./configuration.md) - Configuration options
