# Git Worktree Guide for AmplihACK

Git worktrees are a powerful feature that allow you to have multiple branches checked out simultaneously in different directories. This guide shows how to use git worktrees effectively with AmplihACK for parallel development workflows.

## Table of Contents

- [Quick Start](#quick-start)
- [Core Features](#core-features)
- [Advanced Workflows](#advanced-workflows)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Basic Workflow

```bash
# Create a new worktree for experimentation
git worktree add ../amplihack-my-feature -b my-feature

# Navigate to the new worktree
cd ../amplihack-my-feature

# Work on your feature
# ...make changes, test, etc...

# When done, go back and remove it
cd ../amplihack
git worktree remove ../amplihack-my-feature
git branch -d my-feature  # Delete the branch if done
```

### Why Use Worktrees?

1. **Parallel Experiments**: Test multiple approaches simultaneously
2. **Clean Isolation**: Each worktree has its own branch and files
3. **Fast Switching**: No stashing/unstashing or branch switching needed
4. **Risk-Free**: Experiment freely without affecting your main work

## Core Features

### Creating Worktrees

```bash
# Create with new branch
git worktree add ../amplihack-feature-name -b feature-name

# Create from existing branch
git worktree add ../amplihack-existing existing-branch

# Create from remote branch
git worktree add ../amplihack-remote-feature -b remote-feature origin/remote-feature
```

**What happens:**
- Creates directory: `../amplihack-feature-name/`
- Creates/checks out branch: `feature-name`
- Full working directory ready to use
- Share same git objects as main repo (efficient!)

### Directory Naming Convention

AmplihACK uses a hyphen (`-`) separator between repo name and feature:
- `amplihack-feature-name` - Clear separation
- `amplihack-complex-feature-name` - Handles hyphens in names
- `amplihack-username-feature` - For namespaced branches

### Listing and Removing

```bash
# List all active worktrees
git worktree list

# Remove a worktree
cd ../amplihack  # Go to main repo
git worktree remove ../amplihack-feature-name

# Force remove (even with uncommitted changes)
git worktree remove --force ../amplihack-feature-name

# Delete the branch when done (optional)
git branch -d feature-name  # Safe delete (only if merged)
git branch -D feature-name  # Force delete
```

## Advanced Workflows

### Working with Remote Branches

Pull down branches created on other machines or by teammates:

```bash
# Fetch latest branches
git fetch origin

# Create worktree from remote branch
git worktree add ../amplihack-remote-feature -b remote-feature origin/remote-feature

# Or track an existing remote branch
git worktree add ../amplihack-team-feature --track origin/team-feature
```

**What happens:**
- Fetches latest from origin
- Creates local worktree tracking the remote branch
- Sets up directory as `amplihack-team-feature`
- Ready to continue work started elsewhere

**Perfect for:**
- Continuing work started on another machine
- Checking out a colleague's branch for review
- Testing branches from CI/CD pipelines

### Parallel Development Pattern

```bash
# Create multiple worktrees for different approaches
git worktree add ../amplihack-approach-redis -b approach-redis
git worktree add ../amplihack-approach-memcached -b approach-memcached
git worktree add ../amplihack-approach-inmemory -b approach-inmemory

# Test each in parallel
cd ../amplihack-approach-redis && python -m pytest
cd ../amplihack-approach-memcached && python -m pytest
cd ../amplihack-approach-inmemory && python -m pytest

# Keep the winner, remove the rest
cd ../amplihack
git worktree remove ../amplihack-approach-memcached
git worktree remove ../amplihack-approach-inmemory
git branch -D approach-memcached approach-inmemory
```

### Emergency Bug Fix Pattern

```bash
# You're working on a feature, but need to fix urgent bug
# Current worktree: amplihack-new-feature

# Create hotfix worktree from main
cd ../amplihack
git worktree add ../amplihack-hotfix-login -b hotfix-login

# Fix the bug
cd ../amplihack-hotfix-login
# ...make fix...
git commit -m "Fix login issue"
git push origin hotfix-login

# Create PR, get it merged, then clean up
cd ../amplihack
git worktree remove ../amplihack-hotfix-login
git branch -d hotfix-login

# Return to feature work
cd ../amplihack-new-feature
# Your feature work is untouched!
```

## Best Practices

### 1. Naming Conventions

```bash
# Feature development
git worktree add ../amplihack-feat-authentication -b feat-authentication

# Bug fixes
git worktree add ../amplihack-fix-login-error -b fix-login-error

# Experiments
git worktree add ../amplihack-exp-new-algorithm -b exp-new-algorithm

# With namespaces
git worktree add ../amplihack-myname-feat-caching -b myname/feat-caching
```

### 2. Keep Worktrees Focused

Each worktree should have a single, clear purpose:
- One feature per worktree
- One bug fix per worktree
- One experiment per worktree

Don't try to work on multiple unrelated changes in the same worktree.

### 3. Clean Up Regularly

```bash
# List all worktrees
git worktree list

# Remove finished ones
git worktree remove ../amplihack-old-feature
git branch -d old-feature

# Prune stale worktree metadata
git worktree prune
```

### 4. Cross-Machine Workflow

**Machine A (office):**
```bash
cd amplihack
git worktree add ../amplihack-my-feature -b my-feature
cd ../amplihack-my-feature
# ...work on feature...
git push -u origin my-feature
```

**Machine B (home):**
```bash
cd amplihack
git fetch origin
git worktree add ../amplihack-my-feature -b my-feature origin/my-feature
cd ../amplihack-my-feature
# ...continue work...
```

### 5. Integration with AmplihACK Features

Each worktree has access to all AmplihACK features:
- All agents available through Claude Code
- All commands and workflows
- Shared git history and configuration

**Note:** Each worktree may need its own Python virtual environment if you're installing different dependencies for experiments.

## Command Reference

| Command | Description | Example |
|---------|-------------|---------|
| `git worktree add <path> -b <branch>` | Create new worktree with new branch | `git worktree add ../amplihack-feat -b my-feature` |
| `git worktree add <path> <branch>` | Create from existing branch | `git worktree add ../amplihack-feat existing-branch` |
| `git worktree list` | List all worktrees | `git worktree list` |
| `git worktree remove <path>` | Remove worktree | `git worktree remove ../amplihack-feat` |
| `git worktree remove --force <path>` | Force remove with changes | `git worktree remove --force ../amplihack-feat` |
| `git worktree prune` | Clean up stale metadata | `git worktree prune` |
| `git worktree lock <path>` | Prevent worktree removal | `git worktree lock ../amplihack-feat` |
| `git worktree unlock <path>` | Allow worktree removal | `git worktree unlock ../amplihack-feat` |

## Troubleshooting

### "Worktree already exists" Error

If you get this error, the branch might already have a worktree:
```bash
git worktree list  # Check existing worktrees
git worktree remove ../amplihack-old-one  # Remove if needed
```

### Can't Remove Worktree

If normal remove fails:
```bash
# Force remove (loses uncommitted changes!)
git worktree remove --force ../amplihack-stubborn-feature

# Manual cleanup if completely broken
rm -rf ../amplihack-stubborn-feature
git worktree prune
git branch -D stubborn-feature
```

### Worktree Directory Deleted Manually

If you deleted the worktree directory without using `git worktree remove`:
```bash
# Clean up git's metadata
git worktree prune

# Delete the branch if needed
git branch -D old-feature-branch
```

### VSCode Not Recognizing Worktree

VSCode might need a restart after creating worktrees:
1. Create worktree
2. Open the worktree directory in VSCode
3. If git features aren't working, reload VSCode window (Ctrl+Shift+P → "Reload Window")

### Branch Already Exists

If the branch already exists but isn't checked out:
```bash
# Use the existing branch
git worktree add ../amplihack-existing existing-branch

# Or create from it
git worktree add ../amplihack-new -b new-branch existing-branch
```

## Advanced Tips

### 1. Quickly Navigate Between Worktrees

Add aliases to your shell:
```bash
# In ~/.bashrc or ~/.zshrc
alias wt-main='cd ~/repos/amplihack'
alias wt-list='cd ~/repos/amplihack && git worktree list'

# Function to cd into a worktree by name
wt() {
  cd ~/repos/amplihack-$1
}
# Usage: wt my-feature
```

### 2. Creating Worktrees from Tags

```bash
# Create worktree from a specific tag (read-only exploration)
git worktree add ../amplihack-v1.0 v1.0.0 --detach

# Make changes based on a tag
git worktree add ../amplihack-hotfix-v1 -b hotfix-v1 v1.0.0
```

### 3. Sharing Git Config

All worktrees share the main repo's config:
```bash
# In any worktree
git config --local user.email "you@example.com"
# Applies to all worktrees
```

### 4. Using with Python Virtual Environments

Each worktree can have its own venv:
```bash
# In main repo
python -m venv .venv

# In worktree
cd ../amplihack-experiment
python -m venv .venv  # Different venv for experiments
source .venv/bin/activate
pip install experimental-library
```

### 5. Clean Up All Stale Worktrees

```bash
# Remove all prunable worktrees at once
git worktree prune

# Script to remove all except main
for wt in $(git worktree list --porcelain | grep "worktree" | grep -v "$(pwd)" | cut -d' ' -f2); do
  git worktree remove "$wt"
done
```

## Integration with AmplihACK Workflows

### Using Agents Across Worktrees

Each worktree can use all AmplihACK agents:
```bash
cd ../amplihack-my-experiment
claude  # Start Claude with all agents available
# "Use /amplihack:architect to design this experiment"
```

### Parallel Testing with Different Approaches

Test multiple implementations while preserving separate histories:
```bash
# In worktree 1
cd ../amplihack-approach-a
claude  # Design approach A
# Work on implementation

# In worktree 2
cd ../amplihack-approach-b
claude  # Design approach B
# Work on implementation

# Compare results and choose the better approach
```

### Using with DEFAULT_WORKFLOW.md

Each worktree follows the same workflow but on separate branches:
```bash
# Create feature worktree
git worktree add ../amplihack-new-feature -b feat/issue-123-new-feature

# Follow the workflow
cd ../amplihack-new-feature
# Step 3: Branch already created ✓
# Step 4: Research and design...
# Step 5: Implement...
# etc.

# Main work continues uninterrupted in main worktree
```

## Summary

Git worktrees in AmplihACK provide a powerful way to:
- **Experiment freely** without fear of breaking your main work
- **Test in parallel** to find the best solution faster
- **Handle urgent work** without disrupting current progress
- **Collaborate easily** by adopting branches from anywhere

The core git worktree commands give you full control over parallel development workflows. Use them to experiment with different approaches, handle urgent fixes, or simply keep your work organized across multiple branches.

**Key Principles:**
- One worktree = one focus
- Clean up when done
- Use descriptive names
- Keep branches synchronized across machines

With these patterns, you'll be able to work more efficiently and fearlessly experiment with new ideas while keeping your main work safe and stable.
