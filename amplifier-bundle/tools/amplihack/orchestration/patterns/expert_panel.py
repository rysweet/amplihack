"""Expert Panel Review orchestrator.

Implements expert panel review pattern where multiple expert agents independently
review a solution, each casting a vote with detailed rationale, and votes are
aggregated for a final decision. Provides Byzantine robustness through quorum-based
decision-making.

Based on: Specs/expert-panel-pattern.md
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ..execution import run_parallel
from ..session import OrchestratorSession


class VoteChoice(Enum):
    """Vote options for expert review."""

    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class ExpertReview:
    """Single expert's review with vote."""

    # Expert identity
    expert_id: str
    domain: str

    # Analysis
    analysis: str
    strengths: list[str]
    weaknesses: list[str]

    # Scoring (domain-specific)
    domain_scores: dict[str, float]

    # Vote
    vote: VoteChoice
    confidence: float
    vote_rationale: str

    # Metadata
    review_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    review_duration_seconds: float = 0.0


@dataclass
class AggregatedDecision:
    """Result of vote aggregation."""

    # Decision
    decision: VoteChoice
    confidence: float

    # Vote breakdown
    total_votes: int
    approve_votes: int
    reject_votes: int
    abstain_votes: int

    # Consensus strength
    consensus_type: str
    agreement_percentage: float

    # Dissent handling
    dissenting_opinions: list[ExpertReview]

    # Metadata
    aggregation_method: str
    quorum_met: bool


@dataclass
class DissentReport:
    """Formatted dissent report."""

    decision: VoteChoice
    majority_count: int
    dissent_count: int
    majority_experts: list[str]
    dissent_experts: list[str]
    dissent_rationales: list[str]
    concerns_raised: list[str]


# Default expert profiles
DEFAULT_EXPERTS = [
    {
        "domain": "security",
        "focus": "vulnerabilities, attack vectors, data protection, security best practices",
    },
    {
        "domain": "performance",
        "focus": "speed, scalability, resource efficiency, latency, throughput",
    },
    {
        "domain": "simplicity",
        "focus": "minimal complexity, ruthless simplification, maintainability, clarity",
    },
]


def aggregate_simple_majority(reviews: list[ExpertReview], quorum: int = 3) -> AggregatedDecision:
    """Aggregate votes using simple majority.

    Args:
        reviews: List of expert reviews with votes
        quorum: Minimum number of non-abstain votes required

    Returns:
        AggregatedDecision with majority vote result
    """
    # Count votes
    approve_votes = sum(1 for r in reviews if r.vote == VoteChoice.APPROVE)
    reject_votes = sum(1 for r in reviews if r.vote == VoteChoice.REJECT)
    abstain_votes = sum(1 for r in reviews if r.vote == VoteChoice.ABSTAIN)
    total_votes = len(reviews)
    non_abstain_votes = approve_votes + reject_votes

    # Check quorum
    quorum_met = non_abstain_votes >= quorum

    # Determine decision
    if approve_votes > reject_votes:
        decision = VoteChoice.APPROVE
        majority_count = approve_votes
        dissenting = [r for r in reviews if r.vote == VoteChoice.REJECT]
    elif reject_votes > approve_votes:
        decision = VoteChoice.REJECT
        majority_count = reject_votes
        dissenting = [r for r in reviews if r.vote == VoteChoice.APPROVE]
    else:
        # Tie - default to reject (conservative)
        decision = VoteChoice.REJECT
        majority_count = reject_votes
        dissenting = [r for r in reviews if r.vote == VoteChoice.APPROVE]

    # Calculate agreement percentage
    if non_abstain_votes > 0:
        agreement_percentage = (majority_count / non_abstain_votes) * 100
    else:
        agreement_percentage = 0.0

    # Determine consensus type
    if agreement_percentage == 100:
        consensus_type = "unanimous"
    elif agreement_percentage >= 75:
        consensus_type = "strong_majority"
    elif agreement_percentage > 50:
        consensus_type = "simple_majority"
    else:
        consensus_type = "split"

    # Calculate aggregated confidence
    if decision == VoteChoice.APPROVE:
        relevant_reviews = [r for r in reviews if r.vote == VoteChoice.APPROVE]
    else:
        relevant_reviews = [r for r in reviews if r.vote == VoteChoice.REJECT]

    if relevant_reviews:
        avg_confidence = sum(r.confidence for r in relevant_reviews) / len(relevant_reviews)
    else:
        avg_confidence = 0.5  # Default moderate confidence

    return AggregatedDecision(
        decision=decision,
        confidence=avg_confidence,
        total_votes=total_votes,
        approve_votes=approve_votes,
        reject_votes=reject_votes,
        abstain_votes=abstain_votes,
        consensus_type=consensus_type,
        agreement_percentage=agreement_percentage,
        dissenting_opinions=dissenting,
        aggregation_method="simple_majority",
        quorum_met=quorum_met,
    )


