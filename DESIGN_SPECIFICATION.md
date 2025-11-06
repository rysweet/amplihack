# Design Specification: Auto Mode Log Formatting Fix

## Problem Statement
Auto mode stdout logs lack visual separation between entries, making them difficult to read during execution monitoring.

## Root Cause Analysis
**File**: `src/amplihack/launcher/auto_mode.py`
**Line**: 171
**Current Code**:
```python
print(f"[AUTO {self.sdk.upper()}] {msg}")
```

**Issue**: Uses default `print()` which adds only ONE newline. When mixed with streaming output that uses `end=""`, log entries run together visually.

## Proposed Solution

### Change Required
Modify line 171 to add extra newline and explicit flush:

```python
print(f"[AUTO {self.sdk.upper()}] {msg}\n", flush=True)
```

### Rationale
1. **Double Newline**: `print()` adds one newline by default, plus the `\n` in the string = 2 newlines total
2. **Visual Separation**: Creates blank line between log entries
3. **Explicit Flush**: Ensures immediate visibility in real-time streaming scenarios
4. **No Side Effects**: File logging (line 179) unchanged - still uses single newline

## Philosophy Alignment

### Ruthless Simplicity ✓
- One-line change
- No new abstractions
- No configuration options
- Direct fix at source

### Zero-BS Implementation ✓
- Real fix, not a workaround
- No stubs or TODOs
- Complete solution

### Quality Over Speed ✓
- Test-driven approach (test written first)
- Manual testing required before merge
- No compromise on verification

## Module Specification

### Module: `auto_mode.py`
**Responsibility**: Auto mode orchestration and logging
**Contract**: Log method formats and outputs messages
**Dependencies**: None added
**Testing**: Unit test + manual verification

### Brick Integrity
- Self-contained change within single module
- No impact on other modules
- Clear interface (log method signature unchanged)
- Regeneratable from this specification

## Testing Strategy

### Unit Test (TDD)
**File**: `tests/unit/test_auto_mode_log_formatting.py`
- Test double newline in output
- Test SDK prefix format
- Test level filtering (DEBUG excluded)
- Test visual separation between messages
- Test file logging unchanged

### Manual Testing (Required)
Execute actual auto mode session and verify:
1. Log entries have blank line between them
2. Streaming output not affected
3. UI mode logging not affected
4. File logs format unchanged

## Risk Assessment

### Low Risk Change
- **Scope**: Single line modification
- **Impact**: Stdout formatting only
- **Reversibility**: Trivially revertable
- **Dependencies**: None

### Potential Issues
1. **None identified** - Change is additive (adds newline)
2. **Terminal compatibility** - All modern terminals support `\n`
3. **File logging** - Explicitly unchanged (separate code path)

## Success Criteria

1. ✓ Test written (TDD approach)
2. ✓ Implementation complete (single line change)
3. ✓ Pre-commit hooks pass
4. ✓ Manual testing confirms improved readability
5. ✓ No regression in existing functionality
6. ✓ PR approved and merged

## Implementation Plan

### Step 5: Implement (Next)
- Modify line 171 in worktree copy
- Verify syntax
- Proceed to Step 6

### Step 6: Refactor
- No refactoring needed (minimal change)
- Verify no unnecessary complexity added

### Step 7-8: Testing
- Run pre-commit hooks
- Manual testing in actual auto mode session

### Step 9-15: PR Workflow
- Commit, push, create PR
- Review and merge

## Architecture Decision

**Why modify print() instead of creating formatter?**
- Follows KISS principle (ruthless simplicity)
- No need for abstraction layer for this use case
- One-line fix vs multi-file formatter
- Easy to understand and maintain

**Why flush=True?**
- Auto mode involves real-time streaming
- Ensures logs appear immediately
- Prevents buffering delays
- Minimal performance impact

## Notes
- Environment lacks pytest/pip - tests will run in CI
- Test provides specification even if not run locally
- Manual testing will be primary verification method
- File logging intentionally unchanged (different use case)
