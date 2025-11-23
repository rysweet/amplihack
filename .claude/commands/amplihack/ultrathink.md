---
name: ultrathink
version: 1.0.0
description: Deep analysis mode with multi-agent orchestration
triggers:
  - "Complex multi-step task"
  - "Need deep analysis"
  - "Orchestrate workflow"
  - "Break down and solve"
invokes:
  - type: workflow
    path: .claude/workflow/DEFAULT_WORKFLOW.md
  - type: workflow
    path: .claude/workflow/INVESTIGATION_WORKFLOW.md
---

# Ultra-Think Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/ultrathink <TASK_DESCRIPTION>`

## Purpose

Deep analysis mode for complex tasks. Invokes workflow skills (default-workflow or investigation-workflow) based on task type, with automatic fallback to markdown workflows if skills are not yet available.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **First, detect task type** - Check if task is investigation or development
   - **Investigation keywords**: investigate, explain, understand, how does, why does, analyze, research, explore, examine, study
   - **Development keywords**: implement, build, create, add feature, fix, refactor, deploy
   - **If both types detected**: Use hybrid workflow (investigation first, then development)
   - If only investigation keywords found: Use INVESTIGATION_WORKFLOW.md (6 phases)
   - If only development keywords found: Use DEFAULT_WORKFLOW.md (15 steps)
2. **Invoke the appropriate workflow skill** using the Skill tool:
   - Investigation: `Skill(skill="investigation-workflow")`
   - Development: `Skill(skill="default-workflow")`
   - **FALLBACK**: If skill invocation fails (skill not found), fall back to reading markdown workflows:
     - Investigation: `.claude/workflow/INVESTIGATION_WORKFLOW.md`
     - Development: `.claude/workflow/DEFAULT_WORKFLOW.md`
3. **Create a comprehensive todo list** using TodoWrite that includes all workflow steps/phases
4. **Execute each step systematically**, marking todos as in_progress and completed
5. **Use the specified agents** for each step (marked with "**Use**" or "**Always use**")
6. **MANDATORY: Enforce Steps 11-12** (Code Review) for all development workflows:
   - After Step 10, MUST invoke reviewer agent
   - After Step 11, MUST implement feedback (Step 12)
   - Do NOT mark workflow complete without Steps 11-12
7. **Track decisions** by creating `.claude/runtime/logs/<session_timestamp>/DECISIONS.md`
8. **End with cleanup agent** (development) or knowledge capture (investigation)

## PROMPT-BASED WORKFLOW EXECUTION

Execute this exact sequence for the task: `{TASK_DESCRIPTION}`

### Step-by-Step Execution:

1. **Initialize**:
   - Detect task type (investigation vs. development)
   - Select appropriate workflow:
     - Investigation: investigation-workflow skill (6 phases)
     - Development: default-workflow skill (15 steps)
   - Inform user which workflow is being used
   - Try to invoke the selected workflow skill using Skill tool
   - **FALLBACK**: If skill not found, read the markdown workflow file using Read tool:
     - Investigation: `.claude/workflow/INVESTIGATION_WORKFLOW.md`
     - Development: `.claude/workflow/DEFAULT_WORKFLOW.md`
   - Create TodoWrite list with all workflow steps/phases
   - Create session directory for decision logging

2. **For Each Workflow Step**:
   - Mark step as in_progress in TodoWrite
   - Read the step requirements from workflow
   - Invoke specified agents via Task tool
   - Log decisions made
   - Mark step as completed
   - **MANDATORY ENFORCEMENT**: After Step 10 completion, MUST proceed to Steps 11-12 (Code Review)
   - **Steps 11-12 are NOT optional** - No workflow can be marked complete without code review

3. **Agent Invocation Pattern**:

   ```
   For step requiring "**Use** architect agent":
   → Invoke Task(subagent_type="architect", prompt="[step requirements + task context]")

   For step requiring multiple agents:
   → Invoke multiple Task calls in parallel
   ```

4. **Decision Logging**:
   After each major decision, append to DECISIONS.md:
   - What was decided
   - Why this approach
   - Alternatives considered

5. **Mandatory Cleanup**:
   Always end with Task(subagent_type="cleanup")

## ACTUAL IMPLEMENTATION PROMPT

When `/ultrathink` is called, execute this:

## Agent Orchestration

### When to Use Sequential

- Architecture → Implementation → Review
- Each step depends on previous
- Building progressive context

### When to Use Parallel

- Multiple independent analyses
- Different perspectives needed
- Gathering diverse solutions

## When to Use UltraThink

### Use UltraThink When:

- Task complexity requires deep multi-agent analysis
- Architecture decisions need careful decomposition
- Requirements are vague and need exploration
- Multiple solution paths need evaluation
- Cross-cutting concerns need coordination

### Follow Workflow Directly When:

