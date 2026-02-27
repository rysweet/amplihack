---
name: amplihack:dev
version: 2.0.0
description: |
  Primary entry point for all development and investigation work.
  Classifies task, decomposes into workstreams if parallel-capable,
  and launches execution via recipe runner. The default orchestrator.
triggers:
  - "implement"
  - "build"
  - "create"
  - "fix"
  - "refactor"
  - "investigate"
  - "develop"
  - "make"
  - "add feature"
invokes:
  - type: recipe
    name: smart-orchestrator
  - type: recipe
    name: default-workflow
  - type: recipe
    name: investigation-workflow
dependencies:
  required:
    - amplifier-bundle/recipes/smart-orchestrator.yaml
examples:
  - "/dev add user authentication"
  - "/dev build a webui and an API for user management"
  - "/dev fix the login timeout bug"
  - "/dev investigate how the caching layer works"
  - "/dev implement OAuth and add structured logging"
---

# Dev Command

## Usage

`/dev <TASK_DESCRIPTION>`

The primary entry point for all development work in amplihack. This command
classifies your task, detects parallel workstreams, and executes via recipe runner.

## Glossary

**Workstream**: An isolated parallel execution unit. When your request contains multiple independent components (e.g., "build an API and a webui"), the orchestrator splits them into separate workstreams that run concurrently in `/tmp/amplihack-workstreams/`.

**Recipe**: A YAML workflow definition that specifies the exact sequence of steps Claude follows. The `smart-orchestrator` recipe is what runs when you invoke `/dev`.

**Recipe Runner**: The Python execution engine (`amplihack.recipes.run_recipe_by_name`) that executes recipes with code-enforced step ordering. When available, it's strongly preferred over prompt-based execution.

**Session Tree**: A lightweight state tracker in `/tmp/amplihack-session-trees/` that prevents infinite recursive orchestration by tracking active sessions and enforcing depth and capacity limits.

**Goal-Seeking Loop**: The up-to-3-round retry mechanism. After each execution
round, a reviewer agent evaluates whether the goal was achieved. If PARTIAL or
NOT_ACHIEVED, another round runs automatically (up to 3 total). After all rounds
complete, a mandatory `reflect-final` step runs unconditionally to produce the
definitive `GOAL_STATUS` assessment used in the summary.

**Recursion Guard Fallback**: When the session depth limit is reached and
parallel workstream spawning is blocked, the orchestrator automatically falls
back to single-session execution (via `execute-single-fallback-blocked`). The
task runs as a single Claude session without sub-workstream spawning.

## Examples

**Single task** (one workstream):

```
/dev fix the authentication bug where tokens expire too early
/dev add pagination to the user listing API
/dev investigate how the caching layer works
```

**Parallel tasks** (multiple workstreams launched simultaneously):

```
/dev build a REST API and a React webui for user management
/dev add OAuth support and add structured logging
/dev investigate the auth system then implement refresh tokens
```

## How It Works

```
/dev <request>
      │
      ▼
[smart-orchestrator recipe]
      │
      ├─ Q&A ──────────────────────────────→ analyzer agent (direct answer)
      │
      ├─ Ops ──────────────────────────────→ builder agent (executes operation)
      │
      ├─ 1 workstream ──────────────────────→ default-workflow recipe
      │
      ├─ N workstreams (parallel) ──────────→ multitask orchestrator
      │         [if BLOCKED by depth limit: falls back to]
      └─────────────────────────────────────→ single-session execution
                                                    │
                                                    ▼
                                           [Reflect on goal]
```

## EXECUTION INSTRUCTIONS FOR CLAUDE

> **Note for users**: The section below documents how Claude internally executes this command. You do not need to run any of this code yourself — just type `/dev <your task>`.

When this command is invoked with `{TASK_DESCRIPTION}`:

### Option A: Recipe Runner (PREFERRED when available)

> Note: `{TASK_DESCRIPTION}` below is the literal user text passed to this command.
> Claude must substitute the actual task text — do not pass the string `"{TASK_DESCRIPTION}"`.

```python
from amplihack.recipes import run_recipe_by_name
from amplihack.recipes.adapters.sdk import ClaudeSDKAdapter

# IMPORTANT: Replace TASK_DESCRIPTION with the actual user request text
task = "<the actual task from the user>"

adapter = ClaudeSDKAdapter()
result = run_recipe_by_name(
    "smart-orchestrator",
    adapter=adapter,
    user_context={
        "task_description": task,  # actual text, not literal "{TASK_DESCRIPTION}"
        "repo_path": ".",
    }
)
```

### Option B: Skill invocation (if Recipe Runner unavailable)

```
Skill(skill="dev-orchestrator")
```

### Option C: Direct classification + routing (final fallback)

1. **Classify** the task type from `{TASK_DESCRIPTION}`:
   - **Q&A** (what is, explain, how do I): respond directly
   - **Operations** (cleanup, delete, run command): execute directly
   - **Investigation** (investigate, analyze, understand): `Skill(skill="investigation-workflow")`
   - **Development** (implement, build, fix, create, refactor): continue below

2. **Detect parallel workstreams**:
   - If single cohesive task: `Skill(skill="default-workflow")`
   - If multiple independent components: split into workstreams and launch multitask orchestrator

3. **Reflect on goal achievement**: After execution, verify success criteria met.

## Task Description

```
{TASK_DESCRIPTION}
```
