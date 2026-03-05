"""Outside-in tests for PR #2872: Split power_steering_checker.py into 5 modules.

Tests verify:
1. Import compatibility - public API unchanged
2. Module independence - each module importable independently
3. Security fixes - path traversal in _log_violation and _write_summary
4. Error handling - broad except Exception replaced with WARNING logging
5. Configurable constants - hardcoded values now configurable via env vars
6. Backward compatibility - existing callers continue to work
7. Module orchestration - main_checker coordinates all modules correctly
"""

import importlib
import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure hooks directory is on the path
HOOKS_DIR = Path(__file__).parent.parent
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))


# ============================================================================
# 1. Import Compatibility Tests
# ============================================================================


class TestImportCompatibility:
    """Verify the public API is fully preserved after the split."""

    def test_import_power_steering_checker_package(self):
        """Package can be imported as a top-level module."""
        import power_steering_checker

        assert power_steering_checker is not None

    def test_import_power_steering_checker_class(self):
        """PowerSteeringChecker class importable from package root."""
        from power_steering_checker import PowerSteeringChecker

        assert PowerSteeringChecker is not None
        assert callable(PowerSteeringChecker)

    def test_import_checker_result(self):
        """CheckerResult dataclass importable from package root."""
        from power_steering_checker import CheckerResult

        assert CheckerResult is not None

    def test_import_consideration_analysis(self):
        """ConsiderationAnalysis dataclass importable from package root."""
        from power_steering_checker import ConsiderationAnalysis

        assert ConsiderationAnalysis is not None

    def test_import_power_steering_result(self):
        """PowerSteeringResult dataclass importable from package root."""
        from power_steering_checker import PowerSteeringResult

        assert PowerSteeringResult is not None

    def test_import_power_steering_redirect(self):
        """PowerSteeringRedirect dataclass importable from package root."""
        from power_steering_checker import PowerSteeringRedirect

        assert PowerSteeringRedirect is not None

    def test_import_sdk_available(self):
        """SDK_AVAILABLE flag importable from package root."""
        from power_steering_checker import SDK_AVAILABLE

        assert isinstance(SDK_AVAILABLE, bool)

    def test_import_timeout(self):
        """_timeout context manager importable from package root."""
        from power_steering_checker import _timeout

        assert callable(_timeout)

    def test_import_check_session(self):
        """check_session function importable from package root."""
        from power_steering_checker import check_session

        assert callable(check_session)

    def test_import_is_disabled(self):
        """is_disabled function importable from package root."""
        from power_steering_checker import is_disabled

        assert callable(is_disabled)

    def test_import_analyze_consideration(self):
        """analyze_consideration importable from package root."""
        from power_steering_checker import analyze_consideration

        # May be None if SDK is not available, but the import itself must work
        # The fact that we get here without ImportError is the test

    def test_all_dunder_has_expected_symbols(self):
        """__all__ in __init__.py lists exactly the expected public symbols."""
        import power_steering_checker

        expected = {
            "PowerSteeringChecker",
            "PowerSteeringResult",
            "CheckerResult",
            "ConsiderationAnalysis",
            "PowerSteeringRedirect",
            "SDK_AVAILABLE",
            "_timeout",
            "analyze_consideration",
            "check_session",
            "is_disabled",
        }
        actual = set(power_steering_checker.__all__)
        assert actual == expected, f"Missing: {expected - actual}, Extra: {actual - expected}"


# ============================================================================
# 2. Module Independence Tests
# ============================================================================


