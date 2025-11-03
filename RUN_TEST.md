# Quick Test Guide

## Run Before Committing

As per Step 8 of the workflow, test locally BEFORE committing.

## Command

```bash
python3 test_logging_fixes.py
```

## What It Tests

1. **STDOUT/STDERR logging** to all 3 destinations
2. **Transcript export** to correct location (not UV cache)

## Expected Result

```
✓ ALL TESTS PASSED!

VERIFIED:
  ✓ STDOUT/STDERR flows to session log file
  ✓ Session log contains actual output
  ✓ Transcript files exist in correct location
  ✓ Transcripts in project (not UV cache)
  ✓ Transcript files contain valid content
```

## If Tests Fail

The test will print specific error messages indicating what failed:

- `[FAIL]` messages show the specific failure
- Check the session directory: `.claude/runtime/logs/{session_id}/`
- Review the `auto.log` file for debugging

## Test Duration

Approximately 1-2 minutes (depends on API response time).

## Requirements

- Python 3.10+
- Claude SDK installed
- Valid Anthropic API key
- Project root: `/Users/ryan/src/MicrosoftHackathon2025-AgenticCoding`

## Cleanup

After successful test, you can optionally clean up:

```bash
rm -rf .claude/runtime/logs/auto_claude_*
rm test_output.txt  # Created by the test task
```

## Integration with Workflow

This test is **Step 8** in the default workflow:

1. ~~Read requirements~~
2. ~~Plan implementation~~
3. ~~Implement changes~~
4. ~~Test changes~~
5. ~~Verify fixes~~
6. ~~Document changes~~
7. ~~Review PR description~~
8. **→ Run local test** ← YOU ARE HERE
9. Commit changes
10. Create PR
