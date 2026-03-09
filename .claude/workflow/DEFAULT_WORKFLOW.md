---
name: DEFAULT_WORKFLOW
version: 1.1.0
description: Standard workflow for feature development, bug fixes, and refactoring
steps: 23
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

## Workflow Progress Indicators

**Momentum Building**:

- ✅ Each completed step builds momentum toward completion
- ⚡ The workflow flows naturally from one step to the next
- 🎯 Every step completed brings you closer to a mergeable PR
- 🔄 Continuous progress maintains context and focus

**Flow Pattern**: Step 0 → Step 1 → Step 2 → ... → Step 22 (PR Mergeable)

# Default Coding Workflow

This file defines the default workflow for all non-trivial code changes.

You can customize this workflow by editing this file.

## Multi-Platform Support (GitHub + Azure DevOps)

This workflow supports both GitHub and Azure DevOps repositories. Platform-specific steps provide instructions for both platforms.

**Platform Detection**: Determine your platform from git remote URL:

```bash
git remote get-url origin
```

- Contains `github.com` → Use **GitHub** commands
- Contains `dev.azure.com` or `visualstudio.com` → Use **Azure DevOps** commands

**Prerequisites**:

- **GitHub**: Install and authenticate with `gh` CLI (`gh auth login`)
- **Azure DevOps**: Install and configure `az` CLI (`az login` and `az devops configure`)

Steps with platform-specific instructions: 3, 15, 21, 22

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

## ⚠️ WORKFLOW SELECTION (Read This First)

**This workflow is for NON-TRIVIAL changes only.**

### Quick Classification

Before starting, classify your task:

| Classification | Description                                         | Use Workflow          |
| -------------- | --------------------------------------------------- | --------------------- |
| **TRIVIAL**    | Config edit, doc update, < 10 lines                 | VERIFICATION_WORKFLOW |
| **SIMPLE**     | Straightforward change, < 50 lines, no architecture | SIMPLIFIED_WORKFLOW   |
| **COMPLEX**    | New feature, architecture needed, 50+ lines         | DEFAULT_WORKFLOW      |

### Classification Questions

Ask yourself:

1. Is this a config file edit only? → **TRIVIAL**
2. Is this < 10 lines with no architecture needed? → **TRIVIAL**
3. Is this < 50 lines with clear implementation? → **SIMPLE**
4. Does this need design, architecture, or complex logic? → **COMPLEX**

**If TRIVIAL or SIMPLE**: STOP. Use the appropriate simplified workflow.

**If COMPLEX**: Continue with this workflow.

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
  - Example: `Step 2: Rewrite and Clarify Requirements - Use prompt-writer agent`
  - Example: `Step 5: Research and Design - Use architect agent for solution design`

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
Step 0: Workflow Preparation - Read workflow, create todos for ALL steps (0-22)
Step 1: Prepare the Workspace - Check git status and fetch
Step 2: Rewrite and Clarify Requirements - Use prompt-writer agent to clarify task
Step 3: Create GitHub Issue - Define requirements and constraints using gh issue create
Step 4: Setup Worktree and Branch - Create feat/issue-XXX branch in worktrees/
Step 5: Research and Design - Use architect agent for solution design
...
Step 16: Review the PR - MANDATORY code review
Step 17: Implement Review Feedback - MANDATORY
Step 19: Outside-In Testing in Real Environment - MANDATORY
Step 20c: Quality Audit Loop (3+ cycles, multi-agent validation)
...
Step 22: Ensure PR is Mergeable - TASK COMPLETION POINT
```

**Example Todo Structure (Multiple Parallel Workflows):**

```
[PR1090 TASK] Step 0: Workflow Preparation - Create todos for ALL steps (0-22)
[PR1090 TASK] Step 1: Prepare the Workspace - Check git status
[PR1090 TASK] Step 2: Rewrite and Clarify Requirements - Use prompt-writer agent
[FEATURE-X] Step 0: Workflow Preparation - Create todos for ALL steps (0-22)
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

- [ ] **Read this entire workflow file** - Understand all 23 steps (0-22) before starting
- [ ] **Create TodoWrite entries for ALL steps (0-22)** using format: `Step N: [Step Name] - [Specific Action]`
- [ ] **Mark each step complete ONLY when truly done** - No premature completion
- [ ] **Task is NOT complete until Step 22 is marked complete**

**Self-Verification:** Before proceeding to Step 1, confirm you have 23 todo items visible (Steps 0-22).

**Anti-Pattern Prevention:**

