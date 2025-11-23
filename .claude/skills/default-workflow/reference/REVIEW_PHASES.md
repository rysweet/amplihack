# Review and Merge Phases (Steps 9-15)

This document contains the final phases of the default workflow: commit, review, and merge.

These steps follow after completing **Steps 1-8** (Requirements through Testing) in [../SKILL.md](../SKILL.md).

## Step 9: Commit and Push

- [ ] Stage all changes
- [ ] Write detailed commit message
- [ ] Reference issue number in commit
- [ ] Describe what changed and why
- [ ] Push to remote branch
- [ ] Verify push succeeded

## Step 10: Open Pull Request

- [ ] Create PR using `gh pr create` (pipe through `| cat` for reliable output)
- [ ] Link to the GitHub issue
- [ ] Write comprehensive description
- [ ] Include test plan
- [ ] Add screenshots if UI changes
- [ ] Request appropriate reviewers

**Important**: When using `gh` commands, always pipe through `cat` to ensure output is displayed:

```bash
gh pr create --title "..." --body "..." 2>&1 | cat
```

This ensures you see success messages, error details, and PR URLs.

## Step 11: Review the PR

- [ ] **Always use** reviewer agent for comprehensive code review
- [ ] **Use** security agent for security review
- [ ] Check code quality and standards
- [ ] Verify philosophy compliance
- [ ] Ensure adequate test coverage
- [ ] Post review comments on PR
- [ ] Identify potential improvements
- [ ] Ensure there are no TODOs, stubs, or swallowed exceptions, no unimplemented functions - follow the zero-BS principle.
- [ ] Post the review as a comment on the PR

## Step 12: Implement Review Feedback

- [ ] Review all feedback comments, think very carefully about each one and decide how to address it (or if you should disagree, explain why in a comment)
- [ ] **Always use** builder agent to implement changes
- [ ] **Use** relevant specialized agents for specific feedback
- [ ] Address each review comment
- [ ] Push updates to PR
- [ ] Respond to review comments by posting replies
- [ ] Ensure all tests still pass
- [ ] Ensure PR is still mergeable
- [ ] Request re-review if needed

## Step 13: Philosophy Compliance Check

- [ ] **Always use** reviewer agent for final philosophy check
- [ ] **Use** patterns agent to verify pattern compliance
- [ ] Verify ruthless simplicity achieved
- [ ] Confirm bricks & studs pattern followed
- [ ] Ensure zero-BS implementation (no stubs)
- [ ] Verify all tests passing
- [ ] Check documentation completeness

## Step 14: Ensure PR is Mergeable

- [ ] Check CI status (all checks passing)
- [ ] **Always use** ci-diagnostic-workflow agent if CI fails
- [ ] **💡 TIP**: When investigating CI failures, use [parallel agent investigation](.claude/CLAUDE.md#parallel-agent-investigation-strategy) to explore logs and code simultaneously
- [ ] Resolve any merge conflicts
- [ ] Verify all review comments addressed
- [ ] Confirm PR is approved
- [ ] Notify that PR is ready to merge

## Step 15: Final Cleanup and Verification

- [ ] **CRITICAL: Provide cleanup agent with original user requirements AGAIN**
- [ ] **Always use** cleanup agent for final quality pass
- [ ] Review all changes for philosophy compliance WITHIN user constraints
- [ ] Remove any temporary artifacts or test files (unless user wanted them)
- [ ] Eliminate unnecessary complexity (that doesn't violate user requirements)
- [ ] Verify module boundaries remain clean
- [ ] Ensure zero dead code or stub implementations (unless explicitly requested)
- [ ] **FINAL CHECK: All explicit user requirements preserved**
- [ ] Confirm PR remains mergeable after cleanup

---

## Return to Main Workflow

See [../SKILL.md](../SKILL.md) for Steps 1-8 and workflow overview.
