"""
Unit tests — External Tool Integration Layer
Tests for supply_chain_audit.external_tools module.
"""

import subprocess
import time
from unittest.mock import MagicMock, patch

import pytest
from supply_chain_audit.errors import ToolTimeoutError
from supply_chain_audit.external_tools import (
    TOOL_TIMEOUTS,
    CosignClient,
    CraneClient,
    GhClient,
    GrypeClient,
    SyftClient,
    _CircuitBreaker,
    check_tool_availability,
    get_tool_clients,
)

# ── TOOL_TIMEOUTS constants ────────────────────────────────────────────────────


class TestToolTimeoutConstants:
    """Documented timeout values must be present and correct."""

    def test_gh_timeout_is_15s(self):
        assert TOOL_TIMEOUTS["gh"] == 15

    def test_crane_timeout_is_20s(self):
        assert TOOL_TIMEOUTS["crane"] == 20

    def test_syft_timeout_is_120s(self):
        assert TOOL_TIMEOUTS["syft"] == 120

    def test_grype_timeout_is_60s(self):
        assert TOOL_TIMEOUTS["grype"] == 60

    def test_cosign_timeout_is_30s(self):
        assert TOOL_TIMEOUTS["cosign"] == 30

    def test_all_five_tools_have_timeouts(self):
        for tool in ("gh", "crane", "syft", "grype", "cosign"):
            assert tool in TOOL_TIMEOUTS, f"Missing timeout for '{tool}'"


# ── Circuit breaker ────────────────────────────────────────────────────────────


class TestCircuitBreaker:
    """Circuit breaker opens after threshold failures, resets after timeout."""

    def test_starts_closed(self):
        cb = _CircuitBreaker()
        assert not cb.is_open

    def test_opens_after_failure_threshold(self):
        cb = _CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.is_open

    def test_does_not_open_before_threshold(self):
        cb = _CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open

    def test_resets_on_success(self):
        cb = _CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open
        cb.record_success()
        assert not cb.is_open

    def test_half_open_probe_after_reset_timeout(self):
        cb = _CircuitBreaker(failure_threshold=1, reset_timeout=30)
        cb.record_failure()
        assert cb.is_open
        # Force last_failure_time far enough into the past to exceed reset_timeout
        cb._state.last_failure_time = time.time() - 31
        assert not cb.is_open  # half-open probe allowed after reset window

    def test_manual_reset(self):
        cb = _CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.is_open
        cb.reset()
        assert not cb.is_open


# ── ToolClient base class ──────────────────────────────────────────────────────


class TestToolClientAvailability:
    """is_available() delegates to shutil.which."""

    def test_available_when_which_returns_path(self):
        client = GhClient()
        with patch("shutil.which", return_value="/usr/bin/gh"):
            assert client.is_available() is True

    def test_unavailable_when_which_returns_none(self):
        client = GhClient()
        with patch("shutil.which", return_value=None):
            assert client.is_available() is False


class TestToolClientRun:
    """run() returns stdout on success, None on any failure."""

    def _make_completed(self, returncode=0, stdout=b"ok\n"):
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = returncode
        result.stdout = stdout
        return result

    def test_returns_stdout_on_success(self):
        client = GhClient()
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("subprocess.run", return_value=self._make_completed(0, b"output\n")),
        ):
            assert client.run(["version"]) == "output\n"

    def test_returns_none_when_tool_unavailable(self):
        client = GhClient()
        with patch("shutil.which", return_value=None):
            assert client.run(["version"]) is None

    def test_returns_none_on_timeout(self):
        client = GhClient()
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gh", 15)),
        ):
            assert client.run(["version"]) is None

    def test_returns_none_on_nonzero_exit(self):
        client = GhClient()
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("subprocess.run", return_value=self._make_completed(1, b"")),
        ):
            assert client.run(["bad-command"]) is None

    def test_returns_none_on_file_not_found(self):
        client = GhClient()
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("subprocess.run", side_effect=FileNotFoundError),
        ):
            assert client.run(["version"]) is None

    def test_shell_is_never_true(self):
        """subprocess.run must always be called with shell=False."""
        calls = []

        def capture_run(*args, **kwargs):
            calls.append(kwargs.get("shell", "NOT_SET"))
            return self._make_completed()

        client = GhClient()
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("subprocess.run", side_effect=capture_run),
        ):
            client.run(["version"])

        assert calls, "subprocess.run was not called"
        for shell_arg in calls:
            assert shell_arg is False or shell_arg == "NOT_SET" or not shell_arg, (
                "shell=True detected — security violation"
            )

    def test_circuit_breaker_blocks_after_threshold(self):
        client = GhClient()
        cb = _CircuitBreaker(failure_threshold=2)
        client._cb = cb

        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("subprocess.run", side_effect=FileNotFoundError),
        ):
            client.run(["v1"])
            client.run(["v2"])

        # Circuit should now be open — further calls blocked
        assert cb.is_open
        call_count = 0

        def counting_run(*a, **k):
            nonlocal call_count
            call_count += 1
            return self._make_completed()

        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("subprocess.run", side_effect=counting_run),
        ):
            result = client.run(["v3"])

        assert result is None  # blocked by circuit
        assert call_count == 0  # subprocess.run never called


