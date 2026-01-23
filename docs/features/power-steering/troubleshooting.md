# Power Steering Troubleshooting

Ahoy! This guide helps ye fix common power steering issues, particularly the infinite loop bug that was plaguing the system.

## Quick Diagnosis

If power steering seems stuck or repeatin' messages, run the diagnostic command:

```bash
/amplihack:ps-diagnose
```

This checks yer power steering state health and shows:

- Current counter values
- Session ID consistency
- State file integrity
- Recent save/load operations

## Common Issues

### Issue: Counter Not Incrementing (Infinite Loop)

**Symptoms:**

- Same guidance message appears repeatedly
- Power steering never stops after first display
- State counter stays at 0 or doesn't increment

**Cause:**
State persistence failures due to cloud sync conflicts, atomic write issues, or file system problems.

**Solution (Fixed in v0.9.1+):**

The fix includes:

1. **Atomic writes with fsync**: Forces disk writes to complete
2. **Retry logic**: Handles cloud sync delays automatically
3. **Verification reads**: Confirms state was saved correctly
4. **Defensive validation**: Catches corrupted state data

**Check your version:**

```bash
amplihack --version
```

If ye're on v0.9.0 or earlier, upgrade:

```bash
pip install --upgrade amplihack
# or
uvx install --force amplihack
```

### Issue: State File Corruption

**Symptoms:**

- Power steering crashes with validation errors
- Diagnostic shows "invalid state" warnings
- Counter resets unexpectedly

**Diagnosis:**

```bash
# Check diagnostic logs
cat .claude/runtime/power-steering/*/diagnostic.jsonl | tail -20
```

Look fer:

- `save_success: false` - Write failures
- `load_success: false` - Read failures
- `validation_failed: true` - Corrupted data

**Solution:**

The fix automatically handles corrupted state:

1. Detects invalid counter values (negative or null)
2. Logs corruption event to diagnostics
3. Resets to safe default state
4. Continues operation without crashing

**Manual reset (if needed):**

```bash
# Remove corrupted state files
rm .claude/runtime/power-steering/*/state.json
```

Power steering will create fresh state on next run.

### Issue: Messages Not Customized

**Symptoms:**

- Generic messages appear instead of context-specific guidance
- Check results not reflected in guidance text
- All messages look identical

**Cause (Pre-v0.9.1):**
Message customization logic wasn't properly integrated with check results.

**Solution (Fixed):**

The fix ensures:

1. Check results are captured accurately
2. Messages are customized based on actual check outcomes
3. Context-specific guidance appears at the right time

**Verify the fix:**
Trigger power steering in different contexts and observe message variations based on:

- File modification status
- Workflow compliance
- Quality check results

## Diagnostic Logs

### Understanding Diagnostic Output

Diagnostic logs be written to `~/.amplihack/.claude/runtime/power-steering/{session_id}/diagnostic.jsonl` with this structure:

```json
{
  "timestamp": "2025-12-17T19:30:00Z",
  "operation": "state_save",
  "counter_before": 0,
  "counter_after": 1,
  "session_id": "20251217_193000",
  "file_path": ".claude/runtime/power-steering/20251217_193000/state.json",
  "save_success": true,
  "verification_success": true,
  "retry_count": 0
}
```

**Key fields:**

- `operation`: What happened (state_save, state_load, validation)
- `counter_before/after`: Track counter changes
- `save_success`: Whether write completed
- `verification_success`: Whether verification read worked
- `retry_count`: How many retries were needed

### Common Log Patterns

**Healthy operation:**

```json
{"operation": "state_save", "save_success": true, "verification_success": true, "retry_count": 0}
{"operation": "state_load", "load_success": true, "validation_passed": true}
```

**Cloud sync retry (normal):**

```json
{ "operation": "state_save", "save_success": true, "retry_count": 2 }
```

**Corruption detected:**

```json
{"operation": "state_load", "load_success": true, "validation_failed": true, "reason": "negative_counter"}
{"operation": "state_reset", "counter_reset_to": 0}
```

## Manual Recovery

If automatic recovery doesn't work:

### Step 1: Stop Claude Code

Exit yer current session to prevent concurrent writes.

### Step 2: Clear State

```bash
rm -rf .claude/runtime/power-steering/
```

### Step 3: Restart

Start a fresh Claude Code session. Power steering will initialize cleanly.

### Step 4: Verify

```bash
/amplihack:ps-diagnose
```

Should show fresh state with counter at 0.

## Prevention

The fix includes prevention measures, but ye can help:

1. **Avoid concurrent sessions**: Don't run multiple Claude Code instances in the same repo
2. **Wait fer cloud sync**: If usin' Dropbox/iCloud, let files sync before starting
3. **Keep updated**: Always run latest amplihack version
4. **Check diagnostics periodically**: Run `/amplihack:ps-diagnose` to catch issues early

## Getting Help

If issues persist after these steps:

1. Capture diagnostic output:

   ```bash
   /amplihack:ps-diagnose > ps-diagnostic.txt
   ```

2. Gather logs:

   ```bash
   tar -czf ps-logs.tar.gz .claude/runtime/power-steering/
   ```

3. Create a GitHub issue with:
   - amplihack version (`amplihack --version`)
   - Diagnostic output
   - Compressed logs
   - Description of the problem

Repository: https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues

## Related Documentation

- [Power Steering Overview](./README.md) - What power steering does
- [Architecture](./architecture.md) - How the system works
- [Configuration](./configuration.md) - Customization options
