"""Agentic tests for Expert Panel Review pattern.

These tests use real Claude agents to validate the pattern works end-to-end.
Marked with @pytest.mark.gadugi for selective execution.
"""

import sys
from pathlib import Path

import pytest

# Add orchestration to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude/tools/amplihack"))

from orchestration.patterns.expert_panel import (
    VoteChoice,
    run_expert_panel,
)


@pytest.mark.gadugi
def test_expert_panel_simple_code_review():
    """Test expert panel reviewing simple Python code.

    Real scenario: Review a basic password hashing implementation.
    """
    solution = """
# Password hashing implementation
import hashlib
import os

def hash_password(password: str) -> str:
    '''Hash a password using SHA256 with salt.'''
    salt = os.urandom(32)
    pwdhash = hashlib.pbkdf2_hmac('sha256',
                                   password.encode('utf-8'),
                                   salt,
                                   100000)
    return salt.hex() + pwdhash.hex()

def verify_password(stored_password: str, provided_password: str) -> bool:
    '''Verify a password against a stored hash.'''
    salt = bytes.fromhex(stored_password[:64])
    stored_hash = stored_password[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha256',
                                   provided_password.encode('utf-8'),
                                   salt,
                                   100000)
    return pwdhash.hex() == stored_hash
"""

    result = run_expert_panel(
        solution=solution,
        aggregation_method="simple_majority",
        quorum=3,
        timeout=120,  # 2 minutes per expert
    )

    # Verify structure
    assert "reviews" in result
    assert "decision" in result
    assert "success" in result

    # Should have 3 expert reviews
    assert len(result["reviews"]) >= 2  # At least 2 should succeed

    # Each review should have proper structure
    for review in result["reviews"]:
        assert review.expert_id
        assert review.domain
        assert review.vote in [VoteChoice.APPROVE, VoteChoice.REJECT, VoteChoice.ABSTAIN]
        assert 0.0 <= review.confidence <= 1.0
        assert review.vote_rationale

    # Should have a decision
    if result["success"]:
        assert result["decision"] is not None
        assert result["decision"].decision in [VoteChoice.APPROVE, VoteChoice.REJECT]

    # Print results for manual inspection
    print("\n=== Expert Panel Results ===")
    print(f"Decision: {result['decision'].decision.value if result['decision'] else 'NONE'}")
    print(
        f"Votes: {result['decision'].approve_votes} approve, {result['decision'].reject_votes} reject"
    )
    print(f"Consensus: {result['decision'].consensus_type if result['decision'] else 'N/A'}")

    for review in result["reviews"]:
        print(
            f"\n{review.domain} Expert: {review.vote.value} (confidence: {review.confidence:.2f})"
        )
        print(f"  Rationale: {review.vote_rationale[:100]}...")


@pytest.mark.gadugi
def test_expert_panel_weighted_decision():
    """Test expert panel with weighted aggregation.

    Tests that high-confidence votes carry more weight.
    """
    solution = """
# Simple implementation
def add(a: int, b: int) -> int:
    return a + b
"""

    result = run_expert_panel(
        solution=solution,
        aggregation_method="weighted",
        quorum=3,
        timeout=90,
    )

    assert result["success"]
    assert result["decision"] is not None
    assert result["decision"].aggregation_method == "weighted"

    # Confidence should be set based on weighted votes
    assert result["decision"].confidence > 0.0

    print("\n=== Weighted Decision ===")
    print(f"Decision: {result['decision'].decision.value}")
    print(f"Confidence: {result['decision'].confidence:.2f}")


