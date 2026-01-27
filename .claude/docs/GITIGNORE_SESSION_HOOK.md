# GitIgnore Session Start Hook

**Status**: Production (Automatic)
**Performance Target**: < 500ms (no hard timeout)
**Reliability**: Fail-safe (never breaks session start)
**Implementation**: Python-based, subprocess for Git detection

## Overview

The gitignore session start hook automatically ensures that amplihack runtime and log directories are properly excluded from Git tracking. It runs silently at the start of every Claude Code session in Git repositories.

**Implementation Details**:

- Written in Python
- Uses `subprocess` to invoke `git rev-parse --is-inside-work-tree` for Git detection
- Exact equality matching after normalizing trailing slashes (no wildcards)
- Exceptions are silently caught (fail-safe design)

## What It Does

When you start a Claude Code session in a Git repository, the hook:

1. **Detects Git Repository**: Runs `git rev-parse --is-inside-work-tree` via subprocess to check if inside a Git repository
2. **Locates .gitignore**: Finds the root .gitignore file (or creates one if missing)
3. **Validates Patterns**: Uses exact equality matching after normalizing trailing slashes to check if patterns `.claude/logs/` and `.claude/runtime/` exist
4. **Updates .gitignore**: Adds missing patterns if needed
5. **Notifies User**: Shows a brief message if changes were made

**Pattern Matching**: The hook uses exact equality matching after normalizing trailing slashes - it compares normalized patterns (without trailing slashes) for equality. No wildcards or regex support.

### Protected Directories

The hook ensures these directories are always in .gitignore:

```
.claude/logs/
.claude/runtime/
```

These directories contain:

- Session logs (conversation history, debug info)
- Runtime state (cache files, temporary data)
- Agent outputs (analysis results, generated files)

**Why these must be ignored**: Runtime and log files are local, ephemeral, and can contain sensitive information. They should never be committed to version control.

## What Users See

### Scenario 1: Patterns Already Present

**You see**: Nothing! The hook runs silently and completes in < 100ms.

```
$ claude-code
# Session starts normally, no output from hook
```

### Scenario 2: Patterns Missing

**You see**: A brief notification that .gitignore was updated.

**Before** (.gitignore contents):

```
node_modules/
*.pyc
__pycache__/
```

**After** (.gitignore contents):

```
node_modules/
*.pyc
__pycache__/
.claude/logs/
.claude/runtime/
```

**Terminal output**:

```
$ claude-code

[Amplihack] Updated .gitignore to exclude runtime directories
  Added patterns:
    - .claude/logs/
    - .claude/runtime/

  Action required: Commit the updated .gitignore file
  $ git add .gitignore
  $ git commit -m "chore: Add amplihack runtime directories to .gitignore"

# Session continues normally
```

### Scenario 3: Not a Git Repository

**You see**: Nothing! The hook detects non-Git directories and exits immediately.

```
$ cd ~/non-git-project
$ claude-code
# Session starts normally, hook skips silently
```

## User Actions Required

### After First Installation

When you first install amplihack in a Git repository:

1. **Review the changes**: Check what was added to .gitignore

   ```bash
   git diff .gitignore
   ```

2. **Commit the changes**: Add the updated .gitignore to your repository

   ```bash
   git add .gitignore
   git commit -m "chore: Add amplihack runtime directories to .gitignore"
   ```

3. **Continue working**: That's it! The hook won't bother you again unless patterns are removed.

### Ongoing Usage

**No action required!** The hook maintains .gitignore automatically.

**Exception**: If you intentionally remove the patterns from .gitignore, the hook will add them back and notify you. This is by design to prevent accidental commits of runtime data.

## Troubleshooting

### "Permission denied" when updating .gitignore

**Symptom**: Hook reports it cannot write to .gitignore

**Cause**: .gitignore file has restrictive permissions or is owned by another user

**Solution**:

```bash
# Check file permissions
ls -la .gitignore

# Fix permissions (if you own the file)
chmod u+w .gitignore

# If file is owned by another user, contact your team lead
```

### .gitignore keeps getting modified

**Symptom**: Every session shows the "updated .gitignore" message

