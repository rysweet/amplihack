---
name: investigation-workflow
version: 1.0.0
description: Execute INVESTIGATION_WORKFLOW directly for research and understanding tasks without auto-detection
triggers:
  - "run investigation workflow"
  - "execute investigation"
  - "research workflow"
invokes:
  - type: workflow
    path: .claude/workflow/INVESTIGATION_WORKFLOW.md
---

# Investigation Workflow Command

Directly executes the INVESTIGATION_WORKFLOW.md for research and understanding tasks without task type auto-detection.

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/amplihack:investigation-workflow <INVESTIGATION_QUESTION>`

## Purpose

Execute the 6-phase investigation workflow explicitly for understanding existing systems, codebases, or architectures. Use this when you need deep knowledge excavation without implementation.

## When to Use This Command

Use this command instead of `/ultrathink` when:

- Task is clearly investigation-focused (investigate, explain, understand, how does, why does)
- You need to understand existing code/systems
- You want to document findings before making changes
- You need knowledge capture without implementation
- You're doing research or exploratory analysis

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Inform user** which workflow is being used:
   ```
   Executing INVESTIGATION_WORKFLOW.md (6-phase research workflow)
   ```

2. **Read the workflow file** using the Read tool:
   - `.claude/workflow/INVESTIGATION_WORKFLOW.md`

3. **Create a comprehensive todo list** using TodoWrite with all 6 phases
   - Format: `Phase N: [Phase Name] - [Specific Action]`
   - Example: `Phase 1: Scope Definition - Use prompt-writer agent to clarify investigation questions`

4. **Execute each phase systematically**, marking todos as in_progress and completed

5. **Use the specified agents** for each phase (marked with "**Use**" or "**Deploy**")

6. **Track decisions** by creating `.claude/runtime/logs/<session_timestamp>/DECISIONS.md`

7. **Mandatory: Update DISCOVERIES.md** at Phase 6 (Knowledge Capture)

## The 6-Phase Investigation Workflow

1. **Scope Definition** - Define investigation boundaries and success criteria
   - prompt-writer, ambiguity agents
   - Output: List of questions to answer, scope boundaries

2. **Exploration Strategy** - Plan agent deployment and investigation roadmap
   - architect, patterns agents
   - Output: Exploration roadmap, agent deployment plan

3. **Parallel Deep Dives** - Deploy multiple agents simultaneously for efficient exploration
   - PARALLEL EXECUTION: [analyzer, patterns, security, optimizer, etc.]
   - Output: Findings from all parallel explorations

4. **Verification & Testing** - Test and validate understanding through practical application
   - Create hypotheses, run tests, verify understanding
   - Output: Verification report with test results

5. **Synthesis** - Compile findings into coherent explanation
   - reviewer, patterns agents
   - Output: Executive summary, detailed explanation, visual aids

6. **Knowledge Capture** - Create durable documentation
   - Update DISCOVERIES.md, PATTERNS.md
   - Output: Updated documentation, investigation session log

See `.claude/workflow/INVESTIGATION_WORKFLOW.md` for complete phase details.

## Critical: Parallel Execution in Phase 3

**Phase 3 (Parallel Deep Dives) is the core of this workflow and MUST use parallel agent execution.**

Example parallel agent deployments:

```
Investigation: "How does the reflection system work?"
→ [analyzer(.claude/tools/amplihack/hooks/), patterns(reflection), integration(logging)]

Investigation: "Why is CI failing?"
→ [analyzer(ci-config), patterns(ci-failures), integration(github-actions)]

Investigation: "Understand authentication flow"
→ [analyzer(auth-module), security(auth), patterns(auth), integration(external-auth)]
```

## Task Management

Always use TodoWrite to:

- Track all 6 investigation phases
- Mark progress (pending → in_progress → completed)
- Coordinate parallel agent execution in Phase 3
- Document findings at each phase

## Example Flow

```
User: "/amplihack:investigation-workflow investigate how the authentication system works"