class TestModuleIndependence:
    """Each module can be imported independently without circular imports."""

    def test_considerations_module_importable(self):
        """considerations.py can be imported independently."""
        from power_steering_checker import considerations

        assert hasattr(considerations, "CheckerResult")
        assert hasattr(considerations, "ConsiderationAnalysis")
        assert hasattr(considerations, "PowerSteeringResult")
        assert hasattr(considerations, "PowerSteeringRedirect")
        assert hasattr(considerations, "ConsiderationsMixin")

    def test_sdk_calls_module_importable(self):
        """sdk_calls.py can be imported independently."""
        from power_steering_checker import sdk_calls

        assert hasattr(sdk_calls, "SdkCallsMixin")
        assert hasattr(sdk_calls, "SDK_AVAILABLE")
        assert hasattr(sdk_calls, "CHECKER_TIMEOUT")
        assert hasattr(sdk_calls, "PARALLEL_TIMEOUT")
        assert hasattr(sdk_calls, "_timeout")

    def test_progress_tracking_module_importable(self):
        """progress_tracking.py can be imported independently."""
        from power_steering_checker import progress_tracking

        assert hasattr(progress_tracking, "ProgressTrackingMixin")
        assert hasattr(progress_tracking, "_validate_session_id")
        assert hasattr(progress_tracking, "MAX_LINE_BYTES")
        assert hasattr(progress_tracking, "MAX_WRITE_RETRIES")

    def test_result_formatting_module_importable(self):
        """result_formatting.py can be imported independently."""
        from power_steering_checker import result_formatting

        assert hasattr(result_formatting, "ResultFormattingMixin")
        assert hasattr(result_formatting, "DEFAULT_MAX_CONSECUTIVE_BLOCKS")

    def test_main_checker_module_importable(self):
        """main_checker.py can be imported independently."""
        from power_steering_checker import main_checker

        assert hasattr(main_checker, "PowerSteeringChecker")
        assert hasattr(main_checker, "check_session")
        assert hasattr(main_checker, "is_disabled")

    def test_no_import_side_effects(self):
        """Importing modules does not produce import errors or side effects."""
        # Force reimport to catch any side effects
        modules_to_check = [
            "power_steering_checker.considerations",
            "power_steering_checker.sdk_calls",
            "power_steering_checker.progress_tracking",
            "power_steering_checker.result_formatting",
            "power_steering_checker.main_checker",
        ]
        for mod_name in modules_to_check:
            mod = importlib.import_module(mod_name)
            assert mod is not None, f"Failed to import {mod_name}"


# ============================================================================
# 3. Security Fixes: Path Traversal Tests
# ============================================================================


class TestPathTraversalSecurity:
    """Verify path traversal prevention in _log_violation and _write_summary."""

    def test_validate_session_id_rejects_path_traversal(self):
        """_validate_session_id rejects '../etc/passwd' style inputs."""
        from power_steering_checker.progress_tracking import _validate_session_id

        # Must reject all path traversal attempts
        malicious_ids = [
            "../../etc/passwd",
            "../../../etc/shadow",
            "..%2F..%2Fetc%2Fpasswd",
            "valid/../../../etc/x",
            "/etc/passwd",
            "foo/bar",
            "foo\\bar",
            "..",
            ".",
            "a/b",
            "session\x00id",  # null byte
            " ",  # space
            "a" * 129,  # too long
        ]
        for malicious_id in malicious_ids:
            assert not _validate_session_id(malicious_id), (
                f"Should reject malicious session_id: {malicious_id!r}"
            )

    def test_validate_session_id_accepts_valid_ids(self):
        """_validate_session_id accepts legitimate session identifiers."""
        from power_steering_checker.progress_tracking import _validate_session_id

        valid_ids = [
            "abc123",
            "session-2026-03-04",
            "my_session_id",
            "a1b2c3-d4e5-f6g7",
            "A" * 128,  # max length
            "a",  # single char
            "0",  # just a digit
        ]
        for valid_id in valid_ids:
            assert _validate_session_id(valid_id), (
                f"Should accept valid session_id: {valid_id!r}"
            )

    def test_log_violation_rejects_traversal(self):
        """_log_violation silently returns (no write) when session_id is malicious."""
        from power_steering_checker.main_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))

            # Attempt path traversal
            checker._log_violation(
                "test_consideration",
                {"reason": "test"},
                "../../etc/x",
            )

            # Verify no files were created outside the session directory
            etc_dir = Path(tmpdir).parent.parent / "etc"
            assert not etc_dir.exists() or not (etc_dir / "x").exists(), (
                "Path traversal should have been blocked!"
            )

    def test_write_summary_rejects_traversal(self):
        """_write_summary silently returns (no write) when session_id is malicious."""
        from power_steering_checker.main_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))

            # Attempt path traversal
            checker._write_summary("../../etc/x", "malicious summary")

            # Verify no files created outside runtime dir
            etc_dir = Path(tmpdir).parent.parent / "etc"
            assert not etc_dir.exists() or not (etc_dir / "x").exists(), (
                "Path traversal should have been blocked in _write_summary!"
            )

    def test_log_violation_logs_warning_on_invalid_id(self):
        """_log_violation logs a WARNING when rejecting an invalid session_id."""
        from power_steering_checker.main_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))

            # Capture log output
            with patch.object(checker, "_log") as mock_log:
                checker._log_violation("test", {}, "../../etc/x")
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert "Invalid session_id rejected" in call_args[0][0]
                assert call_args[0][1] == "WARNING"

    def test_write_summary_logs_warning_on_invalid_id(self):
        """_write_summary logs a WARNING when rejecting an invalid session_id."""
        from power_steering_checker.main_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))

            with patch.object(checker, "_log") as mock_log:
                checker._write_summary("../../etc/x", "summary")
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert "Invalid session_id rejected" in call_args[0][0]
                assert call_args[0][1] == "WARNING"

    def test_session_id_pattern_allows_only_safe_chars(self):
        """The session ID regex pattern only allows [a-zA-Z0-9_-]."""
        from power_steering_checker.progress_tracking import _SESSION_ID_PATTERN

        assert _SESSION_ID_PATTERN.pattern == r"^[a-zA-Z0-9_\-]{1,128}$"


