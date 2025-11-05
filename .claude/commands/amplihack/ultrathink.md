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
2. **MANDATORY: Create comprehensive todo list** using TodoWrite - CANNOT PROCEED without this for multi-step tasks (3+ steps)
   - List all major workflow steps identified
   - Mark in_progress as you work on each step
   - Mark completed immediately after finishing each step
   - Failure to use TodoWrite will result in task rejection
3. **Execute each step systematically**, marking todos as in_progress and completed
4. **Use the specified agents** for each step (marked with "**Use**" or "**Always use**")
5. **Track decisions** by creating `.claude/runtime/logs/<session_timestamp>/DECISIONS.md`
6. **End with cleanup agent** to ensure code quality

## PROMPT-BASED WORKFLOW EXECUTION

Execute this exact sequence for the task: `{TASK_DESCRIPTION}`

### Step-by-Step Execution:

1. **Initialize** (MANDATORY SEQUENCE):
   - Read workflow file using FrameworkPathResolver to get the current 13-step process
   - **IMMEDIATELY create TodoWrite list** with all workflow steps (REQUIRED - cannot skip)
   - Create session directory for decision logging
   - TodoWrite MUST be called before proceeding to step 2

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

## Task Management - MANDATORY TodoWrite Usage

**CRITICAL ENFORCEMENT**: TodoWrite is MANDATORY for ALL ultrathink tasks. You CANNOT PROCEED without using TodoWrite first.

### Why TodoWrite is Mandatory

- Users need to see progress through long sessions (e.g., 494-message sessions)
- Provides structure and prevents scope creep
- Clear completion criteria for each step
- Reduces session length by maintaining focus
- Makes complex investigations transparent

### TodoWrite Requirements

**MUST use TodoWrite for:**

- ANY ultrathink task (no exceptions)
- Multi-step tasks with 3+ steps
- Complex investigations or analyses
- Feature implementations
- Bug investigations
- System design tasks

**TodoWrite MUST include:**

- All major workflow steps identified from DEFAULT_WORKFLOW.md
- Clear, actionable task descriptions
- Progress tracking (pending → in_progress → completed)
- One task in_progress at a time

### Example TodoWrite for Investigation Task

```
1. Locate relevant files (pending)
2. Read core implementation (pending)
3. Understand architecture (pending)
4. Test/verify functionality (pending)
5. Document findings (pending)
```

As you work, update status:

```
1. Locate relevant files (completed)
2. Read core implementation (in_progress)
3. Understand architecture (pending)
4. Test/verify functionality (pending)
5. Document findings (pending)
```

### Example TodoWrite for Feature Implementation

```
1. Read workflow file (pending)
2. Create design specification (pending)
3. Implement core functionality (pending)
4. Add unit tests (pending)
5. Run pre-commit checks (pending)
6. Create PR (pending)
```

### Validation and Enforcement

**If TodoWrite is NOT used:**

- Task will be rejected
- You must restart and create TodoWrite first
- No exceptions - this is MANDATORY

**Validation checklist:**

- [ ] TodoWrite called immediately after reading workflow
- [ ] All major steps are listed
- [ ] Tasks marked as in_progress while working
- [ ] Tasks marked as completed after finishing
- [ ] Only one task in_progress at a time

## Example Flow

```
1. Read workflow using FrameworkPathResolver.resolve_workflow_file()
2. MANDATORY: Create TodoWrite list with all workflow steps (CANNOT SKIP)
3. Begin executing workflow steps with deep analysis
4. Update TodoWrite status as you progress through each step
5. Orchestrate multiple agents where complexity requires
6. Follow all workflow steps as defined
7. Adapt to any user customizations automatically
8. MANDATORY: Invoke cleanup agent at task completion
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
