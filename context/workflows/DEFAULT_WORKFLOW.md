---
name: DEFAULT_WORKFLOW
version: 1.1.0
description: Standard 22-step workflow (Steps 0-21) for feature development, bug fixes, and refactoring
steps: 22
phases:
  - requirements-clarification
  - design
  - implementation
  - testing
  - review
  - merge
success_criteria:
  - "All steps completed"
  - "PR is mergeable"
  - "CI passes"
  - "Philosophy compliant"
philosophy_alignment:
  - principle: Ruthless Simplicity
    application: Each step has single clear purpose
  - principle: Zero-BS Implementation
    application: No stubs or placeholders in deliverables
  - principle: Test-Driven Development
    application: Write tests before implementation
  - principle: Modular Design
    application: Clean module boundaries enforced through workflow
customizable: true
---

# Default Coding Workflow

This file defines the default workflow for all non-trivial code changes.

You can customize this workflow by editing this file.

## How This Workflow Works

**This workflow is the single source of truth for:**

- The order of operations (steps must be followed sequentially)
- Git workflow (branch, commit, push, PR process)
- CI/CD integration points
- Review and merge requirements

## When This Workflow Applies

This workflow should be followed for:

- New features
- Bug fixes
- Refactoring
- Any non-trivial code changes

**Execution approach:**

- Start with using the SlashCommand(amplihack:ultrathink) for any non-trivial task
- The workflow defines the process; agents execute the work
- Each step below leverages specialized agents whenever possible
- UltraThink orchestrates parallel agent execution for maximum efficiency
- When you customize this workflow, UltraThink adapts automatically

## TodoWrite Best Practices

When creating todos during workflow execution, reference the workflow steps directly:

- Format: `Step N: [Step Name] - [Specific Action]`
- This helps users track exactly which workflow step is active
- Always show your full ToDo list
- When you get to a particular step, you may always decide to break it down into smaller steps - this is preferred.

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

- **Track Progress**: Users can see exactly which step is active (e.g., "Step 5 of 22")

**Example Todo Structure (Single Workflow):**

```
Step 0: Workflow Preparation - Read workflow, create todos for ALL steps (0-21)
Step 1: Prepare the Workspace - Check git status and fetch
Step 2: Rewrite and Clarify Requirements - Use prompt-writer agent to clarify task
Step 3: Create GitHub Issue - Define requirements and constraints using gh issue create
Step 4: Setup Worktree and Branch - Create feat/issue-XXX branch in worktrees/
Step 5: Research and Design - Use architect agent for solution design
...
Step 16: Review the PR - MANDATORY code review
Step 17: Implement Review Feedback - MANDATORY
...
Step 21: Ensure PR is Mergeable - TASK COMPLETION POINT
```

**Example Todo Structure (Multiple Parallel Workflows):**

```
[PR1090 TASK] Step 0: Workflow Preparation - Create todos for ALL steps (0-21)
[PR1090 TASK] Step 1: Prepare the Workspace - Check git status
[PR1090 TASK] Step 2: Rewrite and Clarify Requirements - Use prompt-writer agent
[FEATURE-X] Step 0: Workflow Preparation - Create todos for ALL steps (0-21)
[FEATURE-X] Step 3: Setup Worktree and Branch - Create feat/issue-XXX branch
[BUGFIX-Y] Step 16: Review the PR - MANDATORY code review
...
```

This step-based structure helps users understand:

- Exactly which workflow step is currently active
- How many steps remain
- What comes next in the workflow

## The Workflow

### Step 0: Workflow Preparation (MANDATORY - DO NOT SKIP)

**CRITICAL: This step MUST be completed before ANY implementation work begins.**

**Why This Step Exists:**

Agents that skip workflow steps (especially mandatory review steps 10, 16-17) create quality issues and erode user trust. This step ensures agents track ALL steps from the start, preventing "completion bias" where agents feel done after implementation but before review.

**Root Cause Prevention:**

- **Completion Bias**: Agents often consider "PR created" as task completion
- **Context Decay**: After heavy implementation, agents lose sight of remaining steps
- **Autonomy Misapplication**: Being autonomous means making implementation decisions independently, NOT skipping mandatory process steps

**Checklist:**

