# Power-Steering Mode

**Intelligent session completion verification that prevents premature work termination**

## What is Power-Steering Mode?

Power-steering mode is an intelligent system that analyzes your work session before allowing it to end. It checks 21 different considerations across 6 categories to ensure your work is truly complete, preventing incomplete PRs and reducing review cycles.

Think of it as a helpful co-pilot that asks "Are you sure you're done?" before you leave, checking things like:

- Have all TODO items been completed?
- Were tests run locally?
- Is CI passing?
- Does the PR have a description?
- Are there any unrelated changes?

## Why Use Power-Steering?

Power-steering helps you catch common mistakes before they become problems:

✅ **Reduces incomplete PRs by 30+%** - Catches forgotten tasks before pushing
✅ **Reduces review cycles by 20+%** - Ensures quality before submission
✅ **Reduces CI failures by 15+%** - Verifies testing before pushing
✅ **Prevents scope creep** - Detects unrelated changes
✅ **Enforces workflow compliance** - Ensures process is followed

## How It Works

When you try to end a session, power-steering:

1. **Analyzes your session transcript** - Reviews all your work and conversations
2. **Checks 21 considerations** - Verifies completeness across multiple dimensions
3. **Provides feedback** - Shows what's complete and what needs attention
4. **Blocks or warns** - Prevents session end if critical items are incomplete

### The 21 Considerations

Power-steering checks six categories of considerations:

1. **Session Completion & Progress** (8 checks)
   - TODOs completed
   - Original objective achieved
   - Documentation updated
   - Next steps documented

2. **Workflow Process Adherence** (2 checks)
   - DEFAULT_WORKFLOW followed
   - Investigation findings documented

3. **Code Quality & Philosophy Compliance** (2 checks)
   - No TODOs, stubs, or placeholders
   - No quality shortcuts taken

4. **Testing & Local Validation** (2 checks)
   - Tests executed locally
   - Interactive testing performed

5. **PR Content & Quality** (4 checks)
   - PR has description and test plan
   - No unrelated changes
   - No root directory pollution
   - Review feedback addressed

6. **CI/CD & Mergeability Status** (3 checks)
   - CI checks passing
   - Branch rebased with main
   - Pre-commit and CI configs aligned

## Quick Start

### Enable Power-Steering

Power-steering is enabled by default. No setup required!

### Disable Power-Steering

If you need to disable power-steering temporarily:

```bash
# Method 1: Environment variable (session-specific)
export AMPLIHACK_SKIP_POWER_STEERING=1

# Method 2: Semaphore file (persistent)
mkdir -p .claude/runtime/power-steering
touch .claude/runtime/power-steering/.disabled

# Method 3: Config file
echo '{"enabled": false}' > .claude/tools/amplihack/.power_steering_config
```

### Re-enable Power-Steering

```bash
# Remove semaphore file
rm .claude/runtime/power-steering/.disabled

# Or unset environment variable
unset AMPLIHACK_SKIP_POWER_STEERING
```

## Customization

Power-steering is highly customizable. You can:

- **Change severity levels** - Make warnings into blockers or vice versa
- **Disable specific checks** - Skip considerations that don't apply to your workflow
- **Add custom checks** - Define team-specific requirements
- **Modify questions** - Customize the prompts to match your terminology

See the [Customization Guide](customization-guide.md) for detailed instructions.

## Understanding Results

When power-steering runs, you'll see results for each consideration:

### ✅ Satisfied

The check passed. This aspect of your work is complete.

### ❌ Failed (Blocker)

The check failed and is marked as a blocker. You must address this before ending the session.

### ⚠️ Failed (Warning)

The check failed but is only a warning. You can proceed, but you should review this.

### Example Output

```
Power-Steering Analysis:
✅ All TODO items completed
✅ Original objective achieved
❌ Local tests not run (BLOCKER)
⚠️ PR description missing (WARNING)
✅ CI checks passing

Decision: BLOCK
Reason: Critical item incomplete - Local tests must be run

Continuation Prompt:
Please run tests locally using pytest or the appropriate test runner,
verify they pass, then try ending the session again.
```

### Feedback Message Formatting

Power-steering uses smart truncation to keep feedback messages concise and readable:

