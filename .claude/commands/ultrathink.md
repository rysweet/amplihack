# UltraThink Command

**Purpose**: Orchestrate the complete workflow from `.claude/workflow/` with multi-agent coordination and parallel execution.

## What This Command Does

UltraThink is the primary orchestrator for non-trivial coding tasks. It:

1. **Loads the selected workflow** from USER_PREFERENCES.md (defaults to DEFAULT_WORKFLOW.md)
2. **Reads the authoritative workflow** definition and parses agent assignments
3. **Understands the task** through requirement clarification
4. **Orchestrates specialized agents** at each workflow step according to workflow
5. **Executes in parallel** whenever possible
6. **Tracks progress** with TodoWrite throughout
7. **Adapts automatically** when you customize workflows or switch between them

## Execution Strategy

### Step 0: Load Workflow Configuration (MANDATORY FIRST STEP)

**Before doing anything else, load the workflow:**

1. Use the Read tool to read `.claude/context/USER_PREFERENCES.md`
2. Find the "**Selected Workflow**:" line in the "Workflow Configuration" section
3. Extract the workflow name (e.g., "DEFAULT_WORKFLOW", "CONSENSUS_WORKFLOW")
4. Construct workflow file path: `.claude/workflow/{workflow_name}.md`
5. Use the Read tool to read the workflow file
6. If workflow file not found or error reading:
   - Log warning: "Selected workflow '{workflow_name}' not found"
   - Fallback: Use `.claude/workflow/DEFAULT_WORKFLOW.md`
   - Notify user: "Using DEFAULT_WORKFLOW as fallback"
7. Parse workflow to extract:
   - Total number of steps (count "### Step" headers)
   - Agent assignments at each step (lines with "**Use**", "**Deploy**", "**Always use**")
   - Consensus triggers (lines with "CONSENSUS TRIGGER", "ALWAYS CONSENSUS", "Multi-Agent Debate", etc.)
   - Success criteria (from final section)

**Workflow Loading Output:**

```
Loaded workflow: {workflow_name}
Steps: {number}
Features detected:
- Multi-agent debate triggers: {count}
- N-Version programming triggers: {count}
- Expert panel reviews: {count}
```

### Requirement Gathering

After workflow is loaded, determine what the user wants to accomplish:

**If task is provided with /ultrathink:** Use the provided task description

**If no task provided:** Ask the user:

> "What task would you like me to help you accomplish? Please describe what you need, including any specific requirements or constraints."

### Workflow Orchestration

Execute the workflow steps loaded from the selected workflow file:

#### Step 1: Rewrite and Clarify Requirements

**Read from workflow**: Extract agent assignments and consensus triggers from Step 1

**Standard agent deployment** (always execute):

- **prompt-writer**: Clarify and structure requirements
- **analyzer**: Understand existing codebase context
- **ambiguity**: Identify and resolve unclear aspects

**If workflow specifies Multi-Agent Debate trigger**:

- Check if requirements are ambiguous or complex
- If YES: Deploy Multi-Agent Debate as specified in workflow
  - Number of agents based on workflow (or USER_PREFERENCES consensus_depth)
  - Number of rounds based on workflow
  - Follow debate protocol from workflow

**CRITICAL**: Capture explicit user requirements that CANNOT be optimized away.

#### Step 2: Create GitHub Issue

- Use `gh issue create` with clarified requirements
- Include success criteria and constraints

#### Step 3: Setup Worktree and Branch

- Create git worktree for isolated development
- Create branch: `feat/issue-{number}-{description}`
- Push and switch to worktree

#### Step 4: Research and Design with TDD

**Read from workflow**: Extract agent assignments and consensus mechanisms from Step 4

**Standard agent deployment** (from workflow specification):

- **architect**: System architecture and module boundaries
- **api-designer**: API contracts (if applicable)
- **database**: Data model design (if applicable)
- **tester**: Write failing tests (TDD approach)
- **security**: Security requirements and threat analysis

**If workflow specifies ALWAYS CONSENSUS or Multi-Agent Debate**:

- Deploy Multi-Agent Debate for architecture design
- Follow debate rounds specified in workflow
- Adjust agent count based on USER_PREFERENCES consensus_depth:
  - quick: 2-3 agents, 2 rounds
  - balanced: 3-4 agents, 3 rounds
  - comprehensive: 5+ agents, 4+ rounds
- Synthesize consensus design specification

#### Step 5: Implement the Solution

**Read from workflow**: Extract agent assignments and N-Version triggers from Step 5

**Standard implementation** (always execute):

- **builder**: Implement from specifications
- **integration**: Handle external service connections
- Make tests pass iteratively

