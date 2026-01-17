---
name: amplihack:ultrathink
version: 2.0.0
description: Systematic workflow orchestration - default for development and investigation tasks
default_for: [development, investigation]
trigger_keywords: [orchestrate, systematic, workflow]
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
You MUST use one of the workflow skills - either default-workflow or investigation-workflow or both or its possible the user could pass in additional workflow skills like cascade or debate.

## Default Behavior

Claude invokes this skill for non-trivial development and investigation tasks:
- Development: "implement", "add", "fix", "create", "refactor"
- Investigation: "investigate", "analyze", "explore", "understand"
- Q&A: Responds directly (no orchestration needed)
- Operations: Responds directly (no orchestration needed) - "run command", "cleanup", "git operations"

**Bypass**: Use explicit commands (`/fix`, `/analyze`) or request "without ultrathink"

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:
Execute this exact sequence for the task: `{TASK_DESCRIPTION}`

1. **First, detect task type** - Check if task is Q&A, investigation, or development
   - **Q&A keywords**: what is, explain briefly, quick question, how do I run, simple question
   - **Investigation keywords**: investigate, explain, understand, how does, why does, analyze, research, explore, examine, study
   - **Development keywords**: implement, build, create, add feature, fix, refactor, deploy
   - **Priority order**: Q&A detection first (simple questions), then Investigation, then Development
   - **If Q&A detected**: Use @.claude/workflow/Q&A_WORKFLOW.md (simple, single-turn answers)
   - **If Investigation keywords found**: Use @.claude/workflow/INVESTIGATION_WORKFLOW.md
   - **If Development keywords found**: Use @.claude/workflow/DEFAULT_WORKFLOW.md
   - **If both Investigation and Development detected**: Use hybrid workflow (investigation first, then development)
2. Mandatory - not doing this wil require rework **Invoke the appropriate workflow skill** using the Skill tool:
   - Q&A: Read @.claude/workflow/Q&A_WORKFLOW.md directly (no skill wrapper needed for simple Q&A)
   - Investigation: Skill(skill="investigation-workflow")`
   - Development: `Skill(skill="default-workflow")`
   - **FALLBACK**: If skill invocation fails (skill not found), fall back to reading markdown workflows:
     - Q&A: @.claude/workflow/Q&A_WORKFLOW.md
     - Investigation: @.claude/workflow/INVESTIGATION_WORKFLOW.md
     - Development: @.claude/workflow/DEFAULT_WORKFLOW.md
3. ALWAYS **Create a comprehensive todo list** using TodoWrite tool that includes all workflow steps/phases
4. ALWAYS **Execute each step systematically**, marking todos as in_progress and completed

THERE IS NO VALUE in SKIPPING STEPS - DO NOT TAKE SHORTCUTS.

- **For Each Workflow Step**:
  - Mark step as in_progress in TodoWrite
  - Break down the step into smaller tasks if needed
  - Read the step requirements from workflow
  - Invoke specified agents via Task tool
  - Log decisions made
  - Mark step as completed
  - No steps are optional - all steps must be followed in sequence.
- **Agent Invocation Pattern**:

  ```
  For step requiring "**Use** architect agent":
  → Invoke Task(subagent_type="architect", prompt="[step requirements + task context]")

  For step requiring multiple agents:
  → Invoke multiple Task calls in parallel
  ```

### Agent Orchestration

#### When to Use Sequential

- Architecture → Implementation → Review
- Each step depends on previous
- Building progressive context

#### When to Use Parallel

- Multiple independent analyses
- Different perspectives needed
- Gathering diverse solutions

- **Decision Logging**:

  After each major decision, append to DECISIONS.md:
  - What was decided
  - Why this approach
  - Alternatives considered

- **Mandatory Cleanup**:
  Always end with Task(subagent_type="cleanup")

5. **Use the specified agents** for each step (marked with "**Use**" or "**Always use**")
6. \*\*MANDATORY: Enforce all steps.
7. **Track decisions** by creating and writing important decisions to `.claude/runtime/logs/<session_timestamp>/DECISIONS.md`
8. **End with cleanup agent** (development) or knowledge capture (investigation)

## Task Management

Always use TodoWrite to:

- Break down complex tasks
- Track progress
- Coordinate agents
- Document decisions
- Track workflow checklist completion

## Example Flow

### Q&A Task Example

```
User: "/ultrathink what is the purpose of the workflow system?"

1. Detect: Q&A task (contains "what is")
2. Select: Q&A workflow (simple, single-turn)
3. Read: `.claude/workflow/Q&A_WORKFLOW.md`
4. Follow Q&A workflow steps (typically 3-4 steps)
5. Provide concise, direct answer
6. No complex agent orchestration needed
```

### Development Task Example

```
User: "/ultrathink implement JWT authentication"

1. Detect: Development task (contains "implement")
2. Select: default-workflow skill
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

# ALWAYS PICK A WORKFLOW OR FOLLOW THE ONE THE USER TOLD YOU TO USE

YOU MAY NOT SKIP STEPS in the workflow.
UltraThink enhances the workflow with deep multi-agent analysis while respecting user customizations.

Remember: Ultra-thinking means thorough analysis before action, followed by ruthless cleanup.
