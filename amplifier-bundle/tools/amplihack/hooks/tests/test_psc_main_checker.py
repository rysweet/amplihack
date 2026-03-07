# File: amplifier-bundle/tools/amplihack/hooks/tests/test_psc_main_checker.py
"""Tests for power_steering_checker.main_checker module.

Tests module constants, PowerSteeringChecker init,
_is_disabled(), check(), check_session(), is_disabled(),
and fail-open with exc_info.
"""

import json
import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker.considerations import PowerSteeringResult
from power_steering_checker.main_checker import (
    MAX_ASK_USER_QUESTIONS,
    MAX_TRANSCRIPT_LINES,
    MIN_TESTS_PASSED_THRESHOLD,
    PowerSteeringChecker,
    _env_int,
    check_session,
    is_disabled,
)


class TestEnvIntMainChecker:
    """Tests for _env_int() in main_checker (REQ-SEC-2)."""

    def test_env_int_exists(self):
        assert callable(_env_int)

    def test_returns_default_on_invalid(self):
        with patch.dict(os.environ, {"PSC_TEST_MC": "notanumber"}):
            result = _env_int("PSC_TEST_MC", 50)
        assert result == 50

    def test_returns_parsed_on_valid(self):
        with patch.dict(os.environ, {"PSC_TEST_MC": "77"}):
            result = _env_int("PSC_TEST_MC", 50)
        assert result == 77

    def test_does_not_raise_on_invalid(self):
        """REQ-SEC-2: Must not crash the module on invalid env var."""
        with patch.dict(os.environ, {"PSC_TEST_MC": "foo"}):
            result = _env_int("PSC_TEST_MC", 42)
        assert result == 42


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_max_transcript_lines_is_int(self):
        assert isinstance(MAX_TRANSCRIPT_LINES, int)

    def test_max_transcript_lines_positive(self):
        assert MAX_TRANSCRIPT_LINES > 0

    def test_max_transcript_lines_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PSC_MAX_TRANSCRIPT_LINES", None)
            import importlib

            import power_steering_checker.main_checker as m

            importlib.reload(m)
            assert m.MAX_TRANSCRIPT_LINES == 50000

    def test_max_transcript_lines_falls_back_on_invalid(self):
        """REQ-SEC-2: Invalid PSC_MAX_TRANSCRIPT_LINES must fall back."""
        with patch.dict(os.environ, {"PSC_MAX_TRANSCRIPT_LINES": "badvalue"}):
            import importlib

            import power_steering_checker.main_checker as m

            importlib.reload(m)
            assert m.MAX_TRANSCRIPT_LINES == 50000

    def test_max_ask_user_questions_is_int(self):
        assert isinstance(MAX_ASK_USER_QUESTIONS, int)

    def test_max_ask_user_questions_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PSC_MAX_ASK_USER_QUESTIONS", None)
            import importlib

            import power_steering_checker.main_checker as m

            importlib.reload(m)
            assert m.MAX_ASK_USER_QUESTIONS == 3

    def test_min_tests_passed_threshold_is_int(self):
        assert isinstance(MIN_TESTS_PASSED_THRESHOLD, int)

    def test_min_tests_passed_threshold_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PSC_MIN_TESTS_PASSED_THRESHOLD", None)
            import importlib

            import power_steering_checker.main_checker as m

            importlib.reload(m)
            assert m.MIN_TESTS_PASSED_THRESHOLD == 10


