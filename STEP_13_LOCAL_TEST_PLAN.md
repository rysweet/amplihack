# Step 13: Local Testing Plan for PR #2149

## Test Environment

- Branch: `fix/amplihack-injection-logic`
- Changes: AMPLIHACK.md injection logic with caching
- Method: Fresh Claude Code session required for hook testing

## Test Scenarios

### Scenario 1: Identical Files (No Injection)

**Setup**:

- CLAUDE.md identical to .claude/AMPLIHACK.md (current state in amplihack repo)

**Expected Behavior**:

1. Hook checks both files, finds them identical
2. NO injection occurs (returns "")
3. Metric: `amplihack_skipped_identical` = 1
4. No AMPLIHACK.md content in context

**Verification**:

```bash
# In fresh Claude Code session
echo "Test message to trigger hook"
# Check hook logs for "amplihack_skipped_identical"
```

### Scenario 2: Different Files (Injection Occurs)

**Setup**:

1. Modify CLAUDE.md to add project-specific content
2. Start fresh session

**Expected Behavior**:

1. Hook detects files differ
2. Injects full AMPLIHACK.md contents into message context
3. Metric: `amplihack_injected_different` = 1
4. AMPLIHACK.md content visible in additional context

**Verification**:

```bash
# Modify CLAUDE.md first
echo "# My Project\nCustom instructions" > CLAUDE.md

# Start fresh Claude Code session
echo "Test message"
# Check hook logs for "amplihack_injected_different"
# Verify framework instructions present in context
```

### Scenario 3: Missing CLAUDE.md (Injection Occurs)

**Setup**:

1. Delete or rename CLAUDE.md
2. Start fresh session

**Expected Behavior**:

1. Hook detects CLAUDE.md missing
2. Injects AMPLIHACK.md contents
3. Metric: `amplihack_injected_missing` = 1

**Verification**:

```bash
mv CLAUDE.md CLAUDE.md.backup
# Start fresh Claude Code session
echo "Test message"
# Check hook logs for "amplihack_injected_missing"
```

### Scenario 4: Caching Performance Test

**Setup**:

- Send multiple messages in same session
- Files unchanged

**Expected Behavior**:

1. First message: Reads files, checks mtime, makes decision
2. Subsequent messages: Only checks mtime (cache hit)
3. Metrics: `amplihack_cache_hit` increases with each message
4. NO file reads after first message (performance improvement)

**Verification**:

```bash
# In same session, send 5 messages
for i in {1..5}; do echo "Test message $i"; sleep 1; done
# Check hook logs - should see:
# Message 1: amplihack_skipped_identical (or injected)
# Messages 2-5: amplihack_cache_hit
```

### Scenario 5: Cache Invalidation

**Setup**:

1. Start session (cache populated)
2. Modify AMPLIHACK.md while session active
3. Send new message

**Expected Behavior**:

1. Hook detects mtime changed
2. Cache invalidated, files re-read
3. New decision made based on updated content

**Verification**:

```bash
# In active session
echo "Message 1" # Cache populated

# In another terminal
echo "# Modified" >> .claude/AMPLIHACK.md

# Back in session
echo "Message 2" # Should detect change, re-read files
```

### Scenario 6: Injection Order Verification

**Setup**:

- Have user preferences set (pirate language)
- Mention an agent (@architect)
- CLAUDE.md differs from AMPLIHACK.md

**Expected Behavior - Injection Order**:

1. FIRST: User preferences injected (pirate language)
2. SECOND: Agent memories injected (for @architect)
3. THIRD: AMPLIHACK.md framework instructions injected

**Verification**:

```bash
# With pirate communication style in USER_PREFERENCES.md
echo "@architect please design a simple API"
# Check response uses pirate language
# Check additional context shows: prefs → memories → framework
```

### Scenario 7: No AMPLIHACK.md Found

**Setup**:

- Rename or delete .claude/AMPLIHACK.md
- No CLAUDE_PLUGIN_ROOT set

**Expected Behavior**:

1. Hook logs: "No AMPLIHACK.md found"
2. No injection occurs
3. Metric: `amplihack_not_found` = 1
4. Hook doesn't fail (graceful degradation)

### Scenario 8: Plugin Architecture Path

**Setup**:

1. Set CLAUDE_PLUGIN_ROOT to centralized location
2. Place AMPLIHACK.md there

**Expected Behavior**:

1. Hook finds AMPLIHACK.md in plugin location (priority over .claude/)
2. Uses that file for comparison/injection

**Verification**:

```bash
export CLAUDE_PLUGIN_ROOT="/path/to/plugin"
cp .claude/AMPLIHACK.md "$CLAUDE_PLUGIN_ROOT/"
# Start fresh session
# Hook should use plugin location
```

## Regression Checks

### ✅ Verify Existing Features Still Work

1. User preferences injection still works
2. Agent memory injection still works
3. Adaptive strategies (copilot/claude) still work
4. Hook doesn't crash on errors

## Test Results Documentation

After testing, document results in PR description:

```markdown
## Step 13: Local Testing Results

**Test Environment**: Branch fix/amplihack-injection-logic, fresh Claude Code
session

**Tests Executed**:

1. Identical files (Scenario 1) → ✅ No injection, metric correct
2. Different files (Scenario 2) → ✅ Injection works, framework present
3. Caching performance (Scenario 4) → ✅ Cache hits after first message
4. Injection order (Scenario 6) → ✅ Prefs → Memories → Framework

**Regressions**: ✅ None detected - preferences and memories still work

**Issues Found**: [List any issues]

**Performance**: Cache reduces file I/O by ~99% after first message
```

## Why This Testing Matters

- Hook runs on EVERY user message - performance critical
- Injection order affects Claude's attention/behavior
- Caching must work correctly or degrades performance
- Graceful degradation ensures hook never breaks sessions
- Regression testing confirms existing features unaffected
