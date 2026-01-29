# Power-Steering Compaction Handling

Robust conversation compaction detection, validation, and recovery for long sessions.

## What Is Compaction?

When a conversation with Claude grows too long (approaching 1M tokens), older messages are automatically removed to stay within context limits. This is called **compaction**.

Compaction is normal and expected in long sessions. However, it can cause problems if critical information is removed:

- Active TODO items
- Original session objectives
- Recent code changes
- Open issues or blockers

**Power-steering's compaction handling ensures:**

- Compaction events are detected automatically
- Critical data preservation is validated
- Clear diagnostics are provided
- Actionable recovery steps guide users

## Quick Example

**Before compaction:**
Session with 100 turns, including TODO list from turn 10.

**After compaction:**
Turns 1-40 removed. Power-steering checks if the TODO list is still visible.

**If preserved:**

```
✅ Compaction handled successfully
TODO list preserved in context
Continue working normally
```

**If lost:**

```
❌ Compaction validation failed
TODO items from turn 10 are no longer visible

Recovery:
  1. Review recent work (turns 41-100)
  2. Recreate TODO list using TodoWrite
  3. Check commit messages for completed items
```

## How It Works

### Detection

Power-steering detects compaction by analyzing the transcript:

1. **Check turn numbering** - Gaps indicate removed messages
2. **Analyze token estimates** - Large jumps suggest compaction
3. **Look for compaction markers** - Claude may note when context is trimmed

**Detection is automatic** - no configuration needed.

### Validation

Once compaction is detected, power-steering validates critical data:

**High-priority checks:**

- ✅ Active TODO items still visible
- ✅ Session objectives still clear
- ✅ User's original goal understandable

**Medium-priority checks:**

- ✅ Recent code changes (last 10 turns) preserved
- ✅ Open issues or blockers still in context
- ✅ Critical decisions not lost

**Validation is conservative** - defaults to "passed" when uncertain (fail-open).

### Diagnostics

Power-steering provides clear diagnostics when compaction occurs:

```
⚠️  COMPACTION DETECTED
Conversation compacted at turn 45
Messages removed: turns 1-30 (estimated 15,000 tokens)

Validation: PASSED ✓

Critical data preserved:
  • 3 active TODO items visible
  • Session objective clear: "Implement compaction handling"
  • Recent context intact (last 15 turns)
  • No blockers lost
```

If validation fails, specific warnings and recovery steps are provided.

## When Does Compaction Occur?

**Typical scenarios:**

- **Long investigation sessions** - Exploring large codebases
- **Complex implementations** - Multi-hour development sessions
- **Debugging marathons** - Deep dives into tricky bugs
- **Documentation sessions** - Writing extensive documentation

**Approximate timing:**

- **~200 turns**: Context getting large, compaction unlikely
- **~400 turns**: Compaction may occur in verbose sessions
- **~600 turns**: Compaction likely in typical sessions
- **~1000+ turns**: Compaction almost certain

**Factors affecting compaction:**

- Message length (longer messages = faster compaction)
- Code snippets (large code blocks use more tokens)
- Tool outputs (verbose tool results accelerate compaction)

## Benefits

### Prevents Data Loss

Without compaction handling, critical information can be silently lost:

❌ **Without validation:**

- User continues working, unaware TODOs were lost
- Session ends with incomplete work
- No way to recover lost context

✅ **With validation:**

- System detects data loss immediately
- User is prompted to recreate lost information
- Recovery steps prevent incomplete sessions

### Improves Long-Session Reliability

Long sessions are more reliable with compaction handling:

- **Checkpoint awareness** - Know when context is trimmed
- **Data preservation** - Critical info explicitly validated
- **Continuity** - Seamless work across compaction events

### Provides Visibility

Users understand what's happening in their session:

- **Transparent** - Compaction is announced, not hidden
- **Informative** - Diagnostics explain what was removed
- **Actionable** - Recovery steps guide next actions

## Configuration

Compaction handling is **automatic by default** and requires no configuration.

### Disable Compaction Checks

To disable compaction validation (not recommended):

**Edit:** `.claude/tools/amplihack/considerations.yaml`

```yaml
- id: compaction_handling
  category: Session Completion & Progress
  question: Was compaction handled appropriately?
  description: Validates critical data preserved after compaction
  severity: warning
  checker: _check_compaction_handling
  enabled: false # Set to false to disable
```

### Adjust Severity

Change compaction validation from warning to blocker:

```yaml
- id: compaction_handling
  severity: blocker # Changed from "warning" to "blocker"
  # ... rest of configuration
```

This will **block session ending** if compaction validation fails.

**Not recommended** - compaction is often recoverable and shouldn't block work.

## Troubleshooting

### Problem: "TODO items lost after compaction"

