# Bug: Duplicate `launch_command()` Definitions in session.py and cli.py

**Severity:** major
**Found in pass:** 1 (contradiction-hunt)
**Layers involved:** 7, 8
**Date:** 2026-03-17

## Description

Both `src/amplihack/session.py` and `src/amplihack/cli.py` define a function named `launch_command()` with the same signature `(args, claude_args=None) -> int`. The `session.py` version imports `ClaudeLauncher`, `DockerManager`, `ProxyManager`, etc. -- the same imports that `cli.py` also performs. The `cli.py` version is the one actually called from `main()`, making the `session.py` version unreachable through normal execution paths.

## Evidence

### Layer 7 truth: Service Components

```python
# src/amplihack/session.py:41
def launch_command(args: argparse.Namespace, claude_args: list[str] | None = None) -> int:
    """Handle the launch command."""
```

_Source: `src/amplihack/session.py:41`_

### Layer 7 truth: Service Components

```python
# src/amplihack/cli.py:136
def launch_command(args: argparse.Namespace, claude_args: list[str] | None = None) -> int:
    """Handle the launch command."""
```

_Source: `src/amplihack/cli.py:136`_

## Contradiction

Layer 7 shows both `session.py` and `cli.py` define `launch_command()`. Layer 8 static analysis confirms that `main()` in `cli.py` calls its own local `launch_command()`, never the one in `session.py`. The `session.py` version appears to be a leftover from the extraction mentioned in its docstring ("Extracted from cli.py, issue #2845").

## Recommendation

Remove `launch_command()` from `session.py` (and its duplicate imports) or consolidate into a single module to eliminate the shadowing.
