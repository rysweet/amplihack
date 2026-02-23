"""A/B reviewer voting for self-improvement patch proposals.

Implements multi-perspective review of proposed patches before they are applied.
Three reviewer perspectives (quality, regression, simplicity) vote on each
proposal, with majority vote determining the outcome.

Philosophy:
- No patch applied without review consensus
- Multiple perspectives catch blind spots
- Every vote has a rationale for traceability
- Challenge phase forces the proposer to defend the change
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .patch_proposer import PatchProposal

logger = logging.getLogger(__name__)


@dataclass
class ReviewVote:
    """A single reviewer's vote on a patch proposal.

    Attributes:
        reviewer_id: Identifier for the reviewer perspective
        vote: Decision - "accept", "reject", or "modify"
        rationale: Explanation of why this vote was cast
        concerns: Specific concerns about the proposal
        suggested_modifications: Optional modifications if vote is "modify"
    """

    reviewer_id: str
    vote: str  # "accept" | "reject" | "modify"
    rationale: str
    concerns: list[str] = field(default_factory=list)
    suggested_modifications: str | None = None


@dataclass
class ChallengeResponse:
    """Result of the challenge phase for a patch proposal.

    Attributes:
        challenge_arguments: Devil's advocate arguments against the patch
        proposer_response: The proposer's defense against the challenge
        concerns_addressed: Whether the proposer adequately addressed concerns
        remaining_concerns: Any concerns that were not satisfactorily addressed
    """

    challenge_arguments: list[str]
    proposer_response: str
    concerns_addressed: bool
    remaining_concerns: list[str] = field(default_factory=list)


@dataclass
class ReviewResult:
    """Aggregated result of the review process for a proposal.

    Attributes:
        proposal: The patch proposal being reviewed
        challenge: The challenge/response exchange (if performed)
        votes: Individual reviewer votes
        decision: Final aggregated decision
        consensus_rationale: Summary rationale for the final decision
    """

    proposal: PatchProposal
    challenge: ChallengeResponse | None
    votes: list[ReviewVote]
    decision: str  # "accepted" | "rejected" | "modified"
    consensus_rationale: str


# ============================================================
# Reviewer system prompts
# ============================================================

QUALITY_REVIEWER_PROMPT = """You are a CODE QUALITY reviewer. Evaluate this patch proposal for:
- Engineering best practices (clean code, no side effects)
- Proper error handling
- Appropriate use of abstractions
- Consistency with existing code style
- Whether the change is well-tested and testable

Respond with JSON:
{{
  "vote": "accept" | "reject" | "modify",
  "rationale": "Why this vote",
  "concerns": ["list of specific concerns"],
  "suggested_modifications": "optional: what to change"
}}"""

REGRESSION_REVIEWER_PROMPT = """You are a REGRESSION reviewer. Evaluate this patch proposal for:
- Could this change break OTHER categories that currently pass?
- Does it modify shared code paths that affect unrelated functionality?
- Are there edge cases that could cause unexpected failures?
- Is the change scoped narrowly enough to avoid collateral damage?

Respond with JSON:
{{
  "vote": "accept" | "reject" | "modify",
  "rationale": "Why this vote",
  "concerns": ["list of specific concerns"],
  "suggested_modifications": "optional: what to change"
}}"""

SIMPLICITY_REVIEWER_PROMPT = """You are a SIMPLICITY reviewer. Evaluate this patch proposal for:
- Is this the SIMPLEST possible fix for the identified problem?
- Could a smaller change achieve the same result?
- Does it add unnecessary complexity or abstraction?
- Could a prompt-only change work instead of a code change?

Respond with JSON:
{{
  "vote": "accept" | "reject" | "modify",
  "rationale": "Why this vote",
  "concerns": ["list of specific concerns"],
  "suggested_modifications": "optional: what to change"
}}"""

DEVIL_ADVOCATE_PROMPT = """You are a DEVIL'S ADVOCATE. Your job is to argue AGAINST this proposed patch.

Find the strongest arguments for why this patch should NOT be applied:
- What assumptions could be wrong?
- What could this break?
- Is there a simpler alternative?
- Is the hypothesis even correct?

Be aggressive but fair. Your goal is to stress-test the proposal.

Respond with JSON:
{{
  "arguments": ["list of strong arguments against the patch"],
  "alternative_approaches": ["list of potentially better approaches"],
  "worst_case_scenario": "what happens if this patch causes harm"
}}"""


def _format_proposal_for_review(
    proposal: PatchProposal,
    challenge: ChallengeResponse | None = None,
) -> str:
    """Format a proposal for reviewer consumption.

    Args:
        proposal: The patch proposal
        challenge: Optional challenge response to include

    Returns:
        Formatted text for the reviewer prompt
    """
    text = f"""## Patch Proposal

**Target File**: {proposal.target_file}
**Hypothesis**: {proposal.hypothesis}
**Description**: {proposal.description}
**Confidence**: {proposal.confidence:.0%}
**Risk Assessment**: {proposal.risk_assessment}

