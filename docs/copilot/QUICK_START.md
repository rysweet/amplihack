# Enhanced Copilot Auto Mode - Quick Start

Get started with enhanced auto mode in 5 minutes.

## Prerequisites

1. **GitHub Copilot CLI** installed:
   ```bash
   which copilot  # Should return path
   ```

2. **amplihack** installed:
   ```bash
   amplihack --version
   ```

## Basic Usage

### 1. Simple Task

```bash
amplihack copilot --auto --enhanced-copilot -- -p "add logging to error handlers"
```

This will:
- Select appropriate agents (likely builder + tester)
- Clarify the objective
- Create an execution plan
- Implement the changes
- Test the implementation
- Evaluate completion

### 2. Complex Feature

```bash
amplihack copilot --auto --enhanced-copilot --max-turns 20 -- -p "implement REST API for user profiles with CRUD operations and tests"
```

This will:
- Select architect, builder, and tester agents
- Design the API structure
- Implement endpoints
- Generate comprehensive tests
- Automatically fork if it takes > 60 minutes

## Common Use Cases

### Bug Fix
```bash
amplihack copilot --auto --enhanced-copilot -- -p "fix: authentication token not being validated properly"
```

**Selected Agents**: Builder, Tester

### Refactoring
```bash
amplihack copilot --auto --enhanced-copilot -- -p "refactor database layer to use repository pattern"
```

**Selected Agents**: Architect, Builder, Reviewer

### Testing
```bash
amplihack copilot --auto --enhanced-copilot -- -p "add comprehensive tests for payment module"
```

**Selected Agents**: Tester

## Monitoring Progress

### Check Logs
```bash
# Find latest session
ls -lt .claude/runtime/logs/auto_copilot_* | head -1

# View log
tail -f .claude/runtime/logs/auto_copilot_*/auto.log
```

### Check State
```bash
# Find session state
cat .claude/runtime/copilot_sessions/*.json | jq
```

## Configuration

### Adjust Max Turns

**Small tasks** (5-10 turns):
```bash
amplihack copilot --auto --enhanced-copilot --max-turns 5 -- -p "fix typo in README"
```

**Large tasks** (20-30 turns):
```bash
amplihack copilot --auto --enhanced-copilot --max-turns 30 -- -p "rewrite authentication system"
```

## Understanding Output

### Turn Phases

1. **Clarifying**: Understanding the objective
2. **Planning**: Creating execution plan
3. **Executing**: Implementing the solution
4. **Evaluating**: Checking if complete
5. **Summarizing**: Final summary

### Completion Signals

Look for:
- `"auto-mode EVALUATION: COMPLETE"`
- `"Objective achieved!"`
- `"All criteria met"`

## Troubleshooting

### Issue: No Copilot CLI

**Error**: `copilot: command not found`

**Fix**: Install Copilot CLI:
```bash
gh extension install github/gh-copilot
```

### Issue: Enhanced Mode Not Available

**Error**: `Enhanced Copilot mode not available`

**Fix**: Ensure you're using the copilot SDK:
```bash
amplihack copilot --auto --enhanced-copilot ...  # Not 'claude' or 'codex'
```

### Issue: Session Timeout

**Problem**: Task timing out

**Solution**: Use enhanced mode (automatic forking):
```bash
# This automatically forks at 60 minutes
amplihack copilot --auto --enhanced-copilot --max-turns 30 -- -p "long task"
```

## Tips & Tricks

### 1. Be Specific

**Good**: "Implement JWT authentication with refresh tokens and proper error handling"

**Bad**: "Make login better"

### 2. Include Success Criteria

**Good**: "Add user profile API with GET, POST, PUT, DELETE endpoints and ensure all tests pass"

**Bad**: "Add user stuff"

### 3. Let Agents Work

Don't interrupt the process - agents work autonomously.

### 4. Monitor Forks

For long tasks, check fork count:
```bash
cat .claude/runtime/copilot_sessions/*.json | jq '.fork_count'
```

## Next Steps

- Read [AUTO_MODE.md](./AUTO_MODE.md) for full documentation
- Review [PHASE_7_SUMMARY.md](./PHASE_7_SUMMARY.md) for architecture
- Check [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) for Copilot integration

## Quick Reference

| Command | Description |
|---------|-------------|
| `--auto` | Enable auto mode |
| `--enhanced-copilot` | Use enhanced mode with agents |
| `--max-turns N` | Set max turns (default: 10) |
| `-p "task"` | Task description |

## Examples by Task Type

### Feature
```bash
amplihack copilot --auto --enhanced-copilot -- -p "feature: add email notifications"
```

### Bug
```bash
amplihack copilot --auto --enhanced-copilot -- -p "bug: fix memory leak in worker"
```

### Refactor
```bash
amplihack copilot --auto --enhanced-copilot -- -p "refactor: extract payment logic to service"
```

### Test
```bash
amplihack copilot --auto --enhanced-copilot -- -p "test: add integration tests for API"
```

---

**Questions?** See [AUTO_MODE.md](./AUTO_MODE.md) for detailed documentation.
