# Automode Worktree Isolation Guide

**Strategy 2: Automatic Worktree Creation**

This guide explains how automode automatically uses git worktrees for complete isolation from your active development directory.

## Overview

Automode now automatically creates and uses git worktrees by default, ensuring:
- Complete isolation from active session
- No file conflicts with .claude/ directory
- Protection of uncommitted changes
- Ability to run multiple automode sessions in parallel
- Automatic cleanup after completion

## How It Works

When you launch automode with `--auto`, the system automatically:

1. Creates a new git worktree in `./worktrees/automode-{task}-{timestamp}`
2. Creates a new branch for the worktree
3. Runs automode in the isolated worktree directory
4. Cleans up the worktree and branch after completion

## Basic Usage

### Default Behavior (Recommended)

Automode uses worktrees by default - no flags needed:

```bash
# Worktree isolation is automatic
amplihack claude --auto --max-turns 10 -- -p "implement user authentication"
```

This will:
- Create worktree at `./worktrees/automode-implement-user-authentication-1234567890/`
- Create branch `automode-implement-user-authentication-1234567890`
- Run automode in complete isolation
- Clean up automatically when done

### Disable Worktrees (Not Recommended)

To run in current directory without worktree isolation:

```bash
# Not recommended - can conflict with active session
amplihack claude --auto --no-worktree -- -p "task description"
```

**Warning**: Only disable worktrees if:
- You understand the risks
- You have committed all important changes
- You're not running other automode sessions
- You're not in an active Claude Code session

## Parallel Execution

With automatic worktree isolation, you can safely run multiple automode sessions in parallel:

```bash
# Launch 3 automode sessions in parallel - all automatically isolated
amplihack claude --auto --max-turns 10 -- -p "implement feature A" &
amplihack claude --auto --max-turns 10 -- -p "implement feature B" &
amplihack claude --auto --max-turns 10 -- -p "fix bug in module C" &

# Wait for all to complete
wait
```

Each session gets its own:
- Isolated worktree directory
- Separate git branch
- Independent .claude/ structure
- Private log directory

## Directory Structure

When automode runs with worktree isolation:

```
your-project/
├── .git/                           # Main repo
├── src/                            # Your working files (untouched)
├── .claude/                        # Your session config (untouched)
└── worktrees/                      # Automode worktrees
    ├── automode-task1-1234567890/  # First automode session
    │   ├── .git                    # Worktree git metadata
    │   ├── src/                    # Isolated copy
    │   └── .claude/                # Isolated automode logs
    ├── automode-task2-1234567891/  # Second automode session
    │   ├── .git
    │   ├── src/
    │   └── .claude/
    └── automode-task3-1234567892/  # Third automode session
        ├── .git
        ├── src/
        └── .claude/
```

## Worktree Lifecycle

### Creation

When automode starts with worktree mode:

1. Validates you're in a git repository
2. Extracts task hint from prompt (first 50 chars)
3. Sanitizes task hint for branch name (alphanumeric, dashes, underscores)
4. Creates worktree: `./worktrees/automode-{task}-{timestamp}`
5. Creates branch: `automode-{task}-{timestamp}`
6. Sets working directory to worktree path

### During Execution

Automode runs completely within the worktree:
- All file operations happen in worktree
- Logs saved in worktree's `.claude/runtime/logs/`
- Git operations (commits, pushes) use worktree branch
- PR creation uses worktree branch

### Cleanup

When automode completes (success or failure):

1. Stops UI thread if running
2. Exports session transcript
3. Removes worktree directory
4. Deletes worktree branch
5. Cleans up empty parent directories

Cleanup happens automatically even if:
- Automode encounters errors
- User interrupts with Ctrl+C
- Session times out

## Benefits

### Safety

- **No Data Loss**: Active session files never touched
- **No Conflicts**: Each session has isolated .claude/ directory
- **Rollback Easy**: Worktree cleanup leaves main branch untouched

### Parallel Execution

- **True Isolation**: Multiple sessions don't interfere
- **Resource Efficient**: Worktrees share git objects
- **Clean Logs**: Each session has separate log directory

### Development Workflow

- **No Interruption**: Continue working while automode runs
- **Easy Review**: Each automode creates PR from its branch
- **Simple Cleanup**: Worktrees auto-deleted after completion

## Advanced Usage

### Manual Worktree Management

If automatic cleanup fails, you can manually manage worktrees:

```bash
# List all worktrees
git worktree list

# Remove specific worktree
git worktree remove ./worktrees/automode-task-1234567890

# Prune stale worktrees
git worktree prune

# Delete associated branch
git branch -D automode-task-1234567890
```

### Cleanup Old Worktrees

Automode can clean up old worktrees (older than 24 hours):

