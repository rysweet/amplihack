# Ultra-Think Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/ultrathink <TASK_DESCRIPTION>`

## Purpose

Deep analysis mode for complex tasks. Orchestrates multiple agents to break down, analyze, and solve challenging problems by following the appropriate workflow (investigation or development).

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **First, detect task type** - Check if task is investigation or development
   - **Investigation keywords**: investigate, explain, understand, how does, why does, analyze, research, explore, examine, study
   - **Development keywords**: implement, build, create, add feature, fix, refactor, deploy
   - **If both types detected**: Use hybrid workflow (investigation first, then development)
   - If only investigation keywords found: Use INVESTIGATION_WORKFLOW.md (6 phases)
   - If only development keywords found: Use DEFAULT_WORKFLOW.md (15 steps)
2. **Read the appropriate workflow file** using the Read tool:
   - Investigation: `.claude/workflow/INVESTIGATION_WORKFLOW.md`
   - Development: `.claude/workflow/DEFAULT_WORKFLOW.md`
3. **Create a comprehensive todo list** using TodoWrite that includes all workflow steps/phases
4. **Execute each step systematically**, marking todos as in_progress and completed
5. **Use the specified agents** for each step (marked with "**Use**" or "**Always use**")
6. **Track decisions** by creating `.claude/runtime/logs/<session_timestamp>/DECISIONS.md`
7. **End with cleanup agent** (development) or knowledge capture (investigation)

## PROMPT-BASED WORKFLOW EXECUTION

Execute this exact sequence for the task: `{TASK_DESCRIPTION}`

### Step-by-Step Execution:

1. **Initialize**:
   - Detect task type (investigation vs. development)
   - Select appropriate workflow:
     - Investigation: INVESTIGATION_WORKFLOW.md (6 phases)
     - Development: DEFAULT_WORKFLOW.md (15 steps)
   - Inform user which workflow is being used
   - Read the selected workflow file using Read tool
   - Create TodoWrite list with all workflow steps/phases
   - Create session directory for decision logging

2. **For Each Workflow Step**:
   - Mark step as in_progress in TodoWrite
   - Read the step requirements from workflow
   - Invoke specified agents via Task tool
   - Log decisions made
   - Mark step as completed

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
2. Select: DEFAULT_WORKFLOW.md (15 steps)
3. Read workflow: `.claude/workflow/DEFAULT_WORKFLOW.md`
4. Begin executing workflow steps with deep analysis
5. Orchestrate multiple agents where complexity requires
6. Follow all workflow steps as defined
7. Adapt to any user customizations automatically
8. MANDATORY: Invoke cleanup agent at task completion
```

### Investigation Task Example

```
User: "/ultrathink investigate how the reflection system works"

1. Detect: Investigation task (contains "investigate")
2. Select: INVESTIGATION_WORKFLOW.md (6 phases)
3. Inform user: "Detected investigation task. Using INVESTIGATION_WORKFLOW.md"
4. Read workflow: `.claude/workflow/INVESTIGATION_WORKFLOW.md`
5. Execute Phase 1: Scope Definition
6. Execute Phase 2: Exploration Strategy
7. Execute Phase 3: Parallel Deep Dives (multiple agents simultaneously)
8. Execute Phase 4: Verification & Testing
9. Execute Phase 5: Synthesis
10. Execute Phase 6: Knowledge Capture
11. MANDATORY: Update DISCOVERIES.md with findings
```

### Hybrid Workflow Example (Investigation → Development)

```
User: "/ultrathink investigate how authentication works, then add OAuth support"

Phase 1: Investigation
1. Detect: Investigation keywords present ("investigate")
2. Select: INVESTIGATION_WORKFLOW.md (6 phases)
3. Execute full investigation workflow
4. Document findings in DISCOVERIES.md

Phase 2: Transition to Development
5. Detect: Development work needed ("add OAuth support")
6. Transition to DEFAULT_WORKFLOW.md
7. Resume at Step 4 (Research and Design) using investigation insights
8. Continue through Step 15 (implementation → testing → PR)
9. MANDATORY: Invoke cleanup agent at completion
```

**When Investigation Leads to Development:**

Some development tasks require investigation first (Step 4 of DEFAULT_WORKFLOW.md):

- Unfamiliar codebase areas
- Complex subsystems requiring understanding
- Unclear architecture or integration points
- Need to understand existing patterns before designing new ones

In these cases, pause development workflow at Step 4, run full INVESTIGATION_WORKFLOW.md, then resume development with the knowledge gained.

## Mandatory Cleanup Phase

**CRITICAL**: Every ultrathink task MUST end with cleanup agent invocation.

The cleanup agent:

- Reviews git status and file changes
- Removes temporary artifacts and planning documents
- Ensures philosophy compliance (ruthless simplicity)
- Provides final report on codebase state
- Guards against technical debt accumulation

**Cleanup Trigger**: Automatically invoke cleanup agent when:

- All todo items are completed
- Main task objectives are achieved
- Before reporting task completion to user

UltraThink enhances the workflow with deep multi-agent analysis while respecting user customizations.

Remember: Ultra-thinking means thorough analysis before action, followed by ruthless cleanup.
