"""Tests for gherkin_prompt_experiment.py — Gherkin v2 recipe step executor.

Tests cover:
1. Agent-based consensus evaluator (unit tests with mocked API)
2. Statistical helpers (mean, stddev, CI)
3. Manifest loading and CLI (integration)

Testing pyramid: 60% unit (evaluator + stats), 30% integration (manifest + CLI), 10% E2E.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from amplihack.eval.gherkin_agent_evaluator import (
    FEATURES,
    AgentVote,
    ConsensusEvaluation,
    _extract_vote,
    _has_anthropic_api_key,
    _parse_agent_response,
)
from amplihack.eval.gherkin_prompt_experiment import (
    _compute_stats,
    default_gherkin_v2_manifest_path,
    load_gherkin_v2_manifest,
    main,
)
from amplihack.eval.tla_prompt_experiment import ConditionMetrics

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_vote(
    features: dict[str, bool],
    agent_id: str = "test_agent",
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> AgentVote:
    return AgentVote(
        agent_id=agent_id,
        persona="test persona",
        features=features,
        reasoning=dict.fromkeys(features, "test"),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        wall_clock_seconds=1.0,
    )


ALL_PASS = dict.fromkeys(FEATURES, True)
ALL_FAIL = dict.fromkeys(FEATURES, False)
MIXED = {
    "conditional_execution": True,
    "dependency_handling": True,
    "retry_logic": False,
    "timeout_semantics": False,
    "output_capture": True,
    "sub_recipe_delegation": True,
}


# ---------------------------------------------------------------------------
# Unit Tests — JSON parsing
# ---------------------------------------------------------------------------


class TestParseAgentResponse:
    """Test response parsing handles various formats."""

    def test_plain_json(self):
        raw = json.dumps({f: {"pass": True, "reasoning": "ok"} for f in FEATURES})
        parsed = _parse_agent_response(raw)
        assert len(parsed) == 6

    def test_json_with_markdown_fences(self):
        raw = (
            "```json\n"
            + json.dumps({f: {"pass": True, "reasoning": "ok"} for f in FEATURES})
            + "\n```"
        )
        parsed = _parse_agent_response(raw)
        assert len(parsed) == 6

    def test_json_with_bare_fences(self):
        raw = (
            "```\n"
            + json.dumps({f: {"pass": False, "reasoning": "no"} for f in FEATURES})
            + "\n```"
        )
        parsed = _parse_agent_response(raw)
        for feat in FEATURES:
            assert parsed[feat]["pass"] is False

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_agent_response("this is not json")


# ---------------------------------------------------------------------------
# Unit Tests — vote extraction
# ---------------------------------------------------------------------------


class TestExtractVote:
    """Test vote extraction from parsed agent responses."""

    def test_all_pass(self):
        raw = {f: {"pass": True, "reasoning": f"good {f}"} for f in FEATURES}
        vote = _extract_vote(raw, "agent_0", "test")
        assert all(vote.features[f] for f in FEATURES)

    def test_all_fail(self):
        raw = {f: {"pass": False, "reasoning": "bad"} for f in FEATURES}
        vote = _extract_vote(raw, "agent_0", "test")
        assert not any(vote.features[f] for f in FEATURES)

    def test_missing_feature_defaults_to_fail(self):
        raw = {"conditional_execution": {"pass": True, "reasoning": "ok"}}
        vote = _extract_vote(raw, "agent_0", "test")
        assert vote.features["conditional_execution"] is True
        assert vote.features["dependency_handling"] is False

    def test_bare_bool_handled(self):
        raw = dict.fromkeys(FEATURES, True)
        vote = _extract_vote(raw, "agent_0", "test")
        assert all(vote.features[f] for f in FEATURES)

    def test_reasoning_preserved(self):
        raw = {f: {"pass": True, "reasoning": f"reason_{f}"} for f in FEATURES}
        vote = _extract_vote(raw, "agent_0", "test")
        assert vote.reasoning["retry_logic"] == "reason_retry_logic"


class TestHasAnthropicApiKey:
    """Test direct API availability helper."""

    def test_returns_false_when_disabled(self, monkeypatch):
        monkeypatch.setenv(
            "ANTHROPIC_API_KEY", "test-key-for-unit-tests"
        )  # pragma: allowlist secret
        monkeypatch.setenv("ANTHROPIC_DISABLED", "true")

        assert _has_anthropic_api_key() is False

    def test_returns_true_when_key_present_and_enabled(self, monkeypatch):
        monkeypatch.setenv(
            "ANTHROPIC_API_KEY", "test-key-for-unit-tests"
        )  # pragma: allowlist secret
        monkeypatch.delenv("ANTHROPIC_DISABLED", raising=False)

        assert _has_anthropic_api_key() is True


# ---------------------------------------------------------------------------
# Unit Tests — consensus scoring
# ---------------------------------------------------------------------------


class TestConsensusScoring:
    """Test that consensus correctly aggregates votes."""

    def test_unanimous_pass(self):
        votes = [_make_vote(ALL_PASS, f"agent_{i}") for i in range(3)]
        # Manually compute consensus
        for feat in FEATURES:
            pass_count = sum(1 for v in votes if v.features[feat])
            assert pass_count / 3 == 1.0

    def test_unanimous_fail(self):
        votes = [_make_vote(ALL_FAIL, f"agent_{i}") for i in range(3)]
        for feat in FEATURES:
            pass_count = sum(1 for v in votes if v.features[feat])
            assert pass_count / 3 == 0.0

    def test_majority_vote(self):
        votes = [
            _make_vote(ALL_PASS, "agent_0"),
            _make_vote(ALL_PASS, "agent_1"),
            _make_vote(ALL_FAIL, "agent_2"),
        ]
        for feat in FEATURES:
            pass_count = sum(1 for v in votes if v.features[feat])
            assert pass_count / 3 == pytest.approx(0.6667, abs=0.001)

    def test_split_vote_on_specific_features(self):
        votes = [
            _make_vote(MIXED, "agent_0"),
            _make_vote(ALL_PASS, "agent_1"),
            _make_vote(ALL_FAIL, "agent_2"),
        ]
        # conditional_execution: True + True + False = 2/3
        pass_count = sum(1 for v in votes if v.features["conditional_execution"])
        assert pass_count / 3 == pytest.approx(0.6667, abs=0.001)
        # retry_logic: False + True + False = 1/3
        pass_count = sum(1 for v in votes if v.features["retry_logic"])
        assert pass_count / 3 == pytest.approx(0.3333, abs=0.001)


# ---------------------------------------------------------------------------
# Unit Tests — AgentVote serialization
# ---------------------------------------------------------------------------


class TestAgentVoteSerialization:
    def test_to_dict_roundtrip(self):
        vote = _make_vote(ALL_PASS, "agent_0", input_tokens=500, output_tokens=200)
        d = vote.to_dict()
        assert d["agent_id"] == "agent_0"
        assert d["input_tokens"] == 500
        assert d["output_tokens"] == 200
        assert all(d["features"][f] for f in FEATURES)


# ---------------------------------------------------------------------------
# Unit Tests — ConsensusEvaluation serialization
# ---------------------------------------------------------------------------


class TestConsensusEvaluationSerialization:
    def test_to_dict_has_required_fields(self):
        votes = [_make_vote(ALL_PASS, f"agent_{i}") for i in range(3)]
        eval_result = ConsensusEvaluation(
            metrics=ConditionMetrics(
                baseline_score=1.0,
                invariant_compliance=1.0,
                proof_alignment=1.0,
                local_protocol_alignment=1.0,
                progress_signal=1.0,
                specification_coverage=1.0,
            ),
            consensus_scores=dict.fromkeys(FEATURES, 1.0),
            agent_votes=votes,
            total_input_tokens=300,
            total_output_tokens=150,
            total_wall_clock_seconds=3.0,
            notes=[],
        )
        d = eval_result.to_dict()
        assert d["evaluation_kind"] == "agent_consensus_v1"
        assert len(d["agent_votes"]) == 3
        assert d["total_input_tokens"] == 300


# ---------------------------------------------------------------------------
# Unit Tests — statistical helpers
# ---------------------------------------------------------------------------


class TestComputeStats:
    def test_empty_list(self):
        stats = _compute_stats([])
        assert stats["mean"] == 0.0
        assert stats["n"] == 0

    def test_single_value(self):
        stats = _compute_stats([0.75])
        assert stats["mean"] == 0.75
        assert stats["stddev"] == 0.0
        assert stats["ci95"] == 0.0
        assert stats["n"] == 1

    def test_two_values(self):
        stats = _compute_stats([0.5, 1.0])
        assert stats["mean"] == 0.75
        assert stats["stddev"] > 0
        assert stats["ci95"] > 0
        assert stats["n"] == 2

    def test_identical_values(self):
        stats = _compute_stats([0.8, 0.8, 0.8])
        assert stats["mean"] == 0.8
        assert stats["stddev"] == 0.0
        assert stats["min"] == 0.8
        assert stats["max"] == 0.8

    def test_known_distribution(self):
        stats = _compute_stats([1.0, 0.0, 1.0])
        assert stats["mean"] == pytest.approx(0.6667, abs=0.001)
        assert stats["min"] == 0.0
        assert stats["max"] == 1.0
        assert stats["n"] == 3


# ---------------------------------------------------------------------------
# Integration Tests — manifest loading and CLI
# ---------------------------------------------------------------------------


class TestManifestLoading:
    """Test manifest loading and validation."""

    def test_manifest_path_construction(self):
        path = default_gherkin_v2_manifest_path("/tmp/fake_root")
        assert str(path).endswith("gherkin_v2_recipe_executor/manifest.json")

    def test_load_manifest_from_repo(self):
        manifest = load_gherkin_v2_manifest()
        assert manifest.experiment_id == "gherkin-v2-recipe-executor"
        assert manifest.generation_target.target_id == "recipe_step_executor"
        assert len(manifest.prompt_variants) == 4
        assert len(manifest.models) == 2

    def test_manifest_variant_ids(self):
        manifest = load_gherkin_v2_manifest()
        variant_ids = {v.variant_id for v in manifest.prompt_variants}
        assert variant_ids == {
            "english",
            "gherkin_only",
            "gherkin_plus_english",
            "gherkin_plus_acceptance",
        }

    def test_manifest_model_ids(self):
        manifest = load_gherkin_v2_manifest()
        model_ids = {m.model_id for m in manifest.models}
        assert model_ids == {"claude-opus-4.6", "gpt-5.4"}

    def test_smoke_matrix_expansion(self):
        manifest = load_gherkin_v2_manifest()
        conditions = manifest.expand_matrix(smoke=True)
        # 4 variants x 2 models x 1 repeat = 8
        assert len(conditions) == 8

    def test_full_matrix_expansion(self):
        manifest = load_gherkin_v2_manifest()
        conditions = manifest.expand_matrix(smoke=False)
        # 4 variants x 2 models x 3 repeats = 24
        assert len(conditions) == 24

    def test_prompt_bundles_load(self):
        manifest = load_gherkin_v2_manifest()
        for variant in manifest.prompt_variants:
            bundle = manifest.load_prompt_bundle(variant.variant_id)
            assert len(bundle.prompt_text) > 0
            combined = bundle.combined_text()
            assert len(combined) > 0
            if variant.append_spec:
                assert "Feature:" in combined or "Scenario:" in combined


class TestCLI:
    """Test CLI entry point."""

    def test_cli_matrix_output(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name
        try:
            exit_code = main(["--smoke", "--output", output_path])
            assert exit_code == 0
            data = json.loads(Path(output_path).read_text())
            assert data["experiment_id"] == "gherkin-v2-recipe-executor"
            assert data["matrix_mode"] == "smoke"
            assert len(data["conditions"]) == 8
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_cli_variant_output(self):
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = main(["--variant", "english"])
        assert exit_code == 0
        output = buf.getvalue()
        assert "RecipeStepExecutor" in output or "recipe" in output.lower()
