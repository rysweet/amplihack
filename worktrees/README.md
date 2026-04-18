# Git Worktrees Directory

This directory contains isolated git worktrees for parallel development.

## Usage

Worktrees are automatically created here by the worktree-manager agent during workflow execution.

## Structure

Each worktree is a separate working directory:

- ./worktrees/feat-issue-123-description/
- ./worktrees/fix-issue-456-bug-name/

## Automatic Stale Registration Handling

The default workflow's `step-04-setup-worktree` automatically runs
`git worktree prune` after removing orphaned worktree directories. This
prevents `fatal: already registered worktree` errors when reattaching to
a branch whose directory was deleted out-of-band. See
[docs/recipes/step-04-worktree-reattach-prune.md](../docs/recipes/step-04-worktree-reattach-prune.md)
for details.

## Cleanup

Remove completed worktrees with:

```bash
git worktree remove ./worktrees/{branch-name}
```

Or prune references to deleted worktrees:

```bash
git worktree prune
```