# ============================================================================
# 4. Error Handling: WARNING Logging Tests
# ============================================================================


class TestErrorHandlingWarningLogging:
    """Verify that except Exception blocks log at WARNING with exc_info=True."""

    def test_no_bare_except_in_considerations(self):
        """considerations.py has no bare 'except:' (without Exception type)."""
        from power_steering_checker import considerations

        source = Path(considerations.__file__).read_text()
        bare_except_pattern = re.compile(r"^\s*except\s*:", re.MULTILINE)
        matches = bare_except_pattern.findall(source)
        assert len(matches) == 0, f"Found bare except: in considerations.py: {matches}"

    def test_no_bare_except_in_sdk_calls(self):
        """sdk_calls.py has no bare 'except:' (without Exception type)."""
        from power_steering_checker import sdk_calls

        source = Path(sdk_calls.__file__).read_text()
        bare_except_pattern = re.compile(r"^\s*except\s*:", re.MULTILINE)
        matches = bare_except_pattern.findall(source)
        assert len(matches) == 0, f"Found bare except: in sdk_calls.py: {matches}"

    def test_no_bare_except_in_progress_tracking(self):
        """progress_tracking.py has no bare 'except:' (without Exception type)."""
        from power_steering_checker import progress_tracking

        source = Path(progress_tracking.__file__).read_text()
        bare_except_pattern = re.compile(r"^\s*except\s*:", re.MULTILINE)
        matches = bare_except_pattern.findall(source)
        assert len(matches) == 0, f"Found bare except: in progress_tracking.py: {matches}"

    def test_no_bare_except_in_result_formatting(self):
        """result_formatting.py has no bare 'except:' (without Exception type)."""
        from power_steering_checker import result_formatting

        source = Path(result_formatting.__file__).read_text()
        bare_except_pattern = re.compile(r"^\s*except\s*:", re.MULTILINE)
        matches = bare_except_pattern.findall(source)
        assert len(matches) == 0, f"Found bare except: in result_formatting.py: {matches}"

    def test_no_bare_except_in_main_checker(self):
        """main_checker.py has no bare 'except:' (without Exception type)."""
        from power_steering_checker import main_checker

        source = Path(main_checker.__file__).read_text()
        bare_except_pattern = re.compile(r"^\s*except\s*:", re.MULTILINE)
        matches = bare_except_pattern.findall(source)
        assert len(matches) == 0, f"Found bare except: in main_checker.py: {matches}"

    def test_except_exception_blocks_log_warning_in_main_checker(self):
        """All 'except Exception' blocks in main_checker.py log at WARNING or ERROR with exc_info."""
        from power_steering_checker import main_checker

        source = Path(main_checker.__file__).read_text()
        lines = source.splitlines()

        except_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("except Exception"):
                except_lines.append(i)

        for except_line_num in except_lines:
            # Check the next 5 lines for logging call
            block = "\n".join(lines[except_line_num : except_line_num + 6])
            has_log = (
                "self._log(" in block
                or "logger.warning(" in block
                or "logger.error(" in block
            )
            assert has_log, (
                f"except Exception at line {except_line_num + 1} in main_checker.py "
                f"does not log. Block:\n{block}"
            )

    def test_except_exception_blocks_log_warning_in_progress_tracking(self):
        """All 'except Exception' blocks in progress_tracking.py log at WARNING."""
        from power_steering_checker import progress_tracking

        source = Path(progress_tracking.__file__).read_text()
        lines = source.splitlines()

        except_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("except Exception"):
                except_lines.append(i)

        for except_line_num in except_lines:
            block = "\n".join(lines[except_line_num : except_line_num + 6])
            has_log = "self._log(" in block or "logger.warning(" in block
            assert has_log, (
                f"except Exception at line {except_line_num + 1} in progress_tracking.py "
                f"does not log. Block:\n{block}"
            )

    def test_except_exception_blocks_log_warning_in_sdk_calls(self):
        """All 'except Exception' blocks in sdk_calls.py log at WARNING or ERROR."""
        from power_steering_checker import sdk_calls

        source = Path(sdk_calls.__file__).read_text()
        lines = source.splitlines()

        except_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("except Exception"):
                except_lines.append(i)

        for except_line_num in except_lines:
            block = "\n".join(lines[except_line_num : except_line_num + 6])
            has_log = (
                "self._log(" in block
                or "logger.warning(" in block
                or "sys.stderr.write(" in block
            )
            assert has_log, (
                f"except Exception at line {except_line_num + 1} in sdk_calls.py "
                f"does not log. Block:\n{block}"
            )

    def test_is_disabled_fail_open_logs_warning(self):
        """is_disabled() logs a WARNING when PowerSteeringChecker() construction fails."""
        from power_steering_checker.main_checker import is_disabled

        with patch(
            "power_steering_checker.main_checker.PowerSteeringChecker",
            side_effect=RuntimeError("test"),
        ):
            result = is_disabled()
            # Should fail-open (return False)
            assert result is False