def aggregate_weighted(reviews: list[ExpertReview], quorum: int = 3) -> AggregatedDecision:
    """Aggregate votes weighted by confidence.

    Args:
        reviews: List of expert reviews with votes
        quorum: Minimum number of non-abstain votes required

    Returns:
        AggregatedDecision with confidence-weighted result
    """
    # Count votes
    total_votes = len(reviews)
    approve_votes = sum(1 for r in reviews if r.vote == VoteChoice.APPROVE)
    reject_votes = sum(1 for r in reviews if r.vote == VoteChoice.REJECT)
    abstain_votes = sum(1 for r in reviews if r.vote == VoteChoice.ABSTAIN)
    non_abstain_votes = approve_votes + reject_votes

    # Check quorum
    quorum_met = non_abstain_votes >= quorum

    # Calculate weighted scores
    approve_weight = sum(r.confidence for r in reviews if r.vote == VoteChoice.APPROVE)
    reject_weight = sum(r.confidence for r in reviews if r.vote == VoteChoice.REJECT)

    # Determine decision
    if approve_weight > reject_weight:
        decision = VoteChoice.APPROVE
        majority_weight = approve_weight
        dissenting = [r for r in reviews if r.vote == VoteChoice.REJECT]
    elif reject_weight > approve_weight:
        decision = VoteChoice.REJECT
        majority_weight = reject_weight
        dissenting = [r for r in reviews if r.vote == VoteChoice.APPROVE]
    else:
        # Tie - default to reject (conservative)
        decision = VoteChoice.REJECT
        majority_weight = reject_weight
        dissenting = [r for r in reviews if r.vote == VoteChoice.APPROVE]

    # Calculate agreement percentage based on weight
    total_weight = approve_weight + reject_weight
    if total_weight > 0:
        agreement_percentage = (majority_weight / total_weight) * 100
    else:
        agreement_percentage = 0.0

    # Determine consensus type
    if agreement_percentage == 100:
        consensus_type = "unanimous"
    elif agreement_percentage >= 75:
        consensus_type = "strong_majority"
    elif agreement_percentage > 50:
        consensus_type = "simple_majority"
    else:
        consensus_type = "split"

    # Use majority weight as confidence
    confidence = majority_weight / max(len([r for r in reviews if r.vote != VoteChoice.ABSTAIN]), 1)

    return AggregatedDecision(
        decision=decision,
        confidence=min(confidence, 1.0),  # Cap at 1.0
        total_votes=total_votes,
        approve_votes=approve_votes,
        reject_votes=reject_votes,
        abstain_votes=abstain_votes,
        consensus_type=consensus_type,
        agreement_percentage=agreement_percentage,
        dissenting_opinions=dissenting,
        aggregation_method="weighted",
        quorum_met=quorum_met,
    )


