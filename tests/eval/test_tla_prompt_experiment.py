import json
import os

import pytest

from amplihack.eval.tla_prompt_experiment import (
    ConditionMetrics,
    ConditionRunResult,
    ExperimentManifest,
    build_tlc_command,
    default_manifest_path,
    evaluate_generated_artifact,
    generate_condition_artifact,
    load_condition_result,
    load_default_experiment_manifest,
    main,
    materialize_condition_packets,
    run_tla_prompt_experiment,
    summarize_condition_results,
    validate_spec_assets,
    write_condition_matrix,
    write_condition_result,
)


def test_default_manifest_path_points_to_experiment_home():
    manifest_path = default_manifest_path()
    assert manifest_path.name == "manifest.json"
    assert "experiments/hive_mind/tla_prompt_language" in str(manifest_path)


def test_default_manifest_loads_scoped_generation_target():
    manifest = load_default_experiment_manifest()
    assert manifest.experiment_id == "tla-prompt-language-v1"
    assert manifest.experiment_home == "experiments/hive_mind/tla_prompt_language"
    assert manifest.generation_target.target_id == "distributed_retrieval_contract"


def test_default_manifest_resolves_prompt_and_spec_assets():
    manifest = load_default_experiment_manifest()
    spec_path = manifest.resolve_asset_path(manifest.spec_asset)
    tlc_path = manifest.resolve_asset_path(manifest.tlc_config_asset or "")
    assert spec_path.name == "DistributedRetrievalContract.tla"
    assert tlc_path.name == "DistributedRetrievalContract.cfg"
    for prompt_variant in manifest.prompt_variants:
        assert manifest.resolve_asset_path(prompt_variant.path).exists()


def test_expand_smoke_matrix_returns_one_repeat_per_model_variant_pair():
    manifest = load_default_experiment_manifest()
    conditions = manifest.expand_matrix(smoke=True)
    assert len(conditions) == 6
    assert {item.repeat_index for item in conditions} == {1}
    assert {item.prompt_variant_id for item in conditions} == {
        "english",
        "tla_only",
        "tla_plus_english",
    }
    assert {item.model_id for item in conditions} == {"claude-opus-4.6", "gpt-5.4"}


def test_expand_full_matrix_uses_full_repeat_count():
    manifest = load_default_experiment_manifest()
    conditions = manifest.expand_matrix(smoke=False)
    assert len(conditions) == 18
    assert {item.repeat_index for item in conditions} == {1, 2, 3}


def test_prompt_bundle_only_appends_spec_when_variant_requires_it():
    manifest = load_default_experiment_manifest()
    english_bundle = manifest.load_prompt_bundle("english")
    tla_bundle = manifest.load_prompt_bundle("tla_only")

    assert "Formal specification" not in english_bundle.combined_text()
    assert "Formal specification" in tla_bundle.combined_text()
    assert "---- MODULE DistributedRetrievalContract ----" in tla_bundle.combined_text()


def test_write_condition_matrix_emits_json(tmp_path):
    output_file = tmp_path / "matrix.json"
    write_condition_matrix(output_file, smoke=True)
    payload = json.loads(output_file.read_text())
    assert payload["experiment_id"] == "tla-prompt-language-v1"
    assert payload["matrix_mode"] == "smoke"
    assert len(payload["conditions"]) == 6


def test_materialize_condition_packets_writes_prompt_spec_and_metadata(tmp_path):
    manifest = load_default_experiment_manifest()
    packets = materialize_condition_packets(tmp_path, smoke=True, manifest=manifest)
    assert len(packets) == 6

    first_packet = packets[0]
    packet_dir = tmp_path / first_packet.condition.condition_id
    prompt_text = (packet_dir / "prompt.md").read_text()
    spec_text = (packet_dir / "DistributedRetrievalContract.tla").read_text()
    metadata = json.loads((packet_dir / "condition.json").read_text())

    assert "Distributed Retrieval Contract" in prompt_text
    assert "---- MODULE DistributedRetrievalContract ----" in spec_text
    assert metadata["condition_id"] == first_packet.condition.condition_id
    assert (tmp_path / "matrix.json").exists()


