---
name: default-workflow
version: 1.0.0
description: Execute DEFAULT_WORKFLOW directly for development tasks without auto-detection
triggers:
  - "run default workflow"
  - "execute standard workflow"
  - "follow development workflow"
invokes:
  - type: workflow
    path: .claude/workflow/DEFAULT_WORKFLOW.md
---

# Default Workflow Command

Directly executes the DEFAULT_WORKFLOW.md for development tasks (features, bug fixes, refactoring) without task type auto-detection.

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/amplihack:default-workflow <TASK_DESCRIPTION>`

## Purpose

Execute the standard 15-step development workflow explicitly, bypassing ultrathink's task type detection. Use this when you know your task requires the full development lifecycle: requirements → design → implementation → testing → PR.

## When to Use This Command

Use this command instead of `/ultrathink` when:

- Task is clearly development-focused (implement, build, create, fix)
- You want to skip investigation and go straight to implementation
- You want explicit control over workflow selection
- Task requires the full development lifecycle (branch → code → test → PR)

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Inform user** which workflow is being used:

   ```
   Executing DEFAULT_WORKFLOW.md (15-step development workflow)
   ```

2. **Read the workflow file** using the Read tool:
   - `.claude/workflow/DEFAULT_WORKFLOW.md`

3. **Create a comprehensive todo list** using TodoWrite with all 15 steps
   - Format: `Step N: [Step Name] - [Specific Action]`
   - Example: `Step 1: Rewrite and Clarify Requirements - Use prompt-writer agent`

4. **Execute each step systematically**, marking todos as in_progress and completed

5. **Use the specified agents** for each step (marked with "**Use**" or "**Always use**")

6. **Track decisions** by creating `.claude/runtime/logs/<session_timestamp>/DECISIONS.md`

7. **Mandatory: End with cleanup agent** at Step 15

## The 15-Step Development Workflow

1. **Rewrite and Clarify Requirements** - prompt-writer, analyzer agents
2. **Create GitHub Issue** - Document requirements
3. **Setup Worktree and Branch** - worktree-manager agent
4. **Research and Design with TDD** - architect, api-designer, database, tester agents
5. **Implement the Solution** - builder, integration agents
6. **Refactor and Simplify** - cleanup, optimizer agents
7. **Run Tests and Pre-commit Hooks** - pre-commit-diagnostic agent
8. **Mandatory Local Testing** - Test in realistic scenarios
9. **Commit and Push** - Stage, commit, push
10. **Open Pull Request** - Create PR with gh
11. **Review the PR** - reviewer, security agents
12. **Implement Review Feedback** - builder agent
13. **Philosophy Compliance Check** - reviewer, patterns agents
14. **Ensure PR is Mergeable** - ci-diagnostic-workflow agent
15. **Final Cleanup and Verification** - cleanup agent

See `.claude/workflow/DEFAULT_WORKFLOW.md` for complete step details.

## Agent Orchestration

### Sequential Execution (Default for Development)

Development workflows are primarily sequential due to dependencies:

```
Step 1: Requirements → Step 2: Issue → Step 3: Branch → Step 4: Design → Step 5: Implement
```

### Parallel Execution (When Applicable)

Use parallel agents within steps when gathering independent information:

```
Step 4: [architect, api-designer, database, tester] for design
Step 11: [reviewer, security] for PR review
```

## Task Management

Always use TodoWrite to:

- Track all 15 workflow steps
- Mark progress (pending → in_progress → completed)
- Coordinate agent execution
- Document decisions at each step

## Example Flow

```
User: "/amplihack:default-workflow implement JWT authentication"

1. Inform: "Executing DEFAULT_WORKFLOW.md (15-step development workflow)"
2. Read workflow: `.claude/workflow/DEFAULT_WORKFLOW.md`
3. Create TodoWrite list with all 15 steps
4. Execute Step 1: Use prompt-writer to clarify JWT requirements
5. Execute Step 2: Create GitHub issue with requirements
6. Execute Step 3: Setup worktree and branch (feat/issue-123-jwt-auth)
7. Execute Step 4: Use architect agent to design JWT implementation
8. Execute Step 5: Use builder agent to implement JWT authentication
9. Execute Step 6: Use cleanup agent to simplify and refactor
10. Execute Step 7: Run pre-commit hooks and tests
11. Execute Step 8: Test JWT implementation locally with real tokens
12. Execute Step 9: Commit and push changes
13. Execute Step 10: Create PR with gh
14. Execute Step 11: Use reviewer agent to review PR
15. Execute Step 12: Implement any review feedback
16. Execute Step 13: Philosophy compliance check
17. Execute Step 14: Ensure CI passes and PR is mergeable
18. Execute Step 15: MANDATORY cleanup agent invocation
```

## Mandatory Cleanup Phase

**CRITICAL**: Step 15 MUST invoke cleanup agent before reporting task completion.

The cleanup agent:

- Reviews git status and file changes
- Removes temporary artifacts and planning documents
- Ensures philosophy compliance (ruthless simplicity)
- Provides final report on codebase state
- Guards against technical debt accumulation

## Comparison to /ultrathink

| Feature                   | /ultrathink                         | /amplihack:default-workflow |
| ------------------------- | ----------------------------------- | --------------------------- |
| **Task Detection**        | Auto-detects (investigation vs dev) | Skip detection, use DEFAULT |
| **Workflow Selection**    | Automatic (investigation or dev)    | Always DEFAULT_WORKFLOW     |
| **Investigation Support** | Yes (switches to INVESTIGATION)     | No (development only)       |
| **Use When**              | Task type unclear                   | Task clearly development    |

## Remember

- This command skips task type detection and goes directly to development workflow
- Use `/ultrathink` if you need investigation before development
- Use `/amplihack:investigation-workflow` if you only need understanding, not implementation
- Always complete all 15 steps - no shortcuts unless user explicitly requests
- Mandatory cleanup agent at Step 15

**When in doubt**: Use `/ultrathink` for automatic workflow detection. Use this command only when you know you want the full development workflow explicitly.
