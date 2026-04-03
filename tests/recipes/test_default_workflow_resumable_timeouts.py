"""TDD coverage for default-workflow checkpoint-boundary resume behavior."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

RECIPE_PATH = Path("amplifier-bundle/recipes/default-workflow.yaml")


def _load_recipe() -> dict:
    return yaml.safe_load(RECIPE_PATH.read_text(encoding="utf-8"))


def _step_map(recipe: dict) -> dict[str, dict]:
    return {step["id"]: step for step in recipe["steps"]}


@pytest.fixture(scope="module")
def recipe() -> dict:
    return _load_recipe()


@pytest.fixture(scope="module")
def steps(recipe: dict) -> dict[str, dict]:
    return _step_map(recipe)


def test_context_declares_resume_metadata_fields(recipe: dict):
    context = recipe["context"]
    assert "resume_checkpoint" in context
    assert "workstream_state_file" in context
    assert "workstream_progress_file" in context


def test_step_03_create_issue_skips_when_issue_is_already_seeded(steps: dict[str, dict]):
    condition = steps["step-03-create-issue"].get("condition", "")
    assert "issue_number" in condition


def test_step_04_setup_worktree_skips_when_resuming_from_checkpoint(steps: dict[str, dict]):
    condition = steps["step-04-setup-worktree"].get("condition", "")
    assert "resume_checkpoint" in condition


def test_step_04b_validate_worktree_exists_for_resume_handoff(steps: dict[str, dict]):
    step = steps["step-04b-validate-worktree"]
    assert step["type"] == "bash"
    assert "worktree_setup.worktree_path" in step["command"]


def test_step_04b_validate_worktree_uses_json_encoder(steps: dict[str, dict]):
    command = steps["step-04b-validate-worktree"]["command"]
    assert "python3 - <<'PY'" in command
    assert "json.dumps" in command


@pytest.mark.parametrize(
    "step_id",
    ["step-07-write-tests", "step-08-implement", "checkpoint-after-implementation"],
)
def test_pre_checkpoint_steps_skip_when_resume_checkpoint_exists(
    steps: dict[str, dict], step_id: str
):
    condition = steps[step_id].get("condition", "")
    assert "resume_checkpoint" in condition
    assert "checkpoint-after-implementation" in condition


@pytest.mark.parametrize(
    "step_id",
    ["step-09-refactor", "step-11b-implement-feedback", "checkpoint-after-review-feedback"],
)
def test_review_feedback_checkpoint_resume_skips_earlier_review_steps(
    steps: dict[str, dict], step_id: str
):
    condition = steps[step_id].get("condition", "")
    assert "resume_checkpoint" in condition
    assert "checkpoint-after-review-feedback" in condition


def test_checkpoint_after_implementation_persists_resume_metadata(steps: dict[str, dict]):
    command = steps["checkpoint-after-implementation"]["command"]
    assert "workstream_state_file" in command
    assert "checkpoint-after-implementation" in command


def test_checkpoint_after_review_feedback_persists_resume_metadata(steps: dict[str, dict]):
    command = steps["checkpoint-after-review-feedback"]["command"]
    assert "workstream_state_file" in command
    assert "checkpoint-after-review-feedback" in command


@pytest.mark.parametrize(
    "step_id",
    ["checkpoint-after-implementation", "checkpoint-after-review-feedback"],
)
def test_checkpoint_commands_are_shell_syntax_valid(
    steps: dict[str, dict], step_id: str, tmp_path: Path
):
    script_path = tmp_path / f"{step_id}.sh"
    script_path.write_text(steps[step_id]["command"], encoding="utf-8")

    result = subprocess.run(
        ["bash", "-n", str(script_path)],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr


_LIST_LITERAL_IN_CONDITION = re.compile(r"\bnot\s+in\s*\[|\bin\s*\[")


@pytest.mark.parametrize(
    "step_id,condition",
    [(step["id"], step["condition"]) for step in _load_recipe()["steps"] if step.get("condition")],
)
def test_step_conditions_do_not_use_list_literals(step_id: str, condition: str):
    """List-literal conditions are incompatible with the Rust recipe runner parser."""
    assert not _LIST_LITERAL_IN_CONDITION.search(condition), (
        f"Step '{step_id}' condition uses list-literal 'in [...]' syntax "
        f"which is incompatible with the Rust recipe runner: {condition!r}"
    )


@pytest.mark.parametrize(
    "step_id,checkpoint_value,expected",
    [
        ("step-07-write-tests", "", True),
        ("step-07-write-tests", "checkpoint-after-implementation", False),
        ("step-07-write-tests", "checkpoint-after-review-feedback", False),
        ("step-08-implement", "", True),
        ("step-08-implement", "checkpoint-after-implementation", False),
        ("step-08-implement", "checkpoint-after-review-feedback", False),
        ("checkpoint-after-implementation", "", True),
        ("checkpoint-after-implementation", "checkpoint-after-implementation", False),
        ("checkpoint-after-implementation", "checkpoint-after-review-feedback", False),
    ],
)
def test_pre_checkpoint_conditions_evaluate_correctly(
    steps: dict[str, dict],
    step_id: str,
    checkpoint_value: str,
    expected: bool,
):
    """The rewritten checkpoint resume conditions must preserve existing behavior."""
    from amplihack.recipes.models import Step, StepType

    raw = steps[step_id]
    step = Step(
        id=raw["id"],
        step_type=StepType.AGENT if raw.get("agent") else StepType.BASH,
        condition=raw.get("condition"),
        prompt=raw.get("prompt", ""),
        output=raw.get("output"),
    )
    result = step.evaluate_condition({"resume_checkpoint": checkpoint_value})
    assert result is expected, (
        f"Step '{step_id}' with resume_checkpoint={checkpoint_value!r}: "
        f"expected {expected}, got {result}"
    )
