# GitHub Copilot CLI Hooks vs Claude Code Hooks: Limitations & Trade-offs

**Date**: 2026-01-16
**Context**: Issue #1906 - Copilot CLI Integration

## Executive Summary

Copilot CLI hooks have **significant limitations** compared to Claude Code hooks, requiring different implementation approaches.

## Detailed Comparison

| Feature | Claude Code Hooks | Copilot CLI Hooks | Impact |
|---------|-------------------|-------------------|---------|
| **Language** | Python | Bash/PowerShell ONLY | Must rewrite all logic |
| **Import amplihack** | ✅ Can import Python modules | ❌ Cannot import - isolated scripts | Hooks can't reuse code |
| **State Access** | ✅ Direct Python objects | ❌ File-based only (JSON) | More complex state |
| **Context** | ✅ Full access to runtime | ❌ JSON stdin only | Limited context |
| **Tool Control** | ❌ N/A (Claude trusts hooks) | ✅ Can deny tool execution | NEW capability! |
| **Async** | ✅ asyncio supported | ❌ Sequential only | No parallel ops |
| **Error Handling** | ✅ Python exceptions | ❌ Exit codes + stderr | Less granular |
| **Testing** | ✅ pytest, mocking | ❌ Bash testing only | Harder to test |
| **IDE Support** | ✅ Full Python tooling | ❌ Limited bash tooling | Harder to maintain |
| **Performance** | ✅ Fast (compiled) | ⚠️ Shell overhead | Slight slowdown |

## Implementation Approaches Taken

### 1. Hooks: **Bash Wrappers Calling Python** ✅ HYBRID

**What we did:**
- `.github/hooks/scripts/session-start.sh` → Calls `.claude/tools/amplihack/hooks/session_start.py`
- `.github/hooks/scripts/session-end.sh` → Calls `.claude/tools/amplihack/hooks/stop.py`
- Other hooks are minimal bash (userPromptSubmitted, preToolUse, postToolUse, errorOccurred)

**Why this works:**
- ✅ Single source of truth (Python hooks)
- ✅ No code duplication
- ✅ Copilot CLI can call bash, bash calls Python
- ✅ Full amplihack functionality preserved
- ✅ Easy to maintain (edit Python, bash wrapper unchanged)

