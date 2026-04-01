"""Gherkin v2 prompt-language experiment utilities for issue #3969.

This module implements a behavioral-specification prompt experiment targeting a
recipe step executor with 6 interacting features.  It reuses the shared
infrastructure from tla_prompt_experiment and provides Gherkin-specific:

- manifest loading (from experiments/hive_mind/gherkin_v2_recipe_executor/)
- agent-based consensus evaluation with 3+ independent LLM judges
- token and wall-clock time tracking for both generation and evaluation
- a thin CLI entry point that plugs into the same runner

V2 redesign: replaced the user-auth ceiling task (PR #3964) with a harder
recipe-step-executor target where models lack strong training priors and
cross-feature interactions create genuine ambiguity.

V3 scoring: replaced regex/keyword heuristic scoring with agent-based
consensus evaluation — multiple independent agents judge each feature
against the acceptance criteria rubric.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from amplihack.eval.gherkin_agent_evaluator import (
    EVALUATION_KIND,
    evaluate_with_consensus,
)
from amplihack.eval.tla_prompt_experiment import (
    ConditionRunResult,
    ExperimentExecutionReport,
    ExperimentManifest,
    PromptGenerationError,
    generate_condition_artifact,
    load_condition_result,
    load_experiment_manifest,
    materialize_condition_packets,
    summarize_condition_results,
)

DEFAULT_GHERKIN_V2_HOME = Path("experiments/hive_mind/gherkin_v2_recipe_executor")
DEFAULT_MANIFEST_NAME = "manifest.json"
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


# ---------------------------------------------------------------------------
# Evaluation asset loading
# ---------------------------------------------------------------------------


def _load_evaluation_assets(
    repo_root: Path | None = None,
) -> tuple[str, str, str]:
    """Load the acceptance criteria, .feature spec, and reference impl.

    Returns (acceptance_criteria, feature_spec, reference_impl).
    """
    root = repo_root or _repo_root()
    experiment_home = root / DEFAULT_GHERKIN_V2_HOME

    acceptance_criteria = (
        experiment_home / "specs" / "recipe_step_executor_acceptance_criteria.md"
    ).read_text()
    feature_spec = (experiment_home / "specs" / "recipe_step_executor.feature").read_text()
    reference_impl = (experiment_home / "reference" / "recipe_step_executor.py").read_text()

    return acceptance_criteria, feature_spec, reference_impl


# ---------------------------------------------------------------------------
# Token and timing tracking
# ---------------------------------------------------------------------------


@dataclass
class GenerationMetrics:
    """Timing and token metrics for one condition's generation phase."""

    generation_wall_clock_seconds: float = 0.0
    generation_input_tokens: int = 0
    generation_output_tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_wall_clock_seconds": round(self.generation_wall_clock_seconds, 2),
            "generation_input_tokens": self.generation_input_tokens,
            "generation_output_tokens": self.generation_output_tokens,
        }


@dataclass
class ConditionRunResultV2:
    """Extended run result with token/time tracking and consensus evaluation."""

    base_result: ConditionRunResult
    generation_metrics: GenerationMetrics = field(default_factory=GenerationMetrics)
    evaluation_metrics: dict[str, Any] | None = None  # from ConsensusEvaluation

    def to_dict(self) -> dict[str, Any]:
        data = self.base_result.to_dict()
        data["generation_metrics"] = self.generation_metrics.to_dict()
        if self.evaluation_metrics is not None:
            data["evaluation_metrics"] = self.evaluation_metrics
        return data


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------


