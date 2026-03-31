"""TLA+ prompt-language experiment utilities for issue #3497.

This module implements the first concrete slice of the planned experiment:

- a machine-readable manifest for the experiment matrix
- prompt/spec asset loading
- smoke/full matrix expansion
- deterministic JSON export for downstream runners

The scoped generation target for this first slice is the distributed retrieval
contract, not a full greenfield distributed hive implementation.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Self

DEFAULT_EXPERIMENT_HOME = Path("experiments/hive_mind/tla_prompt_language")
DEFAULT_MANIFEST_NAME = "manifest.json"
SUPPORTED_MODEL_SDKS = {"claude", "copilot", "microsoft", "mini"}
REPLAY_ARTIFACT_FILENAMES = (
    "generated_artifact.md",
    "generated_response.md",
    "output.md",
    "output.txt",
)
LIVE_GENERATION_SYSTEM_PROMPT = (
    "You are participating in a controlled code-generation experiment. "
    "Follow the user prompt exactly, stay within scope, and return only the "
    "requested implementation artifact and focused tests without extra commentary."
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _slug(value: str) -> str:
    return value.replace(".", "_").replace("-", "_").replace("/", "_")


def _require_non_empty(value: str, field_name: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    return value


def _require_non_empty_list(values: list[Any], field_name: str) -> list[Any]:
    if not values:
        raise ValueError(f"{field_name} cannot be empty")
    return values


def default_manifest_path(repo_root: str | Path | None = None) -> Path:
    root = Path(repo_root) if repo_root is not None else _repo_root()
    return root / DEFAULT_EXPERIMENT_HOME / DEFAULT_MANIFEST_NAME


@dataclass
class GenerationTarget:
    """Scoped generation target for a prompt-language experiment."""

    target_id: str
    summary: str
    deliverables: list[str]
    non_goals: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            target_id=_require_non_empty(data["target_id"], "generation_target.target_id"),
            summary=_require_non_empty(data["summary"], "generation_target.summary"),
            deliverables=_require_non_empty_list(
                list(data["deliverables"]),
                "generation_target.deliverables",
            ),
            non_goals=_require_non_empty_list(
                list(data["non_goals"]),
                "generation_target.non_goals",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "summary": self.summary,
            "deliverables": list(self.deliverables),
            "non_goals": list(self.non_goals),
        }


@dataclass
class PromptVariantAsset:
    """Metadata for a prompt variant bundled with an experiment."""

    variant_id: str
    label: str
    path: str
    append_spec: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            variant_id=_require_non_empty(data["variant_id"], "prompt_variants.variant_id"),
            label=_require_non_empty(data["label"], "prompt_variants.label"),
            path=_require_non_empty(data["path"], "prompt_variants.path"),
            append_spec=bool(data.get("append_spec", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "label": self.label,
            "path": self.path,
            "append_spec": self.append_spec,
        }


@dataclass
class ModelVariant:
    """Metadata for a model included in the matrix."""

    model_id: str
    label: str
    sdk: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        sdk = _require_non_empty(data["sdk"], "models.sdk")
        if sdk not in SUPPORTED_MODEL_SDKS:
            raise ValueError(
                f"models.sdk must be one of {sorted(SUPPORTED_MODEL_SDKS)}; got {sdk!r}"
            )
        return cls(
            model_id=_require_non_empty(data["model_id"], "models.model_id"),
            label=_require_non_empty(data["label"], "models.label"),
            sdk=sdk,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "label": self.label,
            "sdk": self.sdk,
        }


@dataclass
class PromptBundle:
    """Resolved prompt and spec assets for a single prompt variant."""

    experiment_id: str
    target_id: str
    variant_id: str
    prompt_path: str
    spec_path: str
    prompt_text: str
    spec_text: str
    append_spec: bool

    def combined_text(self) -> str:
        prompt_text = self.prompt_text.rstrip()
        if not self.append_spec:
            return f"{prompt_text}\n"
        spec_text = self.spec_text.rstrip()
        return (
            f"{prompt_text}\n\n"
            "## Formal specification\n\n"
            "```tla\n"
            f"{spec_text}\n"
            "```\n"
        )


@dataclass
class ExperimentCondition:
    """One model/prompt/repeat condition from the experiment matrix."""

    experiment_id: str
    target_id: str
    model_id: str
    model_sdk: str
    prompt_variant_id: str
    repeat_index: int
    prompt_path: str
    spec_path: str
    tlc_config_path: str | None = None

    @property
    def condition_id(self) -> str:
        return (
            f"{_slug(self.model_id)}__{_slug(self.prompt_variant_id)}__r{self.repeat_index}"
        )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "condition_id": self.condition_id,
            "experiment_id": self.experiment_id,
            "target_id": self.target_id,
            "model_id": self.model_id,
            "model_sdk": self.model_sdk,
            "prompt_variant_id": self.prompt_variant_id,
            "repeat_index": self.repeat_index,
            "prompt_path": self.prompt_path,
            "spec_path": self.spec_path,
        }
        if self.tlc_config_path is not None:
            data["tlc_config_path"] = self.tlc_config_path
        return data


@dataclass
class MaterializedCondition:
    """Filesystem packet for one experiment condition."""

    condition: ExperimentCondition
    condition_dir: str
    prompt_file: str
    spec_file: str
    metadata_file: str
    tlc_config_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "condition": self.condition.to_dict(),
            "condition_dir": self.condition_dir,
            "prompt_file": self.prompt_file,
            "spec_file": self.spec_file,
            "metadata_file": self.metadata_file,
        }
        if self.tlc_config_file is not None:
            data["tlc_config_file"] = self.tlc_config_file
        return data


@dataclass
class SpecValidationResult:
    """Result from validating the scoped TLA+ spec with TLC."""

    runner_kind: str
    command: list[str]
    cwd: str
    returncode: int
    stdout: str
    stderr: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "runner_kind": self.runner_kind,
            "command": list(self.command),
            "cwd": self.cwd,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


@dataclass
class ConditionMetrics:
    """Score bundle for one completed condition."""

    baseline_score: float | None = None
    invariant_compliance: float | None = None
    proof_alignment: float | None = None
    specification_coverage: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            baseline_score=data.get("baseline_score"),
            invariant_compliance=data.get("invariant_compliance"),
            proof_alignment=data.get("proof_alignment"),
            specification_coverage=data.get("specification_coverage"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_score": self.baseline_score,
            "invariant_compliance": self.invariant_compliance,
            "proof_alignment": self.proof_alignment,
            "specification_coverage": self.specification_coverage,
        }


@dataclass
class ConditionRunResult:
    """Recorded outcome for one materialized experiment condition."""

    condition: ExperimentCondition
    status: str  # planned | completed | failed
    metrics: ConditionMetrics = field(default_factory=ConditionMetrics)
    generated_artifact_path: str | None = None
    evaluation_artifact_path: str | None = None
    notes: list[str] = field(default_factory=list)
    raw_response_path: str | None = None
    tlc_validation: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            condition=ExperimentCondition(
                experiment_id=data["condition"]["experiment_id"],
                target_id=data["condition"]["target_id"],
                model_id=data["condition"]["model_id"],
                model_sdk=data["condition"]["model_sdk"],
                prompt_variant_id=data["condition"]["prompt_variant_id"],
                repeat_index=int(data["condition"]["repeat_index"]),
                prompt_path=data["condition"]["prompt_path"],
                spec_path=data["condition"]["spec_path"],
                tlc_config_path=data["condition"].get("tlc_config_path"),
            ),
            status=_require_non_empty(data["status"], "status"),
            metrics=ConditionMetrics.from_dict(data.get("metrics", {})),
            generated_artifact_path=data.get("generated_artifact_path"),
            evaluation_artifact_path=data.get("evaluation_artifact_path"),
            notes=list(data.get("notes", [])),
            raw_response_path=data.get("raw_response_path"),
            tlc_validation=data.get("tlc_validation"),
        )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "condition": self.condition.to_dict(),
            "status": self.status,
            "metrics": self.metrics.to_dict(),
            "notes": list(self.notes),
        }
        if self.generated_artifact_path is not None:
            data["generated_artifact_path"] = self.generated_artifact_path
        if self.evaluation_artifact_path is not None:
            data["evaluation_artifact_path"] = self.evaluation_artifact_path
        if self.raw_response_path is not None:
            data["raw_response_path"] = self.raw_response_path
        if self.tlc_validation is not None:
            data["tlc_validation"] = self.tlc_validation
        return data


@dataclass
class MetricSummary:
    """Aggregate mean for a metric across completed conditions."""

    mean: float
    count: int

    def to_dict(self) -> dict[str, Any]:
        return {"mean": round(self.mean, 4), "count": self.count}


@dataclass
class ExperimentSummaryReport:
    """Aggregate summary across recorded condition results."""

    experiment_id: str
    total_conditions: int
    completed_conditions: int
    failed_conditions: int
    metric_summary: dict[str, MetricSummary]
    by_prompt_variant: dict[str, dict[str, MetricSummary]]
    by_model: dict[str, dict[str, MetricSummary]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "total_conditions": self.total_conditions,
            "completed_conditions": self.completed_conditions,
            "failed_conditions": self.failed_conditions,
            "metric_summary": {
                key: value.to_dict() for key, value in self.metric_summary.items()
            },
            "by_prompt_variant": {
                key: {metric: summary.to_dict() for metric, summary in value.items()}
                for key, value in self.by_prompt_variant.items()
            },
            "by_model": {
                key: {metric: summary.to_dict() for metric, summary in value.items()}
                for key, value in self.by_model.items()
            },
        }


@dataclass
class PromptGenerationResult:
    """Generated artifact text for one experiment condition."""

    response_text: str
    provider: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HeuristicEvaluation:
    """Heuristic first-slice evaluation of a generated artifact."""

    metrics: ConditionMetrics
    checks: dict[str, bool]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics": self.metrics.to_dict(),
            "checks": dict(self.checks),
            "notes": list(self.notes),
        }


@dataclass
class ExperimentExecutionReport:
    """Aggregate report for one local experiment execution."""

    experiment_id: str
    matrix_mode: str
    output_dir: str
    generated_at: str
    total_conditions: int
    completed_conditions: int
    failed_conditions: int
    summary: ExperimentSummaryReport
    replay_mode: bool
    tlc_validation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "experiment_id": self.experiment_id,
            "matrix_mode": self.matrix_mode,
            "output_dir": self.output_dir,
            "generated_at": self.generated_at,
            "total_conditions": self.total_conditions,
            "completed_conditions": self.completed_conditions,
            "failed_conditions": self.failed_conditions,
            "summary": self.summary.to_dict(),
            "replay_mode": self.replay_mode,
        }
        if self.tlc_validation is not None:
            payload["tlc_validation"] = self.tlc_validation
        return payload


@dataclass
class ExperimentManifest:
    """Manifest for the issue #3497 TLA+ prompt-language experiment."""

    experiment_id: str
    title: str
    experiment_home: str
    generation_target: GenerationTarget
    spec_asset: str
    prompt_variants: list[PromptVariantAsset]
    models: list[ModelVariant]
    result_schema_version: int = 1
    tlc_config_asset: str | None = None
    smoke_repeats: int = 1
    full_repeats: int = 3
    fairness_rules: list[str] = field(default_factory=list)
    ownership_notes: list[str] = field(default_factory=list)
    _base_dir: Path | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, base_dir: Path | None = None) -> Self:
        manifest = cls(
            experiment_id=_require_non_empty(data["experiment_id"], "experiment_id"),
            title=_require_non_empty(data["title"], "title"),
            experiment_home=_require_non_empty(data["experiment_home"], "experiment_home"),
            generation_target=GenerationTarget.from_dict(data["generation_target"]),
            spec_asset=_require_non_empty(data["spec_asset"], "spec_asset"),
            prompt_variants=_require_non_empty_list(
                [PromptVariantAsset.from_dict(item) for item in data["prompt_variants"]],
                "prompt_variants",
            ),
            models=_require_non_empty_list(
                [ModelVariant.from_dict(item) for item in data["models"]],
                "models",
            ),
            result_schema_version=int(data.get("result_schema_version", 1)),
            tlc_config_asset=data.get("tlc_config_asset"),
            smoke_repeats=int(data.get("smoke_repeats", 1)),
            full_repeats=int(data.get("full_repeats", 3)),
            fairness_rules=list(data.get("fairness_rules", [])),
            ownership_notes=list(data.get("ownership_notes", [])),
        )
        manifest._base_dir = base_dir
        manifest.validate()
        return manifest

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        manifest_path = Path(path)
        data = json.loads(manifest_path.read_text())
        return cls.from_dict(data, base_dir=manifest_path.parent)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "experiment_id": self.experiment_id,
            "title": self.title,
            "experiment_home": self.experiment_home,
            "generation_target": self.generation_target.to_dict(),
            "spec_asset": self.spec_asset,
            "prompt_variants": [item.to_dict() for item in self.prompt_variants],
            "models": [item.to_dict() for item in self.models],
            "result_schema_version": self.result_schema_version,
            "smoke_repeats": self.smoke_repeats,
            "full_repeats": self.full_repeats,
            "fairness_rules": list(self.fairness_rules),
            "ownership_notes": list(self.ownership_notes),
        }
        if self.tlc_config_asset is not None:
            data["tlc_config_asset"] = self.tlc_config_asset
        return data

    def validate(self) -> None:
        if self.smoke_repeats < 1:
            raise ValueError("smoke_repeats must be >= 1")
        if self.full_repeats < self.smoke_repeats:
            raise ValueError("full_repeats must be >= smoke_repeats")
        prompt_ids = [item.variant_id for item in self.prompt_variants]
        if len(prompt_ids) != len(set(prompt_ids)):
            raise ValueError("prompt_variants.variant_id values must be unique")
        model_ids = [item.model_id for item in self.models]
        if len(model_ids) != len(set(model_ids)):
            raise ValueError("models.model_id values must be unique")
        if self._base_dir is not None:
            self._require_asset(self.spec_asset, "spec_asset")
            if self.tlc_config_asset is not None:
                self._require_asset(self.tlc_config_asset, "tlc_config_asset")
            for item in self.prompt_variants:
                self._require_asset(item.path, f"prompt_variants[{item.variant_id}]")

    def _require_asset(self, relative_path: str, field_name: str) -> Path:
        asset_path = self.resolve_asset_path(relative_path)
        if not asset_path.exists():
            raise ValueError(f"{field_name} does not exist: {asset_path}")
        return asset_path

    def resolve_asset_path(self, relative_path: str) -> Path:
        if self._base_dir is None:
            raise ValueError("Manifest base directory is unknown; load from a file or pass base_dir")
        return self._base_dir / relative_path

    def get_prompt_variant(self, variant_id: str) -> PromptVariantAsset:
        for item in self.prompt_variants:
            if item.variant_id == variant_id:
                return item
        raise KeyError(f"Unknown prompt variant: {variant_id}")

    def load_prompt_bundle(self, variant_id: str) -> PromptBundle:
        prompt_variant = self.get_prompt_variant(variant_id)
        prompt_path = self.resolve_asset_path(prompt_variant.path)
        spec_path = self.resolve_asset_path(self.spec_asset)
        return PromptBundle(
            experiment_id=self.experiment_id,
            target_id=self.generation_target.target_id,
            variant_id=variant_id,
            prompt_path=str(prompt_path),
            spec_path=str(spec_path),
            prompt_text=prompt_path.read_text(),
            spec_text=spec_path.read_text(),
            append_spec=prompt_variant.append_spec,
        )

    def expand_matrix(self, *, smoke: bool = False) -> list[ExperimentCondition]:
        repeats = self.smoke_repeats if smoke else self.full_repeats
        spec_path = str(self.resolve_asset_path(self.spec_asset))
        tlc_config_path = (
            str(self.resolve_asset_path(self.tlc_config_asset))
            if self.tlc_config_asset is not None
            else None
        )
        conditions: list[ExperimentCondition] = []
        for model in self.models:
            for prompt_variant in self.prompt_variants:
                prompt_path = str(self.resolve_asset_path(prompt_variant.path))
                for repeat_index in range(1, repeats + 1):
                    conditions.append(
                        ExperimentCondition(
                            experiment_id=self.experiment_id,
                            target_id=self.generation_target.target_id,
                            model_id=model.model_id,
                            model_sdk=model.sdk,
                            prompt_variant_id=prompt_variant.variant_id,
                            repeat_index=repeat_index,
                            prompt_path=prompt_path,
                            spec_path=spec_path,
                            tlc_config_path=tlc_config_path,
                        )
                    )
        return conditions