- ❌ DO NOT skip to implementation after reading requirements
- ❌ DO NOT consider "PR created" as completion (Step 22 is the completion point)
- ❌ DO NOT omit Steps 10, 16-17, 19 (mandatory review and testing steps)
- ❌ DO NOT declare task complete with pending steps
- ✅ DO create all step todos BEFORE starting any implementation
- ✅ DO mark steps complete sequentially as you finish them
- ✅ DO track every mandatory step in TodoWrite

**Reference Issue:** This step was added after Issue #1607 identified workflow step skipping as a recurring problem.

### Step 1: Prepare the Workspace

**Prerequisite Check:** Verify Step 0 is complete - you should have 23 todos visible (Steps 0-22) before proceeding.

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

### Step 3: Create Issue/Work Item

**Platform Detection**: Automatically detect your platform from git remote URL:

```bash
git remote get-url origin
```

- github.com → Use GitHub commands
- dev.azure.com or visualstudio.com → Use Azure DevOps commands

**For GitHub**:

```bash
gh issue create \
  --title "Title" \
  --body "Description" \
  --label "label1,label2"
```

**For Azure DevOps**:

```bash
python .claude/scenarios/az-devops-tools/create_work_item.py \
  --type "User Story" \
  --title "Title" \
  --description "Description"
```

- [ ] Include clear problem description
- [ ] Define requirements and constraints
- [ ] Add success criteria
- [ ] Assign appropriate labels/tags

### Step 4: Setup Worktree and Branch

- [ ] **Always use** worktree-manager agent for worktree operations
- [ ] Create new git worktree in `./worktrees/{branch-name}` for isolated development
- [ ] Create branch with format: `feat/issue-{number}-{brief-description}` always branch from an up to date main unless specifically instructed otherwise.
- [ ] Command: `git worktree add ./worktrees/{branch-name} -b {branch-name}`
- [ ] Push branch to remote with tracking: `git push -u origin {branch-name}`
- [ ] Switch to new worktree directory: `cd ./worktrees/{branch-name}`

### Step 5: Research and Design

