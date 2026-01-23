# Automode Safety Guide

**CRITICAL:** Automode works in the current directory and can conflict with active sessions.

## ⚠️ The Problem

When you launch `amplihack claude --auto` from within an active Claude Code session:

- Automode tries to stage files in the same `~/.amplihack/.claude/` directory
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

## Future Improvements

See issue #1090 for planned improvements:

- Add safety warnings to /amplihack:auto command
- Pre-flight validation (uncommitted changes warning)
- --working-dir flag for explicit directory control
- Automatic worktree creation option

## Related

- Issue #1090: Automode safety improvements
- PR #1083: Had to reconstruct lost changes
- `~/.amplihack/.claude/commands/amplihack/auto.md`: Automode documentation

---

**Remember:** Automode is powerful but needs isolation. Always commit first or use worktrees!
