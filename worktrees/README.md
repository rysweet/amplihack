# Git Worktrees Directory

This directory contains isolated git worktrees for parallel development.

## Usage

Worktrees are automatically created here by the worktree-manager agent during workflow execution.

## Structure

Each worktree is a separate working directory:
- ./worktrees/feat-issue-123-description/
- ./worktrees/fix-issue-456-bug-name/

## Cleanup

Remove completed worktrees with:
```bash
git worktree remove ./worktrees/{branch-name}
```

Or prune references to deleted worktrees:
```bash
git worktree prune
```

