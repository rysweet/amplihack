# Module Specification: Hook Registration Audit

## Purpose

Verify ALL amplihack hooks are registered in `hooks.json` with `${CLAUDE_PLUGIN_ROOT}` variable paths.

## Problem

Issue #1948 requirement #2: "ALL hooks with ${CLAUDE_PLUGIN_ROOT}". Currently:

- `hooks.json` has 4 hooks registered (SessionStart, Stop, PostToolUse, PreCompact)
- Directory `~/.amplihack/.claude/tools/amplihack/hooks/` contains 7 Python hook files
- 3 hooks may be missing from `hooks.json`: `pre_tool_use.py`, `user_prompt_submit.py`, `power_steering_checker.py`

## Solution Overview

1. Audit `~/.amplihack/.claude/tools/amplihack/hooks/` directory for all hook files
2. Compare against `hooks.json` entries
3. Add missing hooks to `hooks.json` with proper configuration
4. Verify all paths use `${CLAUDE_PLUGIN_ROOT}` variable

## Contract

### Inputs

**Directory Audit:**

- Scan `~/.amplihack/.claude/tools/amplihack/hooks/*.py` for hook files
- Exclude test files (`test_*.py`) and `__init__.py`

**Current `hooks.json`:**

```json
{
  "SessionStart": [...],
  "Stop": [...],
  "PostToolUse": [...],
  "PreCompact": [...]
}
```

### Outputs

**Updated `hooks.json`:**

```json
{
  "SessionStart": [...],
  "Stop": [...],
  "PreToolUse": [...],        // ADDED
  "PostToolUse": [...],
  "UserPromptSubmit": [...],  // ADDED
  "PreCompact": [...]
}
```

### Side Effects

- Updates `~/.amplihack/.claude/tools/amplihack/hooks/hooks.json` with complete hook list
- Ensures all hooks load properly in Claude Code

## Implementation Design

### Step 1: Audit Hook Files

**Command:**

```bash
ls .claude/tools/amplihack/hooks/*.py | grep -v test_ | grep -v __init__
```

**Expected Files (from git status):**

```
.claude/tools/amplihack/hooks/
├── session_start.py          ✅ In hooks.json (SessionStart)
├── stop.py                   ✅ In hooks.json (Stop)
├── post_tool_use.py          ✅ In hooks.json (PostToolUse)
├── pre_compact.py            ✅ In hooks.json (PreCompact)
├── pre_tool_use.py           ❌ MISSING from hooks.json
├── user_prompt_submit.py     ❌ MISSING from hooks.json
├── power_steering_checker.py ❓ Need to determine if this is a hook or utility
└── agent_memory_hook.py      ❓ Need to determine hook type
```

### Step 2: Determine Hook Types

**Hook Type Mapping (Claude Code Lifecycle):**

1. **SessionStart** - Runs when Claude Code session starts
2. **Stop** - Runs when session ends
3. **PreToolUse** - Runs BEFORE each tool execution
4. **PostToolUse** - Runs AFTER each tool execution
5. **UserPromptSubmit** - Runs when user submits prompt
6. **PreCompact** - Runs before context window compaction

**Analysis Method:**

- Read each missing hook file
- Identify hook type from function signature or imports
- Determine appropriate hook lifecycle event

### Step 3: Hook Configurations

**PreToolUse Hook (if applicable):**

```json
{
  "PreToolUse": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/pre_tool_use.py"
        }
      ]
    }
  ]
}
```

**UserPromptSubmit Hook (if applicable):**

```json
{
  "UserPromptSubmit": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/user_prompt_submit.py",
          "timeout": 10000
        }
      ]
    }
  ]
}
```

**Note on `power_steering_checker.py` and `agent_memory_hook.py`:**

- These may be utility modules called by other hooks (not standalone hooks)
- Verify by checking if they have `if __name__ == "__main__"` entry points
- Only add if they are executable hooks

### Step 4: Updated `hooks.json`

**Complete Configuration (after audit):**

```json
{
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/session_start.py",
          "timeout": 10000
        }
      ]
    }
  ],
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/stop.py",
          "timeout": 30000
        }
      ]
    }
  ],
  "PreToolUse": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/pre_tool_use.py"
        }
      ]
    }
  ],
  "PostToolUse": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/post_tool_use.py"
        }
      ]
    }
  ],
  "UserPromptSubmit": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/user_prompt_submit.py",
          "timeout": 10000
        }
      ]
    }
  ],
  "PreCompact": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/pre_compact.py",
          "timeout": 30000
        }
      ]
    }
  ]
}
```

## Implementation Steps

### Step 1: Read Hook Files

```bash
# Read pre_tool_use.py to determine if it's a hook
cat .claude/tools/amplihack/hooks/pre_tool_use.py | head -50

# Read user_prompt_submit.py to determine if it's a hook
cat .claude/tools/amplihack/hooks/user_prompt_submit.py | head -50

# Read power_steering_checker.py to determine type
cat .claude/tools/amplihack/hooks/power_steering_checker.py | head -50

# Read agent_memory_hook.py to determine type
cat .claude/tools/amplihack/hooks/agent_memory_hook.py | head -50
```

### Step 2: Verify Hook Executability

**Criteria for Inclusion:**

- Has `if __name__ == "__main__"` block OR
- Is imported/called by Claude Code lifecycle hooks OR
- Has docstring indicating hook purpose

**Exclusion Criteria:**

- Utility module (no standalone execution)
- Test file
- Import-only library

### Step 3: Update `hooks.json`

