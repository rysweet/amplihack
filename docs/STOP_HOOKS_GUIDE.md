# Stop Hooks Guide - Amplihack

Complete guide to understanding and using stop hooks in the amplihack framework.

## Table of Contents

- [Overview](#overview)
- [What Are Stop Hooks?](#what-are-stop-hooks)
- [Currently Configured Hooks](#currently-configured-hooks)
- [Stop Hook in Detail](#stop-hook-in-detail)
- [Lock-Based Continuous Work Mode](#lock-based-continuous-work-mode)
- [Hook Metrics](#hook-metrics)
- [Configuration](#configuration)
- [Related Documentation](#related-documentation)

## Overview

Amplihack uses Claude Code's hook system to extend functionality and control Claude's behavior. **Stop hooks** are particularly important as they determine whether Claude can stop working or must continue pursuing the user's objectives.

## What Are Stop Hooks?

Stop hooks intercept Claude Code's attempt to end a conversation turn. They can:

- **Approve** the stop (allow Claude to finish)
- **Block** the stop (force Claude to continue working)
- **Trigger additional actions** (like reflection analysis)

This enables powerful workflows like:
- Continuous work mode (lock-based execution)
- Automatic quality checks before stopping
- Session reflection and learning

## Currently Configured Hooks

Amplihack configures **4 types of hooks** (from `.claude/settings.json`):

### 1. Stop Hook (`stop.py`)

**Trigger:** Every time Claude Code wants to stop/end a turn

**Primary Functions:**
1. **Lock-based Continuous Work Mode**
   - Checks for `.claude/runtime/locks/.lock_active` file
   - If lock exists: BLOCKS stop and forces Claude to continue
   - If no lock: Allows stop to proceed

2. **Reflection Trigger**
   - Optionally triggers reflection analysis when stopping
   - Creates `.reflection_pending` marker for later processing

**Timeout:** 30 seconds

### 2. SessionStart Hook (`session_start.py`)

**Trigger:** When a new Claude Code session starts

**Functions:**
- Captures original user request for substantial prompts
- Records session start metrics
- Initializes context preservation

### 3. PostToolUse Hook (`post_tool_use.py`)

**Trigger:** After every tool use (Read, Write, Bash, etc.)

**Functions:**
- Tracks tool usage statistics
- Categorizes operations (bash, file ops, search ops)
- Detects and logs tool errors

### 4. PreCompact Hook (`pre_compact.py`)

**Trigger:** Before Claude Code compacts conversation context

**Functions:**
- Exports full conversation transcript
- Prevents loss of conversation history
- Creates backup in transcripts directory

**Timeout:** 30 seconds

## Stop Hook in Detail

### Decision Flow

```
Claude wants to stop
       ↓
Stop hook checks: Does .lock_active exist?
       ↓
    YES → BLOCK STOP
          • Return {"decision": "block"}
          • Claude keeps working
          • Looks for TODOs/next steps
       ↓
    NO → Check reflection config
         ↓
         Reflection enabled? → Create .reflection_pending marker
         ↓
         Allow stop → Return {"decision": "approve"}
```

### Lock File Behavior

**Lock File Location:**
```
.claude/runtime/locks/.lock_active
```

**When Lock is Active:**
```python
{
  "decision": "block",
  "reason": "we must keep pursuing the user's objective and must not stop the turn - look for any additional TODOs, next steps, or unfinished work and pursue it diligently in as many parallel tasks as you can"
}
```

**When Lock is Inactive:**
```python
{
  "decision": "approve"
}
```

### Fail-Safe Design

If the lock file cannot be accessed (permissions error, filesystem issue):
- **Default:** Allow stop (fail-safe)
- **Logging:** Warning logged to hook metrics
- **Rationale:** Don't block Claude if system is having issues

## Lock-Based Continuous Work Mode

### How It Works

1. **Lock Created:** When auto mode or a workflow needs continuous execution
2. **Stop Blocked:** Every stop attempt is intercepted and blocked
3. **Claude Continues:** Claude searches for TODOs, next steps, unfinished work
4. **Lock Removed:** When work is complete or user intervenes
5. **Stop Allowed:** Normal stop behavior resumes

### Lock Creation

The lock is typically created by:
- **Auto Mode:** `.claude/tools/amplihack/auto_mode.py`
- **Manual Commands:** User or workflow scripts
- **Worktrees:** Multi-step workflow execution

### Lock Management

**Create Lock:**
```bash
mkdir -p .claude/runtime/locks
touch .claude/runtime/locks/.lock_active
```

**Remove Lock:**
```bash
rm .claude/runtime/locks/.lock_active
```

**Check Lock Status:**
```bash
test -f .claude/runtime/locks/.lock_active && echo "LOCKED" || echo "UNLOCKED"
```

## Reflection System

### How Reflection Works

Reflection is an automatic learning system that analyzes completed sessions to identify improvement opportunities. Here's the complete flow:

#### Phase 1: Trigger (Stop Hook)

1. **Stop Event:** Claude Code wants to stop/end turn
2. **Lock Check:** Stop hook checks if `.lock_active` exists
3. **No Lock:** Stop is allowed, trigger reflection
4. **Check Config:** Reads `.claude/tools/amplihack/.reflection_config`
5. **Verify Enabled:** Only continues if `enabled: true`
6. **Prevent Duplicates:** Checks for `.reflection_lock` file
7. **Create Marker:** Creates `.reflection_pending` for later processing

#### Phase 2: Reflection Analysis (Async)

The reflection system analyzes the session using `SessionReflector` class:

**Analysis Components:**

1. **Pattern Detection:**
   - **Repeated Commands** - Same tool used 3+ times (suggests automation opportunity)
   - **Error Patterns** - Errors/failures appearing 3+ times (suggests error handling gap)
   - **Long Sessions** - 100+ messages (suggests task needs decomposition)
   - **Frustration Indicators** - Keywords like "doesn't work", "still failing", "stuck"
   - **Repeated Reads** - Same file read 5+ times (suggests caching opportunity)

2. **Claude-Trace Log Analysis** (if available):
   - **API Errors** - HTTP errors, connection failures
   - **Rate Limits** - 429 status codes
   - **Slow Requests** - Requests taking >30 seconds
   - **Token Usage** - Total input/output tokens consumed

3. **Metrics Extraction:**
   - Total messages in session
   - Tool use count
   - User vs assistant message ratio

#### Phase 3: Findings Presentation

```
SESSION REFLECTION ANALYSIS
======================================================================

Session Metrics:
  Total messages: 45
  Tool uses: 23

Claude-Trace Analysis:
  Token usage: 125000 input, 8500 output
  API errors: 0
  Rate limit hits: 0
  Slow requests (>30s): 2

Patterns Detected: 3

  1. REPEATED_TOOL_USE
     → Used bash 8 times. Consider creating a tool or script
     tool: bash
     count: 8

  2. LONG_SESSION
     → Consider breaking into smaller, focused tasks
     message_count: 120

  3. SLOW_REQUESTS
     → Optimize prompts or break down complex requests
     count: 2

Suggestions:
  1. Consider creating a script to automate these bash commands.
  2. Long session detected. Future tasks could benefit from better decomposition.
```

#### Phase 4: User Approval (Interactive)

If reflection findings are significant:

```
Create GitHub issues for these improvements? (y/n/select)
  y - Create issues for all suggestions
  n - Skip issue creation
  select - Choose specific suggestions

Your choice: _
```

#### Phase 5: GitHub Issue Creation (Optional)

For each approved pattern:
1. **Generate Issue:** Uses `reflection_issue_template.py` to create structured issue
2. **Create via GitHub API:** Uses `github_issue.py` module
3. **Track Results:** Records issue numbers and URLs

Example created issue:
```
Title: Improvement: Consider creating script for repeated bash commands
Labels: improvement, automation, reflection
Body: [Pattern details, suggestions, context from session]
```

#### Phase 6: Summary Save

All reflection results saved to:
```
.claude/runtime/logs/<session_id>/reflection_summary.json
```

### Reflection Files and Directories

```
.claude/tools/amplihack/.reflection_config          # Configuration (enable/disable)
.claude/runtime/reflection/.reflection_lock         # Prevents concurrent runs
.claude/runtime/reflection/.reflection_pending      # Queues reflection
.claude/runtime/logs/<session_id>/reflection_summary.json # Results
.claude-trace/*.jsonl                               # API traffic logs
```

### Reflection Configuration

**Config File:** `.claude/tools/amplihack/.reflection_config`

```json
{
  "enabled": true,
  "triggers": ["session_end"],
  "min_turns": 5
}
```

**Options:**
- `enabled` - Master on/off switch (default: false)
- `triggers` - When to trigger reflection (currently only "session_end")
- `min_turns` - Minimum conversation length to analyze (prevents trivial session analysis)

### Loop Prevention

**Critical Safety Feature:** `CLAUDE_REFLECTION_MODE` environment variable

Reflection sets `CLAUDE_REFLECTION_MODE=1` when running to prevent:
- Reflection analyzing itself
- Infinite recursion
- Claude Code session within Claude Code session

```python
# In reflection.py line 78
self.enabled = os.environ.get("CLAUDE_REFLECTION_MODE") != "1"
```

If this variable is set, reflection is completely disabled.

## Hook Metrics

All hooks save metrics to `.claude/runtime/metrics/`:

### Stop Hook Metrics

| Metric | Description |
|--------|-------------|
| `lock_blocks` | Number of times stop was blocked by lock |
| `reflection_triggered` | Number of times reflection was triggered |

### Other Hook Metrics

| Hook | Metrics |
|------|---------|
| SessionStart | `prompt_length` |
| PostToolUse | `tool_usage`, `bash_commands`, `file_operations`, `search_operations` |
| PreCompact | `conversation_exports` |

### Viewing Metrics

```bash
# View all metrics
ls -la .claude/runtime/metrics/

# View specific metric file
cat .claude/runtime/metrics/stop_hook_metrics.jsonl
```

## Configuration

### Hook Configuration File

Location: `.claude/settings.json`

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/tools/amplihack/hooks/stop.py",
            "timeout": 30000
          }
        ]
      }
    ]
  }
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_PROJECT_DIR` | Auto-set by Claude Code | Project root |
| `AMPLIHACK_DEBUG` | Enable debug logging | `false` |

### Timeout Configuration

**Stop Hook Timeout:** 30 seconds (30000 ms)

This timeout ensures:
- Hook has time to check files
- Lock detection is reliable
- Reflection config can be read
- But won't hang indefinitely

## Use Cases

### Use Case 1: Continuous Implementation

**Scenario:** User wants Claude to implement a complete feature without stopping

**Setup:**
```bash
# Create lock before starting work
mkdir -p .claude/runtime/locks
touch .claude/runtime/locks/.lock_active

# Start Claude Code with task
claude "Implement user authentication system"
```

**Behavior:**
- Claude implements authentication
- Tries to stop after initial implementation
- Stop hook blocks the stop
- Claude continues: adds tests, documentation, error handling
- Keeps working until lock is removed or work is exhausted

**Remove Lock:**
```bash
rm .claude/runtime/locks/.lock_active
```

### Use Case 2: Multi-Step Workflows

**Scenario:** Execute a complex workflow with multiple phases

**Implementation:**
```bash
#!/bin/bash
# workflow.sh

# Create lock
touch .claude/runtime/locks/.lock_active

# Run workflow
claude "Phase 1: Design architecture
Phase 2: Implement core logic
Phase 3: Add tests
Phase 4: Create documentation"

# Lock keeps Claude working through all phases
# Remove lock when done
rm .claude/runtime/locks/.lock_active
```

### Use Case 3: Session Reflection

**Scenario:** Automatically analyze and learn from completed sessions

**Setup:** Enable reflection in `.claude/tools/amplihack/.reflection_config`:
```json
{
  "enabled": true
}
```

**Behavior:**
- User completes work with Claude
- Claude finishes and tries to stop
- Stop hook allows stop (no lock)
- Reflection trigger creates `.reflection_pending`
- Reflection analysis runs later (asynchronously)

## Troubleshooting

### Stop Hook Not Blocking

**Symptoms:** Lock exists but Claude still stops

**Possible Causes:**
1. Lock file path incorrect
2. Permissions issue reading lock
3. Hook not configured
4. Hook timeout expired

**Solutions:**
```bash
# Verify lock file exists
ls -la .claude/runtime/locks/.lock_active

# Check hook configuration
cat .claude/settings.json | grep -A5 "Stop"

# Check hook logs
cat .claude/runtime/logs/*/hook_logs.txt
```

### Hook Timeout Errors

**Symptoms:** Hook execution fails with timeout

**Cause:** Hook taking longer than 30 seconds

**Solutions:**
1. Check for slow filesystem access
2. Verify hook scripts are executable
3. Review hook logs for bottlenecks
4. Consider increasing timeout in settings

### Reflection Not Triggering

**Symptoms:** Stop allowed but no reflection

**Possible Causes:**
1. Reflection disabled in config
2. Reflection already running (lock exists)
3. Config file missing

**Solutions:**
```bash
# Check config
cat .claude/tools/amplihack/.reflection_config

# Verify no concurrent reflection
ls .claude/runtime/reflection/.reflection_lock

# Check reflection pending marker
ls .claude/runtime/reflection/.reflection_pending
```

## Best Practices

### 1. Use Locks Judiciously

**Do:**
- Use locks for multi-step workflows
- Remove locks when work is complete
- Document why lock is needed

**Don't:**
- Leave locks active indefinitely
- Use locks for simple tasks
- Forget to remove locks

### 2. Monitor Lock Status

```bash
# Add to your workflow scripts
if [ -f .claude/runtime/locks/.lock_active ]; then
    echo "⚠️  Lock is active - continuous work mode enabled"
else
    echo "✅ No lock - normal stop behavior"
fi
```

### 3. Graceful Lock Cleanup

```bash
# Cleanup script
cleanup() {
    echo "Cleaning up locks..."
    rm -f .claude/runtime/locks/.lock_active
}

# Register cleanup on exit
trap cleanup EXIT
```

### 4. Test Hook Behavior

```bash
# Test stop hook without lock
rm -f .claude/runtime/locks/.lock_active
claude "Quick test"
# Should stop normally

# Test stop hook with lock
touch .claude/runtime/locks/.lock_active
claude "Test with lock"
# Should continue working

# Cleanup
rm .claude/runtime/locks/.lock_active
```

## Architecture

### Hook Processor Base Class

All hooks inherit from `HookProcessor` (in `hook_processor.py`):

**Features:**
- Unified logging
- Metric collection
- Session ID management
- Error handling
- JSON I/O handling

**Benefits:**
- Consistent behavior across hooks
- Reduced code duplication
- Easier testing and maintenance

### Stop Hook Implementation

**File:** `.claude/tools/amplihack/hooks/stop.py`

**Key Components:**
1. **Lock Detection** (lines 24-26)
2. **Stop Blocking Logic** (lines 44-51)
3. **Reflection Trigger** (lines 53-100)
4. **Fail-Safe Handling** (lines 38-42)

## Related Documentation

- [Hook Configuration Guide](HOOK_CONFIGURATION_GUIDE.md) - Complete hook setup instructions
- [Auto Mode Documentation](AUTO_MODE.md) - Continuous work mode details
- [DEVELOPING_AMPLIHACK.md](DEVELOPING_AMPLIHACK.md) - Developer guide
- [HOOK_PATTERNS.md](.claude/runtime/analysis/hook_patterns_from_amplifier.md) - Hook design patterns

## Advanced Topics

### Custom Stop Conditions

You can extend the stop hook to add custom stop conditions:

```python
def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    # Check lock (existing)
    if self.lock_flag.exists():
        return {"decision": "block", "reason": "..."}

    # Add custom condition
    if self._has_failing_tests():
        return {
            "decision": "block",
            "reason": "Tests are failing - must fix before stopping"
        }

    # Allow stop
    return {"decision": "approve"}
```

### Stop Hook Chaining

Multiple hooks can be chained for complex logic:

```json
{
  "Stop": [
    {
      "hooks": [
        {"type": "command", "command": "check_lock.py"},
        {"type": "command", "command": "check_tests.py"},
        {"type": "command", "command": "check_quality.py"}
      ]
    }
  ]
}
```

All hooks must approve for stop to proceed.

### Metrics-Based Decisions

Use accumulated metrics to inform stop decisions:

```python
# Example: Block stop if productivity is low
metrics = self.load_metrics()
if metrics.get("tool_usage_count", 0) < 5:
    return {
        "decision": "block",
        "reason": "Not enough work done yet - keep going!"
    }
```

## Summary

**Stop hooks** are the gatekeeper of Claude Code sessions:

- **Approve Mode:** Normal stop behavior
- **Block Mode:** Continuous work until objectives met
- **Lock-Based Control:** Simple file-based state management
- **Fail-Safe Design:** Always allow stop if system has issues
- **Metrics Collection:** Track hook behavior for analysis

The design philosophy: **Ruthless simplicity with powerful capabilities.**

---

**Questions?** File an issue at: https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues
