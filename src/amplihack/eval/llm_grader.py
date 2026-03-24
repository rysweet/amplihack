"""Shared LLM grading helpers for eval modules."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from amplihack.llm.client import completion

DEFAULT_GRADER_MODEL = "claude-opus-4-6"


def extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from LLM response text."""
    stripped = text.strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", stripped, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    # REQ-DATA-2: Omit response content from the exception message — it may contain
    # eval data, student answers, or other sensitive LLM output that must not appear
    # in log streams or tracebacks.
    raise json.JSONDecodeError("No valid JSON found in LLM response", "", 0)


def get_grader_model(explicit_model: str | None = None) -> str:
    """Resolve the grader model from an explicit override or environment."""
    return explicit_model or os.environ.get("GRADER_MODEL", DEFAULT_GRADER_MODEL)


def _infer_required_api_key_var(model: str) -> str | None:
    """Infer the most likely credential env var for a grader model."""
    normalized = model.strip().lower()

    if normalized.startswith("github/"):
        return "GITHUB_API_KEY"
    if normalized.startswith("anthropic/") or normalized.startswith("claude"):
        return "ANTHROPIC_API_KEY"
    if normalized.startswith("openai/") or normalized.startswith(("gpt-", "o1", "o3", "chatgpt")):
        return "OPENAI_API_KEY"
    if normalized.startswith("azure/"):
        return "AZURE_API_KEY"
    return None


def _require_api_key_for_model(model: str) -> None:
    """Raise a clear error when a known provider key is missing."""
    key_var = _infer_required_api_key_var(model)
    if key_var and not os.environ.get(key_var):
        raise OSError(f"{key_var} environment variable is required for grader model {model}")


async def call_grader_json(
    prompt: str,
    *,
    model: str | None = None,
    max_tokens: int = 1000,
    temperature: float | None = None,
    system: str | None = None,
) -> dict[str, Any]:
    """Run a grading prompt through the LLM routing layer and parse the JSON response."""
    resolved_model = get_grader_model(model)
    _require_api_key_for_model(resolved_model)

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict[str, Any] = {
        "model": resolved_model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    response_text = await completion(**kwargs)
    return extract_json(response_text)


__all__ = [
    "DEFAULT_GRADER_MODEL",
    "call_grader_json",
    "extract_json",
    "get_grader_model",
]
