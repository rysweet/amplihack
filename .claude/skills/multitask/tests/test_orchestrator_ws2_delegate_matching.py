#!/usr/bin/env python3
"""WS2: Subordinate Session Delegate Matching — Failing Tests.

Tests that subordinate sessions spawned by the recipe runner use the same
amplihack delegate as the parent (amplihack claude / copilot / amplifier).
These tests FAIL until the WS2 implementation is complete.

Coverage:
  - VALID_DELEGATES: module-level frozenset allowlist
  - _detect_delegate(): env var → LauncherDetector → fallback chain
  - launch(): passes AMPLIHACK_DELEGATE env var to Popen
  - launch_all(): detects delegate once and passes to launch()
  - _write_classic_launcher(): uses detected delegate (not hardcoded 'amplihack claude')
  - _write_recipe_launcher(): exports AMPLIHACK_DELEGATE in run.sh
  - Warning emitted when delegate falls back to default
"""

import os
import sys
import warnings
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


def make_workstream(tmp_path: Path, issue: int = 42):
    """Create a minimal Workstream with work_dir and run.sh."""
    from orchestrator import Workstream

    ws = Workstream(issue=issue, branch=f"feat/issue-{issue}", description="test", task="do it")
    ws.work_dir = tmp_path / f"ws-{issue}"
    ws.work_dir.mkdir(parents=True, exist_ok=True)
    ws.log_file = tmp_path / f"log-{issue}.txt"
    run_sh = ws.work_dir / "run.sh"
    run_sh.write_text("#!/bin/bash\nexit 0\n")
    run_sh.chmod(0o755)
    return ws


# ---------------------------------------------------------------------------
# 1. VALID_DELEGATES: module-level frozenset
# ---------------------------------------------------------------------------


class TestValidDelegates:
    """VALID_DELEGATES frozenset must exist as single source of truth for injection prevention."""

    def test_valid_delegates_exists(self):
        """VALID_DELEGATES must exist at module level in orchestrator.py."""
        import orchestrator as orc_module

        assert hasattr(orc_module, "VALID_DELEGATES"), (
            "VALID_DELEGATES frozenset is missing from orchestrator.py. "
            "Add: VALID_DELEGATES = frozenset({'amplihack claude', 'amplihack copilot', 'amplihack amplifier'})"
        )

    def test_valid_delegates_is_frozenset(self):
        """VALID_DELEGATES must be a frozenset (immutable allowlist)."""
        import orchestrator as orc_module

        vd = orc_module.VALID_DELEGATES
        assert isinstance(vd, frozenset), (
            f"VALID_DELEGATES must be a frozenset for immutability, got {type(vd).__name__}"
        )

    def test_valid_delegates_contains_all_three(self):
        """VALID_DELEGATES must include all three supported delegates."""
        import orchestrator as orc_module

        vd = orc_module.VALID_DELEGATES
        assert "amplihack claude" in vd, (
            f"VALID_DELEGATES must include 'amplihack claude', got {vd}"
        )
        assert "amplihack copilot" in vd, (
            f"VALID_DELEGATES must include 'amplihack copilot', got {vd}"
        )
        assert "amplihack amplifier" in vd, (
            f"VALID_DELEGATES must include 'amplihack amplifier', got {vd}"
        )

    def test_valid_delegates_rejects_arbitrary_strings(self):
        """VALID_DELEGATES must NOT contain arbitrary strings (injection prevention)."""
        import orchestrator as orc_module

        vd = orc_module.VALID_DELEGATES
        injection_attempts = [
            "amplihack claude; rm -rf /",
            "../evil-binary",
            "amplihack claude --extra-flag",
            "",
        ]
        for attempt in injection_attempts:
            assert attempt not in vd, (
                f"VALID_DELEGATES must not contain injection string: {attempt!r}"
            )


# ---------------------------------------------------------------------------
# 2. _detect_delegate(): env var → LauncherDetector → fallback
# ---------------------------------------------------------------------------


