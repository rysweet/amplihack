"""Gherkin/BDD prompt-language experiment utilities for issue #3962.

This module implements a behavioral-specification prompt experiment analogous
to the TLA+ prompt-language experiment (#3497).  It reuses the shared
infrastructure from tla_prompt_experiment and provides Gherkin-specific:

- manifest loading (from experiments/hive_mind/gherkin_prompt_language/)
- heuristic evaluation targeting recipe-step-executor generation (v2)
- a thin CLI entry point

V2 redesign: replaced user-auth-API ceiling task with harder recipe-step-executor
target where models lack strong training priors and cross-feature interactions
create genuine ambiguity that formal specs can resolve.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from amplihack.eval.tla_prompt_experiment import (
    ConditionMetrics,
    ExperimentExecutionReport,
    ExperimentManifest,
    HeuristicEvaluation,
    _contains_all_groups,
    _contains_any,
    load_condition_result,
    load_experiment_manifest,
    materialize_condition_packets,
    run_tla_prompt_experiment,
    summarize_condition_results,
)

DEFAULT_GHERKIN_EXPERIMENT_HOME = Path("experiments/hive_mind/gherkin_prompt_language")
DEFAULT_MANIFEST_NAME = "manifest.json"


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    """Check if text matches any of the given regex patterns."""
    return any(re.search(p, text) for p in patterns)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_gherkin_manifest_path(repo_root: str | Path | None = None) -> Path:
    root = Path(repo_root) if repo_root is not None else _repo_root()
    return root / DEFAULT_GHERKIN_EXPERIMENT_HOME / DEFAULT_MANIFEST_NAME


def load_default_gherkin_manifest(
    repo_root: str | Path | None = None,
) -> ExperimentManifest:
    return load_experiment_manifest(default_gherkin_manifest_path(repo_root))


# ---------------------------------------------------------------------------
# Gherkin-specific heuristic evaluation — recipe step executor (v2)
# ---------------------------------------------------------------------------


def evaluate_gherkin_artifact(text: str) -> HeuristicEvaluation:
    """Evaluate a generated artifact against recipe-step-executor behavioral scenarios."""

    normalized = text.lower()

    checks: dict[str, bool] = {
        # --- Feature 1: Conditional execution ---
        "condition_evaluation": _contains_all_groups(
            normalized,
            ("condition", "eval", "expression"),
            ("context", "dict", "skip", "false"),
        ),
        "condition_skip_on_false": _matches_any(
            normalized,
            ("skipped", "skip", r"status.*skip", r"condition.*false", r"condition.*skip"),
        ),
        "condition_missing_key": _contains_any(
            normalized,
            (
                "nameerror",
                "keyerror",
                "missing key",
                "missing_key",
                "key not found",
                "get(",
                "context.get",
                "except (nameerror",
                "except nameerror",
            ),
        ),
        # --- Feature 2: Step dependencies ---
        "dependency_graph": _contains_all_groups(
            normalized,
            ("blockedby", "blocked_by", "depends", "dependencies", "dependency"),
            ("complete", "wait", "before", "dag", "order", "topological", "graph"),
        ),
        "fail_propagation": _matches_any(
            normalized,
            (
                "dependency_failed",
                "dependency failed",
                "propagat",
                r"blocked.*fail",
                r"fail.*propagat",
                "failed dependency",
            ),
        ),
        "skip_no_propagation": _matches_any(
            normalized,
            (
                r"skip.*not propagat",
                r"skip.*does not",
                r"skip.*normal",
                r"skipped.*execut",
                r"skip.*no.*propagat",
                "skip_does_not_propagate",
                "does not propagate",
                "not propagate",
                r"skip.*continue",
                r"skipped.*proceed",
                "skipped dependency",
                "blocked_by_skipped",
                r"blocked.*skipped.*run",
            ),
        ),
        # --- Feature 3: Retry with backoff ---
        "retry_mechanism": _contains_all_groups(
            normalized,
            ("retry", "retries", "max_retries", "attempt"),
            ("backoff", "exponential", "delay", "1s", "2s", "4s", "sleep"),
        ),
        "retry_exhaustion": _matches_any(
            normalized,
            (
                "exhaust",
                "all retries",
                "max retries",
                "max_retries",
                r"attempt.*fail",
                r"retries.*fail",
            ),
        ),
        # --- Feature 4: Timeout handling ---
        "timeout_enforcement": _contains_all_groups(
            normalized,
            ("timeout", "timeout_seconds", "timed_out", "timed out"),
            ("terminat", "cancel", "kill", "wait_for", "asyncio.wait_for", "signal"),
        ),
        "timeout_not_retried": _matches_any(
            normalized,
            (
                r"timed_out.*not.*retr",
                r"timeout.*not.*retr",
                r"not retr.*timeout",
                r"not retr.*timed",
                r"timed_out.*terminal",
                r"timeout.*skip.*retry",
                "not retried",
                "are not retried",
            ),
        ),
        "timeout_as_failure": _matches_any(
            normalized,
            (
                r"timed_out.*fail",
                r"timeout.*dependency",
                r"timeout.*propagat",
                r"timed.*count.*fail",
                r"timed_out.*blocked",
                "timed_out.*dependency_failed",
                r"failed.*timed_out",
                '"failed", "timed_out"',
            ),
        ),
        # --- Feature 5: Output capture ---
        "output_capture": _contains_all_groups(
            normalized,
            ("output", "result", "capture"),
            ("context", "store", "dict", "key"),
        ),
        "template_resolution": _contains_any(
            normalized,
            (
                "{{",
                "template",
                "interpolat",
                "replace",
                "format",
                "step_id",
                "resolve",
            ),
        ),
        # --- Feature 6: Sub-recipe delegation ---
        "sub_recipe_execution": _contains_all_groups(
            normalized,
            ("sub_recipe", "sub recipe", "child", "nested", "delegate"),
            ("context", "inherit", "execute", "run"),
        ),
        "sub_recipe_isolation": _matches_any(
            normalized,
            (
                "propagate_outputs",
                "propagate outputs",
                r"child.*not.*propagat",
                "isolat",
                "child context",
                "child_context",
            ),
        ),
        "sub_recipe_failure": _matches_any(
            normalized,
            (
                r"sub.*fail.*not.*propagat",
                r"fail.*sub.*no.*propagat",
                r"failed.*child.*no.*output",
                r"sub_recipe.*fail",
                r"child.*fail.*parent",
                "sub-recipe failed",
                "never propagates",
                "child_failed",
                r"failed.*no.*propagat",
            ),
        ),
        # --- Cross-feature interactions ---
        "interaction_retry_output": _matches_any(
            normalized,
            (
                r"retry.*output",
                r"retried.*output",
                r"final.*success.*output",
                r"output.*retry",
                r"attempt.*output",
                r"successful.*attempt.*value",
                r"condition.*retried",
                r"retried.*step.*output",
                "retried_step_output",
                "interaction_condition_on_retried",
                "interaction_template_with_retried",
                r"output.*retried",
                "successful output stored",
            ),
        ),
        "interaction_timeout_dependency": _matches_any(
            normalized,
            (
                r"timed.*block",
                r"timeout.*depend",
                r"timed_out.*dependency",
                r"timeout.*blocked",
                "interaction_timeout_blocks",
                r"timeout.*fails.*dependency",
                r"timed_out.*blocked.*fail",
                "timed_out_blocks",
                r"timed.out.*propagat.*fail",
            ),
        ),
        "interaction_skip_condition": _matches_any(
            normalized,
            (
                r"skip.*condition",
                r"condition.*skip",
                r"skipped.*output.*none",
                r"skip.*no.*output.*condition",
                r"condition.*missing.*skip",
                "interaction_condition_refs_skipped",
                r"condition.*refs.*skipped",
                r"skipped.*step.*condition.*false",
                "referencing_skipped",
                r"condition.*referenc.*skip",
                r"skipped.*condition.*false",
            ),
        ),
        # --- Test generation ---
        "has_tests": _contains_all_groups(
            normalized,
            ("test_", "def test", "pytest", "unittest", "assert"),
            ("step", "executor", "recipe", "context", "status"),
        ),
        "tests_cover_interactions": _contains_all_groups(
            normalized,
            ("test_", "def test", "assert"),
            (
                "retry",
                "timeout",
                "skip",
                "depend",
                "sub_recipe",
                "sub recipe",
                "child",
                "interaction",
                "cross",
            ),
        ),
        # --- Spec alignment (does it reference the Gherkin spec?) ---
        "spec_alignment": _contains_any(
            normalized,
            (
                "gherkin",
                "feature",
                "scenario",
                "given",
                "when",
                "then",
                "behavioral specification",
                "acceptance criteria",
                ".feature",
            ),
        ),
    }

    # --- Composite metrics ---
    condition_checks = ["condition_evaluation", "condition_skip_on_false", "condition_missing_key"]
    dependency_checks = ["dependency_graph", "fail_propagation", "skip_no_propagation"]
    retry_checks = ["retry_mechanism", "retry_exhaustion"]
    timeout_checks = ["timeout_enforcement", "timeout_not_retried", "timeout_as_failure"]
    output_checks = ["output_capture", "template_resolution"]
    sub_recipe_checks = [
        "sub_recipe_execution",
        "sub_recipe_isolation",
        "sub_recipe_failure",
    ]
    interaction_checks = [
        "interaction_retry_output",
        "interaction_timeout_dependency",
        "interaction_skip_condition",
    ]
    test_checks = ["has_tests", "tests_cover_interactions"]

    all_feature_checks = (
        condition_checks
        + dependency_checks
        + retry_checks
        + timeout_checks
        + output_checks
        + sub_recipe_checks
    )

    scenario_coverage_score = sum(checks[c] for c in all_feature_checks) / len(all_feature_checks)
    edge_case_score = sum(checks[c] for c in interaction_checks) / len(interaction_checks)
    step_impl_score = sum(checks[c] for c in all_feature_checks + interaction_checks) / len(
        all_feature_checks + interaction_checks
    )
    test_gen_score = sum(checks[c] for c in test_checks) / len(test_checks)

    all_behavioral = all_feature_checks + interaction_checks
    behavioral_score = sum(checks[c] for c in all_behavioral) / len(all_behavioral)

    all_non_spec = [c for c in checks if c != "spec_alignment"]
    baseline_score = sum(checks[c] for c in all_non_spec) / len(all_non_spec)

    all_checks_list = list(checks.keys())
    spec_coverage_score = sum(checks[c] for c in all_checks_list) / len(all_checks_list)

    metrics = ConditionMetrics(
        baseline_score=round(baseline_score, 4),
        specification_coverage=round(spec_coverage_score, 4),
        scenario_coverage=round(scenario_coverage_score, 4),
        step_implementation=round(step_impl_score, 4),
        edge_case_handling=round(edge_case_score, 4),
        test_generation=round(test_gen_score, 4),
        behavioral_alignment=round(behavioral_score, 4),
    )

    notes = [
        "Heuristic signal only; this is not authoritative grading.",
        "Gherkin/BDD experiment v2: evaluates recipe-step-executor generation quality.",
    ]
    for check_name, passed in checks.items():
        if not passed:
            notes.append(f"Missing heuristic signal: {check_name}")

    return HeuristicEvaluation(metrics=metrics, checks=checks, notes=notes)


# ---------------------------------------------------------------------------
# Runner: thin wrapper around the shared experiment runner
# ---------------------------------------------------------------------------


def run_gherkin_prompt_experiment(
    output_dir: str | Path,
    *,
    smoke: bool = False,
    manifest: ExperimentManifest | None = None,
    replay_dir: str | Path | None = None,
    allow_live: bool = False,
) -> ExperimentExecutionReport:
    """Run the Gherkin prompt-language experiment."""

    resolved_manifest = manifest or load_default_gherkin_manifest()
    return run_tla_prompt_experiment(
        output_dir,
        smoke=smoke,
        manifest=resolved_manifest,
        replay_dir=replay_dir,
        allow_live=allow_live,
        validate_spec=False,
        evaluator=evaluate_gherkin_artifact,
        spec_section_header="Behavioral specification",
        spec_fence_lang="gherkin",
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gherkin/BDD prompt-language experiment (issue #3962).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=default_gherkin_manifest_path(),
        help="Path to the experiment manifest JSON file.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Expand the smoke matrix instead of the full matrix.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the expanded matrix JSON to this path instead of stdout.",
    )
    parser.add_argument(
        "--variant",
        help="Print the fully combined prompt text for a single prompt variant.",
    )
    parser.add_argument(
        "--materialize-dir",
        type=Path,
        help="Write one directory per condition containing prompt/spec packets.",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        help="Execute the experiment and write per-condition artifacts to this directory.",
    )
    parser.add_argument(
        "--replay-dir",
        type=Path,
        help="Read pre-generated condition artifacts from this directory.",
    )
    parser.add_argument(
        "--allow-live",
        action="store_true",
        help="Allow real SDK-backed model execution when --replay-dir is not supplied.",
    )
    parser.add_argument(
        "--summarize-results",
        type=Path,
        help="Read run_result.json files under this directory and print aggregate summary.",
    )
    args = parser.parse_args(argv)

    manifest = load_experiment_manifest(args.manifest)
    if args.run_dir:
        report = run_gherkin_prompt_experiment(
            args.run_dir,
            smoke=args.smoke,
            manifest=manifest,
            replay_dir=args.replay_dir,
            allow_live=args.allow_live,
        )
        print(json.dumps(report.to_dict(), indent=2))
        if report.failed_conditions:
            print(
                f"Experiment run recorded {report.failed_conditions} failed condition(s). "
                f"See {args.run_dir}/*/run_result.json for details.",
                file=sys.stderr,
            )
            return 1
        return 0
    if args.summarize_results:
        result_files = sorted(args.summarize_results.glob("*/run_result.json"))
        if not result_files:
            raise SystemExit("No run_result.json files found under the given directory")
        summary = summarize_condition_results(
            [load_condition_result(path) for path in result_files]
        )
        print(json.dumps(summary.to_dict(), indent=2))
        return 0
    if args.materialize_dir:
        packets = materialize_condition_packets(
            args.materialize_dir,
            smoke=args.smoke,
            manifest=manifest,
        )
        print(
            json.dumps(
                {
                    "experiment_id": manifest.experiment_id,
                    "matrix_mode": "smoke" if args.smoke else "full",
                    "output_dir": str(args.materialize_dir),
                    "materialized_conditions": [item.to_dict() for item in packets],
                },
                indent=2,
            )
        )
        return 0
    if args.variant:
        bundle = manifest.load_prompt_bundle(
            args.variant,
            spec_section_header="Behavioral specification",
            spec_fence_lang="gherkin",
        )
        print(bundle.combined_text(), end="")
        return 0

    payload = {
        "experiment_id": manifest.experiment_id,
        "target_id": manifest.generation_target.target_id,
        "matrix_mode": "smoke" if args.smoke else "full",
        "conditions": [item.to_dict() for item in manifest.expand_matrix(smoke=args.smoke)],
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n")
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
