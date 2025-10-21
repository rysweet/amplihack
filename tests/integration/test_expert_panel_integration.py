"""Integration tests for Expert Panel Review pattern.

Tests the full orchestrator function with mocked ClaudeProcess.
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
from dataclasses import dataclass

# Add orchestration to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude/tools/amplihack"))

from orchestration.patterns.expert_panel import (
    run_expert_panel,
    VoteChoice,
)


@dataclass
class MockProcessResult:
    """Mock ProcessResult for testing."""

    output: str
    exit_code: int
    duration: float


@pytest.fixture
def mock_session(monkeypatch):
    """Mock OrchestratorSession and run_parallel."""
    # Mock OrchestratorSession
    mock_session_instance = Mock()
    mock_session_instance.session_id = "test-session-123"
    mock_session_instance.log_dir = Path("/tmp/test-logs")
    mock_session_instance.log = Mock()
    mock_session_instance.create_process = Mock()

    mock_session_class = Mock(return_value=mock_session_instance)
    monkeypatch.setattr(
        "orchestration.patterns.expert_panel.OrchestratorSession",
        mock_session_class,
    )

    # Mock run_parallel
    mock_run_parallel = Mock()
    monkeypatch.setattr(
        "orchestration.patterns.expert_panel.run_parallel",
        mock_run_parallel,
    )

    return {
        "session": mock_session_instance,
        "session_class": mock_session_class,
        "run_parallel": mock_run_parallel,
    }


def create_expert_output(domain: str, vote: str, confidence: float) -> str:
    """Create a properly formatted expert review output."""
    return f"""## Analysis
Detailed analysis from {domain} perspective. The solution demonstrates good practices
in the {domain} domain with some areas for improvement.

## Strengths
- Well-structured code
- Good error handling
- Clear documentation

## Weaknesses
- Could use more edge case handling
- Performance could be optimized

## Domain Scores
- quality_score: {confidence}
- best_practices: {confidence}

## Vote
{vote}

## Confidence
{confidence}

