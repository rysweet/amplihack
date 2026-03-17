# Bug: `cli_extensions.py` Module Never Imported

**Severity:** minor
**Found in pass:** 1 (contradiction-hunt)
**Layers involved:** 2, 8
**Date:** 2026-03-17

## Description

`src/amplihack/cli_extensions.py` defines three public functions (`bundle()`, `generate()`, `package()`) but is never imported by any module in the codebase. This is dead code.

## Evidence

### Layer 8 truth: Dead Code Report

```
grep -r "from.*import.*cli_extensions\|amplihack\.cli_extensions" src/ tests/ scripts/
# Returns: no matches
```

_Source: `src/amplihack/cli_extensions.py:20-95`_

### Layer 2 truth: Dependencies

The module imports `bundle_generator` and `goal_agent_generator`, creating unnecessary import chains if the module were ever loaded.

## Contradiction

Layer 2 shows `cli_extensions.py` exists as a module with external imports, but Layer 8 shows zero inbound references. The module is dead code.

## Recommendation

Remove `cli_extensions.py` or wire it into the CLI parser as intended.
