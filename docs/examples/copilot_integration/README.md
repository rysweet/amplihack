# GitHub Copilot CLI Integration Examples

This directory contains examples for using amplihack with GitHub Copilot CLI.

## Basic Usage Examples

### Example 1: Interactive Copilot

Launch GitHub Copilot CLI interactively:

```bash
amplihack copilot
```

This starts Copilot in interactive mode with all tools enabled.

### Example 2: Single Prompt

Run Copilot with a single prompt:

```bash
amplihack copilot -- -p "explain how the authentication module works"
```

### Example 3: Auto Mode - Simple Task

Use auto mode for a simple task:

```bash
amplihack copilot --auto -- -p "add type hints to all functions in utils.py"
```

### Example 4: Auto Mode - Feature Implementation

Use auto mode to implement a feature:

```bash
amplihack copilot --auto --max-turns 15 -- -p "add user profile API endpoint with GET and PUT methods, including validation and tests"
```

### Example 5: Auto Mode - Bug Fix

Use auto mode to fix a bug:

```bash
amplihack copilot --auto --max-turns 5 -- -p "fix the race condition in the cache update logic"
```

## Claude vs Copilot Examples

### Using Claude (Traditional)

```bash
# Interactive
amplihack claude

# With prompt
amplihack claude -- -p "refactor the database module"

# Auto mode
amplihack claude --auto -- -p "implement caching layer"
```

### Using Copilot (New)

```bash
# Interactive
amplihack copilot

# With prompt
amplihack copilot -- -p "refactor the database module"

# Auto mode
amplihack copilot --auto -- -p "implement caching layer"
```

## Subagent Invocation with Copilot

When using Copilot CLI (not in auto mode), you can manually invoke subagents:

```bash
copilot --allow-all-tools -p "Include @.claude/agents/amplihack/core/architect.md -- Design a caching layer for the API"
```

Or use commands:

```bash
copilot --allow-all-tools -p "Include @.claude/commands/amplihack/test.md -- Run all unit tests"
```

## Auto Mode Example Workflow

Here's what happens when you run:

```bash
amplihack copilot --auto --max-turns 10 -- -p "add logging to the payment service"
```

**Turn 1**: Clarifies objective

```
Objective: Add comprehensive logging to payment service
Criteria:
- All public methods log entry/exit
- Errors logged with full context
- Performance metrics captured
```

**Turn 2**: Creates plan

```
Step 1: Add logging imports
Step 2: Add logger configuration
Step 3: Add method entry/exit logs
Step 4: Add error logging
Step 5: Add performance logging
Step 6: Add tests for logging
```

**Turns 3-8**: Execute plan

- Implements logging incrementally
- Tests after each change
- Documents as it goes

**Turn 9**: Evaluate completion

```
Evaluation: COMPLETE
- All methods have logging
- Error handling includes logging
- Performance metrics captured
- Tests added and passing
```

**Turn 10**: Summary

```
Summary:
- Modified: payment_service.py
- Added: 15 log statements
- Added: 5 test cases
- All tests passing
```

## Testing These Examples

Before running auto mode examples, ensure you have a clean git state:

```bash
git status
git diff
```

Run a simple example first:

```bash
# Test basic Copilot launch (will try to install if needed)
amplihack copilot -- -p "what is 2+2"
```

Then try auto mode with a trivial task:

```bash
# Create a test file
echo "def add(a, b): return a + b" > test_math.py

# Use auto mode to add docstring
amplihack copilot --auto --max-turns 3 -- -p "add a docstring to the add function in test_math.py"

# Check the result
cat test_math.py

# Cleanup
rm test_math.py
```

## Troubleshooting

### Copilot Not Installed

If you see "Installing GitHub Copilot CLI...", amplihack will attempt to install it via npm.

Ensure you have Node.js and npm:

```bash
node --version
npm --version
```

### Auth Issues with Copilot

GitHub Copilot CLI may require authentication:

```bash
gh auth login
copilot --version
```

### Auto Mode Logs

Check what auto mode is doing:

```bash
# Find the latest auto mode session
ls -lt .claude/runtime/logs/ | head -5

# View the log
cat .claude/runtime/logs/auto_copilot_*/auto.log
```

## Best Practices

1. **Start small**: Try interactive mode before auto mode
2. **Test prompts**: Run with `-p` first to see how Copilot responds
3. **Review changes**: Always review what auto mode did before committing
4. **Use appropriate max-turns**: Don't set too high for simple tasks
5. **Check logs**: Review `.claude/runtime/logs/` to understand behavior

## See Also

- `../docs/AUTO_MODE.md` - Complete auto mode documentation
- `../../AGENTS.md` - Guide for Copilot CLI with amplihack
- `../../.claude/workflow/DEFAULT_WORKFLOW.md` - Standard workflow

---

These examples demonstrate the GitHub Copilot CLI integration with amplihack. Start with simple examples and progress to more complex auto mode usage as you become familiar with the capabilities.