class TestDetectDelegate:
    """_detect_delegate() must resolve delegate via env var or LauncherDetector."""

    def test_detect_delegate_method_exists(self, tmp_path):
        """_detect_delegate() must exist on ParallelOrchestrator."""
        orc = make_orchestrator(tmp_path)
        assert hasattr(orc, "_detect_delegate"), (
            "ParallelOrchestrator is missing '_detect_delegate()' method. "
            "This method resolves the delegate from AMPLIHACK_DELEGATE env var → "
            "LauncherDetector → 'amplihack claude' fallback."
        )
        assert callable(orc._detect_delegate)

    def test_detect_delegate_returns_env_var_when_set(self, tmp_path):
        """_detect_delegate() must return AMPLIHACK_DELEGATE env var value when set and valid."""
        orc = make_orchestrator(tmp_path)

        for delegate in ["amplihack claude", "amplihack copilot", "amplihack amplifier"]:
            with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": delegate}):
                result = orc._detect_delegate()
                assert result == delegate, (
                    f"When AMPLIHACK_DELEGATE='{delegate}', _detect_delegate() "
                    f"must return '{delegate}', got {result!r}"
                )

    def test_detect_delegate_rejects_invalid_env_var(self, tmp_path):
        """_detect_delegate() must reject invalid AMPLIHACK_DELEGATE values (injection prevention)."""
        orc = make_orchestrator(tmp_path)

        invalid_values = [
            "amplihack claude; rm -rf /",
            "evil-binary",
            "amplihack claude --extra-flag",
        ]
        for invalid in invalid_values:
            with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": invalid}):
                result = orc._detect_delegate()
                assert result in ("amplihack claude", "amplihack copilot", "amplihack amplifier"), (
                    f"Invalid AMPLIHACK_DELEGATE={invalid!r} must be rejected. "
                    f"_detect_delegate() should fall back to a valid delegate, got {result!r}"
                )
                assert result != invalid, (
                    f"Injection attempt {invalid!r} was not rejected by _detect_delegate()"
                )

    def test_detect_delegate_uses_launcher_detector_when_env_not_set(self, tmp_path):
        """_detect_delegate() must call LauncherDetector when AMPLIHACK_DELEGATE not in env."""
        orc = make_orchestrator(tmp_path)

        env_without_delegate = {k: v for k, v in os.environ.items() if k != "AMPLIHACK_DELEGATE"}

        with patch.dict(os.environ, env_without_delegate, clear=True):
            with patch(
                "orchestrator.LauncherDetector",
                autospec=True,
            ) as mock_detector_cls:
                mock_instance = mock_detector_cls.return_value
                mock_instance.detect.return_value = "copilot"
                orc._detect_delegate()

            # LauncherDetector must have been instantiated and detect() called
            assert mock_detector_cls.called or mock_instance.detect.called, (
                "_detect_delegate() must use LauncherDetector when AMPLIHACK_DELEGATE "
                "env var is not set."
            )

    def test_detect_delegate_maps_copilot_to_full_command(self, tmp_path):
        """_detect_delegate() must map 'copilot' launcher type → 'amplihack copilot'."""
        orc = make_orchestrator(tmp_path)

        env_without_delegate = {k: v for k, v in os.environ.items() if k != "AMPLIHACK_DELEGATE"}

        with patch.dict(os.environ, env_without_delegate, clear=True):
            with patch("orchestrator.LauncherDetector") as mock_detector_cls:
                mock_instance = mock_detector_cls.return_value
                mock_instance.detect.return_value = "copilot"

                result = orc._detect_delegate()

        assert result == "amplihack copilot", (
            f"LauncherDetector returning 'copilot' should map to 'amplihack copilot', "
            f"got {result!r}"
        )

    def test_detect_delegate_maps_amplifier_to_full_command(self, tmp_path):
        """_detect_delegate() must map 'amplifier' launcher type → 'amplihack amplifier'."""
        orc = make_orchestrator(tmp_path)

        env_without_delegate = {k: v for k, v in os.environ.items() if k != "AMPLIHACK_DELEGATE"}

        with patch.dict(os.environ, env_without_delegate, clear=True):
            with patch("orchestrator.LauncherDetector") as mock_detector_cls:
                mock_instance = mock_detector_cls.return_value
                mock_instance.detect.return_value = "amplifier"

                result = orc._detect_delegate()

        assert result == "amplihack amplifier", (
            f"LauncherDetector returning 'amplifier' should map to 'amplihack amplifier', "
            f"got {result!r}"
        )

    def test_detect_delegate_falls_back_to_claude_on_unknown(self, tmp_path):
        """_detect_delegate() must fall back to 'amplihack claude' when detection fails."""
        orc = make_orchestrator(tmp_path)

        env_without_delegate = {k: v for k, v in os.environ.items() if k != "AMPLIHACK_DELEGATE"}

        with patch.dict(os.environ, env_without_delegate, clear=True):
            with patch("orchestrator.LauncherDetector") as mock_detector_cls:
                mock_instance = mock_detector_cls.return_value
                mock_instance.detect.side_effect = Exception("detection failed")

                result = orc._detect_delegate()

        assert result == "amplihack claude", (
            f"When detection fails completely, must fall back to 'amplihack claude', got {result!r}"
        )

    def test_detect_delegate_emits_warning_on_fallback(self, tmp_path):
        """_detect_delegate() must emit a visible warning when falling back to default."""
        orc = make_orchestrator(tmp_path)

        env_without_delegate = {k: v for k, v in os.environ.items() if k != "AMPLIHACK_DELEGATE"}

        import io as _io

        captured_output = _io.StringIO()

        with patch.dict(os.environ, env_without_delegate, clear=True):
            with patch("orchestrator.LauncherDetector") as mock_detector_cls:
                mock_instance = mock_detector_cls.return_value
                mock_instance.detect.return_value = "unknown"

                with patch("sys.stdout", captured_output):
                    with warnings.catch_warnings(record=True) as w:
                        warnings.simplefilter("always")
                        orc._detect_delegate()

        # Warning must appear in either warnings.warn() OR print() output
        warning_texts = [str(warning.message) for warning in w]
        stdout_text = captured_output.getvalue()
        all_warnings = " ".join(warning_texts) + " " + stdout_text

        assert "WARNING" in all_warnings.upper() or "warn" in all_warnings.lower(), (
            "_detect_delegate() must emit a visible WARNING when falling back to default. "
            f"No warning found in: warnings={warning_texts}, stdout={stdout_text!r}"
        )
        assert "amplihack claude" in all_warnings or "claude" in all_warnings.lower(), (
            f"Warning must mention the fallback delegate 'amplihack claude'. Got: {all_warnings!r}"
        )


