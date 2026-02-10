# How to Configure Power-Steering PR Merge Preferences

> [Home](../index.md) > [How-To Guides](../howto/README.md) > Power-Steering Merge Preferences

This guide explains how to configure Power-Steering to respect your PR merge approval preferences.

## Quick Start

If you want Power-Steering to stop at "PR ready + CI passing" without pressuring you to merge, add this to your `USER_PREFERENCES.md`:

```markdown
**NEVER Merge PRs or Commit Directly Without Explicit Permission**

NEVER merge PRs or commit directly to main without explicit user permission.
Always create PRs and wait for approval.
```

Power-Steering automatically detects this preference and treats "awaiting user approval" as a valid completion state.

---

## What This Feature Does

Power-Steering's default behavior checks that PRs are merged as part of session completion. This can create pressure to auto-merge PRs even when you want manual approval.

**With preference awareness enabled**, Power-Steering:

- ✅ Recognizes "PR ready + CI passing + awaiting approval" as complete
- ✅ Stops pressuring agents to auto-merge
- ✅ Respects your workflow control preferences
- ✅ Still validates all other completion criteria

---

## Configuration

### Step 1: Check Your USER_PREFERENCES.md

Power-Steering reads `.claude/context/USER_PREFERENCES.md` during each CI status check (lazy detection).

Locate the merge permission section (typically around lines 214-227):

```bash
# View your preferences
cat .claude/context/USER_PREFERENCES.md | grep -A 15 "NEVER Merge"
```

### Step 2: Verify Preference Format

The preference must include specific keywords for detection:

**Required keywords** (case-insensitive):

- "NEVER" or "NEVER Merge"
- "Without Permission" or "Without Explicit Permission"
- "PR" or "Pull Request"

**Example valid formats**:

```markdown
**NEVER Merge PRs Without Permission**

**NEVER Merge PRs or Commit Directly Without Explicit Permission**

**NEVER merge pull requests without explicit user permission**
```

All of these activate the preference awareness feature.

### Step 3: Test the Configuration

Create a test session to verify the behavior:

```bash
# Start a simple feature workflow
amplihack claude

# In the Claude session:
# 1. Create a simple PR with passing CI
# 2. Wait for Power-Steering to validate completion
# 3. Verify it shows "PR ready + awaiting approval" as satisfied
```

**Expected output**:

```
✅ CI Status: PR is ready for review (checks passing, awaiting user approval)
```

---

## How It Works

### Detection Logic

Power-Steering uses regex pattern matching to detect the preference:

```python
# Simplified detection logic
pattern = r'NEVER.*(?:Merge|merge).*(?:PR|Pull Request).*(?:Without|without).*(?:Permission|permission)'

if re.search(pattern, user_preferences_content, re.IGNORECASE | re.DOTALL):
    # Preference detected - use no-auto-merge mode
    return True
```

### Validation Behavior

**With preference detected**:

1. Reads PR status from git/gh CLI
2. Checks if PR exists and is ready for review
3. Validates CI checks are passing
4. Returns ✅ satisfied without checking merge status

**Without preference** (default):

1. Performs standard CI status check
2. Requires PR to be merged for completion
3. Traditional Power-Steering behavior

### Fail-Open Design

If errors occur during preference detection, Power-Steering falls back to standard behavior:

- File read errors → default behavior
- Regex match errors → default behavior
- PR status check errors → reports as unsatisfied

This ensures robustness - errors never falsely mark sessions as complete.

---

## Use Cases

### Use Case 1: Manual Code Review

**Scenario**: You require manual review of all PRs before merge.

**Solution**:

```markdown
**NEVER Merge PRs Without Explicit Permission**
```

**Result**: Power-Steering treats "PR ready + CI passing" as the goal state.

### Use Case 2: Compliance Requirements

**Scenario**: Company policy requires human approval for all merges.

**Solution**: Same preference as Use Case 1.

**Result**: Power-Steering aligns with compliance workflow.

### Use Case 3: High-Stakes Changes

**Scenario**: Working on critical infrastructure - want extra caution.

**Solution**: Enable preference before starting work.

**Result**: Power-Steering stops at "ready for review" for every PR in the session.

---

## Troubleshooting

### Preference Not Detected

**Problem**: Power-Steering still pressures to merge despite preference set.

**Solutions**:

1. **Check keyword format**:

   ```bash
   grep -i "never.*merge.*without.*permission" .claude/context/USER_PREFERENCES.md
   ```

   If no match, adjust wording to include required keywords.

2. **Check file location**:

   ```bash
   ls -la .claude/context/USER_PREFERENCES.md
   ```

   File must exist at this path.

3. **Changes take effect immediately**: Preference changes are detected on the next CI check—no restart needed.

### False Positives

**Problem**: Unrelated text triggers preference detection.

**Solution**: The regex pattern is specific - requires all keywords. However, if false positives occur, ensure USER_PREFERENCES.md clearly separates sections with headings.

### CI Status Check Fails

**Problem**: Power-Steering reports CI status as unsatisfied even though checks passed.

**Possible causes**:

1. **PR not pushed**: Ensure `git push` completed successfully
2. **CI still running**: Wait for checks to complete
3. **gh CLI not authenticated**: Run `gh auth status`

**Debug command**:

```bash
# Check PR status manually
gh pr view --json statusCheckRollup,mergeable,state
```

---

## Configuration Examples

### Basic Setup

**File**: `.claude/context/USER_PREFERENCES.md`

```markdown
### 2026-01-23 10:00:00

**NEVER Merge PRs Without Explicit Permission**

NEVER merge PRs or commit directly to main without explicit user permission.
Always create PRs and wait for approval.
```

### With Additional Context

```markdown
### 2026-01-23 10:00:00

**NEVER Merge PRs or Commit Directly Without Explicit Permission**

NEVER merge PRs or commit directly to main without explicit user permission.
Always create PRs and wait for approval. Only the first explicitly approved
merge applies - subsequent PRs require separate approval.

**Implementation Requirements:**

- MUST create PR and wait for user to say "merge" or "please merge"
- MUST ask for permission for EACH PR merge separately
- MUST NOT assume "fix it all" means "merge everything automatically"
```

Both examples activate the preference awareness feature.

---

## Related Documentation

- [Power-Steering Overview](../features/power-steering/README.md) - What is Power-Steering
- [Power-Steering Configuration](../features/power-steering/configuration.md) - General configuration
- [USER_PREFERENCES.md Guide](../reference/user-preferences.md) - Complete preferences reference
- [Power-Steering Technical Reference](../reference/power-steering-merge-preferences.md) - Developer documentation

---

## Next Steps

After configuring merge preferences:

1. **Test the workflow**: Create a test PR to verify behavior
2. **Customize other preferences**: See [Power-Steering Configuration](../features/power-steering/configuration.md)
3. **Review workflow compliance**: Check [DEFAULT_WORKFLOW.md](../../.claude/workflow/DEFAULT_WORKFLOW.md)

---

**Need help?** Check [Power-Steering Troubleshooting](../features/power-steering/troubleshooting.md) or [Discoveries](../DISCOVERIES.md) for common issues.