@pytest.mark.gadugi
def test_expert_panel_byzantine_robustness():
    """Test expert panel Byzantine robustness.

    Submit code that might generate split opinions to verify
    the aggregation handles disagreement properly.
    """
    # Deliberately complex code that might split opinions
    solution = """
# Complex implementation with trade-offs
from functools import wraps
from typing import Callable, Any
import time

def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
):
    '''Decorator for retry logic with exponential backoff.'''
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = base_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(min(delay, max_delay))
                    delay *= 2
            return None
        return wrapper
    return decorator

@retry_with_exponential_backoff(max_retries=5)
def unstable_api_call(endpoint: str) -> dict:
    '''Make an API call with automatic retry.'''
    import requests
    response = requests.get(endpoint)
    response.raise_for_status()
    return response.json()
"""

    result = run_expert_panel(
        solution=solution,
        aggregation_method="simple_majority",
        quorum=3,
        timeout=120,
    )

    assert result["success"]

    # Count votes
    approve_votes = result["decision"].approve_votes
    reject_votes = result["decision"].reject_votes

    # Should have some votes on each side (Byzantine scenario)
    total_votes = approve_votes + reject_votes
    assert total_votes >= 3

    # Verify dissent report exists if there's disagreement
    if reject_votes > 0 and approve_votes > 0:
        if (result["decision"].decision == VoteChoice.APPROVE and reject_votes > 0) or (
            result["decision"].decision == VoteChoice.REJECT and approve_votes > 0
        ):
            assert result["dissent_report"] is not None

    print("\n=== Byzantine Robustness Test ===")
    print(f"Decision: {result['decision'].decision.value}")
    print(f"Votes: {approve_votes} approve, {reject_votes} reject")
    print(f"Consensus: {result['decision'].consensus_type}")

    if result["dissent_report"]:
        print(f"Dissent: {len(result['dissent_report'].dissent_experts)} experts dissented")
        print(f"Concerns: {result['dissent_report'].concerns_raised}")


@pytest.mark.gadugi
def test_expert_panel_unanimous_requirement():
    """Test expert panel with unanimous requirement.

    Submit very simple, clearly correct code that should get unanimous approval.
    """
    solution = """
# Trivially correct implementation
def is_even(n: int) -> bool:
    '''Check if a number is even.'''
    return n % 2 == 0
"""

    result = run_expert_panel(
        solution=solution,
        aggregation_method="unanimous",
        quorum=3,
        timeout=90,
    )

    assert result["success"]

    # With unanimous requirement, expect either all approve or rejection
    if result["decision"].decision == VoteChoice.APPROVE:
        # If approved, should be unanimous
        assert result["decision"].consensus_type == "unanimous"
        assert result["decision"].approve_votes == len(result["reviews"])
        assert result["decision"].reject_votes == 0

    print("\n=== Unanimous Mode Test ===")
    print(f"Decision: {result['decision'].decision.value}")
    print(f"Consensus: {result['decision'].consensus_type}")
    print(f"All experts: {[r.vote.value for r in result['reviews']]}")


@pytest.mark.gadugi
def test_expert_panel_custom_domains():
    """Test expert panel with custom expert domains.

    Define specific expert domains relevant to the solution.
    """
    solution = """
# API endpoint implementation
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    username: str
    email: str

@app.post("/users/")
async def create_user(user: User):
    # Store user logic here
    return {"id": 123, "username": user.username}
"""

    custom_experts = [
        {"domain": "api_design", "focus": "REST API design, endpoint structure, HTTP semantics"},
        {"domain": "security", "focus": "authentication, authorization, input validation"},
        {"domain": "data_modeling", "focus": "data structures, validation, schema design"},
    ]

    result = run_expert_panel(
        solution=solution,
        experts=custom_experts,
        aggregation_method="simple_majority",
        quorum=3,
        timeout=120,
    )

    assert result["success"]
    assert len(result["reviews"]) >= 2

    # Verify custom domains were used
    domains = [r.domain for r in result["reviews"]]
    assert "api_design" in domains or "security" in domains or "data_modeling" in domains

    print("\n=== Custom Domains Test ===")
    print(f"Experts used: {domains}")
    print(f"Decision: {result['decision'].decision.value}")
