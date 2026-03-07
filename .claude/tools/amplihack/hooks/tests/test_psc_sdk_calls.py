# File: amplifier-bundle/tools/amplihack/hooks/tests/test_psc_sdk_calls.py
"""Tests for power_steering_checker.sdk_calls module.

Tests _timeout, SDK_AVAILABLE, EVIDENCE_AVAILABLE, CHECKER_TIMEOUT,
PARALLEL_TIMEOUT, and _env_int() helper (REQ-SEC-2).
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import SDK_AVAILABLE, _timeout
from power_steering_checker.sdk_calls import (
    CHECKER_TIMEOUT,
    EVIDENCE_AVAILABLE,
    PARALLEL_TIMEOUT,
    _env_int,
)


class TestEnvInt:
    """Tests for _env_int() helper (REQ-SEC-2)."""

    def test_returns_default_when_var_not_set(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PSC_TEST_NONEXISTENT_VAR", None)
            result = _env_int("PSC_TEST_NONEXISTENT_VAR", 42)
        assert result == 42

    def test_returns_parsed_value_when_valid_int(self):
        with patch.dict(os.environ, {"PSC_TEST_INT_VAR": "99"}):
            result = _env_int("PSC_TEST_INT_VAR", 10)
        assert result == 99

    def test_falls_back_to_default_on_non_numeric(self):
        """REQ-SEC-2: Non-numeric env var must not raise ValueError."""
        with patch.dict(os.environ, {"PSC_TEST_INT_VAR": "notanumber"}):
            result = _env_int("PSC_TEST_INT_VAR", 25)
        assert result == 25

    def test_falls_back_on_float_string(self):
        with patch.dict(os.environ, {"PSC_TEST_INT_VAR": "3.14"}):
            result = _env_int("PSC_TEST_INT_VAR", 10)
        assert result == 10

    def test_falls_back_on_empty_string(self):
        with patch.dict(os.environ, {"PSC_TEST_INT_VAR": ""}):
            result = _env_int("PSC_TEST_INT_VAR", 5)
        assert result == 5

    def test_falls_back_on_negative_if_min_set(self):
        """Negative integers are valid unless caller rejects them."""
        with patch.dict(os.environ, {"PSC_TEST_INT_VAR": "-1"}):
            result = _env_int("PSC_TEST_INT_VAR", 10)
        # -1 is a valid integer — should parse successfully
        assert result == -1

    def test_returns_int_type(self):
        with patch.dict(os.environ, {"PSC_TEST_INT_VAR": "7"}):
            result = _env_int("PSC_TEST_INT_VAR", 5)
        assert isinstance(result, int)

    def test_default_is_returned_as_int(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PSC_TEST_NONEXISTENT_VAR", None)
            result = _env_int("PSC_TEST_NONEXISTENT_VAR", 100)
        assert isinstance(result, int)
        assert result == 100


class TestConstants:
    """Tests for module-level constants."""

    def test_checker_timeout_is_int(self):
        assert isinstance(CHECKER_TIMEOUT, int)

    def test_checker_timeout_positive(self):
        assert CHECKER_TIMEOUT > 0

    def test_checker_timeout_default_value(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PSC_CHECKER_TIMEOUT", None)
            # Re-import to test default
            import importlib

            import power_steering_checker.sdk_calls as m

            importlib.reload(m)
            assert m.CHECKER_TIMEOUT == 25

    def test_parallel_timeout_is_int(self):
        assert isinstance(PARALLEL_TIMEOUT, int)

    def test_parallel_timeout_positive(self):
        assert PARALLEL_TIMEOUT > 0

    def test_parallel_timeout_default_value(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PSC_PARALLEL_TIMEOUT", None)
            import importlib

            import power_steering_checker.sdk_calls as m

            importlib.reload(m)
            assert m.PARALLEL_TIMEOUT == 60

    def test_sdk_available_is_bool(self):
        assert isinstance(SDK_AVAILABLE, bool)

    def test_evidence_available_is_bool(self):
        assert isinstance(EVIDENCE_AVAILABLE, bool)


class TestTimeout:
    """Tests for _timeout context manager."""

    def test_timeout_imported_from_package(self):
        """_timeout is re-exported from __init__."""
        from power_steering_checker import _timeout as t

        assert callable(t)

    def test_timeout_is_context_manager(self):
        # _timeout should be a generator function (contextmanager)
        import inspect

        assert inspect.isgeneratorfunction(
            _timeout.__wrapped__ if hasattr(_timeout, "__wrapped__") else _timeout
        )

    def test_timeout_does_not_interrupt_fast_operation(self):
        with _timeout(5):
            x = 1 + 1
        assert x == 2

    def test_timeout_raises_timeout_error(self):
        import time

        with pytest.raises((TimeoutError, Exception)):
            with _timeout(1):
                time.sleep(3)


class TestSdkAvailable:
    """Tests for availability flags."""

    def test_sdk_available_accessible_from_package(self):
        from power_steering_checker import SDK_AVAILABLE as sa

        assert isinstance(sa, bool)

    def test_evidence_available_is_bool_sdk_calls(self):
        from power_steering_checker.sdk_calls import EVIDENCE_AVAILABLE as ea

        assert isinstance(ea, bool)