**If workflow specifies N-Version Programming trigger**:

- Check if code is critical (security, financial, safety, data integrity)
- If YES: Deploy N-Version Programming as specified in workflow
  - Number of independent implementations (usually 2-3)
  - Cross-validation protocol
  - Synthesis and consensus vote process

#### Step 6: Refactor and Simplify

**Read from workflow**: Extract agent assignments and Expert Panel triggers from Step 6

**CRITICAL**: Pass original user requirements to these agents:

- **cleanup**: Ruthless simplification WITHIN user constraints
- **optimizer**: Performance improvements

**If workflow specifies Expert Panel Review**:

- Deploy expert panel as specified in workflow
- Typically: cleanup, optimizer, reviewer, patterns agents
- Independent reviews followed by consensus building
- Validate all explicit requirements preserved

**VALIDATE**: All explicit requirements preserved

#### Step 7: Run Tests and Pre-commit Hooks

- Run all tests
- Execute `pre-commit run --all-files`
- **pre-commit-diagnostic**: Use if hooks fail
- Iterate until all checks pass

#### Step 8: Commit and Push

- Stage changes
- Write detailed commit message with issue reference
- Push to remote

#### Step 9: Open Pull Request

- Create PR with `gh pr create`
- Link issue, add description, test plan
- Request reviewers

#### Step 10 or 11: Review the PR

**Read from workflow**: Extract agent assignments and Expert Panel requirements

**Standard review** (parallel execution):

- **reviewer**: Comprehensive code review
- **security**: Security vulnerability assessment
- **patterns**: Pattern compliance check

**If workflow specifies ALWAYS EXPERT PANEL or Expert Panel Review**:

- Deploy full expert panel for comprehensive PR review
- Typically: reviewer, security, optimizer, patterns, tester agents
- Independent parallel reviews
- Consolidate findings into unified review
- Consensus on required vs. optional changes
- Post consolidated review to PR

#### Step 11: Implement Review Feedback

- **builder**: Implement changes from feedback
- Address all review comments
- Push updates

#### Step 12 or 13: Philosophy Compliance Check

**Read from workflow**: Extract agent assignments and Expert Panel requirements

**Standard compliance check**:

- **reviewer**: Final philosophy validation
- **patterns**: Pattern verification
- Confirm zero-BS implementation

**If workflow specifies Expert Panel for philosophy compliance**:

- Deploy compliance panel as specified
- Typically: reviewer, patterns, cleanup agents
- Unanimous approval required for philosophy compliance
- Document any justified complexity (from user requirements)

#### Step 13: Ensure PR is Mergeable

- Check CI status
- **ci-diagnostic-workflow**: Use if CI fails
- Resolve conflicts
- Verify approval

#### Step 14 or 15: Final Cleanup and Verification

**Read from workflow**: Extract agent assignments and final Expert Panel requirements

**CRITICAL**: Pass original user requirements AGAIN:

- **cleanup**: Final quality pass WITHIN user constraints
- Remove temporary artifacts (unless user wanted them)

**If workflow specifies Final Expert Panel**:

- Deploy final quality panel
- Typically: cleanup, reviewer, patterns agents
- Unanimous approval required
- All agents must confirm requirements preserved

**FINAL CHECK**: All explicit requirements preserved

## Parallel Execution Rules

**ALWAYS execute in parallel when:**

- Multiple perspectives needed (design, security, testing)
- Independent analysis tasks (multiple modules/components)
- Review from different angles (code quality, security, patterns)

**Execute sequentially only when:**

- Hard dependencies (specification → implementation → review)
- State mutations (git operations with dependencies)
- Progressive context building

## Task Management

Use TodoWrite to track workflow steps dynamically:

1. After loading workflow, count total steps from workflow file
2. Extract step names from workflow "### Step N: [Name]" headers
3. Create TodoWrite list with all steps from the loaded workflow
4. Mark each step as `in_progress` before starting, `completed` when finished
5. Adapt to workflow length (may be 8, 15, 20+ steps depending on workflow)

**Example for DEFAULT_WORKFLOW (15 steps)**:

```
1. Clarify requirements with multi-agent analysis
2. Create GitHub issue
3. Setup worktree and branch
4. Design solution with TDD approach
5. Implement solution
6. Refactor and simplify
7. Run tests and pre-commit
8. Mandatory local testing
9. Commit and push
10. Open pull request
11. Review PR comprehensively
12. Implement review feedback
13. Philosophy compliance check
14. Ensure PR is mergeable
15. Final cleanup and verification
```

**Example for CONSENSUS_WORKFLOW (15 steps with consensus annotations)**:

