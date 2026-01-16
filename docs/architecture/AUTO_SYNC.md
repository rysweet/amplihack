# Automatic Sync Strategy for Copilot CLI

**Last Updated**: 2026-01-16
**Status**: Production

## Problem Statement

`.github/commands/` must stay in sync with `.claude/commands/`, but manual sync is error-prone and easily forgotten.

## Solution: Multi-Layer Automation

### Layer 1: Pre-commit Hook (Primary) ✅

**Location**: `.claude/tools/amplihack/hooks/pre_commit_sync.py`

**Triggers**: When `.claude/commands/` files are staged for commit

**Action**:
1. Detects staged changes in `.claude/commands/`
2. Runs `amplihack sync-commands --force`
3. Auto-stages generated `.github/commands/` files
4. Allows commit to proceed with synced files

**User Experience**:
```bash
# User edits command
vim .claude/commands/amplihack/ultrathink.md

# User commits
git add .claude/commands/amplihack/ultrathink.md
git commit -m "Update ultrathink command"

# Hook automatically:
# 📝 .claude/commands/ changed - auto-syncing...
# ✅ Commands synced successfully
# ✅ Pre-commit hook: Commands auto-synced and staged
# [main abc123] Update ultrathink command
#  2 files changed... (.claude/commands/ + .github/commands/)
```

**Configuration**: Added to `.pre-commit-config.yaml`:
```yaml
- repo: local
  hooks:
    - id: amplihack-sync-commands
      name: Auto-sync Copilot CLI commands
      entry: .claude/tools/amplihack/hooks/pre_commit_sync.py
      language: python
      files: '^\.claude/commands/'
      pass_filenames: false
```

### Layer 2: CI Validation (Safety Net) ✅

**Location**: `.github/workflows/validate-copilot-sync.yml`

**Triggers**: On PR/push when commands change

**Action**:
1. Checks if `.claude/commands/` and `.github/commands/` are in sync
2. FAILS CI if out of sync
3. Provides clear error message with fix instructions

**Why Both Layers?**:
- Pre-commit: Catches 99% of cases (developer workflow)
- CI: Safety net if pre-commit bypassed (--no-verify) or not installed

### Layer 3: Session Start Check (Optional)

**Location**: `.claude/tools/amplihack/hooks/copilot_session_start.py`

**Triggers**: When starting Copilot CLI session

**Action**:
1. Checks staleness of `.github/commands/`
2. Prompts to sync if stale (based on config)
3. Respects user preference (always/never/ask)

**Configuration**:
```json
{
  "copilot_auto_sync_commands": "ask"
}
```

## Why This Approach?

### Philosophy Alignment

✅ **Single Source of Truth**: `.claude/commands/` is authoritative
✅ **Automation**: Pre-commit hook eliminates manual steps
✅ **Fail-Safe**: CI validation catches bypassed pre-commit
✅ **User Control**: Can disable via `--no-verify` if needed
✅ **Zero-BS**: Sync happens or commit is blocked

### User Benefits

1. **No Manual Work**: Sync happens automatically
2. **Always Current**: .github/commands/ stays synchronized
3. **Fast Feedback**: Pre-commit is faster than CI
4. **Clear Errors**: If sync fails, get actionable message

### Comparison with Manual Sync

| Approach | User Action Required | Error Prone | CI Catches Issues |
|----------|---------------------|-------------|-------------------|
| **Manual Sync** | Run `amplihack sync-commands` | YES | Maybe (if remembered) |
| **Pre-commit Hook** | None (automatic) | NO | Always (CI validates) |

## Edge Cases Handled

### 1. Pre-commit Hook Not Installed

**Scenario**: User hasn't run `pre-commit install`
**Detection**: CI validation fails
**Message**: "Run 'pre-commit install' or 'amplihack sync-commands'"

### 2. Sync Command Fails

**Scenario**: `amplihack sync-commands` returns error
**Behavior**: Commit is blocked
**Message**: Error details + fix instructions
**User can**: Fix error or bypass with `--no-verify`

### 3. User Bypasses Pre-commit

**Scenario**: `git commit --no-verify`
**Detection**: CI validation fails
**Message**: "Commands out of sync - run amplihack sync-commands"
**Prevents**: Merge until fixed

### 4. Copilot CLI Not Installed

**Scenario**: `amplihack` command not available
**Behavior**: Hook reports error but doesn't block
**Fallback**: CI validation will catch it

## Installation

### Enable Auto-Sync

```bash
# Install pre-commit hooks (one-time)
pre-commit install

# Now commits automatically sync commands!
```

### Disable Auto-Sync

```bash
# Temporarily bypass for single commit
git commit --no-verify

# Permanently disable hook
pre-commit uninstall

# Or edit .pre-commit-config.yaml and remove amplihack-sync-commands hook
```

## Testing

### Manual Test

```bash
# 1. Edit a command
echo "# Test change" >> .claude/commands/amplihack/test.md

# 2. Stage and commit
git add .claude/commands/amplihack/test.md
git commit -m "test"

# Expected: Hook auto-syncs and includes .github/commands/ in commit
```

### CI Test

```bash
# 1. Make PR with command change but skip pre-commit
git commit --no-verify -m "test"
git push

# Expected: CI fails with sync error
```

## Maintenance

### When to Update This System

1. **New converter**: If command conversion logic changes
2. **New file types**: If syncing more than just commands
3. **Performance**: If sync becomes slow (> 5 seconds)

### Future Enhancements

Potential additions:
- Auto-sync agents if conversion format changes
- Auto-sync skills if YAML format changes
- File watcher for development (inotify)
- Git post-merge hook to sync after pulling

## Related Files

- `.claude/tools/amplihack/hooks/pre_commit_sync.py` - Pre-commit hook
- `.pre-commit-config.yaml` - Hook configuration
- `.github/workflows/validate-copilot-sync.yml` - CI validation
- `src/amplihack/adapters/copilot_command_converter.py` - Sync logic
- `docs/architecture/COPILOT_SYNC_STRATEGY.md` - Overall strategy

---

**Result**: Commands stay in sync automatically, no manual intervention needed! ⚓
