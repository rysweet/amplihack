# Auto Mode Documentation

Auto mode enables autonomous agentic loops with Claude Code or GitHub Copilot CLI, allowing AI to work through multi-turn workflows with minimal human intervention.

## Overview

Auto mode orchestrates an intelligent loop that:

1. Clarifies objectives with measurable evaluation criteria
2. Creates detailed execution plans identifying parallel opportunities
3. Executes plans autonomously through multiple turns
4. Evaluates progress after each turn
5. Continues until objective achieved or max turns reached
6. Provides comprehensive summary of work completed

## Usage

### With Claude Code

```bash
# Basic auto mode
amplihack claude --auto -- -p "implement user authentication"

# With custom max turns
amplihack claude --auto --max-turns 20 -- -p "refactor the API module"

# With interactive UI (requires Rich library)
amplihack claude --auto --ui -- -p "implement user authentication"

# Alias: launch command also supports auto mode
amplihack launch --auto -- -p "fix all failing tests"
```

### Interactive UI Mode (`--ui`)

Auto mode supports an optional interactive terminal UI that displays real-time progress with:

- Session title and details (turn counter, elapsed time, cost tracking)
- Todo list with status indicators
- Streaming log output
- Interactive controls (pause, resume, exit)

**Installing UI Dependencies:**

The UI feature requires the Rich library. Install it with:

```bash
# Install with optional UI dependencies
pip install 'amplihack[ui]'

# Or install Rich directly
pip install 'rich>=13.0.0'
```

**Usage:**

```bash
# Enable interactive UI
amplihack claude --auto --ui -- -p "implement user authentication"
```

**What happens if Rich is not installed:**

If you use the `--ui` flag without Rich installed, auto mode will display a helpful error message and continue in non-UI mode:

```
⚠️  WARNING: --ui flag requires Rich library
   Error: No module named 'rich'

   To enable TUI mode, install Rich:
     pip install 'amplihack[ui]'
   or:
     pip install rich>=13.0.0

   Continuing in non-UI mode...
```

This ensures auto mode always works, whether Rich is installed or not.

### With GitHub Copilot CLI

```bash
# Basic auto mode
amplihack copilot --auto -- -p "add logging to all services"

# With custom max turns
amplihack copilot --auto --max-turns 15 -- -p "implement feature X"
```

## How It Works

### Turn 1: Objective Clarification

Auto mode starts by transforming your prompt into a clear objective with evaluation criteria.

**Input**: Your prompt
**Output**:

- Clear objective statement
- Measurable evaluation criteria
- Key constraints

### Turn 2: Plan Creation

Creates a detailed execution plan identifying parallel work opportunities.

**Output**:

- Step-by-step plan
- Parallel execution groups
- Dependencies between steps
- Complexity estimates

### Turns 3+: Execute & Evaluate Loop

Iteratively executes the plan and evaluates progress.

**Each turn**:

1. Execute next part of plan
2. Evaluate if objective achieved
3. Continue or complete based on evaluation

### Final Turn: Summary

Provides comprehensive summary of the auto mode session.

**Summary includes**:

- What was accomplished
- What remains (if anything)
- Key decisions made
- Files modified
- Tests run

## Configuration

### Max Turns

Default: 10 turns

Adjust based on task complexity:

- Simple tasks: 5-10 turns
- Medium tasks: 10-15 turns
- Complex tasks: 15-30 turns

```bash
amplihack claude --auto --max-turns 25 -- -p "complex multi-module refactoring"
```

### Per-Turn Timeout

Default: 30 minutes per turn

Controls how long each turn can run before timing out. This prevents runaway executions while allowing complex operations to complete.

**Priority order (highest to lowest):**

1. `--no-timeout` flag (disables timeout entirely)
2. Explicit `--query-timeout-minutes` value
3. Auto-detection (Opus models → 60 minutes)
4. Default (30 minutes)

```bash
# Use default 30-minute timeout
amplihack claude --auto -- -p "implement feature"

# Explicit timeout (45 minutes)
amplihack claude --auto --query-timeout-minutes 45 -- -p "complex refactoring"

# Disable timeout for very long operations
amplihack claude --auto --no-timeout -- -p "comprehensive codebase analysis"

# Opus model auto-detects to 60 minutes
amplihack claude --auto -- --model opus -p "architectural design"
```

**Note:** Opus models automatically use 60-minute timeouts due to extended thinking requirements. Use `--no-timeout` for operations expected to exceed 60 minutes.

### Session Logging

All auto mode sessions are logged to:

```
.claude/runtime/logs/auto_{sdk}_{timestamp}/
  ├── auto.log          # Turn-by-turn log
  ├── prompt.md         # Original prompt and session metadata
  ├── DECISIONS.md      # Decision records (if any)
  ├── append/           # Pending instructions (for --append feature)
  └── appended/         # Processed instructions (archived)
```

## Examples

### Example 1: Implementing a Feature

```bash
amplihack claude --auto -- -p "Implement user profile editing with validation and persistence"
```

