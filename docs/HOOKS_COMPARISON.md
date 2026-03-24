# Claude Code Hooks vs GitHub Copilot CLI Hooks - Complete Comparison

**Last Updated**: 2026-01-16 **Testing**: Both platforms tested in production
**Sources**: Official documentation + empirical testing

## Hook Types Comparison

| Hook Type         | Claude Code          | Copilot CLI            | Notes                           |
| ----------------- | -------------------- | ---------------------- | ------------------------------- |
| **Session Start** | ✅ SessionStart      | ✅ sessionStart        | Both fire at session begin      |
| **Session End**   | ✅ Stop              | ✅ sessionEnd          | Both fire at session end        |
| **Subagent End**  | ✅ SubagentStop      | ❌ Not available       | Claude Code only                |
| **User Prompt**   | ✅ UserPromptSubmit  | ✅ userPromptSubmitted | Both fire on prompt submit      |
| **Pre-Tool**      | ✅ PreToolUse        | ✅ preToolUse          | Both fire before tool execution |
| **Post-Tool**     | ✅ PostToolUse       | ✅ postToolUse         | Both fire after tool execution  |
| **Permission**    | ✅ PermissionRequest | ❌ Not available       | Claude Code only                |
| **Error**         | ❌ Not available     | ✅ errorOccurred       | Copilot CLI only                |
| **Notification**  | ✅ Notification      | ❌ Not available       | Claude Code only                |
| **Pre-Compact**   | ✅ PreCompact        | ❌ Not available       | Claude Code only                |
| **TOTAL**         | 10 hooks             | 6 hooks                | Claude Code more comprehensive  |

---

## Capabilities Comparison

### Context Injection (Adding Information to AI)

| Hook                 | Claude Code                            | Copilot CLI                      | Tested                |
| -------------------- | -------------------------------------- | -------------------------------- | --------------------- |
| **SessionStart**     | ✅ YES - `additionalContext` or stdout | ❌ NO - Output ignored           | ✅ Confirmed via test |
| **UserPromptSubmit** | ✅ YES - `additionalContext` or stdout | ❌ NO - Output ignored           | ✅ Confirmed via test |
| **PreToolUse**       | ✅ YES - `additionalContext`           | ❌ NO - Only permission decision | ✅ Confirmed via test |
| **PostToolUse**      | ✅ YES - `additionalContext`           | ❌ NO - Output ignored           | ✅ Confirmed via test |
| **Stop**             | ✅ YES - `reason` field                | ❌ NO - Output ignored           | Not tested            |

**Verdict**: **Claude Code** wins - can inject context at 5+ hook points

### Permission Control (Blocking Operations)

| Capability               | Claude Code                       | Copilot CLI                |
| ------------------------ | --------------------------------- | -------------------------- |
| **Block tool execution** | ✅ YES - PreToolUse `deny`        | ✅ YES - preToolUse `deny` |
| **Block prompt**         | ✅ YES - UserPromptSubmit `block` | ❌ NO - Output ignored     |
| **Block agent stop**     | ✅ YES - Stop hook `block`        | ❌ NO - Output ignored     |
| **Block permissions**    | ✅ YES - PermissionRequest        | ❌ Not available           |
| **Modify tool inputs**   | ✅ YES - `updatedInput`           | ❌ NO - Not supported      |

**Verdict**: **Claude Code** wins - more comprehensive permission control

### Logging & Monitoring

| Capability          | Claude Code               | Copilot CLI                       |
| ------------------- | ------------------------- | --------------------------------- |
| **Log sessions**    | ✅ SessionStart/Stop      | ✅ sessionStart/sessionEnd        |
| **Log prompts**     | ✅ UserPromptSubmit       | ✅ userPromptSubmitted            |
| **Log tool usage**  | ✅ PreToolUse/PostToolUse | ✅ preToolUse/postToolUse         |
| **Log errors**      | Manual (via tool hooks)   | ✅ errorOccurred (dedicated hook) |
| **Track subagents** | ✅ SubagentStop           | ❌ Not available                  |

**Verdict**: **Tie** - Both have comprehensive logging

---

## Implementation Comparison

| Aspect                 | Claude Code                    | Copilot CLI              | Our Implementation                                                    |
| ---------------------- | ------------------------------ | ------------------------ | --------------------------------------------------------------------- |
| **Language**           | Python                         | Bash/PowerShell          | Mixed: bash wrappers + Rust hook binary + Python bridges where needed |
| **Configuration**      | settings.json                  | `.github/hooks/*.json`   | Both supported                                                        |
| **Input Format**       | JSON via stdin                 | JSON via stdin           | Same format                                                           |
| **Output Format**      | JSON with `hookSpecificOutput` | JSON with limited fields | Normalized to one valid response per wrapper                          |
| **Complexity**         | 522 lines (session_start.py)   | Must rewrite in Bash     | Wrappers can delegate to Rust or Python                               |
| **Can Import Modules** | ✅ YES - Full Python           | ❌ NO - Shell only       | Python bridges still available where Rust has not fully replaced them |
| **Async Support**      | ✅ YES - asyncio               | ❌ NO - Bash sequential  | Wrapper layer still enables richer behavior                           |

