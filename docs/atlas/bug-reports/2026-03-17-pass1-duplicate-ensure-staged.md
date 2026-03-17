# Bug: Duplicate `_ensure_amplihack_staged()` in session.py and cli.py

**Severity:** major
**Found in pass:** 1 (contradiction-hunt)
**Layers involved:** 7, 8
**Date:** 2026-03-17

## Description

Both `src/amplihack/session.py` (line 380) and `src/amplihack/cli.py` (line 1134) define `_ensure_amplihack_staged()`. Both implementations stage `.claude/` files to `~/.amplihack/.claude/` for UVX mode. If both code paths are reachable in a single execution, the staging runs twice, wasting I/O and risking race conditions on concurrent writes.

## Evidence

### Layer 8 truth: AST Symbol Bindings

```python
# src/amplihack/session.py:380
def _ensure_amplihack_staged() -> None:
```

_Source: `src/amplihack/session.py:380`_

```python
# src/amplihack/cli.py:1134
def _ensure_amplihack_staged() -> None:
```

_Source: `src/amplihack/cli.py:1134`_

## Contradiction

Two implementations of the same private function exist in two modules. The `session.py` docstring says it was "Extracted from cli.py (issue #2845)" but the original was not removed from `cli.py`.

## Recommendation

Remove the duplicate from `session.py` and have it import from `cli.py`, or extract to a shared utility module.
