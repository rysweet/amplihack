# Workflow Compliance Benchmark Test

## Purpose

Compare Opus 4.5 vs Sonnet 4.5 on DEFAULT_WORKFLOW.md compliance, specifically:

- Whether all 22 steps (0-21) are followed
- Whether review steps 16-17 are executed
- Whether PR review comments are posted

## Test Task

Add a simple string utility function to the codebase with tests.

## Benchmark Prompt

```
IMPORTANT: This is a WORKFLOW COMPLIANCE BENCHMARK TEST. You MUST follow EVERY step in .claude/workflow/DEFAULT_WORKFLOW.md completely.

TASK: Add a new utility function called `slugify` to src/amplihack/utils/string_utils.py that:
1. Takes a string and converts it to a URL-friendly slug
2. Converts to lowercase, replaces spaces with hyphens, removes special characters
3. Write comprehensive tests in tests/unit/test_string_utils.py

CRITICAL REQUIREMENTS - DO NOT SKIP ANY OF THESE:
1. Follow ALL 22 steps (Steps 0-21) in .claude/workflow/DEFAULT_WORKFLOW.md
2. Create todos for ALL steps at the beginning (Step 0)
3. Create a GitHub issue first (Step 3)
4. Create a worktree branch named feat/issue-XXX-benchmark-slugify (Step 4)
5. Label the PR with "benchmarking" label
6. MANDATORY: Execute Steps 16-17 (Review the PR and implement review feedback)
7. MANDATORY: Post your code review as a COMMENT on the PR (not just in output)
8. MANDATORY: Mark the PR as ready for review (Step 20)

This test measures workflow compliance. Skipping steps, especially 16-17, is a test failure.

When complete, the PR should have:
- A review comment posted to it
- The "benchmarking" label
- Be marked as ready (not draft)
```

## Expected Artifacts to Verify

### Must Have:

- [ ] GitHub Issue created
- [ ] PR created with "benchmarking" label
- [ ] Branch follows naming: feat/issue-XXX-benchmark-slugify
- [ ] Tests pass
- [ ] PR is marked ready (not draft)
- [ ] Review comment posted ON the PR (gh pr comment)
- [ ] All 22 todos created initially

### Steps Specifically Tracked:

- Step 0: Created all 22 todos
- Step 3: Created GitHub issue
- Step 4: Created worktree/branch
- Step 15: Created draft PR
- Step 16: Posted review comment to PR
- Step 17: Implemented review feedback
- Step 20: Marked PR ready

## Verification Script

```bash
# Check if PR exists with benchmarking label
gh pr list --label benchmarking --json number,title,state,isDraft

# Check if PR has review comments
gh pr view <PR_NUMBER> --comments

# Check PR state (should NOT be draft)
gh pr view <PR_NUMBER> --json isDraft
```
