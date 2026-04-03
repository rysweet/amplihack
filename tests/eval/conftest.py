"""Shared fixtures for eval tests."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def mock_anthropic_api_key(monkeypatch):
    """Set a dummy ANTHROPIC_API_KEY for tests that mock the Anthropic client.

    Most eval tests patch anthropic.Anthropic directly, so the real key is
    never used. This fixture ensures the env var check in grader.py passes
    without requiring a real API key in CI.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        monkeypatch.setenv(
            "ANTHROPIC_API_KEY", "test-key-for-unit-tests"
        )  # pragma: allowlist secret