```python
from amplihack.launcher.worktree_manager import WorktreeManager

manager = WorktreeManager(".")
cleaned = manager.cleanup_old_worktrees(max_age_hours=24)
print(f"Cleaned {cleaned} old worktrees")
```

### Custom Worktree Prefix

For testing or specialized use:

```python
from amplihack.launcher.worktree_manager import WorktreeManager

manager = WorktreeManager(".", prefix="experiment")
worktree_path, branch = manager.create_worktree("test-feature")
# Creates: ./worktrees/experiment-test-feature-{timestamp}
```

## Troubleshooting

### Worktree Creation Fails

**Error**: "Failed to create worktree: Not in a git repository"

**Solution**: Ensure you're in a git repository:
```bash
git status  # Should show git status, not error
```

**Error**: "Failed to create worktree: Directory not empty"

**Solution**: Remove stale worktree directory:
```bash
rm -rf ./worktrees/automode-*
git worktree prune
```

### Worktree Cleanup Fails

**Error**: "Failed to remove worktree: uncommitted changes"

**Solution**: Force cleanup:
```bash
git worktree remove --force ./worktrees/automode-task-1234567890
```

### Worktree Remains After Session

**Cause**: Cleanup may fail if process is forcefully killed

**Solution**: Manually remove:
```bash
# List worktrees
git worktree list

# Remove specific worktree
git worktree remove ./worktrees/automode-task-1234567890

# Delete branch
git branch -D automode-task-1234567890
```

### Multiple Worktrees Fill Disk

**Cause**: Old worktrees not cleaned up

**Solution**: Clean worktrees older than 24 hours:
```bash
# Manual cleanup
find ./worktrees -name "automode-*" -mtime +1 -exec git worktree remove {} \;

# Or let Python script handle it
python -c "
from amplihack.launcher.worktree_manager import WorktreeManager
WorktreeManager('.').cleanup_old_worktrees(max_age_hours=24)
"
```

## Comparison with Other Strategies

### Strategy 1: Manual Worktrees

**Manual**:
```bash
# User must manually create worktree
git worktree add ./worktrees/my-task -b my-task
cd ./worktrees/my-task
amplihack claude --auto --no-worktree -- -p "task"
cd ../..
git worktree remove ./worktrees/my-task
```

**Automatic (Strategy 2)**:
```bash
# Worktree created and cleaned up automatically
amplihack claude --auto -- -p "task"
```

### Strategy 3: Different Directory

**Different Dir**:
```bash
# User must clone repo separately
git clone <repo> ~/automode-workspace
cd ~/automode-workspace
amplihack claude --auto --no-worktree -- -p "task"
```

**Automatic (Strategy 2)**:
```bash
# Works in current directory, creates isolated worktree
amplihack claude --auto -- -p "task"
```

## Best Practices

1. **Let Automode Handle Worktrees**: Use default behavior, don't disable with --no-worktree
2. **Trust Automatic Cleanup**: Worktrees are cleaned up automatically
3. **Monitor Disk Space**: Check `./worktrees/` occasionally for stale worktrees
4. **Review PRs Individually**: Each automode creates separate PR for easy review
5. **Use Descriptive Prompts**: First 50 chars become branch name hint

## FAQ

**Q: Do worktrees increase disk usage?**
A: Minimally. Worktrees share git objects, only duplicating working files.

**Q: Can I inspect worktree while automode runs?**
A: Yes! Worktrees are normal directories. Use `cd ./worktrees/automode-*/` to inspect.

**Q: What happens to worktree if automode crashes?**
A: Cleanup runs in `finally` block, so worktree is removed even on crash.

**Q: Can I disable worktrees permanently?**
A: Not recommended, but you can use `--no-worktree` flag each time.

**Q: Do worktrees work with Docker mode?**
A: Yes, worktrees are created before Docker launch.

**Q: How do I find automode logs?**
A: In worktree: `./worktrees/automode-*/. claude/runtime/logs/auto_*`
   After cleanup: Logs are lost (by design, PRs contain all work)

## Implementation Details

For developers interested in the implementation:

- **Module**: `src/amplihack/launcher/worktree_manager.py`
- **Integration**: `src/amplihack/launcher/auto_mode.py` (run() method)
- **CLI**: `src/amplihack/cli.py` (--use-worktree / --no-worktree flags)
- **Tests**: `tests/unit/test_worktree_manager.py`

## Related Documentation

- [Automode Safety Guide](AUTOMODE_SAFETY.md) - General safety patterns
- [Issue #1090](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1090) - Original issue
- [Git Worktrees Documentation](https://git-scm.com/docs/git-worktree) - Official git docs

---

**Remember**: Automatic worktree isolation is **Strategy 2** of the automode safety improvements. It provides the best balance of safety, convenience, and parallel execution capability.
