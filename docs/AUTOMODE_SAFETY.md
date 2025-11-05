# Automode Safety Guide

**CRITICAL:** Automode works in the current directory and can conflict with active sessions.

## ⚠️ The Problem

When you launch `amplihack claude --auto` from within an active Claude Code session:
- Automode tries to stage files in the same `.claude/` directory
- Conflicts with existing structure
- Can overwrite uncommitted changes
- Results in: `OSError: Directory not empty`
- **RISK: Data loss**

## ✅ Safe Usage Patterns

### Option 1: Use Git Worktrees (RECOMMENDED)

**For parallel automode sessions:**
```bash
# Commit current work first
git add -A && git commit -m "checkpoint: before automode"

# Create worktrees for each automode task
git worktree add ./worktrees/automode-task1 -b automode-task1
git worktree add ./worktrees/automode-task2 -b automode-task2

# Launch from worktrees
cd ./worktrees/automode-task1
amplihack claude --auto --max-turns 10 -- -p "task 1 description"

cd ../automode-task2
amplihack claude --auto --max-turns 10 -- -p "task 2 description"
```

**Benefits:**
- Complete isolation
- No file conflicts
- Each session gets clean environment
- Can run truly in parallel

### Option 2: Commit First

**For single automode session:**
```bash
# Save your current work
git add -A && git commit -m "WIP: before automode"

# Launch automode
amplihack claude --auto --max-turns 10 -- -p "task description"

# If automode causes issues, rollback
git reset HEAD~1
```

**Benefits:**
- Simple approach
- Protects uncommitted work
- Easy recovery

### Option 3: Separate Clone

**For experimental automode:**
```bash
# One-time setup
git clone <repo-url> ~/automode-workspace
cd ~/automode-workspace

# Always launch from there
amplihack claude --auto --max-turns 10 -- -p "task"
```

**Benefits:**
- Zero risk to development environment
- Safe for experimentation

## ❌ What NOT To Do

**DON'T: Launch from active session with uncommitted work**
```bash
# In active Claude Code session with changes
amplihack claude --auto ... # ⚠️ DANGEROUS!
```
**Result:** Lost changes, conflicts, crashes

**DON'T: Launch multiple automode in same directory**
```bash
amplihack claude --auto ... &
amplihack claude --auto ... & # ⚠️ CONFLICT!
```
**Result:** File staging conflicts, crashes

## 🛡️ Pre-Flight Checklist

Before launching automode from current directory:

- [ ] All important changes are committed
- [ ] OR using a git worktree
- [ ] OR in a separate clone
- [ ] Understand automode will modify .claude/ directory
- [ ] Have recovery plan if things go wrong

## 🔧 Recovery If Things Go Wrong

**If automode crashes and you lost changes:**
```bash
# Check git reflog
git reflog

# Check for stashes
git stash list

# Check conversation transcript for reconstruction
ls ~/.claude/projects/*/
# Find recent .jsonl file, review for lost code
```

**If automode created conflicts:**
```bash
# Restore to last good state
git reset --hard HEAD

# Or restore specific files
git restore .claude/tools/amplihack/hooks/stop.py
```

## 📝 Recommended Workflow

**Spawning Multiple Automode Sessions:**
```bash
# 1. Commit current state
git add -A && git commit -m "checkpoint: reflection improvements"

# 2. Create worktrees
for i in {1..5}; do
  git worktree add ./worktrees/automode-$i -b automode-improvement-$i
done

# 3. Launch in background from each worktree
(cd ./worktrees/automode-1 && amplihack claude --auto --max-turns 10 -- -p "task 1") &
(cd ./worktrees/automode-2 && amplihack claude --auto --max-turns 10 -- -p "task 2") &
(cd ./worktrees/automode-3 && amplihack claude --auto --max-turns 10 -- -p "task 3") &
(cd ./worktrees/automode-4 && amplihack claude --auto --max-turns 10 -- -p "task 4") &
(cd ./worktrees/automode-5 && amplihack claude --auto --max-turns 10 -- -p "task 5") &

# 4. Monitor progress
wait

# 5. Review PRs from each worktree
# 6. Cleanup worktrees when done
git worktree remove ./worktrees/automode-{1..5}
```

## Automatic Safety Validation (NEW - Strategy 3)

**As of PR #XXXX (Issue #1090), automode now includes automatic git state validation:**

### Pre-Flight Checks

Before automode starts, it automatically validates:

1. **Uncommitted Changes Check**: Detects uncommitted, staged, or untracked files
2. **Active Session Detection**: Identifies existing Claude Code sessions

If validation fails, automode **will not start** and displays:
- Clear error message showing what's blocking execution
- List of affected files (first 10, with count if more)
- Specific suggestions to resolve the issue
- Override option for advanced users

### Example Error Message

```
PRE-FLIGHT VALIDATION FAILED
================================================================================

UNCOMMITTED CHANGES DETECTED
  Directory: /Users/you/project
  Risk: Automode operations may conflict with or overwrite uncommitted work
  Uncommitted files:
    Staged (2):
      M src/module.py
      M tests/test_module.py
    Modified (1):
      M README.md
    Untracked (3):
      ? new_feature.py
      ? draft.md
      ? .env.local

  Recommendation: Commit or stash changes first
    git add -A && git commit -m 'WIP: before automode'
    # or
    git stash

================================================================================
SAFETY OVERRIDE
================================================================================
If you understand the risks and want to proceed anyway:
  amplihack claude --auto --force -- -p 'your task'
================================================================================
```

### Override for Advanced Users

If you need to bypass validation (use with caution):

```bash
amplihack claude --auto --force -- -p "your task"
```

**Warning:** Using `--force` disables all safety checks. Only use if you:
- Understand the risks of data loss
- Have backed up your work
- Know what you're doing

## Automatic Worktree Isolation (Strategy 2) ✅

**NOW IMPLEMENTED**: Automode automatically uses git worktrees for complete isolation!

### How It Works

Automode now creates worktrees by default:

```bash
# Automatic worktree isolation (default behavior)
amplihack claude --auto --max-turns 10 -- -p "implement feature"

# Creates worktree: ./worktrees/automode-implement-feature-{timestamp}
# Runs in complete isolation
# Cleans up automatically when done
```

### Benefits

- **Zero Manual Setup**: Worktrees created and cleaned up automatically
- **Complete Isolation**: No conflicts with active session
- **Parallel Safe**: Run multiple automode sessions simultaneously
- **Data Protection**: Active directory never touched

### Disable If Needed

To run without worktree isolation (not recommended):

```bash
amplihack claude --auto --no-worktree -- -p "task"
```

**See [Automode Worktree Guide](AUTOMODE_WORKTREE_GUIDE.md) for complete documentation.**

## Future Improvements

Additional improvements planned (see issue #1090):
- ✅ **DONE**: Pre-flight validation (uncommitted changes warning) - Strategy 3
- ✅ **DONE**: Automatic worktree creation - Strategy 2
- Strategy 1 under evaluation in parallel PR
- Compare all 3 strategies for best approach

## Related
- Issue #1090: Automode safety improvements (3 parallel strategies)
- PR #XXXX: Strategy 3 - Git State Guard (this implementation)
- PR #1083: Had to reconstruct lost changes
- `.claude/commands/amplihack/auto.md`: Automode documentation

---

**Remember:** Automode now protects you automatically, but you can still use worktrees for complete isolation!
