---
name: Dependabot Auto-Merge
description: Automatically merges safe Dependabot dependency updates after tests pass
on:
  pull_request:
    types: [opened, synchronize]
permissions:
  contents: read
  pull-requests: read
  checks: read
tools:
  github:
    toolsets: [default]
timeout-minutes: 10
strict: true
---

# Dependabot Auto-Merge

This workflow automatically merges safe Dependabot dependency updates after tests pass.

## Workflow

1. **Detect Dependabot PRs**: Only run on pull requests created by Dependabot
2. **Verify Safety**: Check that the PR contains only dependency updates
3. **Wait for Tests**: Ensure all required checks pass
4. **Auto-Merge**: Automatically merge safe dependency updates

## Safe Update Criteria

- PR author is `dependabot[bot]`
- All CI checks pass
- PR is not a major version bump (configurable)
- No manual review required for patch/minor updates

## Configuration

The workflow uses safe-outputs to ensure:

- `require-checks: true` - All required status checks must pass
- `require-approval: false` - No manual approval needed for safe updates

This reduces maintenance overhead while maintaining safety through automated testing.