def aggregate_unanimous(reviews: list[ExpertReview], quorum: int = 3) -> AggregatedDecision:
    """Aggregate votes requiring unanimous agreement.

    Args:
        reviews: List of expert reviews with votes
        quorum: Minimum number of non-abstain votes required

    Returns:
        AggregatedDecision with unanimous requirement
    """
    # Count votes
    total_votes = len(reviews)
    approve_votes = sum(1 for r in reviews if r.vote == VoteChoice.APPROVE)
    reject_votes = sum(1 for r in reviews if r.vote == VoteChoice.REJECT)
    abstain_votes = sum(1 for r in reviews if r.vote == VoteChoice.ABSTAIN)
    non_abstain_votes = approve_votes + reject_votes

    # Check quorum
    quorum_met = non_abstain_votes >= quorum

    # Get non-abstain reviews
    non_abstain_reviews = [r for r in reviews if r.vote != VoteChoice.ABSTAIN]

    # Check for unanimous approval
    if all(r.vote == VoteChoice.APPROVE for r in non_abstain_reviews) and non_abstain_reviews:
        decision = VoteChoice.APPROVE
        consensus_type = "unanimous"
        agreement_percentage = 100.0
        dissenting = []
        # Average confidence of all approvals
        avg_confidence = sum(r.confidence for r in non_abstain_reviews) / len(non_abstain_reviews)
    else:
        # Any dissent or all abstain -> reject
        decision = VoteChoice.REJECT
        consensus_type = "not_unanimous" if approve_votes > 0 else "unanimous_rejection"
        if reject_votes == non_abstain_votes and non_abstain_votes > 0:
            agreement_percentage = 100.0
            dissenting = []
        else:
            # Mixed or mostly reject
            agreement_percentage = (
                (reject_votes / non_abstain_votes) * 100 if non_abstain_votes > 0 else 0.0
            )
            dissenting = [r for r in reviews if r.vote == VoteChoice.APPROVE]

        # Average confidence of rejects if any, else use moderate
        reject_reviews = [r for r in reviews if r.vote == VoteChoice.REJECT]
        if reject_reviews:
            avg_confidence = sum(r.confidence for r in reject_reviews) / len(reject_reviews)
        else:
            avg_confidence = 0.5

    return AggregatedDecision(
        decision=decision,
        confidence=avg_confidence,
        total_votes=total_votes,
        approve_votes=approve_votes,
        reject_votes=reject_votes,
        abstain_votes=abstain_votes,
        consensus_type=consensus_type,
        agreement_percentage=agreement_percentage,
        dissenting_opinions=dissenting,
        aggregation_method="unanimous",
        quorum_met=quorum_met,
    )


def generate_dissent_report(decision: AggregatedDecision) -> DissentReport | None:
    """Generate formatted dissent report.

    Args:
        decision: Aggregated decision with dissenting opinions

    Returns:
        DissentReport if there are dissenting opinions, None otherwise

    Note:
        majority_experts field is empty as only dissenting opinions are passed.
        Caller should track all reviews separately if majority experts needed.
    """
    if not decision.dissenting_opinions:
        return None

    # Determine majority/dissent counts
    if decision.decision == VoteChoice.APPROVE:
        majority_count = decision.approve_votes
        dissent_count = decision.reject_votes
    else:
        majority_count = decision.reject_votes
        dissent_count = decision.approve_votes

    # Extract dissenting experts and rationales
    dissent_experts = [r.expert_id for r in decision.dissenting_opinions]
    dissent_rationales = [r.vote_rationale for r in decision.dissenting_opinions]

    # Extract concerns from dissenting reviews
    concerns_raised = []
    for review in decision.dissenting_opinions:
        concerns_raised.extend(review.weaknesses)

    return DissentReport(
        decision=decision.decision,
        majority_count=majority_count,
        dissent_count=dissent_count,
        majority_experts=[],
        dissent_experts=dissent_experts,
        dissent_rationales=dissent_rationales,
        concerns_raised=list(set(concerns_raised)),
    )


