# Power-Steering Configuration Guide

> [Home](../../index.md) > [Features](../README.md) > [Power-Steering](README.md) > Configuration

Complete guide to configuring Power-Steering for your workflow.

## Quick Start

Power-Steering configuration has two levels:

1. **Considerations** (`.claude/tools/amplihack/considerations.yaml`) - What to check
2. **Preferences** (`.claude/context/USER_PREFERENCES.md`) - How to behave

---

## Configuration Files

### considerations.yaml

**Location**: `.claude/tools/amplihack/considerations.yaml`

**Purpose**: Define the 21 considerations that validate session completeness.

**Format**:

```yaml
- id: unique_id
  category: Category Name
  question: What should we check?
  description: Why this matters
  severity: blocker  # or warning
  checker: method_name  # or "generic"
  enabled: true  # or false
```

**See**: [Customization Guide](customization-guide.md) for detailed YAML syntax.

### USER_PREFERENCES.md

**Location**: `.claude/context/USER_PREFERENCES.md`

**Purpose**: Define your workflow preferences that Power-Steering should respect.

**Format**:

```markdown
### YYYY-MM-DD HH:MM:SS

**Preference Title**

Preference description and requirements.

**Implementation Requirements** (optional):
- Detailed requirements
```

---

## Common Configurations

### Configuration 1: Manual PR Approval

**Use case**: You require manual review of all PRs before merge.

**Setup**:

Add to USER_PREFERENCES.md:

```markdown
### 2026-01-23 10:00:00

**NEVER Merge PRs Without Explicit Permission**

NEVER merge PRs or commit directly to main without explicit user permission.
Always create PRs and wait for approval.
```

**Effect**: Power-Steering stops at "PR ready + CI passing", doesn't require merge.

**Learn more**: [How-To: Merge Preferences](../../howto/power-steering-merge-preferences.md)

### Configuration 2: Strict Local Testing

**Use case**: Enforce local testing on every PR (no CI-only testing).

**Setup**:

Add to USER_PREFERENCES.md:

```markdown
### 2026-01-23 10:00:00

**Step 13 Local Testing - NO EXCEPTIONS**

EVERY PR MUST have local testing completed. Step 13 in DEFAULT_WORKFLOW.md
is MANDATORY and cannot be skipped through rationalization.

**Implementation Requirements:**

- MUST execute at least 2 test scenarios (1 simple + 1 complex) locally
- MUST document test results in PR description
- MUST verify no regressions before committing
```

**Effect**: Power-Steering validates local testing evidence in PR description.

### Configuration 3: Relaxed Workflow (Warnings Only)

**Use case**: Less strict checking for exploratory or prototyping work.

**Setup**:

Modify considerations.yaml:

```yaml
# Change all blockers to warnings
- id: tests_written
  severity: warning  # Changed from blocker

- id: ci_status
  severity: warning  # Changed from blocker

# Keep only critical blockers
- id: zero_bs_compliance
  severity: blocker  # Keep as blocker
```

**Effect**: Power-Steering provides guidance but doesn't block session end.

**Warning**: Use sparingly - reduces quality enforcement.

### Configuration 4: Custom Team Requirements

**Use case**: Add team-specific checks (security review, compliance, etc.).

**Setup**:

Add to considerations.yaml:

```yaml
- id: security_review
  category: Code Quality & Philosophy Compliance
  question: Has the security team reviewed this change for sensitive code?
  description: Ensures security team sign-off for authentication, authorization, or data handling changes
  severity: blocker
  checker: generic  # Uses keyword matching
  enabled: true

- id: compliance_checklist
  category: Session Completion & Progress
  question: Has the compliance checklist been completed for this feature?
  description: Validates regulatory compliance requirements documented
  severity: warning
  checker: generic
  enabled: true
```

**Effect**: Power-Steering checks for keywords like "security review", "compliance checklist" in session transcript.

---

## Preference Configuration

### USER_PREFERENCES.md Format

 Power-Steering reads USER_PREFERENCES.md to detect workflow preferences.

**Standard format**:

```markdown
### YYYY-MM-DD HH:MM:SS

**Preference Title**

Preference statement with MANDATORY keywords.

**Implementation Requirements:**

- Specific requirement 1
- Specific requirement 2
```

### Supported Preferences

| Preference | Keywords Required | Effect |
|------------|-------------------|--------|
| Never Merge Without Permission | NEVER, Merge, PR, Without, Permission | Stops at PR ready state |
| Always Test Locally | Step 13, MANDATORY, Local Testing | Enforces Step 13 evidence |
| No Direct Commits to Main | NEVER, commit, main, without permission | Validates PR workflow used |

### Adding New Preferences

1. **Write preference** in USER_PREFERENCES.md with clear keywords
2. **Test detection** by checking Power-Steering logs
3. **Verify behavior** matches expectation
4. **Document** in team onboarding

**Example**:

```markdown
### 2026-01-23 10:00:00

**Always Include Test Plan in PR Description**

EVERY PR MUST include a "Test Plan" section describing manual testing performed.

**Implementation Requirements:**

- Test Plan section must exist in PR description
- At least 2 test scenarios documented
- Expected results specified
```

 Future versions will support this preference automatically.