- Requirements are clear and straightforward
- Solution approach is well-defined
- Standard implementation patterns apply
- Single agent can handle the task

## Task Management

Always use TodoWrite to:

- Break down complex tasks
- Track progress
- Coordinate agents
- Document decisions
- Track workflow checklist completion

## Example Flow

### Development Task Example

```
User: "/ultrathink implement JWT authentication"

1. Detect: Development task (contains "implement")
2. Select: default-workflow skill (15 steps)
3. Try: Skill(skill="default-workflow")
4. Fallback if needed: Read `.claude/workflow/DEFAULT_WORKFLOW.md`
5. Begin executing workflow steps with deep analysis
6. Orchestrate multiple agents where complexity requires
7. Follow all workflow steps as defined
8. Adapt to any user customizations automatically
9. MANDATORY: Invoke cleanup agent at task completion
```

### Investigation Task Example

```
User: "/ultrathink investigate how the reflection system works"

1. Detect: Investigation task (contains "investigate")
2. Select: investigation-workflow skill (6 phases)
3. Inform user: "Detected investigation task. Using investigation-workflow skill"
4. Try: Skill(skill="investigation-workflow")
5. Fallback if needed: Read `.claude/workflow/INVESTIGATION_WORKFLOW.md`
6. Execute Phase 1: Scope Definition
7. Execute Phase 2: Exploration Strategy
8. Execute Phase 3: Parallel Deep Dives (multiple agents simultaneously)
9. Execute Phase 4: Verification & Testing
10. Execute Phase 5: Synthesis
11. Execute Phase 6: Knowledge Capture
12. MANDATORY: Update DISCOVERIES.md with findings
```

### Hybrid Workflow Example (Investigation → Development)

```
User: "/ultrathink investigate how authentication works, then add OAuth support"

Phase 1: Investigation
1. Detect: Investigation keywords present ("investigate")
2. Select: investigation-workflow skill (6 phases)
3. Try skill invocation (fallback to markdown if needed)
4. Execute full investigation workflow
5. Document findings in DISCOVERIES.md

Phase 2: Transition to Development
6. Detect: Development work needed ("add OAuth support")
7. Transition to default-workflow skill
8. Try skill invocation (fallback to markdown if needed)
9. Resume at Step 4 (Research and Design) using investigation insights
10. Continue through Step 15 (implementation → testing → PR)
11. MANDATORY: Invoke cleanup agent at completion
```

**When Investigation Leads to Development:**

Some development tasks require investigation first (Step 4 of DEFAULT_WORKFLOW.md):

- Unfamiliar codebase areas
- Complex subsystems requiring understanding
- Unclear architecture or integration points
- Need to understand existing patterns before designing new ones

In these cases, pause development workflow at Step 4, run full INVESTIGATION_WORKFLOW.md, then resume development with the knowledge gained.

## Mandatory Code Review (Steps 11-12)

**CRITICAL**: Every development workflow MUST include code review before completion.

**MANDATORY ENFORCEMENT**:

- **After Step 10**: MUST invoke reviewer agent for code review
- **After Step 11**: MUST implement review feedback (Step 12)
- **Do NOT mark workflow complete** until Steps 11-12 are done
- **No PR should be merged without code review**

The reviewer agent (Step 11):

- Reviews code for philosophy compliance (ruthless simplicity)
- Checks module boundaries and contracts
- Identifies code smells and anti-patterns
- Validates test coverage and quality
- Provides actionable feedback for improvements

Feedback Implementation (Step 12):

- Address ALL review feedback before proceeding
- Make required changes to meet quality standards
- Re-run tests after implementing feedback
- Update documentation if needed
- Verify philosophy compliance is achieved

**Review Trigger**: Automatically invoke reviewer agent when:

- Step 10 (implementation) is completed
- Code changes are ready for review
- Before creating pull request
- NEVER skip - Steps 11-12 are mandatory workflow steps

**Reminder**: Steps 11-12 are NOT optional. Code quality and philosophy compliance require systematic review.

## Mandatory Cleanup Phase

**CRITICAL**: Every ultrathink task MUST end with cleanup agent invocation.

**IMPORTANT**: Cleanup happens AFTER mandatory code review (Steps 11-12). Order: Step 10 → Step 11 (Review) → Step 12 (Implement Feedback) → Cleanup.

The cleanup agent:

- Reviews git status and file changes
- Removes temporary artifacts and planning documents
- Ensures philosophy compliance (ruthless simplicity)
- Provides final report on codebase state
- Guards against technical debt accumulation

**Cleanup Trigger**: Automatically invoke cleanup agent when:

- All todo items are completed (including Steps 11-12)
- Code review feedback has been implemented
- Main task objectives are achieved
- Before reporting task completion to user

UltraThink enhances the workflow with deep multi-agent analysis while respecting user customizations.

Remember: Ultra-thinking means thorough analysis before action, followed by ruthless cleanup.
