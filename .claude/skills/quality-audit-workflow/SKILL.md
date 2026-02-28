---
name: quality-audit-workflow
description: Comprehensive codebase quality audit with parallel agent orchestration, GitHub issue creation, automated PR generation per issue, and PM-prioritized recommendations. Use for code review, refactoring audits, technical debt analysis, module quality assessment, or codebase health checks.
source_urls:
  - https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
---

# Quality Audit Workflow

## Purpose

Orchestrates a systematic, parallel quality audit of any codebase with automated remediation through PR generation and PM-prioritized recommendations.

## When I Activate

I automatically load when you mention:

- "quality audit" or "code audit"
- "codebase review" or "full code review"
- "refactoring opportunities" or "technical debt audit"
- "module quality check" or "architecture review"
- "parallel analysis" with multiple agents

## What I Do

Execute a 7-phase workflow that:

1. **Familiarizes** with the project (investigation phase)
2. **Audits** using parallel agents across codebase divisions
3. **Creates** GitHub issues for each discovered problem
   3.5. **Validates** against recent PRs (prevents false positives)
4. **Generates** PRs in parallel worktrees per remaining issues
5. **Reviews** PRs with PM architect for prioritization
6. **Reports** consolidated recommendations in master issue

## Quick Start

```
User: "Run a quality audit on this codebase"
Skill: *activates automatically*
       "Beginning quality audit workflow..."
```

## The 7 Phases

### Phase 1: Project Familiarization

- Run investigation workflow on project structure
- Map modules, dependencies, and entry points
- Understand existing patterns and architecture

### Phase 2: Parallel Quality Audit

- Divide codebase into logical sections
- Deploy multiple agent types per section (analyzer, reviewer, security, optimizer)
- Apply PHILOSOPHY.md standards ruthlessly
- Check module size, complexity, single responsibility

### Phase 3: Issue Assembly

- Create GitHub issue for each finding
- Include severity, location, recommendation
- Tag with appropriate labels
- Add unique IDs, keywords, and file metadata

### Phase 3.5: Post-Audit Validation [NEW]

- Scan merged PRs from last 30 days (configurable)
- Calculate confidence scores for PR-issue matches
- Auto-close high-confidence matches (≥90%)
- Tag medium-confidence matches (70-89%) for verification
- Add bidirectional cross-references between issues and PRs
- Target: <5% false positive rate

### Phase 4: Parallel PR Generation

- Create worktree per remaining open issue (`worktrees/fix-issue-XXX`)
- Run DEFAULT_WORKFLOW.md in each worktree
- Generate fix PR for each confirmed open issue

### Phase 5: PM Review

- Invoke pm-architect skill
- Group PRs by category and priority
- Identify dependencies between fixes

### Phase 6: Master Report

- Create master GitHub issue
- Link all related issues and PRs
- Prioritized action plan with recommendations

## Philosophy Enforcement

This workflow ruthlessly applies:

- **Ruthless Simplicity**: Flag over-engineered modules
- **Module Size Limits**: Target <300 LOC per module
- **Single Responsibility**: One purpose per brick
- **Zero-BS**: No stubs, no TODOs, no dead code

## Navigation Guide

### When to Read Supporting Files

**reference.md** - Read when you need:

- Detailed phase execution steps
- Agent-to-phase mappings
- Codebase division strategies
- Issue template formats

**examples.md** - Read when you need:

- Working audit examples
- Sample issue/PR formats
- Real-world usage patterns
- Output format examples

## Seek/Validate/Fix/Recurse Loop (v2.0)

The quality-audit-cycle recipe now supports automatic recursion:

```
Cycle 1: SEEK → VALIDATE → FIX → decision
Cycle 2: SEEK → VALIDATE → FIX → decision  (if fixes were applied)
Cycle 3: SEEK → VALIDATE → FIX → decision  (if fixes were applied)
...until clean pass or max_cycles reached
```

**Key features:**

- Each finding is independently validated before fixing (prevents false positives)
- Findings marked as false positives are skipped
- The loop stops when no fixes are applied (clean pass) or max_cycles is reached
- Each cycle reports: issues found, validated, fixed, remaining

**Run via recipe:**

```bash
amplihack recipe execute quality-audit-cycle.yaml --context '{"target_path": "src/amplihack", "max_cycles": "3"}'
```

## Configuration

Override defaults via environment or prompt:

**Core Settings**:

- `AUDIT_PARALLEL_LIMIT`: Max concurrent worktrees (default: 8)
- `AUDIT_SEVERITY_THRESHOLD`: Minimum severity to create issue (default: medium)
- `AUDIT_MODULE_LOC_LIMIT`: Flag modules exceeding this LOC (default: 300)

**Recurse Loop Settings** (v2.0):

- `max_cycles`: Maximum audit cycles before stopping (default: 3)
- `validation_threshold`: Minimum validators that must agree (default: 2)

**Phase 3.5 Validation Settings**:

- `AUDIT_PR_SCAN_DAYS`: Days to scan for recent PRs (default: 30)
- `AUDIT_AUTO_CLOSE_THRESHOLD`: Confidence % for auto-close (default: 90)
- `AUDIT_TAG_THRESHOLD`: Confidence % for tagging (default: 70)
- `AUDIT_ENABLE_VALIDATION`: Enable Phase 3.5 (default: true)
