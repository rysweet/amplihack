# Bug: Dual FastAPI App Instances in integrated_proxy.py

**Severity:** major
**Found in pass:** 1 (contradiction-hunt)
**Layers involved:** 3, 7
**Date:** 2026-03-17

## Description

`src/amplihack/proxy/integrated_proxy.py` contains both a `create_app()` factory function (line 212) that creates a scoped `FastAPI()` app, AND a module-level `app = FastAPI()` (line 610) with its own set of route handlers. This means there are **two separate FastAPI applications** in the same file, with duplicated routes (e.g., `POST /v1/messages` is defined twice -- once inside `create_app()` at line 578 and once on the module-level `app` at line 689).

## Evidence

### Layer 3 truth: Routing

```python
# src/amplihack/proxy/integrated_proxy.py:212
def create_app(config: dict[str, str] | None = None) -> FastAPI:
    app = FastAPI()
    # ... defines routes at lines 238, 275, 295, 578
```

_Source: `src/amplihack/proxy/integrated_proxy.py:212`_

```python
# src/amplihack/proxy/integrated_proxy.py:610
# Legacy global app instance (for backward compatibility)
app = FastAPI()
# ... defines routes at lines 671, 689, 1152, 1223, 1228, 1257, 1286, 1321, 1363
```

_Source: `src/amplihack/proxy/integrated_proxy.py:610`_

## Contradiction

Layer 3 shows duplicate HTTP routes (`POST /v1/messages` appears at both line 578 and line 689). Layer 7 shows the `create_app()` factory and the module-level `app` have different route sets, making behavior depend on which app instance is used. The "Legacy global app instance" comment suggests this is technical debt.

## Recommendation

Migrate all routes into `create_app()` and remove the module-level `app = FastAPI()` and its duplicate routes, or extract shared handlers to avoid code duplication.
