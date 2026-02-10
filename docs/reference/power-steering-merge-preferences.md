# Power-Steering Merge Preference Awareness - Technical Reference

> [Home](../index.md) > [Reference](../reference/README.md) > Power-Steering Merge Preferences

Technical documentation for the Power-Steering merge preference awareness feature.

## Overview

Power-Steering respects the USER_PREFERENCES.md setting "NEVER Merge PRs Without Permission". When active, it treats "PR ready + CI passing + awaiting user approval" as a valid completion state, rather than requiring PR merge.

**Key Components**:

- Detection: `_user_prefers_no_auto_merge()` method
- Validation: `_check_ci_status_no_auto_merge()` method
- Integration: `_check_ci_status()` method modification
- Location: `.claude/tools/amplihack/hooks/power_steering_checker.py`

---

## Architecture

### Component Overview

```
[Power-Steering Checker]
         |
         v
[_check_ci_status()] -----> reads USER_PREFERENCES.md
         |
         v
[_user_prefers_no_auto_merge()] -----> regex detection
         |
    yes /   \ no
       /     \
      v       v
[_check_ci_status_no_auto_merge()]  [standard CI check]
      |                                      |
      v                                      v
"PR ready + CI passing"              "PR must be merged"
```

### Design Principles

1. **Fail-Open**: Errors default to standard behavior, never falsely satisfy
2. **Non-Invasive**: No changes to considerations.yaml required
3. **User-Centric**: Respects explicit user preferences
4. **Robust**: Handles missing files, regex errors, PR status failures

---

## API Reference

### Detection Method

```python
def _user_prefers_no_auto_merge(self) -> bool:
    """
    Detect if user has set preference to never auto-merge PRs.

    Reads USER_PREFERENCES.md and searches for the pattern:
    "NEVER ... Merge ... PR ... Without ... Permission"

    Returns:
        bool: True if preference detected, False otherwise

    Behavior:
        - Case-insensitive regex matching
        - Handles multiline preferences
        - Fail-open: returns False on any error
        - File path: .claude/context/USER_PREFERENCES.md

    Examples:
        Detected patterns:
        - "NEVER Merge PRs Without Permission"
        - "NEVER merge pull requests without explicit permission"
        - "Never Merge PRs or Commit Without Explicit Permission"

        Not detected:
        - "Never commit without permission" (missing "merge" + "PR")
        - "NEVER auto-merge" (missing "without permission")
    """
```

**Implementation Notes**:

- Regex pattern: `r'NEVER.*(?:Merge|merge).*(?:PR|Pull Request).*(?:Without|without).*(?:Permission|permission)'`
- Uses `re.IGNORECASE` and `re.DOTALL` flags
- Returns `False` on `FileNotFoundError`, `IOError`, `re.error`
- Logs errors at WARNING level (does not raise)

### Validation Method

```python
def _check_ci_status_no_auto_merge(self) -> CheckResult:
    """
    Validate CI status WITHOUT requiring PR merge.

    Checks:
        1. PR exists and is open
        2. CI checks are passing
        3. PR is ready for review (not draft)

    Returns:
        CheckResult: Satisfied if PR ready + CI passing, else Unsatisfied

    Success Criteria:
        - PR found via gh CLI
        - PR state is "OPEN"
        - CI status is "SUCCESS" or all checks passing
        - Not in draft state

    Failure Modes:
        - No PR found → Unsatisfied ("No PR found")
        - CI checks failing → Unsatisfied ("CI checks failing")
        - gh CLI error → Unsatisfied (error message)

    Example Success Output:
        CheckResult(
            satisfied=True,
            details="PR #123 ready (CI passing, awaiting user approval)",
            evidence=["gh pr view output"]
        )
    """
```

**Implementation Notes**:

- Uses `gh pr view` to fetch PR status
- Parses JSON response for `statusCheckRollup` and `state`
- Does NOT check `mergeable` or `merged` status
- Collects evidence: PR number, CI status, review state

### Integration Method

```python
def _check_ci_status(self) -> CheckResult:
    """
    Check CI status with preference awareness.

    Flow:
        1. Call _user_prefers_no_auto_merge()
        2. If True: call _check_ci_status_no_auto_merge()
        3. If False: use standard CI check logic

    Returns:
        CheckResult: Result from appropriate checker method

    Behavior:
        - Transparent to caller
        - No changes to CheckResult format
        - Maintains backward compatibility
    """
```

