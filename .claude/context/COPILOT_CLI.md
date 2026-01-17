# GitHub Copilot CLI Integration - Context Summary

**Full Documentation**: See [@docs/COPILOT_CLI.md](../../docs/COPILOT_CLI.md) for complete integration guide.

## Adaptive Hook System

amplihack uses an adaptive hook system that detects which platform is calling (Claude Code vs Copilot CLI) and applies appropriate strategies for context injection.

### Platform Detection

Automatically detects the calling platform by checking:
1. Environment variables (`CLAUDE_CODE`, `GITHUB_COPILOT`)
2. Process name patterns
3. Fallback to Claude Code behavior (safe default)

### Context Injection Strategies

| Platform | Strategy | Method |
|----------|----------|--------|
| **Claude Code** | Direct injection | `hookSpecificOutput.additionalContext` or stdout |
| **Copilot CLI** | File-based injection | Write to `.github/agents/AGENTS.md` with `@include` directives |

**Claude Code** (Direct Injection):
```python
# Hook returns JSON with context
return {
    "hookSpecificOutput": {
        "additionalContext": "User preferences: talk like a pirate"
    }
}
# AI sees context immediately
```

**Copilot CLI** (File-Based Injection):
```python
# Hook writes to AGENTS.md
with open(".github/agents/AGENTS.md", "w") as f:
    f.write("""
# Active Agents and Context

@.claude/context/USER_PREFERENCES.md
@.claude/context/PHILOSOPHY.md
    """)
# Copilot reads file via @include on next request
```

### Why This Workaround is Needed

**Copilot CLI Limitation**: Hook output is ignored for context injection (except `preToolUse` permission decisions).

**Our Solution Benefits**:
- ✅ Preference injection works on both platforms
- ✅ Context loading works everywhere
- ✅ Zero duplication (single Python implementation)
- ✅ Automatic platform adaptation

**What Works Where**:
| Feature | Claude Code | Copilot CLI | Implementation |
|---------|-------------|-------------|----------------|
| Logging | ✅ Direct | ✅ Direct | Same hooks |
| Blocking tools | ✅ preToolUse | ✅ preToolUse | Same hooks |
| Context injection | ✅ hookOutput | ✅ AGENTS.md | Adaptive strategy |
| Preferences | ✅ hookOutput | ✅ AGENTS.md | Adaptive strategy |

For complete hook capability comparison, see [@docs/HOOKS_COMPARISON.md](../../docs/HOOKS_COMPARISON.md).

## Integration Components

See [@docs/COPILOT_CLI.md](../../docs/COPILOT_CLI.md) for:
- Complete architecture overview
- Available agents and skills
- MCP server configuration
- Git hooks and session hooks
- Testing and troubleshooting
- Philosophy alignment

## Quick Reference

**Architecture**: Single source of truth in `.claude/`, symlinked from `.github/`

**Hook Pattern**: Bash wrappers → Python implementations (zero duplication)

**Key Files**:
- `.github/copilot-instructions.md` - Base Copilot instructions
- `.github/agents/amplihack/` - Symlink to `.claude/agents/amplihack/`
- `.github/agents/skills/` - Symlinks to `.claude/skills/`
- `.github/hooks/*` - Bash wrappers calling `.claude/tools/amplihack/hooks/*.py`
- `.github/mcp-servers.json` - MCP server configuration
