"""Gherkin/BDD prompt-language experiment utilities.

This module extends the TLA+ prompt-language experiment infrastructure to
test whether Gherkin behavioral specifications improve code generation
quality for feature-oriented tasks (user authentication REST API).

Reuses manifest loading, materialization, generation, and reporting from
tla_prompt_experiment.py. Provides Gherkin-specific heuristic evaluation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from amplihack.eval.tla_prompt_experiment import (
    ConditionMetrics,
    ConditionRunResult,
    ExperimentExecutionReport,
    ExperimentManifest,
    ExperimentSummaryReport,
    HeuristicEvaluation,
    MetricSummary,
    PromptGenerationError,
    _contains_all_groups,
    _contains_any,
    generate_condition_artifact,
    load_experiment_manifest,
    materialize_condition_packets,
    write_condition_result,
)

DEFAULT_GHERKIN_EXPERIMENT_HOME = Path("experiments/hive_mind/gherkin_prompt_language")
DEFAULT_GHERKIN_MANIFEST_NAME = "manifest.json"
GHERKIN_HEURISTIC_EVALUATION_KIND = "gherkin_heuristic_signal_v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_gherkin_manifest_path(repo_root: str | Path | None = None) -> Path:
    root = Path(repo_root) if repo_root is not None else _repo_root()
    return root / DEFAULT_GHERKIN_EXPERIMENT_HOME / DEFAULT_GHERKIN_MANIFEST_NAME


def load_gherkin_manifest(repo_root: str | Path | None = None) -> ExperimentManifest:
    return load_experiment_manifest(default_gherkin_manifest_path(repo_root))


def evaluate_gherkin_artifact(text: str) -> HeuristicEvaluation:
    """Evaluate a generated artifact against Gherkin user-authentication scenarios.

    Scoring dimensions:
    - scenario_coverage: does the generated code handle all Given/When/Then scenarios?
    - step_implementation: are step definitions implemented (not just stubs)?
    - edge_case_handling: does it handle negative/error scenarios from the feature?
    - test_generation: did the model generate tests matching the scenarios?
    - behavioral_alignment: does the code behavior match the spec behavior?
    """

    normalized = text.lower()
    checks: dict[str, bool] = {}

    # --- Scenario coverage checks (14 scenarios in the feature file) ---

    # Registration scenarios
    checks["registration_endpoint"] = _contains_all_groups(
        normalized,
        ("post", "/register", "register"),
        ("email", "password"),
        ("201", "created"),
    )
    checks["duplicate_email_rejection"] = _contains_any(
        normalized,
        (
            "409",
            "conflict",
            "already registered",
            "already exists",
            "duplicate",
            "email_exists",
            "email already",
        ),
    )
    checks["weak_password_rejection"] = _contains_all_groups(
        normalized,
        ("400", "bad request"),
        ("weak", "short", "too weak", "password_too_weak", "validation", "strength"),
    )
    checks["invalid_email_rejection"] = _contains_any(
        normalized,
        (
            "invalid email",
            "invalid_email",
            "email validation",
            "email format",
            "not a valid email",
            "email_invalid",
        ),
    )

    # Login scenarios
    checks["login_endpoint"] = _contains_all_groups(
        normalized,
        ("post", "/login", "login"),
        ("access_token", "access token", "jwt", "token"),
        ("refresh_token", "refresh token", "refresh"),
    )
    checks["wrong_password_401"] = _contains_all_groups(
        normalized,
        ("401", "unauthorized"),
        ("invalid credentials", "invalid_credentials", "wrong password", "authentication failed"),
    )
    checks["account_lockout"] = _contains_any(
        normalized,
        (
            "423",
            "locked",
            "account locked",
            "account_locked",
            "lockout",
            "lock_out",
            "failed_attempts",
            "failed attempts",
            "login_attempts",
        ),
    )

    # Token scenarios
    checks["token_refresh"] = _contains_all_groups(
        normalized,
        ("refresh", "token"),
        ("new", "200", "access_token", "access token"),
    )
    checks["expired_token_rejection"] = _contains_any(
        normalized,
        (
            "token expired",
            "token_expired",
            "expired token",
            "expired_token",
            "expir",
        ),
    )

    # Protected resource
    checks["protected_endpoint"] = _contains_all_groups(
        normalized,
        ("/me", "get /me", "protected", "profile"),
        ("authorization", "bearer", "access_token", "access token"),
    )
    checks["missing_token_401"] = _contains_any(
        normalized,
        (
            "missing authorization",
            "missing_authorization",
            "missing token",
            "no token",
            "unauthorized",
            "missing auth",
        ),
    )

    # Security
    checks["password_hashing"] = _contains_any(
        normalized,
        (
            "bcrypt",
            "hashpw",
            "hash_password",
            "password_hash",
            "generate_password_hash",
            "pbkdf2",
            "argon2",
            "scrypt",
        ),
    )

    # --- Step implementation (not stubs) ---
    checks["has_implementation"] = _contains_all_groups(
        normalized,
        ("def ", "class ", "app.", "router.", "@app.", "@router."),
        ("return", "response", "jsonify", "jsonresponse"),
    )

    # --- Test generation ---
    checks["has_tests"] = _contains_all_groups(
        normalized,
        ("test_", "def test", "pytest", "unittest", "assert"),
        ("register", "login", "token", "/me", "auth"),
    )

    # Compute aggregate scores

    # Scenario coverage: 12 scenario checks out of 12
    scenario_checks = [
        "registration_endpoint",
        "duplicate_email_rejection",
        "weak_password_rejection",
        "invalid_email_rejection",
        "login_endpoint",
        "wrong_password_401",
        "account_lockout",
        "token_refresh",
        "expired_token_rejection",
        "protected_endpoint",
        "missing_token_401",
        "password_hashing",
    ]
    scenario_coverage = sum(checks[c] for c in scenario_checks) / len(scenario_checks)

    # Step implementation: real code, not stubs
    step_implementation = 1.0 if checks["has_implementation"] else 0.0

    # Edge case handling: error scenarios
    edge_case_checks = [
        "duplicate_email_rejection",
        "weak_password_rejection",
        "invalid_email_rejection",
        "wrong_password_401",
        "account_lockout",
        "expired_token_rejection",
        "missing_token_401",
    ]
    edge_case_handling = sum(checks[c] for c in edge_case_checks) / len(edge_case_checks)

    # Test generation
    test_generation = 1.0 if checks["has_tests"] else 0.0

    # Behavioral alignment: overall
    behavioral_alignment = (scenario_coverage + step_implementation + edge_case_handling) / 3.0

    # Map to ConditionMetrics (reusing the existing field names with new semantics)
    metrics = ConditionMetrics(
        baseline_score=round(scenario_coverage, 4),
        invariant_compliance=round(edge_case_handling, 4),
        proof_alignment=round(step_implementation, 4),
        local_protocol_alignment=round(test_generation, 4),
        progress_signal=round(behavioral_alignment, 4),
        specification_coverage=round(
            (scenario_coverage + edge_case_handling + test_generation) / 3.0, 4
        ),
    )

    notes = [
        "Gherkin heuristic signal only; this is not authoritative grading.",
        "Metrics mapping: baseline_score=scenario_coverage, invariant_compliance=edge_case_handling,",
        "  proof_alignment=step_implementation, local_protocol_alignment=test_generation,",
        "  progress_signal=behavioral_alignment, specification_coverage=overall_coverage.",
    ]
    for check_name, passed in checks.items():
        if not passed:
            notes.append(f"Missing heuristic signal: {check_name}")
    return HeuristicEvaluation(metrics=metrics, checks=checks, notes=notes)


def generate_gherkin_markdown_report(
    execution_report: ExperimentExecutionReport,
    results: list[ConditionRunResult],
    output_path: str | Path,
) -> Path:
    """Write a markdown report for a Gherkin prompt-language experiment run."""

    output_file = Path(output_path)
    lines = [
        "# Gherkin Prompt Language Experiment Report",
        "",
        f"**Experiment ID**: `{execution_report.experiment_id}`",
        f"**Generated at**: `{execution_report.generated_at}`",
        f"**Matrix mode**: `{execution_report.matrix_mode}`",
        f"**Replay mode**: `{execution_report.replay_mode}`",
        f"**Evaluation kind**: `{GHERKIN_HEURISTIC_EVALUATION_KIND}`",
        f"**Output dir**: `{execution_report.output_dir}`",
        "",
        "## Metric Semantics",
        "",
        "| Report Column | Gherkin Meaning |",
        "|---------------|-----------------|",
        "| Baseline | Scenario Coverage (12 scenario checks) |",
        "| Invariant | Edge Case Handling (7 error scenarios) |",
        "| Proof | Step Implementation (real code, not stubs) |",
        "| Local | Test Generation (tests matching scenarios) |",
        "| Progress | Behavioral Alignment (composite) |",
        "| Coverage | Overall Coverage (composite) |",
        "",
        "## Summary",
        "",
        f"- Total conditions: {execution_report.total_conditions}",
        f"- Completed conditions: {execution_report.completed_conditions}",
        f"- Failed conditions: {execution_report.failed_conditions}",
        "",
        "## Condition Table",
        "",
        "| Condition | Model | Prompt | Status | Scenario Cov | Edge Cases | Implementation | Tests | Behavioral | Overall |",
        "|-----------|-------|--------|--------|-------------|------------|---------------|-------|------------|---------|",
    ]
    for result in results:
        m = result.metrics
        lines.append(
            "| "
            f"{result.condition.condition_id} | "
            f"{result.condition.model_id} | "
            f"{result.condition.prompt_variant_id} | "
            f"{result.status} | "
            f"{m.baseline_score if m.baseline_score is not None else '--'} | "
            f"{m.invariant_compliance if m.invariant_compliance is not None else '--'} | "
            f"{m.proof_alignment if m.proof_alignment is not None else '--'} | "
            f"{m.local_protocol_alignment if m.local_protocol_alignment is not None else '--'} | "
            f"{m.progress_signal if m.progress_signal is not None else '--'} | "
            f"{m.specification_coverage if m.specification_coverage is not None else '--'} |"
        )

    failed = [item for item in results if item.status == "failed"]
    if failed:
        lines.extend(["", "## Failures", ""])
        for result in failed:
            lines.append(
                f"- `{result.condition.condition_id}`: "
                + ("; ".join(result.notes) if result.notes else "Failed without notes")
            )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Scores in this report are heuristic local signals, not authoritative eval scores.",
            "- Scenario coverage checks for keyword presence of all 12 behavioral scenarios.",
            "- Edge case handling checks the 7 error/negative scenarios specifically.",
            "",
        ]
    )
    output_file.write_text("\n".join(lines))
    return output_file


def _summarize_metric(values: list[float]) -> MetricSummary | None:
    if not values:
        return None
    return MetricSummary(mean=sum(values) / len(values), count=len(values))


def summarize_gherkin_results(results: list[ConditionRunResult]) -> ExperimentSummaryReport:
    """Summarize Gherkin experiment results, grouping by prompt variant and model."""

    if not results:
        raise ValueError("results cannot be empty")

    completed = [item for item in results if item.status == "completed"]
    failed = [item for item in results if item.status == "failed"]
    experiment_id = results[0].condition.experiment_id

    def bucket(items: list[ConditionRunResult]) -> dict[str, MetricSummary]:
        metric_values: dict[str, list[float]] = {
            "baseline_score": [],
            "invariant_compliance": [],
            "proof_alignment": [],
            "local_protocol_alignment": [],
            "progress_signal": [],
            "specification_coverage": [],
        }
        for item in items:
            m = item.metrics
            if m.baseline_score is not None:
                metric_values["baseline_score"].append(m.baseline_score)
            if m.invariant_compliance is not None:
                metric_values["invariant_compliance"].append(m.invariant_compliance)
            if m.proof_alignment is not None:
                metric_values["proof_alignment"].append(m.proof_alignment)
            if m.local_protocol_alignment is not None:
                metric_values["local_protocol_alignment"].append(m.local_protocol_alignment)
            if m.progress_signal is not None:
                metric_values["progress_signal"].append(m.progress_signal)
            if m.specification_coverage is not None:
                metric_values["specification_coverage"].append(m.specification_coverage)
        summary: dict[str, MetricSummary] = {}
        for metric_name, values in metric_values.items():
            ms = _summarize_metric(values)
            if ms is not None:
                summary[metric_name] = ms
        return summary

    by_prompt_variant: dict[str, list[ConditionRunResult]] = {}
    by_model: dict[str, list[ConditionRunResult]] = {}
    for item in completed:
        by_prompt_variant.setdefault(item.condition.prompt_variant_id, []).append(item)
        by_model.setdefault(item.condition.model_id, []).append(item)

    return ExperimentSummaryReport(
        experiment_id=experiment_id,
        total_conditions=len(results),
        completed_conditions=len(completed),
        failed_conditions=len(failed),
        metric_summary=bucket(completed),
        by_prompt_variant={key: bucket(value) for key, value in by_prompt_variant.items()},
        by_model={key: bucket(value) for key, value in by_model.items()},
    )


def run_gherkin_prompt_experiment(
    output_dir: str | Path,
    *,
    smoke: bool = False,
    manifest: ExperimentManifest | None = None,
    replay_dir: str | Path | None = None,
    allow_live: bool = False,
) -> ExperimentExecutionReport:
    """Run the Gherkin prompt-language experiment and emit per-condition artifacts."""

    resolved_manifest = manifest or load_gherkin_manifest()
    replay_root = Path(replay_dir) if replay_dir is not None else None
    if replay_root is None and not allow_live:
        raise ValueError(
            "Live generation is disabled by default. Supply replay_dir or pass allow_live=True / --allow-live."
        )
    packets = materialize_condition_packets(output_dir, smoke=smoke, manifest=resolved_manifest)

    results: list[ConditionRunResult] = []
    for packet in packets:
        condition_dir = Path(packet.condition_dir)
        generated_file = condition_dir / "generated_artifact.md"
        raw_response_file = condition_dir / "raw_response.txt"
        evaluation_file = condition_dir / "evaluation.json"
        run_result_file = condition_dir / "run_result.json"
        try:
            bundle = resolved_manifest.load_prompt_bundle(packet.condition.prompt_variant_id)
            generated = generate_condition_artifact(
                packet.condition,
                bundle.combined_text(),
                work_dir=condition_dir,
                replay_dir=replay_root,
                allow_live=allow_live,
            )
            generated_file.write_text(generated.response_text)
            raw_response_file.write_text(generated.response_text)
            evaluation = evaluate_gherkin_artifact(generated.response_text)
            evaluation_file.write_text(json.dumps(evaluation.to_dict(), indent=2) + "\n")
            generation_notes = [f"generation_provider={generated.provider}"]
            runtime_model_id = generated.metadata.get("runtime_model_id")
            if runtime_model_id and runtime_model_id != packet.condition.model_id:
                generation_notes.append(f"runtime_model_id={runtime_model_id}")
            result = ConditionRunResult(
                condition=packet.condition,
                status="completed",
                metrics=evaluation.metrics,
                generated_artifact_path=str(generated_file),
                evaluation_artifact_path=str(evaluation_file),
                raw_response_path=str(raw_response_file),
                notes=[*generation_notes, *evaluation.notes],
            )
        except PromptGenerationError as exc:
            if exc.response_text:
                raw_response_file.write_text(exc.response_text)
            failure_notes = [str(exc)]
            runtime_model_id = exc.metadata.get("runtime_model_id")
            if runtime_model_id and runtime_model_id != packet.condition.model_id:
                failure_notes.append(f"runtime_model_id={runtime_model_id}")
            result = ConditionRunResult(
                condition=packet.condition,
                status="failed",
                notes=failure_notes,
                raw_response_path=str(raw_response_file) if exc.response_text else None,
            )
        except Exception as exc:
            result = ConditionRunResult(
                condition=packet.condition,
                status="failed",
                notes=[str(exc)],
            )
        write_condition_result(run_result_file, result)
        results.append(result)

    summary = summarize_gherkin_results(results)
    report = ExperimentExecutionReport(
        experiment_id=resolved_manifest.experiment_id,
        matrix_mode="smoke" if smoke else "full",
        output_dir=str(output_dir),
        generated_at=datetime.now(UTC).isoformat(),
        total_conditions=len(results),
        completed_conditions=sum(1 for item in results if item.status == "completed"),
        failed_conditions=sum(1 for item in results if item.status == "failed"),
        summary=summary,
        replay_mode=replay_root is not None,
    )
    output_root = Path(output_dir)
    (output_root / "experiment_report.json").write_text(
        json.dumps(report.to_dict(), indent=2) + "\n"
    )
    generate_gherkin_markdown_report(report, results, output_root / "experiment_report.md")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gherkin/BDD prompt-language experiment runner.",
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
        help="Read pre-generated condition artifacts from this directory instead of invoking live models.",
    )
    parser.add_argument(
        "--allow-live",
        action="store_true",
        help="Allow real SDK-backed model execution when --replay-dir is not supplied.",
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
        print(manifest.load_prompt_bundle(args.variant).combined_text(), end="")
        return 0

    payload = {
        "experiment_id": manifest.experiment_id,
        "target_id": manifest.generation_target.target_id,
        "matrix_mode": "smoke" if args.smoke else "full",
        "conditions": [item.to_dict() for item in manifest.expand_matrix(smoke=args.smoke)],
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