class TestToolClientRunOrRaise:
    """run_or_raise() raises ToolTimeoutError on timeout."""

    def test_raises_tool_timeout_error_on_timeout(self):
        client = GhClient()
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gh", 15)),
        ):
            with pytest.raises(ToolTimeoutError) as exc_info:
                client.run_or_raise(["version"])
            assert exc_info.value.error_code == "TOOL_TIMEOUT"

    def test_returns_empty_string_when_unavailable(self):
        client = GhClient()
        with patch("shutil.which", return_value=None):
            assert client.run_or_raise(["version"]) == ""

    def test_returns_stdout_on_success(self):
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = 0
        result.stdout = b"v2.40.0\n"
        client = GhClient()
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("subprocess.run", return_value=result),
        ):
            assert client.run_or_raise(["version"]) == "v2.40.0\n"


# ── GhClient ──────────────────────────────────────────────────────────────────


class TestGhClient:
    """GhClient-specific adapter methods."""

    def test_tool_name(self):
        assert GhClient.tool_name == "gh"

    def test_default_timeout_matches_constant(self):
        assert GhClient.default_timeout == TOOL_TIMEOUTS["gh"]

    def test_resolve_tag_to_sha_returns_sha(self):
        json_response = b'{"ref":"refs/tags/v4","object":{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","type":"commit"}}'
        result = MagicMock(returncode=0, stdout=json_response)
        client = GhClient()
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("subprocess.run", return_value=result),
        ):
            sha = client.resolve_tag_to_sha("actions", "checkout", "v4")
        assert sha == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    def test_resolve_tag_to_sha_rejects_null_byte(self):
        client = GhClient()
        assert client.resolve_tag_to_sha("owner", "repo", "tag\x00") is None

    def test_resolve_tag_to_sha_rejects_shell_metachar(self):
        client = GhClient()
        for bad in ("tag;rm -rf /", "tag|cat", "tag$HOME"):
            assert client.resolve_tag_to_sha("owner", "repo", bad) is None

    def test_resolve_tag_to_sha_returns_none_on_failure(self):
        client = GhClient()
        with (
            patch("shutil.which", return_value="/usr/bin/gh"),
            patch("subprocess.run", side_effect=FileNotFoundError),
        ):
            assert client.resolve_tag_to_sha("owner", "repo", "v1") is None


# ── CraneClient ───────────────────────────────────────────────────────────────


class TestCraneClient:
    """CraneClient-specific adapter methods."""

    def test_tool_name(self):
        assert CraneClient.tool_name == "crane"

    def test_default_timeout_matches_constant(self):
        assert CraneClient.default_timeout == TOOL_TIMEOUTS["crane"]

    def test_resolve_digest_returns_valid_digest(self):
        digest_bytes = b"sha256:" + b"a" * 64 + b"\n"
        result = MagicMock(returncode=0, stdout=digest_bytes)
        client = CraneClient()
        with (
            patch("shutil.which", return_value="/usr/bin/crane"),
            patch("subprocess.run", return_value=result),
        ):
            digest = client.resolve_digest("ubuntu:22.04")
        assert digest == "sha256:" + "a" * 64

    def test_resolve_digest_rejects_null_byte(self):
        client = CraneClient()
        assert client.resolve_digest("ubuntu\x00:22.04") is None

    def test_resolve_digest_returns_none_for_invalid_format(self):
        result = MagicMock(returncode=0, stdout=b"not-a-digest\n")
        client = CraneClient()
        with (
            patch("shutil.which", return_value="/usr/bin/crane"),
            patch("subprocess.run", return_value=result),
        ):
            assert client.resolve_digest("ubuntu:22.04") is None

    def test_resolve_digest_returns_none_on_failure(self):
        client = CraneClient()
        with patch("shutil.which", return_value=None):
            assert client.resolve_digest("ubuntu:22.04") is None


# ── SyftClient ────────────────────────────────────────────────────────────────


class TestSyftClient:
    """SyftClient-specific adapter methods."""

    def test_tool_name(self):
        assert SyftClient.tool_name == "syft"

    def test_default_timeout_matches_constant(self):
        assert SyftClient.default_timeout == TOOL_TIMEOUTS["syft"]

    def test_generate_sbom_calls_correct_args(self):
        calls = []

        def capture_run(cmd, **kwargs):
            calls.append(cmd)
            return MagicMock(returncode=0, stdout=b'{"bomFormat":"SPDX"}')

        client = SyftClient()
        with (
            patch("shutil.which", return_value="/usr/bin/syft"),
            patch("subprocess.run", side_effect=capture_run),
        ):
            client.generate_sbom(".", output_format="spdx-json")

        assert calls
        assert calls[0] == ["syft", "scan", ".", "-o", "spdx-json"]

    def test_generate_sbom_rejects_invalid_format(self):
        client = SyftClient()
        assert client.generate_sbom(".", output_format="xml") is None

    def test_generate_sbom_rejects_null_byte_in_path(self):
        client = SyftClient()
        assert client.generate_sbom("path\x00", output_format="spdx-json") is None


