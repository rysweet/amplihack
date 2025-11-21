# Default Coding Workflow

This file defines the default workflow for all non-trivial code changes.
You can customize this workflow by editing this file.

## How This Workflow Works

**This workflow is the single source of truth for:**

- The order of operations (steps must be followed sequentially)
- Git workflow (branch, commit, push, PR process)
- CI/CD integration points
- Review and merge requirements

**Execution approach:**

- Start with `/ultrathink` for any non-trivial task
- UltraThink reads this workflow and orchestrates agents to execute it
- Each step leverages specialized agents for maximum effectiveness
- The workflow defines the process; agents execute the work

## Default Execution with UltraThink

**For all non-trivial tasks, start with `/ultrathink` to orchestrate the workflow:**

- `/ultrathink` reads this workflow and executes it with multi-agent coordination
- Each step below leverages specialized agents whenever possible
- UltraThink orchestrates parallel agent execution for maximum efficiency
- When you customize this workflow, UltraThink adapts automatically

**TodoWrite Usage During Workflow Execution:**

When creating todos during workflow execution, reference the workflow steps directly:

- Format: `Step N: [Step Name] - [Specific Action]`
- Example: `Step 1: Rewrite and Clarify Requirements - Use prompt-writer agent`
- This helps users track exactly which workflow step is active (Step X of 15)

## When This Workflow Applies

This workflow should be followed for:

- New features
- Bug fixes
- Refactoring
- Any non-trivial code changes

## TodoWrite Best Practices

When using TodoWrite during workflow execution:

- **Reference Step Numbers**: Include the workflow step number in todo content
  - Example: `Step 1: Rewrite and Clarify Requirements - Use prompt-writer agent`
  - Example: `Step 4: Research and Design - Use architect agent for solution design`

- **Workstream Prefixes** (Optional): When running multiple workflows in parallel, prefix todos with workstream name
  - Format: `[WORKSTREAM] Step N: Description`
  - Example: `[PR1090 TASK] Step 1: Rewrite and Clarify Requirements`
  - Example: `[FEATURE-X] Step 4: Research and Design - Use architect agent`
  - This helps track which todos belong to which parallel workstream

- **Be Specific**: Include the specific agent or action for each step
  - Example: `Step 5: Implement the Solution - Use builder agent from specifications`

- **Track Progress**: Users can see exactly which step is active (e.g., "Step 5 of 15")

**Example Todo Structure (Single Workflow):**

```
Step 1: Rewrite and Clarify Requirements - Use prompt-writer agent to clarify task
Step 2: Create GitHub Issue - Define requirements and constraints using gh issue create
Step 3: Setup Worktree and Branch - Create feat/issue-XXX branch in worktrees/
Step 4: Research and Design - Use architect agent for solution design
Step 5: Implement the Solution - Use builder agent to implement from specifications
...
```

**Example Todo Structure (Multiple Parallel Workflows):**

```
[PR1090 TASK] Step 1: Rewrite and Clarify Requirements - Use prompt-writer agent
[PR1090 TASK] Step 2: Create GitHub Issue - Define requirements using gh issue create
[PR1090 TASK] Step 4: Research and Design - Use architect agent for solution design
[FEATURE-X] Step 1: Rewrite and Clarify Requirements - Use prompt-writer agent
[FEATURE-X] Step 3: Setup Worktree and Branch - Create feat/issue-XXX branch
[BUGFIX-Y] Step 5: Implement the Solution - Use builder agent from specifications
...
```

This step-based structure helps users understand:

- Exactly which workflow step is currently active
- How many steps remain (e.g., Step 5 of 15 means 10 steps left)
- What comes next in the workflow

## The 15-Step Workflow

### Step 1: Rewrite and Clarify Requirements

- [ ] **FIRST: Identify explicit user requirements** that CANNOT be optimized away
- [ ] **Always use** prompt-writer agent to clarify task requirements
- [ ] **Use** analyzer agent to understand existing codebase context
- [ ] **Use** ambiguity agent if requirements are unclear
- [ ] Remove ambiguity from the task description
- [ ] Define clear success criteria
- [ ] Document acceptance criteria
- [ ] **CRITICAL: Pass explicit requirements to ALL subsequent agents**

### Step 2: Create GitHub Issue