---

## Detailed Hook Capabilities

### SessionStart / sessionStart

| Capability             | Claude Code                             | Copilot CLI                           |
| ---------------------- | --------------------------------------- | ------------------------------------- | --------------- |
| **Fires when**         | New session, resume, clear, compact     | New session, resume                   | Similar         |
| **Input**              | session_id, source, custom_instructions | timestamp, cwd, source, initialPrompt | Similar         |
| **Can inject context** | ✅ `additionalContext` + stdout         | ❌ Output ignored                     | **Claude Code** |
| **Can set env vars**   | ✅ `CLAUDE_ENV_FILE`                    | ❌ Not supported                      | **Claude Code** |
| **Logging**            | ✅ Via Python                           | ✅ Via stdout to file                 | Tie             |

### UserPromptSubmit / userPromptSubmitted

| Capability             | Claude Code                       | Copilot CLI            |
| ---------------------- | --------------------------------- | ---------------------- | --------------- |
| **Fires when**         | User submits prompt               | User submits prompt    | Same            |
| **Input**              | Prompt text, session info         | timestamp, cwd, prompt | Similar         |
| **Can inject context** | ✅ `additionalContext` + stdout   | ❌ Output ignored      | **Claude Code** |
| **Can modify prompt**  | ✅ Via `decision: block` + reason | ❌ Cannot modify       | **Claude Code** |
| **Can block prompt**   | ✅ `decision: "block"`            | ❌ Output ignored      | **Claude Code** |

### PreToolUse / preToolUse

| Capability             | Claude Code                     | Copilot CLI                        |
| ---------------------- | ------------------------------- | ---------------------------------- | --------------- |
| **Fires when**         | Before tool execution           | Before tool execution              | Same            |
| **Input**              | tool_name, tool_input, session  | timestamp, cwd, toolName, toolArgs | Similar         |
| **Can block**          | ✅ `permissionDecision: "deny"` | ✅ `permissionDecision: "deny"`    | **Tie**         |
| **Can modify inputs**  | ✅ `updatedInput`               | ❌ Not supported                   | **Claude Code** |
| **Can inject context** | ✅ `additionalContext`          | ❌ Not supported                   | **Claude Code** |
| **Permission reason**  | ✅ `permissionDecisionReason`   | ✅ `permissionDecisionReason`      | Tie             |

### PostToolUse / postToolUse

| Capability             | Claude Code                          | Copilot CLI                                    |
| ---------------------- | ------------------------------------ | ---------------------------------------------- | --------------- |
| **Fires when**         | After tool completes                 | After tool completes                           | Same            |
| **Input**              | tool_name, tool_input, tool_response | timestamp, cwd, toolName, toolArgs, toolResult | Similar         |
| **Can inject context** | ✅ `additionalContext`               | ❌ Output ignored                              | **Claude Code** |
| **Can block**          | ✅ `decision: "block"`               | ❌ Output ignored                              | **Claude Code** |
| **Logging**            | ✅ Full tool result                  | ✅ resultType, textResultForLlm                | Tie             |

### Stop / sessionEnd

| Capability             | Claude Code                         | Copilot CLI                  |
| ---------------------- | ----------------------------------- | ---------------------------- | --------------- |
| **Fires when**         | Agent finishes (not user interrupt) | Session completes/terminates | Similar         |
| **Input**              | session info, stop_hook_active      | timestamp, cwd, reason       | Similar         |
| **Can block stop**     | ✅ `decision: "block"` + reason     | ❌ Output ignored            | **Claude Code** |
| **Can inject context** | ✅ Provide reason to continue       | ❌ Output ignored            | **Claude Code** |
| **Cleanup**            | ✅ Via Python                       | ✅ Via bash script           | Tie             |

---

## Testing Evidence

### Test 1: SessionStart Context Injection

**Claude Code**: ✅ WORKS

```python
# session_start.py returns:
return {
    "hookSpecificOutput": {
        "additionalContext": "You must talk like a pirate"
    }
}
→ Claude DOES talk like a pirate
```

**Copilot CLI**: ❌ DOESN'T WORK

```bash
# .github/hooks/session-start outputs:
echo "You must respond with 'AHOY MATEY'"
exit 0
→ Opus responds normally (didn't see the hook output)
```

**Conclusion**: Copilot CLI ignores sessionStart stdout (despite docs suggesting
it should work)