# ── GrypeClient ───────────────────────────────────────────────────────────────


class TestGrypeClient:
    """GrypeClient-specific adapter methods."""

    def test_tool_name(self):
        assert GrypeClient.tool_name == "grype"

    def test_default_timeout_matches_constant(self):
        assert GrypeClient.default_timeout == TOOL_TIMEOUTS["grype"]

    def test_scan_sbom_builds_correct_args(self):
        calls = []

        def capture_run(cmd, **kwargs):
            calls.append(cmd)
            return MagicMock(returncode=0, stdout=b'{"matches":[]}')

        client = GrypeClient()
        with (
            patch("shutil.which", return_value="/usr/bin/grype"),
            patch("subprocess.run", side_effect=capture_run),
        ):
            client.scan_sbom("sbom.spdx.json")

        assert calls[0] == ["grype", "sbom:sbom.spdx.json", "-o", "json"]

    def test_scan_path_builds_correct_args(self):
        calls = []

        def capture_run(cmd, **kwargs):
            calls.append(cmd)
            return MagicMock(returncode=0, stdout=b'{"matches":[]}')

        client = GrypeClient()
        with (
            patch("shutil.which", return_value="/usr/bin/grype"),
            patch("subprocess.run", side_effect=capture_run),
        ):
            client.scan_path(".")

        assert calls[0] == ["grype", ".", "-o", "json"]

    def test_rejects_null_byte_in_sbom_path(self):
        client = GrypeClient()
        assert client.scan_sbom("path\x00.json") is None


# ── CosignClient ──────────────────────────────────────────────────────────────


class TestCosignClient:
    """CosignClient-specific adapter methods."""

    def test_tool_name(self):
        assert CosignClient.tool_name == "cosign"

    def test_default_timeout_matches_constant(self):
        assert CosignClient.default_timeout == TOOL_TIMEOUTS["cosign"]

    def test_verify_signature_returns_true_on_success(self):
        result = MagicMock(returncode=0, stdout=b"Verified OK\n")
        client = CosignClient()
        with (
            patch("shutil.which", return_value="/usr/bin/cosign"),
            patch("subprocess.run", return_value=result),
        ):
            assert client.verify_signature("ghcr.io/org/image@sha256:" + "a" * 64) is True

    def test_verify_signature_returns_false_when_unavailable(self):
        client = CosignClient()
        with patch("shutil.which", return_value=None):
            assert client.verify_signature("image:tag") is False

    def test_verify_signature_rejects_null_byte(self):
        client = CosignClient()
        assert client.verify_signature("image\x00:tag") is False

    def test_attest_rejects_null_byte(self):
        client = CosignClient()
        assert client.attest("image\x00", "predicate.json") is None
        assert client.attest("image", "pred\x00.json") is None

    def test_attest_rejects_empty_args(self):
        client = CosignClient()
        assert client.attest("", "predicate.json") is None
        assert client.attest("image", "") is None


# ── Factory functions ─────────────────────────────────────────────────────────


class TestGetToolClients:
    """get_tool_clients() returns all five clients."""

    def test_returns_all_five_tools(self):
        clients = get_tool_clients()
        assert set(clients.keys()) == {"gh", "crane", "syft", "grype", "cosign"}

    def test_each_client_is_correct_type(self):
        clients = get_tool_clients()
        assert isinstance(clients["gh"], GhClient)
        assert isinstance(clients["crane"], CraneClient)
        assert isinstance(clients["syft"], SyftClient)
        assert isinstance(clients["grype"], GrypeClient)
        assert isinstance(clients["cosign"], CosignClient)


class TestCheckToolAvailability:
    """check_tool_availability() reports status for all tools."""

    def test_all_tools_unavailable_when_which_returns_none(self):
        with patch("shutil.which", return_value=None):
            status = check_tool_availability()
        assert set(status.keys()) == {"gh", "crane", "syft", "grype", "cosign"}
        for name, msg in status.items():
            assert "unavailable" in msg.lower(), f"Expected 'unavailable' for {name}: {msg}"

    def test_all_tools_available_when_which_returns_path(self):
        with patch("shutil.which", return_value="/usr/bin/tool"):
            status = check_tool_availability()
        for name, msg in status.items():
            assert "available" in msg.lower(), f"Expected 'available' for {name}: {msg}"

    def test_status_includes_timeout_value(self):
        with patch("shutil.which", return_value="/usr/bin/tool"):
            status = check_tool_availability()
        assert "15" in status["gh"]  # 15s timeout visible
        assert "20" in status["crane"]
        assert "120" in status["syft"]
        assert "60" in status["grype"]

    def test_timeout_mentioned_even_when_unavailable(self):
        with patch("shutil.which", return_value=None):
            status = check_tool_availability()
        for name, msg in status.items():
            timeout_val = str(TOOL_TIMEOUTS[name])
            assert timeout_val in msg, (
                f"Timeout {timeout_val} not found in unavailable status for {name!r}: {msg!r}"
            )
