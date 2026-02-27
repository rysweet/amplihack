---
name: dev-orchestrator
description: |
  Default task orchestrator for all development and investigation work.
  Classifies tasks, decomposes into parallel workstreams if appropriate,
  and routes execution through the recipe runner. Replaces ultrathink-orchestrator.
version: 2.0.0
auto_activates:
  - "implement"
  - "build"
  - "create"
  - "add feature"
  - "fix bug"
  - "refactor"
  - "investigate"
  - "analyze"
  - "research"
  - "explore"
  - "develop"
  - "make"
priority: 5
---

# Dev Orchestrator Skill

## Purpose

This is the **default orchestrator** for all non-trivial development and investigation tasks
in amplihack. It replaces the `ultrathink-orchestrator` skill.

When a user asks you to build, implement, fix, investigate, or create anything non-trivial,
this skill ensures:

1. **Task is classified** — Q&A / Operations / Investigation / Development
2. **Goal is formulated** — clear success criteria identified
3. **Workstreams detected** — parallel tasks split automatically
4. **Recipe runner used** — code-enforced workflow execution
5. **Outcome verified** — reflection confirms goal achievement

## How It Works

```
User request
     │
     ▼
[Classify] ──→ Q&A / Ops ──→ Respond directly
     │
     ▼ Development / Investigation
[Decompose] ──→ 1 workstream ──→ [default-workflow recipe]
     │                                      │
     └──────→ N workstreams ──→ [multitask] ┤
                                            ▼
                                    [Reflect on goal]
                                    GOAL_STATUS: ACHIEVED / PARTIAL / NOT_ACHIEVED
                                    (result reported to user)
```

## Activation

This skill auto-activates for development and investigation keywords. It is also the
**default behavior** per CLAUDE.md — invoke it for any non-trivial task.

The `UserPromptSubmit` hook reinforces this by injecting a classification reminder
that references `/dev` as the entry point.

## Execution Instructions

When this skill is activated:

### Step 1: Check Recipe Runner availability

```python
try:
    from amplihack.recipes import run_recipe_by_name
    RECIPE_RUNNER_AVAILABLE = True
except ImportError:
    RECIPE_RUNNER_AVAILABLE = False
```

### Step 2: Route to appropriate execution method

**PREFERRED — Recipe Runner (when available)**:

```python
from amplihack.recipes import run_recipe_by_name
from amplihack.recipes.adapters.sdk import ClaudeSDKAdapter

adapter = ClaudeSDKAdapter()
result = run_recipe_by_name(
    "smart-orchestrator",
    adapter=adapter,
    user_context={
        "task_description": TASK_DESCRIPTION,
        "repo_path": ".",
    }
)
```

**FALLBACK — Direct workflow execution (if Recipe Runner unavailable)**:

- Q&A / Operations: Respond directly
- Investigation: `Skill(skill="investigation-workflow")`
- Development with single task: `Skill(skill="default-workflow")`
- Development with parallel tasks: Invoke `Task(subagent_type="general-purpose")` to run
  the multitask orchestrator

### Step 3: Reflect and verify

After execution completes, verify the goal was achieved. If not:

- For missing information: ask the user
- For fixable gaps: re-invoke with the remaining work description

## Task Type Classification

| Type          | Keywords                                                      | Action                        |
| ------------- | ------------------------------------------------------------- | ----------------------------- |
| Q&A           | "what is", "explain", "how do I", "quick question"            | Respond directly              |
| Operations    | "cleanup", "delete", "git status", "run command"              | Execute directly              |
| Investigation | "investigate", "analyze", "how does", "understand", "explore" | investigation-workflow        |
| Development   | "implement", "build", "create", "add", "fix", "refactor"      | smart-orchestrator            |
| Hybrid        | Both investigation + development keywords                     | investigation first, then dev |

## Workstream Decomposition Examples

| Request                                  | Workstreams                             |
| ---------------------------------------- | --------------------------------------- |
| "implement JWT auth"                     | 1: auth (default-workflow)              |
| "build a webui and an api"               | 2: api + webui (parallel)               |
| "add logging and add metrics"            | 2: logging + metrics (parallel)         |
| "investigate auth system then add OAuth" | 2: investigate + implement (sequential) |
| "fix bug in payment flow"                | 1: bugfix (default-workflow)            |

## Canonical Sources

- **Recipe**: `amplifier-bundle/recipes/smart-orchestrator.yaml`
- **Parallel execution**: `.claude/skills/multitask/orchestrator.py`
- **Development workflow**: `amplifier-bundle/recipes/default-workflow.yaml`
- **Investigation workflow**: `amplifier-bundle/recipes/investigation-workflow.yaml`
- **CLAUDE.md**: Defines this as the default orchestrator

## Relationship to Other Skills

| Skill                     | Relationship                                         |
| ------------------------- | ---------------------------------------------------- |
| `ultrathink-orchestrator` | Deprecated — redirects here                          |
| `default-workflow`        | Called by this orchestrator for single dev tasks     |
| `investigation-workflow`  | Called by this orchestrator for research tasks       |
| `multitask`               | Called by this orchestrator for parallel workstreams |
| `work-delegator`          | Orthogonal — for backlog-driven delegation           |

## Entry Points

- **Primary**: `/dev <task description>`
- **Auto-activation**: Via CLAUDE.md default behavior + hook injection
- **Legacy**: `/ultrathink <task>` (deprecated alias → redirects to `/dev`)
