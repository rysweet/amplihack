"""Regression tests for prompt-writer internal recipe-step guidance."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_PROMPT_WRITER = (
    REPO_ROOT / ".claude" / "agents" / "amplihack" / "specialized" / "prompt-writer.md"
)
BUNDLE_PROMPT_WRITER = (
    REPO_ROOT / "amplifier-bundle" / "agents" / "specialized" / "prompt-writer.md"
)


def test_prompt_writer_copies_stay_in_sync() -> None:
    """The repo and bundle copies should not drift for recipe-critical behavior."""
    local_text = LOCAL_PROMPT_WRITER.read_text(encoding="utf-8")
    bundle_text = BUNDLE_PROMPT_WRITER.read_text(encoding="utf-8")

    assert local_text == bundle_text


def test_prompt_writer_defines_recipe_step_mode_guardrails() -> None:
    """Prompt-writer must explicitly forbid recursive workflow routing."""
    text = LOCAL_PROMPT_WRITER.read_text(encoding="utf-8")

    assert "### 0. Recipe Step Mode (HIGHEST PRIORITY)" in text
    assert "Do **NOT** invoke `/dev`" in text
    assert "Do **NOT** re-classify the prompt for routing/orchestration purposes" in text
    assert "Do **NOT** report on recipe runner status" in text
    assert "If the caller specifies an output format" in text