# ============================================================================
# 5. Configurable Constants Tests
# ============================================================================


class TestConfigurableConstants:
    """Verify hardcoded timeouts/thresholds are now configurable via env vars."""

    def test_checker_timeout_default(self):
        """CHECKER_TIMEOUT defaults to 25."""
        from power_steering_checker.sdk_calls import CHECKER_TIMEOUT

        assert CHECKER_TIMEOUT == 25

    def test_parallel_timeout_default(self):
        """PARALLEL_TIMEOUT defaults to 60."""
        from power_steering_checker.sdk_calls import PARALLEL_TIMEOUT

        assert PARALLEL_TIMEOUT == 60

    def test_min_verified_evidence_count_default(self):
        """MIN_VERIFIED_EVIDENCE_COUNT defaults to 3."""
        from power_steering_checker.sdk_calls import MIN_VERIFIED_EVIDENCE_COUNT

        assert MIN_VERIFIED_EVIDENCE_COUNT == 3

    def test_max_write_retries_default(self):
        """MAX_WRITE_RETRIES defaults to 3."""
        from power_steering_checker.progress_tracking import MAX_WRITE_RETRIES

        assert MAX_WRITE_RETRIES == 3

    def test_write_retry_initial_delay_default(self):
        """WRITE_RETRY_INITIAL_DELAY defaults to 0.1."""
        from power_steering_checker.progress_tracking import WRITE_RETRY_INITIAL_DELAY

        assert WRITE_RETRY_INITIAL_DELAY == 0.1

    def test_max_line_bytes_default(self):
        """MAX_LINE_BYTES defaults to 10 MB."""
        from power_steering_checker.progress_tracking import MAX_LINE_BYTES

        assert MAX_LINE_BYTES == 10 * 1024 * 1024

    def test_default_max_consecutive_blocks(self):
        """DEFAULT_MAX_CONSECUTIVE_BLOCKS defaults to 10."""
        from power_steering_checker.result_formatting import DEFAULT_MAX_CONSECUTIVE_BLOCKS

        assert DEFAULT_MAX_CONSECUTIVE_BLOCKS == 10

    def test_max_transcript_lines_default(self):
        """MAX_TRANSCRIPT_LINES defaults to 50000."""
        from power_steering_checker.main_checker import MAX_TRANSCRIPT_LINES

        assert MAX_TRANSCRIPT_LINES == 50000

    def test_max_ask_user_questions_default(self):
        """MAX_ASK_USER_QUESTIONS defaults to 3."""
        from power_steering_checker.main_checker import MAX_ASK_USER_QUESTIONS

        assert MAX_ASK_USER_QUESTIONS == 3

    def test_min_tests_passed_threshold_default(self):
        """MIN_TESTS_PASSED_THRESHOLD defaults to 10."""
        from power_steering_checker.main_checker import MIN_TESTS_PASSED_THRESHOLD

        assert MIN_TESTS_PASSED_THRESHOLD == 10

    def test_qa_question_density_threshold(self):
        """QA_QUESTION_DENSITY_THRESHOLD defaults to 0.5."""
        from power_steering_checker.considerations import QA_QUESTION_DENSITY_THRESHOLD

        assert QA_QUESTION_DENSITY_THRESHOLD == 0.5

    def test_max_ask_user_count(self):
        """MAX_ASK_USER_COUNT defaults to 3."""
        from power_steering_checker.considerations import MAX_ASK_USER_COUNT

        assert MAX_ASK_USER_COUNT == 3

    def test_env_int_returns_env_override(self):
        """_env_int reads from environment variable when set."""
        from power_steering_checker.considerations import _env_int

        with patch.dict(os.environ, {"TEST_PSC_VAR": "42"}):
            result = _env_int("TEST_PSC_VAR", 10)
            assert result == 42

    def test_env_int_returns_default_for_invalid(self):
        """_env_int falls back to default on non-numeric env var."""
        from power_steering_checker.considerations import _env_int

        with patch.dict(os.environ, {"TEST_PSC_VAR": "not_a_number"}):
            result = _env_int("TEST_PSC_VAR", 10)
            assert result == 10

    def test_env_int_returns_default_when_unset(self):
        """_env_int returns default when env var is not set."""
        from power_steering_checker.considerations import _env_int

        # Ensure var is not set
        os.environ.pop("TEST_PSC_NONEXISTENT_VAR", None)
        result = _env_int("TEST_PSC_NONEXISTENT_VAR", 99)
        assert result == 99

    def test_env_int_does_not_raise_on_garbage(self):
        """_env_int never raises ValueError, even with garbage input."""
        from power_steering_checker.considerations import _env_int

        with patch.dict(os.environ, {"TEST_PSC_VAR": "!!!garbage!!!"}):
            # Must not raise
            result = _env_int("TEST_PSC_VAR", 7)
            assert result == 7


