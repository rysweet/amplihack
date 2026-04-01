"""Tests for hollow-success detection in default-workflow.yaml.

Verifies that:
1. step-08-implement prompt contains stub-replacement instructions
2. step-08c-hollow-success-guard exists and detects 0-change implementations
3. The guard checks for action keywords in the task description
4. Builder agent documentation includes stub-replacement guidance

Addresses: GitHub issue #4094
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

RECIPE_FILE = Path("amplifier-bundle/recipes/default-workflow.yaml")
BUILDER_AGENT_FILE = Path("amplifier-bundle/agents/core/builder.md")


def _load_recipe() -> dict:
    content = RECIPE_FILE.read_text(encoding="utf-8")
    return yaml.safe_load(content)


def _find_step(recipe: dict, step_id: str) -> dict:
    for step in recipe.get("steps", []):
        if step.get("id") == step_id:
            return step
    raise KeyError(f"Step '{step_id}' not found in recipe")


@pytest.fixture(scope="module")
def recipe() -> dict:
    return _load_recipe()


@pytest.fixture(scope="module")
def step_08(recipe: dict) -> dict:
    return _find_step(recipe, "step-08-implement")


@pytest.fixture(scope="module")
def hollow_guard(recipe: dict) -> dict:
    return _find_step(recipe, "step-08c-hollow-success-guard")


# ===========================================================================
# YAML must parse cleanly
# ===========================================================================


class TestRecipeParses:
    def test_yaml_loads(self, recipe: dict):
        assert recipe is not None
        assert "steps" in recipe


# ===========================================================================
# Step 08: Implementation prompt contains stub-replacement instructions
# ===========================================================================


class TestStep08StubReplacement:
    def test_prompt_mentions_stub_replacement(self, step_08: dict):
        prompt = step_08.get("prompt", "")
        assert "Stub/Placeholder Replacement" in prompt, (
            "step-08 prompt must contain stub/placeholder replacement instructions"
        )

    def test_prompt_warns_about_hollow_success(self, step_08: dict):
        prompt = step_08.get("prompt", "")
        assert "hollow success" in prompt.lower(), "step-08 prompt must warn about hollow success"

    def test_prompt_lists_replacement_targets(self, step_08: dict):
        """Prompt must mention common stub patterns as replacement targets."""
        prompt = step_08.get("prompt", "")
        for target in ["stubs", "placeholders", "NotImplementedError", "TODO"]:
            assert target in prompt, f"step-08 prompt must mention '{target}' as replacement target"

    def test_output_requires_files_changed(self, step_08: dict):
        prompt = step_08.get("prompt", "")
        assert "List of files changed" in prompt, (
            "step-08 output section must require listing files changed"
        )


# ===========================================================================
# Step 08c: Hollow success guard exists and is properly configured
# ===========================================================================


class TestHollowSuccessGuard:
    def test_guard_step_exists(self, hollow_guard: dict):
        assert hollow_guard["id"] == "step-08c-hollow-success-guard"

    def test_guard_is_bash_type(self, hollow_guard: dict):
        assert hollow_guard.get("type") == "bash", (
            "Hollow success guard must be a bash step for reliable file-change detection"
        )

    def test_guard_checks_git_diff(self, hollow_guard: dict):
        command = hollow_guard.get("command", "")
        assert "git diff" in command, "Guard must use git diff to detect changes"

    def test_guard_checks_untracked_files(self, hollow_guard: dict):
        command = hollow_guard.get("command", "")
        assert "ls-files" in command, "Guard must check for untracked files via git ls-files"

    def test_guard_detects_action_keywords(self, hollow_guard: dict):
        """Guard must grep for action keywords that imply code changes."""
        command = hollow_guard.get("command", "")
        for keyword in ["replace", "implement", "fix", "create"]:
            assert keyword in command, f"Guard must detect action keyword '{keyword}'"

    def test_guard_fails_on_zero_changes_with_action_keywords(self, hollow_guard: dict):
        command = hollow_guard.get("command", "")
        assert "exit 1" in command, "Guard must exit 1 when hollow success is detected"

    def test_guard_has_output(self, hollow_guard: dict):
        assert hollow_guard.get("output") == "hollow_success_check"

    def test_guard_comes_before_checkpoint(self, recipe: dict):
        """Guard must appear between step-08b and checkpoint-after-implementation."""
        step_ids = [s.get("id") for s in recipe.get("steps", [])]
        guard_idx = step_ids.index("step-08c-hollow-success-guard")
        checkpoint_idx = step_ids.index("checkpoint-after-implementation")
        step_08b_idx = step_ids.index("step-08b-integration")
        assert step_08b_idx < guard_idx < checkpoint_idx, (
            "Guard must be ordered: step-08b < step-08c (guard) < checkpoint"
        )


# ===========================================================================
# Builder agent: stub-replacement guidance
# ===========================================================================


class TestBuilderAgentStubGuidance:
    def test_builder_agent_file_exists(self):
        assert BUILDER_AGENT_FILE.exists()

    def test_builder_mentions_stub_replacement(self):
        content = BUILDER_AGENT_FILE.read_text(encoding="utf-8")
        assert "Stub/Placeholder Replacement" in content, (
            "Builder agent must include stub/placeholder replacement section"
        )

    def test_builder_warns_about_hollow_success(self):
        content = BUILDER_AGENT_FILE.read_text(encoding="utf-8")
        assert "hollow success" in content.lower(), "Builder agent must warn about hollow success"
