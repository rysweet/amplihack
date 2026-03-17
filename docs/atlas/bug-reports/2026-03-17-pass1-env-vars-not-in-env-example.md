# Bug: Multiple AMPLIHACK_* Env Vars Used But Not Documented in .env.example

**Severity:** minor
**Found in pass:** 1 (contradiction-hunt)
**Layers involved:** 1, 6
**Date:** 2026-03-17

## Description

The codebase uses 12+ `AMPLIHACK_*` environment variables (AMPLIHACK_DEBUG, AMPLIHACK_HOOK_ENGINE, AMPLIHACK_USE_DOCKER, AMPLIHACK_AUTO_MODE, AMPLIHACK_SKIP_REFLECTION, AMPLIHACK_ORIGINAL_CWD, etc.) but `.env.example` only documents Azure credentials. Users have no reference for the amplihack-specific configuration variables.

## Evidence

### Layer 6 truth: Env Var Inventory

```
AMPLIHACK_DEBUG          - session.py:38, cli.py:53
AMPLIHACK_HOOK_ENGINE    - settings.py:266
AMPLIHACK_USE_DOCKER     - docker/detector.py:35
AMPLIHACK_AUTO_MODE      - session.py:177
AMPLIHACK_SKIP_REFLECTION - session.py:173, 278
AMPLIHACK_USE_RECIPES    - workflows/execution_tier_cascade.py:127
```

_Source: Multiple files_

### Layer 1 truth: Runtime Topology

`.env.example` contains only Azure Service Principal credentials.

_Source: `.env.example`_

## Contradiction

Layer 6 documents 12+ AMPLIHACK_* env vars in use. Layer 1's `.env.example` documents none of them. Users must read source code to discover configuration options.

## Recommendation

Add a section to `.env.example` (or create a separate `.env.amplihack.example`) documenting all AMPLIHACK_* environment variables with their defaults and purposes.
