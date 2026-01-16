# Automatic Copilot CLI Sync

**Problem**: Copilot CLI agents/commands/skills are adapted copies of Claude Code originals. Changes to `.claude/` must sync to `.github/`.

**Solution**: Automatic sync via multiple mechanisms.

## Auto-Sync Mechanisms

### 1. Startup Hook (Default) ✅

**When**: Every Copilot CLI session start
**How**: `.claude/tools/amplihack/hooks/copilot_session_start.py`
**Behavior**:
- Checks if .github/ is stale
- Auto-syncs if needed (< 2s)
- Configurable: always/never/ask

**Configuration** (`.claude/config.json`):
```json
{
  "copilot_auto_sync_agents": "ask",
  "copilot_sync_on_startup": true
}
```

### 2. Git Pre-Commit Hook (Optional) ✅

**When**: Before every git commit
**How**: `.pre-commit-config-copilot-sync.yaml`
**Behavior**:
- Syncs when `.claude/agents/`, `.claude/commands/`, or `.claude/skills/` change
- Auto-stages synced files
- Transparent to user

**Install**:
```bash
# Merge into existing .pre-commit-config.yaml or use standalone
pre-commit install
```

**Benefits**:
- ✅ Never forget to sync
- ✅ .github/ always matches .claude/
- ✅ No drift possible
- ✅ Automatic staging

### 3. Manual Sync Commands (Always Available)

```bash
amplihack sync-agents    # Sync 38 agents
amplihack sync-commands  # Sync 32 commands
amplihack sync-skills    # Sync 67 skills

# Or all at once:
amplihack setup-copilot  # Full resync
```

## Why We Need Duplication

### Format Adaptation Required

**Agents**:
```diff
- Claude: role + model fields, Task() tool
+ Copilot: combined description, triggers, subagent patterns
```

**Commands**:
```diff
- Claude: @.claude/ references, Skill() tool
+ Copilot: @.github/ references, @agent references
```

**Skills**:
```diff
- Claude: Markdown format with frontmatter
+ Copilot: YAML agent definitions only
```

**Cannot use symlinks** - formats are fundamentally different.

### Alternatives Considered

❌ **Dual-format files** - Violates ruthless simplicity
❌ **Runtime conversion** - Too slow, complex
❌ **Symlinks** - Doesn't work (formats differ)
✅ **Generated copies + auto-sync** - Simple, works, maintainable

## Maintenance Burden

### With Auto-Sync (Recommended)

**User experience:**
1. Edit agent in `.claude/agents/architect.md`
2. `git commit` → Pre-commit auto-syncs → Both versions updated ✅
3. Or start Copilot session → Startup hook auto-syncs ✅

**Zero manual intervention required!**

### Without Auto-Sync

**User experience:**
1. Edit agent in `.claude/agents/architect.md`
2. Remember to run `amplihack sync-agents` ❌
3. Or risk using stale Copilot version ❌

**Manual burden, error-prone.**

## Recommendation

**Enable both auto-sync mechanisms:**
1. ✅ Startup hook (already enabled by default)
2. ✅ Pre-commit hook (add to .pre-commit-config.yaml)

**Result**: Users never think about sync - it just works! ⚓

## Philosophy Compliance

**Is this duplication OK?**

✅ **Yes** - It's not true duplication, it's **transformation**:
- Source files (Claude format) in `.claude/`
- Generated files (Copilot format) in `.github/`
- Auto-sync keeps them in sync
- Single source of truth: `.claude/` (authoritative)

**Principle**: "Code you don't write has no bugs"
- We didn't write duplicate agent logic
- We wrote a converter that generates Copilot format
- The converter is the code, not the generated files

**Verdict**: Philosophy-compliant ✅
