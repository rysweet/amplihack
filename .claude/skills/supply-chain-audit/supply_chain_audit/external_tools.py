# File: supply_chain_audit/external_tools.py
"""External tool integration layer for supply-chain-audit.

Provides typed adapters for each optional CLI tool:
  - GhClient     (gh)     — 15s timeout
  - CraneClient  (crane)  — 20s timeout
  - SyftClient   (syft)   — 120s timeout
  - GrypeClient  (grype)  — 60s timeout
  - CosignClient (cosign) — 30s timeout

All clients:
  - Use argument arrays only (shell=False — no string interpolation of user input).
  - Enforce the documented timeout for their tool.
  - Retry up to max_retries with exponential backoff on transient failures.
  - Implement a lightweight circuit breaker: after failure_threshold consecutive
    failures the circuit opens and stays open for reset_timeout seconds.
  - Return None (never raise) on timeout or tool-not-found — callers fall back to
    offline-only mode and emit advisory messages in the report.

Usage::

    client = GhClient()
    output = client.run(["api", "repos/owner/repo/releases/latest"])
    if output is None:
        # tool unavailable or timed out — run offline only
        ...
"""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from dataclasses import dataclass

from .errors import ToolTimeoutError

# ── Timeouts (seconds) — authoritative values per contracts.md ────────────────
TOOL_TIMEOUTS: dict[str, int] = {
    "gh": 15,
    "crane": 20,
    "syft": 120,
    "grype": 60,
    "cosign": 30,
}


# ── Circuit breaker state ─────────────────────────────────────────────────────


@dataclass
class _CircuitState:
    """Mutable state for a per-tool circuit breaker."""

    failure_count: int = 0
    last_failure_time: float = 0.0
    is_open: bool = False


class _CircuitBreaker:
    """Lightweight in-process circuit breaker.

    Opens after ``failure_threshold`` consecutive failures.
    Attempts a half-open probe after ``reset_timeout`` seconds.
    """

    def __init__(self, failure_threshold: int = 3, reset_timeout: int = 60):
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._state = _CircuitState()

    @property
    def is_open(self) -> bool:
        """True when the circuit is open (tool considered unavailable)."""
        if not self._state.is_open:
            return False
        # Check if the reset window has passed (half-open probe)
        if time.time() - self._state.last_failure_time >= self._reset_timeout:
            self._state.is_open = False
            self._state.failure_count = 0
            return False
        return True

    def record_success(self) -> None:
        self._state.failure_count = 0
        self._state.is_open = False

    def record_failure(self) -> None:
        self._state.failure_count += 1
        self._state.last_failure_time = time.time()
        if self._state.failure_count >= self._failure_threshold:
            self._state.is_open = True

    def reset(self) -> None:
        """Reset to closed state (useful in tests)."""
        self._state = _CircuitState()


# ── Base tool client ──────────────────────────────────────────────────────────


class ToolClient:
    """Base class for external CLI tool adapters.

    Subclasses declare ``tool_name`` and ``default_timeout``.

    Args:
        max_retries:      Maximum number of retry attempts (default: 2, total 3 calls).
        initial_backoff:  Initial backoff in seconds between retries (default: 1).
        circuit_breaker:  Optional shared _CircuitBreaker instance.
    """

    tool_name: str = ""
    default_timeout: int = 30

    def __init__(
        self,
        max_retries: int = 2,
        initial_backoff: float = 1.0,
        circuit_breaker: _CircuitBreaker | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._initial_backoff = initial_backoff
        self._cb = circuit_breaker or _CircuitBreaker()
        self._timeout = TOOL_TIMEOUTS.get(self.tool_name, self.default_timeout)

    # ── Public API ─────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Return True if the tool binary is found in PATH."""
        return shutil.which(self.tool_name) is not None

    def run(
        self,
        args: list[str],
        timeout: int | None = None,
    ) -> str | None:
        """Run the tool with ``args``.

        Returns:
            stdout string on success, ``None`` on any failure.

        Never raises — all errors are caught and return None.
        The ``timeout`` parameter overrides the default for this call only.
        """
        if not self.is_available():
            return None

        if self._cb.is_open:
            return None

        effective_timeout = timeout if timeout is not None else self._timeout
        cmd = [self.tool_name] + list(args)

        # Safety: ensure all arguments are plain strings (no shell interpolation).
        if not all(isinstance(a, str) for a in cmd):
            raise TypeError(
                "All arguments must be plain strings — no Path objects, "
                "no f-strings with embedded commands"
            )

        backoff = self._initial_backoff
        for attempt in range(self._max_retries + 1):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=effective_timeout,
                    shell=False,  # SECURITY: never shell=True
                )
                if result.returncode == 0:
                    self._cb.record_success()
                    return result.stdout.decode("utf-8", errors="replace")

                # Non-zero exit — transient failure, eligible for retry
                # fall through to backoff+retry logic below

            except subprocess.TimeoutExpired:
                self._cb.record_failure()
                # Do NOT retry on timeout — it would exceed the documented limit
                return None

            except (OSError, FileNotFoundError):
                self._cb.record_failure()
                return None

            except subprocess.SubprocessError as exc:
                import logging

                logging.getLogger(__name__).debug("Tool execution failed: %s", exc)
                self._cb.record_failure()
                return None

            # Transient failure — wait before retry (not on last attempt)
            if attempt < self._max_retries:
                time.sleep(backoff)
                backoff *= 2

        # All retries exhausted — record one failure for the circuit breaker
        self._cb.record_failure()
        return None

    def run_or_raise(
        self,
        args: list[str],
        timeout: int | None = None,
    ) -> str:
        """Like ``run()``, but raises ``ToolTimeoutError`` on timeout.

        Use when callers must distinguish timeout from other failures.

        Raises:
            ToolTimeoutError: Tool exceeded its timeout.
        """
        if not self.is_available():
            return ""

        effective_timeout = timeout if timeout is not None else self._timeout
        cmd = [self.tool_name] + list(args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=effective_timeout,
                shell=False,
            )
            if result.returncode == 0:
                return result.stdout.decode("utf-8", errors="replace")
            return ""
        except subprocess.TimeoutExpired:
            raise ToolTimeoutError(self.tool_name, effective_timeout)
        except (OSError, FileNotFoundError):
            return ""