- [ ] **Use** GitHub issue creation tool via agent
- [ ] Create issue using `gh issue create`
- [ ] Include clear problem description
- [ ] Define requirements and constraints
- [ ] Add success criteria
- [ ] Assign appropriate labels

### Step 3: Setup Worktree and Branch

- [ ] **Always use** worktree-manager agent for worktree operations
- [ ] Create new git worktree in `./worktrees/{branch-name}` for isolated development
- [ ] Create branch with format: `feat/issue-{number}-{brief-description}`
- [ ] Command: `git worktree add ./worktrees/{branch-name} -b {branch-name}`
- [ ] Push branch to remote with tracking: `git push -u origin {branch-name}`
- [ ] Switch to new worktree directory: `cd ./worktrees/{branch-name}`

### Step 4: Research and Design with TDD

**⚠️ INVESTIGATION-FIRST PATTERN**: If the existing codebase or system is unfamiliar/complex, consider running the **INVESTIGATION_WORKFLOW.md** (6 phases) FIRST, then return here to continue development. This is especially valuable when:

- The codebase area is unfamiliar or poorly documented
- The feature touches multiple complex subsystems
- You need to understand existing patterns before designing new ones
- The architecture or integration points are unclear

After investigation completes, continue with these tasks:

- [ ] **Use** architect agent to design solution architecture
- [ ] **Use** api-designer agent for API contracts (if applicable)
- [ ] **Use** database agent for data model design (if applicable)
- [ ] **Use** tester agent to write failing tests (TDD approach)
- [ ] **Use** security agent to identify security requirements
- [ ] **💡 TIP**: For diagnostic follow-up questions during research, consider [parallel agent investigation](.claude/CLAUDE.md#parallel-agent-investigation-strategy)
- [ ] Document module specifications
- [ ] Create detailed implementation plan
- [ ] Identify risks and dependencies

### Step 5: Implement the Solution

- [ ] **Always use** builder agent to implement from specifications
- [ ] **Use** integration agent for external service connections
- [ ] Follow the architecture design
- [ ] Make failing tests pass iteratively
- [ ] Ensure all requirements are met
- [ ] Add inline documentation

### Step 6: Refactor and Simplify

- [ ] **CRITICAL: Provide cleanup agent with original user requirements**
- [ ] **Always use** cleanup agent for ruthless simplification WITHIN user constraints
- [ ] **Use** optimizer agent for performance improvements
- [ ] Remove unnecessary abstractions (that weren't explicitly requested)
- [ ] Eliminate dead code (unless user explicitly wanted it)
- [ ] Simplify complex logic (without violating user specifications)
- [ ] Ensure single responsibility principle
- [ ] Verify no placeholders remain - no stubs, no TODOs, no swallowed exceptions, no unimplemented functions - follow the zero-BS principle.
- [ ] **VALIDATE: All explicit user requirements still preserved**

### Step 7: Run Tests and Pre-commit Hooks

- [ ] **Use** pre-commit-diagnostic agent if hooks fail
- [ ] **💡 TIP**: For test failures, use [parallel investigation](.claude/CLAUDE.md#parallel-agent-investigation-strategy) to explore issues while continuing work
- [ ] Run all unit tests
- [ ] Execute `pre-commit run --all-files`
- [ ] Fix any linting issues
- [ ] Fix any formatting issues
- [ ] Resolve type checking errors
- [ ] Iterate until all checks pass

### Step 8: Mandatory Local Testing (NOT in CI)

**CRITICAL: Test all changes locally in realistic scenarios BEFORE committing.**

- [ ] **Test simple use cases** - Basic functionality verification
- [ ] **Test complex use cases** - Edge cases and longer operations
- [ ] **Test integration points** - External dependencies and APIs
- [ ] **Verify no regressions** - Ensure existing functionality still works
- [ ] **Document test results** - What was tested and results
- [ ] **RULE: Never commit without local testing**

**Examples of required tests:**

- If proxy changes: Test simple and long requests locally
- If API changes: Test with real client requests
- If CLI changes: Run actual commands with various options
- If database changes: Test with actual data operations

**Why this matters:**

- CI checks can't catch all real-world issues
- Local testing catches problems before they reach users
- Faster feedback loop than waiting for CI
- Prevents embarrassing failures after merge

### Step 9: Commit and Push

- [ ] Stage all changes
- [ ] Write detailed commit message
- [ ] Reference issue number in commit
- [ ] Describe what changed and why
- [ ] Push to remote branch
- [ ] Verify push succeeded

### Step 10: Open Pull Request

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

### ═══════════════════════════════════════════════════════════════════════════

### Step 11: Review the PR

### ═══════════════════════════════════════════════════════════════════════════

**⚠️ MANDATORY - DO NOT SKIP ⚠️**

**REQUIRED FOR ALL PRs**

**Timing: Within 24 hours of PR creation**

**Consequences of skipping:**

- Violates workflow integrity
- No PR should merge without thorough review
- Quality gates exist for a reason - bypassing them introduces risk
- Pattern of skipping reviews leads to technical debt accumulation

**Review checklist:**

- [ ] **Always use** reviewer agent for comprehensive code review
- [ ] **Use** security agent for security review
- [ ] Check code quality and standards
- [ ] Verify philosophy compliance
- [ ] Ensure adequate test coverage
- [ ] Post review comments on PR
- [ ] Identify potential improvements
- [ ] Ensure there are no TODOs, stubs, or swallowed exceptions, no unimplemented functions - follow the zero-BS principle.
- [ ] Post the review as a comment on the PR

### ═══════════════════════════════════════════════════════════════════════════

### Step 12: Implement Review Feedback

### ═══════════════════════════════════════════════════════════════════════════

**⚠️ MANDATORY - DO NOT SKIP ⚠️**

**REQUIRED FOR ALL PRs**

**Timing: Within 48 hours of receiving review feedback**

**Consequences of skipping:**

- Violates workflow integrity
- Unaddressed feedback means the review process was pointless
- Creates confusion about whether feedback was considered
- Indicates disrespect for reviewer's time and expertise
- May block PR merge indefinitely

**Feedback implementation checklist:**

- [ ] Review all feedback comments, think very carefully about each one and decide how to address it (or if you should disagree, explain why in a comment)
- [ ] **Always use** builder agent to implement changes
- [ ] **Use** relevant specialized agents for specific feedback
- [ ] Address each review comment
- [ ] Push updates to PR
- [ ] Respond to review comments by posting replies
- [ ] Ensure all tests still pass
- [ ] Ensure PR is still mergeable
- [ ] Request re-review if needed

### Step 13: Philosophy Compliance Check

- [ ] **Always use** reviewer agent for final philosophy check
- [ ] **Use** patterns agent to verify pattern compliance
- [ ] Verify ruthless simplicity achieved
- [ ] Confirm bricks & studs pattern followed
- [ ] Ensure zero-BS implementation (no stubs)
- [ ] Verify all tests passing
- [ ] Check documentation completeness

### Step 14: Ensure PR is Mergeable

- [ ] Check CI status (all checks passing)
- [ ] **Always use** ci-diagnostic-workflow agent if CI fails
- [ ] **💡 TIP**: When investigating CI failures, use [parallel agent investigation](.claude/CLAUDE.md#parallel-agent-investigation-strategy) to explore logs and code simultaneously
- [ ] Resolve any merge conflicts
- [ ] Verify all review comments addressed
- [ ] Confirm PR is approved
- [ ] Notify that PR is ready to merge

### Step 15: Final Cleanup and Verification

- [ ] **CRITICAL: Provide cleanup agent with original user requirements AGAIN**
- [ ] **Always use** cleanup agent for final quality pass
- [ ] Review all changes for philosophy compliance WITHIN user constraints
- [ ] Remove any temporary artifacts or test files (unless user wanted them)
- [ ] Eliminate unnecessary complexity (that doesn't violate user requirements)
- [ ] Verify module boundaries remain clean
- [ ] Ensure zero dead code or stub implementations (unless explicitly requested)
- [ ] **FINAL CHECK: All explicit user requirements preserved**
- [ ] Confirm PR remains mergeable after cleanup

## Customization

To customize this workflow:

1. Edit this file to modify, add, or remove steps
2. Save your changes
3. The updated workflow will be used for future tasks

## Philosophy Notes

This workflow enforces our core principles:

- **Ruthless Simplicity**: Each step has one clear purpose
- **Test-Driven Development**: Write tests before implementation
- **Quality Gates**: Multiple review and validation steps
- **Documentation**: Clear commits and PR descriptions
