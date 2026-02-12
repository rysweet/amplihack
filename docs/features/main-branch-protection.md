# Main Branch Commit Protection

**Documentation for pre_tool_use Hook Enhancement**

---

## Overview

The `pre_tool_use` hook now includes **automatic main branch protection** that prevents accidental direct commits to `main` or `master` branches when using Claude Code's bash tool. This protection enforces a feature branch workflow and cannot be bypassed.

### What This Does

- ✅ **Blocks** all `git commit` commands (including variants) when on `main` or `master` branch
- ✅ **Provides** clear, actionable error messages with workflow guidance
- ✅ **Preserves** existing `--no-verify` bypass protection
- ✅ **Fails gracefully** if git commands error (won't block legitimate work)
- ✅ **Allows** all other git operations (push, status, pull, etc.) on protected branches

### Why This Matters

Direct commits to main/master branches bypass code review and can break production. This protection guides developers toward the feature branch workflow automatically, preventing mistakes before they happen.

---

## How It Works

When you run any bash command through Claude Code, the `pre_tool_use` hook:

1. **Detects git commit commands** - Checks if the command contains `git commit`
2. **Determines current branch** - Runs `git branch --show-current`
3. **Enforces protection** - Blocks operation if on `main` or `master`
4. **Provides guidance** - Shows clear error message with workflow steps

### Protected Branches

- `main` (most common default branch name)
- `master` (legacy default branch name)

### Protected Commands

All `git commit` variants are blocked on protected branches:

- `git commit -m "message"`
- `git commit --amend`
- `git commit --fixup`
- `git commit --no-edit`
- `git commit -a -m "message"`
- And any other commit variant

### Allowed Commands

These operations are **NOT** blocked, even on `main` or `master`:

- `git push` - Pushing already-committed changes
- `git pull` - Pulling updates from remote
- `git status` - Checking repository status
- `git branch` - Managing branches
- `git checkout` - Switching branches
- `git merge` - Merging (typically done via PR)
- `git rebase` - Rebasing operations
- Any non-commit git operation

---

## Usage Examples

### ❌ Blocked: Direct Commit to Main

**Scenario:** You're on `main` branch and try to commit:

```bash
git commit -m "fix: update authentication logic"
```

**Result:** ❌ **BLOCKED**

```
⛔ Direct commits to 'main' branch are not allowed.

Please use the feature branch workflow:
  1. Create a feature branch: git checkout -b feature/your-feature-name
  2. Make your commits on the feature branch
  3. Create a Pull Request to merge into main

This protection cannot be bypassed with --no-verify.
```

---

### ❌ Blocked: Amend Commit on Master

**Scenario:** You're on `master` branch and try to amend:

```bash
git commit --amend --no-edit
```

**Result:** ❌ **BLOCKED**

```
⛔ Direct commits to 'master' branch are not allowed.

Please use the feature branch workflow:
  1. Create a feature branch: git checkout -b feature/your-feature-name
  2. Make your commits on the feature branch
  3. Create a Pull Request to merge into master

This protection cannot be bypassed with --no-verify.
```

---

### ✅ Allowed: Commit on Feature Branch

**Scenario:** You're on `feature/auth-improvements` branch:

```bash
git commit -m "feat: add OAuth2 support"
```

**Result:** ✅ **ALLOWED** - Commit proceeds normally

---

### ❌ Blocked: Bypass Attempt with --no-verify

**Scenario:** You try to bypass protection on `main`:

```bash
git commit --no-verify -m "quick fix"
```

**Result:** ❌ **BLOCKED** (main branch check fires first)

```
⛔ Direct commits to 'main' branch are not allowed.

Please use the feature branch workflow:
  1. Create a feature branch: git checkout -b feature/your-feature-name
  2. Make your commits on the feature branch
  3. Create a Pull Request to merge into main

This protection cannot be bypassed with --no-verify.
```

**Note:** If you were on a feature branch, you'd see the existing `--no-verify` protection message instead.

---

### ✅ Allowed: Push to Main

**Scenario:** You want to push commits (made via PR merge) to `main`:

```bash
git push origin main
```

**Result:** ✅ **ALLOWED** - Only commits are blocked, not pushes

---

## Recommended Workflow

When you need to make changes:

### Step 1: Create Feature Branch

```bash
git checkout -b feature/descriptive-name
```

**Branch naming conventions:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/updates

### Step 2: Make Your Commits

```bash
git commit -m "feat: add new functionality"
git commit -m "test: add test coverage"
git commit -m "docs: update README"
```

### Step 3: Push Your Branch

```bash
git push origin feature/descriptive-name
```

### Step 4: Create Pull Request

Use GitHub UI or CLI:

```bash
gh pr create --title "Add new functionality" --body "Description of changes"
```

### Step 5: Merge via Pull Request

After code review and CI passes, merge through GitHub's UI or:

```bash
gh pr merge --squash
```

---

## Configuration

### No Configuration Required

This protection is **always enabled** for the `pre_tool_use` hook. There are no configuration options or settings to change.

### Protected Branches

The list of protected branches is hardcoded:
- `main`
- `master`

**Note:** If your repository uses a different default branch name (e.g., `develop`, `trunk`), those branches are NOT automatically protected. This is intentional - the protection focuses on the most common default branch names.

---

## Error Handling & Graceful Degradation

The hook is designed to **fail-open** - if any error occurs during branch detection, the operation is **allowed** to prevent blocking legitimate work.

### When Protection Fails Open

1. **Not in a git repository**
   - Log: `WARNING: Failed to check git branch (not in repo?)`
   - Result: Operation allowed

2. **Git command not found**
   - Log: `WARNING: Git command not found - allowing operation`
   - Result: Operation allowed

3. **Git command timeout** (>5 seconds)
   - Log: `WARNING: Git branch check timed out - allowing operation`
   - Result: Operation allowed

4. **Detached HEAD state**
   - Branch name is empty (not `main` or `master`)
   - Result: Operation allowed
   - **Why intentional:** Detached HEAD supports important workflows like cherry-picking commits, bisecting for bug hunting, and reviewing historical commits

5. **Any unexpected error**
   - Log: `WARNING: Unexpected error checking git branch`
   - Result: Operation allowed

### Checking Logs

If protection seems to not be working, check the hook logs:

```bash
# View recent log entries
tail -f .claude/runtime/logs/pre_tool_use.log

# Search for warnings
grep WARNING .claude/runtime/logs/pre_tool_use.log

# View all log entries
cat .claude/runtime/logs/pre_tool_use.log
```

**Log Location:** `.claude/runtime/logs/pre_tool_use.log` (relative to project root)

---

## Troubleshooting

### "I need to make an urgent hotfix to main!"

**Don't bypass the protection** - it exists for good reason. Instead:

1. Create a hotfix branch: `git checkout -b hotfix/critical-issue`
2. Make your fix and commit
3. Create a PR and get fast-tracked review
4. Merge via PR (or use emergency merge if your team has that process)

**Why?** Even urgent fixes benefit from:
- Code review (catch mistakes in urgent changes)
- CI validation (prevent broken production deployments)
- Audit trail (know who changed what and why)

### "The protection isn't triggering on my custom default branch"

This is expected. The protection only covers:
- `main`
- `master`

If your repository uses `develop`, `trunk`, or another name, you'll need to either:
1. Rename your default branch to `main` (recommended)
2. Request a feature enhancement to make protected branches configurable

### "I'm not in a git repo, why is my bash command blocked?"

The protection only blocks `git commit` commands. If you're seeing blocks for other commands, that's a different hook feature. Check:
- Existing `--no-verify` protection (blocks the flag on any git command)
- Other hook rules

### "Can I disable this protection?"

No. The protection is intentionally not configurable. If you have a legitimate use case for direct commits to main, please:
1. Use the feature branch workflow (it's there for a reason)
2. File an issue explaining your use case if you believe the protection is incorrect

---

## Technical Details

### Implementation

**Files Modified:**
- `.claude/tools/amplihack/hooks/pre_tool_use.py` (workspace copy)
- `amplifier-bundle/tools/amplihack/hooks/pre_tool_use.py` (bundle copy)

**Dependencies:**
- Python `subprocess` module (stdlib)
- Git binary in PATH

**Performance:**
- Target: <30ms overhead per commit check
- Typical: 10-20ms in normal operation
- Maximum: 50ms in worst-case scenarios (slow git response)
- Timeout: 5 seconds maximum

### File Architecture

This feature is implemented in **TWO identical files**:

- **Workspace copy**: `.claude/tools/amplihack/hooks/pre_tool_use.py`
  - Active in your local Claude Code workspace
  - Used when Claude Code runs in this project
  
- **Bundle copy**: `amplifier-bundle/tools/amplihack/hooks/pre_tool_use.py`
  - Distributed with the amplihack bundle for other users
  - Ensures all amplihack installations have this protection

**Critical:** Both files must remain byte-identical to ensure consistent behavior across environments. When updating this feature, modify both files identically.

### Security Considerations

**Safe Subprocess Execution:**
- Uses hardcoded argument lists (never `shell=True`)
- 5-second timeout prevents hangs
- No user input passed to subprocess
- Sanitizes git output with `.strip()`

**Defense in Depth:**
- Client-side protection (this hook)
- Server-side protection (GitHub branch protection rules - recommended)
- Code review process
- CI validation

### Integration with Existing Features

**Preserves --no-verify Protection:**
The main branch check happens **before** the existing `--no-verify` protection check. Both protections work independently:

| Command | Branch | Main Check | --no-verify Check | Result |
|---------|--------|------------|-------------------|--------|
| `git commit -m "msg"` | `main` | ❌ BLOCKED | - | Main branch error |
| `git commit -m "msg"` | `feature/x` | ✅ PASS | ✅ PASS | Allowed |
| `git commit --no-verify` | `main` | ❌ BLOCKED | - | Main branch error |
| `git commit --no-verify` | `feature/x` | ✅ PASS | ❌ BLOCKED | --no-verify error |

### Special Cases

**Detached HEAD State:** When in detached HEAD state, `git branch --show-current` returns an empty string. Since empty string ≠ "main" or "master", commits are **intentionally allowed** in detached HEAD state. This supports workflows like:
- Cherry-picking commits
- Bisecting for bug hunting
- Reviewing historical commits
- Creating commits before deciding on branch name

---

## Developer Reference

### Hook Execution Flow

```
Bash Tool Invoked
    ↓
PreToolUseHook.process()
    ↓
Extract command from params
    ↓
Is "git commit" in command? → No → Allow ✅
    ↓ Yes
Run: git branch --show-current (5s timeout)
    ↓
Error/Timeout? → Yes → Allow ✅ (fail-open)
    ↓ No
Current branch in ['main', 'master']? → Yes → Block ❌ (return error message)
    ↓ No
Check for --no-verify flag → Found → Block ❌ (existing protection)
    ↓ Not Found
Allow ✅
```

### Error Message Template

```python
MAIN_BRANCH_ERROR_MESSAGE = """⛔ Direct commits to '{branch}' branch are not allowed.

Please use the feature branch workflow:
  1. Create a feature branch: git checkout -b feature/your-feature-name
  2. Make your commits on the feature branch
  3. Create a Pull Request to merge into {branch}

This protection cannot be bypassed with --no-verify."""
```

### Adding Custom Protected Branches

**Not currently supported.** To add support:

1. Modify the hardcoded list: `if current_branch in ['main', 'master']`
2. Update to: `if current_branch in ['main', 'master', 'develop']`
3. Update both file copies identically
4. Test with manual test plan (section 9 of architecture doc)

**Note:** Consider making this configurable via `.claude/config.yaml` in future enhancement.

---

## Testing

### Manual Test Plan

**Prerequisites:**
- Git repository with `main` or `master` branch
- Claude Code with updated hook files

**Test Cases:**

| ID | Action | Branch | Expected Result |
|----|--------|--------|-----------------|
| TC1 | `git commit -m "test"` | `main` | ❌ BLOCKED (main error) |
| TC2 | `git commit -m "test"` | `master` | ❌ BLOCKED (master error) |
| TC3 | `git commit -m "test"` | `feature/xyz` | ✅ ALLOWED |
| TC4 | `git commit --amend` | `main` | ❌ BLOCKED (main error) |
| TC5 | `git commit --no-verify` | `main` | ❌ BLOCKED (main error) |
| TC6 | `git commit --no-verify` | `feature/xyz` | ❌ BLOCKED (--no-verify error) |
| TC7 | `git push` | `main` | ✅ ALLOWED |
| TC8 | `git status` | `main` | ✅ ALLOWED |

### Error Handling Tests

| ID | Scenario | Expected Behavior |
|----|----------|-------------------|
| EC1 | Not in git repo | ✅ ALLOWED (fail-open + warning log) |
| EC2 | Git not in PATH | ✅ ALLOWED (fail-open + warning log) |
| EC3 | Detached HEAD | ✅ ALLOWED (empty branch ≠ main/master) |

---

## Changelog

### Version 1.0 (Initial Release)

**Added:**
- Main/master branch commit protection
- Graceful fail-open error handling
- Clear error messages with workflow guidance
- Integration with existing --no-verify protection

**Security:**
- Hardcoded subprocess arguments
- 5-second timeout on git commands
- Fail-open on all error conditions
- Input sanitization on git output

**Files Modified:**
- `.claude/tools/amplihack/hooks/pre_tool_use.py`
- `amplifier-bundle/tools/amplihack/hooks/pre_tool_use.py`

---

## Related Documentation

- **Hook System Overview**: [Hook README](../../.claude/tools/amplihack/hooks/README.md)
- **GitHub Branch Protection**: See your repository settings for server-side protection
- **Pre-commit Hooks**: `.pre-commit-config.yaml` (complementary protection)
- **Workflow Documentation**: See your team's feature branch workflow documentation

---

## Support & Feedback

**Questions?**
- Check troubleshooting section above
- Review hook logs at `.claude/runtime/logs/pre_tool_use.log`
- File an issue if you believe protection is incorrect

**Feature Requests:**
- Configurable protected branch list
- Per-repository protection settings
- Integration with other hooks

---

**Last Updated:** 2026-02-08  
**Hook Version:** 1.0  
**Minimum Requirements:** Python 3.7+, Git 2.0+
