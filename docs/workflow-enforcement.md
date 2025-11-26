# Workflow Enforcement

Every task must be classified into a workflow before execution. No exceptions.

## Contents

- [Overview](#overview)
- [Classification Rules](#classification-rules)
- [Workflow Types](#workflow-types)
- [Migration from /ultrathink](#migration-from-ultrathink)
- [Troubleshooting](#troubleshooting)

## Overview

Workflow enforcement ensures consistent, appropriate handling of all tasks. Instead of treating every request as a complex implementation project, tasks are routed to the right workflow based on their nature.

**Why this exists:**

- Simple questions do not need 13-step workflows
- Investigations need exploration, not implementation gates
- Code changes need structure and validation

## Classification Rules

Before starting any task, classify it into exactly one workflow:

| Task Type    | Workflow               | Examples                                   |
| ------------ | ---------------------- | ------------------------------------------ |
| Questions    | Q&A_WORKFLOW           | "What does X do?", "How does Y work?"      |
| Exploration  | INVESTIGATION_WORKFLOW | "Why is this failing?", "Map the codebase" |
| Code changes | DEFAULT_WORKFLOW       | "Add feature X", "Fix bug Y", "Refactor Z" |

### Decision Tree

```
Is this a question that can be answered without code changes?
├── YES → Q&A_WORKFLOW
└── NO → Does this require exploration/research before implementation?
    ├── YES → INVESTIGATION_WORKFLOW
    └── NO → DEFAULT_WORKFLOW
```

### Classification Examples

**Q&A_WORKFLOW:**

- "What is the brick philosophy?"
- "How do I run tests?"
- "What workflows are available?"
- "Explain how agents work"

**INVESTIGATION_WORKFLOW:**

- "Why is CI failing?"
- "How is authentication implemented?"
- "Map the dependencies in this module"
- "Find all usages of function X"

**DEFAULT_WORKFLOW:**

- "Add dark mode support"
- "Fix the login bug"
- "Refactor the API module"
- "Update dependencies"

## Workflow Types

### Q&A_WORKFLOW

Minimal 3-step workflow for simple questions.

**Steps:**

1. Understand the question
2. Gather information (read files, search docs)
3. Provide clear answer

**Location:** `.claude/workflow/Q&A_WORKFLOW.md`

**When to use:** Questions answerable without modifying code.

### INVESTIGATION_WORKFLOW

Structured exploration for research and diagnosis.

**Steps:**

1. Clarify scope
2. Discover and map
3. Deep dive analysis
4. Verify understanding
5. Synthesize findings
6. Optional: create persistent docs

**Location:** `.claude/workflow/INVESTIGATION_WORKFLOW.md`

**When to use:** Understanding existing systems, diagnosing issues, researching before implementation.

### DEFAULT_WORKFLOW

Full development workflow for code changes.

**Steps:** 13 steps including planning, implementation, testing, and PR creation.

**Location:** `.claude/workflow/DEFAULT_WORKFLOW.md`

**When to use:** Any task that modifies code.

## Migration from /ultrathink

The `/ultrathink` command is deprecated. Workflow classification replaces it.

### What Changed

| Before                      | After                              |
| --------------------------- | ---------------------------------- |
| `/ultrathink "question"`    | Classify as Q&A_WORKFLOW           |
| `/ultrathink "investigate"` | Classify as INVESTIGATION_WORKFLOW |
| `/ultrathink "implement"`   | Classify as DEFAULT_WORKFLOW       |

### Key Differences

1. **Automatic routing**: No command needed. Classification happens automatically.
2. **Lighter workflows**: Simple tasks get simple workflows.
3. **Same power**: DEFAULT_WORKFLOW still uses full agent orchestration.

### Deprecated Files

These files are kept for backward compatibility but should not be used:

- `.claude/commands/amplihack/ultrathink.md`
- `.claude/skills/ultrathink-orchestrator/SKILL.md`
- `.claude/skills/default-workflow/SKILL.md`

## Troubleshooting

### Wrong workflow selected

**Problem:** Task routed to wrong workflow.

**Solution:** Explicitly state the workflow type:

```
This is a code change task. Use DEFAULT_WORKFLOW.
```

### Task spans multiple workflows

**Problem:** Task needs investigation AND implementation.

**Solution:** Execute sequentially:

1. Run INVESTIGATION_WORKFLOW first
2. Then run DEFAULT_WORKFLOW with findings

### Simple task getting full workflow

**Problem:** Quick fix treated as major feature.

**Solution:** Classify explicitly:

```
Quick question: How do I configure X?
```

### Complex task getting minimal workflow

**Problem:** Major feature treated as simple question.

**Solution:** Mention code changes:

```
I need to implement X (code changes required).
```
