# Quality Audit Workflow - Working Examples

Practical examples demonstrating quality audit workflow execution.

---

## Basic Examples

### Example 1: Simple Quality Audit

**User Request**:

```
User: "Run a quality audit on this codebase"
```

**Skill Activation**:

```
quality-audit-workflow: *activates automatically*
"Beginning comprehensive quality audit of your codebase..."
```

**Execution Flow**:

```
Phase 1: Project Familiarization
├── Exploring project structure...
├── Found 12 modules in src/
├── Mapped 45 dependencies
└── Identified 3 existing TODO markers

Phase 2: Parallel Quality Audit
├── Division: src/core/ (4 agents running)
├── Division: src/api/ (4 agents running)
├── Division: src/utils/ (4 agents running)
└── Consolidated 18 findings

Phase 3: Issue Assembly
├── Created issue #101: [AUDIT] high: Complex auth module
├── Created issue #102: [AUDIT] medium: Dead code in utils
├── Created issue #103: [AUDIT] medium: Missing error handling
└── 3 issues created

Phase 4: Parallel PR Generation
├── worktrees/fix-issue-101 → PR #201
├── worktrees/fix-issue-102 → PR #202
├── worktrees/fix-issue-103 → PR #203
└── 3 PRs created

Phase 5: PM Review
├── Priority 1: PR #202 (no dependencies)
├── Priority 2: PR #203 (no dependencies)
├── Priority 3: PR #201 (complex, review carefully)
└── Recommended merge sequence: #202 → #203 → #201

Phase 6: Master Report
└── Created master issue #104 with full report
```

**Output**:

```
Quality Audit Complete!

Summary:
- 12 modules analyzed
- 18 findings discovered
- 3 issues created
- 3 PRs generated

Master Report: https://github.com/org/repo/issues/104

Recommended Actions:
1. Review and merge PR #202 (trivial dead code removal)
2. Review and merge PR #203 (error handling improvement)
3. Carefully review PR #201 (auth module refactor)
```

---

### Example 2: Targeted Audit (Specific Directory)

**User Request**:

```
User: "Audit only the authentication module for security issues"
```

**Execution**:

```
Phase 1: Familiarization (scoped to src/auth/)
└── Analyzing authentication module...

Phase 2: Parallel Audit (security-focused)
├── security agent: Found 2 issues
├── analyzer agent: Found 1 complexity issue
└── reviewer agent: Found 1 philosophy violation

Phase 3: Issues
├── #201: SQL injection vulnerability in login
├── #202: Hardcoded timeout values
├── #203: Auth module exceeds 500 LOC
└── #204: Missing rate limiting

Phase 4-6: PRs and Report
└── 4 PRs generated, master report created
```

---

### Example 3: Philosophy-Focused Audit

**User Request**:

```
User: "Check if our codebase follows the ruthless simplicity philosophy"
```

**Execution**:

```
Phase 2: Agents focus on philosophy checks

Findings:
├── src/utils/helpers.py: 12 unused utility functions (dead code)
├── src/api/router.py: Over-abstracted routing layer
├── src/models/base.py: Future-proofing for unsupported databases
├── src/services/cache.py: Premature optimization (unused cache)
└── src/core/factory.py: Abstract factory pattern overkill

Issues Created:
├── #301: Remove 12 dead utility functions
├── #302: Simplify routing abstraction
├── #303: Remove unused database adapters
├── #304: Remove premature cache optimization
└── #305: Replace factory with direct instantiation

Philosophy Score: 62/100 (needs improvement)
```

---

## Advanced Examples

### Example 4: Large Codebase Audit (Parallel at Scale)

**User Request**:

```
User: "Full audit of our monorepo with 50+ services"
```

**Configuration**:

```
AUDIT_PARALLEL_LIMIT=8  # Default: 8 concurrent worktrees
AUDIT_SEVERITY_THRESHOLD=medium  # Skip low/info findings
```

**Execution Strategy**:

```
Phase 1: Familiarization
├── Scanning 50 service directories...
├── Total: 50 services, 1200 modules, 150K LOC
└── Division strategy: service-by-service

Phase 2: Parallel Audit (batched)
├── Batch 1: services/auth, services/users, services/payments...
├── Batch 2: services/notifications, services/analytics...
├── ...
└── Batch 7: services/legacy-1, services/legacy-2...

Findings Summary:
├── Critical: 3
├── High: 12
├── Medium: 45
└── Total actionable: 60 issues

Phase 4: Parallel PR Generation (batched)
├── Wave 1: 8 PRs (no conflicts)
├── Wave 2: 8 PRs (no conflicts)
├── ...
└── Wave 8: 4 PRs (remaining)

Master Report:
├── 60 issues created
├── 60 PRs generated
├── Estimated review time: 8 hours
└── Recommended: Start with critical/high (15 PRs)
```

---

### Example 5: Audit with Custom Severity Threshold

**User Request**:

```
User: "Only show me critical and high severity issues,
       we'll deal with medium/low later"
```

**Configuration**:

```
AUDIT_SEVERITY_THRESHOLD=high
```

**Result**:

```
Findings (filtered to high+ only):
├── CRITICAL: SQL injection in user input handling
├── CRITICAL: Exposed API keys in config
├── HIGH: Auth bypass in admin routes
├── HIGH: Memory leak in event handler
├── HIGH: Race condition in payment processing
└── 5 issues created (vs 45 unfiltered)

Note: 40 medium/low findings logged but not issued.
Run with AUDIT_SEVERITY_THRESHOLD=medium to include them.
```

---

## Output Format Examples

### Sample GitHub Issue

````markdown
## Quality Audit Finding

**Severity**: high
**Category**: architecture
**Location**: `src/auth/authenticator.py:45-180`