def load_experiment_manifest(path: str | Path) -> ExperimentManifest:
    return ExperimentManifest.from_file(path)


def load_default_experiment_manifest(repo_root: str | Path | None = None) -> ExperimentManifest:
    return load_experiment_manifest(default_manifest_path(repo_root))


def write_condition_matrix(
    output_path: str | Path,
    *,
    smoke: bool = False,
    manifest: ExperimentManifest | None = None,
) -> Path:
    resolved_manifest = manifest or load_default_experiment_manifest()
    output_file = Path(output_path)
    payload = {
        "experiment_id": resolved_manifest.experiment_id,
        "target_id": resolved_manifest.generation_target.target_id,
        "matrix_mode": "smoke" if smoke else "full",
        "conditions": [item.to_dict() for item in resolved_manifest.expand_matrix(smoke=smoke)],
    }
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(payload, indent=2) + "\n")
    return output_file


def materialize_condition_packets(
    output_dir: str | Path,
    *,
    smoke: bool = False,
    manifest: ExperimentManifest | None = None,
) -> list[MaterializedCondition]:
    resolved_manifest = manifest or load_default_experiment_manifest()
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    packets: list[MaterializedCondition] = []

    for condition in resolved_manifest.expand_matrix(smoke=smoke):
        bundle = resolved_manifest.load_prompt_bundle(condition.prompt_variant_id)
        condition_dir = root / condition.condition_id
        condition_dir.mkdir(parents=True, exist_ok=True)

        prompt_file = condition_dir / "prompt.md"
        spec_file = condition_dir / Path(condition.spec_path).name
        metadata_file = condition_dir / "condition.json"

        prompt_file.write_text(bundle.combined_text())
        spec_file.write_text(bundle.spec_text)

        packet_dict = condition.to_dict()
        packet_dict["materialized_prompt_file"] = str(prompt_file)
        packet_dict["materialized_spec_file"] = str(spec_file)

        tlc_config_file: Path | None = None
        if condition.tlc_config_path is not None:
            tlc_config_file = condition_dir / Path(condition.tlc_config_path).name
            tlc_config_file.write_text(Path(condition.tlc_config_path).read_text())
            packet_dict["materialized_tlc_config_file"] = str(tlc_config_file)

        metadata_file.write_text(json.dumps(packet_dict, indent=2) + "\n")

        packets.append(
            MaterializedCondition(
                condition=condition,
                condition_dir=str(condition_dir),
                prompt_file=str(prompt_file),
                spec_file=str(spec_file),
                metadata_file=str(metadata_file),
                tlc_config_file=str(tlc_config_file) if tlc_config_file is not None else None,
            )
        )

    manifest_file = root / "matrix.json"
    write_condition_matrix(manifest_file, smoke=smoke, manifest=resolved_manifest)
    return packets