def _compute_stats(values: list[float]) -> dict[str, float]:
    """Compute mean, stddev, min, max, and 95% CI half-width for a list of values."""
    n = len(values)
    if n == 0:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0, "ci95": 0.0, "n": 0}
    mean = sum(values) / n
    if n < 2:
        return {
            "mean": mean,
            "stddev": 0.0,
            "min": min(values),
            "max": max(values),
            "ci95": 0.0,
            "n": n,
        }
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    stddev = math.sqrt(variance)
    # t-value for 95% CI with n-1 degrees of freedom (approximation)
    t_values = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
    }
    t = t_values.get(n - 1, 1.96)  # fall back to z=1.96 for large n
    ci95 = t * stddev / math.sqrt(n)
    return {
        "mean": round(mean, 4),
        "stddev": round(stddev, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "ci95": round(ci95, 4),
        "n": n,
    }


# ---------------------------------------------------------------------------
# Gherkin v2 experiment runner — agent-based consensus evaluation
# ---------------------------------------------------------------------------


def run_gherkin_v2_experiment(
    output_dir: str | Path,
    *,
    smoke: bool = False,
    manifest: ExperimentManifest | None = None,
    replay_dir: str | Path | None = None,
    allow_live: bool = False,
    num_evaluator_agents: int = 3,
    evaluator_model: str = "claude-sonnet-4-20250514",
) -> ExperimentExecutionReport:
    """Run the gherkin v2 experiment with agent-based consensus scoring.

    Args:
        output_dir: Directory to write per-condition results.
        smoke: If True, use smoke matrix (fewer repeats).
        manifest: Experiment manifest (loaded from default path if None).
        replay_dir: If set, read pre-generated artifacts instead of live generation.
        allow_live: If True, allow real SDK-backed generation.
        num_evaluator_agents: Number of independent evaluator agents per condition.
        evaluator_model: Model to use for evaluator agents.
    """
    resolved_manifest = manifest or load_gherkin_v2_manifest()
    replay_root = Path(replay_dir) if replay_dir is not None else None
    if replay_root is None and not allow_live:
        raise ValueError(
            "Live generation is disabled by default. Supply replay_dir or pass allow_live=True / --allow-live."
        )
    packets = materialize_condition_packets(output_dir, smoke=smoke, manifest=resolved_manifest)

    # Load evaluation rubric assets once
    acceptance_criteria, feature_spec, reference_impl = _load_evaluation_assets()

    results: list[ConditionRunResult] = []
    extended_results: list[ConditionRunResultV2] = []

    for packet in packets:
        condition_dir = Path(packet.condition_dir)
        generated_file = condition_dir / "generated_artifact.md"
        raw_response_file = condition_dir / "raw_response.txt"
        evaluation_file = condition_dir / "evaluation.json"
        run_result_file = condition_dir / "run_result.json"

        gen_metrics = GenerationMetrics()
        gen_start = time.monotonic()

        try:
            bundle = resolved_manifest.load_prompt_bundle(packet.condition.prompt_variant_id)

            # --- Generation phase with timing ---
            generated = generate_condition_artifact(
                packet.condition,
                bundle.combined_text(),
                work_dir=condition_dir,
                replay_dir=replay_root,
                allow_live=allow_live,
            )
            gen_metrics.generation_wall_clock_seconds = time.monotonic() - gen_start

            # Extract token counts from generation metadata if available
            gen_metrics.generation_input_tokens = int(generated.metadata.get("input_tokens", 0))
            gen_metrics.generation_output_tokens = int(generated.metadata.get("output_tokens", 0))

            generated_file.write_text(generated.response_text)
            raw_response_file.write_text(generated.response_text)

            # --- Evaluation phase: agent-based consensus ---
            consensus = evaluate_with_consensus(
                generated_code=generated.response_text,
                acceptance_criteria=acceptance_criteria,
                feature_spec=feature_spec,
                reference_impl=reference_impl,
                num_agents=num_evaluator_agents,
                model=evaluator_model,
                work_dir=condition_dir / "eval_work",
            )
            evaluation_file.write_text(json.dumps(consensus.to_dict(), indent=2) + "\n")

            generation_notes = [
                f"generation_provider={generated.provider}",
                f"evaluation_kind={EVALUATION_KIND}",
                f"evaluator_agents={num_evaluator_agents}",
                f"evaluator_model={evaluator_model}",
                f"generation_seconds={gen_metrics.generation_wall_clock_seconds:.1f}",
                f"eval_seconds={consensus.total_wall_clock_seconds:.1f}",
                f"eval_input_tokens={consensus.total_input_tokens}",
                f"eval_output_tokens={consensus.total_output_tokens}",
            ]
            runtime_model_id = generated.metadata.get("runtime_model_id")
            if runtime_model_id and runtime_model_id != packet.condition.model_id:
                generation_notes.append(f"runtime_model_id={runtime_model_id}")
            generation_notes.extend(consensus.notes)

            result = ConditionRunResult(
                condition=packet.condition,
                status="completed",
                metrics=consensus.metrics,
                generated_artifact_path=str(generated_file),
                evaluation_artifact_path=str(evaluation_file),
                raw_response_path=str(raw_response_file),
                notes=generation_notes,
            )
            ext_result = ConditionRunResultV2(
                base_result=result,
                generation_metrics=gen_metrics,
                evaluation_metrics={
                    "eval_input_tokens": consensus.total_input_tokens,
                    "eval_output_tokens": consensus.total_output_tokens,
                    "eval_wall_clock_seconds": round(consensus.total_wall_clock_seconds, 2),
                    "consensus_scores": {
                        k: round(v, 4) for k, v in consensus.consensus_scores.items()
                    },
                },
            )

        except PromptGenerationError as exc:
            gen_metrics.generation_wall_clock_seconds = time.monotonic() - gen_start
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
            ext_result = ConditionRunResultV2(base_result=result, generation_metrics=gen_metrics)

        except Exception as exc:
            result = ConditionRunResult(
                condition=packet.condition,
                status="failed",
                notes=[str(exc)],
            )
            ext_result = ConditionRunResultV2(base_result=result, generation_metrics=gen_metrics)

        # Write extended result (includes generation_metrics and evaluation_metrics)
        run_result_file.write_text(json.dumps(ext_result.to_dict(), indent=2) + "\n")
        results.append(result)
        extended_results.append(ext_result)

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
    generate_gherkin_markdown_report(
        report, results, extended_results, output_root / "experiment_report.md"
    )
    return report


# ---------------------------------------------------------------------------
# Gherkin-specific markdown report with statistics
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

_GHERKIN_METRIC_ORDER = [
    "baseline_score",
    "invariant_compliance",
    "proof_alignment",
    "local_protocol_alignment",
    "progress_signal",
    "specification_coverage",
]


def generate_gherkin_markdown_report(
    execution_report: ExperimentExecutionReport,
    results: list[ConditionRunResult],
    extended_results: list[ConditionRunResultV2],
    output_path: str | Path,
) -> Path:
    """Write a markdown report with per-condition scores, stats, and token usage."""

    output_file = Path(output_path)
    lines = [
        "# Gherkin v2 Recipe Step Executor Experiment Report",
        "",
        f"**Experiment ID**: `{execution_report.experiment_id}`",
        f"**Generated at**: `{execution_report.generated_at}`",
        f"**Matrix mode**: `{execution_report.matrix_mode}`",
        f"**Replay mode**: `{execution_report.replay_mode}`",
        f"**Evaluation kind**: `{EVALUATION_KIND}`",
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
        "| Condition | Model | Prompt | Status | Cond | Deps | Retry | T/O | Output | SubRec | Gen(s) | Eval(s) | Eval Tokens |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for result, ext in zip(results, extended_results, strict=False):
        m = result.metrics
        gm = ext.generation_metrics
        em = ext.evaluation_metrics or {}
        eval_tokens = em.get("eval_input_tokens", 0) + em.get("eval_output_tokens", 0)
        lines.append(
            f"| {result.condition.condition_id} "
            f"| {result.condition.model_id} "
            f"| {result.condition.prompt_variant_id} "
            f"| {result.status} "
            f"| {m.baseline_score if m.baseline_score is not None else '--'} "
            f"| {m.invariant_compliance if m.invariant_compliance is not None else '--'} "
            f"| {m.proof_alignment if m.proof_alignment is not None else '--'} "
            f"| {m.local_protocol_alignment if m.local_protocol_alignment is not None else '--'} "
            f"| {m.progress_signal if m.progress_signal is not None else '--'} "
            f"| {m.specification_coverage if m.specification_coverage is not None else '--'} "
            f"| {gm.generation_wall_clock_seconds:.1f} "
            f"| {em.get('eval_wall_clock_seconds', 0):.1f} "
            f"| {eval_tokens} |"
        )

    # --- Per-variant statistics ---
    completed = [
        (r, e) for r, e in zip(results, extended_results, strict=False) if r.status == "completed"
    ]
    if completed:
        # Group by prompt variant
        by_variant: dict[str, list[ConditionRunResult]] = {}
        for r, _ in completed:
            by_variant.setdefault(r.condition.prompt_variant_id, []).append(r)

        lines.extend(["", "## Per-Variant Statistics", ""])
        lines.append("| Variant | N | Cond | Deps | Retry | T/O | Output | SubRec | AVG |")
        lines.append("|---|---|---|---|---|---|---|---|---|")

        for variant_id, variant_results in sorted(by_variant.items()):
            n = len(variant_results)
            metric_values: dict[str, list[float]] = {k: [] for k in _GHERKIN_METRIC_ORDER}
            for r in variant_results:
                for k in _GHERKIN_METRIC_ORDER:
                    v = getattr(r.metrics, k)
                    if v is not None:
                        metric_values[k].append(v)

            stats = {k: _compute_stats(metric_values[k]) for k in _GHERKIN_METRIC_ORDER}
            all_means = [stats[k]["mean"] for k in _GHERKIN_METRIC_ORDER if stats[k]["n"] > 0]
            avg = sum(all_means) / len(all_means) if all_means else 0.0

            def _fmt(s: dict[str, float]) -> str:
                if s["n"] < 2:
                    return f"{s['mean']:.3f}"
                return f"{s['mean']:.3f} +/-{s['ci95']:.3f}"

            lines.append(
                f"| {variant_id} | {n} "
                f"| {_fmt(stats['baseline_score'])} "
                f"| {_fmt(stats['invariant_compliance'])} "
                f"| {_fmt(stats['proof_alignment'])} "
                f"| {_fmt(stats['local_protocol_alignment'])} "
                f"| {_fmt(stats['progress_signal'])} "
                f"| {_fmt(stats['specification_coverage'])} "
                f"| {avg:.3f} |"
            )

    # --- Token usage summary ---
    lines.extend(["", "## Token Usage Summary", ""])
    total_gen_tokens = sum(
        e.generation_metrics.generation_input_tokens + e.generation_metrics.generation_output_tokens
        for e in extended_results
    )
    total_eval_tokens = sum(
        (e.evaluation_metrics or {}).get("eval_input_tokens", 0)
        + (e.evaluation_metrics or {}).get("eval_output_tokens", 0)
        for e in extended_results
    )
    total_gen_seconds = sum(
        e.generation_metrics.generation_wall_clock_seconds for e in extended_results
    )
    total_eval_seconds = sum(
        (e.evaluation_metrics or {}).get("eval_wall_clock_seconds", 0) for e in extended_results
    )
    lines.extend(
        [
            f"- Total generation tokens: {total_gen_tokens:,}",
            f"- Total evaluation tokens: {total_eval_tokens:,}",
            f"- Total generation time: {total_gen_seconds:.1f}s",
            f"- Total evaluation time: {total_eval_seconds:.1f}s",
        ]
    )

    # --- Failures ---
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
            f"- Evaluation uses {EVALUATION_KIND}: multiple independent LLM agents judge each feature.",
            "- Consensus score = fraction of agents voting PASS per feature.",
            "- Statistics include mean, 95% CI (t-distribution) when N >= 2.",
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
        "--num-evaluators",
        type=int,
        default=3,
        help="Number of independent evaluator agents (default: 3).",
    )
    parser.add_argument(
        "--evaluator-model",
        default="claude-sonnet-4-20250514",
        help="Model to use for evaluator agents.",
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
            num_evaluator_agents=args.num_evaluators,
            evaluator_model=args.evaluator_model,
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
