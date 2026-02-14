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

@~/.amplihack/.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/ultrathink <TASK_DESCRIPTION>`

## Purpose

Deep analysis mode for complex tasks. Uses Recipe Runner for code-enforced workflow execution when available, with automatic fallback to workflow skills or markdown workflows.

**Recipe Runner (Code-Enforced)**: When the `amplihack.recipes` module is available, ultrathink uses Recipe Runner to execute workflows as deterministic YAML recipes. This provides:

- **Code enforcement**: Steps execute via Python SDK adapters, not just prompts
- **Fail-fast behavior**: Workflow stops on first step failure
- **Context accumulation**: Each step's output feeds into subsequent steps
- **Conditional execution**: Steps can be skipped based on runtime conditions

**Fallback Chain**: Recipe Runner → Workflow Skills → Markdown Workflows

You MUST use one of the workflow execution methods - Recipe Runner recipes, workflow skills, or markdown workflows (default-workflow, investigation-workflow, cascade, debate, etc.).

## Default Behavior

Claude invokes this skill for non-trivial development and investigation tasks:

- Development: "implement", "add", "fix", "create", "refactor"
- Investigation: "investigate", "analyze", "explore", "understand"
- Q&A: Responds directly (no orchestration needed)
- Operations: Responds directly (no orchestration needed) - "run command", "cleanup", "git operations"

**Bypass**: Use explicit commands (`/fix`, `/analyze`) or request "without ultrathink"

## Workflow Execution Hierarchy

Ultra think follows this preference order for workflow execution:

1. **Recipe Runner** (code-enforced, deterministic, fail-fast)
   - Requires: `amplihack.recipes` module available
   - Enabled by: `AMPLIHACK_USE_RECIPES=1` (default) or unset
   - Disabled by: `AMPLIHACK_USE_RECIPES=0`
   - Benefits: Code enforcement, context accumulation, conditional execution, fail-fast

2. **Workflow Skills** (prompt-based with TodoWrite tracking)
   - Requires: Skill definitions in `.claude/skills/`
   - Provides: Structured prompts, agent orchestration
   - Falls back to: Markdown workflows if skill unavailable

3. **Markdown Workflows** (baseline prompt-based execution)
   - Always available: `.claude/workflow/*.md` files
   - Provides: Baseline workflow instructions
   - Last resort: No code enforcement, relies on Claude following prompts

**When to Force Markdown Mode:**
Set `AMPLIHACK_USE_RECIPES=0` when:

- Debugging workflow issues
- Testing prompt-based execution
- Recipe Runner has bugs
- Developing new workflow features

## ⛔ BLOCKING REQUIREMENT: Workflow Invocation

When ultrathink-orchestrator skill is triggered (auto-activation or explicit /ultrathink command), you MUST:

1. **FIRST: Check if Recipe Runner is available** (unless `AMPLIHACK_USE_RECIPES=0`):
   - Try: `from amplihack.recipes import run_recipe_by_name`
   - If successful: Use Recipe Runner for code-enforced execution
   - If ImportError: Fall back to workflow skills

2. **Recipe Runner Execution** (when available):
   - Development tasks: `run_recipe_by_name("default-workflow", adapter=sdk_adapter, user_context={...})`
   - Investigation tasks: `run_recipe_by_name("investigation-workflow", adapter=sdk_adapter, user_context={...})`
   - Q&A tasks: `run_recipe_by_name("qa-workflow", adapter=sdk_adapter, user_context={...})`
   - **Error Handling**: If `run_recipe_by_name()` raises exception during execution, report error and fall back to workflow skills

3. **Fallback to Workflow Skills** (if Recipe Runner unavailable):
   - Development: `Skill(skill="default-workflow")`
   - Investigation: `Skill(skill="investigation-workflow")`
   - Q&A: Read @~/.amplihack/.claude/workflow/Q&A_WORKFLOW.md directly

4. **Final Fallback to Markdown Workflows** (if skills unavailable):
   - Development: `Read(file_path="~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md")`
   - Investigation: `Read(file_path="~/.amplihack/.claude/workflow/INVESTIGATION_WORKFLOW.md")`

5. **NEVER proceed with workflow execution without loading the workflow**
   - Power-steering will detect this violation at session end
   - Session will be blocked until proper workflow invocation is added

**Self-Check Protocol:**
Before proceeding with any workflow steps, verify you have:

- [ ] Tried Recipe Runner import (unless `AMPLIHACK_USE_RECIPES=0`), OR
- [ ] Invoked Skill tool with workflow skill name, OR
- [ ] Used Read tool to load workflow markdown file
- [ ] Confirmed workflow content is loaded in context

**Error Protocol:**
If you forget to invoke the workflow:

1. Power-steering will block session termination
2. You must retry with proper Recipe Runner, Skill, or Read tool invocation
3. No shortcuts or workarounds accepted

**Environment Variable Control:**

- `AMPLIHACK_USE_RECIPES=1` (default): Use Recipe Runner when available
- `AMPLIHACK_USE_RECIPES=0`: Skip Recipe Runner, use skills/markdown only

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:
Execute this exact sequence for the task: `{TASK_DESCRIPTION}`

1. **First, detect task type** - Check if task is Q&A, investigation, or development
   - **Q&A keywords**: what is, explain briefly, quick question, how do I run, simple question
   - **Investigation keywords**: investigate, explain, understand, how does, why does, analyze, research, explore, examine, study
   - **Development keywords**: implement, build, create, add feature, fix, refactor, deploy
   - **Priority order**: Q&A detection first (simple questions), then Investigation, then Development
   - **If Q&A detected**: Use qa-workflow recipe or Q&A_WORKFLOW.md
   - **If Investigation keywords found**: Use investigation-workflow recipe or INVESTIGATION_WORKFLOW.md
   - **If Development keywords found**: Use default-workflow recipe or DEFAULT_WORKFLOW.md
   - **If both Investigation and Development detected**: Use hybrid workflow (investigation first, then development)

2. **Check Recipe Runner availability** (unless `AMPLIHACK_USE_RECIPES=0`):

   ```python
   # Detection logic Claude should follow (not executable Python):
   # - Check: Is AMPLIHACK_USE_RECIPES=0? If yes, skip Recipe Runner
   # - Otherwise: Try importing amplihack.recipes.run_recipe_by_name
   # - If ImportError: Fall back to workflow skills
   # - If import succeeds: Use Recipe Runner for execution

   use_recipes = os.environ.get('AMPLIHACK_USE_RECIPES', '1') != '0'

   if use_recipes:
       try:
           from amplihack.recipes import run_recipe_by_name
           recipe_available = True
       except ImportError:
           recipe_available = False
   else:
       recipe_available = False
   ```

3. Mandatory - not doing this will require rework **Invoke the appropriate workflow execution method**:

   **OPTION A: Recipe Runner (PREFERRED when available)**:

   ```python
   # For development tasks:
   from amplihack.recipes import run_recipe_by_name
   result = run_recipe_by_name(
       "default-workflow",
       adapter=sdk_adapter,  # Claude Code SDK adapter
       user_context={"task": "{TASK_DESCRIPTION}", "user_requirements": "..."}
   )

   # For investigation tasks:
   result = run_recipe_by_name(
       "investigation-workflow",
       adapter=sdk_adapter,
       user_context={"task": "{TASK_DESCRIPTION}"}
   )

   # For Q&A tasks:
   result = run_recipe_by_name(
       "qa-workflow",
       adapter=sdk_adapter,
       user_context={"question": "{TASK_DESCRIPTION}"}
   )
   ```

   **OPTION B: Workflow Skills (if Recipe Runner unavailable)**:
   - Q&A: Read @~/.amplihack/.claude/workflow/Q&A_WORKFLOW.md directly
   - Investigation: `Skill(skill="investigation-workflow")`
   - Development: `Skill(skill="default-workflow")`

   **OPTION C: Markdown Workflows (final fallback)**:
   - Q&A: @~/.amplihack/.claude/workflow/Q&A_WORKFLOW.md
   - Investigation: @~/.amplihack/.claude/workflow/INVESTIGATION_WORKFLOW.md
   - Development: @~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md

4. ALWAYS **Create a comprehensive todo list** using TodoWrite tool that includes all workflow steps/phases
5. ALWAYS **Execute each step systematically**, marking todos as in_progress and completed

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
7. **Track decisions** by creating and writing important decisions to `~/.amplihack/.claude/runtime/logs/<session_timestamp>/DECISIONS.md`
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
3. Read: `~/.amplihack/.claude/workflow/Q&A_WORKFLOW.md`
4. Follow Q&A workflow steps (typically 3-4 steps)
5. Provide concise, direct answer
6. No complex agent orchestration needed
```

### Development Task Example (with Recipe Runner)

```
User: "/ultrathink implement JWT authentication"

1. Detect: Development task (contains "implement")
2. Check environment: AMPLIHACK_USE_RECIPES not set to 0
3. Try Recipe Runner:
   - Import: `from amplihack.recipes import run_recipe_by_name`
   - Execute: `run_recipe_by_name("default-workflow", adapter=sdk_adapter, user_context={"task": "implement JWT authentication"})`
   - Recipe Runner handles all 23 steps with code enforcement
4. If ImportError (Recipe Runner unavailable):
   - Fall back to: `Skill(skill="default-workflow")`
5. If skill fails:
   - Final fallback: Read `~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md`
6. Recipe Runner automatically:
   - Executes each step via SDK adapter
   - Accumulates context between steps
   - Stops on first failure (fail-fast)
   - Orchestrates agents as defined in recipe
7. MANDATORY: Cleanup agent invoked by recipe
```

### Investigation Task Example (with Recipe Runner)

```
User: "/ultrathink investigate how the reflection system works"

1. Detect: Investigation task (contains "investigate")
2. Check environment: AMPLIHACK_USE_RECIPES not set to 0
3. Try Recipe Runner:
   - Import: `from amplihack.recipes import run_recipe_by_name`
   - Execute: `run_recipe_by_name("investigation-workflow", adapter=sdk_adapter, user_context={"task": "investigate reflection system"})`
   - Recipe Runner handles all 6 phases with code enforcement
4. If ImportError (Recipe Runner unavailable):
   - Fall back to: `Skill(skill="investigation-workflow")`
5. If skill fails:
   - Final fallback: Read `~/.amplihack/.claude/workflow/INVESTIGATION_WORKFLOW.md`
6. Recipe Runner automatically:
   - Phase 1: Scope Definition (code-enforced)
   - Phase 2: Exploration Strategy (code-enforced)
   - Phase 3: Parallel Deep Dives (multiple agents via recipe)
   - Phase 4: Verification & Testing (code-enforced)
   - Phase 5: Synthesis (code-enforced)
   - Phase 6: Knowledge Capture (code-enforced)
7. MANDATORY: DISCOVERIES.md updated by recipe
```

### Hybrid Workflow Example (Investigation → Development with Recipe Runner)

```
User: "/ultrathink investigate how authentication works, then add OAuth support"

Phase 1: Investigation (Recipe Runner)
1. Detect: Investigation keywords present ("investigate")
2. Check Recipe Runner availability
3. Execute investigation via Recipe Runner:
   result1 = run_recipe_by_name(
       "investigation-workflow",
       adapter=sdk_adapter,
       user_context={"task": "investigate authentication system"}
   )
4. Recipe Runner executes all 6 investigation phases
5. Findings stored in result1.context

Phase 2: Transition to Development (Recipe Runner with investigation context)
6. Detect: Development work needed ("add OAuth support")
7. Execute development workflow with investigation findings:
   result2 = run_recipe_by_name(
       "default-workflow",
       adapter=sdk_adapter,
       user_context={
           "task": "add OAuth support",
           "investigation_findings": result1.context,
           "architecture_insights": result1.context.get("insights", {})
       }
   )
8. Recipe Runner executes all 23 development steps
9. Automatically resumes at Step 5 (Research and Design) using investigation insights
10. Continues through Step 22 (implementation → testing → PR)
11. MANDATORY: Cleanup agent invoked by recipe

**Fallback Pattern** (if Recipe Runner unavailable):
- Phase 1: Use `Skill(skill="investigation-workflow")` or Read investigation markdown
- Phase 2: Use `Skill(skill="default-workflow")` or Read default workflow markdown
- Manually pass investigation context between phases
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