def build_tlc_command(
    spec_path: str | Path,
    config_path: str | Path,
    *,
    tlc_bin: str | None = None,
    java_bin: str | None = None,
    tla2tools_jar: str | None = None,
) -> tuple[list[str], str]:
    """Build a TLC command using either a native binary or Java + tla2tools."""

    spec_file = Path(spec_path)
    cfg_file = Path(config_path)
    if spec_file.suffix != ".tla":
        raise ValueError("spec_path must point to a .tla file")
    if cfg_file.suffix != ".cfg":
        raise ValueError("config_path must point to a .cfg file")

    resolved_tlc_bin = tlc_bin or os.environ.get("TLA_TLC_BIN") or shutil.which("tlc")
    if resolved_tlc_bin:
        return [resolved_tlc_bin, "-config", cfg_file.name, spec_file.stem], "tlc"

    resolved_jar = tla2tools_jar or os.environ.get("TLA2TOOLS_JAR")
    resolved_java_bin = java_bin or shutil.which("java")
    if resolved_jar and resolved_java_bin:
        return (
            [
                resolved_java_bin,
                "-cp",
                resolved_jar,
                "tlc2.TLC",
                "-config",
                cfg_file.name,
                spec_file.stem,
            ],
            "java",
        )

    raise RuntimeError(
        "No TLC runner available. Set TLA_TLC_BIN for a native tlc binary or "
        "set TLA2TOOLS_JAR (with java available) for Java-based TLC validation."
    )


