# File: amplifier-bundle/tools/amplihack/hooks/tests/test_psc_result_formatting.py
"""Tests for power_steering_checker.result_formatting module.

Tests DEFAULT_MAX_CONSECUTIVE_BLOCKS, _env_int() usage,
_format_results_text(), _generate_continuation_prompt(), _generate_summary().
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker.considerations import (
    CheckerResult,
    ConsiderationAnalysis,
)
from power_steering_checker.result_formatting import (
    DEFAULT_MAX_CONSECUTIVE_BLOCKS,
    TURN_STATE_AVAILABLE,
    ResultFormattingMixin,
    _env_int,
)


class TestEnvIntResultFormatting:
    """Tests for _env_int() in result_formatting (REQ-SEC-2)."""

    def test_env_int_exists(self):
        assert callable(_env_int)

    def test_returns_default_on_invalid(self):
        with patch.dict(os.environ, {"PSC_TEST_RF": "not_a_number"}):
            result = _env_int("PSC_TEST_RF", 10)
        assert result == 10

    def test_returns_parsed_on_valid(self):
        with patch.dict(os.environ, {"PSC_TEST_RF": "42"}):
            result = _env_int("PSC_TEST_RF", 10)
        assert result == 42


class TestDefaultMaxConsecutiveBlocks:
    """Tests for DEFAULT_MAX_CONSECUTIVE_BLOCKS constant."""

    def test_exists(self):
        assert DEFAULT_MAX_CONSECUTIVE_BLOCKS is not None

    def test_is_int(self):
        assert isinstance(DEFAULT_MAX_CONSECUTIVE_BLOCKS, int)

    def test_default_is_10(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PSC_MAX_CONSECUTIVE_BLOCKS", None)
            import importlib

            import power_steering_checker.result_formatting as m

            importlib.reload(m)
            assert m.DEFAULT_MAX_CONSECUTIVE_BLOCKS == 10

    def test_uses_env_var(self):
        with patch.dict(os.environ, {"PSC_MAX_CONSECUTIVE_BLOCKS": "20"}):
            import importlib

            import power_steering_checker.result_formatting as m

            importlib.reload(m)
            assert m.DEFAULT_MAX_CONSECUTIVE_BLOCKS == 20

    def test_falls_back_on_invalid_env(self):
        """REQ-SEC-2: Non-numeric env var should not crash."""
        with patch.dict(os.environ, {"PSC_MAX_CONSECUTIVE_BLOCKS": "invalid"}):
            import importlib

            import power_steering_checker.result_formatting as m

            importlib.reload(m)
            assert m.DEFAULT_MAX_CONSECUTIVE_BLOCKS == 10


class MockResultFormatter(ResultFormattingMixin):
    """Concrete class for testing ResultFormattingMixin."""

    def __init__(self, considerations=None):
        self.considerations = considerations or []
        self._log_messages = []

    def _log(self, message, level="INFO", exc_info=False):
        self._log_messages.append((level, message))


class TestFormatResultsText:
    """Tests for _format_results_text()."""

    def _make_formatter(self, consideration_ids=None):
        considerations = []
        if consideration_ids:
            for cid in consideration_ids:
                considerations.append(
                    {
                        "id": cid,
                        "name": cid.replace("_", " ").title(),
                        "category": "Test Category",
                    }
                )
        return MockResultFormatter(considerations)

    def test_returns_string(self):
        formatter = self._make_formatter()
        analysis = ConsiderationAnalysis()
        result = formatter._format_results_text(analysis, "SIMPLE")
        assert isinstance(result, str)

    def test_contains_session_type(self):
        formatter = self._make_formatter()
        analysis = ConsiderationAnalysis()
        result = formatter._format_results_text(analysis, "STANDARD")
        assert "STANDARD" in result

    def test_contains_analysis_header(self):
        formatter = self._make_formatter()
        analysis = ConsiderationAnalysis()
        result = formatter._format_results_text(analysis, "SIMPLE")
        assert "POWER-STEERING" in result.upper() or "ANALYSIS" in result.upper()

    def test_shows_passed_checks(self):
        formatter = self._make_formatter(["test_check"])
        analysis = ConsiderationAnalysis()
        analysis.add_result(
            CheckerResult(
                consideration_id="test_check",
                satisfied=True,
                reason="All good",
                severity="blocker",
            )
        )
        result = formatter._format_results_text(analysis, "SIMPLE")
        assert isinstance(result, str)

    def test_shows_failed_checks(self):
        formatter = self._make_formatter(["test_check"])
        analysis = ConsiderationAnalysis()
        analysis.add_result(
            CheckerResult(
                consideration_id="test_check",
                satisfied=False,
                reason="Failed",
                severity="blocker",
            )
        )
        result = formatter._format_results_text(analysis, "SIMPLE")
        assert isinstance(result, str)


class TestTurnStateAvailable:
    """Tests for TURN_STATE_AVAILABLE flag."""

    def test_is_bool(self):
        assert isinstance(TURN_STATE_AVAILABLE, bool)