**⚠️ INVESTIGATION-FIRST PATTERN**: If the existing codebase or system is unfamiliar/complex, consider running the Skills tool Skill(investigation-workflow) or ~.claude/workflow/INVESTIGATION_WORKFLOW.md FIRST, then return here to continue development. This is especially valuable when:

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
- [ ] **💡 TIP**: For diagnostic follow-up questions during research, consider [parallel agent investigation](~/.amplihack/.claude/CLAUDE.md#parallel-agent-investigation-strategy)
- [ ] ask @zen-architect agent to review everything done so far and provide feedback
- [ ] ask @architect agent to consider the feedback
- [ ] Document module specifications
- [ ] Create detailed implementation plan
- [ ] Identify risks and dependencies

### Step 5.5: Proportionality Check (MANDATORY)

Before proceeding to TDD, verify design matches implementation size:

**Implementation Size Estimate**:

- [ ] Count estimated lines of code to be changed
- [ ] Classify: TRIVIAL (< 10 lines), SIMPLE (10-50 lines), COMPLEX (50+ lines)

**Proportionality Decision**:

```yaml
If TRIVIAL:
  - Skip comprehensive TDD (Step 7)
  - Use verification testing only
  - Reason: "Config change - verify it works"

If SIMPLE:
  - Simplified TDD (1-2 test files max)
  - Focus on critical path only

If COMPLEX:
  - Proceed with full TDD (Step 7)
```

**Anti-Pattern Prevention**:

- ❌ DO NOT create elaborate test suites for config changes
- ❌ DO NOT write 50+ tests for < 10 lines of code
- ✅ DO match test effort to implementation complexity

### Step 6: Retcon Documentation Writing

- [ ] ask @documentation-writer agent to retcon write the documentation for the finished feature as if it already exists - ie the documentation for the feature as we want it to be. Write ONLY the documentation, not the code.
- [ ] ask the @architect agent to review the documentation to see if it aligns with their vision correctly or if it highlights any changes that should be made
- [ ] ask @documentation-writer to make revisions based on the architect's review

### Step 7: Test Driven Development - Writing Tests First

- [ ] Following the Test Driven Development methodology - use the tester agent to write failing tests (TDD approach) based upon the work done so far.

### Step 7.5: Test Proportionality Validation

Verify test suite size is proportional to implementation:

**Proportionality Formula**:

```
Test Ratio = (Test Lines) / (Implementation Lines)

Target Ratios:
- Config changes: 1:1 to 2:1 (verification only)
- Business logic: 3:1 to 5:1 (comprehensive tests)
- Critical paths: 5:1 to 10:1 (exhaustive tests)
```

**Validation Checklist**:

- [ ] Test ratio within target range for change type
- [ ] If ratio > 10:1, review for over-testing
- [ ] Remove redundant or low-value tests
- [ ] Consolidate similar test cases

**Escalation**: If ratio > 15:1, pause and consult prompt-writer agent to re-classify task complexity.

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
- [ ] **VALIDATE: All explicit user requirements still preserved** and still adhering to @~/.amplihack/.claude/context/PHILOSOPHY.md

### Step 10: Review Pass Before Commit

- [ ] **Always use** reviewer agent for comprehensive code review
- [ ] **Use** security agent for security review
- [ ] Check code quality and standards
- [ ] Verify philosophy compliance with the philosophy-guardian agent
- [ ] Ensure adequate test coverage
- [ ] Identify potential improvements
- [ ] Ensure there are no TODOs, faked apis or faked data, stubs, or swallowed exceptions, no unimplemented functions - follow the zero-BS principle.

#### PR Cleanliness Check (Pre-Commit)

**CRITICAL: Review staged changes for cleanliness BEFORE committing to git history.**

- [ ] **Unrelated Changes Review**: Check `git diff --staged` - all changes directly related to issue?
  - Remove any files modified for testing/debugging unrelated to the feature
  - Remove any experimental code not required for the feature
  - Remove any "while I'm here" improvements not in the issue scope

- [ ] **Temporary Files Check**: Scan for temporary/test artifacts
  - Pattern: `test_*.py`, `temp_*.js`, `scratch_*.md`, `debug_*.log`, `*.tmp`
  - Pattern: `experiment_*.py`, `test_manual_*.sh`, `playground_*.ts`
  - Remove all temporary files unless explicitly part of the feature requirements

- [ ] **Debugging Code Detection**: Search codebase for debugging statements
  - JavaScript/TypeScript: `console.log`, `console.debug`, `debugger;`
  - Python: `print()` for debugging (keep intentional logging), `breakpoint()`, `pdb.set_trace()`, `import pdb`
  - Remove all debugging code unless it's intentional logging/observability

- [ ] **Point-in-Time Documents Check**: Identify analysis/investigation documents
  - Pattern: `ANALYSIS_YYYYMMDD.md`, `INVESTIGATION_*.md`, `NOTES_*.txt`
  - Pattern: Date-stamped reports not intended as permanent documentation
  - Move to `~/.amplihack/.claude/runtime/logs/` or delete unless required for issue

- [ ] **Git Hygiene Verification**:
  - `.gitignore` properly configured for new file types introduced?
  - No large files (>500KB) added without justification? (Valid: test fixtures, vendored deps, binary assets)
  - No sensitive data or credentials in commits?

**Why This Matters:**

- Prevents clutter from entering git history
- Easier to review PRs with only relevant changes
- Maintains clean, professional codebase
- Reduces noise in git blame and history

### Step 11: Incorporate Any Review Feedback

- [ ] Use the architect agent to assess the reviewer feedback and then hand off to the builder agent to implement any changes
- [ ] Update documentation as needed

### Step 12: Run Tests and Pre-commit Hooks

- [ ] **Pre-commit Hook Check** (run once at start of Step 12): Ensure hooks are installed before running
  - Config exists? `test -f .pre-commit-config.yaml && echo "Config found" || echo "No config"`
  - Hooks installed? `test -f "$(git rev-parse --git-path hooks/pre-commit)" && echo "Hooks installed" || echo "Hooks missing"` (worktree-compatible)
  - If config exists but hooks don't: `pre-commit install`
  - This ensures fresh worktrees work without manual setup
  - ⚠️ **Security Note**: Always review `.pre-commit-config.yaml` changes before running hooks, especially when pulling updates or merging branches
- [ ] **Use** pre-commit-diagnostic agent if hooks fail
- [ ] **💡 TIP**: For test failures, use [parallel investigation](~/.amplihack/.claude/CLAUDE.md#parallel-agent-investigation-strategy) to explore issues while continuing work
- [ ] Run all unit tests
- [ ] Execute `pre-commit run --all-files`
- [ ] Fix any linting issues
- [ ] Fix any formatting issues
- [ ] Resolve type checking errors
- [ ] Iterate until all checks pass

### Step 13: Mandatory Local Testing (NOT in CI)

**CRITICAL: Test all changes locally in realistic scenarios BEFORE committing.**
Test like a user would use the feature - outside-in - not just unit tests.

**🚨 VERIFICATION GATE - CANNOT PROCEED WITHOUT:**

- [ ] **Test execution evidence documented** (outputs, screenshots, or results logged)
- [ ] **At least 2 test scenarios executed** (1 simple + 1 complex/integration)
- [ ] **Test results added to PR description** (include in Step 15)
- [ ] **Regression check completed** (verified existing features still work)

**⚠️ ABSOLUTE RULE**: Testing is ALWAYS possible. Figure out how. Never proceed to Step 14 without test results documented.

**"But I can't test this because..."**

There's always a way to test:

- **"Need fresh session"** → Open new terminal, start fresh Claude Code session, test there
- **"Documentation changes"** → Test in fresh session, verify guidance actually works
- **"Need clean state"** → Create clean state (new directory, fresh checkout, new session)
- **"Too complex"** → Test simpler scenarios that verify core behavior
- **"Takes too long"** → Test critical path only, document what wasn't tested

**No escape hatch. No approval path. Just find a way to test and document results.**

---

**Testing Checklist:**

- [ ] **Test simple use cases** - Basic functionality verification
- [ ] **Test complex use cases** - Edge cases and longer operations
- [ ] **Test integration points** - External dependencies and APIs
- [ ] **Verify no regressions** - Ensure existing functionality still works
- [ ] **Document test results** - What was tested and results for PR description

**Examples of required tests:**

- If proxy changes: Test simple and long requests locally
- If API changes: Test with real client requests
- If CLI changes: Run actual commands with various options
- If database changes: Test with actual data operations
- If documentation changes: Test in fresh session to verify behavior

**Test Results Template** (use in PR description):

```markdown
## Step 13: Local Testing Results

**Test Environment**: <branch, method, date>
**Tests Executed**:

1. Simple: <scenario> → <result> ✅/❌
2. Complex: <scenario> → <result> ✅/❌
   **Regressions**: <verification> → ✅ None detected
   **Issues Found**: <list any issues discovered and fixed>
```

**Why this matters:**

- CI checks can't catch all real-world issues
- Local testing catches problems before they reach users
- Faster feedback loop than waiting for CI
- Prevents embarrassing failures after merge
- **Verification gate prevents rationalization bypass**

### Step 14: Commit and Push

- [ ] Stage all changes
- [ ] Write detailed commit message
- [ ] Reference issue number in commit
- [ ] Describe what changed and why
- [ ] Push to remote branch
- [ ] Verify push succeeded

### Step 15: Open Pull Request as Draft

**For GitHub**:

```bash
gh pr create --draft \
  --title "Title" \
  --body "Description" \
  2>&1 | cat
```

**For Azure DevOps**:

```bash
python .claude/scenarios/az-devops-tools/create_pr.py \
  --source feature/branch \
  --target main \
  --title "Title" \
  --description "Description" \
  --draft
```

- [ ] Link to the issue/work item created in Step 3
- [ ] Write comprehensive description
- [ ] Include test plan and the results of any testing that you have already captured
- [ ] Add screenshots if UI changes
- [ ] Add "WIP" or "Draft" context to indicate work in progress
- [ ] Request appropriate reviewers (optional - they can review draft)

**Why Draft First:**

- Allows review and feedback while still iterating
- Signals the PR is not yet ready to merge
- Enables CI checks to run early
- Creates space for philosophy and quality checks before marking ready
- Prevents premature merge while work continues

### Step 16: Review the PR

**⚠️ MANDATORY - DO NOT SKIP ⚠️**

**REQUIRED FOR ALL PRs**

- Quality gates exist for a reason - bypassing them introduces risk
- Pattern of skipping reviews leads to technical debt accumulation

**Step 16a: Step 13 Compliance Verification**

- [ ] Check PR description has "Step 13: Local Testing Results" section with actual test execution evidence
- [ ] If missing: BLOCK review, comment on PR, request test results (no approval path - just do the testing)

**Step 16b: Invoke reviewer agent**

- [ ] **Always use** reviewer agent for comprehensive code review
  - **Alternative**: Use `/socratic-review` for dialogue-based review when learning is as important as fixing (mentoring, design documentation, complex code explanation)
- [ ] Check code quality and standards
- [ ] Ensure adequate test coverage
- [ ] Identify potential improvements
- [ ] Ensure there are no TODOs, stubs, or swallowed exceptions, no unimplemented functions - follow the zero-BS principle
- [ ] **POST structured review findings to the PR** → Evidence: review comment link

**Step 16c: Invoke security agent**

- [ ] **Use** security agent for security review
- [ ] Verify no security vulnerabilities introduced
- [ ] Check authentication/authorization if applicable
- [ ] Verify sensitive data handling
- [ ] **POST security review to the PR** → Evidence: security comment link

**Step 16d: Invoke philosophy-guardian agent**

- [ ] **Use** philosophy-guardian agent to verify philosophy compliance
- [ ] Verify ruthless simplicity achieved
- [ ] Confirm bricks & studs pattern followed
- [ ] Ensure zero-BS implementation
- [ ] **POST philosophy check to the PR** → Evidence: philosophy comment link

**Step 16e: Address blocking issues**

- [ ] Review all findings from 16b, 16c, 16d
- [ ] Address any blocking issues found before proceeding
- [ ] If issues found, fix and re-run applicable reviews

**Step 16f: Verification Gate**

**🚨 VERIFICATION GATE - Before marking Step 16 complete, verify:**

- [ ] Did I invoke the **reviewer** agent (not just code-review)?
- [ ] Did I invoke the **security** agent?
- [ ] Did I invoke the **philosophy-guardian** agent?
- [ ] Are all three reviews **posted to the PR** as comments?
- [ ] All blocking issues have been addressed?

**Cannot proceed to Step 17 without completing this gate.**

---

\*\*Post reviews as comments on the PR:

**For GitHub**:

```bash
gh pr comment <pr_number> --body "Review comment text"
```

**For Azure DevOps**:

```bash
az repos pr create-thread \
  --id <pr_number> \
  --comment "Review comment text"
```

### Step 17: Implement Review Feedback

**⚠️ MANDATORY - DO NOT SKIP ⚠️**

**REQUIRED FOR ALL PRs**

- Unaddressed feedback means the review process was pointless and creates confusion about whether feedback was considered
- Indicates disrespect for reviewer's time and expertise
- May block PR merge indefinitely

**Step 17a: Review all feedback**

- [ ] Gather all feedback comments from Step 16 reviews (reviewer, security, philosophy-guardian)
- [ ] Think very carefully about each comment
- [ ] Categorize: blocking issues vs. suggestions vs. questions

**Step 17b: Address feedback with builder agent**

- [ ] **Always use** builder agent to implement changes
- [ ] **Use** relevant specialized agents for specific feedback types
- [ ] Address each review comment substantively
- [ ] For disagreements, explain reasoning in a PR comment

**Step 17c: Push and respond**

- [ ] Push updates to PR
- [ ] Respond to each review comment with what was done
- [ ] Post replies as comments on the PR

**Step 17d: Verify and re-review if needed**

- [ ] Ensure all tests still pass
- [ ] Ensure PR is still mergeable
- [ ] Request re-review if significant changes were made

**Step 17e: Verification Gate**

**🚨 VERIFICATION GATE - Before marking Step 17 complete, verify:**

- [ ] Did I address EVERY feedback comment (not just some)?
- [ ] Did I respond to each comment on the PR explaining what was done?
- [ ] Did I use the builder agent for implementation changes?
- [ ] Are all tests still passing?

**Cannot proceed to Step 18 without completing this gate.**

---

**Feedback implementation checklist:**

- [ ] Respond to review comments by posting replies as comments on the PR:

**For GitHub**:

```bash
gh pr comment <pr_number> --body "Response to feedback"
```

**For Azure DevOps**:

```bash
az repos pr create-thread \
  --id <pr_number> \
  --comment "Response to feedback"
```

- [ ] Ensure all tests still pass
- [ ] Ensure PR is still mergeable
- [ ] Request re-review if needed

### Step 18: Philosophy Compliance Check

**Step 18a: Invoke reviewer agent for philosophy check**

- [ ] **Always use** reviewer agent for final philosophy check
- [ ] Verify implementation aligns with project philosophy
- [ ] Check for over-engineering or unnecessary complexity
- [ ] **Document findings** → Evidence: philosophy review notes

**Step 18b: Invoke patterns agent**

- [ ] **Use** patterns agent to verify pattern compliance
- [ ] Design patterns used correctly
- [ ] Architectural patterns followed
- [ ] Code organization patterns maintained
- [ ] **Document findings** → Evidence: patterns review notes

**Step 18c: Zero-BS verification**

- [ ] Verify ruthless simplicity achieved
- [ ] Confirm bricks & studs pattern followed
- [ ] Ensure zero-BS implementation:
  - No stubs
  - No faked APIs or data
  - No swallowed exceptions
  - No TODO comments
  - No unimplemented functions
- [ ] Verify all tests passing
- [ ] Check documentation completeness and accuracy

**Step 18d: Verification Gate**

**🚨 VERIFICATION GATE - Before marking Step 18 complete, verify:**

- [ ] Did I invoke the **reviewer** agent for philosophy check?
- [ ] Did I invoke the **patterns** agent?
- [ ] Did I complete the zero-BS verification checklist?
- [ ] Are all findings documented?
- [ ] Any issues found have been addressed?

**Cannot proceed to Step 19 without completing this gate.**

### Step 19: Outside-In Testing in Real Environment

**🚨 VERIFICATION GATE - CANNOT PROCEED WITHOUT:**

- [ ] **Test execution evidence documented** in realistic environment (Amplifier shadow or equivalent)
- [ ] **Test approach documented** based on interface type (CLI/TUI/Web/Electron/Config)
- [ ] **Test results added to PR description** (include in Step 21)
- [ ] **Real user flows tested** - not just unit tests, actual usage scenarios

**CRITICAL: This step complements Step 13 with realistic environment testing.**

Step 13 validates technical functionality locally. Step 19 validates real-world user experience in a production-like environment.

---

**Testing Approach by Interface Type:**

**For CLI/TUI applications:**

- [ ] Use `/outside-in-testing` skill for guided CLI/TUI testing workflow
- [ ] Test in fresh terminal session with production-like environment
- [ ] Execute actual commands with various flags and inputs
- [ ] Verify output formatting and error messages match expectations
- [ ] Test help text, autocomplete, and interactive prompts
- [ ] Document commands executed and their outputs

**For Web applications:**

- [ ] Deploy to Amplifier shadow environment (staging-like)
- [ ] Test in actual browser with realistic user flows
- [ ] Verify UI rendering, responsiveness, and interactions
- [ ] Test forms, navigation, error states, and loading states
- [ ] Check console for errors and network requests
- [ ] Document user flows tested with screenshots

**For Electron/desktop applications:**

- [ ] Deploy packaged application to test environment
- [ ] Test window management, menus, and keyboard shortcuts
- [ ] Verify file system interactions and permissions
- [ ] Test update mechanisms and crash recovery
- [ ] Document application behavior and screenshots

**For Configuration/infrastructure changes:**

- [ ] Deploy to shadow environment with configuration applied
- [ ] Verify services start correctly with new configuration
- [ ] Test rollback procedures if applicable
- [ ] Monitor logs for configuration-related warnings
- [ ] Document configuration values tested and results

---

**Using Amplifier Shadow Environment:**

Amplifier provides shadow environments for realistic testing without affecting production:

```bash
# Deploy to shadow environment (example - adapt to your setup)
amplifier deploy --env shadow --pr <pr_number>

# Or use your project's deployment script
./scripts/deploy-to-shadow.sh <branch_name>
```

- [ ] Deploy PR branch to shadow environment
- [ ] Test with realistic data volumes and user scenarios
- [ ] Verify integrations with external services work correctly
- [ ] Check observability (logs, metrics, traces)
- [ ] Test error handling and edge cases in realistic conditions

**If shadow environment unavailable:**

- Document alternative realistic testing approach used
- Provide clear evidence that changes work in production-like conditions
- Example alternatives: Docker compose stack, local staging environment, isolated test account

---

**Test Results Documentation Template:**

Add this section to your PR description:

```markdown
## Step 19: Outside-In Testing Results

**Test Environment**: <shadow environment URL, staging server, Docker setup, etc.>
**Interface Type**: <CLI/TUI/Web/Electron/Config>

**User Flows Tested**:

1. **Flow 1**: <description> → <result> ✅/❌
   - Commands/Actions: <specific commands or user actions>
   - Expected: <expected behavior>
   - Actual: <actual behavior>
   - Evidence: <screenshot, log output, command output>

2. **Flow 2**: <description> → <result> ✅/❌
   - Commands/Actions: <specific commands or user actions>
   - Expected: <expected behavior>
   - Actual: <actual behavior>
   - Evidence: <screenshot, log output, command output>

**Edge Cases Tested**: <unusual inputs, error conditions, etc.> → ✅/❌
**Integration Points Verified**: <external services, APIs, databases> → ✅/❌
**Observability Check**: <logs reviewed, metrics checked, traces examined> → ✅/❌
**Issues Found**: <list any issues discovered and how they were resolved>
```

---

**Why This Matters:**

- **Step 13** (Mandatory Local Testing) validates technical correctness in isolated environment
- **Step 19** (Outside-In Testing) validates real-world usability and integration
- Unit tests can't catch: deployment issues, environment-specific bugs, real user experience problems, integration failures
- Testing in production-like environment catches issues before production deployment
- User-centric testing ensures changes actually solve the problem for end users
- Creates confidence for reviewers and future maintainers

**Remember**: Outside-in means testing from the user's perspective, not from the code's perspective. Start at the interface and verify behavior matches user expectations.

### Step 20: Final Cleanup and Verification

- [ ] **CRITICAL: Provide cleanup agent with original user requirements AGAIN**
- [ ] **Always use** cleanup agent for final quality pass
- [ ] Review all changes for philosophy compliance WITHIN user constraints
- [ ] Remove any temporary artifacts or test files (unless user wanted them)
- [ ] Eliminate unnecessary complexity (that doesn't violate user requirements)
- [ ] Verify module boundaries remain clean
- [ ] Ensure zero dead code or stub implementations (unless explicitly requested)
- [ ] **FINAL CHECK: All explicit user requirements preserved**

#### PR Cleanliness Check (Final Verification)

**CRITICAL: Final scan for any temporary/debugging artifacts before marking PR ready.**

- [ ] **Full Diff Review**: Run `git diff main...HEAD` and verify all changes are intentional
  - Every changed file serves the feature's purpose
  - No leftover experimental branches or testing code
  - No accidentally committed local configuration changes

- [ ] **Comprehensive File Scan**: Check entire PR changeset for temporary patterns
  - Pattern: `test_*.py`, `temp_*.js`, `scratch_*.md`, `debug_*.log`, `*.tmp`
  - Pattern: `experiment_*.py`, `test_manual_*.sh`, `playground_*.ts`
  - Pattern: `ANALYSIS_YYYYMMDD.md`, `INVESTIGATION_*.md`, `NOTES_*.txt`
  - Remove or move to `~/.amplihack/.claude/runtime/logs/` as appropriate

- [ ] **Debugging Code Sweep**: Final search for debugging statements across all modified files
  - JavaScript/TypeScript: `console.log`, `console.debug`, `debugger;`
  - Python: `print()` for debugging (keep intentional logging), `breakpoint()`, `pdb.set_trace()`, `import pdb`
  - Rust: `dbg!()` macros used during development
  - Remove all debugging artifacts

- [ ] **Documentation Audit**: Verify only permanent documentation is included
  - Point-in-time analysis docs moved to `~/.amplihack/.claude/runtime/logs/`
  - Investigation notes not required for feature understanding removed
  - Only architectural/design docs that serve ongoing maintenance included

- [ ] **Git Hygiene Final Check**:
  - No large files without justification (check `git diff --stat`) - (Valid: test fixtures, vendored deps, binary assets)
  - `.gitignore` comprehensive for new file types
  - No sensitive data exposed (run `detect-secrets` if available)

**Why This Matters:**

- Last chance to catch cleanliness issues before marking PR ready
- Ensures professional, maintainable codebase
- Prevents embarrassing temporary artifacts in production branches
- Maintains git history integrity

- [ ] Ensure any cleanup agent changes get committed, validated by pre-commit, pushed to remote
- [ ] Add a comment to the PR about any work the Cleanup agent did

### Step 20c: Quality Audit Loop

**Added per issues #2805, #2809, #2810.**

Invoke the **quality-audit** skill to run a comprehensive, iterative quality audit on all files changed in this PR. This is the last substantive check before the PR is marked ready.

#### Loop Structure

```
Cycle 1: SEEK → VALIDATE (3 agents) → FIX → decision
Cycle 2: SEEK (deeper) → VALIDATE → FIX → decision
Cycle 3: SEEK (deepest) → VALIDATE → FIX → decision
...continues if thresholds not met, up to 6 cycles
```

**Minimum 3 cycles.** Continue past 3 if:

- Any **critical** or **high** severity findings remain, OR
- More than **3 medium** severity findings remain

Each cycle escalates depth: look with fresh eyes, dig deeper, challenge prior findings.

#### 9 Audit Categories

**Code Quality:**

- [ ] **Security**: Hardcoded secrets, missing input validation
- [ ] **Reliability**: Missing timeouts, bare except clauses
- [ ] **Dead Code**: Unused imports, unreachable branches, stale TODOs
- [ ] **Test Gaps**: Files without tests, tests without assertions
- [ ] **Doc Gaps**: Public functions without docstrings

**Anti-Degradation (#2805, #2810):**

- [ ] **Silent Fallbacks**: `except: pass`, broad catches returning defaults silently, fallback chains masking failures, `or default_value` hiding upstream errors
- [ ] **Error Swallowing**: `except` blocks with no logging/re-raise, error-to-None transforms, catch-all discarding exceptions, functions returning True/False instead of raising

**Structural (#2809):**

- [ ] **Structural Issues**: Files >500 LOC, functions >50 lines, nesting >4 levels, >5 parameters, circular imports

**Hardcoded Limits (#2822):**

- [ ] **Hardcoded Limits**: Non-configurable numeric caps (`[:N]`, `max_X = N`, `if len() > N`), silent truncation without logging. Severity: HIGH = data loss, MEDIUM = incomplete data, LOW = display-only.

**Documentation Audit:**

- [ ] **Point-in-time removal**: Remove ALL temporal content — status updates, session notes, "as of today", "we just finished". Docs must read correctly years after being written.
- [ ] **Professional tone**: No pirate speak ("fer"/"ye"/"yer"/"arr"/"matey"), no chatbot artifacts ("Sure!", "Great question!"), no informal language in shipped documentation.
- [ ] **Quality review**: Organization, comprehensiveness, clarity, navigation, correctness vs actual code behavior.

#### Multi-Agent Validation

Every finding is independently validated by **3 separate agents**:

1. **Analyzer** — evaluates on technical merits
2. **Reviewer** — skeptically verifies by reading actual code
3. **Architect** — adversarial review, looks for reasons finding is wrong

A finding is **confirmed** only if ≥2 of 3 agents agree. This eliminates false positives.

#### Fix Process

All confirmed findings are fixed using the full **DEFAULT_WORKFLOW** approach:

1. Understand the finding and its context
2. Write or update tests that verify the fix
3. Implement the minimal fix
4. Verify the fix doesn't break existing tests

#### Completion Criteria

- [ ] Minimum 3 audit cycles completed
- [ ] Final cycle: 0 critical/high findings, ≤3 medium findings
- [ ] All confirmed findings fixed with tests
- [ ] Documentation passes tone and durability checks
- [ ] Results documented: "QUALITY AUDIT: CLEAN" or remaining findings listed

#### Self-Improvement Review

After all audit cycles complete, step back and ask:

> **"How else would you improve this code?"**

- [ ] Look for systemic issues the audit missed
- [ ] Identify architectural improvements that prevent recurring findings
- [ ] Check if fixes introduced new issues
- [ ] Find cross-cutting concerns that should be standardized
- [ ] Fix any **CRITICAL** improvements found immediately
- [ ] Document **ADVISORY** improvements as follow-up issues

**Cannot proceed to Step 21 without completing the quality audit loop.**

### Step 21: Convert PR to Ready for Review

**For GitHub**:

```bash
gh pr ready 2>&1 | cat
```

**For Azure DevOps**:

```bash
# Azure DevOps: Mark PR as ready by setting auto-complete or removing draft status
az repos pr update \
  --id <pr_number> \
  --draft false
```

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

**Why This Step Matters:**

- Signals transition from "work in progress" to "ready to merge"
- Indicates you've completed all quality checks
- Requests final approval from reviewers
- Makes PR eligible for merge queue

### Step 22: Ensure PR is Mergeable

**Check CI status**:

**For GitHub**:

```bash
gh pr checks
# Or for specific PR:
gh pr checks <pr_number>
```

**For Azure DevOps**:

```bash
# Check pipeline runs for current branch
az pipelines runs list --branch $(git branch --show-current) --top 1

# Or check PR build status
az repos pr show --id <pr_number> --query "mergeStatus"
```

- [ ] Verify all CI checks passing
- [ ] **Always use** ci-diagnostic-workflow agent if CI fails
- [ ] **💡 TIP**: When investigating CI failures, use [parallel agent investigation](~/.amplihack/.claude/CLAUDE.md#parallel-agent-investigation-strategy) to explore logs and code simultaneously
- [ ] Resolve any merge conflicts
- [ ] Verify all review comments addressed, including check for any that showed up after marking the PR as ready
- [ ] Confirm PR is approved
- [ ] Notify that PR is ready to merge

## Customization

To customize this workflow:

1. Edit this file to modify, add, or remove steps
2. Save your changes
3. The updated workflow will be used for future tasks