class TestPowerSteeringCheckerInit:
    """Tests for PowerSteeringChecker initialization."""

    def test_can_instantiate(self, tmp_path):
        with patch("power_steering_checker.main_checker.get_shared_runtime_dir") as mock_rt:
            mock_rt.return_value = str(tmp_path / "runtime")
            checker = PowerSteeringChecker(tmp_path)
        assert checker is not None

    def test_has_runtime_dir(self, tmp_path):
        with patch("power_steering_checker.main_checker.get_shared_runtime_dir") as mock_rt:
            mock_rt.return_value = str(tmp_path / "runtime")
            checker = PowerSteeringChecker(tmp_path)
        assert hasattr(checker, "runtime_dir")

    def test_has_project_root(self, tmp_path):
        with patch("power_steering_checker.main_checker.get_shared_runtime_dir") as mock_rt:
            mock_rt.return_value = str(tmp_path / "runtime")
            checker = PowerSteeringChecker(tmp_path)
        assert hasattr(checker, "project_root")

    def test_has_considerations(self, tmp_path):
        with patch("power_steering_checker.main_checker.get_shared_runtime_dir") as mock_rt:
            mock_rt.return_value = str(tmp_path / "runtime")
            checker = PowerSteeringChecker(tmp_path)
        assert hasattr(checker, "considerations")


class TestIsDisabledModule:
    """Tests for is_disabled() module-level function."""

    def test_returns_bool(self, tmp_path):
        with patch("power_steering_checker.main_checker.get_shared_runtime_dir") as mock_rt:
            mock_rt.return_value = str(tmp_path / "runtime")
            result = is_disabled(tmp_path)
        assert isinstance(result, bool)

    def test_returns_false_when_not_disabled(self, tmp_path):
        with patch("power_steering_checker.main_checker.get_shared_runtime_dir") as mock_rt:
            mock_rt.return_value = str(tmp_path / "runtime")
            result = is_disabled(tmp_path)
        assert result is False

    def test_fail_open_returns_false_on_checker_error(self, tmp_path):
        """If checker creation fails, is_disabled returns False (fail-open)."""
        with patch(
            "power_steering_checker.main_checker.PowerSteeringChecker",
            side_effect=RuntimeError("test error"),
        ):
            result = is_disabled(tmp_path)
        assert result is False

    def test_fail_open_logs_warning_with_exc_info(self, tmp_path, caplog):
        """REQ: fail-open exception must log at WARNING with exc_info=True."""
        with caplog.at_level(logging.WARNING):
            with patch(
                "power_steering_checker.main_checker.PowerSteeringChecker",
                side_effect=RuntimeError("test error"),
            ):
                is_disabled(tmp_path)
        assert any(
            "test error" in record.message or "not disabled" in record.message
            for record in caplog.records
        )


class TestCheckSession:
    """Tests for check_session() module-level function."""

    def test_returns_power_steering_result(self, tmp_path):
        transcript = [{"role": "user", "content": "Hello"}]
        transcript_path = tmp_path / "transcript.jsonl"
        transcript_path.write_text("\n".join(json.dumps(m) for m in transcript))

        with patch("power_steering_checker.main_checker.get_shared_runtime_dir") as mock_rt:
            mock_rt.return_value = str(tmp_path / "runtime")
            # Mock the check to avoid actual SDK calls
            with patch.object(PowerSteeringChecker, "check") as mock_check:
                mock_check.return_value = PowerSteeringResult(decision="approve", reasons=["test"])
                result = check_session(transcript_path, "session123", tmp_path)
        assert isinstance(result, PowerSteeringResult)


class TestCheckFailOpen:
    """Tests for fail-open behavior in check() method."""

    def test_check_returns_approve_on_error(self, tmp_path):
        """If check() encounters an error, it fail-opens with approve."""
        with patch("power_steering_checker.main_checker.get_shared_runtime_dir") as mock_rt:
            mock_rt.return_value = str(tmp_path / "runtime")
            checker = PowerSteeringChecker(tmp_path)

        transcript = [{"role": "user", "content": "Hello"}]
        transcript_path = tmp_path / "transcript.jsonl"
        transcript_path.write_text("\n".join(json.dumps(m) for m in transcript))

        # Patch inner analysis to raise an error to trigger fail-open
        with patch.object(checker, "detect_session_type", side_effect=RuntimeError("force error")):
            result = checker.check(transcript_path, "session-test-123")

        assert result.decision == "approve"
        assert "error_failopen" in result.reasons
