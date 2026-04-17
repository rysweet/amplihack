"""Exercise answer validators for the teaching agent."""

from __future__ import annotations

from typing import Any


def _validate_contains(user_answer: str, required_fragments: list[str]) -> bool:
    """Return True when *user_answer* contains all *required_fragments* (case-insensitive)."""
    lower = user_answer.lower()
    return all(frag.lower() in lower for frag in required_fragments)


def _validate_prompt_file(user_answer: str) -> bool:
    """Check that user_answer looks like a valid prompt.md file."""
    return _validate_contains(user_answer, ["# goal", "constraint", "success"])


def _validate_cli_command(user_answer: str) -> bool:
    """Check that user_answer contains a valid CLI invocation."""
    return _validate_contains(user_answer, ["amplihack", "new", "--file"])


def _validate_sdk_choice(user_answer: str) -> bool:
    """Check that user_answer names one of the four SDKs."""
    sdks = ["copilot", "claude", "microsoft", "mini"]
    lower = user_answer.lower()
    return any(sdk in lower for sdk in sdks)


def _validate_multi_agent_command(user_answer: str) -> bool:
    """Check that user_answer includes --multi-agent flag."""
    return _validate_contains(user_answer, ["--multi-agent"])


def _validate_spawning_command(user_answer: str) -> bool:
    """Check that user_answer includes both --multi-agent and --enable-spawning."""
    return _validate_contains(user_answer, ["--multi-agent", "--enable-spawning"])


def _validate_eval_command(user_answer: str) -> bool:
    """Check that user_answer invokes the progressive test suite."""
    return _validate_contains(user_answer, ["python", "amplihack"]) and _validate_contains(
        user_answer, ["eval"]
    )


def _validate_level_explanation(user_answer: str) -> bool:
    """Check that user_answer mentions at least three eval levels."""
    levels_found = sum(1 for lvl in ["L1", "L2", "L3", "L4", "L5", "L6"] if lvl in user_answer)
    return levels_found >= 3


def _validate_self_improve(user_answer: str) -> bool:
    """Check that user_answer describes the self-improvement loop steps."""
    return _validate_contains(user_answer, ["eval", "analy", "improv"])


def _validate_security_prompt(user_answer: str) -> bool:
    """Check that user_answer contains security-related prompt content."""
    return _validate_contains(user_answer, ["security"]) and _validate_contains(
        user_answer, ["goal"]
    )


def _validate_custom_level(user_answer: str) -> bool:
    """Check that user_answer describes a custom eval level structure."""
    return _validate_contains(user_answer, ["article"]) and _validate_contains(
        user_answer, ["question"]
    )


def _validate_retrieval_strategy(user_answer: str) -> bool:
    """Check that user_answer names retrieval strategies correctly."""
    strategies = ["simple", "entity", "concept", "tiered"]
    lower = user_answer.lower()
    return sum(1 for s in strategies if s in lower) >= 2


def _validate_intent_types(user_answer: str) -> bool:
    """Check that user_answer lists intent types correctly."""
    intents = ["simple_recall", "mathematical", "temporal", "multi_source", "contradiction"]
    lower = user_answer.lower()
    return sum(1 for i in intents if i.replace("_", " ") in lower or i in lower) >= 3


def _validate_patch_proposer(user_answer: str) -> bool:
    """Check that user_answer describes the patch proposer workflow."""
    return _validate_contains(user_answer, ["patch"]) and _validate_contains(
        user_answer, ["review"]
    )


def _validate_runner_config(user_answer: str) -> bool:
    """Check that user_answer describes RunnerConfig fields."""
    return _validate_contains(user_answer, ["iteration"]) and _validate_contains(
        user_answer, ["threshold"]
    )


def _validate_memory_export(user_answer: str) -> bool:
    """Check that user_answer describes memory export/import concepts."""
    return _validate_contains(user_answer, ["export"]) or _validate_contains(
        user_answer, ["snapshot"]
    )


# Map from validation function name to callable
VALIDATORS: dict[str, Any] = {
    "validate_prompt_file": _validate_prompt_file,
    "validate_cli_command": _validate_cli_command,
    "validate_sdk_choice": _validate_sdk_choice,
    "validate_multi_agent_command": _validate_multi_agent_command,
    "validate_spawning_command": _validate_spawning_command,
    "validate_eval_command": _validate_eval_command,
    "validate_level_explanation": _validate_level_explanation,
    "validate_self_improve": _validate_self_improve,
    "validate_security_prompt": _validate_security_prompt,
    "validate_custom_level": _validate_custom_level,
    "validate_retrieval_strategy": _validate_retrieval_strategy,
    "validate_intent_types": _validate_intent_types,
    "validate_patch_proposer": _validate_patch_proposer,
    "validate_runner_config": _validate_runner_config,
    "validate_memory_export": _validate_memory_export,
}
