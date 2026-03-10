"""
Subprocess bridge to the amplihack-xpia-defender Rust CLI binary.

Calls the compiled `xpia-defend` binary via subprocess, parsing JSON output.
NO FALLBACKS: if the binary is missing or returns non-JSON, we raise an error.
Fail-closed: subprocess errors → blocked result, never silently allow.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Binary name — must be on PATH or at a known location
BINARY_NAME = "xpia-defend"

# Exit codes from the Rust binary
EXIT_VALID = 0
EXIT_BLOCKED = 1
EXIT_ERROR = 2

# Timeout for subprocess calls (seconds)
SUBPROCESS_TIMEOUT = 30


class RustXPIAError(Exception):
    """Raised when the Rust XPIA binary fails or is unavailable."""


@dataclass
class RustValidationResult:
    """Parsed result from the Rust CLI binary."""

    is_valid: bool
    risk_level: str
    threats: list[dict[str, Any]]
    recommendations: list[str]
    metadata: dict[str, Any]
    timestamp: str
    raw_json: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def should_block(self) -> bool:
        return self.risk_level in ("high", "critical")

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> RustValidationResult:
        return cls(
            is_valid=data.get("is_valid", False),
            risk_level=data.get("risk_level", "critical"),
            threats=data.get("threats", []),
            recommendations=data.get("recommendations", []),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            raw_json=data,
        )

    @classmethod
    def blocked(cls, reason: str) -> RustValidationResult:
        """Fail-closed: create a blocked result for error conditions."""
        return cls(
            is_valid=False,
            risk_level="critical",
            threats=[
                {
                    "threat_type": "injection",
                    "severity": "critical",
                    "description": reason,
                    "location": None,
                    "mitigation": "Review and retry",
                }
            ],
            recommendations=["Content blocked due to validation error"],
            metadata={"error": True, "reason": reason},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


def find_binary(*, auto_install: bool = False) -> str:
    """Find the xpia-defend binary.

    Search order:
    1. System PATH
    2. ~/.cargo/bin/
    3. ~/.amplihack/bin/ (managed install location)
    4. /usr/local/bin/
    5. If not found and auto_install=True, download from GitHub releases

    Raises RustXPIAError if not found and auto-install disabled or fails.
    """
    # Check PATH first
    path = shutil.which(BINARY_NAME)
    if path:
        return path

    # Check common install locations
    candidates = [
        Path.home() / ".cargo" / "bin" / BINARY_NAME,
        Path.home() / ".amplihack" / "bin" / BINARY_NAME,
        Path("/usr/local/bin") / BINARY_NAME,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    # Auto-install from GitHub releases
    if auto_install:
        try:
            from amplihack.security.xpia_install import ensure_xpia_binary

            installed = ensure_xpia_binary()
            return str(installed)
        except Exception as e:
            logger.warning("Auto-install of xpia-defend failed: %s", e)

    msg = (
        f"XPIA defender binary '{BINARY_NAME}' not found. "
        f"Install with: pip install amplihack (auto-installs), "
        f"or cargo install --features cli --path <amplihack-xpia-defender>"
    )
    raise RustXPIAError(msg)


def _run_command(args: list[str], stdin_data: str | None = None) -> dict[str, Any]:
    """Run xpia-defend with args, return parsed JSON. Fail-closed on any error."""
    binary = find_binary()

    try:
        result = subprocess.run(
            [binary, *args],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
            input=stdin_data,
        )
    except subprocess.TimeoutExpired as e:
        raise RustXPIAError(f"XPIA binary timed out after {SUBPROCESS_TIMEOUT}s") from e
    except FileNotFoundError as e:
        raise RustXPIAError(f"XPIA binary not found at {binary}") from e
    except OSError as e:
        raise RustXPIAError(f"Failed to execute XPIA binary: {e}") from e

    # Exit 2 = internal error in the Rust binary — always fail-closed
    if result.returncode == EXIT_ERROR:
        raise RustXPIAError(
            f"XPIA binary internal error (exit {result.returncode}). "
            f"stderr: {result.stderr}"
        )

    if not result.stdout.strip():
        raise RustXPIAError(
            f"XPIA binary produced no output (exit {result.returncode}). "
            f"stderr: {result.stderr}"
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RustXPIAError(
            f"XPIA binary produced invalid JSON: {e}. "
            f"stdout: {result.stdout[:200]}"
        ) from e


def validate_content(
    content: str,
    content_type: str = "user-input",
    security_level: str = "medium",
    source: str = "python",
) -> RustValidationResult:
    """Validate content for injection attacks via Rust CLI.

    Fail-closed: any error → blocked result.
    """
    try:
        args = [
            "validate-content",
            "--content-type", content_type,
            "--security-level", security_level,
            "--source", source,
        ]
        # Use stdin for content to avoid shell injection via args
        data = _run_command(args, stdin_data=content)
        return RustValidationResult.from_json(data)
    except RustXPIAError as e:
        logger.error("XPIA validate_content failed (fail-closed): %s", e)
        return RustValidationResult.blocked(str(e))


def validate_bash_command(
    command: str,
    security_level: str = "medium",
    source: str = "python",
) -> RustValidationResult:
    """Validate a bash command via Rust CLI.

    Fail-closed: any error → blocked result.
    """
    try:
        args = [
            "validate-bash",
            "--command", command,
            "--security-level", security_level,
            "--source", source,
        ]
        data = _run_command(args)
        return RustValidationResult.from_json(data)
    except RustXPIAError as e:
        logger.error("XPIA validate_bash failed (fail-closed): %s", e)
        return RustValidationResult.blocked(str(e))


def validate_webfetch_request(
    url: str,
    prompt: str,
    security_level: str = "medium",
    source: str = "python",
) -> RustValidationResult:
    """Validate a web fetch request via Rust CLI.

    Fail-closed: any error → blocked result.
    """
    try:
        args = [
            "validate-webfetch",
            "--url", url,
            "--prompt", prompt,
            "--security-level", security_level,
            "--source", source,
        ]
        data = _run_command(args)
        return RustValidationResult.from_json(data)
    except RustXPIAError as e:
        logger.error("XPIA validate_webfetch failed (fail-closed): %s", e)
        return RustValidationResult.blocked(str(e))


def validate_agent_communication(
    source_agent: str,
    target_agent: str,
    message: str,
    security_level: str = "medium",
) -> RustValidationResult:
    """Validate agent-to-agent communication via Rust CLI.

    Fail-closed: any error → blocked result.
    """
    try:
        args = [
            "validate-agent",
            "--source-agent", source_agent,
            "--target-agent", target_agent,
            "--security-level", security_level,
        ]
        data = _run_command(args, stdin_data=message)
        return RustValidationResult.from_json(data)
    except RustXPIAError as e:
        logger.error("XPIA validate_agent failed (fail-closed): %s", e)
        return RustValidationResult.blocked(str(e))


def health_check(settings_path: str | None = None) -> dict[str, Any]:
    """Run XPIA health check via Rust CLI.

    Unlike validation functions, health check raises on failure
    (it's diagnostic, not a security gate).
    """
    args = ["health"]
    if settings_path:
        args.extend(["--settings-path", settings_path])
    return _run_command(args)


def list_patterns() -> list[dict[str, Any]]:
    """List all registered attack patterns."""
    result = _run_command(["patterns"])
    if isinstance(result, list):
        return result
    raise RustXPIAError(f"Expected array from 'patterns', got {type(result).__name__}")


def get_config(security_level: str = "medium") -> dict[str, Any]:
    """Get security configuration."""
    return _run_command(["config", "--security-level", security_level])


def is_available() -> bool:
    """Check if the Rust XPIA binary is available."""
    try:
        find_binary()
        return True
    except RustXPIAError:
        return False
