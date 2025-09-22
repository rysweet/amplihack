# Ultra-Think Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/ultrathink <TASK_DESCRIPTION>`

## Purpose

Deep analysis mode for complex tasks. Orchestrates multiple agents to break down, analyze, and solve challenging problems.

## Integration with Default Workflow

UltraThink dynamically follows the workflow defined in `.claude/workflow/DEFAULT_WORKFLOW.md`:

- Reads and follows whatever workflow steps are defined
- Adapts automatically when users customize the workflow
- Provides deep multi-agent analysis within the workflow structure
- No need to update UltraThink when workflow changes

## Process

For non-trivial code changes, UltraThink:

1. **Reads the current workflow** from `.claude/workflow/DEFAULT_WORKFLOW.md`
2. **Provides deep analysis** using multiple agents where complexity requires it
3. **Follows each workflow step** as defined by the user
4. **Orchestrates agents** according to workflow requirements

The workflow is the single source of truth - UltraThink adapts to it automatically.

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
1. Read workflow from DEFAULT_WORKFLOW.md
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
