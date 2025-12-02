"""Tests for retry module."""

import pytest

from amplihack.api_client.exceptions import RetryExhaustedError
from amplihack.api_client.retry import RetryHandler


def test_retry_success_first_attempt():
    """Test successful execution on first attempt."""
    retry = RetryHandler(max_retries=3, backoff=0.01)

    result = retry.execute(lambda: "success")
    assert result == "success"


def test_retry_success_after_failures():
    """Test successful execution after transient failures."""
    retry = RetryHandler(max_retries=3, backoff=0.01)

    counter = {"count": 0}

    def flaky_func():
        counter["count"] += 1
        if counter["count"] < 3:
            raise ValueError("Temporary error")
        return "success"

    result = retry.execute(flaky_func, retry_on=(ValueError,))
    assert result == "success"
    assert counter["count"] == 3


def test_retry_exhaustion():
    """Test retry exhaustion after max attempts."""
    retry = RetryHandler(max_retries=2, backoff=0.01)

    counter = {"count": 0}

    def always_fails():
        counter["count"] += 1
        raise ValueError("Permanent error")

    with pytest.raises(RetryExhaustedError) as exc_info:
        retry.execute(always_fails, retry_on=(ValueError,))

    assert exc_info.value.attempts == 3  # max_retries=2 means 3 total attempts
    assert counter["count"] == 3


def test_retry_with_args_kwargs():
    """Test retry with function arguments."""
    retry = RetryHandler(max_retries=1, backoff=0.01)

    def func_with_args(a, b, c=None):
        return f"{a}-{b}-{c}"

    result = retry.execute(func_with_args, "x", "y", c="z")
    assert result == "x-y-z"


def test_retry_selective_exceptions():
    """Test retry only on specified exceptions."""
    retry = RetryHandler(max_retries=2, backoff=0.01)

    def raises_type_error():
        raise TypeError("Not retryable")

    # TypeError not in retry_on, should raise immediately
    with pytest.raises(TypeError, match="Not retryable"):
        retry.execute(raises_type_error, retry_on=(ValueError,))
