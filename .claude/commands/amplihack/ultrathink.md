# Ultra-Think Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/ultrathink <TASK_DESCRIPTION>`

## Purpose

Deep analysis mode for complex tasks. Orchestrates multiple agents to break down, analyze, and solve challenging problems by following the default workflow.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **First, read the workflow file** using FrameworkPathResolver.resolve_workflow_file() to get the correct path, then use the Read tool
2. **Create a comprehensive todo list** using TodoWrite that includes all 13 workflow steps
3. **Execute each step systematically**, marking todos as in_progress and completed
4. **Use the specified agents** for each step (marked with "**Use**" or "**Always use**")
5. **Track decisions** by creating `.claude/runtime/logs/<session_timestamp>/DECISIONS.md`
6. **End with cleanup agent** to ensure code quality

## PROMPT-BASED WORKFLOW EXECUTION

Execute this exact sequence for the task: `{TASK_DESCRIPTION}`

### Step-by-Step Execution:

1. **Initialize**:
   - Read workflow file using FrameworkPathResolver to get the current 13-step process
   - Create TodoWrite list with all workflow steps
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

```
1. Read workflow using FrameworkPathResolver.resolve_workflow_file()
2. Begin executing workflow steps with deep analysis
3. Orchestrate multiple agents where complexity requires
4. Follow all workflow steps as defined
5. Adapt to any user customizations automatically
6. MANDATORY: Invoke cleanup agent at task completion
```

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
