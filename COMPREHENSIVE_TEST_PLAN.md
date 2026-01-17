# Comprehensive Test Plan - Copilot CLI Integration

## Additional Tests Needed

### 1. Multi-Session Test
**Purpose**: Verify AGENTS.md persists across sessions
**Test**:
```bash
# Session 1
uvx --from git+...@branch amplihack copilot -- -p "Test 1: Are you a pirate?"
# Session 2
uvx --from git+...@branch amplihack copilot -- -p "Test 2: Still a pirate?"
```
**Expected**: Both sessions see pirate preferences

### 2. Claude Code Regression Test
**Purpose**: Ensure changes don't break Claude Code
**Test**:
```bash
amplihack launch -- -p "Are you a pirate in Claude Code?"
```
**Expected**: Claude Code session gets pirate preferences

### 3. Hook Execution Order Test
**Purpose**: Verify all 6 hooks fire in correct order
**Test**: Run Copilot session, check logs:
- session_start.log
- user_prompt_submit.log
- pre_tool_use.log (if tools used)
- post_tool_use.log (if tools used)
- error_occurred.log (if errors)
- Session end (via stop.py)

### 4. Permission Control Test
**Purpose**: Verify preToolUse can block dangerous operations
**Test**:
```bash
copilot -- -p "Run: git commit --no-verify"
```
**Expected**: preToolUse hook blocks operation

### 5. AGENTS.md Location Test
**Purpose**: Verify AGENTS.md created in correct location for UVX
**Test**: After uvx run, check where AGENTS.md was created
**Expected**: In project root visible to Copilot

### 6. Symlink Integrity Test
**Purpose**: Verify symlinks survive packaging
**Test**:
```bash
# After uvx install
ls -la .github/agents/amplihack
# Should be symlink to .claude/agents/amplihack
```

### 7. Error Recovery Test
**Purpose**: Verify hooks fail gracefully
**Test**: Corrupt launcher_context.json, run session
**Expected**: Falls back to Claude Code behavior

### 8. Cross-Platform Test
**Purpose**: Test on different OS (if possible)
**Platforms**: Linux (done), macOS, Windows
**Expected**: Hooks work on all platforms

## Current Test Status

| Test | Status | Result |
|------|--------|--------|
| UVX Build | ✅ | 163 packages, 133ms |
| Agents Work | ✅ | architect.md, tester.md readable |
| Skills Work | ✅ | code-smell-detector working |
| Commands |✅ | ultrathink.md accessible |
| Hooks Fire | ✅ | Logs created |
| Context Injection | ⚠️ | Worked once, then stopped |
| Model | ✅ | Opus 4.5 confirmed |
| Claude Code | ✅ | Hooks work, preferences applied |
| Multi-Session | ❌ | Not tested |
| Permission Control | ❌ | Not tested |
| Error Recovery | ❌ | Not tested |

## Issue Found: AGENTS.md Timing Problem

**Problem**:
- AGENTS.md created by session_start HOOK
- But Copilot needs AGENTS.md BEFORE starting session
- Chicken-and-egg problem in UVX environment

**Evidence**:
- First test: Pirate worked (AGENTS.md existed from previous test)
- Second test: Not pirate (fresh UVX install, no AGENTS.md yet)

**Solution Needed**:
- Create AGENTS.md at PACKAGE TIME (in build_hooks.py)
- Or create AGENTS.md in launcher BEFORE spawning Copilot
- Or use different mechanism (not AGENTS.md)

## Recommended Fix

**Create AGENTS.md in copilot.py launcher BEFORE spawning copilot**:
```python
def launch_copilot(args, interactive=True):
    # ... existing code ...

    # BEFORE launching Copilot, create AGENTS.md
    from amplihack.context.adaptive.strategies import CopilotStrategy
    strategy = CopilotStrategy(project_root)

    # Load and inject preferences
    prefs = load_preferences()  # From session_start logic
    strategy.inject_context(prefs)

    # NOW launch Copilot (AGENTS.md exists)
    subprocess.run(cmd)
```

This ensures AGENTS.md exists BEFORE Copilot starts, so it can discover and load it.