# ── Concrete adapters ─────────────────────────────────────────────────────────


class GhClient(ToolClient):
    """Adapter for the GitHub CLI (``gh``).

    Timeout: 15 seconds (per contracts.md §Tool Timeouts).
    """

    tool_name = "gh"
    default_timeout = 15

    def resolve_tag_to_sha(self, owner: str, repo: str, tag: str) -> str | None:
        """Resolve a git tag to a 40-char commit SHA via the GitHub API.

        Returns the SHA string or None if resolution fails.
        """
        for part in (owner, repo, tag):
            if not part or any(c in part for c in ("'", '"', ";", "|", "&", "$", "\x00")):
                return None

        output = self.run(["api", f"repos/{owner}/{repo}/git/refs/tags/{tag}"])
        if not output:
            return None

        sha_match = re.search(r'"sha"\s*:\s*"([0-9a-f]{40})"', output)
        return sha_match.group(1) if sha_match else None


class CraneClient(ToolClient):
    """Adapter for ``crane`` (Google container tool).

    Timeout: 20 seconds (per contracts.md §Tool Timeouts).
    """

    tool_name = "crane"
    default_timeout = 20

    def resolve_digest(self, image_ref: str) -> str | None:
        """Return the sha256 digest for an image reference.

        Returns a string like ``sha256:abc123...`` (64 hex chars) or None.
        """
        if not image_ref or "\x00" in image_ref:
            return None

        output = self.run(["digest", image_ref])
        if not output:
            return None

        digest = output.strip()
        if re.match(r"^sha256:[a-f0-9]{64}$", digest):
            return digest
        return None


class SyftClient(ToolClient):
    """Adapter for ``syft`` (SBOM generator).

    Timeout: 120 seconds (per contracts.md §Tool Timeouts).
    """

    tool_name = "syft"
    default_timeout = 120

    FORMATS = frozenset({"spdx-json", "cyclonedx-json", "syft-json", "table"})

    def generate_sbom(
        self,
        path: str,
        output_format: str = "spdx-json",
    ) -> str | None:
        """Generate an SBOM for a directory or image.

        Args:
            path:          Path to directory or image reference.
            output_format: Output format (default: ``spdx-json``).

        Returns:
            SBOM content string or None on failure.
        """
        if output_format not in self.FORMATS:
            return None
        if not path or "\x00" in path:
            return None

        return self.run(["scan", path, "-o", output_format])


class GrypeClient(ToolClient):
    """Adapter for ``grype`` (vulnerability scanner).

    Timeout: 60 seconds (per contracts.md §Tool Timeouts).
    """

    tool_name = "grype"
    default_timeout = 60

    def scan_sbom(self, sbom_path: str) -> str | None:
        """Scan an SBOM file for known CVEs. Returns JSON output or None."""
        if not sbom_path or "\x00" in sbom_path:
            return None
        return self.run(["sbom:" + sbom_path, "-o", "json"])

    def scan_path(self, path: str) -> str | None:
        """Scan a directory for vulnerabilities. Returns JSON output or None."""
        if not path or "\x00" in path:
            return None
        return self.run([path, "-o", "json"])


class CosignClient(ToolClient):
    """Adapter for ``cosign`` (image signing and attestation).

    Timeout: 30 seconds.
    """

    tool_name = "cosign"
    default_timeout = 30

    def verify_signature(self, image_ref: str) -> bool:
        """Return True if the image has a valid cosign signature."""
        if not image_ref or "\x00" in image_ref:
            return False
        output = self.run(["verify", image_ref])
        return output is not None

    def attest(
        self,
        image_ref: str,
        predicate_path: str,
        predicate_type: str = "https://slsa.dev/provenance/v1",
    ) -> str | None:
        """Create a cosign attestation for an image."""
        if not image_ref or not predicate_path:
            return None
        if "\x00" in image_ref or "\x00" in predicate_path:
            return None

        return self.run(
            [
                "attest",
                "--predicate",
                predicate_path,
                "--type",
                predicate_type,
                image_ref,
            ]
        )


# ── Convenience factory ───────────────────────────────────────────────────────


def get_tool_clients() -> dict[str, ToolClient]:
    """Return a dict of pre-configured tool clients keyed by tool name."""
    return {
        "gh": GhClient(),
        "crane": CraneClient(),
        "syft": SyftClient(),
        "grype": GrypeClient(),
        "cosign": CosignClient(),
    }


def check_tool_availability() -> dict[str, str]:
    """Check availability of all optional external tools.

    Returns a dict mapping tool name to status string.
    Status: ``"available (timeout: Xs)"`` or ``"unavailable (not found in PATH)"``.
    """
    clients = get_tool_clients()
    status: dict[str, str] = {}
    for name, client in clients.items():
        timeout = TOOL_TIMEOUTS.get(name, client.default_timeout)
        if client.is_available():
            status[name] = f"available (timeout: {timeout}s)"
        else:
            status[name] = f"unavailable (not found in PATH; timeout would be {timeout}s)"
    return status
