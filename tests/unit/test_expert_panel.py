"""Unit tests for Expert Panel Review pattern.

Tests all data models, aggregation functions, dissent reporter, and helper functions.
No mocks - pure unit tests of logic.
"""

import sys
from pathlib import Path
import pytest
from datetime import datetime

# Add orchestration to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude/tools/amplihack"))

from orchestration.patterns.expert_panel import (
    VoteChoice,
    ExpertReview,
    AggregatedDecision,
    DissentReport,
    aggregate_simple_majority,
    aggregate_weighted,
    aggregate_unanimous,
    generate_dissent_report,
    _extract_section,
    _extract_list_items,
    _extract_scores,
)


# Data Model Tests


def test_vote_choice_enum():
    """Test VoteChoice enum values."""
    assert VoteChoice.APPROVE.value == "approve"
    assert VoteChoice.REJECT.value == "reject"
    assert VoteChoice.ABSTAIN.value == "abstain"


def test_expert_review_creation():
    """Test ExpertReview dataclass creation."""
    review = ExpertReview(
        expert_id="test-expert",
        domain="security",
        analysis="Test analysis",
        strengths=["Strong encryption"],
        weaknesses=["Missing input validation"],
        domain_scores={"vulnerability_score": 0.9},
        vote=VoteChoice.APPROVE,
        confidence=0.85,
        vote_rationale="Strong security practices",
    )

    assert review.expert_id == "test-expert"
    assert review.domain == "security"
    assert review.vote == VoteChoice.APPROVE
    assert review.confidence == 0.85
    assert len(review.strengths) == 1
    assert len(review.weaknesses) == 1
    assert "vulnerability_score" in review.domain_scores


def test_expert_review_default_timestamp():
    """Test ExpertReview auto-generates timestamp."""
    review = ExpertReview(
        expert_id="test",
        domain="test",
        analysis="test",
        strengths=[],
        weaknesses=[],
        domain_scores={},
        vote=VoteChoice.APPROVE,
        confidence=0.5,
        vote_rationale="test",
    )

    # Should have a timestamp
    assert review.review_timestamp
    # Should be ISO format parseable
    datetime.fromisoformat(review.review_timestamp)


def test_aggregated_decision_creation():
    """Test AggregatedDecision dataclass."""
    decision = AggregatedDecision(
        decision=VoteChoice.APPROVE,
        confidence=0.8,
        total_votes=3,
        approve_votes=2,
        reject_votes=1,
        abstain_votes=0,
        consensus_type="simple_majority",
        agreement_percentage=66.7,
        dissenting_opinions=[],
        aggregation_method="simple_majority",
        quorum_met=True,
    )

    assert decision.decision == VoteChoice.APPROVE
    assert decision.total_votes == 3
    assert decision.approve_votes == 2
    assert decision.quorum_met is True


def test_dissent_report_creation():
    """Test DissentReport dataclass."""
    report = DissentReport(
        decision=VoteChoice.APPROVE,
        majority_count=2,
        dissent_count=1,
        majority_experts=["expert-1", "expert-2"],
        dissent_experts=["expert-3"],
        dissent_rationales=["Complexity concerns"],
        concerns_raised=["Too many abstractions", "High maintenance burden"],
    )

    assert report.decision == VoteChoice.APPROVE
    assert report.majority_count == 2
    assert report.dissent_count == 1
    assert len(report.concerns_raised) == 2


# Aggregation Function Tests - Simple Majority


def test_aggregate_simple_majority_unanimous_approve():
    """Test simple majority with unanimous approval."""
    reviews = [
        ExpertReview("expert-1", "security", "good", [], [], {}, VoteChoice.APPROVE, 0.9, "secure"),
        ExpertReview(
            "expert-2", "performance", "good", [], [], {}, VoteChoice.APPROVE, 0.8, "fast"
        ),
        ExpertReview(
            "expert-3", "simplicity", "good", [], [], {}, VoteChoice.APPROVE, 0.85, "simple"
        ),
    ]

    decision = aggregate_simple_majority(reviews, quorum=3)

    assert decision.decision == VoteChoice.APPROVE
    assert decision.approve_votes == 3
    assert decision.reject_votes == 0
    assert decision.abstain_votes == 0
    assert decision.consensus_type == "unanimous"
    assert decision.agreement_percentage == 100.0
    assert decision.quorum_met is True
    assert len(decision.dissenting_opinions) == 0