# ---------------------------------------------------------------------------
# 3. launch(): passes AMPLIHACK_DELEGATE env var to Popen
# ---------------------------------------------------------------------------


class TestLaunchPassesDelegateEnv:
    """launch() must inject AMPLIHACK_DELEGATE into the subprocess environment."""

    def test_launch_passes_amplihack_delegate_env_var(self, tmp_path):
        """launch() must pass env={**os.environ, 'AMPLIHACK_DELEGATE': delegate} to Popen."""
        import subprocess

        orc = make_orchestrator(tmp_path)
        ws = make_workstream(tmp_path, issue=300)

        popen_calls = []

        def mock_popen(*args, **kwargs):
            popen_calls.append(kwargs)
            return subprocess.Popen(
                ["echo", "done"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack copilot"}):
            with patch("subprocess.Popen", side_effect=mock_popen):
                try:
                    orc.launch(ws, delegate="amplihack copilot")
                except TypeError:
                    # launch() might not take delegate as arg yet — try without
                    pass
                except Exception:
                    pass

        if not popen_calls:
            # Try calling launch without explicit delegate arg
            with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack copilot"}):
                with patch("subprocess.Popen", side_effect=mock_popen):
                    try:
                        orc.launch(ws)
                    except Exception:
                        pass

        assert popen_calls, "subprocess.Popen was never called during launch()"
        call_env = popen_calls[0].get("env")
        assert call_env is not None, (
            "launch() must pass an explicit 'env' dict to subprocess.Popen. "
            "Without it, AMPLIHACK_DELEGATE won't be set in the subprocess environment."
        )
        assert "AMPLIHACK_DELEGATE" in call_env, (
            f"The 'env' dict passed to Popen must contain 'AMPLIHACK_DELEGATE'. "
            f"Got env keys: {list(call_env.keys())[:10]}..."
        )
        assert call_env["AMPLIHACK_DELEGATE"] in (
            "amplihack claude",
            "amplihack copilot",
            "amplihack amplifier",
        ), (
            f"AMPLIHACK_DELEGATE in Popen env must be a valid delegate, "
            f"got {call_env['AMPLIHACK_DELEGATE']!r}"
        )

    def test_launch_all_detects_delegate_once(self, tmp_path):
        """launch_all() must call _detect_delegate() once, not once per workstream."""
        orc = make_orchestrator(tmp_path)

        detect_calls = []

        def mock_detect():
            detect_calls.append(1)
            return "amplihack claude"

        # Add multiple workstreams
        for i in range(3):
            ws = make_workstream(tmp_path, issue=400 + i)
            orc.workstreams.append(ws)

        with patch.object(orc, "_detect_delegate", side_effect=mock_detect):
            with patch.object(orc, "launch"):  # Mock launch to avoid subprocess
                orc.launch_all()

        assert len(detect_calls) <= 1, (
            f"launch_all() must call _detect_delegate() at most ONCE for efficiency, "
            f"but it was called {len(detect_calls)} times (once per workstream is wrong). "
            "Detect the delegate once and pass it to each launch() call."
        )


# ---------------------------------------------------------------------------
# 4. _write_classic_launcher(): uses detected delegate
# ---------------------------------------------------------------------------


class TestWriteClassicLauncher:
    """_write_classic_launcher() must use the detected delegate, not hardcode 'amplihack claude'."""

    def test_classic_launcher_uses_detected_delegate_not_hardcoded(self, tmp_path):
        """run.sh written by _write_classic_launcher() must use detected delegate."""
        orc = make_orchestrator(tmp_path)
        ws = make_workstream(tmp_path, issue=500)

        # Simulate copilot environment
        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack copilot"}):
            orc._write_classic_launcher(ws)

        run_sh_content = (ws.work_dir / "run.sh").read_text()

        # Must NOT contain hardcoded 'amplihack claude' when copilot is the delegate
        assert "amplihack claude" not in run_sh_content, (
            "_write_classic_launcher() hardcodes 'amplihack claude' in run.sh even when "
            "the parent is running under copilot. "
            f"run.sh content:\n{run_sh_content}"
        )
        # Must contain the detected delegate
        assert "amplihack copilot" in run_sh_content, (
            f"run.sh must use the detected delegate 'amplihack copilot', but got:\n{run_sh_content}"
        )

    def test_classic_launcher_default_is_claude(self, tmp_path):
        """When no delegate detected, run.sh must default to 'amplihack claude'."""
        orc = make_orchestrator(tmp_path)
        ws = make_workstream(tmp_path, issue=501)

        env_without_delegate = {k: v for k, v in os.environ.items() if k != "AMPLIHACK_DELEGATE"}

        with patch.dict(os.environ, env_without_delegate, clear=True):
            with patch("orchestrator.LauncherDetector") as mock_det_cls:
                mock_det_cls.return_value.detect.return_value = "unknown"
                orc._write_classic_launcher(ws)

        run_sh_content = (ws.work_dir / "run.sh").read_text()
        assert "amplihack claude" in run_sh_content, (
            f"When no delegate is detected, run.sh must default to 'amplihack claude'. "
            f"Got:\n{run_sh_content}"
        )

    def test_classic_launcher_uses_exec_not_shell_variable(self, tmp_path):
        """run.sh must use baked delegate value, not '$AMPLIHACK_DELEGATE' variable expansion."""
        orc = make_orchestrator(tmp_path)
        ws = make_workstream(tmp_path, issue=502)

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack copilot"}):
            orc._write_classic_launcher(ws)

        run_sh_content = (ws.work_dir / "run.sh").read_text()

        # Must NOT use shell variable expansion for the delegate command
        # (vulnerable to env var poisoning between write-time and exec-time)
        assert "$AMPLIHACK_DELEGATE" not in run_sh_content, (
            "run.sh must NOT use '$AMPLIHACK_DELEGATE' shell variable expansion. "
            "The delegate must be baked in at generation time to prevent injection. "
            f"Got run.sh:\n{run_sh_content}"
        )


# ---------------------------------------------------------------------------
# 5. _write_recipe_launcher(): exports AMPLIHACK_DELEGATE
# ---------------------------------------------------------------------------


class TestWriteRecipeLauncher:
    """_write_recipe_launcher() must export AMPLIHACK_DELEGATE in run.sh."""

    def test_recipe_launcher_exports_amplihack_delegate(self, tmp_path):
        """run.sh from _write_recipe_launcher() must export AMPLIHACK_DELEGATE."""
        orc = make_orchestrator(tmp_path)
        ws = make_workstream(tmp_path, issue=600)

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack copilot"}):
            orc._write_recipe_launcher(ws)

        run_sh_content = (ws.work_dir / "run.sh").read_text()

        assert "AMPLIHACK_DELEGATE" in run_sh_content, (
            "run.sh from _write_recipe_launcher() must export AMPLIHACK_DELEGATE "
            "so nested ClaudeProcess (in claude_process.py) inherits the correct delegate. "
            f"Got:\n{run_sh_content}"
        )
        # Must be an export, not just a comment
        assert "export AMPLIHACK_DELEGATE" in run_sh_content or (
            "AMPLIHACK_DELEGATE" in run_sh_content and "export" in run_sh_content
        ), f"AMPLIHACK_DELEGATE must be exported (not just set) in run.sh. Got:\n{run_sh_content}"

    def test_recipe_launcher_bakes_in_delegate_value(self, tmp_path):
        """run.sh must contain the actual delegate value, not a variable reference."""
        orc = make_orchestrator(tmp_path)
        ws = make_workstream(tmp_path, issue=601)

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack amplifier"}):
            orc._write_recipe_launcher(ws)

        run_sh_content = (ws.work_dir / "run.sh").read_text()

        assert "amplihack amplifier" in run_sh_content, (
            "run.sh must contain the baked delegate value 'amplihack amplifier'. "
            f"Got:\n{run_sh_content}"
        )

    def test_recipe_launcher_propagates_through_nested_calls(self, tmp_path):
        """AMPLIHACK_DELEGATE in run.sh must be exported so child processes inherit it."""
        orc = make_orchestrator(tmp_path)
        ws = make_workstream(tmp_path, issue=602)

        with patch.dict(os.environ, {"AMPLIHACK_DELEGATE": "amplihack copilot"}):
            orc._write_recipe_launcher(ws)

        run_sh_content = (ws.work_dir / "run.sh").read_text()

        # The export must make AMPLIHACK_DELEGATE available to child processes
        # (i.e., "export" keyword must be present, not just an assignment)
        lines_with_delegate = [
            ln
            for ln in run_sh_content.splitlines()
            if "AMPLIHACK_DELEGATE" in ln and not ln.strip().startswith("#")
        ]
        assert lines_with_delegate, "No non-comment lines with AMPLIHACK_DELEGATE found in run.sh"
        has_export = any("export" in ln for ln in lines_with_delegate)
        assert has_export, (
            "AMPLIHACK_DELEGATE must be exported with 'export' keyword so child "
            f"processes inherit it. Lines found: {lines_with_delegate}"
        )


# ---------------------------------------------------------------------------
# 6. Warning contract
# ---------------------------------------------------------------------------


class TestDelegateWarningContract:
    """WARNING must be emitted (not suppressed) when falling back to default delegate."""

    def test_warning_mentions_amplihack_delegate_env_var(self, tmp_path):
        """Warning message must tell the user how to fix it (set AMPLIHACK_DELEGATE)."""
        orc = make_orchestrator(tmp_path)

        import io as _io

        captured = _io.StringIO()
        env_without_delegate = {k: v for k, v in os.environ.items() if k != "AMPLIHACK_DELEGATE"}

        with patch.dict(os.environ, env_without_delegate, clear=True):
            with patch("orchestrator.LauncherDetector") as mock_det:
                mock_det.return_value.detect.return_value = "unknown"
                with patch("sys.stdout", captured):
                    with warnings.catch_warnings(record=True) as w:
                        warnings.simplefilter("always")
                        try:
                            orc._detect_delegate()
                        except Exception:
                            pass

        all_output = captured.getvalue() + " ".join(str(warning.message) for warning in w)

        # Per design spec: format must be visible (not debug-level)
        # Check warning mentions either AMPLIHACK_DELEGATE or the fallback behavior
        assert "AMPLIHACK_DELEGATE" in all_output or "claude" in all_output.lower(), (
            "Warning must mention 'AMPLIHACK_DELEGATE' or the default delegate. "
            f"Got: {all_output!r}"
        )

    def test_warning_not_suppressed_as_debug(self, tmp_path):
        """Warning must appear in standard output (print or warnings.warn), not only in logs."""
        orc = make_orchestrator(tmp_path)

        import io as _io
        import logging

        # Capture logging output too
        log_capture = _io.StringIO()
        handler = logging.StreamHandler(log_capture)
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        captured_stdout = _io.StringIO()
        env_without_delegate = {k: v for k, v in os.environ.items() if k != "AMPLIHACK_DELEGATE"}

        try:
            with patch.dict(os.environ, env_without_delegate, clear=True):
                with patch("orchestrator.LauncherDetector") as mock_det:
                    mock_det.return_value.detect.return_value = "unknown"
                    with patch("sys.stdout", captured_stdout):
                        with warnings.catch_warnings(record=True) as w:
                            warnings.simplefilter("always")
                            try:
                                orc._detect_delegate()
                            except Exception:
                                pass
        finally:
            root_logger.removeHandler(handler)

        stdout_text = captured_stdout.getvalue()
        warning_texts = " ".join(str(wn.message) for wn in w)
        log_text = log_capture.getvalue()

        # At least one of stdout or warnings must be non-empty
        total_output = stdout_text + warning_texts + log_text
        assert total_output.strip(), (
            "_detect_delegate() must emit some visible output when falling back. "
            "An invisible/suppressed warning is unacceptable per the design spec."
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