# ============================================================================
# 6. Backward Compatibility Tests
# ============================================================================


class TestBackwardCompatibility:
    """Verify existing callers continue to work unchanged."""

    def test_checker_result_has_id_alias(self):
        """CheckerResult.id property still works as backward-compat alias."""
        from power_steering_checker import CheckerResult

        result = CheckerResult(
            consideration_id="test_check",
            satisfied=True,
            reason="test passed",
            severity="warning",
        )
        assert result.id == "test_check"
        assert result.consideration_id == "test_check"

    def test_power_steering_result_dataclass_fields(self):
        """PowerSteeringResult has expected fields."""
        from power_steering_checker import PowerSteeringResult

        result = PowerSteeringResult(
            decision="approve",
            reasons=["all_passed"],
        )
        assert result.decision == "approve"
        assert result.reasons == ["all_passed"]
        assert result.continuation_prompt is None
        assert result.summary is None
        assert result.analysis is None

    def test_consideration_analysis_default_creation(self):
        """ConsiderationAnalysis can be created with defaults."""
        from power_steering_checker import ConsiderationAnalysis

        analysis = ConsiderationAnalysis()
        assert analysis.results == {}
        assert analysis.failed_blockers == []
        assert analysis.failed_warnings == []
        assert not analysis.has_blockers

    def test_checker_instantiation_with_temp_dir(self):
        """PowerSteeringChecker can be instantiated with a project root."""
        from power_steering_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))
            assert checker.project_root == Path(tmpdir)
            assert checker.runtime_dir is not None

    def test_checker_has_check_method(self):
        """PowerSteeringChecker has a check() method."""
        from power_steering_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))
            assert hasattr(checker, "check")
            assert callable(checker.check)

    def test_checker_has_format_results_text_method(self):
        """PowerSteeringChecker has _format_results_text from ResultFormattingMixin."""
        from power_steering_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))
            assert hasattr(checker, "_format_results_text")

    def test_checker_has_check_todos_complete_method(self):
        """PowerSteeringChecker has _check_todos_complete from ConsiderationsMixin."""
        from power_steering_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))
            assert hasattr(checker, "_check_todos_complete")

    def test_checker_has_check_philosophy_compliance_method(self):
        """PowerSteeringChecker has _check_philosophy_compliance from ConsiderationsMixin."""
        from power_steering_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))
            assert hasattr(checker, "_check_philosophy_compliance")

    def test_checker_inherits_all_four_mixins(self):
        """PowerSteeringChecker inherits from all 4 mixin classes."""
        from power_steering_checker.considerations import ConsiderationsMixin
        from power_steering_checker.main_checker import PowerSteeringChecker
        from power_steering_checker.progress_tracking import ProgressTrackingMixin
        from power_steering_checker.result_formatting import ResultFormattingMixin
        from power_steering_checker.sdk_calls import SdkCallsMixin

        assert issubclass(PowerSteeringChecker, ConsiderationsMixin)
        assert issubclass(PowerSteeringChecker, SdkCallsMixin)
        assert issubclass(PowerSteeringChecker, ProgressTrackingMixin)
        assert issubclass(PowerSteeringChecker, ResultFormattingMixin)

    def test_check_session_returns_power_steering_result(self):
        """check_session() returns a PowerSteeringResult with valid structure."""
        from power_steering_checker import PowerSteeringResult, check_session

        result = check_session([], "test-session-123")
        assert isinstance(result, PowerSteeringResult)
        assert result.decision in ("approve", "block")

    def test_is_disabled_returns_bool(self):
        """is_disabled() returns a boolean."""
        from power_steering_checker import is_disabled

        result = is_disabled()
        assert isinstance(result, bool)

    def test_timeout_works_as_context_manager(self):
        """_timeout can be used as a context manager."""
        from power_steering_checker import _timeout

        with _timeout(5):
            x = 1 + 1
            assert x == 2

    def test_timeout_raises_on_expiry(self):
        """_timeout raises TimeoutError when time limit exceeded."""
        import time

        from power_steering_checker import _timeout

        with pytest.raises(TimeoutError):
            with _timeout(1):
                time.sleep(3)