def validate_spec_assets(
    manifest: ExperimentManifest,
    *,
    tlc_bin: str | None = None,
    java_bin: str | None = None,
    tla2tools_jar: str | None = None,
) -> SpecValidationResult:
    """Run TLC against the manifest's scoped spec and config."""

    if manifest.tlc_config_asset is None:
        raise ValueError("Manifest has no tlc_config_asset configured")

    spec_path = manifest.resolve_asset_path(manifest.spec_asset)
    config_path = manifest.resolve_asset_path(manifest.tlc_config_asset)
    command, runner_kind = build_tlc_command(
        spec_path,
        config_path,
        tlc_bin=tlc_bin,
        java_bin=java_bin,
        tla2tools_jar=tla2tools_jar,
    )
    completed = subprocess.run(
        command,
        cwd=spec_path.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    result = SpecValidationResult(
        runner_kind=runner_kind,
        command=command,
        cwd=str(spec_path.parent),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "TLC validation failed for "
            f"{spec_path.name} with return code {result.returncode}.\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def write_condition_result(output_path: str | Path, result: ConditionRunResult) -> Path:
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(result.to_dict(), indent=2) + "\n")
    return output_file


def load_condition_result(path: str | Path) -> ConditionRunResult:
    return ConditionRunResult.from_dict(json.loads(Path(path).read_text()))


def _summarize_metric(values: list[float]) -> MetricSummary | None:
    if not values:
        return None
    return MetricSummary(mean=sum(values) / len(values), count=len(values))


def summarize_condition_results(results: list[ConditionRunResult]) -> ExperimentSummaryReport:
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
            "specification_coverage": [],
        }
        for item in items:
            metrics = item.metrics
            if metrics.baseline_score is not None:
                metric_values["baseline_score"].append(metrics.baseline_score)
            if metrics.invariant_compliance is not None:
                metric_values["invariant_compliance"].append(metrics.invariant_compliance)
            if metrics.proof_alignment is not None:
                metric_values["proof_alignment"].append(metrics.proof_alignment)
            if metrics.specification_coverage is not None:
                metric_values["specification_coverage"].append(metrics.specification_coverage)
        summary: dict[str, MetricSummary] = {}
        for metric_name, values in metric_values.items():
            metric_summary = _summarize_metric(values)
            if metric_summary is not None:
                summary[metric_name] = metric_summary
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


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def evaluate_generated_artifact(text: str) -> HeuristicEvaluation:
    """Evaluate a generated artifact with explicit first-slice heuristics."""

    normalized = text.lower()
    checks = {
        "preserves_original_question": _contains_any(
            normalized,
            (
                "original question",
                "original_question",
                "preserve the question",
                "question preservation",
            ),
        ),
        "fans_out_all_agents": _contains_any(
            normalized,
            (
                "all active agents",
                "all agents",
                "fan out",
                "fan-out",
                "broadcast",
                "participating agents",
                "for agent in",
            ),
        ),
        "deterministic_merge": _contains_any(
            normalized,
            (
                "deterministic",
                "stable order",
                "arrival order",
                "sorted(",
                "sort(",
            ),
        ),
        "explicit_failure_surface": _contains_any(
            normalized,
            (
                "explicit failure",
                "shard failure",
                "failed_agents",
                "failedagents",
                "raise ",
                "error",
                "exception",
            ),
        ),
        "focused_tests": _contains_any(
            normalized,
            (
                "test_",
                "pytest",
                "assert ",
                "unittest",
                "focused tests",
            ),
        ),
        "spec_alignment": _contains_any(
            normalized,
            (
                "tla",
                "invariant",
                "specification",
                "distributedretrievalcontract",
            ),
        ),
    }
    baseline_numerator = sum(
        checks[name]
        for name in (
            "preserves_original_question",
            "fans_out_all_agents",
            "deterministic_merge",
            "explicit_failure_surface",
            "focused_tests",
        )
    )
    invariant_numerator = sum(
        checks[name]
        for name in (
            "preserves_original_question",
            "fans_out_all_agents",
            "deterministic_merge",
            "explicit_failure_surface",
        )
    )
    coverage_numerator = sum(
        checks[name]
        for name in (
            "preserves_original_question",
            "fans_out_all_agents",
            "deterministic_merge",
            "explicit_failure_surface",
            "spec_alignment",
        )
    )
    metrics = ConditionMetrics(
        baseline_score=round(baseline_numerator / 5.0, 4),
        invariant_compliance=round(invariant_numerator / 4.0, 4),
        proof_alignment=1.0 if checks["spec_alignment"] else 0.0,
        specification_coverage=round(coverage_numerator / 5.0, 4),
    )
    notes = [
        "Heuristic first-slice analysis only; authoritative grading still belongs in amplihack-agent-eval."
    ]
    for check_name, passed in checks.items():
        if not passed:
            notes.append(f"Missing heuristic signal: {check_name}")
    return HeuristicEvaluation(metrics=metrics, checks=checks, notes=notes)


