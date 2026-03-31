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
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security: Input validation
# ---------------------------------------------------------------------------

# Allowlist pattern for Python import names (e.g. "agent_framework", "os.path").
# Rejects shell metacharacters and path traversal sequences before any subprocess use.
_VALID_IMPORT_NAME: re.Pattern[str] = re.compile(
    r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)*$"
)

# Allowlist pattern for pip package specs following PEP 508 (name + optional version).
# Allows extras (e.g. "pkg[extra]") and version specifiers (e.g. "pkg>=1.0.0rc1").
_VALID_PKG_SPEC: re.Pattern[str] = re.compile(
    r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?"  # distribution name
    r"(\[[\w,\s]+\])?"  # optional extras
    r"([\s]*(==|!=|<=|>=|<|>|~=)\s*[\w.*+!]+)*$"  # optional version specifier(s)
)


def _validate_import_name(import_name: str) -> None:
    """Validate a Python import name before use.

    Raises:
        ValueError: If the name contains characters outside the allowed set.
    """
    if not _VALID_IMPORT_NAME.match(import_name):
        raise ValueError(
            f"Invalid Python import name: {import_name!r}. "
            "Only alphanumeric characters, underscores, and dots are permitted."
        )


def _validate_pkg_spec(pkg_spec: str) -> None:
    """Validate a pip package specifier before passing to subprocess.

    Raises:
        ValueError: If the specifier is not a valid PEP 508 name/version string.
    """
    if not _VALID_PKG_SPEC.match(pkg_spec.strip()):
        raise ValueError(
            f"Invalid pip package specifier: {pkg_spec!r}. "
            "Must follow PEP 508 (e.g. 'package>=1.0.0')."
        )


def _sanitize_pip_output(text: str) -> str:
    """Strip potentially sensitive data from pip stderr before logging.

    Removes embedded credentials (``user:token@host`` URLs) and common
    secret-bearing key=value patterns so that internal registry tokens do
    not appear in log files or CI/CD stdout captures.

    Args:
        text: Raw pip stderr/stdout text (already truncated by caller).

    Returns:
        Sanitized text safe for INFO/WARNING log output.
    """
    # Remove URLs with embedded credentials (e.g. https://user:pass@host/...)  # pragma: allowlist secret
    text = re.sub(r"https?://[^@\s]+@[^\s]+", "[REDACTED_URL]", text)  # pragma: allowlist secret
    # Remove common token/secret key=value patterns
    text = re.sub(
        r"(?i)(token|key|secret|password|auth)[=:\s]+\S+", r"\1=[REDACTED]", text
    )  # pragma: allowlist secret
    return text


# ---------------------------------------------------------------------------
# SDK dependency registry
# ---------------------------------------------------------------------------

# SDK packages that MUST be importable for agent adapters to work.
# Maps package import name -> pinned pip install specifier.
# SECURITY: Always pin to a minimum version to prevent supply-chain attacks
# via newly-published malicious versions of the same package name.
SDK_DEPENDENCIES: dict[str, str] = {
    "agent_framework": "agent-framework-core>=1.0.0rc1",
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

    Raises:
        ValueError: If ``import_name`` fails the allowlist validation.
    """
    _validate_import_name(import_name)
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def _collect_dep_status() -> DepCheckResult:
    """Quietly check all SDK dependencies without any output.

    This is a pre-install status check that produces no stderr output.
    Use this to inspect which deps are available before attempting installation.

    Returns:
        DepCheckResult with available and missing package lists.
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

    For packages requiring pre-release versions (like agent-framework-core),
    uses subprocess to run pip/uv install with pre-release flags.

    Uses ``--python sys.executable`` with uv to ensure packages are
    installed into the *running* Python environment (critical when
    amplihack is launched via uvx, whose ephemeral venv differs from the
    project .venv that bare ``uv pip install`` targets).

    Returns:
        DepCheckResult after installation attempt.
    """
    result = validate_sdk_deps(raise_on_missing=False)
    if result.all_ok:
        return result

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
            logger.warning("Neither uv nor pip found. Cannot auto-install SDK deps.")
            return result

    for import_name in result.missing:
        pip_spec = SDK_DEPENDENCIES[import_name]
        # Security: validate the spec before handing it to subprocess.
        # SDK_DEPENDENCIES values are hardcoded, but this guard prevents
        # regressions if the dict is ever populated from external input.
        try:
            _validate_pkg_spec(pip_spec)
        except ValueError as ve:
            logger.error("Skipping auto-install of %r: %s", import_name, ve)
            continue
        cmd = base_cmd + [pip_spec]
        logger.info("Auto-installing SDK dep: %s", pip_spec)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0:
                logger.info("Installed %s successfully", pip_spec)
            else:
                # Sanitize pip stderr before logging to prevent credential leakage.
                safe_stderr = _sanitize_pip_output(proc.stderr[:500])
                logger.warning(
                    "Failed to install %s (exit %d): %s",
                    pip_spec,
                    proc.returncode,
                    safe_stderr,
                )
        except Exception as e:
            raise RuntimeError(f"Failed to install {pip_spec}: {e}") from e

    # Invalidate import caches so Python picks up newly-installed packages
    # without requiring a process restart.
    importlib.invalidate_caches()

    # Re-check after install
    return validate_sdk_deps(raise_on_missing=False)


__all__ = [
    "validate_sdk_deps",
    "check_sdk_dep",
    "ensure_sdk_deps",
    "DepCheckResult",
    "SDK_DEPENDENCIES",
]
