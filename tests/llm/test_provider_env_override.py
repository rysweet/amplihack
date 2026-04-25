"""Tests for amplihack.llm.client provider env-var override.

Regression coverage for the bug where embedded callers (Simard's Rust OODA
daemon and any other host that imports amplihack directly without going
through `amplihack copilot`) silently fell back to the bundled Claude Code
CLI — which is "Not logged in" by default — and produced empty completions
that were swallowed by metacognition_grader's JSON-parse-fail path.

The fix: AMPLIHACK_LLM_PROVIDER / SIMARD_LLM_PROVIDER env vars take priority
over file-based launcher detection.
"""

from __future__ import annotations

import importlib

import pytest


def _reload_client():
    import amplihack.llm.client as client
    importlib.reload(client)
    client._detector_cache = None
    return client


@pytest.fixture(autouse=True)
def _clear_provider_env(monkeypatch):
    for var in ("AMPLIHACK_LLM_PROVIDER", "SIMARD_LLM_PROVIDER"):
        monkeypatch.delenv(var, raising=False)
    yield


def test_provider_from_env_returns_none_when_unset():
    client = _reload_client()
    assert client._provider_from_env() is None


@pytest.mark.parametrize(
    "value,expected",
    [
        ("copilot", "copilot"),
        ("Copilot", "copilot"),
        ("  COPILOT  ", "copilot"),
        ("github-copilot", "copilot"),
        ("gh-copilot", "copilot"),
        ("rustyclawd", "copilot"),
        ("claude", "claude"),
        ("Claude-Code", "claude"),
        ("anthropic", "claude"),
    ],
)
def test_provider_from_env_recognized(monkeypatch, value, expected):
    monkeypatch.setenv("AMPLIHACK_LLM_PROVIDER", value)
    client = _reload_client()
    assert client._provider_from_env() == expected


def test_simard_env_var_also_honored(monkeypatch):
    monkeypatch.setenv("SIMARD_LLM_PROVIDER", "copilot")
    client = _reload_client()
    assert client._provider_from_env() == "copilot"


def test_amplihack_env_takes_priority_over_simard(monkeypatch):
    monkeypatch.setenv("AMPLIHACK_LLM_PROVIDER", "claude")
    monkeypatch.setenv("SIMARD_LLM_PROVIDER", "copilot")
    client = _reload_client()
    assert client._provider_from_env() == "claude"


def test_unrecognized_value_falls_through(monkeypatch):
    monkeypatch.setenv("AMPLIHACK_LLM_PROVIDER", "ollama")
    client = _reload_client()
    assert client._provider_from_env() is None


def test_detect_launcher_uses_env_override_when_present(monkeypatch, tmp_path):
    monkeypatch.setenv("SIMARD_LLM_PROVIDER", "copilot")
    client = _reload_client()
    assert client._detect_launcher(tmp_path) == "copilot"


def test_detect_launcher_uses_env_override_over_file(monkeypatch, tmp_path):
    runtime = tmp_path / ".claude" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "launcher_context.json").write_text(
        '{"launcher": "claude", "version": "1", "timestamp": "2025-01-01T00:00:00"}'
    )
    monkeypatch.setenv("AMPLIHACK_LLM_PROVIDER", "copilot")
    client = _reload_client()
    assert client._detect_launcher(tmp_path) == "copilot"


@pytest.mark.asyncio
async def test_completion_explicit_copilot_no_silent_claude_fallback(
    monkeypatch,
):
    monkeypatch.setenv("AMPLIHACK_LLM_PROVIDER", "copilot")
    client = _reload_client()
    monkeypatch.setattr(client, "_COPILOT_SDK_OK", False)
    monkeypatch.setattr(client, "_CLAUDE_SDK_OK", True)

    async def _boom_claude(prompt, project_root):
        raise AssertionError("should not silently fall back to claude")

    monkeypatch.setattr(client, "_query_claude", _boom_claude)

    out = await client.completion(
        messages=[{"role": "user", "content": "hi"}],
    )
    assert out == ""


@pytest.mark.asyncio
async def test_completion_explicit_claude_no_silent_copilot_fallback(
    monkeypatch,
):
    monkeypatch.setenv("AMPLIHACK_LLM_PROVIDER", "claude")
    client = _reload_client()
    monkeypatch.setattr(client, "_CLAUDE_SDK_OK", False)
    monkeypatch.setattr(client, "_COPILOT_SDK_OK", True)

    async def _boom_copilot(prompt, project_root):
        raise AssertionError("should not silently fall back to copilot")

    monkeypatch.setattr(client, "_query_copilot", _boom_copilot)

    out = await client.completion(
        messages=[{"role": "user", "content": "hi"}],
    )
    assert out == ""