```
1. Clarify requirements (Multi-Agent Debate if ambiguous)
2. Create GitHub issue
3. Setup worktree and branch
4. Design with TDD (ALWAYS Multi-Agent Debate)
5. Implement solution (N-Version for critical code)
6. Refactor and simplify (Expert Panel review)
7. Run tests and pre-commit
8. Mandatory local testing
9. Commit and push
10. Open pull request
11. Review PR (ALWAYS Expert Panel)
12. Implement review feedback
13. Philosophy compliance (Expert Panel)
14. Ensure PR is mergeable
15. Final cleanup (Expert Panel)
```

## Priority Hierarchy (MANDATORY)

1. **EXPLICIT USER REQUIREMENTS** (HIGHEST - NEVER OVERRIDE)
2. **USER_PREFERENCES.md** (MANDATORY - MUST FOLLOW)
3. **PROJECT PHILOSOPHY** (Strong guidance)
4. **DEFAULT BEHAVIORS** (LOWEST - Override when needed)

When user says "ALL files", "include everything", or provides specific requirements in quotes, these CANNOT be optimized away by simplification agents.

## Context Passing

Every agent invoked must receive:

- Original user requirements (explicit constraints)
- Current workflow step
- Relevant preferences from USER_PREFERENCES.md
- Dependencies from previous steps

## Success Criteria

UltraThink succeeds when:

- All workflow steps completed (count varies by workflow)
- PR is mergeable (CI passing, approved)
- All explicit user requirements met
- Philosophy compliance verified
- Zero dead code or stubs remain
- Workflow-specific success criteria met (e.g., consensus achieved if using CONSENSUS_WORKFLOW)

## Workflow Management

### Viewing Current Workflow

To see which workflow is active:

```bash
/amplihack:customize show
```

Look for "**Selected Workflow**:" in the output.

### Switching Workflows

To change workflows:

```bash
# List available workflows
/amplihack:customize list-workflows

# Switch to a different workflow
/amplihack:customize set-workflow CONSENSUS_WORKFLOW

# View workflow details
/amplihack:customize show-workflow CONSENSUS_WORKFLOW
```

### Workflow Selection Guide

**Use DEFAULT_WORKFLOW for**:

- Standard features and bug fixes
- Day-to-day development work
- When speed matters
- Well-understood requirements

**Use CONSENSUS_WORKFLOW for**:

- Ambiguous or complex requirements
- Architecturally significant changes
- Mission-critical code
- Security-sensitive implementations
- Public APIs with long-term commitments

### Creating Custom Workflows

1. Copy template: `cp .claude/workflow/templates/WORKFLOW_TEMPLATE.md .claude/workflow/MY_WORKFLOW.md`
2. Customize steps, agent assignments, and success criteria
3. Switch to it: `/amplihack:customize set-workflow MY_WORKFLOW`
4. Test with a simple task
5. Iterate and refine

## Customization

### Modifying Existing Workflows

1. Edit the workflow file directly in `.claude/workflow/`
2. Save changes
3. UltraThink will use updated workflow on next invocation
4. No need to reload or restart

### Workflow Features

UltraThink automatically adapts to workflow features:

- **Multi-Agent Debate**: Detected from "Multi-Agent Debate" keywords
- **N-Version Programming**: Detected from "N-Version" keywords
- **Expert Panel**: Detected from "Expert Panel" keywords
- **Parallel execution**: Detected from "PARALLEL" or "Deploy ... in parallel"
- **Conditional logic**: Detected from "IF ... →" patterns

## Troubleshooting

### Workflow Not Loading

**Problem**: UltraThink uses DEFAULT_WORKFLOW even though different workflow selected

**Solution**: Check workflow configuration:

```bash
/amplihack:customize show
```

Ensure "**Selected Workflow**:" shows correct workflow name (without .md extension)

### Workflow File Not Found

**Problem**: Selected workflow file doesn't exist

**Solution**: UltraThink will automatically fallback to DEFAULT_WORKFLOW and notify you. Either:

- Create the missing workflow file
- Switch back to existing workflow: `/amplihack:customize set-workflow DEFAULT_WORKFLOW`

### Consensus Mechanisms Not Triggering

**Problem**: Using CONSENSUS_WORKFLOW but consensus mechanisms aren't activating

**Solution**: Check that:

- Workflow file has proper trigger keywords (ALWAYS CONSENSUS, Multi-Agent Debate, etc.)
- USER_PREFERENCES.md consensus_depth is set (defaults to "balanced")
- Conditions for triggers are met (e.g., "IF ambiguous" requires actual ambiguity)

---

**Start by loading the workflow configuration, then asking for the task if not provided, then execute the workflow with aggressive agent delegation and parallel execution.**
