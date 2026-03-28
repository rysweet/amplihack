"""Regression tests for the validate_gh_account helper."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import pytest

SCRIPT_PATH = Path("amplifier-bundle/tools/validate_gh_account.py")


def _load_module():
    assert SCRIPT_PATH.exists(), f"Missing helper script: {SCRIPT_PATH}"
    spec = importlib.util.spec_from_file_location("validate_gh_account", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _get_validate_fn(module):
    for name in (
        "validate_gh_account",
        "validate_expected_gh_account",
        "require_expected_gh_account",
    ):
        fn = getattr(module, name, None)
        if callable(fn):
            return fn
    pytest.fail("validate_gh_account.py must expose a callable account-validation helper")


def _call_validate(fn, *, status_output: str, expected_account: str, status_exit_code: int = 0):
    try:
        return fn(status_output, expected_account, status_exit_code)
    except TypeError:
        pass
    try:
        return fn(expected_account, status_output, status_exit_code)
    except TypeError:
        pass

    signature = inspect.signature(fn)
    kwargs = {}
    if "status_output" in signature.parameters:
        kwargs["status_output"] = status_output
    elif "auth_status_output" in signature.parameters:
        kwargs["auth_status_output"] = status_output
    elif "gh_auth_status" in signature.parameters:
        kwargs["gh_auth_status"] = status_output

    if "expected_account" in signature.parameters:
        kwargs["expected_account"] = expected_account
    elif "expected_gh_account" in signature.parameters:
        kwargs["expected_gh_account"] = expected_account
    if "status_exit_code" in signature.parameters:
        kwargs["status_exit_code"] = status_exit_code

    if kwargs:
        return fn(**kwargs)
    raise AssertionError("Could not determine how to call the account-validation helper")


def test_validate_gh_account_script_exists() -> None:
    assert SCRIPT_PATH.exists(), f"Missing helper script: {SCRIPT_PATH}"


def test_accepts_matching_account() -> None:
    module = _load_module()
    validate = _get_validate_fn(module)
    result = _call_validate(
        validate,
        status_output="github.com\n  ✓ Logged in to github.com account rysweet (/tmp/gh)\n",
        expected_account="rysweet",
    )
    if isinstance(result, dict):
        assert result.get("actual") == "rysweet" or result.get("login") == "rysweet"
    else:
        assert result == "rysweet"


def test_rejects_account_mismatch_with_exact_user_visible_message() -> None:
    module = _load_module()
    validate = _get_validate_fn(module)
    with pytest.raises(
        Exception, match=r"GitHub account mismatch: expected rysweet, got someone-else"
    ):
        _call_validate(
            validate,
            status_output="github.com\n  ✓ Logged in to github.com account someone-else (/tmp/gh)\n",
            expected_account="rysweet",
        )


def test_rejects_unauthenticated_state_explicitly() -> None:
    module = _load_module()
    validate = _get_validate_fn(module)
    with pytest.raises(Exception, match=r"(?i)(no github account authenticated|not authenticated)"):
        _call_validate(
            validate,
            status_output="You are not logged into any GitHub hosts. Run gh auth login.\n",
            expected_account="rysweet",
        )


def test_rejects_empty_expected_account_explicitly() -> None:
    module = _load_module()
    validate = _get_validate_fn(module)
    with pytest.raises(Exception, match=r"expected_gh_account"):
        _call_validate(
            validate,
            status_output="github.com\n  ✓ Logged in to github.com account rysweet (/tmp/gh)\n",
            expected_account="",
        )


def test_nonzero_gh_auth_status_still_surfaces_unauthenticated_message() -> None:
    module = _load_module()
    validate = _get_validate_fn(module)
    with pytest.raises(Exception, match=r"(?i)(no github account authenticated|not authenticated)"):
        _call_validate(
            validate,
            status_output="You are not logged into any GitHub hosts. Run gh auth login.\n",
            expected_account="rysweet",
            status_exit_code=1,
        )
