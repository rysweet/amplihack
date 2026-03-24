"""
Unit tests — Named Error Conditions
TDD: Tests define the 5 named error conditions from contracts.md.
All tests FAIL until supply_chain_audit.errors is implemented.
"""

import pytest
from supply_chain_audit.audit import run_audit
from supply_chain_audit.errors import (
    AcceptedRisksOverflowError,
    InvalidScopeError,
    PathTraversalError,
)


class TestInvalidScopeError:
    """INVALID_SCOPE: unrecognized --scope value."""

    def test_error_code_in_exception(self, tmp_path):
        with pytest.raises(InvalidScopeError) as exc_info:
            run_audit(str(tmp_path), scope="kubernetes")
        assert exc_info.value.error_code == "INVALID_SCOPE"

    def test_valid_scope_list_in_exception_message(self, tmp_path):
        with pytest.raises(InvalidScopeError) as exc_info:
            run_audit(str(tmp_path), scope="invalid")
        msg = str(exc_info.value)
        # Must list valid scopes so user knows what to use
        for valid in ["gha", "containers", "python", "node", "go", "rust", "dotnet", "all"]:
            assert valid in msg

    def test_audit_aborts_immediately_on_invalid_scope(self, tmp_path):
        """No files should be read when scope is invalid."""
        reads = []
        import builtins

        original_open = builtins.open

        def tracking_open(path, *args, **kwargs):
            reads.append(str(path))
            return original_open(path, *args, **kwargs)

        import builtins

        builtins.open = tracking_open
        try:
            with pytest.raises(InvalidScopeError):
                run_audit(str(tmp_path), scope="bad_scope")
        finally:
            builtins.open = original_open

        # No project files should have been opened — audit aborted before reading
        project_reads = [
            r for r in reads if not r.endswith(".py") and "supply_chain_audit" not in r
        ]
        assert project_reads == []


class TestPathTraversalError:
    """PATH_TRAVERSAL: path contains ../, null byte, or escaping symlink."""

    def test_error_code_in_exception(self, tmp_path):
        with pytest.raises(PathTraversalError) as exc_info:
            run_audit(str(tmp_path / ".." / "other"), scope="all")
        assert exc_info.value.error_code == "PATH_TRAVERSAL"

    def test_rejected_path_logged_in_exception(self, tmp_path):
        bad_path = str(tmp_path / ".." / "sensitive")
        with pytest.raises(PathTraversalError) as exc_info:
            run_audit(bad_path, scope="all")
        assert bad_path in str(exc_info.value) or ".." in str(exc_info.value)

    def test_audit_never_begins_on_path_traversal(self, tmp_path):
        """Filesystem reads must not occur after PATH_TRAVERSAL detection."""
        import supply_chain_audit.detector as detector

        calls = []
        original_detect = detector.detect_ecosystems

        def tracking_detect(*args, **kwargs):
            calls.append(args)
            return original_detect(*args, **kwargs)

        detector.detect_ecosystems = tracking_detect
        try:
            with pytest.raises(PathTraversalError):
                run_audit(str(tmp_path / ".." / "other"), scope="all")
        finally:
            detector.detect_ecosystems = original_detect

        assert calls == [], "Ecosystem detection must not run on traversal path"


class TestToolTimeoutError:
    """TOOL_TIMEOUT: external tool exceeds timeout; audit continues degraded."""

    def test_timeout_does_not_abort_audit(self, tmp_path, monkeypatch):
        import subprocess

        def always_timeout(args, **kwargs):
            raise subprocess.TimeoutExpired(args[0] if args else "tool", 15)

        monkeypatch.setattr(subprocess, "run", always_timeout)
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\npermissions: read-all\njobs:\n  build:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
        )
        # Must not raise — degraded mode
        result = run_audit(str(tmp_path), scope="gha")
        assert result is not None

    def test_degraded_mode_report_names_timed_out_tool(self, tmp_path, monkeypatch):
        import subprocess

        def timeout_gh(args, **kwargs):
            if isinstance(args, (list, tuple)) and args and "gh" in str(args[0]):
                raise subprocess.TimeoutExpired("gh", 15)
            return subprocess.CompletedProcess(args, 0, b"", b"")

        monkeypatch.setattr(subprocess, "run", timeout_gh)
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\npermissions: read-all\njobs:\n  build:\n"
            "    runs-on: ubuntu-latest\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        report = result.render_report()
        assert "gh" in report or "tool" in report.lower()
        assert (
            "degraded" in report.lower()
            or "unavailable" in report.lower()
            or "offline" in report.lower()
        )

    def test_offline_detectable_findings_still_reported_on_timeout(self, tmp_path, monkeypatch):
        """offline_detectable=true findings must still appear when tools time out."""
        import subprocess

        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired(str(a), 15)),
        )
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        # SHA pinning finding (offline_detectable=true) must appear
        assert len(result.findings) >= 1
        sha_findings = [f for f in result.findings if f.offline_detectable is True]
        assert len(sha_findings) >= 1