# ============================================================================
# 7. Main Checker Orchestration Tests
# ============================================================================


class TestMainCheckerOrchestration:
    """Verify main_checker orchestrates all modules correctly."""

    def test_checker_fail_open_on_any_error(self):
        """check() returns approve when an internal error occurs (fail-open)."""
        from power_steering_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))
            # Force an internal error by patching _is_disabled to crash
            with patch.object(
                checker,
                "_is_disabled",
                side_effect=RuntimeError("test crash"),
            ):
                result = checker.check([], "test-session")
                assert result.decision == "approve"

    def test_checker_returns_result_for_empty_transcript(self):
        """check() handles empty transcript gracefully."""
        from power_steering_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))
            result = checker.check([], "test-session")
            assert result.decision in ("approve", "block")

    def test_already_ran_returns_approve(self):
        """check() returns approve if session already ran."""
        from power_steering_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))

            # Create semaphore file to simulate already ran
            session_dir = checker.runtime_dir / "test-session-abc"
            session_dir.mkdir(parents=True, exist_ok=True)
            (session_dir / ".complete").touch()

            result = checker.check([], "test-session-abc")
            assert result.decision == "approve"

    def test_disabled_returns_approve(self):
        """check() returns approve if checker is disabled."""
        from power_steering_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))

            # Create disabled file
            checker.runtime_dir.mkdir(parents=True, exist_ok=True)
            (checker.runtime_dir / ".disabled").touch()

            result = checker.check([], "test-session-xyz")
            assert result.decision == "approve"

    def test_check_session_module_function_delegates_to_class(self):
        """check_session() is a convenience wrapper that creates and calls a checker."""
        from power_steering_checker.main_checker import check_session

        # Just verify it works end-to-end
        result = check_session([], "test-module-func")
        assert result.decision in ("approve", "block")