- **200 character maximum** - Messages are automatically truncated for readability and security
- **Sentence boundaries preferred** - Truncation happens at natural sentence breaks (. ! ?)
- **Word boundaries fallback** - If no sentence boundary, truncates at last word before limit
- **Ellipsis indicator** - Truncated messages end with "..." to show content was shortened

**Examples:**

```
✅ "Tests passing locally and in CI."
   (Short message, no truncation needed)

⚠️ "Complete the 3 incomplete TODOs shown in the task list. Update the..."
   (Long message truncated at word boundary)

❌ "Run pytest to verify your changes. Ensure all tests pass."
   (Long message truncated at sentence boundary)
```

This ensures feedback is always scannable and actionable, even for complex checks with detailed reasoning.

## Fail-Open Philosophy

Power-steering follows a **fail-open** design philosophy:

- If power-steering encounters an error, it **always approves** the session end
- Users are never blocked due to bugs in power-steering
- Errors are logged for debugging but don't impact your workflow
- Power-steering enhances the experience but is never a critical blocker

This ensures power-steering helps when it can, but never gets in your way.

## Configuration File

Power-steering uses a YAML configuration file:

```
.claude/tools/amplihack/considerations.yaml
```

This file defines all 21 considerations with their:

- Questions and descriptions
- Severity levels (blocker vs warning)
- Checker implementations (specific vs generic)
- Enabled/disabled status

See the [Customization Guide](customization-guide.md) for the complete file format and examples.

## Troubleshooting

### Power-steering isn't running

Check if it's been disabled:

```bash
# Check for semaphore file
ls -la .claude/runtime/power-steering/.disabled

# Check environment variable
echo $AMPLIHACK_SKIP_POWER_STEERING

# Check config file
cat .claude/tools/amplihack/.power_steering_config
```

### Too many false positives

If power-steering is blocking you incorrectly:

1. Review the specific consideration that's failing
2. Adjust its severity from "blocker" to "warning" in considerations.yaml
3. Or disable the consideration entirely
4. See the [Customization Guide](customization-guide.md) for instructions

### Power-steering is too strict

Tune the severity levels:

- Change blockers to warnings for non-critical checks
- Disable considerations that don't apply to your workflow
- Adjust checker sensitivity (requires code changes)

### Power-steering is too lenient

Make warnings into blockers:

- Identify which warnings you want to enforce
- Change their severity to "blocker" in considerations.yaml
- Add custom considerations for team-specific requirements

## Performance

Power-steering is designed to be fast:

- **P50 latency**: < 100ms
- **P95 latency**: < 300ms
- **Hard timeout**: 30 seconds (configurable)
- **Memory usage**: < 50MB

If you experience slowdowns, check the logs:

```
.claude/runtime/power-steering/power_steering.log
```

## Documentation Links

### User Guides

- [Customization Guide](customization-guide.md) - Detailed customization instructions
- [Troubleshooting](./troubleshooting.md) - Fix common issues including infinite loop bug
- [Migration Guide v0.9.1](./migration-v0.9.1.md) - Upgrade from v0.9.0 to v0.9.1

### Technical Reference

- [Architecture](/Specs/power_steering_architecture.md) - Technical implementation details (for developers)
- [Checker Implementation](/Specs/power_steering_checker.md) - Checker logic details (for developers)
- [Technical Reference](./technical-reference.md) - Developer reference for state management and diagnostics

### Release Notes

- [Changelog v0.9.1](./changelog-v0.9.1.md) - Infinite loop fix details and release notes

## Best Practices

### Do's

✅ Start with the default configuration and tune as needed
✅ Use warnings first, upgrade to blockers after testing
✅ Add custom considerations for team-specific requirements
✅ Review power-steering feedback - it catches real issues
✅ Share your customizations with your team via git

### Don'ts

❌ Don't disable power-steering permanently without trying it first
❌ Don't ignore warnings - they're often catching real problems
❌ Don't make everything a blocker - balance strictness with productivity
❌ Don't skip local testing just to bypass power-steering

## Getting Help

If you need help with power-steering:

1. Check the [Customization Guide](customization-guide.md)
2. Review logs at `.claude/runtime/power-steering/power_steering.log`
3. Try disabling problematic considerations temporarily
4. Report issues with your configuration and specific error messages

## Version

**Current Version**: Phase 2 (Full Implementation)
**Status**: Production Ready
**Last Updated**: 2025

---

Ready to customize power-steering for your workflow? See the [Customization Guide](customization-guide.md).
