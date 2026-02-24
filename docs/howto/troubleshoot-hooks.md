# How to Troubleshoot Hook Issues

Quick guide to diagnose and fix amplihack hook problems.

## Quick Checks

### 1. Verify Hooks Are Installed

```bash
# Check if hooks exist in settings.json
cat ~/.claude/settings.json | grep -A5 hooks

# Expected output: Should show SessionStart, Stop, and PostToolUse hooks
```

### 2. Verify Hook Files Exist

```bash
# Check if hook files are installed
ls -la ~/.claude/tools/amplihack/hooks/

# Expected output: session_start.py, stop.py, post_tool_use.py
```

### 3. Check Hook Execution

Start Claude Code and look for hook execution messages in the output:

```
✓ SessionStart [/home/user/.claude/tools/amplihack/hooks/session_start.py] completed
```

## Common Issues and Solutions

### Issue 1: Hooks Disappear After Exit (Pre-v0.9.1)

**Symptom:**

- Hooks work on first launch
- After exiting Claude, hooks are missing
- Must re-run `amplihack install` every time

**Cause:** Bug in versions before 0.9.1 where SettingsManager restored old settings without hooks.

**Solution:**

Upgrade to v0.9.1 or later:

```bash
uvx --from git+https://github.com/rysweet/amplihack amplihack --version
```

### Issue 2: "Hook not found" Error

**Symptom:**

```
⏺ Stop [.claude/tools/amplihack/hooks/stop.py] failed with non-blocking status code 127
```

**Cause:** Hook path is incorrect or relative instead of absolute.

**Solution:**

Check and fix hook paths in ~/.claude/settings.json:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/home/user/.claude/tools/amplihack/hooks/stop.py"
          }
        ]
      }
    ]
  }
}
```

**Automatic Fix:** As of v0.9.1, amplihack automatically fixes relative paths to absolute during launch.

### Issue 3: Hooks Not Running At All

**Symptom:**

- No hook execution messages
- amplihack features don't work
- No errors shown

**Cause:** Project-level settings.json is overriding global hooks.

**Diagnosis:**

```bash
# Check if project has its own settings
cat .claude/settings.json | grep hooks

# If this shows hooks, they're overriding global ones
```

**Solution:**

Manually merge amplihack hooks into project settings. See [Hook Configuration Guide](../HOOK_CONFIGURATION_GUIDE.md) for complete instructions.

### Issue 4: Permission Denied Errors

**Symptom:**

```
⏺ SessionStart failed: Permission denied
```

**Cause:** Hook files aren't executable.

**Solution:**

```bash
# Make hooks executable
chmod +x ~/.claude/tools/amplihack/hooks/*.py
```

### Issue 5: Hook Timeout

**Symptom:**

```
⏺ Stop hook timed out after 120s
```

**Cause:** Stop hook is performing long-running operations.

**Solution:**

This is usually normal for the Stop hook, which captures session artifacts. If it consistently times out:

1. Check disk space: `df -h ~/.claude/runtime/logs/`
2. Check for stuck processes: `ps aux | grep amplihack`
3. Review logs: `tail ~/.claude/runtime/logs/latest/stop_hook.log`

## Diagnostic Commands

### Full Hook Status Check

```bash
# Create diagnostic script
cat > /tmp/check_hooks.sh << 'EOF'
#!/bin/bash

echo "=== Hook Configuration Diagnostic ==="
echo ""

echo "1. Global Settings Hooks:"
grep -A10 hooks ~/.claude/settings.json 2>/dev/null || echo "   No global hooks found"
echo ""

echo "2. Project Settings Hooks:"
grep -A10 hooks .claude/settings.json 2>/dev/null || echo "   No project hooks found"
echo ""

echo "3. Hook Files:"
ls -lh ~/.claude/tools/amplihack/hooks/ 2>/dev/null || echo "   Hook directory not found"
echo ""

echo "4. Recent Hook Execution (from logs):"
tail -20 ~/.claude/runtime/logs/latest/session.log 2>/dev/null | grep -i hook || echo "   No recent hook logs"
echo ""

echo "5. Amplihack Version:"
uvx --from git+https://github.com/rysweet/amplihack amplihack --version 2>/dev/null || echo "   Cannot determine version"

EOF

chmod +x /tmp/check_hooks.sh
/tmp/check_hooks.sh
```

### Watch Hook Execution Live

```bash
# Monitor logs during Claude session
tail -f ~/.claude/runtime/logs/latest/*.log
```

## Getting Help

If hooks still aren't working after trying these solutions:

1. **Collect diagnostic information:**

   ```bash
   /tmp/check_hooks.sh > /tmp/hook_diagnostic.txt
   ```

2. **Check existing issues:**

   [amplihack/issues](https://github.com/rysweet/amplihack/issues?q=is%3Aissue+hook)

3. **File a new issue:**

   Include:
   - Output from diagnostic script
   - amplihack version
   - Operating system and version
   - Steps to reproduce

## Related Documentation

- [Hook Configuration Guide](../HOOK_CONFIGURATION_GUIDE.md) - Complete configuration reference
- [Changelog v0.9.1](../CHANGELOG_v0.9.1.md) - Hook persistence fix details