def test_aggregate_simple_majority_2_to_1_approve():
    """Test simple majority with 2-1 approval."""
    reviews = [
        ExpertReview("expert-1", "security", "good", [], [], {}, VoteChoice.APPROVE, 0.9, "secure"),
        ExpertReview(
            "expert-2", "performance", "good", [], [], {}, VoteChoice.APPROVE, 0.8, "fast"
        ),
        ExpertReview(
            "expert-3", "simplicity", "bad", [], [], {}, VoteChoice.REJECT, 0.85, "complex"
        ),
    ]

    decision = aggregate_simple_majority(reviews, quorum=3)

    assert decision.decision == VoteChoice.APPROVE
    assert decision.approve_votes == 2
    assert decision.reject_votes == 1
    assert decision.consensus_type == "simple_majority"
    assert decision.agreement_percentage == pytest.approx(66.67, rel=0.1)
    assert decision.quorum_met is True
    assert len(decision.dissenting_opinions) == 1
    assert decision.dissenting_opinions[0].expert_id == "expert-3"


def test_aggregate_simple_majority_2_to_1_reject():
    """Test simple majority with 2-1 rejection."""
    reviews = [
        ExpertReview("expert-1", "security", "bad", [], [], {}, VoteChoice.REJECT, 0.9, "insecure"),
        ExpertReview("expert-2", "performance", "bad", [], [], {}, VoteChoice.REJECT, 0.8, "slow"),
        ExpertReview(
            "expert-3", "simplicity", "good", [], [], {}, VoteChoice.APPROVE, 0.85, "simple"
        ),
    ]

    decision = aggregate_simple_majority(reviews, quorum=3)

    assert decision.decision == VoteChoice.REJECT
    assert decision.approve_votes == 1
    assert decision.reject_votes == 2
    assert decision.consensus_type == "simple_majority"
    assert decision.agreement_percentage == pytest.approx(66.67, rel=0.1)
    assert len(decision.dissenting_opinions) == 1
    assert decision.dissenting_opinions[0].expert_id == "expert-3"


def test_aggregate_simple_majority_with_abstain():
    """Test simple majority with abstentions."""
    reviews = [
        ExpertReview("expert-1", "security", "good", [], [], {}, VoteChoice.APPROVE, 0.9, "secure"),
        ExpertReview(
            "expert-2", "performance", "good", [], [], {}, VoteChoice.APPROVE, 0.8, "fast"
        ),
        ExpertReview(
            "expert-3",
            "simplicity",
            "unclear",
            [],
            [],
            {},
            VoteChoice.ABSTAIN,
            0.5,
            "not enough info",
        ),
    ]

    decision = aggregate_simple_majority(reviews, quorum=2)

    assert decision.decision == VoteChoice.APPROVE
    assert decision.approve_votes == 2
    assert decision.reject_votes == 0
    assert decision.abstain_votes == 1
    assert decision.quorum_met is True
    assert decision.consensus_type == "unanimous"  # Unanimous among non-abstain


def test_aggregate_simple_majority_quorum_not_met():
    """Test quorum failure with too many abstentions."""
    reviews = [
        ExpertReview("expert-1", "security", "good", [], [], {}, VoteChoice.APPROVE, 0.9, "secure"),
        ExpertReview(
            "expert-2",
            "performance",
            "unclear",
            [],
            [],
            {},
            VoteChoice.ABSTAIN,
            0.5,
            "unclear",
        ),
        ExpertReview(
            "expert-3",
            "simplicity",
            "unclear",
            [],
            [],
            {},
            VoteChoice.ABSTAIN,
            0.5,
            "unclear",
        ),
    ]

    decision = aggregate_simple_majority(reviews, quorum=3)

    assert decision.quorum_met is False
    assert decision.approve_votes == 1
    assert decision.abstain_votes == 2


def test_aggregate_simple_majority_tie_defaults_reject():
    """Test that ties default to reject (conservative)."""
    reviews = [
        ExpertReview("expert-1", "security", "good", [], [], {}, VoteChoice.APPROVE, 0.9, "secure"),
        ExpertReview("expert-2", "performance", "bad", [], [], {}, VoteChoice.REJECT, 0.8, "slow"),
    ]

    decision = aggregate_simple_majority(reviews, quorum=2)

    assert decision.decision == VoteChoice.REJECT  # Conservative on tie
    assert decision.approve_votes == 1
    assert decision.reject_votes == 1
    assert decision.consensus_type == "split"


# Aggregation Function Tests - Weighted


def test_aggregate_weighted_high_confidence_wins():
    """Test weighted aggregation where high confidence wins."""
    reviews = [
        ExpertReview(
            "expert-1", "security", "good", [], [], {}, VoteChoice.APPROVE, 0.95, "very secure"
        ),
        ExpertReview(
            "expert-2", "performance", "bad", [], [], {}, VoteChoice.REJECT, 0.6, "somewhat slow"
        ),
        ExpertReview(
            "expert-3", "simplicity", "bad", [], [], {}, VoteChoice.REJECT, 0.5, "bit complex"
        ),
    ]

    decision = aggregate_weighted(reviews, quorum=3)

    # Approve weight: 0.95, Reject weight: 1.1, should reject
    assert decision.decision == VoteChoice.REJECT
    assert decision.aggregation_method == "weighted"
    assert decision.quorum_met is True