**What happens**:

1. Clarifies requirements for profile editing feature
2. Plans: API endpoint, validation logic, database updates, tests
3. Executes: Implements each component
4. Evaluates: Checks tests pass, requirements met
5. Completes: Summarizes implementation

### Example 2: Bug Fix

```bash
amplihack copilot --auto --max-turns 5 -- -p "Fix the login timeout issue reported in issue #123"
```

**What happens**:

1. Clarifies the timeout bug and success criteria
2. Plans: Investigate cause, implement fix, add tests
3. Executes: Identifies issue, applies fix
4. Evaluates: Verifies fix resolves timeout
5. Completes: Documents fix and tests

### Example 3: Refactoring

```bash
amplihack claude --auto --max-turns 15 -- -p "Refactor authentication module to use dependency injection"
```

**What happens**:

1. Clarifies refactoring scope and constraints
2. Plans: Update interfaces, modify implementations, update tests
3. Executes: Refactors module incrementally
4. Evaluates: Ensures all tests pass, no regressions
5. Completes: Documents refactoring decisions

### Example 4: Test Suite Creation

```bash
amplihack copilot --auto -- -p "Add comprehensive test coverage for the payment processing module"
```

**What happens**:

1. Clarifies coverage goals and test types needed
2. Plans: Unit tests, integration tests, edge cases
3. Executes: Writes test suite
4. Evaluates: Checks coverage percentage, test quality
5. Completes: Reports final coverage metrics

## Injecting Instructions Mid-Session

You can append new instructions to a running auto mode session without interrupting it using the `--append` flag. This allows you to steer the agent's work in real-time as you observe its progress.

### Usage

```bash
# Terminal 1: Start auto mode
amplihack claude --auto -- -p "Implement user authentication"

# Terminal 2: After reviewing initial work, append a new instruction
amplihack claude --append "Also add rate limiting to prevent brute force attacks"

# Terminal 2: Add another instruction
amplihack claude --append "Ensure all passwords are hashed with bcrypt"
```

### How It Works

1. The `--append` flag finds the active auto mode session in the current project
2. It writes your instruction to `.claude/runtime/logs/auto_<sdk>_<timestamp>/append/<timestamp>.md`
3. Before the next turn, auto mode reads and processes all instructions in the `append/` directory
4. The instructions are integrated into the turn prompt as additional requirements
5. Processed instruction files are moved to `appended/` directory for tracking

### Example Workflow

```bash
# Start auto mode with initial task
$ amplihack claude --auto --max-turns 20 -- -p "Implement user authentication system"

# Watch progress in logs
$ tail -f .claude/runtime/logs/auto_claude_*/auto.log

# After turn 3, you realize you need additional security
$ amplihack claude --append "Add two-factor authentication support"
✓ Instruction appended to session: auto_claude_1729699200
  File: 20241023_120534_123456.md
  The auto mode session will process this on its next turn.

# Add another requirement
$ amplihack claude --append "Include comprehensive input validation for all forms"
✓ Instruction appended to session: auto_claude_1729699200
  File: 20241023_120612_789012.md
  The auto mode session will process this on its next turn.
```

### Best Practices for Appending

1. **Be Specific**: Appended instructions are added as-is. Be clear and specific about what you want.

   **Good**: `amplihack claude --append "Add input validation that checks password length is at least 12 characters"`

   **Less Good**: `amplihack claude --append "improve security"`

2. **Timing**: Instructions are processed before the next turn starts. Wait for the current turn to complete before expecting the new instruction to take effect.

3. **Multiple Instructions**: You can append multiple instructions - they queue in order and are all processed before the next turn.

4. **Monitor Progress**: Watch the logs to see when your appended instructions are processed:

   ```bash
   tail -f .claude/runtime/logs/auto_claude_*/auto.log
   ```

5. **Review Appended History**: Check what has been processed:
   ```bash
   ls -la .claude/runtime/logs/auto_claude_*/appended/
   cat .claude/runtime/logs/auto_claude_*/appended/*.md
   ```

### Troubleshooting Append

**Error: No active auto mode session found**

- **Cause**: No auto mode is currently running in this project
- **Solution**: Start an auto mode session first with `amplihack claude --auto -- -p "your task"`

**Instruction not being processed**

- **Cause**: Auto mode may have completed before processing
- **Solution**: Check if auto mode reached max turns or completed the objective. Review logs to see what happened.

**Multiple sessions detected**

- **Behavior**: The system will use the most recent auto mode session
- **Tip**: Only run one auto mode session per project to avoid confusion

### Security and Limits

The append feature includes several security controls:

- **Size Limit**: Instructions are limited to 100KB each
- **Rate Limiting**: Maximum 10 appends per minute, 100 pending instructions total
- **Content Sanitization**: Suspicious patterns are detected and sanitized before injection
- **File Permissions**: Instruction files are created with restrictive permissions (owner-only)

### Log Directory Structure

