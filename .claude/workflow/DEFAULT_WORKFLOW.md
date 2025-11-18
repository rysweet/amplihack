# Default Coding Workflow

<!-- THIS WORKFLOW MUST BE FOLLOWED -->
<!-- MANDATORY: This workflow defines the authoritative process for all non-trivial code changes -->
<!-- SKIP AT YOUR OWN RISK: Skipping steps leads to bugs, rework, and failed PRs -->

**CRITICAL READING REQUIREMENT**: Before starting ANY task, Claude MUST:

1. Read this ENTIRE workflow file (DEFAULT_WORKFLOW.md)
2. Identify which steps apply to the current task
3. Create todos using TodoWrite that reference specific step numbers
4. Execute steps in the defined order

This file defines the default workflow for all non-trivial code changes.
You can customize this workflow by editing this file.

## Workflow Variables

Configure these variables to customize workflow behavior:

```yaml
# Required Reading
WORKFLOW_ENFORCEMENT: MANDATORY # Never skip without explicit user permission

# TodoWrite Format
TODO_FORMAT: "Step N: [Step Name] - [Action]" # MANDATORY format for all todos
WORKFLOW_PREFIX_REQUIRED: true # Must reference workflow steps in todos

# Agent Usage
AGENT_DELEGATION_MODE: MAXIMUM # Use agents for every applicable step
PARALLEL_EXECUTION_DEFAULT: true # Execute independent operations in parallel

# Git Configuration
WORKTREE_REQUIRED: true # Always use worktrees for isolation
BRANCH_FORMAT: "feat/issue-{number}-{brief-description}"

# Quality Gates
PRE_COMMIT_REQUIRED: true # Must pass pre-commit before commit
LOCAL_TESTING_REQUIRED: true # Must test locally before push (Step 8)
CI_VALIDATION_REQUIRED: true # CI must pass before merge
PHILOSOPHY_CHECK_REQUIRED: true # Must verify philosophy compliance (Step 13)

# Review Requirements
SELF_REVIEW_REQUIRED: true # Always review your own PR (Step 11)
REVIEWER_AGENT_REQUIRED: true # Use reviewer agent for PR analysis
SECURITY_REVIEW_REQUIRED: true # Security agent review for sensitive changes
```

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

**IMPORTANT: For specialized scenarios, use these alternative workflows:**

- **Large Features (10+ files)**: Use Document-Driven Development (DDD) workflow
  - See: `.claude/workflow/DDD_WORKFLOW.md`
  - Commands: `/ddd:0-help`, `/ddd:1-plan`, `/ddd:2-docs`, etc.
  - When: Multi-file features requiring clear specifications

- **Codebase Understanding**: Use Investigation workflow
  - See: `.claude/workflow/INVESTIGATION_WORKFLOW.md`
  - Use when: Analyzing unfamiliar code or system architecture
  - Creates persistent documentation in `.claude/docs/`

- **Pre-Commit Failures**: Use Pre-Commit Diagnostic workflow
  - See: `.claude/agents/amplihack/specialized/pre-commit-diagnostic.md`
  - Trigger: "Pre-commit failed", "Can't commit", "Hooks failing"
  - Handles: Formatting, linting, type checking before push

- **CI Failures**: Use CI Diagnostic workflow
  - See: `.claude/agents/amplihack/specialized/ci-diagnostic-workflow.md`
  - Trigger: "CI failing", "Fix CI", "Make PR mergeable"
  - Iterates until PR is mergeable (never auto-merges)

- **Rapid Fix Patterns**: Use Fix Agent workflow
  - See: `.claude/agents/amplihack/specialized/fix-agent.md`
  - Command: `/fix [pattern] [scope]`
  - Patterns: import, ci, test, config, quality, logic

**Cross-Workflow Integration Points:**

1. **Step 4 + Investigation**: If codebase is unfamiliar, run INVESTIGATION_WORKFLOW before continuing
2. **Step 7 + Pre-Commit**: If hooks fail, use pre-commit-diagnostic agent
3. **Step 14 + CI**: If CI fails, use ci-diagnostic-workflow agent
4. **Any Step + Fix**: For specific error patterns, use fix-agent with appropriate pattern

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

### Step 11: Review the PR

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

## Self-Validation Questions

**Before claiming you followed this workflow, ask yourself:**

### Workflow Adherence

- [ ] Did I read this ENTIRE workflow file before starting?
- [ ] Did I create todos using TodoWrite with "Step N: [Step Name]" format?
- [ ] Did I execute steps in the defined sequential order?
- [ ] Did I use specialized agents at every applicable step?
- [ ] Did I skip any steps without explicit user permission?

### Requirements Preservation

- [ ] Did I identify explicit user requirements that CANNOT be optimized away?
- [ ] Did I pass these requirements to ALL subsequent agents?
- [ ] Did cleanup/simplification agents preserve ALL user requirements?
- [ ] Did I validate that no user requirements were lost?

### Quality Gates

- [ ] Did I run local testing BEFORE committing (Step 8)?
- [ ] Did I pass all pre-commit hooks (Step 7)?
- [ ] Did I run a self-review using reviewer agent (Step 11)?
- [ ] Did I verify philosophy compliance (Step 13)?
- [ ] Did I ensure CI passes before marking PR ready (Step 14)?

### Git Workflow

- [ ] Did I use a worktree for isolation (Step 3)?
- [ ] Did I create a properly formatted branch name?
- [ ] Did I write a detailed commit message referencing the issue?
- [ ] Did I create a comprehensive PR description with test plan (Step 10)?

### Agent Usage

- [ ] Did I use prompt-writer agent for requirements (Step 1)?
- [ ] Did I use architect agent for design (Step 4)?
- [ ] Did I use builder agent for implementation (Step 5)?
- [ ] Did I use cleanup agent for simplification (Step 6)?
- [ ] Did I use reviewer agent for PR review (Step 11)?
- [ ] Did I provide explicit user requirements to cleanup agents?

### Documentation

- [ ] Did I update relevant documentation files?
- [ ] Did I add inline documentation to new code?
- [ ] Did I document any discoveries in `.claude/context/DISCOVERIES.md`?
- [ ] Did I include a test plan in the PR description?

**If you answered "No" to ANY of these questions, you did NOT follow this workflow.**

**Common Skip Patterns to Avoid:**

1. "I'll just quickly implement this..." → Skipped Steps 1-4
2. "Tests can wait until later..." → Skipped TDD approach
3. "Pre-commit is annoying..." → Skipped Step 7
4. "I'll test in CI..." → Skipped Step 8 (local testing)
5. "It's a small change, no review needed..." → Skipped Step 11
6. "Philosophy check is overkill..." → Skipped Step 13

**Remember: Every skipped step increases the risk of bugs, rework, and failed PRs.**