1. Inform: "Executing INVESTIGATION_WORKFLOW.md (6-phase research workflow)"
2. Read workflow: `.claude/workflow/INVESTIGATION_WORKFLOW.md`
3. Create TodoWrite list with all 6 phases
4. Execute Phase 1: Use prompt-writer to clarify investigation scope
   → Define questions: "How is auth implemented?", "What libraries are used?", etc.
5. Execute Phase 2: Use architect agent to plan exploration strategy
   → Plan to explore: auth module, config files, test files, API endpoints
6. Execute Phase 3: Deploy parallel agents for deep dives
   → [analyzer(src/auth), patterns(authentication), security(auth), integration(api)]
7. Execute Phase 4: Verify understanding through practical tests
   → Trace actual auth flow in code, test with sample tokens
8. Execute Phase 5: Use reviewer agent to synthesize findings
   → Create explanation, diagrams, key insights
9. Execute Phase 6: MANDATORY update DISCOVERIES.md
   → Document auth system architecture, patterns used, security considerations
```

## Transitioning to Development Workflow

After investigation completes, if implementation is needed:

```
Option 1: Resume DEFAULT_WORKFLOW at Step 4
→ Use investigation findings to inform design

Option 2: Use /ultrathink with hybrid task
→ UltraThink will run investigation then transition to development

Option 3: Use /amplihack:default-workflow
→ Manually run development workflow with investigation knowledge
```

## Efficiency Targets

This workflow targets 30-40% reduction in message count compared to ad-hoc investigation:

| Ad-Hoc Approach         | Investigation Workflow    |
| ----------------------- | ------------------------- |
| 70-90 messages          | 40-60 messages            |
| Frequent backtracking   | Planned exploration       |
| Redundant investigation | Parallel deep dives       |
| Unclear scope           | Explicit scope definition |
| Lost knowledge          | Documented insights       |

## Comparison to /ultrathink

| Feature                   | /ultrathink                        | /amplihack:investigation-workflow |
| ------------------------- | ---------------------------------- | --------------------------------- |
| **Task Detection**        | Auto-detects (investigation vs dev)| Skip detection, use INVESTIGATION |
| **Workflow Selection**    | Automatic (investigation or dev)   | Always INVESTIGATION_WORKFLOW     |
| **Development Support**   | Yes (switches to DEFAULT)          | No (investigation only)           |
| **Use When**              | Task type unclear                  | Task clearly investigation        |

## Phase Mapping to DEFAULT_WORKFLOW

For user familiarity, investigation phases map to development steps:

| Investigation Phase           | DEFAULT_WORKFLOW Equivalent        | Purpose                              |
| ----------------------------- | ---------------------------------- | ------------------------------------ |
| Phase 1: Scope Definition     | Step 1: Requirements Clarification | Define what success looks like       |
| Phase 2: Exploration Strategy | Step 4: Research and Design        | Plan the approach                    |
| Phase 3: Parallel Deep Dives  | Step 5: Implementation             | Execute the plan (explore vs. build) |
| Phase 4: Verification         | Steps 7-8: Testing                 | Validate results                     |
| Phase 5: Synthesis            | Step 11: Review                    | Ensure quality and completeness      |
| Phase 6: Knowledge Capture    | Step 15: Cleanup                   | Make results durable                 |

## Mandatory Knowledge Capture

**CRITICAL**: Phase 6 MUST update `.claude/context/DISCOVERIES.md` with investigation findings.

This ensures:

- Knowledge persists across sessions
- Future investigations can reference findings
- Patterns are captured for reuse
- No duplicate investigation work

## Remember

- This command skips task type detection and goes directly to investigation workflow
- Use `/ultrathink` if you need investigation followed by implementation
- Use `/amplihack:default-workflow` if you only need implementation, not investigation
- Phase 3 MUST use parallel agent execution for efficiency
- Mandatory DISCOVERIES.md update at Phase 6

**When in doubt**: Use `/ultrathink` for automatic workflow detection. Use this command only when you know you want investigation workflow explicitly.
