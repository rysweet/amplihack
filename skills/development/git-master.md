# Git Master

Advanced Git workflows and techniques for effective version control.

## When to Use

- Managing complex branching strategies
- Working on multiple features simultaneously
- Investigating code history
- Resolving merge conflicts
- Cleaning up commit history

## Branching Strategies

### Trunk-Based Development

```
main (always deployable)
  │
  ├── feature/short-lived-1 (1-2 days max)
  │     └── merge → main
  │
  ├── feature/short-lived-2
  │     └── merge → main
  │
  └── releases created from main via tags
```

**Best for:**
- Small teams
- Continuous deployment
- High test coverage
- Feature flags available

**Commands:**
```bash
# Create short-lived feature branch
git checkout main
git pull origin main
git checkout -b feature/my-feature

# Keep updated with main
git fetch origin
git rebase origin/main

# Merge back (prefer squash for clean history)
git checkout main
git merge --squash feature/my-feature
git commit -m "Add my feature"
git push origin main
git branch -d feature/my-feature
```

### GitFlow

```
main (production)
  │
develop (integration)
  │
  ├── feature/feature-a ──→ develop
  ├── feature/feature-b ──→ develop
  │
  ├── release/1.0 ──→ main + develop (tag: v1.0)
  │
  └── hotfix/urgent ──→ main + develop
```

**Best for:**
- Scheduled releases
- Multiple versions in production
- Larger teams
- Long-lived features

**Commands:**
```bash
# Start feature
git checkout develop
git checkout -b feature/my-feature

# Finish feature
git checkout develop
git merge --no-ff feature/my-feature
git branch -d feature/my-feature

# Start release
git checkout develop
git checkout -b release/1.0

# Finish release
git checkout main
git merge --no-ff release/1.0
git tag -a v1.0 -m "Release 1.0"
git checkout develop
git merge --no-ff release/1.0
git branch -d release/1.0

# Hotfix
git checkout main
git checkout -b hotfix/urgent-fix
# ... fix ...
git checkout main
git merge --no-ff hotfix/urgent-fix
git tag -a v1.0.1 -m "Hotfix 1.0.1"
git checkout develop
git merge --no-ff hotfix/urgent-fix
```

### GitHub Flow

```
main (always deployable)
  │
  ├── feature-1 → PR → review → merge → deploy
  ├── feature-2 → PR → review → merge → deploy
  └── feature-3 → PR → review → merge → deploy
```

**Best for:**
- Web applications
- Continuous deployment
- GitHub/GitLab workflows

**Commands:**
```bash
# Create feature branch
git checkout main
git pull
git checkout -b my-feature

# Push and create PR
git push -u origin my-feature
gh pr create --fill

# After review, merge via GitHub UI or:
gh pr merge --squash
```

## Worktree Management

Work on multiple branches simultaneously without stashing or switching.

### Basic Worktree Usage

```bash
# List existing worktrees
git worktree list

# Add a worktree for a branch
git worktree add ../project-feature feature/my-feature

# Add worktree with new branch
git worktree add -b feature/new-feature ../project-new-feature main

# Work in the new directory
cd ../project-feature
# ... make changes, commit, push ...

# Remove worktree when done
cd ../project-main
git worktree remove ../project-feature
# Or force remove if changes exist
git worktree remove --force ../project-feature
```

### Worktree Workflow Example

```bash
# You're on main, working on feature, need hotfix
# Current structure:
# ~/project (main)

# Add worktree for hotfix
git worktree add ~/project-hotfix -b hotfix/urgent main

# Now you have:
# ~/project (main) - your main work
# ~/project-hotfix (hotfix/urgent) - hotfix work

# Work on hotfix
cd ~/project-hotfix
# ... fix, commit, push, merge ...

# Cleanup
cd ~/project
git worktree remove ~/project-hotfix

# Continue feature work without ever switching branches
```

### Worktree Tips

```bash
# Prune stale worktree references
git worktree prune

# Lock worktree (prevent pruning)
git worktree lock ../project-feature

# Unlock worktree
git worktree unlock ../project-feature

# Move worktree
git worktree move ../project-feature ../new-location
```

## Interactive Rebase

Rewrite history for cleaner commits.

### Common Operations

```bash
# Rebase last N commits
git rebase -i HEAD~5

# Rebase onto branch
git rebase -i main

# In editor, change commands:
# pick   - keep commit as-is
# reword - keep commit, edit message
# edit   - pause to amend commit
# squash - meld into previous commit (keep message)
# fixup  - meld into previous commit (discard message)
# drop   - remove commit
```

### Squash Workflow

```bash
# Before: many messy commits
git log --oneline
# a1b2c3 fix typo
# d4e5f6 oops forgot file
# g7h8i9 WIP
# j0k1l2 Add feature X

# Squash into one clean commit
git rebase -i HEAD~4

# In editor, change to:
# pick j0k1l2 Add feature X
# fixup g7h8i9 WIP
# fixup d4e5f6 oops forgot file
# fixup a1b2c3 fix typo

# Result: one commit "Add feature X"
```

### Split a Commit

```bash
git rebase -i HEAD~3
# Mark the commit to split as 'edit'

# When rebase pauses:
git reset HEAD^  # Undo commit, keep changes
git add file1.py
git commit -m "First part"
git add file2.py
git commit -m "Second part"
git rebase --continue
```

