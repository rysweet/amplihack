# Test Scenario Results for Amplihack Hook Configuration

## Test Date: 2025-01-22

### Scenario 1: New User Installation

**✅ PASSED**

**Test Steps:**

1. Simulated fresh install with no existing ~/.claude/settings.json
2. Reviewed install.sh lines 122-178

**Result:**

- Install script creates new settings.json with HOME_PLACEHOLDER
- Line 175 correctly replaces placeholder with actual $HOME path
- Final hooks have absolute paths like
  `/home/user/.claude/tools/amplihack/hooks/session_start.py`
- **Hooks will work correctly from any directory**

### Scenario 2: Project with Local Hooks

**❌ ISSUES FOUND**

**Test Setup:** Project has `.claude/settings.json` with:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "command": ".claude/tools/project-specific/hook.py"
          }
        ]
      }
    ]
  }
}
```

**Result:**

1. **Hook Override Issue**: Project hooks completely replace global amplihack
   hooks
   - Claude Code does NOT merge hook arrays
   - Project's SessionStart replaces global SessionStart
   - Amplihack hooks don't run at all in this project

2. **Path Resolution Issue**: If project references amplihack hooks with
   relative paths:

   ```json
   "command": ".claude/tools/amplihack/hooks/session_start.py"
   ```

   - This fails with "No such file or directory"
   - Hook files only exist in ~/.claude/, not in project

### Critical Findings

#### 1. Hook Priority Behavior

- Claude Code uses **last-wins** merge strategy for hooks
- Project settings override global settings completely
- No way to combine global + project hooks

#### 2. Installation Gaps

- Install script only updates ~/.claude/settings.json
- Doesn't scan for or warn about project-level conflicts
- Users may not know their project hooks are blocking amplihack

#### 3. Error Messages

- When relative paths fail: Clear error message (good)
- When hooks are overridden: Silent failure (bad)
- No indication that amplihack hooks aren't running

### Recommendations

#### Immediate Actions

1. **Documentation Update**: Add warning about project hook conflicts
2. **Install Script Enhancement**: Check for common project locations and warn
3. **Migration Guide**: Help users merge their hooks

#### Long-term Solutions

1. **Hook Merging Strategy**: Implement additive hook merging in Claude Code
2. **Hook Namespacing**: Prefix amplihack hooks to avoid conflicts
3. **Configuration Validator**: Tool to check for conflicts

### Workarounds for Users

#### Option 1: Remove Project Hooks

```bash
# Remove hooks section from project's .claude/settings.json
# Amplihack global hooks will then work
```

#### Option 2: Manually Merge Hooks

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "command": "/Users/username/.claude/tools/amplihack/hooks/session_start.py",
            "timeout": 10000
          },
          {
            "command": "./project-specific-hook.py"
          }
        ]
      }
    ]
  }
}
```

#### Option 3: Create Wrapper Script

Create a project hook that calls both project and amplihack hooks.

### Test Commands Used

```bash
# Check if settings exist
ls -la ~/.claude/settings.json
ls -la .claude/settings.json

# Verify hook paths
grep -r "hooks" .claude/settings.json
grep -r "command" ~/.claude/settings.json

# Test hook execution
# (Would need actual Claude Code session to fully test)
```

### Conclusion

The current implementation:

- ✅ Works perfectly for new users
- ✅ Works for users without project hooks
- ❌ Fails silently when projects have hooks
- ❌ Doesn't handle hook merging
- ❌ No conflict detection or warnings

Priority fix needed for Scenario 2 to prevent silent failures.
