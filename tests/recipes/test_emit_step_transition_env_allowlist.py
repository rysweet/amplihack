"""TDD tests for emit_step_transition, build_rust_env, and the env allowlist.

Several tests here are INTENTIONALLY FAILING (red phase) because they specify
behaviour not yet implemented:

  - test_emit_step_transition_rejects_empty_step_name
      emit_step_transition() does not yet validate inputs.

  - test_log_file_does_not_grow_unbounded
      No MAX_LOG_BYTES cap is implemented; the log grows without limit.

Token forwarding (GH_AW_GITHUB_TOKEN, GITHUB_TOKEN) is now implemented —
both variables are in _ALLOWED_RUST_ENV_VARS so the Rust subprocess receives
the credentials it needs for GitHub API calls.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from unittest.mock import patch

import pytest

from amplihack.recipes.rust_runner_execution import (
    build_rust_env,
    emit_step_transition,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _capture_stderr(fn, *args, **kwargs):
    """Run *fn* and return whatever it wrote to sys.stderr as a string."""
    buf = io.StringIO()
    with patch("sys.stderr", buf):
        fn(*args, **kwargs)
    return buf.getvalue()


def _no_op_wrapper(real_path: str) -> str:
    """Stub wrapper_factory that returns a temp dir (cleaned up by OS on exit)."""
    return tempfile.mkdtemp(prefix="compat-")


def _make_env(extras: dict[str, str]) -> dict[str, str]:
    """Patch os.environ with *extras* and return the env dict from build_rust_env."""
    with patch.dict(os.environ, extras, clear=False):
        return build_rust_env(wrapper_factory=_no_op_wrapper, which=lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# emit_step_transition — basic contract (should PASS with current impl)
# ---------------------------------------------------------------------------

class TestEmitStepTransitionContract:
    """emit_step_transition must write a single valid JSONL object to stderr."""

    def test_writes_exactly_one_line_to_stderr(self):
        output = _capture_stderr(emit_step_transition, "build", "start")
        lines = [l for l in output.splitlines() if l.strip()]
        assert len(lines) == 1, f"Expected 1 line, got {len(lines)}: {output!r}"

    def test_output_is_valid_json(self):
        output = _capture_stderr(emit_step_transition, "test-step", "done")
        obj = json.loads(output.strip())
        assert isinstance(obj, dict)

    def test_output_contains_type_field(self):
        output = _capture_stderr(emit_step_transition, "deploy", "start")
        obj = json.loads(output.strip())
        assert obj["type"] == "step_transition"

    def test_output_contains_step_field(self):
        output = _capture_stderr(emit_step_transition, "my-step", "start")
        obj = json.loads(output.strip())
        assert obj["step"] == "my-step"

    def test_output_contains_status_field(self):
        output = _capture_stderr(emit_step_transition, "deploy", "done")
        obj = json.loads(output.strip())
        assert obj["status"] == "done"

    def test_output_contains_numeric_timestamp(self):
        output = _capture_stderr(emit_step_transition, "build", "fail")
        obj = json.loads(output.strip())
        assert isinstance(obj["ts"], (int, float))
        assert obj["ts"] > 0

    def test_handles_step_name_with_spaces(self):
        output = _capture_stderr(emit_step_transition, "Run tests", "start")
        obj = json.loads(output.strip())
        assert obj["step"] == "Run tests"

    def test_handles_step_name_with_unicode(self):
        output = _capture_stderr(emit_step_transition, "étape-1", "done")
        obj = json.loads(output.strip())
        assert obj["step"] == "étape-1"

    def test_status_values_start_done_fail_skip_all_accepted(self):
        for status in ("start", "done", "fail", "skip"):
            output = _capture_stderr(emit_step_transition, "step", status)
            obj = json.loads(output.strip())
            assert obj["status"] == status

    def test_output_uses_compact_separators(self):
        """Compact JSON (no spaces after : or ,) keeps each line terse."""
        output = _capture_stderr(emit_step_transition, "s", "start")
        line = output.strip()
        # Compact JSON must not have ": " or ", " sequences.
        assert ": " not in line, "Separators must be compact (no space after colon)"
        assert ", " not in line, "Separators must be compact (no space after comma)"


# ---------------------------------------------------------------------------
# emit_step_transition — input validation (FAILING — not yet implemented)
# ---------------------------------------------------------------------------

class TestEmitStepTransitionValidation:
    """These tests specify DESIRED behaviour that is not yet implemented.

    They are expected to FAIL in the red phase and PASS once validation is added.
    """

    @pytest.mark.xfail(
        reason="emit_step_transition does not yet raise on empty step_name (not implemented)",
        strict=True,
    )
    def test_rejects_empty_step_name(self):
        """An empty step name makes JSONL events unidentifiable — must be rejected."""
        with pytest.raises(ValueError, match="step_name"):
            emit_step_transition("", "start")

    @pytest.mark.xfail(
        reason="emit_step_transition does not yet validate status values (not implemented)",
        strict=True,
    )
    def test_rejects_unknown_status(self):
        """Only the four canonical statuses (start/done/fail/skip) should be accepted."""
        with pytest.raises(ValueError, match="status"):
            emit_step_transition("build", "INVALID_STATUS")

    @pytest.mark.xfail(
        reason="emit_step_transition does not yet reject newlines (not implemented)",
        strict=True,
    )
    def test_rejects_step_name_with_newline(self):
        """A step name containing a newline would break line-delimited JSON parsing."""
        with pytest.raises(ValueError, match="step_name"):
            emit_step_transition("line1\nline2", "start")


# ---------------------------------------------------------------------------
# build_rust_env — env allowlist (PASSING — basic secret exclusion)
# ---------------------------------------------------------------------------

class TestBuildRustEnvSecretExclusion:
    """build_rust_env must NEVER forward secret variables to the subprocess."""

    def test_excludes_anthropic_api_key(self):
        env = _make_env({"ANTHROPIC_API_KEY": "sk-ant-secret"})
        assert "ANTHROPIC_API_KEY" not in env, (
            "ANTHROPIC_API_KEY must never be forwarded to the Rust subprocess"
        )

    def test_excludes_gh_token(self):
        env = _make_env({"GH_TOKEN": "ghp_secret"})
        assert "GH_TOKEN" not in env, (
            "GH_TOKEN must never be forwarded to the Rust subprocess"
        )

    def test_excludes_gh_aw_github_mcp_server_token(self):
        env = _make_env({"GH_AW_GITHUB_MCP_SERVER_TOKEN": "ghs_mcp_secret"})
        assert "GH_AW_GITHUB_MCP_SERVER_TOKEN" not in env

    def test_excludes_aws_secret_access_key(self):
        env = _make_env({"AWS_SECRET_ACCESS_KEY": "FAKE_TEST_KEY_not_real"})
        assert "AWS_SECRET_ACCESS_KEY" not in env

    def test_excludes_npm_token(self):
        env = _make_env({"NPM_TOKEN": "FAKE_npm_test_token"})
        assert "NPM_TOKEN" not in env


# ---------------------------------------------------------------------------
# build_rust_env — token forwarding
# ---------------------------------------------------------------------------

class TestBuildRustEnvTokenForwarding:
    """GH_AW_GITHUB_TOKEN and GITHUB_TOKEN must be forwarded to the Rust subprocess.

    The Rust runner invokes the gh CLI and makes GitHub API calls; it therefore
    needs at least one GitHub token.  Both tokens are now in _ALLOWED_RUST_ENV_VARS.
    GH_AW_GITHUB_TOKEN is the preferred scoped token; GITHUB_TOKEN is the fallback.
    """

    def test_forwards_gh_aw_github_token(self):
        """GH_AW_GITHUB_TOKEN must reach the Rust subprocess so gh CLI calls succeed."""
        env = _make_env({"GH_AW_GITHUB_TOKEN": "ghs_preferred_token"})
        assert "GH_AW_GITHUB_TOKEN" in env, (
            "GH_AW_GITHUB_TOKEN must be in the forwarded env; add it to _ALLOWED_RUST_ENV_VARS"
        )

    def test_forwards_github_token_as_fallback(self):
        """GITHUB_TOKEN must be forwarded when GH_AW_GITHUB_TOKEN is absent."""
        env = _make_env({"GITHUB_TOKEN": "ghs_fallback_token"})
        assert "GITHUB_TOKEN" in env, (
            "GITHUB_TOKEN must be in the forwarded env; add it to _ALLOWED_RUST_ENV_VARS"
        )


# ---------------------------------------------------------------------------
# build_rust_env — safe vars that MUST be forwarded (PASSING)
# ---------------------------------------------------------------------------

class TestBuildRustEnvSafeVarForwarding:
    """Variables in _ALLOWED_RUST_ENV_VARS must be present when set in the parent env."""

    @pytest.mark.parametrize(
        "key,value",
        [
            ("PATH", "/usr/local/bin:/usr/bin"),
            ("HOME", "/home/runner"),
            ("PYTHONPATH", "/app/src"),
            ("AMPLIHACK_SESSION_ID", "sess-abc123"),
            ("AMPLIHACK_AGENT_BINARY", "copilot"),
            ("TMPDIR", "/tmp"),
        ],
    )
    def test_allowed_var_is_forwarded(self, key, value):
        env = _make_env({key: value})
        assert env.get(key) == value, f"{key} must be forwarded to Rust subprocess"

    def test_returns_dict_not_none(self):
        env = _make_env({})
        assert isinstance(env, dict)


# ---------------------------------------------------------------------------
# Log file size cap (FAILING — MAX_LOG_BYTES not yet implemented)
# ---------------------------------------------------------------------------

class TestLogFileSizeCap:
    """The log file written during progress-mode execution must be bounded.

    Design spec risk: 'Log file size unbounded — no MAX_LOG_BYTES cap
    implemented yet.'  These tests specify the desired behaviour.
    """

    @pytest.mark.xfail(
        reason="No MAX_LOG_BYTES constant or truncation logic exists (not implemented)",
        strict=True,
    )
    def test_max_log_bytes_constant_exists(self):
        """A MAX_LOG_BYTES sentinel must be importable from the module."""
        import amplihack.recipes.rust_runner_execution as m  # noqa: PLC0415

        assert hasattr(m, "MAX_LOG_BYTES"), (
            "Define MAX_LOG_BYTES (e.g. 10 * 1024 * 1024) to cap log file growth"
        )
        assert m.MAX_LOG_BYTES > 0

    @pytest.mark.xfail(
        reason="No log truncation / rotation logic exists (not implemented)",
        strict=True,
    )
    def test_write_progress_mode_does_not_exceed_max_log_bytes(self, tmp_path):
        """Simulated large output must not produce a log file larger than MAX_LOG_BYTES."""
        import amplihack.recipes.rust_runner_execution as m  # noqa: PLC0415
        import subprocess  # noqa: PLC0415

        huge_line = "x" * 1024 + "\n"
        # Simulate a process that produces 12 MB of stdout (above any sensible cap).
        fake_stdout = (huge_line * (12 * 1024)).encode()
        log_file = tmp_path / "recipe.log"

        process = subprocess.Popen(
            ["python", "-c", f"import sys; sys.stdout.buffer.write({len(fake_stdout)}*b'x')"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
        m._stream_process_output_with_progress(
            process,  # type: ignore[arg-type]
            recipe_name="bigtest",
            log_file_path=log_file,
        )

        size = log_file.stat().st_size if log_file.exists() else 0
        assert size <= m.MAX_LOG_BYTES, (
            f"Log file grew to {size} bytes, exceeding MAX_LOG_BYTES={m.MAX_LOG_BYTES}"
        )