def run_expert_panel(
    solution: str,
    experts: list[dict[str, str]] | None = None,
    aggregation_method: str = "simple_majority",
    quorum: int = 3,
    model: str | None = None,
    working_dir: Path | None = None,
    timeout: int | None = None,
) -> dict[str, Any]:
    """Execute Expert Panel Review pattern.

    Multiple expert agents independently review a solution, each casting a vote
    with detailed rationale. Votes are aggregated for a final decision using
    the specified aggregation method.

    Steps:
    1. Initialize expert panel (default: security, performance, simplicity)
    2. Each expert performs independent review in parallel
    3. Each expert casts vote with rationale
    4. Aggregate votes using specified method
    5. Generate dissent report if split decision
    6. Return aggregated decision

    Args:
        solution: Solution to review (implementation, design proposal, etc.)
        experts: List of expert definitions with 'domain' and 'focus' keys
                 (default: security, performance, simplicity experts)
        aggregation_method: Method to aggregate votes:
                          - "simple_majority" (default): Count votes, majority wins
                          - "weighted": Weight votes by confidence
                          - "unanimous": Require all experts to agree
        quorum: Minimum number of non-abstain votes required (default: 3)
        model: Claude model to use for all experts (default: None = CLI default)
        working_dir: Working directory for processes (default: current dir)
        timeout: Timeout per expert review in seconds (default: None = no timeout)

    Returns:
        Dict containing:
        - reviews: List[ExpertReview] - all expert reviews
        - decision: AggregatedDecision - final aggregated decision
        - dissent_report: Optional[DissentReport] - dissent report if applicable
        - session_id: str - session identifier for logs
        - success: bool - whether operation completed successfully

    Example:
        >>> result = run_expert_panel(
        ...     solution="# Python code to review\\ndef hash_password(pwd): ...",
        ...     aggregation_method="simple_majority",
        ...     quorum=3
        ... )
        >>> print(f"Decision: {result['decision'].decision.value}")
        >>> print(f"Confidence: {result['decision'].confidence:.2f}")
    """
    # Setup
    working_dir = working_dir or Path.cwd()
    experts = experts or DEFAULT_EXPERTS

    # Validate aggregation method
    valid_methods = ["simple_majority", "weighted", "unanimous"]
    if aggregation_method not in valid_methods:
        raise ValueError(
            f"Invalid aggregation_method '{aggregation_method}'. Must be one of: {valid_methods}"
        )

    # Create session
    session = OrchestratorSession(
        pattern_name="expert-panel",
        working_dir=working_dir,
        model=model,
    )

    session.log(f"Starting Expert Panel Review with {len(experts)} experts")
    session.log(f"Aggregation method: {aggregation_method}")
    session.log(f"Quorum: {quorum}")

    # Step 1: Initialize expert panel
    session.log("Step 1: Initializing expert panel")
    session.log(f"Experts: {', '.join(e['domain'] for e in experts)}")

    # Step 2: Parallel expert reviews
    session.log("Step 2: Conducting parallel expert reviews")

    processes = []
    for i, expert_def in enumerate(experts):
        domain = expert_def["domain"]
        focus = expert_def["focus"]

        # Build expert review prompt
        review_prompt = f"""You are an expert reviewer participating in an Expert Panel Review.

SOLUTION TO REVIEW:
{solution}

YOUR EXPERTISE: {domain.upper()}
FOCUS AREAS: {focus}

Your task is to perform an independent expert review from your domain perspective
and cast a vote on this solution.

REVIEW PROCESS:

1. **Detailed Analysis**
   - Analyze the solution according to your domain expertise
   - Identify specific strengths and weaknesses
   - Look for domain-specific issues or best practices

2. **Domain Scoring**
   - Rate key aspects of your domain (0.0 = poor, 1.0 = excellent)
   - Be specific about what you're measuring

3. **Vote Decision**
   - APPROVE: Solution meets standards in your domain
   - REJECT: Solution has significant issues in your domain
   - ABSTAIN: Insufficient information to judge from your domain

4. **Vote Rationale**
   - Explain WHY you voted this way
   - Reference specific findings from your analysis
   - Be clear about deal-breakers or critical strengths

IMPORTANT:
- You are ONE expert among multiple (total: {len(experts)})
- Your review is INDEPENDENT (do not consider other experts)
- Focus ONLY on your domain of expertise
- Be intellectually honest and evidence-based
- Use your confidence score to express uncertainty (0.0 - 1.0)

FORMAT YOUR RESPONSE EXACTLY AS:

## Analysis
[Your detailed analysis from {domain} perspective]

## Strengths
- [Strength 1]
- [Strength 2]
- [Strength 3]

## Weaknesses
- [Weakness 1]
- [Weakness 2]

## Domain Scores
[Provide 2-4 scores for key aspects, e.g.:]
- aspect_name_1: 0.8
- aspect_name_2: 0.6
- aspect_name_3: 0.9

## Vote
[APPROVE or REJECT or ABSTAIN]

## Confidence
[Number between 0.0 and 1.0, e.g. 0.85]

## Vote Rationale
[Clear explanation of why you voted this way, referencing your analysis]
"""

        process = session.create_process(
            prompt=review_prompt,
            process_id=f"expert_{domain}",
            timeout=timeout,
        )
        processes.append((domain, expert_def, process))

    # Execute all expert reviews in parallel
    session.log(f"Executing {len(experts)} expert reviews in parallel...")
    review_results = run_parallel([p[2] for p in processes])

    # Step 3: Parse expert reviews
    session.log("Step 3: Parsing expert reviews and votes")

    expert_reviews = []
    for (domain, expert_def, _), result in zip(processes, review_results, strict=False):
        if result.exit_code != 0:
            session.log(f"WARNING: Expert {domain} review failed", level="WARNING")
            continue

        # Parse the expert output
        output = result.output
        try:
            # Extract sections
            analysis = _extract_section(output, "Analysis")
            strengths = _extract_list_items(output, "Strengths")
            weaknesses = _extract_list_items(output, "Weaknesses")
            domain_scores = _extract_scores(output, "Domain Scores")
            vote_str = _extract_section(output, "Vote").strip().upper()
            confidence_str = _extract_section(output, "Confidence").strip()
            vote_rationale = _extract_section(output, "Vote Rationale")

            # Parse vote
            vote = (
                VoteChoice[vote_str]
                if vote_str in ["APPROVE", "REJECT", "ABSTAIN"]
                else VoteChoice.ABSTAIN
            )

            # Parse confidence
            try:
                confidence = float(confidence_str)
                confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
            except (ValueError, TypeError):
                confidence = 0.5  # Default moderate confidence

            # Create ExpertReview
            review = ExpertReview(
                expert_id=f"{domain}-expert",
                domain=domain,
                analysis=analysis,
                strengths=strengths,
                weaknesses=weaknesses,
                domain_scores=domain_scores,
                vote=vote,
                confidence=confidence,
                vote_rationale=vote_rationale,
                review_duration_seconds=result.duration,
            )
            expert_reviews.append(review)

            session.log(f"Expert {domain}: {vote.value.upper()} (confidence: {confidence:.2f})")

        except Exception as e:
            session.log(f"ERROR: Failed to parse {domain} expert output: {e}", level="ERROR")
            continue

    # Check if we have enough reviews
    if len(expert_reviews) == 0:
        session.log("ERROR: All expert reviews failed", level="ERROR")
        return {
            "reviews": [],
            "decision": None,
            "dissent_report": None,
            "session_id": session.session_id,
            "success": False,
        }

    session.log(f"Successfully parsed {len(expert_reviews)}/{len(experts)} expert reviews")

    # Step 4: Aggregate votes
    session.log(f"Step 4: Aggregating votes using {aggregation_method}")

    if aggregation_method == "simple_majority":
        decision = aggregate_simple_majority(expert_reviews, quorum)
    elif aggregation_method == "weighted":
        decision = aggregate_weighted(expert_reviews, quorum)
    elif aggregation_method == "unanimous":
        decision = aggregate_unanimous(expert_reviews, quorum)
    else:
        session.log(f"ERROR: Unknown aggregation method: {aggregation_method}", level="ERROR")
        return {
            "reviews": expert_reviews,
            "decision": None,
            "dissent_report": None,
            "session_id": session.session_id,
            "success": False,
        }

    session.log(
        f"Decision: {decision.decision.value.upper()} "
        f"({decision.consensus_type}, {decision.agreement_percentage:.1f}% agreement)"
    )
    session.log(
        f"Vote breakdown: {decision.approve_votes} approve, "
        f"{decision.reject_votes} reject, {decision.abstain_votes} abstain"
    )
    session.log(f"Quorum met: {decision.quorum_met}")

    # Step 5: Generate dissent report if applicable
    dissent_report = None
    if decision.dissenting_opinions:
        session.log("Step 5: Generating dissent report")
        dissent_report = generate_dissent_report(decision)
        session.log(f"Dissent report: {len(decision.dissenting_opinions)} dissenting opinions")

    session.log(f"Session logs: {session.log_dir}")

    return {
        "reviews": expert_reviews,
        "decision": decision,
        "dissent_report": dissent_report,
        "session_id": session.session_id,
        "success": decision.quorum_met,
    }


# Helper functions for parsing expert output


def _extract_section(text: str, section_name: str) -> str:
    """Extract content from a markdown section."""
    pattern = rf"##\s+{section_name}\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def _extract_list_items(text: str, section_name: str) -> list[str]:
    """Extract bullet list items from a section."""
    section_text = _extract_section(text, section_name)
    if not section_text:
        return []

    items = re.findall(r"^[-*]\s+(.+)$", section_text, re.MULTILINE)
    return [item.strip() for item in items]


def _extract_scores(text: str, section_name: str) -> dict[str, float]:
    """Extract domain scores from a section."""
    section_text = _extract_section(text, section_name)
    if not section_text:
        return {}

    scores = {}
    pattern = r"[-*]?\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([\d.]+)"
    matches = re.findall(pattern, section_text)

    for name, value in matches:
        try:
            scores[name] = float(value)
        except ValueError:
            continue

    return scores