**What happened:**
Active TODO items from early in the session were removed during compaction.

**Impact:**
You may not remember all tasks or their completion status.

**Recovery:**

1. **Review recent work** - Check the last 20-30 turns for clues
2. **Check git commits** - Recent commits show completed work
3. **Recreate TODO list** - Use `TodoWrite` to rebuild task list
4. **Mark completed items** - Use commit messages as evidence
5. **Continue working** - Focus on remaining tasks

**Example recovery:**

```bash
# Check recent commits for completed work
git log --oneline -10

# Review recent test runs
pytest --last-failed

# Recreate TODO list based on findings
# Then use TodoWrite tool to document remaining tasks
```

**Prevent next time:**

- Mark TODOs complete as you finish them
- Commit code frequently (creates checkpoints)
- Consider ending session after major milestones

### Problem: "Session objectives unclear after compaction"

**What happened:**
The original user goal was stated in messages that were removed.

**Impact:**
Current work direction may be unclear without original context.

**Recovery:**

1. **Review recent work** - What have you been working on?
2. **Check PR description** - Often states the goal
3. **Look at git branch name** - May indicate objective
4. **Explicitly restate goal** - Tell Claude your current objective
5. **Continue with clarity** - Ensure goal is now clear

**Example recovery:**

```
"Let me clarify the objective: I'm implementing compaction handling
for power-steering mode. The goal is to detect when context is
compacted and validate that critical data (TODOs, objectives) wasn't
lost. I've already implemented the CompactionValidator class and now
need to write tests."
```

**Prevent next time:**

- State objectives clearly at session start
- Restate goals after major milestones
- Use descriptive git branch names
- Write PR descriptions early

### Problem: "Frequent compaction warnings"

**What happened:**
Your sessions are hitting compaction multiple times.

**Impact:**
Repeated context loss, potential work fragmentation.

**Solutions:**

**Short-term:**

- End session and start fresh after major milestones
- Break large tasks into smaller sessions
- Commit work frequently to preserve state

**Long-term:**

- Plan sessions to be < 400 turns when possible
- Use completion evidence (tests, commits) instead of memory
- Split complex investigations across multiple sessions
- End sessions after completing logical units of work

**When acceptable:**

- Complex debugging that requires deep context
- Large-scale refactoring across many files
- Exploratory investigations with many dead ends

### Problem: "False positives - validation fails incorrectly"

**What happened:**
Compaction validation reports data loss when nothing is actually lost.

**Possible causes:**

1. **TODO items were completed** - Not lost, just marked done
2. **Objectives changed** - Legitimate pivot, not data loss
3. **Context sufficient** - Old messages not needed anymore

**Solutions:**

**If TODOs were completed:**

```
"The TODO items from earlier were completed - you can see the
test output and commits showing this work was finished."
```

**If objectives changed:**

```
"We pivoted to a different approach after discovering issue X.
The new objective is clear: implement solution Y."
```

**If context is sufficient:**

```
"The removed messages contained investigation that led to the
current solution. That context isn't needed anymore - the
solution stands on its own."
```

**Report the false positive:**
If validation logic is incorrect, report it so the heuristics can be improved.

### Problem: "No compaction detected in long session"

**What happened:**
Session has 500+ turns but no compaction warnings.

**Likely causes:**

1. **Context not full yet** - 500 turns with short messages < 200k tokens
2. **Detection issue** - Bug in compaction detection (rare)
3. **Compaction hasn't occurred** - Token limit not reached yet

**Check:**

```python
# View session diagnostics (if available)
from power_steering_checker import CompactionValidator

validator = CompactionValidator()
ctx = validator.get_compaction_context(transcript)

print(f"Detected: {ctx.detected}")
print(f"Turn count: {len(transcript)}")
```

**Actions:**

- Continue working normally if no issues
- If context feels fragmented, manually checkpoint (commit code)
- Report if detection seems broken

### Problem: "Compaction validation is slow"

**What happened:**
Validation takes > 1 second to complete.

**Acceptable performance:**

- Small transcript (< 50 turns): < 10ms
- Medium transcript (50-200 turns): < 50ms
- Large transcript (200-500 turns): < 200ms
- Very large (500+ turns): < 500ms

**If slower than this:**

1. **Check transcript size** - May be unusually large
2. **Check system resources** - CPU/memory constraints
3. **Report performance issue** - May need optimization

**Workaround:**
Temporarily disable compaction checks if blocking work:

```bash
# In considerations.yaml
enabled: false
```

## Metrics Interpretation

Compaction events expose metrics for monitoring session health.

### Key Metrics

**compaction.detected**

- **Type:** Counter
- **Meaning:** Number of compaction events across all sessions
- **Good:** Low rate (< 10% of sessions)
- **Concerning:** High rate (> 50% of sessions) - sessions too long

