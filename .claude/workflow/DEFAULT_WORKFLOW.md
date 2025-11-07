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

**TodoWrite Usage During UltraThink Execution:**

- Create initial todo list with all workflow phases labeled (see TodoWrite Best Practices below)
- Update todos frequently during phase transitions to show progress
- Include phase context in task descriptions (e.g., "PHASE 2: DESIGN - Use architect agent...")
- Mark entire phases as completed when transitioning to the next phase
- This helps users track progress and understand which workflow phase is active

## When This Workflow Applies

This workflow should be followed for:

- New features
- Bug fixes
- Refactoring
- Any non-trivial code changes

## TodoWrite Best Practices

When using TodoWrite during workflow execution:

- **Group by Phase**: Label related tasks with phase context for clarity
  - Example: `PHASE 1: PLANNING - Create GitHub issue`
  - Example: `PHASE 2: DESIGN - Use architect agent to design solution`

- **Update Frequently**: Update todo status during phase transitions to show progress

- **Be Descriptive**: Include agent names and specific actions in task descriptions

- **Show Progress**: When transitioning between major phases, update the entire todo list to reflect new phase focus

**Example Todo Structure:**
```
PHASE 1: PLANNING - Create GitHub issue
PHASE 1: PLANNING - Setup worktree and branch
PHASE 2: DESIGN - Use architect agent to design solution
PHASE 2: DESIGN - Use tester agent to write failing tests
PHASE 3: IMPLEMENTATION - Use builder agent to implement from specs
PHASE 4: VALIDATION - Run tests and pre-commit hooks
PHASE 5: FINALIZATION - Use cleanup agent for final quality pass
```

This phase labeling helps users understand:
- Which workflow phase they're currently in
- How much progress has been made overall
- What's coming next in the workflow

## The 15-Step Workflow

### Step 1: Rewrite and Clarify Requirements
**WORKFLOW PHASE: PLANNING (Phase 1 of 5)**

- [ ] **FIRST: Identify explicit user requirements** that CANNOT be optimized away
- [ ] **Always use** prompt-writer agent to clarify task requirements
- [ ] **Use** analyzer agent to understand existing codebase context
- [ ] **Use** ambiguity agent if requirements are unclear
- [ ] Remove ambiguity from the task description
- [ ] Define clear success criteria
- [ ] Document acceptance criteria
- [ ] **CRITICAL: Pass explicit requirements to ALL subsequent agents**

### Step 2: Create GitHub Issue
**WORKFLOW PHASE: PLANNING (Phase 1 of 5)**

- [ ] **Use** GitHub issue creation tool via agent
- [ ] Create issue using `gh issue create`
- [ ] Include clear problem description
- [ ] Define requirements and constraints
- [ ] Add success criteria
- [ ] Assign appropriate labels

### Step 3: Setup Worktree and Branch
**WORKFLOW PHASE: PLANNING (Phase 1 of 5)**

- [ ] **Always use** worktree-manager agent for worktree operations
- [ ] Create new git worktree in `./worktrees/{branch-name}` for isolated development
- [ ] Create branch with format: `feat/issue-{number}-{brief-description}`
- [ ] Command: `git worktree add ./worktrees/{branch-name} -b {branch-name}`
- [ ] Push branch to remote with tracking: `git push -u origin {branch-name}`
- [ ] Switch to new worktree directory: `cd ./worktrees/{branch-name}`

---
**📊 PROGRESS CHECKPOINT**: Planning phase complete! Update your todo list to reflect transition to Design phase.
---

### Step 4: Research and Design with TDD
**WORKFLOW PHASE: DESIGN (Phase 2 of 5)**

