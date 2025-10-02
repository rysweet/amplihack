# UltraThink Command

**Purpose**: Orchestrate the complete 14-step workflow from `.claude/workflow/DEFAULT_WORKFLOW.md` with multi-agent coordination and parallel execution.

## What This Command Does

UltraThink is the primary orchestrator for non-trivial coding tasks. It:

1. **Reads the authoritative workflow** from `DEFAULT_WORKFLOW.md`
2. **Understands the task** through requirement clarification
3. **Orchestrates specialized agents** at each workflow step
4. **Executes in parallel** whenever possible
5. **Tracks progress** with TodoWrite throughout
6. **Adapts automatically** when you customize the workflow

## Execution Strategy

### Requirement Gathering

First, determine what the user wants to accomplish:

**If task is provided with /ultrathink:** Use the provided task description

**If no task provided:** Ask the user:

> "What task would you like me to help you accomplish? Please describe what you need, including any specific requirements or constraints."

### Workflow Orchestration

Execute the 14-step workflow from `DEFAULT_WORKFLOW.md`:

#### Step 1: Rewrite and Clarify Requirements (PARALLEL)

Deploy agents in parallel for requirement analysis:

- **prompt-writer**: Clarify and structure requirements
- **analyzer**: Understand existing codebase context
- **ambiguity**: Identify and resolve unclear aspects

**CRITICAL**: Capture explicit user requirements that CANNOT be optimized away.

#### Step 2: Create GitHub Issue

- Use `gh issue create` with clarified requirements
- Include success criteria and constraints

#### Step 3: Setup Worktree and Branch

- Create git worktree for isolated development
- Create branch: `feat/issue-{number}-{description}`
- Push and switch to worktree

#### Step 4: Research and Design with TDD (PARALLEL)

Deploy design agents in parallel:

- **architect**: System architecture and module boundaries
- **api-designer**: API contracts (if applicable)
- **database**: Data model design (if applicable)
- **tester**: Write failing tests (TDD approach)
- **security**: Security requirements and threat analysis

#### Step 5: Implement the Solution

- **builder**: Implement from specifications
- **integration**: Handle external service connections
- Make tests pass iteratively

#### Step 6: Refactor and Simplify

**CRITICAL**: Pass original user requirements to these agents:

- **cleanup**: Ruthless simplification WITHIN user constraints
- **optimizer**: Performance improvements
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

#### Step 10: Review the PR (PARALLEL)

Deploy review agents in parallel:

- **reviewer**: Comprehensive code review
- **security**: Security vulnerability assessment
- **patterns**: Pattern compliance check

#### Step 11: Implement Review Feedback

- **builder**: Implement changes from feedback
- Address all review comments
- Push updates

#### Step 12: Philosophy Compliance Check (PARALLEL)

- **reviewer**: Final philosophy validation
- **patterns**: Pattern verification
- Confirm zero-BS implementation

#### Step 13: Ensure PR is Mergeable

- Check CI status
- **ci-diagnostic-workflow**: Use if CI fails
- Resolve conflicts
- Verify approval

#### Step 14: Final Cleanup and Verification

**CRITICAL**: Pass original user requirements AGAIN:

- **cleanup**: Final quality pass WITHIN user constraints
- Remove temporary artifacts (unless user wanted them)
- **FINAL CHECK**: All explicit requirements preserved

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

Use TodoWrite to track the 14 workflow steps:

```
1. Clarify requirements with multi-agent analysis
2. Create GitHub issue
3. Setup worktree and branch
4. Design solution with TDD approach
5. Implement solution
6. Refactor and simplify
7. Run tests and pre-commit
8. Commit and push
9. Open pull request
10. Review PR comprehensively
11. Implement review feedback
12. Philosophy compliance check
13. Ensure PR is mergeable
14. Final cleanup and verification
```

Mark each step as `in_progress` before starting, `completed` when finished.

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

- All 14 workflow steps completed
- PR is mergeable (CI passing, approved)
- All explicit user requirements met
- Philosophy compliance verified
- Zero dead code or stubs remain

## Customization

To modify this workflow:

1. Edit `.claude/workflow/DEFAULT_WORKFLOW.md`
2. Save changes
3. UltraThink will use updated workflow automatically

---

**Start by asking for the task if not provided, then execute the workflow with aggressive agent delegation and parallel execution.**
