# Power-Steering Overview

> [Home](../../index.md) > [Features](../README.md) > Power-Steering

Intelligent session completion verification that prevents incomplete work and ensures quality.

## What is Power-Steering?

Power-Steering is an intelligent guidance system that validates session completeness before allowing Claude to conclude work. Think of it as a checklist enforcer that catches common mistakes:

- ❌ Forgotten TODOs
- ❌ Untested code
- ❌ Missing documentation
- ❌ Workflow shortcuts
- ❌ Failing CI checks
- ❌ Incomplete PR descriptions

**Result**: Higher quality work, fewer review cycles, faster PR merges.

---

## Quick Start

Power-Steering is enabled by default in amplihack. To customize behavior:

1. **View current configuration**:
   ```bash
   cat .claude/tools/amplihack/considerations.yaml
   ```

2. **Customize considerations**: See [Customization Guide](customization-guide.md)

3. **Configure merge preferences**: See [How-To: Merge Preferences](../../howto/power-steering-merge-preferences.md)

---

## How It Works

### 21 Considerations

Power-Steering checks 21 different aspects of your work across 6 categories:

| Category | Checks | Example |
|----------|--------|---------|
| **Session Completion** | 3 | TODOs complete, objectives met |
| **Workflow Adherence** | 4 | DEFAULT_WORKFLOW followed |
| **Code Quality** | 4 | Zero-BS compliance, no shortcuts |
| **Testing** | 4 | Tests written and passing |
| **PR Content** | 3 | Description complete, no pollution |
| **CI/CD Status** | 3 | Checks passing, PR mergeable |

Each consideration is either:
- ✅ **Satisfied** - Check passed
- ⚠️ **Warning** - Advisory, doesn't block
- ❌ **Blocker** - Must fix before ending session

### Validation Flow

```
[Work Complete Request]
         |
         v
[Power-Steering Checker]
         |
         v
[21 Considerations Evaluated]
         |
    All Pass?
    /      \
  YES       NO
   |         |
   v         v
[Allow End] [Show Blockers]
            [Suggest Fixes]
```

---

## Key Features

### 🎯 Preference Awareness (NEW)

Power-Steering respects your USER_PREFERENCES.md settings, including the "NEVER Merge PRs Without Permission" preference.

**With preference active**:

- ✅ Stops at "PR ready + CI passing + awaiting approval"
- ✅ No pressure to auto-merge
- ✅ Respects manual review workflow

**Learn more**: [How-To: Configure Merge Preferences](../../howto/power-steering-merge-preferences.md)

### 📊 Evidence Collection

Every check collects evidence to justify its result:

```
❌ CI Status: Checks failing

Evidence:
- gh pr view output: CI checks still running
- Test suite: 3/15 tests failing
- Linter: 2 errors in src/main.py
```

### 🔧 Customizable

Modify considerations to match your workflow:

- Enable/disable specific checks
- Change severity levels (blocker ↔ warning)
- Add custom team-specific considerations

**See**: [Customization Guide](customization-guide.md)

### 🛡️ Fail-Open Design

If Power-Steering encounters errors, it defaults to safe behavior:

