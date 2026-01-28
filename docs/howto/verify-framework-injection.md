# How to Verify Framework Instruction Injection

Quick guide to verify that amplihack's UserPromptSubmit hook properly injects framework instructions when CLAUDE.md differs from AMPLIHACK.md.

## When You Need This

- When using amplihack in a project with custom CLAUDE.md
- If framework behaviors aren't being applied
- After modifying CLAUDE.md
- When troubleshooting inconsistent agent behavior

## Verify Injection is Working

Check the hook logs to see injection activity:

```bash
# View recent hook activity
tail -f ~/.amplihack/.claude/runtime/logs/user_prompt_submit.log

# Send a test message to trigger the hook
# (in Claude Code or any amplihack CLI)
# Type any message and press enter

# Check logs for injection confirmation
grep "Injected AMPLIHACK.md" ~/.amplihack/.claude/runtime/logs/user_prompt_submit.log
```

## Expected Behavior

### When CLAUDE.md Differs from AMPLIHACK.md

Framework instructions are injected on every message:

```
[INFO] Injected AMPLIHACK.md framework instructions
[INFO] Injection order: preferences → memories → framework
```

Claude receives framework instructions automatically without requiring them in your CLAUDE.md.

### When CLAUDE.md Matches AMPLIHACK.md

No injection occurs (files are identical):

```
[DEBUG] CLAUDE.md matches AMPLIHACK.md - skipping framework injection
```

This happens in amplihack's own repository where CLAUDE.md === AMPLIHACK.md.

## Quick Test

Test framework injection with a simple prompt:

```bash
# In Claude Code
echo "What agents are available?"

# Check if framework instructions were injected
tail -5 ~/.amplihack/.claude/runtime/logs/user_prompt_submit.log
```

If you see "Injected AMPLIHACK.md framework instructions", injection is working.

## Verify Cache Performance

Check that caching works correctly:

```bash
# Send multiple messages in quick succession
# The first message reads both files
# Subsequent messages use cache (unless files change)

# View cache hit rate
grep "cache" ~/.amplihack/.claude/runtime/logs/user_prompt_submit.log
```

Expected: ~99% cache hit rate after first message.

## Troubleshooting

### Framework Behaviors Not Applied

If Claude doesn't follow framework instructions:

```bash
# Verify AMPLIHACK.md exists
ls -la ~/.amplihack/.claude/AMPLIHACK.md
# or
ls -la .claude/AMPLIHACK.md  # per-project mode

# Check hook is running
tail -20 ~/.amplihack/.claude/runtime/logs/user_prompt_submit.log

# Verify CLAUDE.md differs from AMPLIHACK.md
diff CLAUDE.md ~/.amplihack/.claude/AMPLIHACK.md
```

If `diff` shows no differences, files are identical and no injection occurs (by design).

### Injection Too Slow

If messages take too long to process:

```bash
# Check metrics for timing issues
tail ~/.amplihack/.claude/runtime/metrics/user_prompt_submit_metrics.jsonl

# Look for cache hits (should be fast)
# Cache miss: ~50-100ms
# Cache hit: <1ms
```

Slow injection usually means cache isn't working. Check that file modification times aren't constantly changing.

### Wrong Framework Instructions

If Claude receives outdated instructions:

```bash
# Clear cache by restarting the session
# or
# Force re-read by touching AMPLIHACK.md
touch ~/.amplihack/.claude/AMPLIHACK.md

# Next message will re-read both files
```

## What Gets Injected

When CLAUDE.md differs from AMPLIHACK.md, the hook injects:

1. **User preferences** (from USER_PREFERENCES.md)
2. **Agent memories** (if agents mentioned in prompt)
3. **Framework instructions** (entire AMPLIHACK.md contents)

This ensures framework behaviors are always available even when your project has custom CLAUDE.md.

## Performance Characteristics

**First message**: ~50-100ms (reads and compares both files)
**Cached messages**: <1ms (uses cached comparison result)
**Cache invalidation**: Only when file modification time changes

## Related

- [Framework Injection Architecture](../concepts/framework-injection-architecture.md) - Why this approach
- [UserPromptSubmit Hook API](../reference/user-prompt-submit-hook-api.md) - Developer details
- [Hook Configuration Guide](../HOOK_CONFIGURATION_GUIDE.md) - Hook system overview
