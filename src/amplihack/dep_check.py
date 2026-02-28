"""Startup dependency validation for SDK adapters.

Checks that all required SDK packages are importable at startup
and fails loudly if any are missing. This prevents silent ImportError
failures deep in agent code.

Philosophy:
- Fail fast: detect missing deps before any eval or agent work
- No silent fallbacks: if a dep is missing, say so clearly
- Single responsibility: just check imports, nothing else

Public API:
    validate_sdk_deps: Check all SDK packages, raise if missing
    check_sdk_dep: Check a single SDK package, return bool
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# SDK packages that MUST be importable for agent adapters to work.
# Maps package import name -> pip install name for error messages.
SDK_DEPENDENCIES: dict[str, str] = {
    "agent_framework": "agent-framework",
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
    result = DepCheckResult()

    for import_name, pip_name in SDK_DEPENDENCIES.items():
        if check_sdk_dep(import_name):
            result.available.append(import_name)
            logger.debug("SDK dep OK: %s", import_name)
        else:
            result.missing.append(import_name)
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

    For packages requiring pre-release versions (like agent-framework),
    uses subprocess to run pip install with --prerelease=allow.

    Returns:
        DepCheckResult after installation attempt.
    """
    result = validate_sdk_deps(raise_on_missing=False)
    if result.all_ok:
        return result

    import shutil
    import subprocess

    # Try uv first, fall back to pip
    installer = shutil.which("uv")
    if installer:
        base_cmd = [installer, "pip", "install", "--prerelease=allow"]
    else:
        installer = shutil.which("pip")
        if installer:
            base_cmd = [installer, "install"]
        else:
            logger.warning("Neither uv nor pip found. Cannot auto-install SDK deps.")
            return result

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
                    pip_name, proc.returncode, proc.stderr[:200]
                )
        except Exception as e:
            logger.warning("Failed to install %s: %s", pip_name, e)

    # Re-check after install
    return validate_sdk_deps(raise_on_missing=False)


__all__ = [
    "validate_sdk_deps", "check_sdk_dep", "ensure_sdk_deps",
    "DepCheckResult", "SDK_DEPENDENCIES",
]
