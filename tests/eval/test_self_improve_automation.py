"""Tests for self-improvement automation: patch proposer, reviewer voting,
regression detection, auto-revert, and challenge/response flow.

Tests:
- PatchProposal generation (with mock LLM)
- Reviewer voting with mock votes
- Regression detection logic
- Auto-revert mechanism
- Challenge/response flow
- Integration test of one full iteration (with mocked LLM)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.eval.long_horizon_self_improve import (
    LongHorizonRunnerConfig,
    _analyze_categories,
    _diagnose_bottleneck,
    detect_regression,
)
from amplihack.eval.self_improve.patch_proposer import (
    PatchHistory,
    PatchProposal,
    _build_proposal_prompt,
    _parse_llm_response,
    propose_patch,
    propose_patch_from_analysis,
)
from amplihack.eval.self_improve.reviewer_voting import (
    ChallengeResponse,
    ReviewResult,
    ReviewVote,
    _build_consensus_rationale,
    _tally_votes,
    challenge_proposal,
    review_result_to_dict,
    vote_on_proposal,
)


# ============================================================
# PatchProposal Tests
# ============================================================


class TestPatchProposal:
    """Tests for PatchProposal dataclass and propose_patch function."""

    def test_patch_proposal_creation(self):
        proposal = PatchProposal(
            target_file="src/agent.py",
            hypothesis="Retrieval misses entities",
            description="Add entity indexing",
            diff="--- a/src/agent.py\n+++ b/src/agent.py\n@@ -1 +1 @@\n-old\n+new",
            expected_impact={"needle_in_haystack": 10.0},
            risk_assessment="Could slow retrieval",
            confidence=0.7,
        )
        assert proposal.target_file == "src/agent.py"
        assert proposal.confidence == 0.7
        assert "needle_in_haystack" in proposal.expected_impact

    def test_patch_proposal_defaults(self):
        proposal = PatchProposal(
            target_file="test.py",
            hypothesis="test",
            description="test",
            diff="",
        )
        assert proposal.expected_impact == {}
        assert proposal.risk_assessment == ""
        assert proposal.confidence == 0.0

    def test_propose_patch_without_llm(self):
        """Without LLM, should return a stub proposal."""
        proposal = propose_patch(
            category="needle_in_haystack",
            category_score=0.3,
            failed_questions=[{"question_text": "Q1", "score": 0.2}],
            bottleneck="retrieval:keyword_search",
            suggested_fix="Add entity indexing",
        )
        assert proposal.target_file != ""
        assert proposal.confidence == 0.1  # stub confidence
        assert "needle_in_haystack" in proposal.hypothesis
        assert proposal.diff == ""  # no LLM, no diff

    def test_propose_patch_with_mock_llm(self):
        """With mock LLM returning valid JSON, should parse the proposal."""
        mock_response = json.dumps(
            {
                "hypothesis": "The retrieval system misses entity-based queries",
                "description": "Add entity name indexing to retrieval",
                "diff": "--- a/src/agent.py\n+++ b/src/agent.py\n@@ -10 +10 @@\n-pass\n+index()",
                "expected_impact": {"needle_in_haystack": 15.0},
                "risk_assessment": "Could affect query latency",
                "confidence": 0.8,
            }
        )

        def mock_llm(prompt: str) -> str:
            return mock_response

        proposal = propose_patch(
            category="needle_in_haystack",
            category_score=0.3,
            failed_questions=[],
            bottleneck="retrieval:keyword_search",
            suggested_fix="Add indexing",
            llm_call=mock_llm,
        )
        assert proposal.hypothesis == "The retrieval system misses entity-based queries"
        assert proposal.confidence == 0.8
        assert "index()" in proposal.diff

    def test_propose_patch_with_invalid_llm_response(self):
        """With invalid LLM JSON, should return fallback proposal."""

        def mock_llm(prompt: str) -> str:
            return "This is not valid JSON at all"

        proposal = propose_patch(
            category="meta_memory",
            category_score=0.2,
            failed_questions=[],
            bottleneck="retrieval:aggregation",
            suggested_fix="Add aggregation",
            llm_call=mock_llm,
        )
        assert proposal.confidence == 0.1  # fallback
        assert "meta_memory" in proposal.hypothesis

    def test_propose_patch_with_markdown_wrapped_json(self):
        """LLM might wrap JSON in markdown code blocks."""
        raw_json = json.dumps(
            {
                "hypothesis": "Test hypothesis",
                "description": "Test desc",
                "diff": "",
                "expected_impact": {},
                "risk_assessment": "None",
                "confidence": 0.6,
            }
        )

        def mock_llm(prompt: str) -> str:
            return f"```json\n{raw_json}\n```"

        proposal = propose_patch(
            category="test",
            category_score=0.5,
            failed_questions=[],
            bottleneck="unknown",
            suggested_fix="test",
            llm_call=mock_llm,
        )
        assert proposal.hypothesis == "Test hypothesis"
        assert proposal.confidence == 0.6

    def test_propose_patch_from_analysis(self):
        """Test the convenience wrapper."""
        analysis_dict = {
            "category": "temporal_evolution",
            "avg_score": 0.4,
            "failed_questions": [
                {"question_text": "When did X happen?", "score": 0.3}
            ],
            "bottleneck": "retrieval:temporal_ordering",
            "suggested_fix": "Add temporal metadata",
        }
        proposal = propose_patch_from_analysis(analysis_dict)
        assert proposal.target_file != ""
        assert "temporal_evolution" in proposal.hypothesis

    def test_patch_history_tracking(self):
        """PatchHistory should accumulate entries."""
        history = PatchHistory()
        assert len(history.applied_patches) == 0
        assert len(history.reverted_patches) == 0
        assert len(history.rejected_patches) == 0

        history.applied_patches.append({"target": "a.py", "desc": "fix1"})
        history.reverted_patches.append({"target": "b.py", "desc": "fix2"})
        assert len(history.applied_patches) == 1
        assert len(history.reverted_patches) == 1

    def test_build_proposal_prompt_includes_history(self):
        """Prompt should include reverted and rejected patch history."""
        history = PatchHistory(
            reverted_patches=[
                {
                    "target_file": "agent.py",
                    "description": "Bad fix attempt",
                    "revert_reason": "regression",
                }
            ],
            rejected_patches=[
                {
                    "target_file": "agent.py",
                    "description": "Another bad fix",
                    "rejection_reason": "too complex",
                }
            ],
        )
        prompt = _build_proposal_prompt(
            category="test",
            category_score=0.3,
            failed_questions=[],
            bottleneck="retrieval:keyword_search",
            suggested_fix="fix it",
            relevant_code="def foo(): pass",
            history=history,
        )
        assert "Bad fix attempt" in prompt
        assert "Another bad fix" in prompt
        assert "DO NOT repeat" in prompt

    def test_parse_llm_response_plain_json(self):
        """Parse plain JSON response."""
        data = _parse_llm_response('{"key": "value"}')
        assert data == {"key": "value"}

    def test_parse_llm_response_markdown_wrapped(self):
        """Parse markdown-wrapped JSON."""
        data = _parse_llm_response('```json\n{"key": "value"}\n```')
        assert data == {"key": "value"}


# ============================================================
# Reviewer Voting Tests
# ============================================================


class TestReviewerVoting:
    """Tests for the A/B reviewer voting system."""

    def _make_proposal(self, confidence: float = 0.7) -> PatchProposal:
        return PatchProposal(
            target_file="src/agent.py",
            hypothesis="Test hypothesis",
            description="Test fix",
            diff="--- a/test\n+++ b/test\n@@ -1 +1 @@\n-old\n+new",
            expected_impact={"test_cat": 10.0},
            risk_assessment="Low risk",
            confidence=confidence,
        )

    def test_vote_without_llm_high_confidence(self):
        """High confidence proposal should get accept votes."""
        proposal = self._make_proposal(confidence=0.8)
        result = vote_on_proposal(proposal)
        assert result.decision == "accepted"
        assert len(result.votes) == 3
        for v in result.votes:
            assert v.vote == "accept"

    def test_vote_without_llm_medium_confidence(self):
        """Medium confidence proposal should get modify votes."""
        proposal = self._make_proposal(confidence=0.5)
        result = vote_on_proposal(proposal)
        assert result.decision == "modified"
        assert all(v.vote == "modify" for v in result.votes)

    def test_vote_without_llm_low_confidence(self):
        """Low confidence proposal should get reject votes."""
        proposal = self._make_proposal(confidence=0.2)
        result = vote_on_proposal(proposal)
        assert result.decision == "rejected"
        assert all(v.vote == "reject" for v in result.votes)

    def test_vote_with_mock_llm(self):
        """Mock LLM returning accept votes."""
        proposal = self._make_proposal()

        def mock_llm(prompt: str) -> str:
            return json.dumps(
                {
                    "vote": "accept",
                    "rationale": "Looks good",
                    "concerns": [],
                    "suggested_modifications": None,
                }
            )

        result = vote_on_proposal(proposal, llm_call=mock_llm)
        assert result.decision == "accepted"
        assert all(v.vote == "accept" for v in result.votes)

    def test_vote_with_mixed_llm_responses(self):
        """Mock LLM returning different votes per reviewer."""
        proposal = self._make_proposal()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            # First two accept, third rejects
            if call_count <= 2:
                return json.dumps(
                    {"vote": "accept", "rationale": "Fine", "concerns": []}
                )
            return json.dumps(
                {
                    "vote": "reject",
                    "rationale": "Too risky",
                    "concerns": ["regression risk"],
                }
            )

        result = vote_on_proposal(proposal, llm_call=mock_llm)
        assert result.decision == "accepted"  # 2/3 accept
        accept_count = sum(1 for v in result.votes if v.vote == "accept")
        assert accept_count == 2

    def test_vote_majority_reject(self):
        """Two out of three reject should lead to rejected decision."""
        proposal = self._make_proposal()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return json.dumps(
                    {"vote": "accept", "rationale": "OK", "concerns": []}
                )
            return json.dumps(
                {"vote": "reject", "rationale": "Bad", "concerns": ["issue"]}
            )

        result = vote_on_proposal(proposal, llm_call=mock_llm)
        assert result.decision == "rejected"

    def test_vote_with_challenge(self):
        """Votes should include challenge context."""
        proposal = self._make_proposal()
        challenge = ChallengeResponse(
            challenge_arguments=["Could break retrieval"],
            proposer_response="We only modify indexing, not query path",
            concerns_addressed=True,
            remaining_concerns=[],
        )

        result = vote_on_proposal(proposal, challenge=challenge)
        assert result.challenge is not None
        assert result.challenge.concerns_addressed

    def test_review_vote_creation(self):
        vote = ReviewVote(
            reviewer_id="quality",
            vote="accept",
            rationale="Clean code",
            concerns=["minor style issue"],
            suggested_modifications="Fix indentation",
        )
        assert vote.reviewer_id == "quality"
        assert vote.vote == "accept"
        assert len(vote.concerns) == 1

    def test_tally_votes_all_accept(self):
        votes = [
            ReviewVote("a", "accept", "ok"),
            ReviewVote("b", "accept", "ok"),
            ReviewVote("c", "accept", "ok"),
        ]
        assert _tally_votes(votes) == "accepted"

    def test_tally_votes_all_reject(self):
        votes = [
            ReviewVote("a", "reject", "no"),
            ReviewVote("b", "reject", "no"),
            ReviewVote("c", "reject", "no"),
        ]
        assert _tally_votes(votes) == "rejected"

    def test_tally_votes_mixed(self):
        votes = [
            ReviewVote("a", "accept", "yes"),
            ReviewVote("b", "reject", "no"),
            ReviewVote("c", "modify", "maybe"),
        ]
        assert _tally_votes(votes) == "modified"

    def test_tally_votes_empty(self):
        assert _tally_votes([]) == "rejected"

    def test_build_consensus_rationale(self):
        votes = [
            ReviewVote("quality", "accept", "Clean code"),
            ReviewVote("regression", "reject", "Too risky", ["might break L2"]),
        ]
        rationale = _build_consensus_rationale(votes, "modified")
        assert "modified" in rationale
        assert "quality" in rationale
        assert "regression" in rationale
        assert "might break L2" in rationale

    def test_review_result_to_dict(self):
        proposal = self._make_proposal()
        challenge = ChallengeResponse(
            challenge_arguments=["arg1"],
            proposer_response="defense",
            concerns_addressed=True,
        )
        result = ReviewResult(
            proposal=proposal,
            challenge=challenge,
            votes=[ReviewVote("q", "accept", "ok")],
            decision="accepted",
            consensus_rationale="All good",
        )
        d = review_result_to_dict(result)
        assert d["decision"] == "accepted"
        assert d["challenge"]["concerns_addressed"] is True
        assert len(d["votes"]) == 1
        assert d["proposal"]["target_file"] == "src/agent.py"

    def test_review_result_to_dict_no_challenge(self):
        proposal = self._make_proposal()
        result = ReviewResult(
            proposal=proposal,
            challenge=None,
            votes=[],
            decision="rejected",
            consensus_rationale="No votes",
        )
        d = review_result_to_dict(result)
        assert d["challenge"] is None


# ============================================================
# Challenge/Response Tests
# ============================================================


class TestChallengeResponse:
    """Tests for the devil's advocate challenge phase."""

    def _make_proposal(self) -> PatchProposal:
        return PatchProposal(
            target_file="src/agent.py",
            hypothesis="Retrieval fails on entities",
            description="Add entity indexing",
            diff="",
            expected_impact={"needle_in_haystack": 10.0},
            confidence=0.7,
        )

    def test_challenge_without_llm(self):
        """Without LLM, challenge should be auto-passed."""
        proposal = self._make_proposal()
        response = challenge_proposal(proposal)
        assert response.concerns_addressed is True
        assert len(response.challenge_arguments) == 1  # "No LLM available"

    def test_challenge_with_mock_llm(self):
        """Mock LLM providing both challenge and defense."""
        proposal = self._make_proposal()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Devil's advocate
                return json.dumps(
                    {
                        "arguments": [
                            "Could slow down queries",
                            "Entity indexing adds complexity",
                        ],
                        "alternative_approaches": ["Use better similarity"],
                        "worst_case_scenario": "Queries timeout",
                    }
                )
            # Proposer defense
            return json.dumps(
                {
                    "defense": "Indexing is O(1) lookup, won't slow queries",
                    "concerns_acknowledged": ["Entity indexing adds complexity"],
                    "concerns_refuted": ["Could slow down queries"],
                }
            )

        response = challenge_proposal(proposal, llm_call=mock_llm)
        assert len(response.challenge_arguments) == 2
        assert response.concerns_addressed is True  # 2/2 addressed

    def test_challenge_with_unaddressed_concerns(self):
        """When proposer doesn't address enough concerns."""
        proposal = self._make_proposal()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return json.dumps(
                    {
                        "arguments": [
                            "Arg 1",
                            "Arg 2",
                            "Arg 3",
                            "Arg 4",
                        ],
                        "alternative_approaches": [],
                        "worst_case_scenario": "Bad",
                    }
                )
            return json.dumps(
                {
                    "defense": "I only address one thing",
                    "concerns_acknowledged": [],
                    "concerns_refuted": ["Arg 1"],
                }
            )

        response = challenge_proposal(proposal, llm_call=mock_llm)
        # Only 1 out of 4 addressed = 25% < 50% threshold
        assert response.concerns_addressed is False

    def test_challenge_with_invalid_llm_json(self):
        """Invalid JSON from LLM should still produce a response."""
        proposal = self._make_proposal()
        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "Not valid JSON"
            return "Also not valid JSON"

        response = challenge_proposal(proposal, llm_call=mock_llm)
        assert isinstance(response, ChallengeResponse)
        # Should have fallback arguments
        assert len(response.challenge_arguments) > 0