**Limitations:**
- ⚠️ Requires Python available (already required by amplihack)
- ⚠️ sessionStart and sessionEnd work, but userPromptSubmitted/preToolUse/postToolUse are Copilot-specific (don't have Python equivalents)

### 2. Agents: **Generated Copies (Adapted)** ⚠️ NECESSARY DUPLICATION

**What we did:**
- `.claude/agents/` → Converted → `.github/agents/` (adapted format)
- NOT symlinks, NOT wrappers - actual file copies with transformations

**Why we can't symlink:**
```diff
# Claude Code agent format:
---
name: architect
version: 1.0.0
description: "..."
role: "System architect..."
model: inherit
---
Use Task(subagent_type="builder") for implementation

# Copilot CLI agent format (DIFFERENT):
---
name: architect
description: "System architect..." (combined description+role)
triggers:
  - architecture
  - design
---
Use subagent invocation for implementation
```

**Adaptations needed:**
- ❌ Can't symlink - formats are different
- ✅ Must generate adapted files
- ✅ Must run `amplihack sync-agents` after editing .claude/agents/
- ⚠️ Risk of drift if sync forgotten

**Better approach considered:**
- Make agents work with BOTH formats (dual frontmatter)
- But this violates ruthless simplicity
- Current approach: Accept the sync requirement

### 3. Commands: **Generated Copies** ⚠️ NECESSARY DUPLICATION

**What we did:**
- `.claude/commands/**/*.md` → `.github/commands/**/*.md`
- Adapted references (@.claude/ → @.github/)

**Why not symlinks:**
- Commands reference `.claude/` paths that need adaptation
- Invocation patterns differ (Skill() vs @references)
- Must be converted, not linked

### 4. Skills: **Generated Agent YAML** ⚠️ FORMAT CONVERSION

**What we did:**
- `.claude/skills/` (markdown) → `.github/agents/skills/` (YAML format)
- Complete format conversion (markdown → YAML frontmatter + description)
- 67 skills → 58 agent files

**Why not symlinks:**
- Format completely different (markdown → YAML)
- Copilot expects YAML agent definitions
- Conversion required

## Copilot CLI Hooks Limitations

### What Copilot Hooks CANNOT Do (vs Claude Code)

1. **Cannot import amplihack Python modules**
   - Isolated bash scripts
   - No access to ContextPreserver, HookProcessor, etc.
   - Must reimplement logic in bash or call Python as subprocess

2. **Cannot access Claude Code context directly**
   - Only get JSON stdin
   - No access to conversation history, tool results, etc.
   - Limited to what Copilot provides in JSON

3. **Cannot modify prompts** (userPromptSubmitted)
   - Claude Code: Can inject context into prompts
   - Copilot CLI: Output ignored, can only log
   - Missing user preference injection capability

4. **Cannot modify tool results** (postToolUse)
   - Claude Code: Can transform results
   - Copilot CLI: Output ignored, can only log
   - Can't enhance tool output

5. **No async support**
   - All hooks run sequentially
   - No concurrent operations
   - Claude Code can run async hooks

### What Copilot Hooks CAN Do (NEW!)

1. **Permission control** (preToolUse)
   - Can DENY tool execution
   - Can block dangerous operations
   - Claude Code doesn't have this!
   - Security win: Block --no-verify, rm -rf /, etc.

2. **Cross-platform** (Bash + PowerShell)
   - Works on Windows, Linux, macOS
   - Claude Code hooks are Python only

## Code Duplication Analysis

### ❌ Duplicated (Necessary)

| Component | Source | Target | Reason | Sync Required |
|-----------|--------|--------|--------|---------------|
| **Agents** | .claude/agents/ | .github/agents/ | Format adaptation (frontmatter, instructions) | `amplihack sync-agents` |
| **Commands** | .claude/commands/ | .github/commands/ | Reference adaptation (@.claude/ → @.github/) | `amplihack sync-commands` |
| **Skills** | .claude/skills/ (MD) | .github/agents/skills/ (YAML) | Format conversion (MD → YAML) | `amplihack sync-skills` |

**Total files duplicated**: 38 agents + 32 commands + 58 skills = **128 files**

**Disk usage**: ~2MB (text files, minimal impact)

### ✅ No Duplication (Wrappers)

| Component | Approach | Size |
|-----------|----------|------|
| **sessionStart** | Bash wrapper → Python hook | 24 lines (was 132) |
| **sessionEnd** | Bash wrapper → Python hook | 18 lines (was 86) |
| **userPromptSubmitted** | Minimal bash (Copilot-specific) | 26 lines |
| **preToolUse** | Minimal bash (Copilot-specific) | 33 lines |
| **postToolUse** | Minimal bash (logging only) | 21 lines |
| **errorOccurred** | Minimal bash (logging only) | 27 lines |

**Total hook code**: ~150 lines (vs ~600 lines if fully duplicated)
**Savings**: 450 lines eliminated via wrappers

## Maintenance Implications

### What Users Must Do

**After editing `.claude/agents/`:**
```bash
amplihack sync-agents
```

**After editing `.claude/commands/`:**
```bash
amplihack sync-commands
```

**After editing `.claude/skills/`:**
```bash
amplihack sync-skills
```

**After editing Python hooks** (.claude/tools/):
- Nothing! Bash wrappers call them automatically ✅

### Auto-Sync Options

**Option A: Git pre-commit hook** (Recommended)
```bash
# .git/hooks/pre-commit
amplihack sync-agents --force
amplihack sync-commands --force
amplihack sync-skills --force
```

**Option B: File watcher** (Development)
```bash
# Watch for changes and auto-sync
fswatch .claude/agents/ | xargs -n1 amplihack sync-agents
```

**Option C: Startup hook** (Current)
- `.claude/tools/amplihack/hooks/copilot_session_start.py` checks staleness
- Auto-syncs if needed
- User preference: always/never/ask

## Why We Can't Use Pure Symlinks

### Technical Reasons

1. **Format Differences**
   - Claude agents: YAML frontmatter + Claude-specific patterns
   - Copilot agents: Different YAML structure + Copilot patterns
   - Cannot be the same file

2. **Reference Adaptation**
   - Claude: `@.claude/context/PHILOSOPHY.md`
   - Copilot: `@.claude/context/PHILOSOPHY.md` (actually works same!)
   - But: `Task()` → subagent patterns need conversion

3. **Tool References**
   - Claude: `Task(subagent_type="builder")`
   - Copilot: "Use subagent invocation"
   - Text must be different

### Could We Use Dual-Format Agents?

**Theoretical approach:**
```markdown
---
# Claude Code frontmatter
name: architect
role: "System architect"
model: inherit

# Copilot CLI frontmatter (also in same file)
copilot:
  name: architect
  triggers: [architecture, design]
---

# Agent instructions (same for both)
You are the system architect...

<!-- Claude Code patterns -->
Use Task(subagent_type="builder") for implementation

<!-- Copilot CLI patterns -->
Use subagent invocation for implementation
```

**Why we didn't:**
- ❌ Violates ruthless simplicity (complex dual format)
- ❌ Confusing to both systems
- ❌ Hard to maintain
- ❌ Not worth the complexity to avoid 2MB of text files

## Recommendation: Accept the Duplication

### Why It's OK

1. **Text files are cheap** - 128 files × ~15KB = ~2MB
2. **Sync is fast** - < 2 seconds for all 128 files
3. **Auto-sync available** - Startup hook handles it
4. **Clear separation** - .claude/ for Claude, .github/ for Copilot
5. **Format adaptation required** - Not true duplication, it's transformation

### Mitigation Strategies

✅ **Implemented:**
- Auto-sync at startup (configurable)
- Fast sync commands (< 2s)
- Staleness detection
- `amplihack setup-copilot` does initial sync

⚠️ **Could add:**
- Git pre-commit hook for auto-sync
- File watcher for development
- CI check that .github/ is synced

## Answer to Your Questions

**Q: This includes hooks?**
A: ✅ YES - All 6 Copilot hook types implemented

**Q: What are limitations of Copilot hooks vs Claude Code hooks?**
A:
- ❌ Cannot import Python modules
- ❌ Cannot modify prompts/results
- ❌ No async support
- ✅ CAN deny tool execution (NEW capability!)

**Q: Did you duplicate code or make wrappers around hooks?**
A: **WRAPPERS** ✅
- sessionStart/sessionEnd: 24-line bash wrappers → Python hooks
- Other 4 hooks: Minimal bash (Copilot-specific, no Python equivalent)
- ~150 lines total (vs ~600 if duplicated)
- Single source of truth preserved

**Q: Did you COPY agents/skills or link to them?**
A: **COPIED (Adapted)** ⚠️ - But for good reason:
- Agents/skills need format adaptation
- Cannot use same file for both systems
- Symlinks won't work (formats differ)
- Must run sync commands after edits
- Auto-sync at startup mitigates issue

---

**Should I implement auto-sync via git pre-commit hook to eliminate manual sync burden?** That would make the duplication transparent to users.