- [ ] **Read this entire workflow file** - Understand all 22 steps (0-21) before starting
- [ ] **Create TodoWrite entries for ALL steps (0-21)** using format: `Step N: [Step Name] - [Specific Action]`
- [ ] **Mark each step complete ONLY when truly done** - No premature completion
- [ ] **Task is NOT complete until Step 21 is marked complete**

**Self-Verification:** Before proceeding to Step 1, confirm you have 22 todo items visible (Steps 0-21).

**Anti-Pattern Prevention:**

- ❌ DO NOT skip to implementation after reading requirements
- ❌ DO NOT consider "PR created" as completion (Step 21 is the completion point)
- ❌ DO NOT omit Steps 10, 16-17 (mandatory review steps)
- ❌ DO NOT declare task complete with pending steps
- ✅ DO create all step todos BEFORE starting any implementation
- ✅ DO mark steps complete sequentially as you finish them
- ✅ DO track every mandatory step in TodoWrite

**Reference Issue:** This step was added after Issue #1607 identified workflow step skipping as a recurring problem.

### Step 1: Prepare the Workspace

**Prerequisite Check:** Verify Step 0 is complete - you should have 22 todos visible (Steps 0-21) before proceeding.

- [ ] start with a clean local environment and make sure it is up to date (no unstashed changes, git fetch)

### Step 2: Rewrite and Clarify Requirements

- [ ] **FIRST: Identify explicit user requirements** that CANNOT be optimized away
- [ ] **Always use** prompt-writer agent to clarify task requirements (includes automatic task classification)
- [ ] **Use** analyzer agent to understand existing codebase context
- [ ] **Use** ambiguity agent if requirements are unclear - employ other agents using Task() tool or Skills() using Skill tool as needed
- [ ] Remove ambiguity from the task description - using your own best judgement to work autonomously and independently
- [ ] Define clear success criteria
- [ ] Document acceptance criteria
- [ ] **CRITICAL: Pass explicit requirements to ALL subsequent agents**

### Step 3: Create GitHub Issue

- [ ] **Use** GitHub issue creation tool via agent
- [ ] Create issue using `gh issue create`
- [ ] Include clear problem description
- [ ] Define requirements and constraints
- [ ] Add success criteria
- [ ] Assign appropriate labels

### Step 4: Setup Worktree and Branch

- [ ] **Always use** worktree-manager agent for worktree operations
- [ ] Create new git worktree in `./worktrees/{branch-name}` for isolated development
- [ ] Create branch with format: `feat/issue-{number}-{brief-description}` always branch from an up to date main unless specifically instructed otherwise.
- [ ] Command: `git worktree add ./worktrees/{branch-name} -b {branch-name}`
- [ ] Push branch to remote with tracking: `git push -u origin {branch-name}`
- [ ] Switch to new worktree directory: `cd ./worktrees/{branch-name}`

### Step 5: Research and Design

**⚠️ INVESTIGATION-FIRST PATTERN**: If the existing codebase or system is unfamiliar/complex, consider running the Skills tool Skill(investigation-workflow) or ~@amplihack:workflow/INVESTIGATION_WORKFLOW.md FIRST, then return here to continue development. This is especially valuable when:

- The codebase area is unfamiliar or poorly documented
- The feature touches multiple complex subsystems
- You need to understand existing patterns before designing new ones
- The architecture or integration points are unclear

After investigation completes, continue with these tasks:

- [ ] check for any Skill tool Skills() that are applicable to this task and employ them
- [ ] **Use** architect agent to design solution architecture
- [ ] **Use** api-designer agent for API contracts (if applicable)
- [ ] **Use** database agent for data model design (if applicable)
- [ ] **Use** security agent to identify security requirements
- [ ] use other subagents as appropriate if their expertise is applicable to the problem
- [ ] **💡 TIP**: For diagnostic follow-up questions during research, consider [parallel agent investigation](@amplihack:CLAUDE.md#parallel-agent-investigation-strategy)
- [ ] ask @zen-architect agent to review everything done so far and provide feedback
- [ ] ask @architect agent to consider the feedback
- [ ] Document module specifications
- [ ] Create detailed implementation plan
- [ ] Identify risks and dependencies

### Step 6: Retcon Documentation Writing

- [ ] ask @documentation-writer agent to retcon write the documentation for the finished feature as if it already exists - ie the documentation for the feature as we want it to be. Write ONLY the documentation, not the code.
- [ ] ask the @architect agent to review the documentation to see if it aligns with their vision correctly or if it highlights any changes that should be made
- [ ] ask @documentation-writer to make revisions based ont he architect's review

### Step 7: Test Driven Development - Writing Tests First

- [ ] Followingg the Test Driven Development methodology - use the tester agent to write failing tests (TDD approach) based upon the work done so far.

### Step 8: Implement the Solution

- [ ] **Always use** builder agent to implement from specifications, including considering the retcon'd documentation
- [ ] **Use** integration agent for external service connections
- [ ] Follow the architecture design, leverage appropriate skills with the Skill() tool as needed, handoff to other subagents if appropriate
- [ ] Make failing tests pass iteratively
- [ ] Ensure all requirements are met
- [ ] Update documentation as needed

### Step 9: Refactor and Simplify

- [ ] **CRITICAL: Provide cleanup agent with original user requirements**
- [ ] **Always use** cleanup agent for ruthless simplification WITHIN user constraints
- [ ] **Use** optimizer agent for performance improvements
- [ ] Remove unnecessary abstractions (that weren't explicitly requested)
- [ ] Eliminate dead code (unless user explicitly wanted it)
- [ ] Simplify complex logic (without violating user specifications)
- [ ] Ensure single responsibility principle
- [ ] Verify no placeholders remain - no stubs, no TODOs, no swallowed exceptions, no unimplemented functions - follow the zero-BS principle.
- [ ] **VALIDATE: All explicit user requirements still preserved** and still adhering to @amplihack:context/PHILOSOPHY.md

### Step 10: Review Pass Before Commit

- [ ] **Always use** reviewer agent for comprehensive code review
- [ ] **Use** security agent for security review
- [ ] Check code quality and standards
- [ ] Verify philosophy compliance with the philosophy-guardian agent
- [ ] Ensure adequate test coverage
- [ ] Identify potential improvements
- [ ] Ensure there are no TODOs, faked apis or faked data, stubs, or swallowed exceptions, no unimplemented functions - follow the zero-BS principle.

### Step 11: Incorporate Any Review Feedback

- [ ] Use the architect agent to assess the reviewer feedback and then handoff to the builder agent to implement any changes
- [ ] Update documentation as needed

### Step 12: Run Tests and Pre-commit Hooks

- [ ] **Use** pre-commit-diagnostic agent if hooks fail
- [ ] **💡 TIP**: For test failures, use [parallel investigation](@amplihack:CLAUDE.md#parallel-agent-investigation-strategy) to explore issues while continuing work
- [ ] Run all unit tests
- [ ] Execute `pre-commit run --all-files`
- [ ] Fix any linting issues
- [ ] Fix any formatting issues
- [ ] Resolve type checking errors
- [ ] Iterate until all checks pass

### Step 13: Mandatory Local Testing (NOT in CI)

**CRITICAL: Test all changes locally in realistic scenarios BEFORE committing.**
Test like a user would use the feature - outside-in - not just unit tests.

- [ ] **Test simple use cases** - Basic functionality verification
- [ ] **Test complex use cases** - Edge cases and longer operations
- [ ] **Test integration points** - External dependencies and APIs
- [ ] **Verify no regressions** - Ensure existing functionality still works
- [ ] **Document test results** - What was tested and results for the PR description (to be used in a moment) not in the repo
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

### Step 14: Commit and Push

- [ ] Stage all changes
- [ ] Write detailed commit message
- [ ] Reference issue number in commit
- [ ] Describe what changed and why
- [ ] Push to remote branch
- [ ] Verify push succeeded

### Step 15: Open Pull Request as Draft

- [ ] Create PR as DRAFT using `gh pr create --draft` (pipe through `| cat` for reliable output)
- [ ] Link to the GitHub issue
- [ ] Write comprehensive description
- [ ] Include test plan and the rsults of any testing that you have already captured
- [ ] Add screenshots if UI changes
- [ ] Add "WIP" or "Draft" context to indicate work in progress
- [ ] Request appropriate reviewers (optional - they can review draft)

**Important**: When using `gh` commands, always pipe through `cat` to ensure output is displayed:

```bash
gh pr create --draft --title "..." --body "..." 2>&1 | cat
```

**Why Draft First:**

- Allows review and feedback while still iterating
- Signals the PR is not yet ready to merge
- Enables CI checks to run early
- Creates space for philosophy and quality checks before marking ready
- Prevents premature merge while work continues

This ensures you see success messages, error details, and PR URLs.

### Step 16: Review the PR

**⚠️ MANDATORY - DO NOT SKIP ⚠️**

**REQUIRED FOR ALL PRs**

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
- [ ] Always Post the review as a comment on the PR

### Step 17: Implement Review Feedback

**⚠️ MANDATORY - DO NOT SKIP ⚠️**

**REQUIRED FOR ALL PRs**

- Unaddressed feedback means the review process was pointless and creates confusion about whether feedback was considered
- Indicates disrespect for reviewer's time and expertise
- May block PR merge indefinitely

**Feedback implementation checklist:**

- [ ] Review all feedback comments, think very carefully about each one and decide how to address it (or if you should disagree, explain why in a comment)
- [ ] **Always use** builder agent to implement changes
- [ ] **Use** relevant specialized agents for specific feedback
- [ ] Address each review comment
- [ ] Push updates to PR
- [ ] Respond to review comments by posting replies as coments on the PR
- [ ] Ensure all tests still pass
- [ ] Ensure PR is still mergeable
- [ ] Request re-review if needed

### Step 18: Philosophy Compliance Check

- [ ] **Always use** reviewer agent for final philosophy check
- [ ] **Use** patterns agent to verify pattern compliance
- [ ] Verify ruthless simplicity achieved
- [ ] Confirm bricks & studs pattern followed
- [ ] Ensure zero-BS implementation (no stubs, faked apis, swalloed exceptions, etc)
- [ ] Verify all tests passing
- [ ] Check documentation completeness and accuracy

### Step 19: Final Cleanup and Verification

- [ ] **CRITICAL: Provide cleanup agent with original user requirements AGAIN**
- [ ] **Always use** cleanup agent for final quality pass
- [ ] Review all changes for philosophy compliance WITHIN user constraints
- [ ] Remove any temporary artifacts or test files (unless user wanted them)
- [ ] Eliminate unnecessary complexity (that doesn't violate user requirements)
- [ ] Verify module boundaries remain clean
- [ ] Ensure zero dead code or stub implementations (unless explicitly requested)
- [ ] **FINAL CHECK: All explicit user requirements preserved**
- [ ] Ensure any cleanup agent changes get committed, validated by pre-commit, pushed to remote
- [ ] Add a comment to the PR about any work the Cleanup agent did

### Step 20: Convert PR to Ready for Review

- [ ] Convert draft PR to ready-for-review using `gh pr ready`
- [ ] Verify all previous steps completed
- [ ] Ensure all review feedback has been addressed
- [ ] Confirm philosophy compliance check passed
- [ ] Add comment summarizing changes and readiness
- [ ] Tag reviewers for final approval

**Important**: Only convert to ready when:

- All review feedback addressed
- Philosophy compliance verified
- You believe the PR is truly ready to merge
- No known blockers remain

```bash
gh pr ready 2>&1 | cat
```

**Why This Step Matters:**

- Signals transition from "work in progress" to "ready to merge"
- Indicates you've completed all quality checks
- Requests final approval from reviewers
- Makes PR eligible for merge queue

### Step 21: Ensure PR is Mergeable

- [ ] Check CI status (all checks passing)
- [ ] **Always use** ci-diagnostic-workflow agent if CI fails
- [ ] **💡 TIP**: When investigating CI failures, use [parallel agent investigation](@amplihack:CLAUDE.md#parallel-agent-investigation-strategy) to explore logs and code simultaneously
- [ ] Resolve any merge conflicts
- [ ] Verify all review comments addressed, including check for any that showed up after marking the PR as ready
- [ ] Confirm PR is approved
- [ ] Notify that PR is ready to merge

## Customization

To customize this workflow:

1. Edit this file to modify, add, or remove steps
2. Save your changes
3. The updated workflow will be used for future tasks