# ============================================================
# Regression Detection Tests
# ============================================================


class TestRegressionDetection:
    """Tests for detect_regression function."""

    def test_no_regression(self):
        baseline = {"cat_a": 0.8, "cat_b": 0.7, "overall": 0.75}
        post = {"cat_a": 0.85, "cat_b": 0.72, "overall": 0.785}
        has_regression, worst_cat, regression_pp = detect_regression(
            baseline, post, threshold=5.0
        )
        assert has_regression is False

    def test_regression_detected(self):
        baseline = {"cat_a": 0.8, "cat_b": 0.7, "overall": 0.75}
        post = {"cat_a": 0.8, "cat_b": 0.60, "overall": 0.70}
        has_regression, worst_cat, regression_pp = detect_regression(
            baseline, post, threshold=5.0
        )
        assert has_regression is True
        assert worst_cat == "cat_b"
        assert regression_pp == pytest.approx(10.0)

    def test_regression_with_compensating_gain(self):
        """Regression with compensating gain should NOT trigger."""
        baseline = {"cat_a": 0.8, "cat_b": 0.5, "overall": 0.65}
        post = {"cat_a": 0.70, "cat_b": 0.65, "overall": 0.675}
        # cat_a regresses 10pp, but cat_b gains 15pp (> 5pp threshold)
        has_regression, worst_cat, regression_pp = detect_regression(
            baseline, post, threshold=5.0
        )
        assert has_regression is False

    def test_regression_without_compensating_gain(self):
        """Regression without sufficient compensating gain SHOULD trigger."""
        baseline = {"cat_a": 0.8, "cat_b": 0.5, "overall": 0.65}
        post = {"cat_a": 0.70, "cat_b": 0.52, "overall": 0.61}
        # cat_a regresses 10pp, cat_b gains only 2pp (< 5pp threshold)
        has_regression, worst_cat, regression_pp = detect_regression(
            baseline, post, threshold=5.0
        )
        assert has_regression is True
        assert worst_cat == "cat_a"

    def test_regression_custom_threshold(self):
        baseline = {"cat_a": 0.8, "overall": 0.8}
        post = {"cat_a": 0.77, "overall": 0.77}
        # 3pp regression, threshold=2.0 -> should trigger
        has_regression, _, regression_pp = detect_regression(
            baseline, post, threshold=2.0
        )
        assert has_regression is True
        assert regression_pp == pytest.approx(3.0)

    def test_regression_just_below_threshold(self):
        baseline = {"cat_a": 0.80, "overall": 0.80}
        post = {"cat_a": 0.76, "overall": 0.76}
        # 4.0pp regression < 5.0 threshold -> NOT regression
        has_regression, _, regression_pp = detect_regression(
            baseline, post, threshold=5.0
        )
        assert has_regression is False
        assert regression_pp == pytest.approx(4.0, abs=0.01)

    def test_regression_empty_scores(self):
        has_regression, worst_cat, pp = detect_regression({}, {}, threshold=5.0)
        assert has_regression is False
        assert worst_cat == ""
        assert pp == 0.0

    def test_regression_ignores_overall(self):
        """The 'overall' key should be ignored in per-category comparison."""
        baseline = {"cat_a": 0.8, "overall": 0.3}
        post = {"cat_a": 0.82, "overall": 0.1}
        # 'overall' drops 20pp but should be ignored
        has_regression, _, _ = detect_regression(baseline, post, threshold=5.0)
        assert has_regression is False


