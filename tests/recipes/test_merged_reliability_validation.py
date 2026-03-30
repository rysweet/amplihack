"""Merged-code regression contracts for recipe-runner reliability fixes.

These tests validate the concrete runtime behaviors requested for merged-code
validation:

1. Recipe resolution must prefer the repo-root ``amplifier-bundle/recipes``
   copy over the stale ``src/amplihack/amplifier-bundle/recipes`` copy.
2. Large spilled context must avoid transport failure *and* be dereferenced
   before recipe template rendering sees it.
3. Legacy bracket conditions such as ``scope['has_ambiguities']`` must work in
   the real Rust-backed recipe runner path.
4. Investigation workflow entry must bridge ``task_description`` into the
   ``investigation_question`` field that downstream prompts actually render.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from amplihack.recipes import find_recipe
from amplihack.recipes.rust_runner import _resolve_recipe_target, run_recipe_via_rust


REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT_BUNDLE = REPO_ROOT / "amplifier-bundle" / "recipes"
SRC_BUNDLE = REPO_ROOT / "src" / "amplihack" / "amplifier-bundle" / "recipes"
INVESTIGATION_WORKFLOW = REPO_ROOT_BUNDLE / "investigation-workflow.yaml"


def _write_temp_recipe(tmp_dir: Path, name: str, body: str) -> Path:
    recipe_path = tmp_dir / f"{name}.yaml"
    recipe_path.write_text(body, encoding="utf-8")
    return recipe_path


class TestRecipeResolutionPrecedence:
    """Lock the editable-checkout resolution target used by the Rust runner."""

    def test_find_recipe_prefers_repo_root_bundle_over_src_bundle(self) -> None:
        expected = REPO_ROOT_BUNDLE / "smart-orchestrator.yaml"
        stale_src_copy = SRC_BUNDLE / "smart-orchestrator.yaml"

        assert expected.is_file(), f"Missing repo-root recipe: {expected}"
        assert stale_src_copy.is_file(), f"Missing src recipe copy: {stale_src_copy}"

        resolved = find_recipe("smart-orchestrator")

        assert resolved == expected, (
            "find_recipe() must prefer the repo-root amplifier-bundle copy in an editable checkout; "
            f"got {resolved}, expected {expected}"
        )

    def test_resolve_recipe_target_prefers_repo_root_bundle_over_src_bundle(self) -> None:
        expected = str((REPO_ROOT_BUNDLE / "smart-orchestrator.yaml").resolve())
        resolved = _resolve_recipe_target(
            "smart-orchestrator",
            recipe_dirs=None,
            working_dir=str(REPO_ROOT),
        )

        assert resolved == expected, (
            "_resolve_recipe_target() must resolve smart-orchestrator to the repo-root bundle path "
            f"in this worktree; got {resolved}, expected {expected}"
        )


class TestPromptTransportContracts:
    """Exercise the real Rust-backed path for spill transport behavior."""

    def test_real_runner_spilled_context_is_dereferenced_before_rendering(self) -> None:
        recipe_body = """\
name: spill-probe
steps:
  - id: detect
    type: bash
    command: |
      case "{{big}}" in
        file://*) printf '%s' 'FILE_URI' ;;
        *) printf '%s' 'CONTENT' ;;
      esac
    output: probe
"""

        with tempfile.TemporaryDirectory() as tmp:
            recipe_path = _write_temp_recipe(Path(tmp), "spill-probe", recipe_body)
            result = run_recipe_via_rust(
                str(recipe_path),
                user_context={"big": "A" * 33000},
                emit_startup_banner=False,
            )

        assert result.success, (
            "Large prompt/context transport must not fail structurally when values spill to temp files "
            "(this guards against E2BIG / Argument list too long regressions)."
        )
        assert result.context.get("probe") == "CONTENT", (
            "Spilled file:// transport must be dereferenced before template rendering. "
            f"Observed probe output: {result.context.get('probe')!r}"
        )


class TestLegacyBracketConditionSupport:
    """Verify bracket-style conditions work in the real runner, not just unit helpers."""

    def test_real_runner_evaluates_legacy_bracket_condition(self) -> None:
        recipe_body = """\
name: condition-probe
steps:
  - id: setup
    type: bash
    command: |
      printf '%s' '{"has_ambiguities": true}'
    output: scope
    parse_json: true
  - id: guarded
    type: bash
    condition: "scope['has_ambiguities']"
    command: |
      printf '%s' 'bracket-ok'
    output: verdict
"""

        with tempfile.TemporaryDirectory() as tmp:
            recipe_path = _write_temp_recipe(Path(tmp), "condition-probe", recipe_body)
            result = run_recipe_via_rust(str(recipe_path), emit_startup_banner=False)

        assert result.success, "Legacy bracket conditions must execute successfully in the real runner"
        assert result.context.get("verdict") == "bracket-ok"


class TestInvestigationWorkflowVariablePlumbing:
    """Lock the workflow contract for downstream prompt fields."""

    def test_investigation_workflow_bridges_task_description_into_investigation_question(self) -> None:
        recipe = yaml.safe_load(INVESTIGATION_WORKFLOW.read_text(encoding="utf-8"))
        steps = recipe["steps"]
        first_agent_index = next(i for i, step in enumerate(steps) if step.get("agent"))

        bridging_steps: list[str] = []
        for step in steps[:first_agent_index]:
            rendered = yaml.safe_dump(step, sort_keys=False)
            if "task_description" in rendered and "investigation_question" in rendered:
                bridging_steps.append(step.get("id", "<unknown>"))

        assert bridging_steps, (
            "investigation-workflow must normalize task_description into investigation_question "
            "before the first agent prompt so downstream prompts render the real task text."
        )