### Expected Impact
"""
    for cat, delta in proposal.expected_impact.items():
        text += f"- {cat}: {delta:+.1f}pp\n"

    if proposal.diff:
        text += f"\n### Diff\n```diff\n{proposal.diff[:2000]}\n```\n"

    if challenge:
        text += "\n### Challenge Phase Results\n"
        text += f"**Concerns Addressed**: {'Yes' if challenge.concerns_addressed else 'No'}\n"
        for arg in challenge.challenge_arguments:
            text += f"- Challenge: {arg}\n"
        text += f"\n**Proposer Defense**: {challenge.proposer_response[:500]}\n"
        if challenge.remaining_concerns:
            text += "\n**Remaining Concerns**:\n"
            for c in challenge.remaining_concerns:
                text += f"- {c}\n"

    return text


def _parse_vote_response(response_text: str, reviewer_id: str) -> ReviewVote:
    """Parse an LLM response into a ReviewVote.

    Args:
        response_text: Raw LLM response
        reviewer_id: The reviewer perspective ID

    Returns:
        Parsed ReviewVote
    """
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        parsed = json.loads(text)
        vote = parsed.get("vote", "reject")
        if vote not in ("accept", "reject", "modify"):
            vote = "reject"

        return ReviewVote(
            reviewer_id=reviewer_id,
            vote=vote,
            rationale=parsed.get("rationale", "No rationale provided"),
            concerns=parsed.get("concerns", []),
            suggested_modifications=parsed.get("suggested_modifications"),
        )
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("Failed to parse %s vote: %s", reviewer_id, e)
        return ReviewVote(
            reviewer_id=reviewer_id,
            vote="reject",
            rationale=f"Parse error: {e}",
            concerns=["Could not parse reviewer response"],
        )


def challenge_proposal(
    proposal: PatchProposal,
    llm_call: Any | None = None,
) -> ChallengeResponse:
    """Run the devil's advocate challenge phase on a proposal.

    A separate LLM call argues against the proposal. The "proposer" then
    responds to the challenge. Only if concerns are addressed does the
    proposal proceed to voting.

    Args:
        proposal: The patch proposal to challenge
        llm_call: LLM callable. Signature: (prompt: str) -> str.

    Returns:
        ChallengeResponse with the exchange results
    """
    if llm_call is None:
        return ChallengeResponse(
            challenge_arguments=["No LLM available for challenge"],
            proposer_response="Challenge phase skipped (no LLM)",
            concerns_addressed=True,
            remaining_concerns=[],
        )

    # Step 1: Devil's advocate argues against the proposal
    proposal_text = _format_proposal_for_review(proposal)
    challenge_prompt = f"{DEVIL_ADVOCATE_PROMPT}\n\n{proposal_text}"

    try:
        challenge_text = llm_call(challenge_prompt)
        challenge_text = challenge_text.strip()
        if challenge_text.startswith("```"):
            lines = challenge_text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            challenge_text = "\n".join(lines)

        challenge_data = json.loads(challenge_text)
        challenge_arguments = challenge_data.get("arguments", [])
    except (json.JSONDecodeError, TypeError):
        challenge_arguments = ["Could not parse challenge arguments"]

    # Step 2: Proposer responds to the challenge
    defense_prompt = f"""The following arguments have been raised AGAINST your proposed patch:

## Arguments Against
{chr(10).join(f'- {a}' for a in challenge_arguments)}

## Your Original Proposal
- Hypothesis: {proposal.hypothesis}
- Description: {proposal.description}
- Confidence: {proposal.confidence:.0%}

Respond to each argument. Explain why the patch should still be applied,
or acknowledge valid concerns.