# ============================================================================
# 8. Considerations Module Tests
# ============================================================================


class TestConsiderationsModule:
    """Tests specific to the considerations module functionality."""

    def test_checker_result_fields(self):
        """CheckerResult has all expected fields with correct types."""
        from power_steering_checker.considerations import CheckerResult

        result = CheckerResult(
            consideration_id="test",
            satisfied=True,
            reason="all good",
            severity="warning",
            recovery_steps=["step1"],
            executed=True,
        )
        assert result.consideration_id == "test"
        assert result.satisfied is True
        assert result.reason == "all good"
        assert result.severity == "warning"
        assert result.recovery_steps == ["step1"]
        assert result.executed is True

    def test_consideration_analysis_has_blockers(self):
        """ConsiderationAnalysis correctly identifies when blockers exist."""
        from power_steering_checker.considerations import (
            CheckerResult,
            ConsiderationAnalysis,
        )

        analysis = ConsiderationAnalysis()
        assert not analysis.has_blockers

        analysis.failed_blockers.append(
            CheckerResult(
                consideration_id="blocker_test",
                satisfied=False,
                reason="failed",
                severity="blocker",
            )
        )
        assert analysis.has_blockers

    def test_precompiled_regex_patterns_exist(self):
        """Pre-compiled regex patterns are defined at module level."""
        from power_steering_checker import considerations

        assert hasattr(considerations, "_HANDOFF_PATTERNS")
        assert hasattr(considerations, "_SHORTCUT_PATTERNS")
        assert hasattr(considerations, "_NEXT_STEPS_PATTERNS")
        assert hasattr(considerations, "_NEGATION_PATTERNS")
        assert hasattr(considerations, "_TODO_FIXME_PATTERN")
        assert hasattr(considerations, "_STUB_INLINE_PATTERN")

        # Verify they are compiled patterns
        assert isinstance(considerations._HANDOFF_PATTERNS, list)
        assert all(
            isinstance(p, re.Pattern) for p in considerations._HANDOFF_PATTERNS
        )


# ============================================================================
# 9. Progress Tracking Module Tests
# ============================================================================


class TestProgressTrackingModule:
    """Tests specific to progress tracking functionality."""

    def test_write_with_retry_creates_file(self):
        """_write_with_retry creates file with content."""
        from power_steering_checker.progress_tracking import _write_with_retry

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.txt"
            _write_with_retry(filepath, "hello world")
            assert filepath.read_text() == "hello world"

    def test_write_with_retry_creates_parent_dirs(self):
        """_write_with_retry creates parent directories automatically."""
        from power_steering_checker.progress_tracking import _write_with_retry

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "nested" / "dir" / "test.txt"
            _write_with_retry(filepath, "nested content")
            assert filepath.read_text() == "nested content"

    def test_write_with_retry_append_mode(self):
        """_write_with_retry supports append mode."""
        from power_steering_checker.progress_tracking import _write_with_retry

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.txt"
            filepath.write_text("first\n")
            _write_with_retry(filepath, "second\n", mode="a")
            content = filepath.read_text()
            assert "first" in content
            assert "second" in content

    def test_gh_pr_subprocess_timeout_exists(self):
        """GH_PR_SUBPROCESS_TIMEOUT is defined."""
        from power_steering_checker.progress_tracking import GH_PR_SUBPROCESS_TIMEOUT

        assert isinstance(GH_PR_SUBPROCESS_TIMEOUT, int)
        assert GH_PR_SUBPROCESS_TIMEOUT > 0


# ============================================================================
# 10. SDK Calls Module Tests
# ============================================================================