- [ ] **Use** architect agent to design solution architecture
- [ ] **Use** api-designer agent for API contracts (if applicable)
- [ ] **Use** database agent for data model design (if applicable)
- [ ] **Use** tester agent to write failing tests (TDD approach)
- [ ] **Use** security agent to identify security requirements
- [ ] **💡 TIP**: For diagnostic follow-up questions during research, consider [parallel agent investigation](.claude/CLAUDE.md#parallel-agent-investigation-strategy)
- [ ] Document module specifications
- [ ] Create detailed implementation plan
- [ ] Identify risks and dependencies

---
**📊 PROGRESS CHECKPOINT**: Design phase complete! Update your todo list to reflect transition to Implementation phase.
---

### Step 5: Implement the Solution
**WORKFLOW PHASE: IMPLEMENTATION (Phase 3 of 5)**

- [ ] **Always use** builder agent to implement from specifications
- [ ] **Use** integration agent for external service connections
- [ ] Follow the architecture design
- [ ] Make failing tests pass iteratively
- [ ] Ensure all requirements are met
- [ ] Add inline documentation

---
**📊 PROGRESS CHECKPOINT**: Implementation complete! Update your todo list to reflect transition to Validation phase.
---

### Step 6: Refactor and Simplify
**WORKFLOW PHASE: VALIDATION (Phase 4 of 5)**

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
**WORKFLOW PHASE: VALIDATION (Phase 4 of 5)**

- [ ] **Use** pre-commit-diagnostic agent if hooks fail
- [ ] **💡 TIP**: For test failures, use [parallel investigation](.claude/CLAUDE.md#parallel-agent-investigation-strategy) to explore issues while continuing work
- [ ] Run all unit tests
- [ ] Execute `pre-commit run --all-files`
- [ ] Fix any linting issues
- [ ] Fix any formatting issues
- [ ] Resolve type checking errors
- [ ] Iterate until all checks pass

### Step 8: Mandatory Local Testing (NOT in CI)
**WORKFLOW PHASE: VALIDATION (Phase 4 of 5)**

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
**WORKFLOW PHASE: VALIDATION (Phase 4 of 5)**

- [ ] Stage all changes
- [ ] Write detailed commit message
- [ ] Reference issue number in commit
- [ ] Describe what changed and why
- [ ] Push to remote branch
- [ ] Verify push succeeded

### Step 10: Open Pull Request
**WORKFLOW PHASE: VALIDATION (Phase 4 of 5)**

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

### Step 11: Review the PR
**WORKFLOW PHASE: VALIDATION (Phase 4 of 5)**

- [ ] **Always use** reviewer agent for comprehensive code review
- [ ] **Use** security agent for security review
- [ ] Check code quality and standards
- [ ] Verify philosophy compliance
- [ ] Ensure adequate test coverage
- [ ] Post review comments on PR
- [ ] Identify potential improvements
- [ ] Ensure there are no TODOs, stubs, or swallowed exceptions, no unimplemented functions - follow the zero-BS principle.
- [ ] Post the review as a comment on the PR

### Step 12: Implement Review Feedback
**WORKFLOW PHASE: VALIDATION (Phase 4 of 5)**

- [ ] Review all feedback comments, think very carefully about each one and decide how to address it (or if you should disagree, explain why in a comment)
- [ ] **Always use** builder agent to implement changes
- [ ] **Use** relevant specialized agents for specific feedback
- [ ] Address each review comment
- [ ] Push updates to PR
- [ ] Respond to review comments by posting replies
- [ ] Ensure all tests still pass
- [ ] Ensure PR is still mergeable
- [ ] Request re-review if needed

---
**📊 PROGRESS CHECKPOINT**: Validation phase complete! Update your todo list to reflect transition to Finalization phase.
---

### Step 13: Philosophy Compliance Check
**WORKFLOW PHASE: FINALIZATION (Phase 5 of 5)**

- [ ] **Always use** reviewer agent for final philosophy check
- [ ] **Use** patterns agent to verify pattern compliance
- [ ] Verify ruthless simplicity achieved
- [ ] Confirm bricks & studs pattern followed
- [ ] Ensure zero-BS implementation (no stubs)
- [ ] Verify all tests passing
- [ ] Check documentation completeness

### Step 14: Ensure PR is Mergeable
**WORKFLOW PHASE: FINALIZATION (Phase 5 of 5)**

- [ ] Check CI status (all checks passing)
- [ ] **Always use** ci-diagnostic-workflow agent if CI fails
- [ ] **💡 TIP**: When investigating CI failures, use [parallel agent investigation](.claude/CLAUDE.md#parallel-agent-investigation-strategy) to explore logs and code simultaneously
- [ ] Resolve any merge conflicts
- [ ] Verify all review comments addressed
- [ ] Confirm PR is approved
- [ ] Notify that PR is ready to merge

### Step 15: Final Cleanup and Verification
**WORKFLOW PHASE: FINALIZATION (Phase 5 of 5)**

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