### Reorder Commits

```bash
git rebase -i HEAD~5

# In editor, just reorder the lines:
# pick c3 Third feature
# pick c1 First feature  
# pick c2 Second feature

# Commits will be reordered
```

## Conflict Resolution

### Understanding Conflict Markers

```python
<<<<<<< HEAD (current branch)
def calculate(x):
    return x * 2
=======
def calculate(x):
    return x * 3
>>>>>>> feature-branch (incoming change)
```

### Resolution Strategies

```bash
# Take current branch version
git checkout --ours path/to/file

# Take incoming branch version  
git checkout --theirs path/to/file

# Manual resolution
# Edit file, remove markers, keep what you want
git add path/to/file
git commit  # or git rebase --continue

# Abort if needed
git merge --abort
git rebase --abort
```

### Conflict Prevention

```bash
# Before merging, preview conflicts
git merge --no-commit --no-ff feature-branch
git diff --cached
git merge --abort  # if you want to back out

# Rebase frequently to minimize conflicts
git fetch origin
git rebase origin/main

# Use merge tools
git mergetool  # Opens configured merge tool
```

### Rerere (Reuse Recorded Resolution)

```bash
# Enable rerere
git config --global rerere.enabled true

# Git will remember conflict resolutions
# and apply them automatically next time

# See recorded resolutions
ls .git/rr-cache/

# Forget a resolution
git rerere forget path/to/file
```

## History Archaeology

### Git Log Mastery

```bash
# Pretty log format
git log --oneline --graph --all

# Search commit messages
git log --grep="fix bug"

# Search code changes
git log -S "function_name"  # Pickaxe: when added/removed
git log -G "regex_pattern"  # When pattern changed

# Filter by author
git log --author="alice"

# Filter by date
git log --since="2024-01-01" --until="2024-02-01"

# Filter by path
git log -- path/to/file

# Show stat of changes
git log --stat

# Show full diff
git log -p

# Custom format
git log --format="%h %an %s" --since="1 week ago"
```

### Git Blame

```bash
# Who changed each line
git blame path/to/file

# Ignore whitespace changes
git blame -w path/to/file

# Show specific lines
git blame -L 10,20 path/to/file

# Show original author (ignore move/copy)
git blame -M path/to/file   # Detect moves within file
git blame -C path/to/file   # Detect moves from other files
git blame -CCC path/to/file # Detect at creation time too

# Ignore specific commits (e.g., formatting changes)
git blame --ignore-rev abc123 path/to/file

# Create ignore file for common commits
echo "abc123 # formatting commit" >> .git-blame-ignore-revs
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

### Git Bisect

```bash
# Start bisect
git bisect start

# Mark bad commit (usually current)
git bisect bad

# Mark known good commit
git bisect good v1.0.0

# Git checks out middle - test and mark
git bisect good  # or git bisect bad

# Continue until found
# Git will say "abc123 is the first bad commit"

# Reset
git bisect reset

# Automated bisect with test script
git bisect start HEAD v1.0.0
git bisect run ./test.sh
# test.sh should exit 0 for good, 1 for bad
```

### Finding Lost Commits

```bash
# Show all ref updates (including deleted)
git reflog

# Recover deleted branch
git reflog | grep "branch-name"
git checkout -b recovered-branch abc123

# Find dangling commits
git fsck --lost-found

# Search for commit by message (even deleted)
git log --all --oneline | grep "message"
```

## Advanced Git Commands

### Stash Management

```bash
# Stash with message
git stash push -m "WIP: feature X"

# Stash including untracked files
git stash push -u

# List stashes
git stash list

# Apply specific stash
git stash apply stash@{2}

# Pop (apply and remove)
git stash pop

# Create branch from stash
git stash branch new-branch stash@{0}

# Drop specific stash
git stash drop stash@{0}
```

### Cherry-pick

```bash
# Apply specific commit
git cherry-pick abc123

# Cherry-pick without committing
git cherry-pick --no-commit abc123

# Cherry-pick range
git cherry-pick abc123..def456

# Continue after conflict resolution
git cherry-pick --continue

# Abort
git cherry-pick --abort
```

### Reset vs Revert

```bash
# Reset: move branch pointer (rewrites history)
git reset --soft HEAD~1   # Keep changes staged
git reset --mixed HEAD~1  # Keep changes unstaged (default)
git reset --hard HEAD~1   # Discard changes

# Revert: create inverse commit (safe for shared branches)
git revert abc123
git revert HEAD~3..HEAD  # Revert range
```

### Clean Working Directory

```bash
# Show what would be deleted
git clean -n

# Delete untracked files
git clean -f

# Delete untracked files and directories
git clean -fd

# Delete ignored files too
git clean -fdx

# Interactive mode
git clean -i
```

## Git Configuration Tips

```bash
# Useful aliases
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.cm commit
git config --global alias.lg "log --oneline --graph --all"
git config --global alias.last "log -1 HEAD"
git config --global alias.unstage "reset HEAD --"

# Better defaults
git config --global pull.rebase true
git config --global fetch.prune true
git config --global diff.colorMoved zebra
git config --global init.defaultBranch main

# Credential caching
git config --global credential.helper cache  # 15 min
git config --global credential.helper 'cache --timeout=3600'  # 1 hour
```
