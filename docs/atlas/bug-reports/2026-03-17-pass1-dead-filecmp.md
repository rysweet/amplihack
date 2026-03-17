# Bug: `filecmp()` in `__init__.py` Exported but Never Used

**Severity:** minor
**Found in pass:** 1 (contradiction-hunt)
**Layers involved:** 2, 8
**Date:** 2026-03-17

## Description

`src/amplihack/__init__.py` defines `filecmp(f1, f2)` at line 149 and exports it in `__all__`. However, no module in the codebase imports or calls this function. It is a custom reimplementation of `filecmp.cmp()` from the standard library.

## Evidence

### Layer 8 truth: Dead Code Report

```
grep -r "from.*import.*filecmp\|amplihack\.filecmp" src/ tests/ scripts/
# Returns: no matches (only the definition itself)
```

_Source: `src/amplihack/__init__.py:149`_

## Contradiction

The function is listed in `__all__` (the public API), implying it is part of the module's contract, but no consumer exists.

## Recommendation

Remove `filecmp()` from `__init__.py` and `__all__`, or use the stdlib `filecmp.cmp()` where file comparison is needed.