def _load_replay_generation(
    replay_dir: Path,
    condition: ExperimentCondition,
) -> PromptGenerationResult:
    condition_dir = replay_dir / condition.condition_id
    for filename in REPLAY_ARTIFACT_FILENAMES:
        artifact_file = condition_dir / filename
        if artifact_file.exists():
            return PromptGenerationResult(
                response_text=artifact_file.read_text(),
                provider="replay",
                metadata={"source_path": str(artifact_file)},
            )
    raise FileNotFoundError(
        f"No replay artifact found for {condition.condition_id} under {condition_dir}"
    )


def _generate_live_artifact(
    condition: ExperimentCondition,
    prompt_text: str,
    *,
    storage_path: Path,
) -> PromptGenerationResult:
    from amplihack.agents.goal_seeking.runtime_factory import create_goal_agent_runtime

    runtime = create_goal_agent_runtime(
        agent_name=f"tla-prompt-{condition.condition_id}",
        sdk=condition.model_sdk,
        model=condition.model_id,
        storage_path=storage_path,
        enable_memory=False,
        enable_eval=True,
        instructions=LIVE_GENERATION_SYSTEM_PROMPT,
    )
    try:
        response_text = runtime.answer_question(prompt_text)
    finally:
        runtime.close()
    return PromptGenerationResult(
        response_text=str(response_text),
        provider="live",
        metadata={"sdk": condition.model_sdk, "model_id": condition.model_id},
    )