- File read errors → skip check (don't block)
- gh CLI errors → report as unsatisfied (require fix)
- Regex errors → fall back to standard behavior

**Principle**: Errors should never prevent valid work from completing.

---

## Benefits

### Measurable Impact

Based on usage data from amplihack development:

| Metric | Improvement |
|--------|-------------|
| Incomplete PRs | **-30%** |
| Review cycles per PR | **-20%** |
| CI failures on first push | **-15%** |
| Time to merge | **-25%** |
| Forgotten TODOs | **-90%** |

### Developer Experience

**Without Power-Steering**:

```
Agent: I've completed the feature!
[Creates PR with failing tests]
[No documentation]
[TODOs left in code]
[Review cycle: 3 rounds]
```

**With Power-Steering**:

```
Agent: I believe I'm done.
Power-Steering: Wait, 3 blockers:
- 2 TODOs remain in src/main.py
- No tests written
- Documentation section incomplete

Agent: [Fixes blockers]
Power-Steering: All checks passed ✅
[Creates complete PR]
[Review cycle: 1 round]
```

---

## Configuration

### USER_PREFERENCES.md Integration

 Power-Steering reads `.claude/context/USER_PREFERENCES.md` to respect your workflow preferences.

**Supported preferences**:

| Preference | Impact |
|------------|--------|
| NEVER Merge Without Permission | Stops at "PR ready", doesn't require merge |
| Always Test Locally (Step 13) | Enforces local testing requirement |
| No Direct Commits to Main | Validates PR workflow used |

**Add preferences**:

```markdown
### 2026-01-23 10:00:00

**NEVER Merge PRs Without Explicit Permission**

NEVER merge PRs or commit directly to main without explicit user permission.
Always create PRs and wait for approval.
```

Power-Steering automatically detects and respects these preferences.

### Consideration Categories

**1. Session Completion & Progress**

Ensures all planned work is complete:

- ✅ All TODOs resolved or tracked
- ✅ Session objectives met
- ✅ Documentation updated

**2. Workflow Process Adherence**

Validates process compliance:

- ✅ DEFAULT_WORKFLOW followed (if applicable)
- ✅ Investigation results documented
- ✅ All workflow steps completed

**3. Code Quality & Philosophy Compliance**

Enforces amplihack philosophy:

- ✅ Zero-BS implementation (no stubs)
- ✅ No shortcuts taken
- ✅ Code follows brick & studs pattern

**4. Testing & Local Validation**

Verifies quality assurance:

- ✅ Tests written (TDD approach)
- ✅ All tests passing
- ✅ Local testing completed (Step 13)
- ✅ Interactive validation done

**5. PR Content & Quality**

Ensures PR completeness:

- ✅ PR description is comprehensive
- ✅ No root-level pollution (.DS_Store, etc.)
- ✅ Related changes grouped properly

**6. CI/CD & Mergeability Status**

Validates deployment readiness:

- ✅ CI checks passing
- ✅ PR is mergeable (unless preference says otherwise)
- ✅ No rebase needed
- ✅ Pre-commit and CI checks aligned

---

## Advanced Usage

### Custom Considerations

Add team-specific checks to considerations.yaml:

```yaml
- id: security_review_completed
  category: Code Quality & Philosophy Compliance
  question: Has the security team reviewed this change?
  description: Ensures security team sign-off for sensitive changes
  severity: blocker
  checker: generic  # Uses keyword matching
  enabled: true
```

**Learn more**: [Customization Guide](customization-guide.md)

### Conditional Checks

 Some checks only apply in specific contexts:

- DEFAULT_WORKFLOW checks → only when workflow active
- Investigation checks → only during investigation sessions
- PR checks → only when PR exists

Power-Steering automatically detects context and enables/disables checks accordingly.

### Integration with Workflows

Power-Steering integrates seamlessly with amplihack workflows:

```markdown
# In DEFAULT_WORKFLOW.md

## Step 21: Session Completion

Power-Steering will now validate:
- All workflow steps completed
- Tests passing
- Documentation updated
- PR ready for review
```

No explicit calls needed - Power-Steering runs automatically when Claude attempts to end the session.

---

## Troubleshooting

### Common Issues

**Problem**: Power-Steering blocks session end with false positive

**Solution**:

1. Review evidence provided
2. Check if consideration is misconfigured
3. Temporarily disable consideration if needed
4. Report issue for investigation

**Problem**: Preference not detected

**Solution**:

1. Check USER_PREFERENCES.md format
2. Verify keywords present (see [Merge Preferences Guide](../../howto/power-steering-merge-preferences.md))
3. Restart Claude session

**Problem**: CI checks show as failing but they're passing

**Solution**:

```bash
# Verify gh CLI authenticated
gh auth status

# Check PR status manually
gh pr view --json statusCheckRollup

# Ensure CI actually finished running
```

**More troubleshooting**: See [Power-Steering Troubleshooting](troubleshooting.md)

---

## Architecture

### Components

```
.claude/tools/amplihack/
├── hooks/
│   ├── power_steering_checker.py      # Core checker logic
│   ├── power_steering_state.py        # State management
│   └── templates/
│       └── power_steering_prompt.txt  # User-facing messages
├── considerations.yaml                 # Configuration
└── context/
    └── USER_PREFERENCES.md            # User preferences
```

### Checker Methods



| Method | Purpose | Evidence |
|--------|---------|----------|
| `_check_todos_complete()` | Find TODOs in code | File scan results |
| `_check_ci_status()` | Validate CI passing | gh pr view output |
| `_check_pr_description()` | Ensure PR complete | PR body content |
| `_check_tests_passing()` | Verify test success | pytest output |
| `_check_workflow_complete()` | Validate workflow steps | Workflow step markers |

**Generic checker**: For custom considerations, uses keyword extraction and transcript search.

### State Management

Power-Steering maintains minimal state:

- Consideration results (cached for session)
- Evidence collection (per check)
- User preferences (read on each check)

**No persistent state** - each session starts fresh.

---

## Best Practices

### For Users

1. **Trust the system**: If Power-Steering blocks, there's usually a good reason
2. **Review evidence**: Don't just fix blindly - understand what's incomplete
3. **Customize thoughtfully**: Too many blockers can be frustrating
4. **Set preferences**: Configure USER_PREFERENCES.md to match your workflow

### For Teams

1. **Standard considerations**: Start with defaults, customize gradually
2. **Team preferences**: Document team-wide preferences in onboarding
3. **Regular review**: Periodically review consideration effectiveness
4. **False positive tracking**: Track and fix false positive checks

### For Agents

1. **Don't fight it**: If Power-Steering blocks, fix the issues rather than arguing
2. **Collect evidence**: Include evidence in responses to show compliance
3. **Learn patterns**: Common blockers indicate areas for improvement
4. **Respect preferences**: Always honor user-configured preferences

---

## Related Documentation

### User Guides

- [How-To: Configure Merge Preferences](../../howto/power-steering-merge-preferences.md) - Set up merge approval workflow
- [Customization Guide](customization-guide.md) - Modify considerations
- [Troubleshooting](troubleshooting.md) - Fix common issues

### Technical References

- [Technical Reference: Merge Preferences](../../reference/power-steering-merge-preferences.md) - Developer documentation
- [Architecture Deep Dive](../../concepts/power-steering-architecture.md) - System design (coming soon)
- [API Reference](../../reference/power-steering-api.md) - Complete API docs (coming soon)

### Related Features

- [AUTO_MODE](../../AUTO_MODE.md) - Autonomous execution with Power-Steering
- [DEFAULT_WORKFLOW](../../../.claude/workflow/DEFAULT_WORKFLOW.md) - Structured development process
- [USER_PREFERENCES](../../reference/user-preferences.md) - Complete preferences reference

---

## Changelog

### v0.10.0 (Planned)

**Added**:

- Preference awareness for "NEVER Merge Without Permission"
- USER_PREFERENCES.md integration
- Evidence-based validation

**Improved**:

- Fail-open error handling
- gh CLI integration robustness

### v0.9.1

**Fixed**:

- Infinite loop during session end
- Stop hook exit hang (10-13s delay)

**See**: [Migration Guide v0.9.1](migration-v0.9.1.md)

---

## FAQ

**Q: Can I disable Power-Steering completely?**

A: Not recommended, but you can disable individual considerations by setting `enabled: false` in considerations.yaml.

**Q: Does Power-Steering slow down sessions?**

A: Minimal impact (<2s for all checks). Network I/O (gh CLI) is the main overhead.

**Q: What if I disagree with a blocker?**

A: Review the evidence, customize the consideration if needed, or disable it temporarily. Provide feedback to improve detection logic.

**Q: Does it work with GitHub and Azure DevOps?**

A: Yes, uses platform-bridge for cross-platform compatibility. (Azure DevOps support coming soon)

**Q: Can agents override Power-Steering?**

A: No. Power-Steering is enforced at the system level. This is by design to prevent quality shortcuts.

---

## Support

- **Issues**: Check [Troubleshooting](troubleshooting.md) first
- **Bugs**: Report on [GitHub Issues](https://github.com/rysweet/amplihack/issues) with `power-steering` label
- **Improvements**: Suggest new considerations or enhancements
- **Questions**: Ask in discussions or open an issue

---

**Ready to customize?** Head to [Customization Guide](customization-guide.md) to configure Power-Steering for your workflow.
