"""Health check module for the amplihack project.

Provides a single entry point `check_health()` that inspects:
  - Critical Python package availability (importlib.util.find_spec — no code executed)
  - Critical path existence relative to _PROJECT_ROOT

Structural assumptions:
  - This file lives at <project_root>/src/amplihack/health_check.py
  - _PROJECT_ROOT is computed once at import time as the directory three levels up

Security note: HealthReport.details contains internal diagnostic data (absolute paths,
package names) intended for developer tooling only. Do NOT expose details in
external-facing APIs or dashboards without sanitizing path and version information.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal

__all__ = ["check_health", "HealthReport"]

# ---------------------------------------------------------------------------
# Module-level constants — computed once at import time
# ---------------------------------------------------------------------------

_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

_CRITICAL_DEPS: tuple[str, ...] = ("anthropic", "kuzu", "litellm", "rich")

_CRITICAL_PATHS: tuple[str, ...] = ("src", "tests", "pyproject.toml")

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

Status = Literal["healthy", "degraded", "unhealthy"]


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Immutable snapshot of project health at a point in time.

    Attributes:
        status: Overall health classification.
            - "healthy"   — all critical deps and paths found
            - "degraded"  — all critical deps found but ≥1 critical path missing
            - "unhealthy" — ≥1 critical dependency missing
        checks_passed: Names of checks that succeeded.
        checks_failed: Names of checks that failed.
        details: Read-only mapping of check name → diagnostic message.
            Contains internal data (absolute paths, package availability).
            Do not expose externally without sanitization.
    """

    status: Status
    checks_passed: tuple[str, ...]
    checks_failed: tuple[str, ...]
    details: Mapping[str, str]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _check_dependency(name: str) -> tuple[bool, str]:
    """Check whether a Python package is importable without executing it.

    Uses ``importlib.util.find_spec`` — no module-level code is executed.

    Args:
        name: Package/module name to probe.

    Returns:
        ``(True, "found")`` if the package is importable.
        ``(False, "not found")`` if absent or the name is malformed
            (``ModuleNotFoundError`` or ``ValueError`` from find_spec).
        ``(False, "internal error")`` for any other unexpected exception.
    """
    try:
        spec = importlib.util.find_spec(name)
        if spec is None:
            return False, "not found"
        return True, "found"
    except (ModuleNotFoundError, ValueError):
        return False, "not found"
    except Exception:
        return False, "internal error"


def _check_path(name: str) -> tuple[bool, str]:
    """Check whether a path exists relative to _PROJECT_ROOT.

    Path traversal is blocked: any ``name`` that resolves outside
    ``_PROJECT_ROOT`` returns ``(False, "path traversal blocked")`` without
    touching the filesystem.

    Args:
        name: Relative path component (e.g. ``"src"``, ``"pyproject.toml"``).

    Returns:
        ``(True, "found")`` if the path exists within the project root.
        ``(False, "not found")`` if the path does not exist.
        ``(False, "path traversal blocked")`` if ``name`` escapes project root.
        ``(False, "inaccessible")`` on ``OSError`` (permissions, symlink loops).
    """
    target = (_PROJECT_ROOT / name).resolve()
    if not target.is_relative_to(_PROJECT_ROOT):
        return False, "path traversal blocked"
    try:
        exists = target.exists()
    except OSError:
        return False, "inaccessible"
    return (True, "found") if exists else (False, "not found")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def check_health() -> HealthReport:
    """Return an immutable health report for the current environment.

    Never raises — all exceptions are caught internally and reflected in the
    ``checks_failed`` field and ``details`` mapping.

    Returns:
        A ``HealthReport`` with:
            - ``status`` set to "unhealthy" if any critical dependency is
              missing, "degraded" if all deps are present but ≥1 path is
              missing, "healthy" otherwise.
            - ``checks_passed`` / ``checks_failed`` tuples listing check names.
            - ``details`` as a read-only ``MappingProxyType`` mapping each
              check name to its diagnostic message.
    """
    passed: list[str] = []
    failed: list[str] = []
    details: dict[str, str] = {}

    # --- Dependency checks (highest priority for status) ---
    dep_failure = False
    for dep in _CRITICAL_DEPS:
        ok, msg = _check_dependency(dep)
        details[dep] = msg
        if ok:
            passed.append(dep)
        else:
            failed.append(dep)
            dep_failure = True

    # --- Path checks (only relevant when deps are healthy) ---
    for path_name in _CRITICAL_PATHS:
        ok, msg = _check_path(path_name)
        details[path_name] = msg
        if ok:
            passed.append(path_name)
        else:
            failed.append(path_name)

    # --- Determine status ---
    if dep_failure:
        status: Status = "unhealthy"
    elif any(n in failed for n in _CRITICAL_PATHS):
        status = "degraded"
    else:
        status = "healthy"

    return HealthReport(
        status=status,
        checks_passed=tuple(passed),
        checks_failed=tuple(failed),
        details=MappingProxyType(details),
    )