def generate_condition_artifact(
    condition: ExperimentCondition,
    prompt_text: str,
    *,
    work_dir: Path,
    replay_dir: Path | None = None,
) -> PromptGenerationResult:
    """Generate an artifact either from replay files or a live SDK-backed runtime."""

    if replay_dir is not None:
        return _load_replay_generation(replay_dir, condition)
    return _generate_live_artifact(
        condition,
        prompt_text,
        storage_path=work_dir / "agent_state",
    )


def generate_experiment_markdown_report(
    execution_report: ExperimentExecutionReport,
    results: list[ConditionRunResult],
    output_path: str | Path,
) -> Path:
    """Write a markdown report for a local TLA prompt-language experiment run."""

    output_file = Path(output_path)
    lines = [
        "# TLA+ Prompt Language Experiment Report",
        "",
        f"**Experiment ID**: `{execution_report.experiment_id}`",
        f"**Generated at**: `{execution_report.generated_at}`",
        f"**Matrix mode**: `{execution_report.matrix_mode}`",
        f"**Replay mode**: `{execution_report.replay_mode}`",
        f"**Output dir**: `{execution_report.output_dir}`",
        "",
        "## Summary",
        "",
        f"- Total conditions: {execution_report.total_conditions}",
        f"- Completed conditions: {execution_report.completed_conditions}",
        f"- Failed conditions: {execution_report.failed_conditions}",
        "",
        "## Condition Table",
        "",
        "| Condition | Model | SDK | Prompt | Status | Baseline | Invariant | Proof | Coverage |",
        "|-----------|-------|-----|--------|--------|----------|-----------|-------|----------|",
    ]
    for result in results:
        metrics = result.metrics
        lines.append(
            "| "
            f"{result.condition.condition_id} | "
            f"{result.condition.model_id} | "
            f"{result.condition.model_sdk} | "
            f"{result.condition.prompt_variant_id} | "
            f"{result.status} | "
            f"{metrics.baseline_score if metrics.baseline_score is not None else '--'} | "
            f"{metrics.invariant_compliance if metrics.invariant_compliance is not None else '--'} | "
            f"{metrics.proof_alignment if metrics.proof_alignment is not None else '--'} | "
            f"{metrics.specification_coverage if metrics.specification_coverage is not None else '--'} |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "| Condition | Generated Artifact | Evaluation | Raw Response |",
            "|-----------|--------------------|------------|--------------|",
        ]
    )
    for result in results:
        lines.append(
            "| "
            f"{result.condition.condition_id} | "
            f"{result.generated_artifact_path or '--'} | "
            f"{result.evaluation_artifact_path or '--'} | "
            f"{result.raw_response_path or '--'} |"
        )
    if execution_report.tlc_validation is not None:
        tlc = execution_report.tlc_validation
        lines.extend(
            [
                "",
                "## TLC Validation",
                "",
                f"- Runner: `{tlc['runner_kind']}`",
                f"- Return code: `{tlc['returncode']}`",
                f"- Command: `{ ' '.join(tlc['command']) }`",
            ]
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
            "- Heuristic metrics in this report are first-slice local analysis only.",
            "- Authoritative grading and packaged reports still belong in `amplihack-agent-eval`.",
            "",
        ]
    )
    output_file.write_text("\n".join(lines))
    return output_file