# ============================================================
# Runner Config Tests
# ============================================================


class TestRunnerConfig:
    """Tests for LongHorizonRunnerConfig with new regression_threshold field."""

    def test_defaults(self):
        config = LongHorizonRunnerConfig()
        assert config.num_turns == 100
        assert config.num_questions == 20
        assert config.max_iterations == 3
        assert config.failure_threshold == 0.7
        assert config.regression_threshold == 5.0
        assert not config.use_multi_agent

    def test_custom_regression_threshold(self):
        config = LongHorizonRunnerConfig(regression_threshold=3.0)
        assert config.regression_threshold == 3.0


# ============================================================
# Integration Test (mocked LLM, one full iteration flow)
# ============================================================


class TestFullIterationFlow:
    """Integration test: propose -> challenge -> vote -> decide."""

    def test_full_flow_accepted_patch(self):
        """Test the full flow from proposal through voting to acceptance."""
        # Step 1: Propose a patch
        mock_proposal_response = json.dumps(
            {
                "hypothesis": "Entity indexing is missing",
                "description": "Add entity-based retrieval indexing",
                "diff": "--- a/src/agent.py\n+++ b/src/agent.py\n@@ -1 +1 @@\n-search(q)\n+entity_search(q)",
                "expected_impact": {"needle_in_haystack": 15.0},
                "risk_assessment": "Minimal risk",
                "confidence": 0.85,
            }
        )

        # Step 2: Challenge and defense
        mock_challenge_response = json.dumps(
            {
                "arguments": ["Might slow queries"],
                "alternative_approaches": ["Better embeddings"],
                "worst_case_scenario": "Queries timeout",
            }
        )
        mock_defense_response = json.dumps(
            {
                "defense": "Entity indexing is O(1), won't slow queries",
                "concerns_acknowledged": [],
                "concerns_refuted": ["Might slow queries"],
            }
        )

        # Step 3: All three reviewers accept
        mock_vote_response = json.dumps(
            {
                "vote": "accept",
                "rationale": "Clean, targeted fix",
                "concerns": [],
            }
        )

        call_count = 0

        def mock_llm(prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_proposal_response
            if call_count == 2:
                return mock_challenge_response
            if call_count == 3:
                return mock_defense_response
            return mock_vote_response

        # Run the proposal
        proposal = propose_patch(
            category="needle_in_haystack",
            category_score=0.3,
            failed_questions=[
                {
                    "question_text": "Who works on Project X?",
                    "expected_answer": "Alice",
                    "actual_answer": "Unknown",
                    "score": 0.1,
                }
            ],
            bottleneck="retrieval:keyword_search",
            suggested_fix="Add entity indexing",
            llm_call=mock_llm,
        )
        assert proposal.confidence == 0.85

        # Run the challenge
        challenge = challenge_proposal(proposal, llm_call=mock_llm)
        assert challenge.concerns_addressed is True

        # Run the voting
        review = vote_on_proposal(proposal, challenge=challenge, llm_call=mock_llm)
        assert review.decision == "accepted"

        # Check no regression
        baseline = {"needle_in_haystack": 0.3, "meta_memory": 0.8, "overall": 0.55}
        post = {"needle_in_haystack": 0.45, "meta_memory": 0.78, "overall": 0.615}
        has_regression, _, _ = detect_regression(baseline, post, threshold=5.0)
        assert has_regression is False

    def test_full_flow_rejected_patch(self):
        """Test the flow where proposal is rejected by reviewers."""
        proposal = PatchProposal(
            target_file="src/agent.py",
            hypothesis="Too complex change needed",
            description="Rewrite entire retrieval system",
            diff="",
            expected_impact={"all": 20.0},
            risk_assessment="Very high risk",
            confidence=0.2,
        )

        # With low confidence and no LLM, stub votes will reject
        review = vote_on_proposal(proposal)
        assert review.decision == "rejected"

    def test_full_flow_with_regression_revert(self):
        """Test the regression detection and revert path."""
        baseline = {"needle_in_haystack": 0.8, "meta_memory": 0.7, "overall": 0.75}
        post = {"needle_in_haystack": 0.85, "meta_memory": 0.55, "overall": 0.70}

        # meta_memory regressed 15pp, no compensating gain >= threshold
        has_regression, worst_cat, regression_pp = detect_regression(
            baseline, post, threshold=5.0
        )
        assert has_regression is True
        assert worst_cat == "meta_memory"
        assert regression_pp == pytest.approx(15.0)

        # Verify this would be logged in patch history
        history = PatchHistory()
        history.reverted_patches.append(
            {
                "target_file": "src/agent.py",
                "description": "Entity indexing",
                "revert_reason": f"{worst_cat} regressed {regression_pp:.1f}pp",
            }
        )
        assert len(history.reverted_patches) == 1
        assert "meta_memory" in history.reverted_patches[0]["revert_reason"]


# ============================================================
# Serialization Tests
# ============================================================


class TestSerialization:
    """Tests for JSON serialization of review results."""

    def test_review_result_roundtrip(self):
        """ReviewResult should serialize to dict and contain all fields."""
        proposal = PatchProposal(
            target_file="agent.py",
            hypothesis="h",
            description="d",
            diff="diff",
            confidence=0.5,
        )
        challenge = ChallengeResponse(
            challenge_arguments=["a1", "a2"],
            proposer_response="defense",
            concerns_addressed=True,
            remaining_concerns=["r1"],
        )
        result = ReviewResult(
            proposal=proposal,
            challenge=challenge,
            votes=[
                ReviewVote("quality", "accept", "good", ["minor"]),
                ReviewVote("regression", "reject", "risky", ["could break"]),
                ReviewVote("simplicity", "accept", "simple enough"),
            ],
            decision="accepted",
            consensus_rationale="2/3 accept",
        )

        d = review_result_to_dict(result)
        # Verify all top-level keys exist
        assert "proposal" in d
        assert "challenge" in d
        assert "votes" in d
        assert "decision" in d
        assert "consensus_rationale" in d

        # Verify JSON serializable
        serialized = json.dumps(d)
        deserialized = json.loads(serialized)
        assert deserialized["decision"] == "accepted"
        assert len(deserialized["votes"]) == 3
        assert deserialized["challenge"]["concerns_addressed"] is True