```bash
# Backup current hooks.json
cp .claude/tools/amplihack/hooks/hooks.json .claude/tools/amplihack/hooks/hooks.json.backup

# Edit hooks.json with verified hooks
# Add PreToolUse, UserPromptSubmit if they are hooks
```

### Step 4: Verify Paths Use Variable

**Check all paths:**

```bash
cat .claude/tools/amplihack/hooks/hooks.json | grep -o 'command.*' | grep -v CLAUDE_PLUGIN_ROOT
```

Should return **nothing** (all paths should use `${CLAUDE_PLUGIN_ROOT}`).

## Dependencies

- **None** (pure configuration audit)
- **Tools:** `grep`, `jq`, text editor

## Testing Strategy

### Verification Tests

1. **Path Variable Test:**

   ```bash
   # All paths should use ${CLAUDE_PLUGIN_ROOT}
   cat .claude/tools/amplihack/hooks/hooks.json | jq -r '.. | .command? // empty' | grep -v 'CLAUDE_PLUGIN_ROOT'
   # Should output nothing
   ```

2. **Hook Count Test:**

   ```bash
   # Count hooks in directory (excluding tests, __init__)
   ls .claude/tools/amplihack/hooks/*.py | grep -v test_ | grep -v __init__ | wc -l

   # Count hooks in hooks.json
   cat .claude/tools/amplihack/hooks/hooks.json | jq 'keys | length'

   # Counts should match (or justify difference)
   ```

3. **JSON Validity Test:**
   ```bash
   # Verify JSON is valid
   cat .claude/tools/amplihack/hooks/hooks.json | jq '.'
   # Should output formatted JSON without errors
   ```

### Runtime Tests

```python
# Test hook loading
def test_all_hooks_registered():
    """Verify all hooks are registered in hooks.json."""
    hooks_dir = Path(".claude/tools/amplihack/hooks")
    hooks_json = hooks_dir / "hooks.json"

    # Get all hook files
    hook_files = [
        f.stem for f in hooks_dir.glob("*.py")
        if not f.name.startswith("test_") and f.name != "__init__.py"
    ]

    # Get registered hooks
    import json
    registered_hooks = json.loads(hooks_json.read_text())

    # Verify all executable hooks are registered
    for hook_file in hook_files:
        # Check if file is executable (has __main__ or is called by hooks)
        file_path = hooks_dir / f"{hook_file}.py"
        content = file_path.read_text()

        if '__name__ == "__main__"' in content:
            # This is an executable hook - should be in hooks.json
            # Convert filename to hook type (e.g., pre_tool_use -> PreToolUse)
            hook_type = "".join(word.capitalize() for word in hook_file.split("_"))

            # Search for command path in hooks.json
            found = False
            for lifecycle, configs in registered_hooks.items():
                for config in configs:
                    for hook in config.get("hooks", []):
                        if hook_file in hook.get("command", ""):
                            found = True
                            break

            assert found, f"Hook {hook_file}.py not found in hooks.json"

def test_all_paths_use_variable():
    """Verify all paths use ${CLAUDE_PLUGIN_ROOT} variable."""
    hooks_json = Path(".claude/tools/amplihack/hooks/hooks.json")
    import json
    hooks = json.loads(hooks_json.read_text())

    for lifecycle, configs in hooks.items():
        for config in configs:
            for hook in config.get("hooks", []):
                command = hook.get("command", "")
                assert "${CLAUDE_PLUGIN_ROOT}" in command, \
                    f"Hook command does not use CLAUDE_PLUGIN_ROOT: {command}"
```

## Complexity Assessment

- **Total Lines:** ~0-50 lines (configuration only, no code)
- **Effort:** 1-2 hours
  - 30 min: Read hook files to determine types
  - 30 min: Update hooks.json
  - 30 min: Verify and test
- **Risk:** Low (configuration change only)

## Success Metrics

- [ ] All executable hooks in directory are in `hooks.json`
- [ ] All paths use `${CLAUDE_PLUGIN_ROOT}` variable
- [ ] `hooks.json` is valid JSON
- [ ] Hook count matches directory count (or difference justified)
- [ ] All hooks load successfully in Claude Code
- [ ] No duplicate hook registrations

## Decision Tree

```
For each *.py file in .claude/tools/amplihack/hooks/:
  ├─ Is it a test file (test_*.py)? → SKIP
  ├─ Is it __init__.py? → SKIP
  ├─ Does it have `if __name__ == "__main__"`? → ADD TO hooks.json
  ├─ Is it called by other hooks? → UTILITY (don't add)
  └─ Uncertain? → READ FILE, determine purpose
```

## Philosophy Compliance

- ✅ **Ruthless Simplicity:** Configuration audit, no code changes
- ✅ **Zero-BS Implementation:** Verify actual hooks, not assumptions
- ✅ **Modular Design:** Each hook is independent
- ✅ **Regeneratable:** hooks.json can be regenerated from directory
- ✅ **Single Responsibility:** hooks.json only contains hooks

## Next Actions

1. Read `pre_tool_use.py`, `user_prompt_submit.py` to verify they are hooks
2. Read `power_steering_checker.py`, `agent_memory_hook.py` to determine type
3. Update `hooks.json` with verified hooks
4. Test with `jq` to verify JSON validity and path variables
5. Run plugin in Claude Code to verify hooks load

## References

- Issue #1948, Requirement #2: "ALL hooks with ${CLAUDE_PLUGIN_ROOT}"
- `ISSUE_1948_REQUIREMENTS.md`, Gap 3 (lines 325-347)
- Current `hooks.json` (lines 1-46 in `~/.amplihack/.claude/tools/amplihack/hooks/hooks.json`)