## Problem

The Authenticator class violates single responsibility principle
with 135 lines handling authentication, session management,
token refresh, AND audit logging.

## Philosophy Violation

**Principle**: Ruthless Simplicity - Single Responsibility
**Violation**: One class doing 4 distinct jobs

## Evidence

```python
class Authenticator:
    def authenticate(self, ...): ...      # Lines 45-80
    def manage_session(self, ...): ...    # Lines 81-110
    def refresh_tokens(self, ...): ...    # Lines 111-145
    def log_audit_event(self, ...): ...   # Lines 146-180
```
````

## Recommended Fix

Split into 4 focused classes:

1. `Authenticator` - authentication only
2. `SessionManager` - session handling
3. `TokenRefresher` - token operations
4. `AuditLogger` - audit trail

## Impact

- **Risk**: Changes to any functionality affect all others
- **Effort**: moderate (refactor to 4 files, update imports)

## Agent Analysis

| Agent    | Finding                                   |
| -------- | ----------------------------------------- |
| analyzer | Cyclomatic complexity: 24 (should be <10) |
| reviewer | Violates brick philosophy                 |
| patterns | God class anti-pattern detected           |

````

---

### Sample Pull Request

```markdown
## Fixes #456

## Summary

Split monolithic Authenticator into 4 focused modules following
brick philosophy.

## Changes

- `src/auth/authenticator.py`: Now handles only authentication (35 LOC)
- `src/auth/session_manager.py`: New - session handling (30 LOC)
- `src/auth/token_refresher.py`: New - token operations (35 LOC)
- `src/auth/audit_logger.py`: New - audit logging (25 LOC)
- `src/auth/__init__.py`: Updated exports

## Testing

- [x] Existing auth tests pass
- [x] Added unit tests for each new module
- [x] Integration tests verify modules work together
- [x] Manual login flow tested

## Philosophy Checklist

- [x] Each module has single responsibility
- [x] No module exceeds 50 LOC
- [x] Clear public APIs defined
- [x] Zero code duplication

## Before/After

| Metric | Before | After |
|--------|--------|-------|
| LOC per module | 135 | 31 avg |
| Complexity | 24 | 4 avg |
| Responsibilities | 4 | 1 each |

---
*Audit PR - Review with context of issue #456*
````

---

### Sample Master Report

```markdown
# Codebase Quality Audit Report

**Date**: 2025-11-25
**Scope**: src/, lib/, tests/
**Duration**: 45 minutes

## Executive Summary

Audit identified 23 issues across 4 severity levels.
Primary concerns are in authentication (3 critical) and
data processing (2 high). Overall philosophy compliance
is 71/100.

## Statistics

| Metric           | Value |
| ---------------- | ----- |
| Modules Analyzed | 45    |
| Issues Found     | 23    |
| Critical         | 3     |
| High             | 5     |
| Medium           | 10    |
| Low              | 5     |
| PRs Generated    | 18    |

## Related Issues

- #101 [CRITICAL] SQL injection vulnerability
- #102 [CRITICAL] Exposed credentials
- #103 [CRITICAL] Auth bypass
- #104 [HIGH] Memory leak
- #105 [HIGH] Race condition
- ... (18 more)

## Related PRs

| PR   | Issue | Status | Priority |
| ---- | ----- | ------ | -------- |
| #201 | #101  | Draft  | 1        |
| #202 | #102  | Draft  | 2        |
| #203 | #103  | Draft  | 3        |
| ...  | ...   | ...    | ...      |

## Priority Action Plan

### Immediate (This Sprint)

1. #101 → #201: Fix SQL injection
2. #102 → #202: Remove exposed credentials
3. #103 → #203: Fix auth bypass

### Short Term (Next Sprint)

4. #104 → #204: Fix memory leak
5. #105 → #205: Fix race condition

### Long Term (Backlog)

6-23. Medium/Low issues

## Merge Sequence
```

#202 (no deps) ─┐
#203 (no deps) ─┼─→ #201 (depends on credential cleanup)
│
#204 (no deps) ─┘

```

## Recommendations

### Architecture
- Consider extracting auth into separate service
- Implement proper dependency injection

### Security
- Add input validation layer
- Implement rate limiting
- Set up secret scanning in CI

### Performance
- Profile and fix memory leaks before scale
- Add caching strategically (not prematurely)

---
*Generated by quality-audit-workflow*
```

---

## Integration Patterns

### Pattern 1: Scheduled Audits

Run weekly quality audits:

```bash
# In CI/CD or cron
claude-code --skill quality-audit-workflow \
  --prompt "Weekly quality audit" \
  --env AUDIT_SEVERITY_THRESHOLD=high
```

### Pattern 2: Pre-Release Audit

Before major releases:

```bash
claude-code --skill quality-audit-workflow \
  --prompt "Pre-release security and quality audit for v2.0"
```

### Pattern 3: New Developer Onboarding

Help new devs understand codebase:

```
"Run a quality audit but don't create issues -
just generate the familiarization report"
```

---

## Troubleshooting

### Issue: Too Many Low-Value Issues

**Symptom**: 100+ issues created for minor style issues

**Fix**:

```
AUDIT_SEVERITY_THRESHOLD=medium
```

### Issue: Worktree Creation Fails

**Symptom**: "fatal: worktree already exists"

**Fix**:

```bash
# Clean up old worktrees
git worktree prune
rm -rf worktrees/fix-issue-*
```

### Issue: Agents Timeout on Large Files

**Symptom**: "Task timeout" on 5000+ LOC files

**Fix**: Flag as finding rather than analyzing

```
# Module too large to analyze effectively
# Create issue: "Module exceeds analyzable size limit"
```

---

**Last Updated**: 2025-11-25
