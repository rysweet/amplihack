# Goal: GitHub Pull Request Manager

Autonomous agent for managing GitHub pull requests - reviewing, labeling, merging, and maintaining PR workflow.

## Constraints

- Must use GitHub CLI (gh) and Git
- Should complete PR reviews within 10 minutes
- Must follow branch protection rules
- Should not force-push or delete branches without approval

## Success Criteria

- Reviews PRs for code quality, tests, documentation
- Applies appropriate labels (bug, feature, documentation, etc.)
- Checks CI status before merging
- Posts review comments with specific feedback
- Merges approved PRs following merge strategy
- Creates release notes from merged PRs

## Context

This agent helps maintain PR workflow by:

- Reviewing new PRs automatically
- Labeling based on content
- Checking tests and CI
- Merging when approved and passing
- Tracking what was released
