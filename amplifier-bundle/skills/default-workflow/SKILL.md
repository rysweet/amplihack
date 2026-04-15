---
name: default-workflow
version: 2.0.0
description: |
  Development workflow for features, bugs, refactoring. Normally executed as a
  sub-recipe by dev-orchestrator/smart-orchestrator. Supports direct invocation
  via recipe runner for standalone use.
auto_activates:
  - "implement feature spanning multiple files"
  - "complex integration across components"
  - "refactor affecting 5+ files"
explicit_triggers:
  - /amplihack:default-workflow
confirmation_required: true
skip_confirmation_if_explicit: true
token_budget: 4500
---

# Default Workflow Skill

## Relationship to Dev Orchestrator

**Normal execution path**: This workflow is invoked as a sub-recipe by the
`dev-orchestrator` skill via `smart-orchestrator`. You do NOT normally need
to activate this skill directly.

```
User request → dev-orchestrator → smart-orchestrator recipe
    → default-workflow recipe (this skill's recipe)
```

**Direct invocation** is supported as a compatibility path when the
dev-orchestrator is unavailable or when explicitly requested. In that case,
use the recipe runner (see Execution Instructions below).

## Workflow Graph

```mermaid
flowchart TD
    subgraph P1["Phase 1: Requirements Clarification"]
        S0[Step 0: Workflow Preparation] --> S1[Step 1: Prepare Workspace]
        S1 --> S2[Step 2: Clarify Requirements]
        S2 --> S2b[Step 2b: Analyze Codebase]
        S2b --> S2c{Ambiguity?}
        S2c -->|yes| S2d[Step 2c: Resolve Ambiguity]
        S2c -->|no| S3
        S2d --> S3[Step 3: Create GitHub Issue]
        S3 --> S3b[Step 3b: Extract Issue Number]
    end

    subgraph P2["Phase 2: Design"]
        S4[Step 4: Setup Worktree/Branch] --> S5[Step 5: Architecture Design]
        S5 --> S5b{API needed?}
        S5b -->|yes| S5c[Step 5b: API Design]
        S5b -->|no| S5d
        S5c --> S5d{Database needed?}
        S5d -->|yes| S5e[Step 5c: Database Design]
        S5d -->|no| S5f
        S5e --> S5f[Step 5d: Security Review]
        S5f --> S5g[Step 5e: Design Consolidation]
    end

    subgraph P3["Phase 3: Implementation"]
        S6[Step 6: Documentation] --> S6b[Step 6b: Doc Review]
        S6b --> S6c[Step 6c: Doc Refinement]
        S6c --> S7[Step 7: Write Tests - TDD]
        S7 --> S8[Step 8: Implement]
        S8 --> S8b[Step 8b: Integration]
        S8b --> S9[Step 9: Refactor]
        S9 --> S9b[Step 9b: Optimize]
    end

    subgraph P4["Phase 4: Testing & Review"]
        S10[Step 10: Pre-commit Review] --> S10b[Step 10b: Security Review]
        S10b --> S10c[Step 10c: Philosophy Check]
        S10c --> S11[Step 11: Incorporate Feedback]
        S11 --> S11b[Step 11b: Implement Feedback]
        S11b --> S12[Step 12: Run Pre-commit Hooks]
        S12 --> S13[Step 13: Local Testing]
    end

    subgraph P5["Phase 5: Version & PR"]
        S14[Step 14: Bump Version - MANDATORY] --> S15[Step 15: Commit & Push]
        S15 --> S16[Step 16: Create Draft PR]
        S16 --> S16b[Step 16b: Outside-In Fix Loop]
    end

    subgraph P6["Phase 6: PR Review - MANDATORY"]
        S17a[Step 17a: Compliance Verification] --> S17b[Step 17b: Reviewer Agent]
        S17b --> S17c[Step 17c: Security Review]
        S17c --> S17d[Step 17d: Philosophy Guardian]
        S17d --> S17e{Blocking issues?}
        S17e -->|yes| S17f[Step 17e: Address Blocking]
        S17e -->|no| S17g
        S17f --> S17g[Step 17f: Verification Gate]
        S17g --> S18a[Step 18a: Analyze Feedback]
        S18a --> S18b[Step 18b: Implement Feedback]
        S18b --> S18c[Step 18c: Push Changes]
        S18c --> S18d[Step 18d: Respond to Comments]
        S18d --> S18e[Step 18e: Verification Gate]
    end

    subgraph P7["Phase 7: Merge"]
        S19a[Step 19a: Philosophy Check] --> S19b[Step 19b: Patterns Check]
        S19b --> S19c[Step 19c: Zero-BS Verification]
        S19c --> S19d[Step 19d: Verification Gate]
        S19d --> S20[Step 20: Final Cleanup]
        S20 --> S20b[Step 20b: Push Cleanup]
        S20b --> S20c[Step 20c: Quality Audit]
        S20c --> S21[Step 21: PR Ready]
        S21 --> S22[Step 22: Ensure Mergeable]
        S22 --> S22b[Step 22b: Final Status]
    end

    P1 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7
```

## Purpose

This skill provides the standard development workflow for all non-trivial code changes
in amplihack. It is normally executed as a sub-recipe by the `dev-orchestrator` via
`smart-orchestrator`, but can also be invoked directly via the recipe runner.

The workflow defines the canonical execution process: from requirements clarification
through design, implementation, testing, review, and merge. It ensures consistent
quality by orchestrating specialized agents at each step and enforcing philosophy
compliance throughout.

## Canonical Sources

- **Executable source (recipe)**: `amplifier-bundle/recipes/default-workflow.yaml`
- **Reference documentation**: `.claude/workflow/DEFAULT_WORKFLOW.md`

The recipe YAML is the authoritative execution definition. The `.md` file serves as
human-readable reference documentation for the workflow steps.

