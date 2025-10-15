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

# Alias: launch command also supports auto mode
amplihack launch --auto -- -p "fix all failing tests"
```

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

### Session Logging

All auto mode sessions are logged to:

```
.claude/runtime/logs/auto_{sdk}_{timestamp}/
  ├── auto.log          # Turn-by-turn log
  └── DECISIONS.md      # Decision records (if any)
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