---

## Consideration Configuration

### Enable/Disable Considerations

**Disable a consideration**:

```yaml
- id: workflow_followed
  enabled: false  # Disabled
```

**Use cases**:

- Temporarily disable during prototyping
- Disable team-specific checks not relevant to your workflow
- Troubleshoot false positives

### Change Severity Levels

**Convert blocker to warning**:

```yaml
- id: pr_description_complete
  severity: warning  # Changed from blocker
```

**Use cases**:

- Less critical checks become advisory
- Reduce friction during exploration
- Gradual enforcement rollout

**Warning**: Too many warnings reduce effectiveness.

### Custom Checker Methods

**Use specific checker** (requires code):

```yaml
- id: custom_check
  checker: _check_custom_requirement
```

**Requirements**:

- Method must exist in `power_steering_checker.py`
- Method signature: `def _check_custom_requirement(self) -> CheckResult`
- Returns `CheckResult` with satisfied, details, evidence

**Use generic checker** (no code required):

```yaml
- id: custom_check
  question: Has the custom requirement been documented in DOCS.md?
  checker: generic
```

**How it works**:

1. Extracts keywords from question: "custom", "requirement", "documented", "DOCS.md"
2. Searches session transcript for keywords
3. Returns satisfied if keywords found, unsatisfied otherwise

### Custom Categories

Add new category:

```yaml
- id: new_check
  category: Custom Category Name
  question: Custom check question?
  description: What this checks
  severity: blocker
  checker: generic
  enabled: true
```

Categories are free-form - use any name that makes sense for your team.

---

## Configuration Examples

### Example 1: High-Quality Workflow

**Goal**: Maximum quality enforcement, manual approval required.

**considerations.yaml**:

```yaml
# All quality checks as blockers
- id: zero_bs_compliance
  severity: blocker

- id: tests_written
  severity: blocker

- id: local_testing_completed
  severity: blocker

- id: pr_description_complete
  severity: blocker

- id: ci_status
  severity: blocker
```

**USER_PREFERENCES.md**:

```markdown
**NEVER Merge PRs Without Explicit Permission**

**Step 13 Local Testing - NO EXCEPTIONS**
```

**Result**: Strictest enforcement, highest quality PRs.

### Example 2: Exploratory Workflow

**Goal**: Guidance without blocking, fast iteration.

**considerations.yaml**:

```yaml
# Most checks as warnings
- id: tests_written
  severity: warning

- id: pr_description_complete
  severity: warning

# Keep only critical blockers
- id: ci_status
  severity: blocker  # Still require CI passing
```

**USER_PREFERENCES.md**:

```markdown
# No additional preferences - use defaults
```

**Result**: Fast iteration with safety net for critical issues.

### Example 3: Team Collaboration

**Goal**: Team-specific requirements, balanced enforcement.

**considerations.yaml**:

```yaml
# Standard checks as blockers
- id: tests_written
  severity: blocker

- id: ci_status
  severity: blocker

# Custom team checks
- id: design_review_completed
  category: Session Completion & Progress
  question: Has the design been reviewed by the architecture team?
  description: Ensures architectural alignment for significant changes
  severity: warning
  checker: generic
  enabled: true

- id: api_contract_documented
  category: PR Content & Quality
  question: Is the API contract documented in the PR?
  description: Validates API changes include contract documentation
  severity: blocker
  checker: generic
  enabled: true
```

**USER_PREFERENCES.md**:

```markdown
**NEVER Merge PRs Without Explicit Permission**

**API Changes Require Architecture Review**

All API changes MUST be reviewed by architecture team before merge.
```

**Result**: Team-specific workflow with quality enforcement.

---

## Testing Configuration

### Validate Preferences

Test if preference detected:

```bash
# Check preference keywords present
grep -i "never.*merge.*without.*permission" .claude/context/USER_PREFERENCES.md

# Expected: Line matching the preference
```

### Test Considerations

Run Power-Steering manually:

```python
# In Python REPL
from amplihack.hooks.power_steering_checker import PowerSteeringChecker

checker = PowerSteeringChecker()
result = checker.check_consideration("ci_status")

print(f"Satisfied: {result.satisfied}")
print(f"Details: {result.details}")
print(f"Evidence: {result.evidence}")
```

### Debug Logging

Enable debug logging:

```bash
# Set environment variable
export AMPLIHACK_LOG_LEVEL=DEBUG

# Launch Claude
amplihack claude
```

**Log output**:

```
DEBUG: Reading considerations.yaml
DEBUG: Loaded 21 considerations
DEBUG: Reading USER_PREFERENCES.md
DEBUG: Detected preference: NEVER Merge Without Permission
DEBUG: Using no-auto-merge CI check
DEBUG: CI check satisfied (PR ready, awaiting user approval)
```

---

## Configuration Best Practices

### Start Conservative

1. Use default considerations first
2. Observe where friction occurs
3. Customize gradually based on real usage
4. Document why each change was made

### Team Alignment