## Execution Instructions

### Normal path (via dev-orchestrator)

If you reached this skill via `dev-orchestrator` / `smart-orchestrator`, the recipe
runner is already managing execution. **Do not re-invoke the recipe runner.** The
orchestrator handles the full lifecycle including goal-seeking reflection loops.

### Direct invocation (standalone)

If this skill is activated directly (not via dev-orchestrator), you MUST use the
recipe runner — **do NOT read the .md file and follow steps manually**:

```python
from amplihack.recipes import run_recipe_by_name

result = run_recipe_by_name(
    "default-workflow",
    user_context={
        "task_description": "TASK_DESCRIPTION_HERE",
        "repo_path": ".",
    },
    progress=True,
)
```

Or via shell:

```bash
cd /path/to/repo && env -u CLAUDECODE \
  AMPLIHACK_HOME=/path/to/amplihack PYTHONPATH=${AMPLIHACK_HOME:-~/.amplihack}/src python3 -c "
from amplihack.recipes import run_recipe_by_name
result = run_recipe_by_name('default-workflow', user_context={
    'task_description': '''TASK_DESCRIPTION_HERE''',
    'repo_path': '.',
}, progress=True)
print(f'Recipe result: {result}')
"
```

**Do NOT** read `DEFAULT_WORKFLOW.md` and follow steps manually. The recipe runner
enforces step ordering, recursion guards, checkpoints, and quality gates that manual
execution cannot replicate.

### Preferred: Use dev-orchestrator instead

For most tasks, invoke `Skill(skill="dev-orchestrator")` or use `/dev <task>` rather
than activating this skill directly. The dev-orchestrator adds goal-seeking reflection,
workstream decomposition, and adaptive error recovery on top of this workflow.

## Auto-Activation Triggers

This skill auto-activates for:

- Features spanning multiple files (5+)
- Complex integrations across components
- Refactoring affecting 5+ files
- Any non-trivial code changes requiring structured workflow

**Note**: The `dev-orchestrator` skill has higher priority and broader triggers.
In most cases, it will activate first and invoke this workflow as a sub-recipe.

## Known Failure Points & Resilience Guidance

Steps that commonly fail during workflow execution. Agents executing this workflow
MUST apply the documented resilience patterns when encountering these steps.

### Step 3 — Issue Creation (label missing)

**Failure**: `gh label create` fails silently when labels cannot be created (permission denied, API timeout).
**Resilience**: Label attachment is best-effort. If `gh issue create --label` fails, retry without `--label`. The issue itself is the critical artifact, not its labels.

### Step 4 — Worktree Setup (no remote / no origin/main)

**Failure**: `git fetch origin main` aborts when the repo has no remotes or `origin/main` does not exist.
**Resilience**: Topology detection runs first. If no remote exists, use `HEAD` as base ref and skip push/upstream setup. The `bootstrap` flag in worktree output signals downstream steps to skip remote operations.

### Step 4 — Initial Push (network transient)

**Failure**: `git push origin <branch>` fails on fresh branch creation due to network issues.
**Resilience**: Push failure at step 4 emits a visible WARNING and defers to step 15/16. Push is retried with bounded retry (3 attempts, 2s backoff) at commit-and-push time. Step 16 also retries push before PR creation.

### Step 5b — Agent Output Artifact Missing

**Failure**: Agent output file not written or corrupted, causing downstream steps to fail with empty input.
**Resilience**: If an agent step produces empty output, the recipe runner should surface the error visibly. Checkpoints after design (step 5e) and after implementation (step 8b) preserve partial work so the workflow can resume from the nearest safe point.

### Step 15 — Push to Remote (upstream tracking)

**Failure**: `git rev-list --count @{u}..HEAD` fails when upstream is not set (first push scenario).
**Resilience**: Detect missing upstream explicitly. If `@{u}` fails, push unconditionally instead of silently skipping. Retry push with backoff on transient network errors.

### Step 16 — PR Creation (already exists / no commits)

**Failure**: `gh pr create` fails with "No commits between main and branch" or duplicate PR.
**Resilience**: Idempotency guard checks for existing PRs by branch name before creating. If PR already exists, reuse it. If no commits ahead, surface the error visibly rather than creating an empty PR.

### Step 21 — PR Ready (large template variables)

**Failure**: Shell `&&`-chain breaks when `philosophy_check`, `patterns_check`, or `quality_audit_results` template variables contain shell metacharacters or exceed ARG_MAX.
**Resilience**: Large template variables are captured via heredoc and truncated to 1KB before use in shell commands. Step 21 avoids echoing raw template content in bash; agent steps handle large text natively.

## Checkpoint Strategy

The workflow creates automatic checkpoints at these points to prevent work loss:

| Checkpoint                         | After Step                | Preserves                                     |
| ---------------------------------- | ------------------------- | --------------------------------------------- |
| `checkpoint-after-design`          | 5e (Design Consolidation) | Architecture decisions, API design, DB schema |
| `checkpoint-after-implementation`  | 8b (Integration)          | Tests, implementation code, integration work  |
| `checkpoint-after-review-feedback` | 11b (Implement Feedback)  | Review-addressed changes                      |

If a step fails after a checkpoint, the worktree branch retains all committed work. Agents can resume from the latest checkpoint by re-running the workflow with the existing worktree.

## Related Files

- **Recipe (executable)**: `amplifier-bundle/recipes/default-workflow.yaml`
- **Reference docs**: `.claude/workflow/DEFAULT_WORKFLOW.md`
- **Command Interface**: `.claude/commands/amplihack/dev.md`
- **Orchestrator Skill**: `.claude/skills/dev-orchestrator/`
- **Investigation Workflow**: `.claude/skills/investigation-workflow/`
