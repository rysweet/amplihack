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

## When This Workflow Applies

This workflow should be followed for:

- New features
- Bug fixes
- Refactoring
- Any non-trivial code changes

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

### Step 1.5: Analyze Task for Verbosity Adjustment

**Purpose**: Dynamically adjust message frequency based on task complexity and type to match user's verbosity preference appropriately.

**Reference**: See `.claude/context/VERBOSITY_MATRIX.md` for complete guidance.

Before proceeding with execution:

1. **Assess Task Complexity** (1-13 scale):
   - Count affected files/components (1-2 = Simple, 3-7 = Moderate, 8+ = Complex)
   - Identify integration points (external dependencies, APIs, services)
   - Evaluate architectural impact (breaking changes, new modules, refactoring)
   - Assign complexity score: Simple (1-4), Moderate (5-8), Complex (9-13)

2. **Identify Task Type** (keyword analysis):
   - **Investigation**: "investigate", "explain", "understand", "how does", "why", "analyze"
   - **Implementation**: "add", "create", "build", "implement", "develop", "write"
   - **Debugging**: "fix", "debug", "resolve", "error", "issue", "problem"
   - **Refactoring**: "refactor", "restructure", "simplify", "cleanup", "reorganize"
   - Select primary type based on keyword matches

3. **Look Up Verbosity Setting**:
   - Read `.claude/context/USER_PREFERENCES.md`
   - Extract current verbosity value: concise/balanced/detailed

4. **Calculate Target Message Count**:
   - Use VERBOSITY_MATRIX.md table
   - Look up [user preference × complexity level × task type]
   - Note target message range (e.g., "30-45 messages")
   - Note update frequency (Minimal/Regular/Frequent/Verbose)

5. **Log Verbosity Decision** (in session logs):

   ```
   Verbosity Analysis:
   - Task Complexity: [score]/13 ([Simple/Moderate/Complex])
   - Task Type: [Investigation/Implementation/Debugging/Refactoring]
   - User Preference: [concise/balanced/detailed]
   - Target Message Count: [min-max] messages
   - Update Frequency: [Minimal/Regular/Frequent/Verbose]
   ```

6. **Apply Message Batching Rules** (throughout session):
   - **Rule 1**: Batch independent tool calls (5 messages → 1 message, 80% reduction)
   - **Rule 2**: Combine status with action (3 messages → 1-2 messages, 33-50% reduction)
   - **Rule 3**: Summary over play-by-play (5 messages → 1-2 messages, 60-80% reduction)
   - Follow update frequency guidelines from matrix
   - Aim for target message range (some variance acceptable)

**Examples**:

- **Moderate Investigation + Balanced**: Target 30-45 messages, Regular frequency
- **Simple Implementation + Concise**: Target 12-18 messages, Minimal frequency
- **Complex Debugging + Detailed**: Target 100-140 messages, Verbose frequency

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

- [ ] **Use** architect agent to design solution architecture
- [ ] **Use** api-designer agent for API contracts (if applicable)
- [ ] **Use** database agent for data model design (if applicable)
- [ ] **Use** tester agent to write failing tests (TDD approach)
- [ ] **Use** security agent to identify security requirements
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
