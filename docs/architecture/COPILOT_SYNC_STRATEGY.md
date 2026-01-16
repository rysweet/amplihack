# Copilot CLI Sync Strategy - Single Source of Truth

**Last Updated**: 2026-01-16
**Status**: Implementation Guide

## The Problem

GitHub Copilot CLI requires files in `.github/` directories, but amplihack's source of truth is `.claude/`. We must avoid duplication while supporting both platforms.

## Solution Strategy (by Component)

### 1. Agents: CONVERTED COPIES (Necessary)

**Why Copies?**
- Copilot CLI needs different frontmatter format than Claude Code
- Conversion is required (combine description+role, remove model field, add triggers)
- Can't use symlinks because content must change

**Approach**:
- `.claude/agents/` = Source of truth (Claude Code format)
- `.github/agents/` = Generated (Copilot CLI format)
- `amplihack sync-agents` converts source → target
- Auto-sync at setup or session start (if stale)

**Trade-off**: Copies exist, but they're **generated artifacts** like compiled code.

### 2. Hooks: WRAPPERS (Zero Duplication) ✅

**Why Wrappers?**
- Copilot hooks must be Bash/PowerShell
- Python hooks contain complex logic we don't want to rewrite
- Wrappers eliminate duplication

**Approach**:
- `.claude/tools/amplihack/hooks/` = Source (Python, 522+ lines each)
- `.github/hooks/scripts/` = Thin wrappers (15 lines each)
- Wrappers just call Python hooks: `python3 .claude/tools/.../session_start.py`

**Benefit**: Single source of truth, zero duplication!

**Current Implementation**:
```bash
# .github/hooks/scripts/session-start.sh (15 lines)
#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
python3 "$PROJECT_ROOT/.claude/tools/amplihack/hooks/session_start.py" "$@"
```

### 3. Skills: SYMLINKS (Zero Duplication) ✅

**Why Symlinks?**
- Skills are directories, not single files
- Copilot CLI can read skill README.md files
- No format conversion needed

**Approach**:
- `.claude/skills/<skill-name>/` = Source
- `.github/agents/skills/<skill-name>` = Symlink → `../../../.claude/skills/<skill-name>`

**Benefit**: Zero duplication, changes immediately visible!

**Current Implementation**:
```bash
.github/agents/skills/code-smell-detector -> ../../../.claude/skills/code-smell-detector
.github/agents/skills/economist-analyst -> ../../../.claude/skills/economist-analyst
# 67+ symlinks total
```

### 4. Commands: CONVERTED COPIES (Automated Sync) 🤖

**Why Copies?**
- Commands may need adaptation for Copilot CLI invocation patterns
- References to Skill() tool → MCP server patterns
- Task() tool → agent invocation patterns

**Approach**:
- `.claude/commands/` = Source
- `.github/commands/` = Generated (adapted)
- **Automatic sync via pre-commit hook** 🆕
- Manual sync: `amplihack sync-commands`

**Auto-Sync**: Pre-commit hook automatically runs sync when `.claude/commands/` changes!
- Edit command → commit → hook auto-syncs → both files committed
- CI validation ensures sync happened
- See `docs/architecture/AUTO_SYNC.md` for details

**Trade-off**: Like agents, these are generated artifacts, but sync is now automatic!

## Duplication Summary

| Component | Strategy | Duplication | Justification |
|-----------|----------|-------------|---------------|
| **Agents (38)** | Converted Copies | Yes | Format conversion required |
| **Hooks (6)** | Wrappers | **NO** | Python logic preserved |
| **Skills (67)** | Symlinks | **NO** | No conversion needed |
| **Commands (32)** | Converted Copies | Yes | Pattern adaptation required |

**Total Duplication**: 70 files (38 agents + 32 commands)
**Zero Duplication**: 73 files (6 hooks + 67 skills)

## Auto-Sync Strategy

### When Sync Runs

1. **Manual**: `amplihack sync-agents`, `amplihack sync-commands`
2. **Setup**: `amplihack setup-copilot` (runs all syncs)
3. **Session Start** (optional): Copilot session start hook checks staleness

### Staleness Detection

```python
def is_stale(source_dir: Path, target_dir: Path) -> bool:
    """Check if target needs regeneration."""
    # Compare newest source file vs oldest target file
    source_mtime = max(f.stat().st_mtime for f in source_dir.rglob("*.md"))
    target_mtime = min(f.stat().st_mtime for f in target_dir.rglob("*.md"))
    return source_mtime > target_mtime
```

### Auto-Sync Options

**Config in `.claude/config.json`**:
```json
{
  "copilot_auto_sync": "ask",  // "always", "never", "ask"
  "copilot_sync_on_startup": true
}
```

## Maintenance

### When You Update Source Files

**Agents**:
```bash
# Edit .claude/agents/amplihack/core/architect.md
vim .claude/agents/amplihack/core/architect.md

# Sync to Copilot format
amplihack sync-agents
```

**Hooks**: Changes immediately active (wrappers call Python)

**Skills**: Changes immediately active (symlinks)

**Commands**:
```bash
# Edit .claude/commands/amplihack/ultrathink.md
vim .claude/commands/amplihack/ultrathink.md

# Sync to Copilot format
amplihack sync-commands
```

## Comparison with Other Tools

This is similar to:
- **TypeScript** → JavaScript (tsc compiles)
- **Sass** → CSS (sass compiles)
- **.claude/** → **.github/** (amplihack converts)

The `.github/` files are **build artifacts**, not source.

## Philosophy Alignment

✅ **Single Source of Truth**: `.claude/` is authoritative
✅ **Regeneratable**: Can rebuild `.github/` anytime
✅ **Minimal Duplication**: Wrappers and symlinks where possible
✅ **Explicit Build Step**: Users know when to sync
✅ **Zero-BS**: Generated files work, no placeholders

## Limitations of Copilot Hooks

### What Copilot Hooks CAN'T Do (vs Claude Code):

1. **No Python Imports**: Can't `from amplihack import ...`
2. **No Async**: Bash is synchronous only
3. **Limited State**: File-based only, no Python objects
4. **No Tool Access**: Can't call amplihack Python modules directly
5. **JSON Only**: Input/output via JSON stdin/stdout

### What Copilot Hooks CAN Do (NEW):

1. **Permission Control**: Can block tool execution (Claude Code can't)
2. **Cross-Platform**: Bash + PowerShell support
3. **Standard Tooling**: jq, shell commands available

## Recommendation

**Current Implementation** (after fixes):
- ✅ Hooks: Wrappers (zero duplication)
- ✅ Skills: Symlinks (zero duplication)
- ⚠️ Agents: Converted copies (necessary for format)
- ⚠️ Commands: Converted copies (necessary for adaptation)

**Duplication Reduced**: From 143 files → 70 files (51% reduction)

**Maintenance**: Run `amplihack sync-agents` and `amplihack sync-commands` after editing source files in `.claude/`.

---

**This is the philosophically correct approach**: Minimize duplication where possible, accept necessary build artifacts where conversion is required.