1. **Document preferences**: Write team-specific preferences in onboarding docs
2. **Review regularly**: Quarterly review of configuration effectiveness
3. **Track metrics**: Monitor PR quality, review cycles, CI failures
4. **Iterate**: Adjust based on data and feedback

### Avoid Over-Configuration

**Warning signs**:

- Too many custom considerations (>30 total)
- Everything is a blocker (reduces trust)
- Everything is a warning (reduces effectiveness)
- Complex detection logic (hard to maintain)

**Better approach**:

- Focus on 3-5 critical requirements per team
- Balance blockers (5-10) and warnings (5-10)
- Use generic checker for custom checks
- Keep detection simple and clear

---

## Troubleshooting Configuration

### Preference Not Detected

**Diagnosis**:

```bash
# Check file exists
ls -la .claude/context/USER_PREFERENCES.md

# Check content
cat .claude/context/USER_PREFERENCES.md
```

**Solutions**:

1. Verify file location correct
2. Check keywords present (see [Merge Preferences](../../howto/power-steering-merge-preferences.md))
3. Restart Claude session (preferences read on initialization)

### Consideration Not Running

**Diagnosis**:

Check enabled status:

```bash
# Search for consideration ID
grep -A 5 "id: consideration_id" .claude/tools/amplihack/considerations.yaml
```

**Solutions**:

1. Set `enabled: true`
2. Verify YAML syntax valid (use YAML validator)
3. Check checker method exists (if using specific checker)

### False Positives

**Diagnosis**:

Review evidence:

```
❌ Check Failed: Tests not written

Evidence:
- No pytest output found
- No test files in tests/ directory
```

**Solutions**:

1. Fix the actual issue (write tests)
2. If false positive, adjust detection logic
3. Change severity to warning if check too strict
4. Disable temporarily if blocking valid work

---

## Advanced Configuration

### Conditional Checks

 Some considerations only apply in specific contexts:

```yaml
- id: workflow_followed
  enabled_when: DEFAULT_WORKFLOW_ACTIVE
  # Only checks if DEFAULT_WORKFLOW was used

- id: investigation_documented
  enabled_when: INVESTIGATION_SESSION
  # Only checks during investigation sessions
```

**Note**: Context detection is automatic based on session transcript.

### Precedence Rules

Configuration precedence (highest to lowest):

1. USER_PREFERENCES.md (user-specific)
2. considerations.yaml (project-specific)
3. Default considerations (framework defaults)

**Example**:

- Default: Require PR merge
- USER_PREFERENCES.md: NEVER merge without permission
- **Result**: Preference overrides default

### Version Control

**Recommendation**: Track configuration in git:

```bash
# Track considerations.yaml
git add .claude/tools/amplihack/considerations.yaml

# DO NOT track USER_PREFERENCES.md (personal)
# Already in .gitignore
```

**Team workflow**:

1. Standard considerations.yaml in repo
2. Individual USER_PREFERENCES.md per developer
3. Document standard preferences in onboarding

---

## Migration Guide

### From No Configuration

**Before**: Using default Power-Steering behavior

**After**: Custom configuration

**Steps**:

1. Copy default considerations.yaml: `cp .claude/tools/amplihack/considerations.yaml.default .claude/tools/amplihack/considerations.yaml`
2. Review each consideration, adjust as needed
3. Add preferences to USER_PREFERENCES.md
4. Test with a simple PR workflow
5. Iterate based on feedback

### From v0.9.1 to v0.10.0

**Changes**:

- Added: USER_PREFERENCES.md preference awareness
- Added: Merge preference detection
- No breaking changes to considerations.yaml

**Migration**:

1. Update Power-Steering code (automatic)
2. Add preferences to USER_PREFERENCES.md (optional)
3. Test merge preference behavior
4. No configuration changes required

---

## Related Documentation

### User Guides

- [Power-Steering Overview](README.md) - Feature overview
- [How-To: Merge Preferences](../../howto/power-steering-merge-preferences.md) - Configure merge approval
- [Customization Guide](customization-guide.md) - Detailed YAML customization
- [Troubleshooting](troubleshooting.md) - Fix common issues

### Technical References

- [Technical Reference: Merge Preferences](../../reference/power-steering-merge-preferences.md) - Developer docs
- [considerations.yaml Schema](../../reference/considerations-schema.md) - Complete YAML reference (coming soon)
- [USER_PREFERENCES.md Reference](../../reference/user-preferences.md) - Complete preferences reference

---

## FAQ

**Q: Do I need to restart Claude after changing configuration?**

A: considerations.yaml: No (loaded on each check). USER_PREFERENCES.md: Yes (read on session start).

**Q: Can I have different configurations per project?**

A: Yes. considerations.yaml is per-project. USER_PREFERENCES.md is per-project but can reference global preferences.

**Q: What if my team uses Azure DevOps instead of GitHub?**

A: Power-Steering uses platform-bridge for cross-platform support. Most checks work on both platforms.

**Q: Can I disable Power-Steering for specific sessions?**

A: Not recommended. Better to use warning-only severity for less critical checks.

---

**Ready to customize?** Start with [Customization Guide](customization-guide.md) for detailed YAML syntax and examples.