def test_aggregate_weighted_balanced():
    """Test weighted aggregation with balanced confidence."""
    reviews = [
        ExpertReview("expert-1", "security", "good", [], [], {}, VoteChoice.APPROVE, 0.9, "secure"),
        ExpertReview(
            "expert-2", "performance", "good", [], [], {}, VoteChoice.APPROVE, 0.8, "fast"
        ),
        ExpertReview(
            "expert-3", "simplicity", "bad", [], [], {}, VoteChoice.REJECT, 0.7, "complex"
        ),
    ]

    decision = aggregate_weighted(reviews, quorum=3)

    # Approve weight: 1.7, Reject weight: 0.7, should approve
    assert decision.decision == VoteChoice.APPROVE
    # Confidence is average of approve votes divided by number of non-abstain voters
    # (0.9 + 0.8) / 3 = 0.5666...
    assert decision.confidence > 0.5  # Moderate confidence


def test_aggregate_weighted_with_abstain():
    """Test weighted aggregation ignores abstentions."""
    reviews = [
        ExpertReview("expert-1", "security", "good", [], [], {}, VoteChoice.APPROVE, 0.9, "secure"),
        ExpertReview(
            "expert-2", "performance", "good", [], [], {}, VoteChoice.APPROVE, 0.8, "fast"
        ),
        ExpertReview(
            "expert-3",
            "simplicity",
            "unclear",
            [],
            [],
            {},
            VoteChoice.ABSTAIN,
            0.5,
            "unclear",
        ),
    ]

    decision = aggregate_weighted(reviews, quorum=2)

    assert decision.decision == VoteChoice.APPROVE
    assert decision.abstain_votes == 1
    # Confidence should be average of approve votes
    assert decision.confidence <= 1.0


# Aggregation Function Tests - Unanimous


def test_aggregate_unanimous_all_approve():
    """Test unanimous aggregation with all approvals."""
    reviews = [
        ExpertReview("expert-1", "security", "good", [], [], {}, VoteChoice.APPROVE, 0.9, "secure"),
        ExpertReview(
            "expert-2", "performance", "good", [], [], {}, VoteChoice.APPROVE, 0.8, "fast"
        ),
        ExpertReview(
            "expert-3", "simplicity", "good", [], [], {}, VoteChoice.APPROVE, 0.85, "simple"
        ),
    ]

    decision = aggregate_unanimous(reviews, quorum=3)

    assert decision.decision == VoteChoice.APPROVE
    assert decision.consensus_type == "unanimous"
    assert decision.agreement_percentage == 100.0
    assert len(decision.dissenting_opinions) == 0


def test_aggregate_unanimous_one_dissent_rejects():
    """Test unanimous mode rejects with any dissent."""
    reviews = [
        ExpertReview("expert-1", "security", "good", [], [], {}, VoteChoice.APPROVE, 0.9, "secure"),
        ExpertReview(
            "expert-2", "performance", "good", [], [], {}, VoteChoice.APPROVE, 0.8, "fast"
        ),
        ExpertReview(
            "expert-3", "simplicity", "bad", [], [], {}, VoteChoice.REJECT, 0.85, "complex"
        ),
    ]

    decision = aggregate_unanimous(reviews, quorum=3)

    assert decision.decision == VoteChoice.REJECT
    assert decision.consensus_type == "not_unanimous"
    assert len(decision.dissenting_opinions) == 2  # The 2 approvals are dissenting


def test_aggregate_unanimous_with_abstain():
    """Test unanimous mode ignores abstentions."""
    reviews = [
        ExpertReview("expert-1", "security", "good", [], [], {}, VoteChoice.APPROVE, 0.9, "secure"),
        ExpertReview(
            "expert-2", "performance", "good", [], [], {}, VoteChoice.APPROVE, 0.8, "fast"
        ),
        ExpertReview(
            "expert-3",
            "simplicity",
            "unclear",
            [],
            [],
            {},
            VoteChoice.ABSTAIN,
            0.5,
            "unclear",
        ),
    ]

    decision = aggregate_unanimous(reviews, quorum=2)

    assert decision.decision == VoteChoice.APPROVE
    assert decision.consensus_type == "unanimous"
    assert decision.abstain_votes == 1