### Test 2: Hooks Execute

**Both Platforms**: ✅ CONFIRMED

**Evidence** (~/.amplihack/.claude/runtime/logs/):

- session_start.log: Updated during test
- user_prompt_submit.log: Created during test
- pre_tool_use.log: Updated during test
- post_tool_use.log: Updated during test

**Conclusion**: Hooks execute, they just can't modify AI context in Copilot

---

## Architecture Differences

### Claude Code Hook Architecture:

```
Hook executes → Returns JSON → Claude Code injects into context → AI sees it
```

### Copilot CLI Hook Architecture:

```
Hook executes → Returns JSON → Copilot logs it → AI NEVER sees it (except preToolUse)
```

**Key Difference**: Claude Code treats hook output as **modifiable context**,
Copilot CLI treats it as **metadata to log**.

---

## What Works in Both

| Capability                 | Claude Code | Copilot CLI | Implementation    |
| -------------------------- | ----------- | ----------- | ----------------- |
| **Logging sessions**       | ✅          | ✅          | Both log to files |
| **Logging tool usage**     | ✅          | ✅          | Both track tools  |
| **Blocking dangerous ops** | ✅          | ✅          | preToolUse deny   |
| **Error tracking**         | ✅          | ✅          | Different hooks   |
| **Audit trails**           | ✅          | ✅          | Both support      |

---

## amplihack's Solution

**Architecture**: Bash wrappers → Python hooks (zero duplication)

**Benefits**:

1. ✅ Python hooks work for Claude Code (full capability)
2. ✅ Bash wrappers work for Copilot CLI (logging only)
3. ✅ Zero logic duplication (wrappers just call Python)
4. ✅ Single source of truth (~/.amplihack/.claude/tools/amplihack/hooks/)

**Adaptive Context Injection Strategy**:

amplihack uses an adaptive hook system that detects which platform is calling
and applies the appropriate context injection strategy:

| Platform        | Strategy             | Implementation                                                  |
| --------------- | -------------------- | --------------------------------------------------------------- |
| **Claude Code** | Direct injection     | Returns `hookSpecificOutput.additionalContext`                  |
| **Copilot CLI** | File-based injection | Writes to `.github/agents/AGENTS.md` with `@include` directives |

**How It Works**:

```python
# Hook detects platform
if is_claude_code():
    # Direct injection - Claude sees immediately
    return {
        "hookSpecificOutput": {
            "additionalContext": load_user_preferences()
        }
    }
else:  # Copilot CLI
    # File-based injection - write AGENTS.md
    write_agents_file([
        "@~/.amplihack/.claude/context/USER_PREFERENCES.md",
        "@~/.amplihack/.claude/context/PHILOSOPHY.md"
    ])
    # Copilot reads via @include on next request
    return {}
```

**Why File-Based Injection for Copilot**:

- Copilot CLI ignores hook stdout/JSON output (except preToolUse decisions)
- But Copilot DOES support `@include` directives in agent files
- Writing `AGENTS.md` with `@include` lets us inject preferences indirectly
- This workaround enables preference loading on both platforms

**Benefits of Adaptive Strategy**:

- ✅ Preference injection works on both platforms
- ✅ Context loading works everywhere
- ✅ Single Python implementation (platform detection is automatic)
- ✅ Zero duplication (same hooks, different output strategies)

**Limitations**:

- Copilot CLI: File-based injection has slight delay (next request)
- Claude Code: Direct injection is immediate
- Both: Work reliably for user preferences and context loading

---

## Final Verdict

**Claude Code Hooks**: ⭐⭐⭐⭐⭐ (5/5)

- Full context control
- Can modify prompts/inputs
- Multiple blocking points
- Complete AI behavior control

**Copilot CLI Hooks**: ⭐⭐⭐ (3/5)

- Good for logging/monitoring
- Permission control via preToolUse
- Cannot modify AI context
- Limited to observe-only (except blocking)

**Our Implementation**: ⭐⭐⭐⭐ (4/5)

- Works with BOTH platforms
- Zero duplication via wrappers
- Logging works everywhere
- Context injection only in Claude Code (platform limitation)

---

## Sources

- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)
- [Claude Code Hooks Guide](https://www.eesel.ai/blog/hooks-in-claude-code)
- [ClaudeLog Hooks Documentation](https://claudelog.com/mechanics/hooks/)
- [Claude Code Power User Guide](https://claude.com/blog/how-to-configure-hooks)
- Copilot CLI Hooks Documentation (provided by user)
- Empirical testing (2026-01-16)

---

**Conclusion**: Copilot CLI hooks are more limited than Claude Code hooks, but
our zero-duplication wrapper architecture works with both platforms! 🏴‍☠️