Respond with JSON:
{{
  "defense": "Your defense of the patch",
  "concerns_acknowledged": ["list of valid concerns you acknowledge"],
  "concerns_refuted": ["list of concerns you have addressed"]
}}"""

    try:
        defense_text = llm_call(defense_prompt)
        defense_text = defense_text.strip()
        if defense_text.startswith("```"):
            lines = defense_text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            defense_text = "\n".join(lines)

        defense_data = json.loads(defense_text)
        proposer_response = defense_data.get("defense", "No defense provided")
        acknowledged = defense_data.get("concerns_acknowledged", [])
        refuted = defense_data.get("concerns_refuted", [])
    except (json.JSONDecodeError, TypeError):
        proposer_response = "Could not parse defense"
        acknowledged = []
        refuted = []

    # Determine if concerns were adequately addressed
    total_challenges = len(challenge_arguments)
    addressed_count = len(acknowledged) + len(refuted)
    concerns_addressed = addressed_count >= (total_challenges * 0.5) if total_challenges > 0 else True

    remaining = [
        a
        for a in challenge_arguments
        if a not in refuted and not any(ack in a for ack in acknowledged)
    ]

    return ChallengeResponse(
        challenge_arguments=challenge_arguments,
        proposer_response=proposer_response,
        concerns_addressed=concerns_addressed,
        remaining_concerns=remaining,
    )


def vote_on_proposal(
    proposal: PatchProposal,
    challenge: ChallengeResponse | None = None,
    llm_call: Any | None = None,
) -> ReviewResult:
    """Run the 3-reviewer voting process on a proposal.

    Three reviewer perspectives (quality, regression, simplicity) each
    cast a vote. Majority vote determines the outcome.

    Args:
        proposal: The patch proposal to review
        challenge: Optional challenge phase results
        llm_call: LLM callable. Signature: (prompt: str) -> str.

    Returns:
        ReviewResult with all votes and the final decision
    """
    proposal_text = _format_proposal_for_review(proposal, challenge)

    reviewers = [
        ("quality", QUALITY_REVIEWER_PROMPT),
        ("regression", REGRESSION_REVIEWER_PROMPT),
        ("simplicity", SIMPLICITY_REVIEWER_PROMPT),
    ]

    votes: list[ReviewVote] = []

    for reviewer_id, system_prompt in reviewers:
        if llm_call is None:
            # Without LLM, provide stub votes based on confidence
            if proposal.confidence >= 0.7:
                stub_vote = "accept"
                stub_rationale = f"High confidence ({proposal.confidence:.0%})"
            elif proposal.confidence >= 0.4:
                stub_vote = "modify"
                stub_rationale = f"Medium confidence ({proposal.confidence:.0%})"
            else:
                stub_vote = "reject"
                stub_rationale = f"Low confidence ({proposal.confidence:.0%})"

            votes.append(
                ReviewVote(
                    reviewer_id=reviewer_id,
                    vote=stub_vote,
                    rationale=f"Stub vote ({reviewer_id}): {stub_rationale}",
                    concerns=[],
                )
            )
            continue

        review_prompt = f"{system_prompt}\n\n{proposal_text}"
        try:
            response = llm_call(review_prompt)
            vote = _parse_vote_response(response, reviewer_id)
        except Exception as e:
            logger.error("Error getting %s vote: %s", reviewer_id, e)
            vote = ReviewVote(
                reviewer_id=reviewer_id,
                vote="reject",
                rationale=f"Error during review: {e}",
                concerns=[str(e)],
            )
        votes.append(vote)

    # Tally votes: majority wins
    decision = _tally_votes(votes)

    # Build consensus rationale
    consensus_rationale = _build_consensus_rationale(votes, decision)

    return ReviewResult(
        proposal=proposal,
        challenge=challenge,
        votes=votes,
        decision=decision,
        consensus_rationale=consensus_rationale,
    )


def _tally_votes(votes: list[ReviewVote]) -> str:
    """Determine the final decision from reviewer votes.

    Rules:
    - 2/3 or more accept -> "accepted"
    - 2/3 or more reject -> "rejected"
    - Otherwise -> "modified" (mixed signals)

    Args:
        votes: List of reviewer votes

    Returns:
        Decision string: "accepted", "rejected", or "modified"
    """
    if not votes:
        return "rejected"

    accept_count = sum(1 for v in votes if v.vote == "accept")
    reject_count = sum(1 for v in votes if v.vote == "reject")
    total = len(votes)
    threshold = total / 2.0

    if accept_count > threshold:
        return "accepted"
    if reject_count > threshold:
        return "rejected"
    return "modified"


def _build_consensus_rationale(votes: list[ReviewVote], decision: str) -> str:
    """Build a summary rationale from all votes.

    Args:
        votes: Individual reviewer votes
        decision: The final decision

    Returns:
        Human-readable consensus rationale
    """
    parts = [f"Decision: {decision} ({len(votes)} votes)"]

    for v in votes:
        parts.append(f"  [{v.reviewer_id}] {v.vote}: {v.rationale[:100]}")
        if v.concerns:
            for c in v.concerns[:2]:
                parts.append(f"    Concern: {c[:80]}")

    return "\n".join(parts)


def review_result_to_dict(result: ReviewResult) -> dict[str, Any]:
    """Serialize a ReviewResult to a JSON-compatible dict.

    Args:
        result: The review result to serialize

    Returns:
        Dict representation
    """
    return {
        "proposal": {
            "target_file": result.proposal.target_file,
            "hypothesis": result.proposal.hypothesis,
            "description": result.proposal.description,
            "confidence": result.proposal.confidence,
            "risk_assessment": result.proposal.risk_assessment,
            "expected_impact": result.proposal.expected_impact,
        },
        "challenge": {
            "arguments": result.challenge.challenge_arguments,
            "proposer_response": result.challenge.proposer_response,
            "concerns_addressed": result.challenge.concerns_addressed,
            "remaining_concerns": result.challenge.remaining_concerns,
        }
        if result.challenge
        else None,
        "votes": [
            {
                "reviewer_id": v.reviewer_id,
                "vote": v.vote,
                "rationale": v.rationale,
                "concerns": v.concerns,
                "suggested_modifications": v.suggested_modifications,
            }
            for v in result.votes
        ],
        "decision": result.decision,
        "consensus_rationale": result.consensus_rationale,
    }


__all__ = [
    "ReviewVote",
    "ChallengeResponse",
    "ReviewResult",
    "challenge_proposal",
    "vote_on_proposal",
    "review_result_to_dict",
]
