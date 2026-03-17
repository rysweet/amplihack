# Pass 3: Journey Verdict -- Install and Launch

**Date:** 2026-03-17

## Journey: install-and-launch

### Verdict: NEEDS_ATTENTION

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Layer 3 routes match journey steps | pass | `src/amplihack/cli.py:504` -- `create_parser()` defines `install` and `launch` subcommands |
| Layer 4 data flows complete | pass | `src/amplihack/install.py` -- `copytree_manifest()`, `ensure_settings_json()`, `verify_hooks()` all present |
| Layer 7 service components reachable | attention | `src/amplihack/session.py` -- `_ensure_amplihack_staged()` is unreachable duplicate; staging may use wrong version |
| No dead code on critical path | attention | `src/amplihack/session.py:41` -- `launch_command()` is dead code on the import path but its imports still execute |

**Verdict Rationale:** The install-and-launch journey's core path (CLI -> install -> launch) works correctly through `cli.py`. However, the dead code in `session.py` means that importing `session.py` (which happens because `cli.py` imports from the same package) loads unnecessary imports (`DockerManager`, `ClaudeLauncher`, `ProxyManager`) that slow down startup. The `_ensure_amplihack_staged()` duplicate means a maintainer could accidentally call the wrong version. NEEDS_ATTENTION because the journey works but carries unnecessary technical debt.