def run_tla_prompt_experiment(
    output_dir: str | Path,
    *,
    smoke: bool = False,
    manifest: ExperimentManifest | None = None,
    replay_dir: str | Path | None = None,
    validate_spec: bool = False,
    tlc_bin: str | None = None,
    tla2tools_jar: str | None = None,
) -> ExperimentExecutionReport:
    """Run the local first-slice experiment and emit per-condition artifacts."""

    resolved_manifest = manifest or load_default_experiment_manifest()
    packets = materialize_condition_packets(output_dir, smoke=smoke, manifest=resolved_manifest)
    replay_root = Path(replay_dir) if replay_dir is not None else None
    shared_tlc_result: SpecValidationResult | None = None
    if validate_spec:
        shared_tlc_result = validate_spec_assets(
            resolved_manifest,
            tlc_bin=tlc_bin,
            tla2tools_jar=tla2tools_jar,
        )
        tlc_file = Path(output_dir) / "tlc_validation.json"
        tlc_file.write_text(json.dumps(shared_tlc_result.to_dict(), indent=2) + "\n")

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
            )
            generated_file.write_text(generated.response_text)
            raw_response_file.write_text(generated.response_text)
            evaluation = evaluate_generated_artifact(generated.response_text)
            evaluation_file.write_text(json.dumps(evaluation.to_dict(), indent=2) + "\n")
            result = ConditionRunResult(
                condition=packet.condition,
                status="completed",
                metrics=evaluation.metrics,
                generated_artifact_path=str(generated_file),
                evaluation_artifact_path=str(evaluation_file),
                raw_response_path=str(raw_response_file),
                notes=[f"generation_provider={generated.provider}", *evaluation.notes],
                tlc_validation=shared_tlc_result.to_dict() if shared_tlc_result else None,
            )
        except Exception as exc:
            result = ConditionRunResult(
                condition=packet.condition,
                status="failed",
                notes=[str(exc)],
                tlc_validation=shared_tlc_result.to_dict() if shared_tlc_result else None,
            )
        write_condition_result(run_result_file, result)
        results.append(result)

    summary = summarize_condition_results(results)
    report = ExperimentExecutionReport(
        experiment_id=resolved_manifest.experiment_id,
        matrix_mode="smoke" if smoke else "full",
        output_dir=str(output_dir),
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_conditions=len(results),
        completed_conditions=sum(1 for item in results if item.status == "completed"),
        failed_conditions=sum(1 for item in results if item.status == "failed"),
        summary=summary,
        replay_mode=replay_root is not None,
        tlc_validation=shared_tlc_result.to_dict() if shared_tlc_result else None,
    )
    output_root = Path(output_dir)
    (output_root / "experiment_report.json").write_text(json.dumps(report.to_dict(), indent=2) + "\n")
    generate_experiment_markdown_report(report, results, output_root / "experiment_report.md")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Load the issue #3497 TLA+ prompt-language experiment manifest.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=default_manifest_path(),
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
        help="Execute the local first-slice runner and write per-condition artifacts to this directory.",
    )
    parser.add_argument(
        "--replay-dir",
        type=Path,
        help="Read pre-generated condition artifacts from this directory instead of invoking live model generation.",
    )
    parser.add_argument(
        "--validate-spec",
        action="store_true",
        help="Run TLC against the bundled scoped TLA+ spec.",
    )
    parser.add_argument(
        "--tlc-bin",
        help="Path to a native tlc executable.",
    )
    parser.add_argument(
        "--tla2tools-jar",
        type=Path,
        help="Path to tla2tools.jar for Java-based TLC validation.",
    )
    parser.add_argument(
        "--summarize-results",
        type=Path,
        help="Read run_result.json files under this directory and print an aggregate summary.",
    )
    args = parser.parse_args(argv)

    manifest = load_experiment_manifest(args.manifest)
    if args.run_dir:
        report = run_tla_prompt_experiment(
            args.run_dir,
            smoke=args.smoke,
            manifest=manifest,
            replay_dir=args.replay_dir,
            validate_spec=args.validate_spec,
            tlc_bin=args.tlc_bin,
            tla2tools_jar=str(args.tla2tools_jar) if args.tla2tools_jar else None,
        )
        print(json.dumps(report.to_dict(), indent=2))
        return 0
    if args.validate_spec:
        result = validate_spec_assets(
            manifest,
            tlc_bin=args.tlc_bin,
            tla2tools_jar=str(args.tla2tools_jar) if args.tla2tools_jar else None,
        )
        print(json.dumps(result.to_dict(), indent=2))
        return 0
    if args.summarize_results:
        result_files = sorted(args.summarize_results.glob("*/run_result.json"))
        if not result_files:
            raise SystemExit("No run_result.json files found under the given directory")
        summary = summarize_condition_results([load_condition_result(path) for path in result_files])
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
