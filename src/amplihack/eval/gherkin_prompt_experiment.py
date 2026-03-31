"""Gherkin v2 prompt-language experiment utilities for issue #3969.

This module implements a behavioral-specification prompt experiment targeting a
recipe step executor with 6 interacting features.  It reuses the shared
infrastructure from tla_prompt_experiment and provides Gherkin-specific:

- manifest loading (from experiments/hive_mind/gherkin_v2_recipe_executor/)
- heuristic evaluation with 6 scoring dimensions matching the 6 features
- a thin CLI entry point that plugs into the same runner

V2 redesign: replaced the user-auth ceiling task (PR #3964) with a harder
recipe-step-executor target where models lack strong training priors and
cross-feature interactions create genuine ambiguity.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from amplihack.eval.tla_prompt_experiment import (
    ConditionMetrics,
    ConditionRunResult,
    ExperimentExecutionReport,
    ExperimentManifest,
    HeuristicEvaluation,
    PromptGenerationError,
    _contains_all_groups,
    _contains_any,
    generate_condition_artifact,
    load_condition_result,
    load_experiment_manifest,
    materialize_condition_packets,
    summarize_condition_results,
    write_condition_result,
)

DEFAULT_GHERKIN_V2_HOME = Path("experiments/hive_mind/gherkin_v2_recipe_executor")
DEFAULT_MANIFEST_NAME = "manifest.json"
GHERKIN_HEURISTIC_KIND = "gherkin_heuristic_v2"
GHERKIN_LIVE_SYSTEM_PROMPT = (
    "You are participating in a controlled code-generation experiment. "
    "Follow the user prompt exactly, stay within scope, and return only the "
    "requested Python implementation and focused tests without extra commentary. "
    "Do not read, write, or modify repository files. Do not run shell commands. "
    "Return the artifact directly in your response."
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_gherkin_v2_manifest_path(repo_root: str | Path | None = None) -> Path:
    root = Path(repo_root) if repo_root is not None else _repo_root()
    return root / DEFAULT_GHERKIN_V2_HOME / DEFAULT_MANIFEST_NAME


def load_gherkin_v2_manifest(
    repo_root: str | Path | None = None,
) -> ExperimentManifest:
    return load_experiment_manifest(default_gherkin_v2_manifest_path(repo_root))


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    """Check if text matches any of the given regex patterns."""
    return any(re.search(p, text) for p in patterns)


# ---------------------------------------------------------------------------
# Gherkin v2 heuristic evaluation — recipe step executor (6 features)
# ---------------------------------------------------------------------------


@dataclass
class GherkinConditionMetrics:
    """Score bundle for the 6-feature recipe step executor evaluation."""

    conditional_execution: float | None = None
    dependency_handling: float | None = None
    retry_logic: float | None = None
    timeout_semantics: float | None = None
    output_capture: float | None = None
    sub_recipe_delegation: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "conditional_execution": self.conditional_execution,
            "dependency_handling": self.dependency_handling,
            "retry_logic": self.retry_logic,
            "timeout_semantics": self.timeout_semantics,
            "output_capture": self.output_capture,
            "sub_recipe_delegation": self.sub_recipe_delegation,
        }


def evaluate_gherkin_artifact(text: str) -> HeuristicEvaluation:
    """Evaluate a generated artifact against recipe-step-executor behavioral scenarios.

    Scores 6 features plus cross-feature interaction signals. Each feature
    score is a float in [0, 1] derived from heuristic keyword/pattern matching.
    """

    normalized = text.lower()

    checks: dict[str, bool] = {
        # --- Feature 1: Conditional execution ---
        "condition_evaluation": _contains_all_groups(
            normalized,
            ("condition", "eval"),
            ("context", "dict", "skip", "false"),
        ),
        "condition_skip": _matches_any(
            normalized,
            (r"skipped", r"skip", r"status.*skip", r"condition.*false"),
        ),
        "condition_missing_key": _contains_any(
            normalized,
            (
                "keyerror",
                "nameerror",
                "missing key",
                "key not found",
                "context.get",
                "except (keyerror",
                "except keyerror",
                "except (nameerror",
                "except nameerror",
            ),
        ),
        # --- Feature 2: Step dependencies ---
        "dependency_graph": _contains_all_groups(
            normalized,
            ("blockedby", "blocked_by", "depends", "dependencies", "dependency"),
            ("complete", "completed", "failed", "status"),
        ),
        "failure_propagation": _contains_any(
            normalized,
            (
                "dependency_failed",
                "propagat",
                "blocked by failed",
                "blocked by a failed",
                "dep.*fail",
            ),
        ),
        "skip_no_propagation": _matches_any(
            normalized,
            (
                r"skip.*does\s*not\s*propagat",
                r"skip.*not.*fail",
                r"skipped.*dep.*execut",
                r"skipped.*proceed",
                r"skip.*normal",
            ),
        ),
        "dag_ordering": _contains_any(
            normalized,
            (
                "topological",
                "topo_sort",
                "toposort",
                "dependency graph",
                "execution order",
                "dag",
                "directed acyclic",
            ),
        ),
        # --- Feature 3: Retry with exponential backoff ---
        "retry_mechanism": _contains_all_groups(
            normalized,
            ("retry", "max_retries", "retries", "attempt"),
            ("fail", "error", "except"),
        ),
        "exponential_backoff": _matches_any(
            normalized,
            (
                r"exponential.*backoff",
                r"backoff.*exponential",
                r"1s.*2s.*4s",
                r"1,\s*2,\s*4",
                r"2\s*\*\*",
                r"delay\s*\*\s*2",
                r"delay\s*\*=\s*2",
            ),
        ),
        "retry_exhaustion": _contains_any(
            normalized,
            (
                "exhausted",
                "all retries",
                "max retries reached",
                "attempt_count",
                "attempt count",
                "attempts == max",
            ),
        ),
        # --- Feature 4: Timeout handling ---
        "timeout_mechanism": _contains_all_groups(
            normalized,
            ("timeout", "timeout_seconds", "timed_out", "timed out"),
            ("terminat", "kill", "cancel", "signal", "interrupt", "raise"),
        ),
        "timeout_no_retry": _matches_any(
            normalized,
            (
                r"timed.?out.*not.*retr",
                r"timeout.*not.*retr",
                r"not.*retr.*timed.?out",
                r"timed_out.*skip.*retry",
                r"if.*timed_out.*break",
                r"if.*timed_out.*return",
            ),
        ),
        "timeout_as_failure": _matches_any(
            normalized,
            (
                r"timed.?out.*count.*fail",
                r"timed.?out.*treat.*fail",
                r"timed.?out.*propagat.*fail",
                r"timed_out.*dependency_failed",
            ),
        ),
        # --- Feature 5: Output capture ---
        "output_capture": _contains_all_groups(
            normalized,
            ("output", "capture", "stdout", "result"),
            ("context", "store", "dict", "context["),
        ),
        "template_resolution": _matches_any(
            normalized,
            (
                r"\{\{step",
                r"\{\{.*\}\}",
                r"template",
                r"interpolat",
                r"re\.sub",
                r"format.*\{",
                r"replace.*\{\{",
            ),
        ),
        # --- Feature 6: Sub-recipe delegation ---
        "sub_recipe_execution": _contains_any(
            normalized,
            (
                "sub_recipe",
                "sub-recipe",
                "child recipe",
                "child context",
                "child_context",
                "nested recipe",
            ),
        ),
        "context_isolation": _matches_any(
            normalized,
            (
                r"child.*context.*inherit",
                r"inherit.*parent.*context",
                r"context.*copy",
                r"context.*isol",
                r"propagate_outputs",
                r"propagate.*output",
            ),
        ),
        "sub_recipe_failure": _matches_any(
            normalized,
            (
                r"sub.?recipe.*fail",
                r"child.*fail.*parent",
                r"failed.*sub.?recipe",
                r"sub.?recipe.*not.*retr",
            ),
        ),
        # --- Cross-feature interactions ---
        "retry_output_replacement": _matches_any(
            normalized,
            (
                r"retr.*output.*replac",
                r"final.*output",
                r"overwrite.*output",
                r"context\[.*\]\s*=.*output",
                r"latest.*attempt",
            ),
        ),
        "focused_tests": _contains_all_groups(
            normalized,
            ("test_", "pytest", "assert ", "unittest", "def test"),
            ("condition", "retry", "timeout", "depend", "output", "sub_recipe"),
        ),
    }

    # --- Feature scores (each in [0, 1]) ---

    # Feature 1: Conditional execution (3 checks)
    cond_score = (
        sum(checks[c] for c in ("condition_evaluation", "condition_skip", "condition_missing_key"))
        / 3.0
    )

    # Feature 2: Dependency handling (4 checks)
    dep_score = (
        sum(
            checks[c]
            for c in (
                "dependency_graph",
                "failure_propagation",
                "skip_no_propagation",
                "dag_ordering",
            )
        )
        / 4.0
    )

    # Feature 3: Retry logic (3 checks)
    retry_score = (
        sum(checks[c] for c in ("retry_mechanism", "exponential_backoff", "retry_exhaustion")) / 3.0
    )

    # Feature 4: Timeout semantics (3 checks)
    timeout_score = (
        sum(checks[c] for c in ("timeout_mechanism", "timeout_no_retry", "timeout_as_failure"))
        / 3.0
    )

    # Feature 5: Output capture (2 checks)
    output_score = sum(checks[c] for c in ("output_capture", "template_resolution")) / 2.0

    # Feature 6: Sub-recipe delegation (3 checks)
    sub_recipe_score = (
        sum(
            checks[c]
            for c in (
                "sub_recipe_execution",
                "context_isolation",
                "sub_recipe_failure",
            )
        )
        / 3.0
    )

    # Map to the shared ConditionMetrics (6 slots) for compatibility with the
    # summarization and reporting pipeline:
    #   baseline_score -> conditional_execution
    #   invariant_compliance -> dependency_handling
    #   proof_alignment -> retry_logic
    #   local_protocol_alignment -> timeout_semantics
    #   progress_signal -> output_capture
    #   specification_coverage -> sub_recipe_delegation
    metrics = ConditionMetrics(
        baseline_score=round(cond_score, 4),
        invariant_compliance=round(dep_score, 4),
        proof_alignment=round(retry_score, 4),
        local_protocol_alignment=round(timeout_score, 4),
        progress_signal=round(output_score, 4),
        specification_coverage=round(sub_recipe_score, 4),
    )

    _gherkin_metrics = GherkinConditionMetrics(
        conditional_execution=round(cond_score, 4),
        dependency_handling=round(dep_score, 4),
        retry_logic=round(retry_score, 4),
        timeout_semantics=round(timeout_score, 4),
        output_capture=round(output_score, 4),
        sub_recipe_delegation=round(sub_recipe_score, 4),
    )

    notes = [
        "Gherkin v2 heuristic scoring for recipe step executor (6 features).",
        "Metric mapping: baseline_score=conditional_execution, "
        "invariant_compliance=dependency_handling, "
        "proof_alignment=retry_logic, "
        "local_protocol_alignment=timeout_semantics, "
        "progress_signal=output_capture, "
        "specification_coverage=sub_recipe_delegation.",
    ]
    for check_name, passed in checks.items():
        if not passed:
            notes.append(f"Missing heuristic signal: {check_name}")

    return HeuristicEvaluation(metrics=metrics, checks=checks, notes=notes)


# ---------------------------------------------------------------------------
# Gherkin v2 experiment runner — reuses shared pipeline with custom evaluation
# ---------------------------------------------------------------------------


def run_gherkin_v2_experiment(
    output_dir: str | Path,
    *,
    smoke: bool = False,
    manifest: ExperimentManifest | None = None,
    replay_dir: str | Path | None = None,
    allow_live: bool = False,
) -> ExperimentExecutionReport:
    """Run the gherkin v2 experiment with recipe-step-executor scoring."""

    resolved_manifest = manifest or load_gherkin_v2_manifest()
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
            # Use GHERKIN evaluation instead of TLA+ evaluation
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
            if exc.metadata.get("error"):
                failure_notes.append(f"runtime_error={exc.metadata['error']}")
            if exc.metadata.get("error_type"):
                failure_notes.append(f"runtime_error_type={exc.metadata['error_type']}")
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

    summary = summarize_condition_results(results)
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


# ---------------------------------------------------------------------------
# Gherkin-specific markdown report
# ---------------------------------------------------------------------------

# Gherkin metric labels for readable reports
_GHERKIN_METRIC_LABELS = {
    "baseline_score": "Conditional",
    "invariant_compliance": "Dependencies",
    "proof_alignment": "Retry",
    "local_protocol_alignment": "Timeout",
    "progress_signal": "Output",
    "specification_coverage": "SubRecipe",
}


def generate_gherkin_markdown_report(
    execution_report: ExperimentExecutionReport,
    results: list[ConditionRunResult],
    output_path: str | Path,
) -> Path:
    """Write a markdown report for a gherkin v2 experiment run."""

    output_file = Path(output_path)
    lines = [
        "# Gherkin v2 Recipe Step Executor Experiment Report",
        "",
        f"**Experiment ID**: `{execution_report.experiment_id}`",
        f"**Generated at**: `{execution_report.generated_at}`",
        f"**Matrix mode**: `{execution_report.matrix_mode}`",
        f"**Replay mode**: `{execution_report.replay_mode}`",
        f"**Evaluation kind**: `{GHERKIN_HEURISTIC_KIND}`",
        f"**Output dir**: `{execution_report.output_dir}`",
        "",
        "## Summary",
        "",
        f"- Total conditions: {execution_report.total_conditions}",
        f"- Completed conditions: {execution_report.completed_conditions}",
        f"- Failed conditions: {execution_report.failed_conditions}",
        "",
        "## Metric Mapping",
        "",
        "| Shared Metric Name | Gherkin Feature |",
        "|---|---|",
        "| baseline_score | Conditional Execution |",
        "| invariant_compliance | Dependency Handling |",
        "| proof_alignment | Retry Logic |",
        "| local_protocol_alignment | Timeout Semantics |",
        "| progress_signal | Output Capture |",
        "| specification_coverage | Sub-recipe Delegation |",
        "",
        "## Condition Table",
        "",
        "| Condition | Model | Prompt | Status | Conditional | Dependencies | Retry | Timeout | Output | SubRecipe |",
        "|-----------|-------|--------|--------|-------------|--------------|-------|---------|--------|-----------|",
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
                + ("; ".join(result.notes[:3]) if result.notes else "Failed without notes")
            )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Scores are heuristic local signals based on keyword/pattern matching.",
            "- Each feature score is the fraction of sub-checks that matched (0.0 to 1.0).",
            "- Cross-feature interaction checks contribute to individual feature scores.",
            "",
        ]
    )
    output_file.write_text("\n".join(lines))
    return output_file


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gherkin v2 recipe step executor prompt-language experiment.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
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
        help="Execute the experiment runner and write per-condition artifacts.",
    )
    parser.add_argument(
        "--replay-dir",
        type=Path,
        help="Read pre-generated artifacts from this directory.",
    )
    parser.add_argument(
        "--allow-live",
        action="store_true",
        help="Allow real SDK-backed model execution.",
    )
    parser.add_argument(
        "--summarize-results",
        type=Path,
        help="Read run_result.json files and print aggregate summary.",
    )
    args = parser.parse_args(argv)

    manifest_path = args.manifest or default_gherkin_v2_manifest_path()
    manifest = load_experiment_manifest(manifest_path)

    if args.run_dir:
        report = run_gherkin_v2_experiment(
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
        print(manifest.load_prompt_bundle(args.variant).combined_text(), end="")
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