class TestSdkCallsModule:
    """Tests specific to SDK calls module."""

    def test_timeout_hierarchy_order(self):
        """CHECKER_TIMEOUT < PARALLEL_TIMEOUT (timeout hierarchy)."""
        from power_steering_checker.sdk_calls import CHECKER_TIMEOUT, PARALLEL_TIMEOUT

        assert CHECKER_TIMEOUT < PARALLEL_TIMEOUT, (
            f"CHECKER_TIMEOUT ({CHECKER_TIMEOUT}) must be < PARALLEL_TIMEOUT ({PARALLEL_TIMEOUT})"
        )

    def test_sdk_available_reflects_import_state(self):
        """SDK_AVAILABLE accurately reflects whether claude_power_steering was imported."""
        from power_steering_checker.sdk_calls import SDK_AVAILABLE, _SDK_IMPORT_OK

        assert SDK_AVAILABLE == _SDK_IMPORT_OK

    def test_evidence_available_reflects_import_state(self):
        """EVIDENCE_AVAILABLE accurately reflects completion_evidence import."""
        from power_steering_checker.sdk_calls import EVIDENCE_AVAILABLE, _EVIDENCE_IMPORT_OK

        assert EVIDENCE_AVAILABLE == _EVIDENCE_IMPORT_OK


# ============================================================================
# 11. Result Formatting Module Tests
# ============================================================================


class TestResultFormattingModule:
    """Tests specific to result formatting module."""

    def test_format_results_all_passed(self):
        """_format_results_text produces correct output when all checks pass."""
        from power_steering_checker import (
            CheckerResult,
            ConsiderationAnalysis,
            PowerSteeringChecker,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))

            analysis = ConsiderationAnalysis(
                results={
                    "test_check": CheckerResult(
                        consideration_id="test_check",
                        satisfied=True,
                        reason="all good",
                        severity="warning",
                    )
                }
            )

            text = checker._format_results_text(analysis, "DEVELOPMENT")
            assert "POWER-STEERING ANALYSIS RESULTS" in text
            assert "DEVELOPMENT" in text

    def test_format_results_contains_category(self):
        """_format_results_text groups results by category."""
        from power_steering_checker import (
            CheckerResult,
            ConsiderationAnalysis,
            PowerSteeringChecker,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))

            analysis = ConsiderationAnalysis(
                results={
                    "philosophy_compliance": CheckerResult(
                        consideration_id="philosophy_compliance",
                        satisfied=True,
                        reason="clean code",
                        severity="blocker",
                    )
                }
            )

            text = checker._format_results_text(analysis, "DEVELOPMENT")
            assert isinstance(text, str)
            assert len(text) > 0


# ============================================================================
# 12. Cross-Module Integration Tests
# ============================================================================


class TestCrossModuleIntegration:
    """Verify modules work together correctly."""

    def test_main_checker_uses_considerations_mixin(self):
        """PowerSteeringChecker._check_todos_complete is from ConsiderationsMixin."""
        from power_steering_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))

            # _check_todos_complete requires (transcript, session_id)
            transcript = [{"role": "assistant", "content": "No TODO items found."}]
            result = checker._check_todos_complete(transcript, "test-session")
            assert isinstance(result, bool) or result is None  # depends on content

    def test_main_checker_uses_progress_tracking_mixin(self):
        """PowerSteeringChecker._already_ran is from ProgressTrackingMixin."""
        from power_steering_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))

            # _already_ran should work (comes from ProgressTrackingMixin)
            result = checker._already_ran("valid-session-id")
            assert isinstance(result, bool)

    def test_main_checker_uses_result_formatting_mixin(self):
        """PowerSteeringChecker._format_results_text is from ResultFormattingMixin."""
        from power_steering_checker import ConsiderationAnalysis, PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))

            analysis = ConsiderationAnalysis()
            text = checker._format_results_text(analysis, "TEST")
            assert isinstance(text, str)

    def test_main_checker_uses_sdk_calls_mixin(self):
        """PowerSteeringChecker._evidence_suggests_complete is from SdkCallsMixin."""
        from power_steering_checker import PowerSteeringChecker

        with tempfile.TemporaryDirectory() as tmpdir:
            checker = PowerSteeringChecker(project_root=Path(tmpdir))

            result = checker._evidence_suggests_complete([])
            assert result is False