**Cause**: Another tool or process is removing the patterns

**Solution**:

```bash
# Check if patterns are actually in .gitignore
grep ".claude/logs/" .gitignore
grep ".claude/runtime/" .gitignore

# If missing, check for conflicting automation
git log --oneline -n 20 -- .gitignore

# If another tool is removing them, configure that tool or file an issue
```

### Hook seems slow (> 500ms)

**Symptom**: Noticeable delay at session start

**Cause**: Large .gitignore file or slow disk I/O

**Note**: The 500ms is a **performance target**, not a hard timeout. The hook will complete its work even if it takes longer.

**Solution**:

```bash
# Check .gitignore size
ls -lh .gitignore

# If > 100KB, consider splitting into multiple files
# (Git supports .gitignore in subdirectories)

# Check disk performance
time ls -la .gitignore

# If disk is slow, this is a system issue, not the hook
```

### Hook didn't run / Patterns not added

**Symptom**: Runtime files are being tracked by Git

**Cause**: Hook failed silently (fail-safe behavior)

**Solution**:

```bash
# Check if you're in a Git repository
git status

# Manually add patterns to .gitignore
echo ".claude/logs/" >> .gitignore
echo ".claude/runtime/" >> .gitignore

# Untrack files that shouldn't be tracked
git rm --cached -r .claude/logs/ 2>/dev/null
git rm --cached -r .claude/runtime/ 2>/dev/null

# Commit the changes
git add .gitignore
git commit -m "chore: Add amplihack runtime directories to .gitignore"
```

## Technical Details

### Performance Characteristics

- **Typical runtime**: 50-150ms
- **Performance target**: < 500ms (not a hard timeout - hook completes work even if longer)
- **Memory usage**: < 5MB
- **Disk I/O**: 1-2 reads, 0-1 write (only if update needed)

### Implementation Details

- **Language**: Python
- **Git Detection**: Uses `subprocess.run()` to execute `git rev-parse --is-inside-work-tree`
- **Pattern Matching**: Exact equality after normalizing trailing slashes - no wildcards or regex
- **Error Handling**: Exceptions are silently caught (fail-safe design)

### Fail-Safe Design

The hook is designed to **never break your session**:

- **Exception handling**: Wrapped in try/catch - exceptions are silently caught and don't propagate
- **Performance target**: Aims for < 500ms (not a hard timeout - completes work even if longer)
- **Read-only fallback**: If .gitignore is unwritable, session continues anyway
- **Non-Git detection**: Uses `git rev-parse --is-inside-work-tree` to immediately exit in non-Git directories

**Philosophy**: It's better to skip .gitignore updates than to delay or break the user's session start.

**Design Decision**: No logging is implemented to avoid circular dependencies with the logging infrastructure. Exceptions are silently caught to maintain fail-safe operation.

### Hook Execution Order

The gitignore hook runs during the SessionStartHooks phase:

1. **PreSessionStart** (before amplihack loads)
2. **SessionStartHooks** ← GitIgnore hook runs here
3. **PostSessionStart** (after amplihack is ready)

This ensures .gitignore is updated before any runtime files are created.

### Implementation Flow

```python
# Pseudocode for hook execution
def gitignore_hook():
    try:
        # Step 1: Git detection
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return  # Not a Git repo, exit silently

        # Step 2: Find .gitignore
        gitignore_path = Path(".gitignore")
        if not gitignore_path.exists():
            gitignore_content = ""
        else:
            gitignore_content = gitignore_path.read_text()

        # Step 3: Check patterns (exact equality after normalization)
        required_patterns = [".claude/logs/", ".claude/runtime/"]
        missing_patterns = [
            p for p in required_patterns
            if not is_directory_ignored(p, parse_patterns(gitignore_content))
        ]

        # Step 4: Update if needed
        if missing_patterns:
            updated_content = gitignore_content
            for pattern in missing_patterns:
                updated_content += f"\n{pattern}"

            gitignore_path.write_text(updated_content)
            notify_user(missing_patterns)

    except Exception as e:
        # Silently catch exception, never break session (fail-safe design)
        pass
```

