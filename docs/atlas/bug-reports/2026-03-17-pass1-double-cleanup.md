# Bug: `cleanup_legacy_skills()` Imported in Both session.py and cli.py

**Severity:** minor
**Found in pass:** 1 (contradiction-hunt)
**Layers involved:** 7, 8
**Date:** 2026-03-17

## Description

`cleanup_legacy_skills()` from `staging_cleanup.py` is imported at the top of both `session.py` (line 26) and `cli.py` (line 24). Since `cli.py:launch_command()` calls `_common_launcher_startup()` which likely calls `cleanup_legacy_skills()`, and `session.py:launch_command()` also calls it, the cleanup could run twice if both code paths are traversed in a single process.

## Evidence

### Layer 8 truth: Symbol References

```python
# src/amplihack/cli.py:24
from .staging_cleanup import cleanup_legacy_skills
```

_Source: `src/amplihack/cli.py:24`_

```python
# src/amplihack/session.py:26
from .staging_cleanup import cleanup_legacy_skills
```

_Source: `src/amplihack/session.py:26`_

## Contradiction

Both modules import the same cleanup function. Given that `session.py` is likely dead code (see separate bug report on duplicate `launch_command`), this may not cause runtime issues. But it indicates incomplete code extraction.

## Recommendation

Remove the import from `session.py` as part of the overall cleanup of the session.py/cli.py duplication.
