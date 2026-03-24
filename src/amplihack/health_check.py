"""
health_check — system health checking for the amplihack installation.

Brick philosophy:
  - Single responsibility: health checking only
  - Clear public contract: check_health() -> HealthReport
  - Zero runtime dependencies (stdlib only)
  - Immutable result: HealthReport is frozen
  - Never raises: all exceptions are captured as failed checks

Public API:
    from amplihack.health_check import check_health, HealthReport

    report = check_health()
    # report.status         → 'healthy' | 'degraded' | 'unhealthy'
    # report.checks_passed  → list of check names that succeeded
    # report.checks_failed  → list of check names that failed
    # report.details        → {check_name: human-readable message}

Status classification (reduction rule):
    healthy   = all checks pass
    degraded  = only path checks fail (deps all present)
    unhealthy = any dependency check fails

Structural assumption:
    _project_root() anchors to __file__.parent.parent.parent.
    This assumes the module lives at src/amplihack/health_check.py
    relative to the project root. Relocating the module requires
    updating _project_root() accordingly.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration: dependencies and paths to check
# ---------------------------------------------------------------------------

_CRITICAL_DEPS: tuple[str, ...] = (
    "kuzu",
    "rich",
    "anthropic",
)

_CRITICAL_PATHS: tuple[str, ...] = (
    "amplifier-bundle",
    "recipes",
    "workflows",
)


# ---------------------------------------------------------------------------
# Public contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HealthReport:
    """Immutable result of a health check run.

    Fields:
        status:         'healthy' | 'degraded' | 'unhealthy'
        checks_passed:  list of check names that succeeded
        checks_failed:  list of check names that failed
        details:        mapping of check name → human-readable message
    """

    status: str
    checks_passed: list
    checks_failed: list
    details: dict


def check_health() -> HealthReport:
    """Run all system health checks and return a HealthReport.

    This function never raises. All exceptions from sub-checks are captured
    and recorded as failed checks in the returned HealthReport.

    Returns:
        HealthReport with status, checks_passed, checks_failed, and details.
    """
    checks_passed: list[str] = []
    checks_failed: list[str] = []
    details: dict[str, str] = {}
    dep_failed = False

    # Dependency checks
    for pkg in _CRITICAL_DEPS:
        name = f"dep:{pkg}"
        ok, msg = _check_dependency(pkg)
        details[name] = msg
        if ok:
            checks_passed.append(name)
        else:
            checks_failed.append(name)
            dep_failed = True

    # Path checks
    try:
        root = _project_root()
    except Exception:
        root = None

    for path_name in _CRITICAL_PATHS:
        name = f"path:{path_name}"
        if root is None:
            ok, msg = False, "internal error"
        else:
            ok, msg = _check_path(root / path_name)
        details[name] = msg
        if ok:
            checks_passed.append(name)
        else:
            checks_failed.append(name)

    # Status reduction: unhealthy > degraded > healthy
    if dep_failed:
        status = "unhealthy"
    elif checks_failed:
        status = "degraded"
    else:
        status = "healthy"

    return HealthReport(
        status=status,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
        details=details,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    """Return the project root directory.

    Structural assumption: this module lives at src/amplihack/health_check.py,
    so the root is three levels up from __file__.

    Extracted as a function for testability.
    """
    return Path(__file__).resolve().parent.parent.parent


def _check_dependency(pkg: str) -> tuple[bool, str]:
    """Check whether a Python package is importable without executing it.

    Uses importlib.util.find_spec so no package code runs — prevents
    import-time side effects from affecting the health check.

    Security: unknown exceptions produce a sanitized 'internal error'
    message. Raw exception strings are never returned (prevents leaking
    internal implementation details into HealthReport.details).

    Args:
        pkg: Python package name (e.g. 'kuzu', 'rich').

    Returns:
        (True, 'found') if importable, (False, safe_message) otherwise.
    """
    try:
        spec = importlib.util.find_spec(pkg)
    except (ModuleNotFoundError, ImportError, AttributeError, ValueError):
        return False, "not found"
    except Exception:
        return False, "internal error"

    if spec is None:
        return False, "not found"

    return True, "found"


def _check_path(path: Path) -> tuple[bool, str]:
    """Check whether a filesystem path exists.

    Security: the full absolute path is intentionally withheld from the
    returned message to prevent filesystem layout disclosure if
    HealthReport.details is ever forwarded externally.

    Args:
        path: Absolute Path to check.

    Returns:
        (True, 'ok') if the path exists, (False, 'not found') otherwise.
    """
    try:
        exists = path.exists()
    except Exception:
        return False, "internal error"

    if exists:
        return True, "ok"
    return False, "not found"