---

## Data Structures

### CheckResult

```python
@dataclass
class CheckResult:
    """Result of a Power-Steering consideration check."""

    satisfied: bool
    """Whether the check passed."""

    details: str
    """Human-readable explanation of result."""

    evidence: List[str] = field(default_factory=list)
    """Supporting evidence (command outputs, file contents)."""

    error: Optional[str] = None
    """Error message if check failed due to error."""
```

**Usage in Preference Awareness**:

```python
# Success case
CheckResult(
    satisfied=True,
    details="PR #123 ready for review (CI passing, awaiting user approval)",
    evidence=[
        "gh pr view output",
        "CI status: SUCCESS",
        "Review state: APPROVED"
    ]
)

# Failure case
CheckResult(
    satisfied=False,
    details="CI checks still running",
    evidence=["gh pr view output"],
    error=None
)

# Error case
CheckResult(
    satisfied=False,
    details="Failed to check PR status",
    evidence=[],
    error="gh CLI not authenticated"
)
```

---

## File Paths

### USER_PREFERENCES.md

**Location**: `.claude/context/USER_PREFERENCES.md`

**Format**:

```markdown
### YYYY-MM-DD HH:MM:SS

**Preference Title**

Preference description. Must include keywords:

- NEVER
- Merge (or merge)
- PR (or Pull Request)
- Without (or without)
- Permission (or permission)

**Implementation Requirements** (optional):

- Additional details
```

**Example**:

```markdown
### 2026-01-23 10:00:00

**NEVER Merge PRs or Commit Directly Without Explicit Permission**

NEVER merge PRs or commit directly to main without explicit user permission.
Always create PRs and wait for approval. Only the first explicitly approved
merge applies - subsequent PRs require separate approval.

**Implementation Requirements:**

- MUST create PR and wait for user to say "merge" or "please merge"
- MUST ask for permission for EACH PR merge separately
```

### Power-Steering Checker

**Location**: `.claude/tools/amplihack/hooks/power_steering_checker.py`

**Class**: `PowerSteeringChecker`

**Modified Methods**:

- `_check_ci_status()` - Entry point, delegates based on preference
- `_user_prefers_no_auto_merge()` - Detection logic (NEW)
- `_check_ci_status_no_auto_merge()` - Validation logic (NEW)

---

## Integration Points

### Lazy Detection Design

Preference detection occurs **during each `_check_ci_status()` call**, not at initialization:

```python
# In _check_ci_status()
if self._user_prefers_no_auto_merge():
    return self._check_ci_status_no_auto_merge()
else:
    # Standard CI check logic
    return self._check_ci_status_standard()
```

> **⚙️ Design Rationale: Lazy Detection**
>
> Power-Steering reads `USER_PREFERENCES.md` during each CI check rather than at initialization. This design provides:
>
> 1. **Zero Startup Overhead**: No file I/O during hook initialization
> 2. **Dynamic Updates**: Preference changes take effect immediately without restart
> 3. **Fail-Open Safety**: If `USER_PREFERENCES.md` is temporarily unavailable, the system continues with standard behavior
> 4. **Resilience**: Detection errors never prevent CI validation
>
> The file read overhead (<1ms) is negligible compared to `gh` CLI network calls (100-500ms).

**Key Behaviors**:

- Preference state is NOT cached between checks
- Changes to `USER_PREFERENCES.md` are detected on next check
- No restart required when adding/removing preference
- File read errors default to standard behavior (fail-open)

### gh CLI Integration

Uses GitHub CLI to fetch PR status:

```bash
# Command executed
gh pr view --json state,statusCheckRollup,isDraft

# Expected JSON response
{
  "state": "OPEN",
  "isDraft": false,
  "statusCheckRollup": [
    {"state": "SUCCESS", "context": "ci/test"},
    {"state": "SUCCESS", "context": "ci/lint"}
  ]
}
```

**Requirements**:

- `gh` CLI installed and in PATH
- Authenticated: `gh auth status` succeeds
- Repository has GitHub remote configured

**Fallback**: If `gh` CLI unavailable, check falls back to standard behavior.

---

## Error Handling

### Error Scenarios