def test_manifest_from_dict_rejects_missing_assets(tmp_path):
    bad_manifest = {
        "experiment_id": "bad",
        "title": "Broken manifest",
        "experiment_home": "experiments/hive_mind/tla_prompt_language",
        "generation_target": {
            "target_id": "distributed_retrieval_contract",
            "summary": "Broken",
            "deliverables": ["One"],
            "non_goals": ["Two"],
        },
        "spec_asset": "missing.tla",
        "prompt_variants": [
            {
                "variant_id": "english",
                "label": "English",
                "path": "missing.md",
                "append_spec": False,
            }
        ],
        "models": [{"model_id": "claude-opus-4.6", "label": "Claude Opus 4.6", "sdk": "claude"}],
    }

    with pytest.raises(ValueError, match="does not exist"):
        ExperimentManifest.from_dict(bad_manifest, base_dir=tmp_path)


def test_condition_run_result_round_trip(tmp_path):
    manifest = load_default_experiment_manifest()
    condition = manifest.expand_matrix(smoke=True)[0]
    result = ConditionRunResult(
        condition=condition,
        status="completed",
        metrics=ConditionMetrics(
            baseline_score=0.82,
            invariant_compliance=0.9,
            proof_alignment=0.75,
            specification_coverage=0.8,
        ),
        generated_artifact_path="/tmp/generated.py",
        evaluation_artifact_path="/tmp/eval.json",
        notes=["smoke slice"],
    )

    output_file = tmp_path / "run_result.json"
    write_condition_result(output_file, result)
    loaded = load_condition_result(output_file)

    assert loaded.status == "completed"
    assert loaded.metrics.invariant_compliance == 0.9
    assert loaded.generated_artifact_path == "/tmp/generated.py"
    assert loaded.condition.condition_id == condition.condition_id


def test_summarize_condition_results_groups_by_model_and_prompt_variant():
    manifest = load_default_experiment_manifest()
    conditions = manifest.expand_matrix(smoke=True)
    results = [
        ConditionRunResult(
            condition=conditions[0],
            status="completed",
            metrics=ConditionMetrics(
                baseline_score=0.8,
                invariant_compliance=0.9,
                proof_alignment=0.7,
                specification_coverage=0.75,
            ),
        ),
        ConditionRunResult(
            condition=conditions[1],
            status="completed",
            metrics=ConditionMetrics(
                baseline_score=0.85,
                invariant_compliance=0.95,
                proof_alignment=0.8,
                specification_coverage=0.78,
            ),
        ),
        ConditionRunResult(
            condition=conditions[2],
            status="failed",
            metrics=ConditionMetrics(),
            notes=["model error"],
        ),
    ]

    report = summarize_condition_results(results)
    payload = report.to_dict()

    assert payload["completed_conditions"] == 2
    assert payload["failed_conditions"] == 1
    assert payload["metric_summary"]["baseline_score"]["count"] == 2
    assert "english" in payload["by_prompt_variant"]
    assert "claude-opus-4.6" in payload["by_model"]


def test_build_tlc_command_prefers_native_tlc_binary():
    command, runner_kind = build_tlc_command(
        "DistributedRetrievalContract.tla",
        "DistributedRetrievalContract.cfg",
        tlc_bin="/tmp/tlc",
    )
    assert runner_kind == "tlc"
    assert command == ["/tmp/tlc", "-config", "DistributedRetrievalContract.cfg", "DistributedRetrievalContract"]


