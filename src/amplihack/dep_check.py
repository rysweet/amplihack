"""Startup dependency validation for SDK adapters.

Checks that all required SDK packages are importable at startup
and auto-installs any that are missing. This prevents silent ImportError
failures deep in agent code.

Philosophy:
- Fail fast: detect missing deps before any eval or agent work
- Auto-heal: install missing deps targeting the running interpreter
- Single responsibility: just check imports and install if needed

Public API:
    validate_sdk_deps: Check all SDK packages, raise if missing
    check_sdk_dep: Check a single SDK package, return bool
    ensure_sdk_deps: Check and auto-install missing SDK packages
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# SDK packages that MUST be importable for agent adapters to work.
# Maps package import name -> pip install name for error messages.
SDK_DEPENDENCIES: dict[str, str] = {
    "agent_framework": "agent-framework-core",
}


@dataclass
class DepCheckResult:
    """Result of a dependency check."""

    available: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return len(self.missing) == 0


def check_sdk_dep(import_name: str) -> bool:
    """Check if a single SDK package is importable.

    Args:
        import_name: Python import name (e.g. "agent_framework")

    Returns:
        True if the package can be imported, False otherwise.
    """
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def _collect_dep_status() -> DepCheckResult:
    """Check all SDK deps without logging warnings.

    Used internally before auto-install to avoid warning about deps
    that are about to be installed.
    """
    result = DepCheckResult()
    for import_name in SDK_DEPENDENCIES:
        if check_sdk_dep(import_name):
            result.available.append(import_name)
        else:
            result.missing.append(import_name)
    return result


def validate_sdk_deps(raise_on_missing: bool = True) -> DepCheckResult:
    """Validate that all required SDK dependencies are importable.

    Checks every entry in SDK_DEPENDENCIES. If any are missing and
    raise_on_missing is True, raises ImportError with clear install
    instructions.

    Args:
        raise_on_missing: If True, raise ImportError when deps are missing.
            If False, just return the result for inspection.

    Returns:
        DepCheckResult with available and missing package lists.

    Raises:
        ImportError: When raise_on_missing is True and deps are missing.
    """
    result = _collect_dep_status()

    for import_name in result.missing:
        pip_name = SDK_DEPENDENCIES[import_name]
        logger.warning("SDK dep MISSING: %s (install: pip install %s)", import_name, pip_name)

    if result.missing and raise_on_missing:
        install_cmds = [f"  pip install {SDK_DEPENDENCIES[m]}" for m in result.missing]
        raise ImportError(
            "Required SDK dependencies are missing. Install them:\n"
            + "\n".join(install_cmds)
            + "\n\nOr reinstall amplihack: pip install amplihack"
        )

    return result


def ensure_sdk_deps() -> DepCheckResult:
    """Check SDK deps and auto-install any that are missing.

    For packages requiring pre-release versions (like agent-framework-core),
    uses subprocess to run pip/uv install with pre-release flags.

    Uses ``--python sys.executable`` with uv to ensure packages are
    installed into the *running* Python environment (critical when
    amplihack is launched via uvx, whose ephemeral venv differs from the
    project .venv that bare ``uv pip install`` targets).

    Returns:
        DepCheckResult after installation attempt.
    """
    import sys

    # Quiet check first — no warnings for deps we're about to install
    result = _collect_dep_status()
    if result.all_ok:
        return result

    import shutil
    import subprocess

    # Try uv first, fall back to pip.
    # Always target the *running* interpreter so the package lands in the
    # correct site-packages (not the project .venv when running under uvx).
    installer = shutil.which("uv")
    if installer:
        base_cmd = [
            installer,
            "pip",
            "install",
            "--python",
            sys.executable,
            "--prerelease=allow",
        ]
    else:
        installer = shutil.which("pip")
        if installer:
            base_cmd = [installer, "install", "--pre"]
        else:
            install_cmds = [f"  pip install {SDK_DEPENDENCIES[m]}" for m in result.missing]
            raise ImportError(
                "Required SDK dependencies are missing and no installer (uv/pip) found.\n"
                "Install them manually:\n"
                + "\n".join(install_cmds)
            )

    for import_name in result.missing:
        pip_name = SDK_DEPENDENCIES[import_name]
        cmd = base_cmd + [pip_name]
        logger.info("Auto-installing SDK dep: %s", pip_name)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0:
                logger.info("Installed %s successfully", pip_name)
            else:
                logger.warning(
                    "Failed to install %s (exit %d): %s",
                    pip_name,
                    proc.returncode,
                    proc.stderr[:200],
                )
        except Exception as e:
            logger.warning("Failed to install %s: %s", pip_name, e)

    # Invalidate import caches so Python picks up newly-installed packages
    # without requiring a process restart.
    importlib.invalidate_caches()

    # Re-check after install — if still missing, that's a real failure
    return validate_sdk_deps(raise_on_missing=True)


__all__ = [
    "validate_sdk_deps",
    "check_sdk_dep",
    "ensure_sdk_deps",
    "DepCheckResult",
    "SDK_DEPENDENCIES",
]