class TestAcceptedRisksOverflow:
    """ACCEPTED_RISKS_OVERFLOW: file > 64KB aborts audit."""

    def test_overflow_file_aborts_audit(self, tmp_path):
        risk_file = tmp_path / ".supply-chain-accepted-risks.yml"
        risk_file.write_bytes(b"- id: HIGH-001\n" * 5000)  # well over 64KB
        assert risk_file.stat().st_size > 64 * 1024
        with pytest.raises(AcceptedRisksOverflowError) as exc_info:
            run_audit(str(tmp_path), scope="all")
        assert exc_info.value.error_code == "ACCEPTED_RISKS_OVERFLOW"

    def test_overflow_error_instructs_user_to_split_file(self, tmp_path):
        risk_file = tmp_path / ".supply-chain-accepted-risks.yml"
        risk_file.write_bytes(b"x" * (64 * 1024 + 100))
        with pytest.raises(AcceptedRisksOverflowError) as exc_info:
            run_audit(str(tmp_path), scope="all")
        msg = str(exc_info.value)
        # Must tell user what to do
        assert "split" in msg.lower() or "archive" in msg.lower()

    def test_exactly_64kb_is_accepted(self, tmp_path):
        risk_file = tmp_path / ".supply-chain-accepted-risks.yml"
        risk_file.write_bytes(b"x" * (64 * 1024))  # exactly 64KB — must be OK
        # Should not raise overflow
        try:
            run_audit(str(tmp_path), scope="all")
        except AcceptedRisksOverflowError:
            pytest.fail("64KB exactly should not trigger ACCEPTED_RISKS_OVERFLOW")
        except Exception:
            pass  # Other errors are fine


class TestToolNotAvailableDegradedMode:
    """When a tool is absent (not timeout), report degraded mode and continue."""

    def test_missing_gh_tool_falls_back_to_offline(self, tmp_path, monkeypatch):
        import shutil

        monkeypatch.setattr(shutil, "which", lambda tool: None)  # no tools found
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        report = result.render_report()
        assert (
            "not available" in report.lower()
            or "unavailable" in report.lower()
            or "degraded" in report.lower()
        )

    def test_tool_not_available_message_names_tool_and_degraded_checks(self, tmp_path, monkeypatch):
        import shutil

        monkeypatch.setattr(shutil, "which", lambda tool: None)
        wf = tmp_path / ".github" / "workflows" / "ci.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n"
        )
        result = run_audit(str(tmp_path), scope="gha")
        report = result.render_report()
        # Must name which checks are degraded
        assert "gh" in report or "crane" in report or "tool" in report.lower()


class TestFileNotReadableError:
    """Unreadable files produce a warning and skip that file's dimension checks."""

    def test_unreadable_file_skipped_with_warning(self, tmp_path):
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        wf = wf_dir / "ci.yml"
        wf.write_text("name: CI\n")
        wf.chmod(0o000)  # Make unreadable
        try:
            result = run_audit(str(tmp_path), scope="gha")
            report = result.render_report()
            assert (
                "not readable" in report.lower()
                or "unreadable" in report.lower()
                or "skipped" in report.lower()
            )
        finally:
            wf.chmod(0o644)  # Restore for cleanup

    def test_unreadable_file_does_not_abort_audit(self, tmp_path):
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        wf1 = wf_dir / "ci.yml"
        wf2 = wf_dir / "release.yml"
        wf1.write_text(
            "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n"
        )
        wf2.write_text("name: Release\n")
        wf2.chmod(0o000)
        try:
            # Should not raise — should skip unreadable and continue
            result = run_audit(str(tmp_path), scope="gha")
            assert result is not None
        finally:
            wf2.chmod(0o644)
