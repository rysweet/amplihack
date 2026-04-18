# Workflow to Skills Migration Guide

**Version**: 2.0
**Date**: 2026-04-17
**Status**: Phase 6 (Python → Rust CLI Migration Complete)

## Architecture Change

**Before**: Workflows | Commands | Agents | Skills (4 mechanisms)
**After**: Skills | Commands | Agents (3 mechanisms)

Workflows are now implemented as skills per Claude Code best practices.

## Deprecated Files

| File                      | Replacement                  |
| ------------------------- | ---------------------------- |
| DEFAULT_WORKFLOW.md       | default-workflow skill       |
| INVESTIGATION_WORKFLOW.md | investigation-workflow skill |
| CASCADE_WORKFLOW.md       | cascade-workflow skill       |
| CONSENSUS_WORKFLOW.md     | consensus-workflow skill     |
| DEBATE_WORKFLOW.md        | debate-workflow skill        |
| N_VERSION_WORKFLOW.md     | n-version-workflow skill     |

## Timeline

- **v1.0 (2025-11-20)**: Deprecation warnings (Phase 5)
- **v2.0 (2026-04-17)**: Python → Rust CLI migration complete (Phase 6)
- **v3.0 (planned)**: Markdown workflows removed

---

## Phase 6: Python → Rust CLI Skill Migration (April 2026)

Skills previously invoked workflows through the Python `amplihack` package
API. All skill files have been migrated to use `amplihack recipe run` (the
Rust CLI) as the primary execution path.

### What Changed

**Old pattern (deprecated):**

```python
from amplihack.recipes import run_recipe_by_name
from amplihack.launcher_detector import LauncherDetector

detector = LauncherDetector()
result = run_recipe_by_name("default-workflow", context={...})
```

**New pattern (canonical):**

```bash
amplihack recipe run default-workflow \
  -c task_description="Fix login timeout" \
  -c repo_path="$(pwd)"
```

### Migration Scope

| PR | Scope | Files |
|----|-------|-------|
| [#4383](https://github.com/rysweet/amplihack/pull/4383) | Core skills | 6 key skill files |
| [#4386](https://github.com/rysweet/amplihack/pull/4386) | Full directory | 30 skill files in `.claude/skills/` |

### Pattern Replacements Applied

| Old pattern | New pattern |
|------------|-------------|
| `run_recipe_by_name()` | `amplihack recipe run <name>` |
| `LauncherDetector` import | `AMPLIHACK_AGENT_BINARY` env var |
| `src/amplihack/` paths | `crates/amplihack-*/src/` paths |
| `from amplihack.*` Python imports | `use amplihack_*::` Rust statements |
| Legacy Python API blocks | Removed or marked deprecated |

### Skills Not Yet Migrated

These skills have no Rust CLI equivalent and retain their Python invocation:

| Skill | Reason |
|-------|--------|
| `mcp-manager` | Standalone Python tool (`python3 -m mcp-manager.cli`) |
| `transcript-viewer` | Python one-liners for JSONL parsing |
| `gh-work-report` | Python heredocs for data processing |

### Agent Binary Configuration

Skills now use the centralized `AMPLIHACK_AGENT_BINARY` env var (established
in PR #3174) for agent-agnostic binary selection:

```bash
export AMPLIHACK_AGENT_BINARY=claude    # default
export AMPLIHACK_AGENT_BINARY=copilot  # GitHub Copilot CLI
export AMPLIHACK_AGENT_BINARY=/path/to/custom-agent
```

This replaces the `LauncherDetector` Python class across all migrated skills.

---

## Related

- CLAUDE.md: 3-mechanism architecture
- Specs/ATOMIC_DELIVERY_PLAN.md: Migration plan
- [docs/recipes/RECENT_FIXES_APRIL_2026.md](./recipes/RECENT_FIXES_APRIL_2026.md): Detailed PR notes for the migration
- [docs/recipes/README.md](./recipes/README.md): Recipe runner engine selection and CLI reference
