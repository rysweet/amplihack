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

### Example 6: Phase 3.5 False Positive Prevention

**User Request**:

```
User: "Run quality audit, but check for duplicate work first"
```

**Skill Activation**:

```
quality-audit-workflow: *activates automatically*
"Beginning quality audit with Phase 3.5 validation enabled..."
```

**Execution Flow**:

```
Phase 1: Familiarization
└── Exploring project structure... (completed)

Phase 2: Parallel Audit
└── 10 findings discovered across 3 divisions

Phase 3: Issue Assembly
├── Created issue #101: [AUDIT] high: Complex auth module
├── Created issue #102: [AUDIT] medium: Dead code in utils
├── Created issue #103: [AUDIT] medium: Missing error handling
├── Created issue #104: [AUDIT] medium: Over-abstracted router
├── Created issue #105: [AUDIT] low: Inconsistent naming
├── Created issue #106: [AUDIT] medium: Hardcoded config
├── Created issue #107: [AUDIT] high: SQL injection risk
├── Created issue #108: [AUDIT] medium: Memory leak in handler
├── Created issue #109: [AUDIT] low: Missing docstrings
└── Created issue #110: [AUDIT] medium: Duplicate logic
└── 10 issues created with unique IDs and metadata

Phase 3.5: Post-Audit Validation [NEW]
├── Scanning merged PRs from last 30 days...
├── Found 5 PRs that reference audit work
├── PR #201: "fix: Improve authentication module" (merged 10 days ago)
├── PR #202: "refactor: Remove unused utility functions" (merged 15 days ago)
├── PR #203: "fix: Add error handling to API routes" (merged 20 days ago)
├── PR #204: "refactor: Simplify routing layer" (merged 5 days ago)
├── PR #205: "chore: Standardize variable naming" (merged 25 days ago)
│
├── Calculating confidence scores...
│   ├── Issue #101 vs PR #201: 95% (file match + keywords + reference)
│   ├── Issue #102 vs PR #202: 92% (file match + keywords)
│   ├── Issue #103 vs PR #203: 91% (file match + reference + category)
│   ├── Issue #104 vs PR #204: 78% (file match only)
│   ├── Issue #105 vs PR #205: 45% (keyword match only)
│   └── Issues #106-110: 0% (no matches)
│
├── Applying actions based on thresholds...
│   ├── Issue #101: AUTO-CLOSED (95% ≥ 90%)
│   ├── Issue #102: AUTO-CLOSED (92% ≥ 90%)
│   ├── Issue #103: AUTO-CLOSED (91% ≥ 90%)
│   ├── Issue #104: TAGGED needs-verification (78% in 70-89% range)
│   └── Issues #105-110: Remain open (< 70%)
│
└── Validation complete: 3 auto-closed, 1 tagged, 6 remain open
```

**Phase 3.5 Validation Report**:

```markdown
# Phase 3.5: Post-Audit Validation Report

**Scan Window**: Last 30 days
**PRs Scanned**: 5 merged PRs
**Child Issues**: 10 created

## Validation Results

| Issue | Confidence | Action         | PR   | Reason                |
| ----- | ---------- | -------------- | ---- | --------------------- |
| #101  | 95%        | Auto-closed    | #201 | File+keyword+ref      |
| #102  | 92%        | Auto-closed    | #202 | File+keyword          |
| #103  | 91%        | Auto-closed    | #203 | File+ref+category     |
| #104  | 78%        | Needs-verify   | #204 | File match only       |
| #105  | 45%        | Remains open   | -    | Low confidence        |
| #106  | 0%         | Remains open   | -    | No PR found           |
| #107  | 0%         | Remains open   | -    | No PR found           |
| #108  | 0%         | Remains open   | -    | No PR found           |
| #109  | 0%         | Remains open   | -    | No PR found           |
| #110  | 0%         | Remains open   | -    | No PR found           |

## Summary

- **Auto-closed**: 3 issues (30%)
- **Needs verification**: 1 issue (10%)
- **Remaining open**: 6 issues (60%)
- **False positive rate**: 3% (target <5% met ✅)

## Confidence Score Breakdown

**High Confidence Auto-Closures** (≥90%):

- **Issue #101 (95%)**: Auth module complexity
  - File match: `src/auth/authenticator.py` (40 pts)
  - Keywords: "authentication", "complexity", "refactor" (28 pts)
  - Direct reference: "Fixes issue mentioned in audit report" (20 pts)
  - Category: "architecture" in PR body (7 pts)

- **Issue #102 (92%)**: Dead code in utils
  - File match: `src/utils/helpers.py` (40 pts)
  - Keywords: "unused", "dead code", "cleanup" (30 pts)
  - Direct reference: None (0 pts)
  - Category: "quality" in PR title (10 pts)
  - Note: PR #202 removed exactly the 12 functions flagged in audit

- **Issue #103 (91%)**: Missing error handling
  - File match: `src/api/routes.py` (40 pts)
  - Keywords: "error handling", "try-catch", "exceptions" (25 pts)
  - Direct reference: "Addresses audit feedback" (20 pts)
  - Category: "quality" in PR labels (6 pts)

**Medium Confidence Verification** (70-89%):

- **Issue #104 (78%)**: Over-abstracted router
  - File match: `src/api/router.py` (40 pts)
  - Keywords: "routing", "simplify" (18 pts)
  - Direct reference: None (0 pts)
  - Category: "architecture" in PR body (10 pts)
  - Note: PR #204 simplified routing, but unclear if it addressed audit's specific concerns

## Next Steps

1. **Manual Review**: Check issue #104 (needs-verification) against PR #204
   - If fixed: Close #104 with reference to PR #204
   - If not fixed: Remove "needs-verification" label, proceed to Phase 4

2. **Proceed to Phase 4**: Generate PRs for 6 confirmed open issues (#105-110)

3. **Monitor**: Track false positive closure rate (currently 0/3 = 0%)
```

**Auto-Closed Issue Comment Example** (Issue #101):

```markdown
Automatically closed - detected as fixed in PR #201

**Confidence Score**: 95%

**Matching Factors**:

- ✅ File match: `src/auth/authenticator.py` in both issue and PR
- ✅ Keyword match: "authentication", "complexity", "refactor"
- ✅ Direct reference: PR body mentions "audit report"
- ✅ Category match: "architecture" in both

**PR Summary**: "fix: Improve authentication module - split into focused classes"

**Verification**: PR #201 split the 135-line Authenticator class into 4 focused modules (exactly as recommended in this audit finding).

If this closure is incorrect, please reopen and add the `false-positive-closure` label.

---

_Auto-closed by Phase 3.5: Post-Audit Validation_
```

**Needs-Verification Issue Comment Example** (Issue #104):

```markdown
⚠️ **Verification Needed**

This issue may have been fixed in PR #204

**Confidence Score**: 78%

**Matching Factors**:

- ✅ File match: `src/api/router.py`
- ⚠️ Keyword match: Partial ("routing", "simplify" found, but not all terms)
- ❌ Direct reference: PR doesn't reference this specific issue
- ✅ Category match: "architecture"

**Why verification needed**: PR #204 simplified routing, but it's unclear if the changes address the specific over-abstraction concerns raised in this audit finding.

**Action Required**: Please review PR #204 and:

- If fixed: Close this issue with comment: `Closes #104. Fixed in PR #204`
- If not fixed: Remove the `needs-verification` label and this issue will proceed to Phase 4 for PR generation

**PR Link**: https://github.com/org/repo/pull/204

---

_Tagged by Phase 3.5: Post-Audit Validation_
```

**Output Summary**:

```
Phase 3.5 Validation Complete!

Summary:
- 10 child issues created
- 5 recent PRs scanned
- 3 issues auto-closed (high confidence ≥90%)
- 1 issue tagged for verification (70-89%)
- 6 issues remain open for Phase 4

False Positive Prevention:
- Prevented 3 duplicate PRs (30% reduction)
- False positive rate: 3% (target <5% met)
- Estimated time saved: 2-3 hours of duplicate work

Proceeding to Phase 4 with 6 confirmed open issues...
```

**Developer Experience Benefits**:

1. **No Duplicate Work**: Developer would have wasted time creating PRs for #101-103
2. **Clear Guidance**: Issue #104 tagged for quick manual check (5 min vs 30 min to implement)
3. **Accurate Tracking**: Only genuine issues (#105-110) proceed to Phase 4
4. **Learning Loop**: Cross-reference instructions help prevent false positives in future audits

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
