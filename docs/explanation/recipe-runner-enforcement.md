# Recipe Runner Enforcement: Why It's Mandatory

**Diátaxis category**: Explanation

This document explains why the recipe runner is mandatory for `/dev` Development and Investigation tasks, the problems it solves, and the design decisions behind this enforcement.

## Contents

- [The Problem: Workflow Bypass](#the-problem-workflow-bypass)
- [Root Cause Analysis](#root-cause-analysis)
- [The Solution: Mandatory Enforcement](#the-solution-mandatory-enforcement)
- [Design Decisions](#design-decisions)
- [Impact on User Experience](#impact-on-user-experience)
- [Exceptions: Q&A and Operations](#exceptions-qa-and-operations)

## The Problem: Workflow Bypass

Before March 2026, the recipe runner was presented as "PREFERRED" with documented fallback paths. This led to a critical issue: **LLMs consistently bypassed the 23-step workflow** by taking the simplest path.

### Observed Behavior

When given these options:
- **Option A** (PREFERRED): Run recipe runner with 23 enforced steps
- **Option B**: Invoke skill directly (simpler, fewer steps)
- **Option C**: Direct classification and implementation (simplest)

Claude would consistently choose Option B or C, optimizing for simplicity rather than following the intended workflow.

### Seven Documented Escape Hatches

| # | Location | Escape Hatch | Result |
|---|----------|-------------|--------|
| 1 | dev.md | "PREFERRED when available" | Treated as optional |
| 2 | dev.md | Option B (skill fallback) | Bypass via skill invocation |
| 3 | dev.md | Option C (direct classification) | Complete bypass |
| 4 | dev.md | "strongly preferred" glossary | Weak enforcement signal |
| 5 | SKILL.md | PREFERRED/FALLBACK dual-path | Alternative execution path |
| 6 | SKILL.md | Self-assessed availability check | LLM decides to skip |
| 7 | CLAUDE.md | "without orchestration" override | User-requested bypass |

## Root Cause Analysis

### LLM Optimization Behavior

LLMs are trained to optimize for:
1. **Simplicity**: Fewest steps to accomplish a goal
2. **Directness**: Shortest path from input to output
3. **Efficiency**: Minimal token usage and tool calls

When documentation presents multiple paths, LLMs treat documented fallbacks as **equally valid alternatives** and choose the simplest one.

### Documentation Anti-Pattern

Writing "PREFERRED when available" signals to the LLM:
- This path is optional
- Other paths exist and are documented for a reason
- Evaluate which path is "better" based on the situation

This is exactly the opposite of what we wanted.

## The Solution: Mandatory Enforcement

### Changes Made (PR #2741)

**dev.md**:
- Removed Options B and C entirely
- Changed "PREFERRED" → "REQUIRED"
- Added CRITICAL anti-bypass statement:
  > "The recipe runner is REQUIRED for all Development and Investigation tasks. There are no bypass or fallback paths."

**SKILL.md**:
- Removed FALLBACK section completely
- Single execution path only
- Q&A/Operations tasks still bypass correctly (this is intentional)

**USER_PREFERENCES.md**:
- Added learned pattern with red-flag detection
- Documents the history of bypass attempts
- Provides clear guidance on mandatory enforcement

### Code-Level Enforcement

The recipe runner provides code-level step enforcement:
- Steps execute sequentially in YAML-defined order
- Models cannot skip steps
- Models cannot reorder steps
- Each step must complete before the next begins

This prevents LLMs from:
- Skipping requirements clarification
- Jumping directly to implementation
- Omitting code review
- Bypassing CI/CD integration

## Design Decisions

### Why Not Just Better Prompting?

**Considered**: Adding stronger language like "ALWAYS use recipe runner" or "NEVER bypass the workflow"

**Rejected**: LLMs interpret absolute language ("always", "never") as strong guidance, but when they find documented alternatives, they still optimize for simplicity.

**Lesson**: Documentation structure matters more than word choice. If fallback paths are documented, they will be used.

### Why Single Execution Path?

**Decision**: Remove all documented alternatives, leaving only one way to execute Development/Investigation tasks.

**Rationale**:
- Eliminates choice → eliminates optimization decision
- Clear, unambiguous instructions
- Matches user expectations (consistent behavior)

### Why Keep Q&A and Operations Bypass?

**Decision**: Q&A and Operations tasks intentionally bypass the workflow.

**Rationale**:
- Simple questions don't need 23-step workflows
- Admin commands (git operations, cleanup) should be fast
- User experience: instant answers for simple queries

This is NOT an escape hatch — it's intentional routing based on task classification.

## Impact on User Experience

### Before Enforcement

**User**: `/dev fix the login timeout bug`

**Claude's Decision Tree**:
1. See "PREFERRED when available"
2. Check if recipe runner is "available" (always true)
3. Notice Options B and C exist
4. Optimize: Option C is simplest
5. Execute direct implementation (bypass workflow)

**Result**: Inconsistent behavior, missed steps (no code review, no tests), user confusion.

### After Enforcement

**User**: `/dev fix the login timeout bug`

**Claude's Behavior**:
1. Single execution path: recipe runner
2. No decision to make
3. Execute smart-orchestrator recipe
4. All 23 steps enforced

**Result**: Consistent, predictable behavior. Every Development task follows the same workflow.

### User Perception

**Positive**:
- Predictable behavior
- Consistent quality (all steps executed)
- Clear expectations (always 23 steps)

**Potential Concerns**:
- "Why can't I skip steps for simple tasks?"
- "This seems slower for trivial changes"

**Answer**: Use the appropriate recipe for the task complexity:
- **Simple fixes**: `/fix` command (quick-fix recipe, 4 steps)
- **Medium tasks**: Trimmed custom recipes
- **Full features**: `/dev` with full workflow (22-23 steps)

## Exceptions: Q&A and Operations

### Q&A Tasks

**Classification**: Questions, explanations, documentation lookups

**Behavior**: Bypass workflow entirely, respond directly

**Examples**:
- "What does the circuit breaker pattern do?"
- "Explain how JWT authentication works"
- "Show me the architecture of the auth module"

**Why Bypass**: These tasks don't modify code. Running a 23-step workflow would be wasteful.

### Operations Tasks

**Classification**: Admin commands, git operations, repository management

**Behavior**: Execute directly, skip workflow

**Examples**:
- "Run git status"
- "List all branches"
- "Clean up temporary files"

**Why Bypass**: Operations are typically single-command executions. The workflow is designed for code implementation, not admin tasks.

### How Classification Works

The `dev-orchestrator` classifies each task before routing:

```python
classification = classify_task(user_input)

if classification in ["Q&A", "Operations"]:
    # Respond directly, no workflow
    return execute_directly(user_input)
elif classification in ["Development", "Investigation"]:
    # REQUIRED: use recipe runner
    return run_recipe(smart_orchestrator, context)
```

This classification is intentional and correct. It's not an escape hatch.

## Conclusion

The mandatory recipe runner enforcement solves a critical problem: **consistent, predictable workflow execution for all Development and Investigation tasks**.

By removing documented alternatives and providing a single execution path, we eliminated the LLM's ability to optimize for simplicity and ensured that all implementations follow the same high-quality 23-step process.

This change improves:
- **Consistency**: Every task follows the same workflow
- **Quality**: No skipped steps (code review, testing, CI/CD)
- **Predictability**: Users know exactly what to expect
- **Trust**: The system behaves the same way every time

The recipe runner is not optional. It's the foundation of amplihack's quality guarantee.

---

**Related Documentation**:
- [Dev Orchestrator Tutorial](../tutorials/dev-orchestrator-tutorial.md) - How to use `/dev`
- [Recipe CLI Reference](../reference/recipe-cli-reference.md) - Recipe runner commands
- [DEFAULT_WORKFLOW](../../.claude/workflow/DEFAULT_WORKFLOW.md) - The 23-step process