**compaction.validation.passed**

- **Type:** Counter
- **Meaning:** Compactions where critical data was preserved
- **Good:** High rate (> 95%)
- **Concerning:** Low rate (< 80%) - data loss issues

**compaction.validation.failed**

- **Type:** Counter
- **Meaning:** Compactions where critical data was lost
- **Good:** Low rate (< 5%)
- **Concerning:** High rate (> 20%) - validation issues

**compaction.turn_at_compaction**

- **Type:** Histogram
- **Meaning:** Distribution of when compaction occurs
- **Typical:** p50 = 400-600 turns, p95 = 800-1000 turns
- **Concerning:** p50 < 200 turns - compaction too early

**compaction.messages_removed**

- **Type:** Histogram
- **Meaning:** How many messages removed per compaction
- **Typical:** p50 = 50-100 messages, p95 = 200-300 messages
- **Concerning:** p95 > 500 messages - large context loss

### Alerting Thresholds

**Warning alerts:**

- Compaction validation failure rate > 10%
- Average turn at compaction < 300 turns
- Messages removed p95 > 400

**Critical alerts:**

- Compaction validation failure rate > 25%
- Any crashes during validation
- Validation duration p95 > 1 second

### Using Metrics

**Monitor session health:**

```python
from power_steering_checker import CompactionValidator

# Track compaction rate
sessions_with_compaction = 0
total_sessions = 0

for session in sessions:
    total_sessions += 1
    ctx = validator.get_compaction_context(session.transcript)
    if ctx.detected:
        sessions_with_compaction += 1

compaction_rate = sessions_with_compaction / total_sessions
print(f"Compaction rate: {compaction_rate:.1%}")

# Alert if too high
if compaction_rate > 0.5:
    print("⚠️  Warning: High compaction rate - sessions too long")
```

**Track validation quality:**

```python
validation_failures = 0
validation_total = 0

for session in sessions:
    ctx = validator.get_compaction_context(session.transcript)
    if ctx.detected:
        validation_total += 1
        if not ctx.validation_passed:
            validation_failures += 1

if validation_total > 0:
    failure_rate = validation_failures / validation_total
    print(f"Validation failure rate: {failure_rate:.1%}")

    if failure_rate > 0.25:
        print("❌ Critical: High validation failure rate")
```

## Best Practices

### For Users

**DO:**

- ✅ Commit code frequently (creates recovery points)
- ✅ Mark TODOs complete as you finish them
- ✅ Restate objectives after major milestones
- ✅ End sessions after logical completion points
- ✅ Use completion evidence (tests, commits) over memory

**DON'T:**

- ❌ Ignore compaction warnings
- ❌ Continue working without addressing validation failures
- ❌ Assume all context is preserved forever
- ❌ Let sessions grow beyond 1000 turns regularly

### For Teams

**DO:**

- ✅ Version control `considerations.yaml` for consistency
- ✅ Monitor compaction metrics across team
- ✅ Share session length best practices
- ✅ Use checkpoints (commits) as recovery points

**DON'T:**

- ❌ Disable compaction validation without good reason
- ❌ Ignore high compaction rates (indicates process issues)
- ❌ Block sessions on compaction (use warnings)

## FAQ

**Q: Will compaction lose my code?**

A: No. Compaction only removes conversation messages. Your code changes are preserved in files and git commits, which exist outside the conversation context.

**Q: Should I end my session when compaction is detected?**

A: Not necessarily. If validation passes (critical data preserved), you can continue working normally. Only consider ending if validation fails or context feels too fragmented.

**Q: Can I prevent compaction?**

A: Not directly - it's automatic when context approaches limits. However, you can reduce session length by committing work frequently and ending sessions after milestones.

**Q: What if I disagree with the validation failure?**

A: If you believe validation incorrectly flagged data loss, explicitly state that context is sufficient and continue. The validation is advisory (warning level by default), not blocking.

**Q: Does compaction affect power-steering's other checks?**

A: No. Other considerations (tests, CI, TODO completion) work normally. They analyze the current transcript, whether or not compaction occurred.

**Q: Can I see what was removed during compaction?**

A: No - removed messages are gone. However, the diagnostics show approximately when compaction occurred (turn number) and how many messages were removed.

**Q: Is compaction the same as token limits?**

A: Yes - compaction occurs to stay within Claude's context window limits (approximately 1M tokens input).

---

**See also:**

- [Compaction API Reference](./power_steering_compaction_api.md) - Developer documentation
- [How to Customize Power-Steering](../.claude/tools/amplihack/HOW_TO_CUSTOMIZE_POWER_STEERING.md#compaction-handling) - Configuration guide

**Version:** v1.0
**Status:** Implemented
**Last Updated:** 2026-01-22