def test_build_tlc_command_falls_back_to_java_and_jar(monkeypatch):
    def fake_which(name: str) -> str | None:
        if name == "tlc":
            return None
        return "/usr/bin/java" if name == "java" else None

    monkeypatch.delenv("TLA_TLC_BIN", raising=False)
    monkeypatch.setattr("amplihack.eval.tla_prompt_experiment.shutil.which", fake_which)
    command, runner_kind = build_tlc_command(
        "DistributedRetrievalContract.tla",
        "DistributedRetrievalContract.cfg",
        java_bin="/usr/bin/java",
        tla2tools_jar="/tmp/tla2tools.jar",
    )
    assert runner_kind == "java"
    assert command == [
        "/usr/bin/java",
        "-cp",
        "/tmp/tla2tools.jar",
        "tlc2.TLC",
        "-config",
        "DistributedRetrievalContract.cfg",
        "DistributedRetrievalContract",
    ]


def test_build_tlc_command_requires_configured_runner(monkeypatch):
    monkeypatch.delenv("TLA_TLC_BIN", raising=False)
    monkeypatch.delenv("TLA2TOOLS_JAR", raising=False)
    monkeypatch.setattr("amplihack.eval.tla_prompt_experiment.shutil.which", lambda _: None)

    with pytest.raises(RuntimeError, match="No TLC runner available"):
        build_tlc_command("DistributedRetrievalContract.tla", "DistributedRetrievalContract.cfg")


def test_validate_spec_assets_runs_configured_tlc_binary(tmp_path):
    runner = tmp_path / "tlc"
    runner.write_text("#!/usr/bin/env bash\necho 'TLC OK'\n")
    runner.chmod(0o755)

    manifest = load_default_experiment_manifest()
    result = validate_spec_assets(manifest, tlc_bin=str(runner))

    assert result.runner_kind == "tlc"
    assert result.returncode == 0
    assert "TLC OK" in result.stdout


def test_validate_spec_assets_runs_real_tlc_when_available():
    tlc_bin = os.environ.get("TLA_TLC_BIN")
    tla2tools_jar = os.environ.get("TLA2TOOLS_JAR")
    if not tlc_bin and not tla2tools_jar:
        pytest.skip("requires a real TLC runtime")

    manifest = load_default_experiment_manifest()
    result = validate_spec_assets(manifest, tlc_bin=tlc_bin, tla2tools_jar=tla2tools_jar)

    assert result.returncode == 0


def test_evaluate_generated_artifact_scores_contract_signals():
    evaluation = evaluate_generated_artifact(
        """
        Preserve the original question by storing original_question.
        Fan out retrieval to all active agents and sort(results) for deterministic merge.
        Raise an error for shard failure and add pytest test_retrieval_contract assertions.
        The implementation follows the TLA invariant in DistributedRetrievalContract.
        """
    )

    assert evaluation.metrics.baseline_score == 1.0
    assert evaluation.metrics.invariant_compliance == 1.0
    assert evaluation.metrics.proof_alignment == 1.0
    assert evaluation.checks["focused_tests"] is True


def test_evaluate_generated_artifact_penalizes_off_topic_output():
    evaluation = evaluate_generated_artifact(
        """
        class AuthService:
            def login(self, username, password):
                raise ValueError("invalid credentials")

        def test_login_rejects_invalid_password():
            assert True
        """
    )

    assert evaluation.metrics.baseline_score == 0.0
    assert evaluation.metrics.invariant_compliance == 0.0
    assert evaluation.checks["focused_tests"] is False
    assert evaluation.checks["explicit_failure_surface"] is False


def test_generate_condition_artifact_requires_allow_live_without_replay(tmp_path):
    manifest = load_default_experiment_manifest()
    condition = manifest.expand_matrix(smoke=True)[0]
    bundle = manifest.load_prompt_bundle(condition.prompt_variant_id)

    with pytest.raises(ValueError, match="allow_live=True"):
        generate_condition_artifact(condition, bundle.combined_text(), work_dir=tmp_path)


def test_run_tla_prompt_experiment_requires_live_opt_in(tmp_path):
    manifest = load_default_experiment_manifest()

    with pytest.raises(ValueError, match="allow_live=True / --allow-live"):
        run_tla_prompt_experiment(tmp_path / "run", smoke=True, manifest=manifest)


