# Quality Audit Workflow - Complete Reference

Detailed documentation for executing comprehensive codebase quality audits.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Phase 1: Project Familiarization](#phase-1-project-familiarization)
3. [Phase 2: Parallel Quality Audit](#phase-2-parallel-quality-audit)
4. [Phase 3: Issue Assembly](#phase-3-issue-assembly)
5. [Phase 3.5: Post-Audit Validation](#phase-35-post-audit-validation)
6. [Phase 4: Parallel PR Generation](#phase-4-parallel-pr-generation)
7. [Phase 5: PM Review](#phase-5-pm-review)
8. [Phase 6: Master Report](#phase-6-master-report)
9. [Agent Mappings](#agent-mappings)
10. [Codebase Division Strategies](#codebase-division-strategies)
11. [Issue & PR Templates](#issue--pr-templates)

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
│  Phase 3.5: Post-Audit Validation (Sequential) [NEW]            │
│    └── scan PRs → score confidence → auto-close/tag issues      │
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

## Phase 3.5: Post-Audit Validation

**Objective**: Detect and close child issues already fixed in recent PRs to prevent false positives

### Overview

After creating child issues in Phase 3, Phase 3.5 scans merged PRs from the last 30 days (configurable) that reference the parent issue. It analyzes each PR's changes against child issues using confidence scoring, then automatically closes high-confidence matches or tags medium-confidence matches for verification.

**Why This Phase Exists**:

- Prevents false positive child issues (target: <5% false positive rate)
- Detects PRs that fixed problems but only referenced parent issue
- Reduces duplicate work for developers
- Maintains accurate issue tracking

**Performance**: Runs in <2 minutes for typical audits (10 issues, 5 PRs scanned)

### Step 3.5.1: PR Discovery

Scan for merged PRs referencing the parent audit issue:

```bash
# Find PRs that mention the audit report issue
gh pr list --state merged --search "audit in:title,body" --json number,title,files,body --limit 50

# Filter to last N days (default: 30)
CUTOFF_DATE=$(date -d '30 days ago' +%Y-%m-%d)

# Get PRs with file changes and descriptions
for pr_number in "${pr_numbers[@]}"; do
    gh pr view "$pr_number" --json files,body,createdAt
done
```

**Discovery Criteria**:

- PR state: merged
- PR age: within last 30 days (configurable via `AUDIT_PR_SCAN_DAYS`)
- PR mentions: references parent audit issue in title or body
- PR files: has file changes available

### Step 3.5.2: Confidence Scoring

Match each child issue against PR changes using a multi-factor confidence algorithm:

```python
def calculate_confidence_score(issue: dict, pr: dict) -> float:
    """
    Calculate confidence that PR fixed this issue.

    Returns: 0.0-100.0 (percentage confidence)
    """
    score = 0.0
    max_score = 100.0

    # Factor 1: File path match (40 points)
    issue_files = set(issue.get("files", []))
    pr_files = set(pr.get("changed_files", []))

    if issue_files & pr_files:  # Intersection
        file_match_ratio = len(issue_files & pr_files) / len(issue_files)
        score += 40.0 * file_match_ratio

    # Factor 2: Keyword match (30 points)
    issue_keywords = set(issue.get("keywords", []))
    pr_body = pr.get("body", "").lower()
    pr_title = pr.get("title", "").lower()
    pr_text = f"{pr_title} {pr_body}"

    matched_keywords = sum(1 for kw in issue_keywords if kw.lower() in pr_text)
    if issue_keywords:
        keyword_ratio = matched_keywords / len(issue_keywords)
        score += 30.0 * keyword_ratio

    # Factor 3: Issue reference (20 points)
    issue_number = issue.get("number")
    if f"#{issue_number}" in pr_text or f"issue {issue_number}" in pr_text.lower():
        score += 20.0

    # Factor 4: Category match (10 points)
    issue_category = issue.get("category", "").lower()
    if issue_category and issue_category in pr_text:
        score += 10.0

    return min(score, max_score)
```

**Confidence Thresholds**:

- **≥90%**: High confidence - auto-close issue
- **70-89%**: Medium confidence - tag "needs-verification"
- **<70%**: Low confidence - no action

### Step 3.5.3: Issue State Management

Apply three-tier action system based on confidence scores:

```bash
# High confidence (≥90%): Auto-close
if (( $(echo "$confidence >= 90.0" | bc -l) )); then
    gh issue close "$issue_number" --comment "$(cat <<EOF
Automatically closed - detected as fixed in PR #${pr_number}

**Confidence Score**: ${confidence}%

**Matching Factors**:
- File match: ${file_match}
- Keyword match: ${keyword_match}
- Direct reference: ${direct_ref}

**PR Summary**: ${pr_title}

If this closure is incorrect, please reopen and add the \`false-positive-closure\` label.
EOF
)"

    # Add cross-reference labels
    gh issue edit "$issue_number" --add-label "auto-closed,fixed-in-pr-${pr_number}"
fi

# Medium confidence (70-89%): Tag for verification
if (( $(echo "$confidence >= 70.0 && $confidence < 90.0" | bc -l) )); then
    gh issue comment "$issue_number" --body "$(cat <<EOF
⚠️ **Verification Needed**

This issue may have been fixed in PR #${pr_number}

**Confidence Score**: ${confidence}%

**Matching Factors**:
- File match: ${file_match}
- Keyword match: ${keyword_match}

**Action Required**: Please review PR #${pr_number} and:
- If fixed: Close this issue and reference the PR
- If not fixed: Remove the \`needs-verification\` label and proceed with implementation

EOF
)"

    gh issue edit "$issue_number" --add-label "needs-verification,possibly-fixed-pr-${pr_number}"
fi

# Low confidence (<70%): No action, issue remains open
```

**State Transitions**:

```
Child Issue Created (Phase 3)
    ↓
Confidence Scoring (Phase 3.5)
    ↓
    ├─ ≥90% → Auto-closed with comment
    ├─ 70-89% → Tagged "needs-verification"
    └─ <70% → Remains open
```

### Step 3.5.4: Bidirectional Cross-Referencing

Create bidirectional links between issues and PRs for future prevention:

**In Child Issues** (via template updates):

````markdown
## Cross-Reference Instructions

**To prevent future false positives**, when fixing this issue:

1. Reference this specific issue number in your PR: `Fixes #${issue_number}`
2. Use the unique ID in commit messages: `audit-${category}-${key_term}`
3. Tag PR with: `audit-fix,${category}`

**Unique ID**: `audit-${category}-${key_term}`
**Keywords**: `${keyword_list}`
**Files**: `${file_list}`
````

**In PR Comments** (auto-added by Phase 3.5):

```markdown
## Audit Cross-Reference

This PR may have addressed quality audit findings:

- Issue #123 (90% confidence) - [auto-closed]
- Issue #124 (75% confidence) - [needs verification]

**For future reference**: Use unique IDs in commit messages to improve matching accuracy.
```

### Step 3.5.5: Validation Reporting

Generate summary report of validation results:

```markdown
# Phase 3.5: Post-Audit Validation Report

**Scan Window**: Last 30 days
**PRs Scanned**: 5 merged PRs
**Child Issues**: 10 created

## Validation Results

| Issue | Confidence | Action         | PR     | Reason                    |
| ----- | ---------- | -------------- | ------ | ------------------------- |
| #101  | 95%        | Auto-closed    | #201   | File + keyword + ref      |
| #102  | 92%        | Auto-closed    | #202   | File + keyword match      |
| #103  | 91%        | Auto-closed    | #203   | File + ref + category     |
| #104  | 78%        | Needs-verify   | #204   | File match only           |
| #105  | 45%        | Remains open   | -      | Low confidence            |
| #106  | 12%        | Remains open   | -      | No match                  |
| #107  | 0%         | Remains open   | -      | No PR found               |
| #108  | 0%         | Remains open   | -      | No PR found               |
| #109  | 0%         | Remains open   | -      | No PR found               |
| #110  | 0%         | Remains open   | -      | No PR found               |

## Summary

- **Auto-closed**: 3 issues (30%)
- **Needs verification**: 1 issue (10%)
- **Remaining open**: 6 issues (60%)
- **False positive rate**: <5% (target met)

## Next Steps

1. Review "needs-verification" issues manually
2. Proceed to Phase 4 with 6 remaining open issues
3. Generate PRs only for confirmed open issues
```

### Step 3.5.6: Transition to Phase 4

Prepare for PR generation with validated issue list:

```python
# Filter to only open issues after validation
validated_open_issues = [
    issue for issue in child_issues
    if issue["state"] == "open" and "auto-closed" not in issue["labels"]
]

# Pass to Phase 4
print(f"Proceeding to Phase 4 with {len(validated_open_issues)} confirmed issues")
```

**Transition Criteria**:

- Validation report generated
- Auto-closed issues confirmed
- Needs-verification issues tagged
- Open issue list updated
- Ready for worktree creation (Phase 4)

### Configuration Options

Control Phase 3.5 behavior via environment variables:

```bash
# Days to scan for recent PRs (default: 30)
export AUDIT_PR_SCAN_DAYS=30

# Confidence threshold for auto-close (default: 90.0)
export AUDIT_AUTO_CLOSE_THRESHOLD=90.0

# Confidence threshold for tagging (default: 70.0)
export AUDIT_TAG_THRESHOLD=70.0

# Enable/disable Phase 3.5 (default: true)
export AUDIT_ENABLE_VALIDATION=true
```

**Recommended Settings**:

- **Conservative**: `AUTO_CLOSE_THRESHOLD=95.0` (fewer auto-closures, more verification)
- **Balanced**: `AUTO_CLOSE_THRESHOLD=90.0` (default, tested threshold)
- **Aggressive**: `AUTO_CLOSE_THRESHOLD=85.0` (more auto-closures, review verification tags)

### Error Handling

Phase 3.5 uses graceful degradation:

```python
try:
    # Attempt PR discovery
    merged_prs = scan_merged_prs(parent_issue, days=30)
except GitHubAPIError as e:
    print(f"Warning: Could not scan PRs ({e}). Skipping Phase 3.5.")
    print("All issues will proceed to Phase 4.")
    return child_issues  # Continue without validation

try:
    # Attempt confidence scoring
    for issue in child_issues:
        confidence = calculate_confidence_score(issue, merged_prs)
except Exception as e:
    print(f"Warning: Confidence scoring failed ({e}). Using conservative approach.")
    # Proceed with all issues open (no auto-closures)
```

**Failure Modes**:

- **GitHub API unavailable**: Skip Phase 3.5, proceed to Phase 4 with all issues
- **Confidence scoring error**: Conservative approach (no auto-closures)
- **Issue update failure**: Log error, continue with remaining issues

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
**Unique ID**: `audit-{category}-{key-term}`

## Problem

{Clear description of what's wrong}

## Philosophy Violation

**Principle**: {which PHILOSOPHY.md principle}
**Violation**: {how it's violated}

## Evidence

```{language}
{code snippet showing the problem}
```

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

## Metadata (for Phase 3.5)

**Keywords**: `{comma-separated list of key terms}`
**Files**: `{comma-separated list of affected files}`

## Cross-Reference Instructions

**To prevent future false positives**, when fixing this issue:

1. Reference this specific issue number in your PR: `Fixes #{issue_number}`
2. Use the unique ID in commit messages: `audit-{category}-{key-term}`
3. Tag PR with: `audit-fix,{category}`

This helps Phase 3.5 auto-detect fixes in future audits.
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
