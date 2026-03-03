# Quality Audit Workflow - Complete Reference

Detailed documentation for executing comprehensive codebase quality audits.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Phase 1: Project Familiarization](#phase-1-project-familiarization)
3. [Phase 2: Parallel Quality Audit](#phase-2-parallel-quality-audit)
4. [Phase 3: Issue Assembly](#phase-3-issue-assembly)
5. [Phase 4: Parallel PR Generation](#phase-4-parallel-pr-generation)
6. [Phase 5: PM Review](#phase-5-pm-review)
7. [Phase 6: Master Report](#phase-6-master-report)
8. [Agent Mappings](#agent-mappings)
9. [Codebase Division Strategies](#codebase-division-strategies)
10. [Issue & PR Templates](#issue--pr-templates)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUALITY AUDIT WORKFLOW                       │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1: Familiarization (Sequential)                          │
│    └── investigation-workflow → project understanding           │
├─────────────────────────────────────────────────────────────────┤
│  Phase 2: Parallel Audit                                        │
│    ├── Division A ─┬─ analyzer ─┬─ findings                     │
│    │               ├─ reviewer  │                               │
│    │               ├─ security  │                               │
│    │               └─ optimizer ┘                               │
│    ├── Division B ─┬─ analyzer ─┬─ findings                     │
│    │               ├─ reviewer  │                               │
│    │               └─ patterns  ┘                               │
│    └── Division N...                                            │
├─────────────────────────────────────────────────────────────────┤
│  Phase 3: Issue Assembly (Sequential)                           │
│    └── findings → deduplicate → create GitHub issues            │
├─────────────────────────────────────────────────────────────────┤
│  Phase 4: Parallel PR Generation                                │
│    ├── Issue #1 → worktree → DEFAULT_WORKFLOW → PR #1           │
│    ├── Issue #2 → worktree → DEFAULT_WORKFLOW → PR #2           │
│    └── Issue #N...                                              │
├─────────────────────────────────────────────────────────────────┤
│  Phase 5: PM Review (Sequential)                                │
│    └── pm-architect → prioritize → group → dependencies         │
├─────────────────────────────────────────────────────────────────┤
│  Phase 6: Master Report (Sequential)                            │
│    └── create master issue → link all → recommendations         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Project Familiarization

**Objective**: Deep understanding of project before audit

**Execution**:

```
Task(subagent_type="Explore", prompt="""
Thoroughly explore this codebase:
1. Identify all modules and their responsibilities
2. Map dependencies between components
3. Document entry points and public APIs
4. Identify patterns and conventions used
5. Note any existing technical debt markers (TODOs, FIXMEs)
Return: Structured project map for quality audit
""")
```

**Key Outputs**:

- Project structure map
- Module dependency graph
- Pattern inventory
- Existing debt markers

**Duration**: 5-15 minutes depending on codebase size

**Transition Criteria**: Project map complete, ready to divide for audit

---

## Phase 2: Parallel Quality Audit

**Objective**: Multi-perspective analysis of each codebase division

### Step 2.1: Divide Codebase

Use one of these division strategies (see [Codebase Division Strategies](#codebase-division-strategies)):

```python
# By directory (most common)
divisions = ["src/core/", "src/api/", "src/utils/", "tests/"]

# By module type
divisions = ["models/", "views/", "controllers/", "services/"]

# By feature
divisions = ["auth/", "payments/", "notifications/", "analytics/"]
```

### Step 2.2: Deploy Parallel Agents Per Division

For EACH division, run these agents IN PARALLEL:

```
# All agents run simultaneously on each division
Task(subagent_type="analyzer", prompt="Analyze {division} for complexity, coupling, cohesion...")
Task(subagent_type="reviewer", prompt="Review {division} against PHILOSOPHY.md standards...")
Task(subagent_type="security", prompt="Audit {division} for security vulnerabilities...")
Task(subagent_type="optimizer", prompt="Identify performance issues in {division}...")
Task(subagent_type="patterns", prompt="Check {division} for pattern compliance and anti-patterns...")
```

### Step 2.3: Philosophy Checks

Each agent MUST evaluate against PHILOSOPHY.md:

**Ruthless Simplicity Checks**:

- [ ] Module has single, clear responsibility
- [ ] No unnecessary abstractions
- [ ] No future-proofing code
- [ ] Minimal dependencies

**Module Quality Checks**:

- [ ] LOC < 300 (flag if exceeded)
- [ ] Cyclomatic complexity < 10
- [ ] Clear public API (studs)
- [ ] Self-contained (brick)

**Zero-BS Checks**:

- [ ] No stubs or placeholders
- [ ] No dead code
- [ ] No swallowed exceptions
- [ ] No TODO/FIXME in production code

### Step 2.4: Consolidate Findings

```python
findings = {
    "critical": [],    # Security, data loss risks
    "high": [],        # Architecture violations
    "medium": [],      # Code quality issues
    "low": [],         # Style/convention issues
    "info": []         # Suggestions for improvement
}
```

---

## Phase 3: Issue Assembly

**Objective**: Create actionable GitHub issues from findings

### Step 3.1: Deduplicate Findings

Multiple agents may flag the same issue. Merge duplicates:

```python
# Group by file + line range
# Merge findings with >80% overlap
# Preserve all perspectives in merged issue
```

### Step 3.2: Create Issues

For each unique finding at severity >= threshold:

```bash
gh issue create \
  --title "[AUDIT] {severity}: {brief description}" \
  --body "$(cat <<'EOF'
## Quality Audit Finding

**Severity**: {severity}
**Location**: {file}:{lines}
**Category**: {category}

## Problem

{detailed description}

## Philosophy Violation

{which principle is violated and how}

## Recommended Fix

{specific actionable recommendation}

## Agent Perspectives

- **Analyzer**: {analysis}
- **Reviewer**: {review}
- **Security**: {security notes}

---
*Generated by quality-audit-workflow*
EOF
)" \
  --label "audit,{severity},{category}"
```

### Step 3.3: Track Issues

Maintain mapping for Phase 4:

```python
issue_map = {
    "issue-123": {"file": "src/auth.py", "severity": "high"},
    "issue-124": {"file": "src/utils.py", "severity": "medium"},
    # ...
}
```

---

## Phase 4: Parallel PR Generation

**Objective**: Fix each issue via parallel worktree workflows

### Step 4.1: Create Worktrees

For each issue (up to AUDIT_PARALLEL_LIMIT):

```bash
# Create worktree for issue
git worktree add ./worktrees/fix-issue-{number} -b fix/audit-issue-{number}
cd ./worktrees/fix-issue-{number}
```

### Step 4.2: Execute DEFAULT_WORKFLOW Per Worktree

Each worktree runs the full workflow:

```
Task(subagent_type="builder", prompt="""
Working in worktree for issue #{number}:

ISSUE CONTEXT:
{issue body}

EXECUTION:
1. Follow DEFAULT_WORKFLOW.md steps 5-14
2. Implement fix for this specific issue
3. Ensure fix doesn't break other functionality
4. Write/update tests as needed
5. Create PR linked to issue #{number}

CONSTRAINTS:
- Focus ONLY on this issue
- Minimal changes (surgical fix)
- Follow philosophy principles
""")
```

### Step 4.3: PR Creation

Each worktree creates its PR:

```bash
gh pr create \
  --title "fix: [AUDIT-{number}] {brief description}" \
  --body "$(cat <<'EOF'
## Fixes #{issue_number}

## Summary
{what was changed}

## Changes
- {change 1}
- {change 2}

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual verification complete

## Philosophy Compliance
- [ ] Ruthless simplicity maintained
- [ ] No new technical debt
- [ ] Zero-BS implementation

---
*Generated by quality-audit-workflow*
EOF
)" \
  --draft
```

---

## Phase 5: PM Review

**Objective**: Prioritize and group PRs for efficient review/merge

### Step 5.1: Invoke PM Architect

```
Skill(skill="pm-architect")

Task: Review all audit PRs and provide:
1. Priority ordering (which to merge first)
2. Grouping by category
3. Dependency analysis (which PRs must merge before others)
4. Risk assessment for each PR
5. Recommended merge sequence
```

### Step 5.2: Generate Priority Matrix

```markdown
| Priority | PR   | Issue | Risk   | Dependencies |
| -------- | ---- | ----- | ------ | ------------ |
| 1        | #201 | #123  | Low    | None         |
| 2        | #202 | #124  | Medium | #201         |
| 3        | #203 | #125  | High   | #201, #202   |
```

### Step 5.3: Identify Merge Conflicts

Check for PRs that modify same files:

```bash
# For each pair of PRs, check file overlap
gh pr diff {pr1} --name-only > pr1_files.txt
gh pr diff {pr2} --name-only > pr2_files.txt
comm -12 pr1_files.txt pr2_files.txt  # Files in both
```

---

## Phase 6: Master Report

**Objective**: Consolidated findings and recommendations

### Step 6.1: Create Master Issue

```bash
gh issue create \
  --title "[AUDIT REPORT] Codebase Quality Audit - {date}" \
  --body "$(cat <<'EOF'
# Codebase Quality Audit Report

**Date**: {date}
**Scope**: {directories audited}
**Duration**: {time taken}

## Executive Summary

{high-level findings}

## Statistics

| Metric | Value |
|--------|-------|
| Modules Analyzed | {count} |
| Issues Found | {total} |
| Critical | {critical} |
| High | {high} |
| Medium | {medium} |
| Low | {low} |
| PRs Generated | {pr_count} |

## Related Issues

{list of all created issues with links}

## Related PRs

{list of all created PRs with links and status}

## Priority Action Plan

### Immediate (Critical/High)
1. {issue + PR}
2. {issue + PR}

### Short Term (Medium)
1. {issue + PR}
2. {issue + PR}

### Long Term (Low/Info)
1. {issue}
2. {issue}

## Recommendations

### Architecture
{recommendations}

### Code Quality
{recommendations}

### Security
{recommendations}

### Performance
{recommendations}

## Merge Sequence

{recommended order with rationale}

---
*Generated by quality-audit-workflow*
EOF
)" \
  --label "audit-report,tracking"
```

---

## Agent Mappings

| Phase | Agent               | Purpose                             |
| ----- | ------------------- | ----------------------------------- |
| 1     | Explore             | Project structure discovery         |
| 1     | analyzer            | Existing code understanding         |
| 2     | analyzer            | Complexity and coupling analysis    |
| 2     | reviewer            | Philosophy compliance check         |
| 2     | security            | Vulnerability scanning              |
| 2     | optimizer           | Performance bottleneck detection    |
| 2     | patterns            | Pattern/anti-pattern identification |
| 2     | philosophy-guardian | Ruthless simplicity validation      |
| 4     | builder             | Fix implementation                  |
| 4     | tester              | Test generation                     |
| 4     | cleanup             | Post-fix simplification             |
| 5     | pm-architect        | PR prioritization                   |

---

## Codebase Division Strategies

### Strategy 1: Directory-Based (Default)

Best for: Monorepos, standard project layouts

```python
divisions = glob("src/*/") + glob("lib/*/")
```

### Strategy 2: Module-Type-Based

Best for: MVC/MVVM architectures

```python
divisions = ["models/", "views/", "controllers/", "services/", "utils/"]
```

### Strategy 3: Feature-Based

Best for: Feature-sliced architectures

```python
divisions = ["features/auth/", "features/payments/", "features/users/"]
```

### Strategy 4: Layer-Based

Best for: Clean architecture, hexagonal

```python
divisions = ["domain/", "application/", "infrastructure/", "presentation/"]
```

### Strategy 5: Complexity-Based

Best for: Large codebases, targeted audits

```python
# Audit only highest-complexity modules first
divisions = get_modules_by_complexity(threshold=10)
```

---

## Issue & PR Templates

### Issue Template

````markdown
## Quality Audit Finding

**Severity**: {critical|high|medium|low|info}
**Category**: {security|architecture|performance|quality|style}
**Location**: `{file}:{start_line}-{end_line}`

## Problem

{Clear description of what's wrong}

## Philosophy Violation

**Principle**: {which PHILOSOPHY.md principle}
**Violation**: {how it's violated}

## Evidence

```{language}
{code snippet showing the problem}
```
````

## Recommended Fix

{Specific, actionable steps to fix}

## Impact

- **Risk**: {what could go wrong if not fixed}
- **Effort**: {estimated fix complexity: trivial|simple|moderate|complex}

## Agent Analysis

| Agent    | Finding |
| -------- | ------- |
| analyzer | {notes} |
| reviewer | {notes} |
| security | {notes} |

````

### PR Template

```markdown
## Fixes #{issue_number}

## Summary

{One-line description of fix}

## Changes

- `{file}`: {what changed}
- `{file}`: {what changed}

## Testing

- [ ] Existing tests pass
- [ ] New tests added for fix
- [ ] Manual verification complete

## Philosophy Checklist

- [ ] No new abstractions added
- [ ] No future-proofing
- [ ] Minimal change surface
- [ ] Zero-BS implementation

## Screenshots

{if UI changes}

---
*Audit PR - Review with context of issue #{issue_number}*
````

---

## Troubleshooting

### Too Many Issues Created

**Problem**: Audit creates hundreds of low-value issues

**Solution**: Increase severity threshold

```
AUDIT_SEVERITY_THRESHOLD=high
```

### Worktree Conflicts

**Problem**: Multiple worktrees modify same files

**Solution**: Use PM review to identify and sequence conflicting PRs

### Agent Timeout

**Problem**: Large divisions cause agent timeouts

**Solution**: Further subdivide large directories

```python
# Instead of "src/" use "src/auth/", "src/api/", etc.
```

---

**Last Updated**: 2025-11-25
