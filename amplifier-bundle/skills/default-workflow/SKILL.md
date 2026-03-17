---
name: default-workflow
version: 1.0.0
description: Development workflow for features, bugs, refactoring. Auto-activates for multi-file implementations.
auto_activates:
  - "implement feature spanning multiple files"
  - "complex integration across components"
  - "refactor affecting 5+ files"
explicit_triggers:
  - /ultrathink
  - /amplihack:default-workflow
confirmation_required: true
skip_confirmation_if_explicit: true
token_budget: 4500
---

# Default Workflow Skill

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

This skill provides the standard development workflow for all non-trivial code changes in amplihack. It auto-activates when detecting multi-file implementations, complex integrations, or significant refactoring work.

The workflow defines the canonical execution process: from requirements clarification through design, implementation, testing, review, and merge. It ensures consistent quality by orchestrating specialized agents at each step and enforcing philosophy compliance throughout.

This is a thin wrapper that references the complete workflow definition stored in a single canonical location, ensuring no duplication or drift between the skill interface and the workflow specification.

## Canonical Source

**This skill is a thin wrapper that references the canonical workflow:**

**Source**: `~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md` (471+ lines)

The canonical workflow contains the complete development process with all details, agent specifications, and execution guidance.

## Execution Instructions

When this skill is activated, you MUST:

1. **Read the canonical workflow** immediately:

   ```
   Read(file_path="~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md")
   ```

   Note: Path is relative to project root. Claude Code resolves this automatically.

2. **Follow all steps** exactly as specified in the canonical workflow

3. **Use TodoWrite** to track progress through workflow steps with format:
   - `Step N: [Step Name] - [Specific Action]`
   - Example: `Step 1: Rewrite and Clarify Requirements - Use prompt-writer agent`
   - This helps users track exactly which workflow step is active

4. **Invoke specialized agents** as specified in each workflow step:
   - Step 1: prompt-writer, analyzer, ambiguity agents
   - Step 4: architect, api-designer, database, tester, security agents
   - Step 5: builder, integration agents
   - Step 6: cleanup, optimizer agents
   - Step 7: pre-commit-diagnostic agent
   - Step 9-15: Review and merge agents

## Why This Pattern

**Benefits:**

- Single source of truth for workflow definition
- No content duplication or drift
- Changes to workflow made once in canonical location
- Clear delegation contract between skill and workflow
- Reduced token usage (skill is ~60 lines vs 471+ in canonical source)

## Auto-Activation Triggers

This skill auto-activates for:

- Features spanning multiple files (5+)
- Complex integrations across components
- Refactoring affecting 5+ files
- Any non-trivial code changes requiring structured workflow

## Related Files

- **Canonical Workflow**: `~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md`
- **Command Interface**: `~/.amplihack/.claude/commands/amplihack/ultrathink.md`
- **Orchestrator Skill**: `~/.amplihack/.claude/skills/ultrathink-orchestrator/`
- **Investigation Workflow**: `~/.amplihack/.claude/skills/investigation-workflow/`