| Error Type       | Trigger                      | Behavior                      | User Impact                       |
| ---------------- | ---------------------------- | ----------------------------- | --------------------------------- |
| File not found   | USER_PREFERENCES.md missing  | Return `False` from detection | Standard CI check runs            |
| Read error       | Permission denied, I/O error | Return `False` from detection | Standard CI check runs            |
| Regex error      | Invalid pattern (unlikely)   | Return `False` from detection | Standard CI check runs            |
| gh CLI missing   | `gh` not in PATH             | Return unsatisfied            | User notified to install gh       |
| gh CLI auth fail | Not authenticated            | Return unsatisfied            | User notified to run `gh auth`    |
| PR not found     | No PR created yet            | Return unsatisfied            | Expected - user hasn't created PR |
| CI checks fail   | Tests failing                | Return unsatisfied            | Expected - user must fix tests    |

### Fail-Open Principle

**Definition**: When in doubt, default to safe behavior that doesn't falsely satisfy checks.

**Implementation**:

```python
try:
    # Attempt preference detection
    if self._user_prefers_no_auto_merge():
        return self._check_ci_status_no_auto_merge()
except Exception as e:
    logger.warning(f"Error detecting merge preference: {e}")
    # Fall through to standard behavior

# Standard CI check (requires merge)
return self._check_ci_status_standard()
```

**Rationale**:

- Errors during detection should never prevent CI validation
- Better to require merge when in doubt than skip validation
- Preserves backward compatibility

---

## Testing

### Unit Tests

Test coverage for preference awareness:

```python
# test_power_steering_checker.py

class TestMergePreferenceAwareness:
    """Tests for USER_PREFERENCES merge preference detection."""

    def test_preference_detected_standard_format(self):
        """NEVER Merge PRs Without Permission detected."""

    def test_preference_detected_verbose_format(self):
        """NEVER merge pull requests without explicit user permission detected."""

    def test_preference_not_detected_missing_keywords(self):
        """Preference with missing keywords not detected."""

    def test_preference_detection_file_not_found(self):
        """Missing USER_PREFERENCES.md returns False."""

    def test_ci_check_no_auto_merge_pr_ready(self):
        """PR ready + CI passing returns satisfied."""

    def test_ci_check_no_auto_merge_ci_failing(self):
        """PR ready + CI failing returns unsatisfied."""

    def test_ci_check_no_auto_merge_no_pr(self):
        """No PR created returns unsatisfied."""

    def test_ci_check_standard_behavior_without_preference(self):
        """Standard behavior when preference not detected."""
```

### Integration Tests

End-to-end validation:

```python
class TestMergePreferenceIntegration:
    """Integration tests for merge preference workflow."""

    def test_workflow_with_preference_stops_at_pr_ready(self):
        """Workflow completes when PR ready (not merged)."""

    def test_workflow_without_preference_requires_merge(self):
        """Workflow requires merge when preference not set."""

    def test_preference_change_during_session(self):
        """Preference changes reflected in subsequent checks."""
```

### Manual Testing

**Test Plan**:

1. **Setup**: Create test repository with USER_PREFERENCES.md
2. **Create PR**: Push code, create PR, wait for CI
3. **Run Power-Steering**: Verify consideration check passes
4. **Verify Evidence**: Check logs for "awaiting user approval" message
5. **Remove Preference**: Comment out preference, verify standard behavior

---

## Performance Considerations

### File I/O

- `USER_PREFERENCES.md` read during each `_check_ci_status()` call (lazy detection)
- Typical size: <10KB
- Read overhead: <1ms
- No caching between checks (enables dynamic preference changes)

**Note**: Could cache preference state per session if file I/O becomes measurable overhead, but current design prioritizes dynamic updates.

### Regex Performance

- Pattern complexity: Medium (5 groups, quantifiers)
- Typical input size: 1-100 lines
- Match overhead: <1ms

**Note**: Performance negligible compared to network I/O (gh CLI).

### gh CLI Overhead

- Network latency: 100-500ms (GitHub API)
- Dominant performance factor
- Unavoidable for accurate PR status

---

## Security Considerations

### Input Validation

**USER_PREFERENCES.md**:

- File read with encoding='utf-8'
- No code execution risk (text file only)
- Regex matching is safe (no eval/exec)

**gh CLI Output**:

- JSON parsing with built-in `json` module
- No shell injection (uses subprocess.run with list args)
- Output sanitized before logging

### Privilege Escalation

**Risk**: None. Feature reads configuration, doesn't modify state.

**Validation**:

- No file writes
- No git operations
- No GitHub API mutations

### Information Disclosure

**Risk**: Low. Logs may contain PR numbers and status.

**Mitigation**:

- Logs written to `.claude/runtime/logs/` (gitignored)
- No secrets logged (API tokens, passwords)
- Evidence collection uses sanitized output

---

## Migration Guide

### From Standard Behavior

**Before** (standard Power-Steering):

```yaml
# considerations.yaml
- id: ci_status
  question: Are CI checks passing and PR merged?
  checker: _check_ci_status
```

**After** (with preference awareness):

```yaml
# No changes to considerations.yaml required
- id: ci_status
  question: Are CI checks passing and PR merged?
  checker: _check_ci_status # Now preference-aware
```

**Migration Steps**:

1. Update Power-Steering code (already done)
2. Add preference to `USER_PREFERENCES.md` (user action)
3. **No restart needed** - changes detected on next CI check
4. Verify behavior with test PR

**Note**: If creating `USER_PREFERENCES.md` for the first time, restart Claude to ensure the file is accessible. Subsequent changes take effect immediately.

---

## Troubleshooting

### Debug Logging

Enable detailed logging:

```python
# In power_steering_checker.py
logger.setLevel(logging.DEBUG)

# Logs output
DEBUG: Reading USER_PREFERENCES.md
DEBUG: Preference pattern: NEVER.*Merge.*PR.*Without.*Permission
DEBUG: Preference detected: True
DEBUG: Using no-auto-merge CI check
DEBUG: Executing: gh pr view --json state,statusCheckRollup,isDraft
DEBUG: PR #123 state: OPEN, CI: SUCCESS
INFO: CI check satisfied (PR ready, awaiting user approval)
```

### Common Issues

**Issue**: Preference detected but CI check still fails

**Diagnosis**:

```bash
# Check PR status manually
gh pr view --json state,statusCheckRollup,isDraft

# Expected output
{
  "state": "OPEN",
  "statusCheckRollup": [{"state": "SUCCESS"}]
}
```

**Solution**: Ensure CI checks actually passing, PR not in draft state.

**Issue**: Preference not detected despite correct format

**Diagnosis**:

```bash
# Check file exists and has correct content
cat .claude/context/USER_PREFERENCES.md | grep -i "never.*merge.*without.*permission"
```

**Solution**:

- Verify file location at `.claude/context/USER_PREFERENCES.md`
- If file was just created, restart Claude session (first-time only)
- If file already existed, changes take effect immediately on next check

---

## Related Documentation

- [How-To: Configure Merge Preferences](../howto/power-steering-merge-preferences.md) - User guide
- [Power-Steering Overview](../features/power-steering/README.md) - Feature overview
- [Power-Steering Configuration](../features/power-steering/configuration.md) - General configuration
- [USER_PREFERENCES.md Reference](../reference/user-preferences.md) - Complete preferences documentation

---

## Changelog

### v0.10.0 (Planned)

**Added**:

- `_user_prefers_no_auto_merge()` method for preference detection
- `_check_ci_status_no_auto_merge()` method for no-merge validation
- Preference-aware logic in `_check_ci_status()`

**Changed**:

- `_check_ci_status()` now respects USER_PREFERENCES.md merge setting

**Technical Details**:

- No breaking changes
- Backward compatible with existing workflows
- Fail-open design for robustness

---

## Future Enhancements

### Planned Improvements

1. **Caching**: Cache preference state per session to reduce file I/O
2. **Configuration**: Add explicit toggle in considerations.yaml for preference awareness
3. **Metrics**: Track preference usage and CI check success rates
4. **Documentation**: Auto-detect preference format variations

### Research Directions

1. **Granular Preferences**: Per-PR merge preferences (e.g., "auto-merge bug fixes, manual for features")
2. **Time-Based**: Preference inheritance from parent branch or project defaults
3. **Team Policies**: Organization-wide merge preferences

---

**Questions?** Open an issue on [GitHub](https://github.com/rysweet/amplihack/issues) with the `power-steering` label.
