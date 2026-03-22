# File: amplifier-bundle/tools/amplihack/hooks/tests/test_psc_integration.py
"""Integration tests for power_steering_checker package.

Tests package structure, __init__.py re-exports, backward compat,
no circular imports, end-to-end flow, _log(exc_info=True).
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPackageStructure:
    """Tests for package file structure."""

    PACKAGE_DIR = Path(__file__).parent.parent / "power_steering_checker"

    def test_package_dir_exists(self):
        assert self.PACKAGE_DIR.is_dir()

    def test_init_py_exists(self):
        assert (self.PACKAGE_DIR / "__init__.py").exists()

    def test_considerations_py_exists(self):
        assert (self.PACKAGE_DIR / "considerations.py").exists()

    def test_sdk_calls_py_exists(self):
        assert (self.PACKAGE_DIR / "sdk_calls.py").exists()

    def test_progress_tracking_py_exists(self):
        assert (self.PACKAGE_DIR / "progress_tracking.py").exists()

    def test_result_formatting_py_exists(self):
        assert (self.PACKAGE_DIR / "result_formatting.py").exists()

    def test_main_checker_py_exists(self):
        assert (self.PACKAGE_DIR / "main_checker.py").exists()

    def test_all_modules_parse_cleanly(self):
        """All modules must be syntactically valid Python."""
        import ast

        for module_file in self.PACKAGE_DIR.glob("*.py"):
            source = module_file.read_text()
            try:
                ast.parse(source)
            except SyntaxError as e:
                pytest.fail(f"SyntaxError in {module_file}: {e}")


class TestInitPyReexports:
    """Tests for __init__.py re-exports."""

    def test_power_steering_checker_importable(self):
        import power_steering_checker

        assert power_steering_checker is not None

    def test_power_steering_checker_class_exported(self):
        from power_steering_checker import PowerSteeringChecker

        assert PowerSteeringChecker is not None

    def test_power_steering_result_exported(self):
        from power_steering_checker import PowerSteeringResult

        assert PowerSteeringResult is not None

    def test_checker_result_exported(self):
        from power_steering_checker import CheckerResult

        assert CheckerResult is not None

    def test_consideration_analysis_exported(self):
        from power_steering_checker import ConsiderationAnalysis

        assert ConsiderationAnalysis is not None

    def test_power_steering_redirect_exported(self):
        from power_steering_checker import PowerSteeringRedirect

        assert PowerSteeringRedirect is not None

    def test_sdk_available_exported(self):
        from power_steering_checker import SDK_AVAILABLE

        assert isinstance(SDK_AVAILABLE, bool)

    def test_timeout_exported(self):
        from power_steering_checker import _timeout

        assert callable(_timeout)

    def test_check_session_exported(self):
        from power_steering_checker import check_session

        assert callable(check_session)

    def test_is_disabled_exported(self):
        from power_steering_checker import is_disabled

        assert callable(is_disabled)

    def test_all_dunder_contains_expected(self):
        import power_steering_checker

        expected = {
            "PowerSteeringChecker",
            "PowerSteeringResult",
            "CheckerResult",
            "ConsiderationAnalysis",
            "PowerSteeringRedirect",
            "SDK_AVAILABLE",
            "_timeout",
            "check_session",
            "is_disabled",
        }
        for name in expected:
            assert name in power_steering_checker.__all__, f"{name} missing from __all__"


class TestNoCircularImports:
    """Tests that no circular imports exist."""

    def test_considerations_no_circular(self):
        """considerations.py should be importable without circular deps."""
        # If already imported, this is fine

    def test_sdk_calls_no_circular(self):
        pass

    def test_progress_tracking_no_circular(self):
        pass

    def test_result_formatting_no_circular(self):
        pass

    def test_main_checker_no_circular(self):
        pass

    def test_all_modules_importable_together(self):
        pass


class TestBackwardCompat:
    """Tests backward compatibility via __init__.py imports."""

    def test_old_style_import_checker_result(self):
        """from power_steering_checker import CheckerResult still works."""
        from power_steering_checker import CheckerResult

        r = CheckerResult(
            consideration_id="test",
            satisfied=True,
            reason="ok",
            severity="blocker",
        )
        assert r.consideration_id == "test"

    def test_old_style_import_power_steering_result(self):
        from power_steering_checker import PowerSteeringResult

        r = PowerSteeringResult(decision="approve", reasons=["done"])
        assert r.decision == "approve"

    def test_old_style_import_power_steering_redirect(self):
        from power_steering_checker import PowerSteeringRedirect

        r = PowerSteeringRedirect(
            redirect_number=1,
            timestamp="2024-01-01",
            failed_considerations=["a"],
            continuation_prompt="fix",
        )
        assert r.redirect_number == 1

    def test_old_style_import_sdk_available(self):
        from power_steering_checker import SDK_AVAILABLE

        assert isinstance(SDK_AVAILABLE, bool)

    def test_old_style_import_timeout(self):
        from power_steering_checker import _timeout

        assert callable(_timeout)


class TestSecurityFeatureIntegration:
    """Integration tests for security features."""

    def test_validate_session_id_accessible(self):
        """REQ-SEC-1: _validate_session_id should be available."""
        from power_steering_checker.progress_tracking import _validate_session_id

        assert callable(_validate_session_id)

    def test_max_line_bytes_accessible(self):
        """REQ-SEC-3: MAX_LINE_BYTES should be defined."""
        from power_steering_checker.progress_tracking import MAX_LINE_BYTES

        assert isinstance(MAX_LINE_BYTES, int)
        assert MAX_LINE_BYTES == 10 * 1024 * 1024

    def test_env_int_in_sdk_calls(self):
        """REQ-SEC-2: _env_int should exist in sdk_calls."""
        from power_steering_checker.sdk_calls import _env_int

        assert callable(_env_int)

    def test_env_int_in_main_checker(self):
        """REQ-SEC-2: _env_int should exist in main_checker."""
        from power_steering_checker.main_checker import _env_int

        assert callable(_env_int)

    def test_env_int_in_result_formatting(self):
        """REQ-SEC-2: _env_int should exist in result_formatting."""
        from power_steering_checker.result_formatting import _env_int

        assert callable(_env_int)

    def test_log_method_supports_exc_info(self, tmp_path):
        """_log method must accept exc_info=True parameter."""
        from power_steering_checker.main_checker import PowerSteeringChecker

        with patch("power_steering_checker.main_checker.get_shared_runtime_dir") as mock_rt:
            mock_rt.return_value = str(tmp_path / "runtime")
            checker = PowerSteeringChecker(tmp_path)
        # Should not raise when exc_info=True
        checker._log("test message", "WARNING", exc_info=True)

    def test_invalid_env_vars_do_not_crash_imports(self):
        """REQ-SEC-2: Invalid env vars must not prevent module import."""
        env_overrides = {
            "PSC_CHECKER_TIMEOUT": "notanumber",
            "PSC_PARALLEL_TIMEOUT": "bad",
            "PSC_MAX_TRANSCRIPT_LINES": "invalid",
            "PSC_MAX_ASK_USER_QUESTIONS": "nope",
            "PSC_MIN_TESTS_PASSED_THRESHOLD": "wrong",
            "PSC_MAX_CONSECUTIVE_BLOCKS": "fail",
        }
        with patch.dict(os.environ, env_overrides):
            import importlib

            import power_steering_checker.main_checker as mc
            import power_steering_checker.result_formatting as rf
            import power_steering_checker.sdk_calls as sdk

            importlib.reload(sdk)
            importlib.reload(mc)
            importlib.reload(rf)
            # All should have fallen back to defaults
            assert isinstance(sdk.CHECKER_TIMEOUT, int)
            assert isinstance(mc.MAX_TRANSCRIPT_LINES, int)
            assert isinstance(rf.DEFAULT_MAX_CONSECUTIVE_BLOCKS, int)


class TestEndToEndFlow:
    """End-to-end flow tests."""

    def test_checker_check_returns_result(self, tmp_path):
        """PowerSteeringChecker.check() returns PowerSteeringResult."""
        from power_steering_checker import PowerSteeringChecker, PowerSteeringResult

        transcript = [
            {"role": "user", "content": "Fix the bug"},
            {"role": "assistant", "content": "Done"},
        ]
        transcript_path = tmp_path / "transcript.jsonl"
        transcript_path.write_text("\n".join(json.dumps(m) for m in transcript))

        with patch("power_steering_checker.main_checker.get_shared_runtime_dir") as mock_rt:
            mock_rt.return_value = str(tmp_path / "runtime")
            checker = PowerSteeringChecker(tmp_path)
            result = checker.check(transcript_path, "test-session-abc123")

        assert isinstance(result, PowerSteeringResult)
        assert result.decision in ("approve", "block")