## Configuration

### Disabling the Hook

The hook cannot be disabled (by design). Runtime directories should always be excluded from Git.

**Rationale**: Committing runtime files causes:

- Repository bloat (logs can be > 100MB)
- Merge conflicts (everyone's logs are different)
- Security risks (logs may contain API keys, secrets)
- CI/CD failures (unexpected files in repository)

If you genuinely need to commit runtime files for debugging:

```bash
# Temporarily force-add specific files (not recommended)
git add -f .claude/runtime/specific-file.json
git commit -m "debug: Add runtime file for investigation"

# Remove after debugging is complete
git rm --cached .claude/runtime/specific-file.json
```

### Customizing Patterns

The hook always enforces these patterns:

- `.claude/logs/`
- `.claude/runtime/`

**Cannot be customized** - these are fundamental to amplihack's operation.

**Additional patterns**: If you need to ignore other amplihack directories, add them manually to .gitignore. The hook will preserve them.

## Integration with Other Tools

### Pre-commit Hooks

The gitignore session hook runs **before** pre-commit hooks (it runs at session start, not at commit time).

**No conflicts** - the hook updates .gitignore, pre-commit hooks validate it.

### Git Worktrees

**Fully supported** - Git worktrees share the same .gitignore file with the main repository (not separate files).

**How it works**:

- Worktrees share the repository's .git directory structure
- The .gitignore file at the repository root applies to all worktrees
- Hook detects Git repository using `git rev-parse --is-inside-work-tree`
- Updates the shared .gitignore file once (applies to all worktrees)

```bash
# Create worktree
git worktree add ../feat/my-feature

# Start session in worktree
cd ../feat/my-feature
claude-code

# Hook updates the shared .gitignore in the main repository
# (Not a separate .gitignore for the worktree)
```

### Submodules

**Fully supported** - when run inside a submodule, the hook updates the submodule's own .gitignore file.

**How it works**:

- `git rev-parse --is-inside-work-tree` returns true when inside a submodule
- Hook treats the submodule as an independent Git repository
- Updates the submodule's .gitignore (not the parent repository's)

**Best practice**: Run Claude Code sessions in each submodule to ensure its .gitignore has amplihack patterns.

```bash
# Work in submodule
cd path/to/submodule
claude-code

# Hook updates path/to/submodule/.gitignore
# (Parent repository's .gitignore is unchanged)
```

## FAQ

### Why not use .git/info/exclude instead?

`.git/info/exclude` is local and not shared with the team. Using `.gitignore` ensures everyone on the team automatically excludes runtime directories.

### What if I want to commit runtime files for debugging?

Use `git add -f <file>` to force-add specific files. The hook won't remove them from Git's index.

**Warning**: Be careful not to commit secrets or sensitive information.

### Does this work with monorepos?

**Yes** - the hook respects Git repository boundaries and updates the appropriate .gitignore for each repository.

In a monorepo with multiple .gitignore files:

- Hook updates the root .gitignore if it exists
- Falls back to creating .gitignore if missing
- Respects subdirectory .gitignore files

### What if I'm using a different ignore file name?

The hook only works with `.gitignore`. If you're using custom ignore files (rare), you'll need to manually maintain amplihack patterns.

### Does this hook run in CI/CD?

**No** - CI/CD environments typically:

1. Don't run Claude Code (no session start)
2. Use clean checkouts (runtime dirs don't exist)
3. Don't commit changes (read-only)

The hook is designed for local development only.

## Related Documentation

- **Session Hooks Architecture**: See `.claude/docs/SESSION_HOOKS.md` (planned)
- **Runtime Directory Structure**: See `docs/runtime/DIRECTORY_STRUCTURE.md` (planned)
- **Git Integration Guide**: See `docs/git/INTEGRATION.md` (planned)

## Changelog

### v1.0.0 (2025-01-23)

- Initial implementation
- Automatic .gitignore pattern enforcement
- Fail-safe design with < 500ms guarantee
- Support for Git worktrees and monorepos

---

**Remember**: This hook is designed to be invisible and automatic. If you notice it running, something unexpected happened - check the troubleshooting section above.