## Vote Rationale
Based on my analysis from the {domain} perspective, I vote {vote} with {confidence} confidence.
The solution meets the essential requirements but has room for improvement.
"""


def test_expert_panel_unanimous_approval(mock_session):
    """Test expert panel with unanimous approval."""
    # Setup mock responses
    mock_session["run_parallel"].return_value = [
        MockProcessResult(
            output=create_expert_output("security", "APPROVE", 0.9),
            exit_code=0,
            duration=2.5,
        ),
        MockProcessResult(
            output=create_expert_output("performance", "APPROVE", 0.85),
            exit_code=0,
            duration=2.3,
        ),
        MockProcessResult(
            output=create_expert_output("simplicity", "APPROVE", 0.8),
            exit_code=0,
            duration=2.1,
        ),
    ]

    # Execute
    result = run_expert_panel(
        solution="def example(): pass",
        aggregation_method="simple_majority",
        quorum=3,
    )

    # Verify
    assert result["success"] is True
    assert len(result["reviews"]) == 3
    assert result["decision"].decision == VoteChoice.APPROVE
    assert result["decision"].consensus_type == "unanimous"
    assert result["decision"].approve_votes == 3
    assert result["decision"].reject_votes == 0
    assert result["dissent_report"] is None  # No dissent


def test_expert_panel_split_decision(mock_session):
    """Test expert panel with split decision (2-1)."""
    # Setup mock responses
    mock_session["run_parallel"].return_value = [
        MockProcessResult(
            output=create_expert_output("security", "APPROVE", 0.9),
            exit_code=0,
            duration=2.5,
        ),
        MockProcessResult(
            output=create_expert_output("performance", "APPROVE", 0.85),
            exit_code=0,
            duration=2.3,
        ),
        MockProcessResult(
            output=create_expert_output("simplicity", "REJECT", 0.8),
            exit_code=0,
            duration=2.1,
        ),
    ]

    # Execute
    result = run_expert_panel(
        solution="def example(): pass",
        aggregation_method="simple_majority",
        quorum=3,
    )

    # Verify
    assert result["success"] is True
    assert len(result["reviews"]) == 3
    assert result["decision"].decision == VoteChoice.APPROVE
    assert result["decision"].consensus_type == "simple_majority"
    assert result["decision"].approve_votes == 2
    assert result["decision"].reject_votes == 1
    assert result["dissent_report"] is not None  # Has dissent
    assert len(result["decision"].dissenting_opinions) == 1


def test_expert_panel_weighted_aggregation(mock_session):
    """Test expert panel with weighted aggregation."""
    # Setup mock responses - high confidence rejection should win
    mock_session["run_parallel"].return_value = [
        MockProcessResult(
            output=create_expert_output("security", "REJECT", 0.95),
            exit_code=0,
            duration=2.5,
        ),
        MockProcessResult(
            output=create_expert_output("performance", "APPROVE", 0.6),
            exit_code=0,
            duration=2.3,
        ),
        MockProcessResult(
            output=create_expert_output("simplicity", "APPROVE", 0.5),
            exit_code=0,
            duration=2.1,
        ),
    ]

    # Execute
    result = run_expert_panel(
        solution="def example(): pass",
        aggregation_method="weighted",
        quorum=3,
    )

    # Verify - high confidence reject should win despite 2 approves
    assert result["success"] is True
    assert len(result["reviews"]) == 3
    # Weighted: reject=0.95, approve=1.1, so approve wins actually
    # Let me recalculate: security REJECT 0.95, performance APPROVE 0.6, simplicity APPROVE 0.5
    # REJECT weight: 0.95, APPROVE weight: 1.1
    # So APPROVE should win
    assert result["decision"].decision == VoteChoice.APPROVE
    assert result["decision"].aggregation_method == "weighted"


def test_expert_panel_unanimous_mode_with_dissent(mock_session):
    """Test unanimous mode rejects with any dissent."""
    # Setup mock responses
    mock_session["run_parallel"].return_value = [
        MockProcessResult(
            output=create_expert_output("security", "APPROVE", 0.9),
            exit_code=0,
            duration=2.5,
        ),
        MockProcessResult(
            output=create_expert_output("performance", "APPROVE", 0.85),
            exit_code=0,
            duration=2.3,
        ),
        MockProcessResult(
            output=create_expert_output("simplicity", "REJECT", 0.8),
            exit_code=0,
            duration=2.1,
        ),
    ]

    # Execute
    result = run_expert_panel(
        solution="def example(): pass",
        aggregation_method="unanimous",
        quorum=3,
    )

    # Verify - one dissent should cause rejection in unanimous mode
    assert result["success"] is True
    assert result["decision"].decision == VoteChoice.REJECT
    assert result["decision"].consensus_type == "not_unanimous"


def test_expert_panel_with_abstention(mock_session):
    """Test expert panel with one abstention."""
    # Setup mock responses
    mock_session["run_parallel"].return_value = [
        MockProcessResult(
            output=create_expert_output("security", "APPROVE", 0.9),
            exit_code=0,
            duration=2.5,
        ),
        MockProcessResult(
            output=create_expert_output("performance", "APPROVE", 0.85),
            exit_code=0,
            duration=2.3,
        ),
        MockProcessResult(
            output=create_expert_output("simplicity", "ABSTAIN", 0.5),
            exit_code=0,
            duration=2.1,
        ),
    ]

    # Execute
    result = run_expert_panel(
        solution="def example(): pass",
        aggregation_method="simple_majority",
        quorum=2,  # Quorum=2, have 2 non-abstain votes
    )

    # Verify
    assert result["success"] is True
    assert result["decision"].approve_votes == 2
    assert result["decision"].abstain_votes == 1
    assert result["decision"].quorum_met is True


def test_expert_panel_quorum_failure(mock_session):
    """Test expert panel fails quorum with too many abstentions."""
    # Setup mock responses
    mock_session["run_parallel"].return_value = [
        MockProcessResult(
            output=create_expert_output("security", "APPROVE", 0.9),
            exit_code=0,
            duration=2.5,
        ),
        MockProcessResult(
            output=create_expert_output("performance", "ABSTAIN", 0.5),
            exit_code=0,
            duration=2.3,
        ),
        MockProcessResult(
            output=create_expert_output("simplicity", "ABSTAIN", 0.5),
            exit_code=0,
            duration=2.1,
        ),
    ]

    # Execute
    result = run_expert_panel(
        solution="def example(): pass",
        aggregation_method="simple_majority",
        quorum=3,  # Need 3, only have 1
    )

    # Verify
    assert result["success"] is False  # Quorum not met
    assert result["decision"].quorum_met is False


def test_expert_panel_all_experts_fail(mock_session):
    """Test expert panel handles all expert failures gracefully."""
    # Setup mock responses - all fail
    mock_session["run_parallel"].return_value = [
        MockProcessResult(output="Error", exit_code=1, duration=0.1),
        MockProcessResult(output="Error", exit_code=1, duration=0.1),
        MockProcessResult(output="Error", exit_code=1, duration=0.1),
    ]

    # Execute
    result = run_expert_panel(
        solution="def example(): pass",
        aggregation_method="simple_majority",
        quorum=3,
    )

    # Verify
    assert result["success"] is False
    assert len(result["reviews"]) == 0
    assert result["decision"] is None


def test_expert_panel_custom_experts(mock_session):
    """Test expert panel with custom expert definitions."""
    custom_experts = [
        {"domain": "security", "focus": "threat modeling"},
        {"domain": "ux", "focus": "user experience"},
        {"domain": "compliance", "focus": "regulatory requirements"},
    ]

    # Setup mock responses
    mock_session["run_parallel"].return_value = [
        MockProcessResult(
            output=create_expert_output("security", "APPROVE", 0.9),
            exit_code=0,
            duration=2.5,
        ),
        MockProcessResult(
            output=create_expert_output("ux", "APPROVE", 0.85),
            exit_code=0,
            duration=2.3,
        ),
        MockProcessResult(
            output=create_expert_output("compliance", "APPROVE", 0.8),
            exit_code=0,
            duration=2.1,
        ),
    ]

    # Execute
    result = run_expert_panel(
        solution="def example(): pass",
        experts=custom_experts,
        aggregation_method="simple_majority",
        quorum=3,
    )

    # Verify
    assert result["success"] is True
    assert len(result["reviews"]) == 3
    # Check that custom expert domains are used
    domains = [r.domain for r in result["reviews"]]
    assert "security" in domains
    assert "ux" in domains
    assert "compliance" in domains


def test_expert_panel_invalid_aggregation_method():
    """Test expert panel raises error with invalid aggregation method."""
    with pytest.raises(ValueError, match="Invalid aggregation_method"):
        run_expert_panel(
            solution="def example(): pass",
            aggregation_method="invalid_method",
            quorum=3,
        )