def test_generate_condition_artifact_replay_mode_explains_packet_only_dirs(tmp_path):
    manifest = load_default_experiment_manifest()
    packets_dir = tmp_path / "packets"
    packet = materialize_condition_packets(packets_dir, smoke=True, manifest=manifest)[0]
    bundle = manifest.load_prompt_bundle(packet.condition.prompt_variant_id)

    with pytest.raises(
        FileNotFoundError,
        match="--materialize-dir contains prompt/spec packets only",
    ):
        generate_condition_artifact(
            packet.condition,
            bundle.combined_text(),
            work_dir=tmp_path / "work",
            replay_dir=packets_dir,
        )


def test_generate_condition_artifact_live_mode_uses_runtime_factory(tmp_path, monkeypatch):
    manifest = load_default_experiment_manifest()
    condition = manifest.expand_matrix(smoke=True)[0]
    bundle = manifest.load_prompt_bundle(condition.prompt_variant_id)
    captured: dict[str, object] = {}

    class DummyRuntime:
        def answer_question(self, prompt: str) -> str:
            captured["prompt"] = prompt
            return "generated retrieval contract artifact"

        def close(self) -> None:
            captured["closed"] = True

    def fake_create_goal_agent_runtime(**kwargs: object) -> DummyRuntime:
        captured["kwargs"] = kwargs
        return DummyRuntime()

    monkeypatch.setattr(
        "amplihack.agents.goal_seeking.runtime_factory.create_goal_agent_runtime",
        fake_create_goal_agent_runtime,
    )

    result = generate_condition_artifact(
        condition,
        bundle.combined_text(),
        work_dir=tmp_path,
        allow_live=True,
    )

    assert result.provider == "live"
    assert result.response_text == "generated retrieval contract artifact"
    assert captured["closed"] is True
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["sdk"] == condition.model_sdk
    assert kwargs["model"] == condition.model_id
    assert kwargs["enable_memory"] is False


def test_main_returns_nonzero_when_run_report_has_failed_conditions(tmp_path, capsys):
    manifest = load_default_experiment_manifest()
    packets_dir = tmp_path / "packets"
    materialize_condition_packets(packets_dir, smoke=True, manifest=manifest)

    exit_code = main(
        [
            "--manifest",
            str(default_manifest_path()),
            "--smoke",
            "--run-dir",
            str(tmp_path / "run"),
            "--replay-dir",
            str(packets_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert '"failed_conditions": 6' in captured.out
    assert "failed condition(s)" in captured.err


def test_run_tla_prompt_experiment_replay_mode_writes_reports(tmp_path):
    manifest = load_default_experiment_manifest()
    replay_dir = tmp_path / "replay"
    packets = materialize_condition_packets(replay_dir, smoke=True, manifest=manifest)

    for packet in packets:
        condition_dir = replay_dir / packet.condition.condition_id
        (condition_dir / "generated_artifact.md").write_text(
            """
            Preserve the original question.
            Fan out across all active agents.
            Use sorted(results) for deterministic merge.
            Raise shard failure errors explicitly.
            Add pytest test_retrieval_contract coverage.
            Reference the TLA invariant from DistributedRetrievalContract.
            """
        )

    output_dir = tmp_path / "run"
    report = run_tla_prompt_experiment(
        output_dir,
        smoke=True,
        manifest=manifest,
        replay_dir=replay_dir,
    )

    assert report.replay_mode is True
    assert report.total_conditions == 6
    assert report.completed_conditions == 6
    assert report.to_dict()["evaluation_kind"] == "heuristic_signal_v1"
    assert (output_dir / "experiment_report.json").exists()
    assert (output_dir / "experiment_report.md").exists()
    for packet in packets:
        assert (output_dir / packet.condition.condition_id / "run_result.json").exists()