When using the append feature, your log directory will have this structure:

```
.claude/runtime/logs/auto_claude_1729699200/
├── auto.log              # Turn-by-turn execution log
├── prompt.md             # Original prompt and session metadata
├── DECISIONS.md          # Decision records (if any)
├── append/               # Pending instructions (waiting to be processed)
│   ├── 20241023_120534_123456.md
│   └── 20241023_120612_789012.md
└── appended/             # Processed instructions (archived)
    └── 20241023_120455_000000.md
```

## Best Practices

### 1. Be Specific in Your Prompt

**Good**:

```bash
amplihack claude --auto -- -p "Add rate limiting to the API with 100 requests per minute per user"
```

**Less Good**:

```bash
amplihack claude --auto -- -p "improve the API"
```

### 2. Set Appropriate Max Turns

Match max turns to task complexity:

- Quick fixes: 3-5 turns
- Feature implementation: 10-15 turns
- Major refactoring: 20-30 turns

### 3. Let Auto Mode Work

Don't interrupt the process. Auto mode is designed to work autonomously. Check the logs afterward to see what was done.

### 4. Review Before Committing

Auto mode implements changes but doesn't commit them. Always:

1. Review the changes made
2. Run final tests manually
3. Verify quality before committing

### 5. Use for Repetitive Tasks

Auto mode excels at:

- Adding tests to multiple files
- Refactoring patterns across codebase
- Implementing similar features
- Fixing categories of bugs

## Troubleshooting

### Auto Mode Stops Early

**Cause**: Objective achieved before max turns
**Solution**: This is normal - check the summary

### Reaches Max Turns

**Cause**: Task more complex than estimated
**Solution**:

- Increase `--max-turns`
- Break task into smaller subtasks
- Review what was completed and continue manually

### Execution Errors

**Cause**: Syntax errors, test failures during execution
**Solution**: Auto mode logs errors and continues. Review logs in `.claude/runtime/logs/` to see what happened.

### Turn Timeouts

**Cause**: A turn exceeded the per-turn timeout (default 30 minutes)
**Solution**:

- Check logs for `Turn N timed out after X seconds`
- For Opus models, ensure auto-detection is working (uses 60 min automatically)
- Use `--query-timeout-minutes 60` for longer operations
- Use `--no-timeout` for very long operations (use with caution)
- Consider breaking complex tasks into smaller subtasks

### Installation Issues (Copilot)

**Cause**: GitHub Copilot CLI not installed
**Solution**: Auto mode will attempt to install via npm. Ensure Node.js and npm are installed.

## Hooks Integration

### Session Start Hook

Runs at the beginning of auto mode session.

- Location: `.claude/tools/amplihack/hooks/session_start.py`
- Use: Initialize session logging, set up environment

### Stop Hook

Runs at the end of auto mode session.

- Location: `.claude/tools/amplihack/hooks/stop.py`
- Use: Cleanup, final logging, metrics collection

**Note**: Only `session_start` and `stop` hooks run in auto mode. Tool-use hooks aren't supported.

## Advanced Usage

### Combining with Subagents

Auto mode automatically leverages subagents when appropriate. You can guide this in your prompt:

```bash
amplihack claude --auto -- -p "Use the architect agent to design a caching layer, then the builder agent to implement it"
```

### Parallel Execution

Auto mode identifies parallel work opportunities. Help it by structuring your prompt:

```bash
amplihack copilot --auto -- -p "Add logging to all three services: auth, payment, and notification - these can be done in parallel"
```

### Continuing Work

If auto mode runs out of turns, you can continue manually or start a new auto mode session with adjusted objectives:

```bash
# First session
amplihack claude --auto --max-turns 10 -- -p "implement feature X"

# If incomplete, refine and continue
amplihack claude --auto --max-turns 10 -- -p "complete feature X implementation: finish the API endpoint and add tests"
```

## Comparison: Claude vs Copilot

### Claude Auto Mode

- Tighter integration with Claude Code features
- Supports `--continue` flag for context preservation
- Automatic hook execution
- Better for complex, multi-file changes

### Copilot Auto Mode

- Works with GitHub Copilot CLI
- Requires explicit subagent invocation
- Manual hook execution
- Good for focused, specific tasks

## Tips

1. **Start small**: Test auto mode with simpler tasks first
2. **Monitor logs**: Check `.claude/runtime/logs/` to understand what auto mode is doing
3. **Iterate prompts**: Refine your prompts based on results
4. **Use max-turns wisely**: Don't set too high - better to run multiple focused sessions
5. **Trust the process**: Let auto mode work through its turns autonomously

## See Also

- `AGENTS.md` - Guide for using subagents with Copilot CLI
- `.claude/workflow/DEFAULT_WORKFLOW.md` - Standard workflow steps
- `.claude/context/PHILOSOPHY.md` - Development principles

---

Auto mode brings autonomous agent capabilities to your development workflow, handling multi-turn tasks with minimal intervention while maintaining quality and following best practices.
