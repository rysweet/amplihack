# Knowledge Extraction Example: Discovery

## Scenario

After a 45-minute debugging session to fix pre-commit hooks failing silently.

## Session Summary

- **Problem**: Pre-commit hooks appeared to run but didn't modify files
- **Investigation**: 45 minutes of systematic debugging
- **False leads**: Initially blamed merge conflicts, then tool versions
- **Root cause**: Cloud sync (OneDrive) file locks preventing hook modifications
- **Solution**: Exponential backoff retry logic for file I/O
- **Outcome**: Hooks now work reliably, even with cloud storage

## Extraction Process

### Step 1: Session Analysis

**What happened**:

- Started with cryptic error ("hooks ran but nothing changed")
- Checked merge conflicts (false lead)
- Checked tool versions (false lead)
- Eventually realized issue was file I/O timing
- Solution: Add retry logic with exponential backoff

**What was learned**:

- Cloud sync file locks cause silent I/O failures
- Need defensive file I/O with retries
- Error messages should be more diagnostic
- Cloud-related issues are often invisible

### Step 2: Create Discovery Entry

````markdown
## Pre-commit Hooks Cloud Sync Issue (2025-11-08)

### Issue

Pre-commit hooks appeared to run but didn't modify files. No error messages,
just silent failure.

### Root Cause

OneDrive (cloud sync) was holding file locks on hook-modified files. The
subprocess.run() call would complete "successfully" without actually writing
changes because of the lock.

### Solution

Implemented exponential backoff retry logic for file I/O:

```python
def write_with_retry(filepath, data, max_retries=3):
    retry_delay = 0.1
    for attempt in range(max_retries):
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(data)
            return
        except OSError as e:
            if e.errno == 5 and attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise
```
````

### Key Learnings

1. **Cloud sync issues are silent**: Tools don't report locks, operations appear to succeed
2. **File I/O needs defensive coding**: Always add retry logic for file operations
3. **Debugging methodology matters**: Systematic check of each layer (hooks → versions → I/O)
4. **Environment-specific issues**: Development machines with cloud sync need different handling

### Prevention

For any file I/O operation:

1. Use write_with_retry() for all file modifications
2. Add explicit error logging if retries occur
3. Test with cloud storage enabled
4. Document that system expects possible brief I/O delays
5. Consider adding diagnostic flag: `--verbose-io` to show retry attempts

```

### Step 3: Quality Checklist

- ✅ Issue is specific (not "tools broken")
- ✅ Root cause identified (OneDrive file locks, not merge conflicts)
- ✅ Solution is working (now used in production)
- ✅ Learning is generalized (applies to all file I/O)
- ✅ Prevention strategy is actionable (use retry logic)
- ✅ Code examples provided
- ✅ No speculation or future-proofing

## Related Knowledge

### Discovery Connects To
- **PATTERNS.md**: "Resilient File I/O with Cloud Sync Resilience"
  - General solution for file I/O with retry logic
  - Applicable beyond just pre-commit hooks

### Could Enable New Agent
- **Agent**: "cloud-sync-issue-detector"
  - Detects when I/O errors are cloud-related
  - Suggests diagnostic approach
  - Value: Saves 30-45 minutes debugging time

## Impact

**Before extraction**:
- Developer encounters hook failure → 45 min debug → discovery
- Next developer encounters same issue → another 45 min debug

**After extraction**:
- Developer reads DISCOVERIES.md → sees root cause
- Implements retry logic → issue solved
- Time: 10 minutes vs 45 minutes = 80% improvement

**Organization impact**:
- If issue happens 4x per year: saves 140 minutes per year
- If pattern extracted: saves across multiple issues
- If agent created: saves 2-3 hours per quarter

## Key Principle

Good discoveries transform individual debugging work into organizational knowledge that prevents future mistakes and accelerates solutions.
```