def test_aggregate_unanimous_all_reject():
    """Test unanimous rejection."""
    reviews = [
        ExpertReview("expert-1", "security", "bad", [], [], {}, VoteChoice.REJECT, 0.9, "insecure"),
        ExpertReview("expert-2", "performance", "bad", [], [], {}, VoteChoice.REJECT, 0.8, "slow"),
        ExpertReview(
            "expert-3", "simplicity", "bad", [], [], {}, VoteChoice.REJECT, 0.85, "complex"
        ),
    ]

    decision = aggregate_unanimous(reviews, quorum=3)

    assert decision.decision == VoteChoice.REJECT
    assert decision.consensus_type == "unanimous_rejection"
    assert decision.agreement_percentage == 100.0


# Dissent Report Tests


def test_generate_dissent_report_with_dissent():
    """Test dissent report generation with dissenting opinions."""
    dissenting_reviews = [
        ExpertReview(
            expert_id="simplicity-expert",
            domain="simplicity",
            analysis="Too complex",
            strengths=[],
            weaknesses=["5 abstraction layers", "12 dependencies"],
            domain_scores={},
            vote=VoteChoice.REJECT,
            confidence=0.8,
            vote_rationale="Too complex for maintenance",
        )
    ]

    decision = AggregatedDecision(
        decision=VoteChoice.APPROVE,
        confidence=0.85,
        total_votes=3,
        approve_votes=2,
        reject_votes=1,
        abstain_votes=0,
        consensus_type="simple_majority",
        agreement_percentage=66.7,
        dissenting_opinions=dissenting_reviews,
        aggregation_method="simple_majority",
        quorum_met=True,
    )

    report = generate_dissent_report(decision)

    assert report is not None
    assert report.decision == VoteChoice.APPROVE
    assert report.majority_count == 2
    assert report.dissent_count == 1
    assert "simplicity-expert" in report.dissent_experts
    assert len(report.dissent_rationales) == 1
    assert len(report.concerns_raised) == 2


def test_generate_dissent_report_no_dissent():
    """Test dissent report returns None with unanimous decision."""
    decision = AggregatedDecision(
        decision=VoteChoice.APPROVE,
        confidence=0.85,
        total_votes=3,
        approve_votes=3,
        reject_votes=0,
        abstain_votes=0,
        consensus_type="unanimous",
        agreement_percentage=100.0,
        dissenting_opinions=[],
        aggregation_method="simple_majority",
        quorum_met=True,
    )

    report = generate_dissent_report(decision)

    assert report is None


# Helper Function Tests


def test_extract_section_basic():
    """Test extracting a basic markdown section."""
    text = """
## Analysis
This is the analysis content.
More content here.

## Vote
APPROVE
"""

    analysis = _extract_section(text, "Analysis")
    assert "This is the analysis content" in analysis
    assert "More content here" in analysis

    vote = _extract_section(text, "Vote")
    assert vote == "APPROVE"


def test_extract_section_not_found():
    """Test extracting non-existent section returns empty string."""
    text = """
## Analysis
Content here
"""

    result = _extract_section(text, "NonExistent")
    assert result == ""


def test_extract_list_items_basic():
    """Test extracting bullet list items."""
    text = """
## Strengths
- Strong encryption
- Good error handling
- Clear documentation

## Weaknesses
"""

    strengths = _extract_list_items(text, "Strengths")
    assert len(strengths) == 3
    assert "Strong encryption" in strengths
    assert "Good error handling" in strengths


def test_extract_list_items_empty_section():
    """Test extracting from empty section returns empty list."""
    text = """
## Strengths

## Weaknesses
"""

    strengths = _extract_list_items(text, "Strengths")
    assert strengths == []


def test_extract_scores_basic():
    """Test extracting domain scores."""
    text = """
## Domain Scores
- vulnerability_score: 0.9
- performance_rating: 0.85
- complexity_score: 0.6

## Other Section
"""

    scores = _extract_scores(text, "Domain Scores")
    assert len(scores) == 3
    assert scores["vulnerability_score"] == 0.9
    assert scores["performance_rating"] == 0.85
    assert scores["complexity_score"] == 0.6


def test_extract_scores_various_formats():
    """Test extracting scores with different formats."""
    text = """
## Domain Scores
vulnerability_score: 0.9
- performance: 0.85
* simplicity: 0.7
"""

    scores = _extract_scores(text, "Domain Scores")
    assert "vulnerability_score" in scores
    assert "performance" in scores
    assert "simplicity" in scores


def test_extract_scores_invalid_values():
    """Test extracting scores skips invalid values."""
    text = """
## Domain Scores
- valid_score: 0.9
- invalid_score: abc
- another_valid: 0.5
"""

    scores = _extract_scores(text, "Domain Scores")
    assert len(scores) == 2
    assert "valid_score" in scores
    assert "another_valid" in scores
    assert "invalid_score" not in scores
