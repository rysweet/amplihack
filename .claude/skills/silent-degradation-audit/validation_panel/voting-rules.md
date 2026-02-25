# Voting Rules and Implementation

## Vote Tallying Logic

Python implementation of 2/3 consensus voting mechanism.

```python
from enum import Enum
from typing import Callable, Dict, List, Any, Tuple


class Vote(Enum):
    """Vote options for validation panel."""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ABSTAIN = "ABSTAIN"


class ValidationResult(Enum):
    """Validation outcomes."""
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"


class ConsensusType(Enum):
    """Strength of consensus."""
    STRONG = "strong"  # AAA or RRR
    WEAK = "weak"      # AAR or ARR with 2/3
    NONE = "none"      # Inconclusive


def tally_votes(votes: List[Dict[str, Any]]) -> Tuple[ValidationResult, ConsensusType, str]:
    """Tally votes from validation panel and determine outcome.

    Args:
        votes: List of vote dictionaries with keys:
            - agent: str (agent name)
            - vote: str (APPROVE, REJECT, or ABSTAIN)
            - justification: str (reason for vote)

    Returns:
        Tuple of (validation_result, consensus_type, recommendation)

    Consensus Rules:
        - 3 APPROVE → VALIDATED (strong)
        - 2 APPROVE, 1 REJECT → VALIDATED (weak)
        - 2 APPROVE, 1 ABSTAIN → VALIDATED (weak)
        - 1 APPROVE, 2 REJECT → REJECTED
        - 0 APPROVE, 3 REJECT → REJECTED (strong)
        - 1 REJECT, 2 ABSTAIN → REJECTED (weak)
        - 1 APPROVE, 2 ABSTAIN → INCONCLUSIVE
        - 0 APPROVE, 0 REJECT, 3 ABSTAIN → INCONCLUSIVE
    """
    if not votes:
        return ValidationResult.INCONCLUSIVE, ConsensusType.NONE, "No votes received"

    approve_count = sum(1 for v in votes if v.get("vote") == Vote.APPROVE.value)
    reject_count = sum(1 for v in votes if v.get("vote") == Vote.REJECT.value)
    abstain_count = sum(1 for v in votes if v.get("vote") == Vote.ABSTAIN.value)

    total_votes = len(votes)

    # Strong consensus: all agree
    if approve_count == total_votes:
        return (
            ValidationResult.VALIDATED,
            ConsensusType.STRONG,
            "Strong consensus: all agents approve"
        )

    if reject_count == total_votes:
        return (
            ValidationResult.REJECTED,
            ConsensusType.STRONG,
            "Strong consensus: all agents reject"
        )

    # 2/3 threshold (excluding abstentions)
    active_votes = total_votes - abstain_count

    if active_votes == 0:
        return (
            ValidationResult.INCONCLUSIVE,
            ConsensusType.NONE,
            "All agents abstained"
        )

    # Need at least 2 votes to reach consensus
    if active_votes < 2:
        return (
            ValidationResult.INCONCLUSIVE,
            ConsensusType.NONE,
            "Insufficient active votes for consensus"
        )

    # Check for 2/3 approval
    if approve_count >= 2:
        if abstain_count > 0:
            return (
                ValidationResult.VALIDATED,
                ConsensusType.WEAK,
                f"Weak consensus: {approve_count} approve, {abstain_count} abstain"
            )
        else:
            return (
                ValidationResult.VALIDATED,
                ConsensusType.WEAK,
                f"Weak consensus: {approve_count} approve, {reject_count} reject"
            )

    # Check for 2/3 rejection
    if reject_count >= 2:
        return (
            ValidationResult.REJECTED,
            ConsensusType.WEAK if abstain_count > 0 else ConsensusType.STRONG,
            f"Rejected: {reject_count} reject, {approve_count} approve"
        )

    # Couldn't reach consensus
    return (
        ValidationResult.INCONCLUSIVE,
        ConsensusType.NONE,
        f"No consensus: {approve_count} approve, {reject_count} reject, {abstain_count} abstain"
    )


def validate_finding(finding: Dict[str, Any], agent_votes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate a finding using validation panel votes.

    Args:
        finding: The finding to validate
        agent_votes: List of votes from validation panel agents

    Returns:
        Dictionary with validation result and details
    """
    result, consensus, recommendation = tally_votes(agent_votes)

    return {
        "finding_id": finding.get("id", "unknown"),
        "validation_result": result.value,
        "consensus_type": consensus.value,
        "votes": agent_votes,
        "recommendation": recommendation,
        "review_required": result == ValidationResult.INCONCLUSIVE,
        "should_fix": result == ValidationResult.VALIDATED,
    }


def batch_validate_findings(
    findings: List[Dict[str, Any]],
    vote_collector: Callable[[Dict[str, Any]], List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """Validate a batch of findings.

    Args:
        findings: List of findings to validate
        vote_collector: Function that collects votes for a finding
            Signature: vote_collector(finding) -> List[Dict[str, Any]]

    Returns:
        List of validation results
    """
    results = []

    for finding in findings:
        try:
            votes = vote_collector(finding)
            result = validate_finding(finding, votes)
            results.append(result)
        except Exception as e:
            results.append({
                "finding_id": finding.get("id", "unknown"),
                "validation_result": ValidationResult.INCONCLUSIVE.value,
                "error": str(e),
                "review_required": True,
            })

    return results


def format_validation_summary(results: List[Dict[str, Any]]) -> str:
    """Format validation results as human-readable summary.

    Args:
        results: List of validation results

    Returns:
        Formatted summary string
    """
    total = len(results)
    validated = sum(1 for r in results if r.get("validation_result") == ValidationResult.VALIDATED.value)
    rejected = sum(1 for r in results if r.get("validation_result") == ValidationResult.REJECTED.value)
    inconclusive = sum(1 for r in results if r.get("validation_result") == ValidationResult.INCONCLUSIVE.value)

    strong_consensus = sum(
        1 for r in results
        if r.get("consensus_type") == ConsensusType.STRONG.value
    )

    lines = [
        "Validation Panel Results",
        "=" * 50,
        f"Total Findings: {total}",
        f"Validated: {validated} ({validated/total*100:.1f}%)",
        f"Rejected: {rejected} ({rejected/total*100:.1f}%)",
        f"Inconclusive: {inconclusive} ({inconclusive/total*100:.1f}%)",
        "",
        f"Strong Consensus: {strong_consensus} ({strong_consensus/total*100:.1f}%)",
        "",
        "Findings requiring fix: " + ", ".join(
            r.get("finding_id", "?")
            for r in results
            if r.get("should_fix", False)
        ) if validated > 0 else "None",
        "",
        "Findings requiring human review: " + ", ".join(
            r.get("finding_id", "?")
            for r in results
            if r.get("review_required", False)
        ) if inconclusive > 0 else "None",
    ]

    return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    # Example finding
    finding = {
        "id": "dep-001",
        "category": "dependency-failures",
        "description": "Exception caught but not logged",
    }

    # Example votes
    votes = [
        {
            "agent": "security",
            "vote": Vote.APPROVE.value,
            "justification": "Creates security blind spot"
        },
        {
            "agent": "architect",
            "vote": Vote.APPROVE.value,
            "justification": "Violates observability principles"
        },
        {
            "agent": "builder",
            "vote": Vote.APPROVE.value,
            "justification": "Simple one-line fix"
        }
    ]

    result = validate_finding(finding, votes)
    print(f"Result: {result['validation_result']}")
    print(f"Consensus: {result['consensus_type']}")
    print(f"Recommendation: {result['recommendation']}")
```

## Vote Pattern Examples

### Pattern Matrix

| Approve | Reject | Abstain | Result       | Consensus | Recommendation       |
| ------- | ------ | ------- | ------------ | --------- | -------------------- |
| 3       | 0      | 0       | VALIDATED    | strong    | Proceed with fix     |
| 2       | 1      | 0       | VALIDATED    | weak      | Proceed with caution |
| 2       | 0      | 1       | VALIDATED    | weak      | Proceed with fix     |
| 1       | 2      | 0       | REJECTED     | weak      | Add to exclusions    |
| 0       | 3      | 0       | REJECTED     | strong    | Clear false positive |
| 0       | 2      | 1       | REJECTED     | weak      | Add to exclusions    |
| 1       | 1      | 1       | INCONCLUSIVE | none      | Human review needed  |
| 1       | 0      | 2       | INCONCLUSIVE | none      | Insufficient votes   |
| 0       | 0      | 3       | INCONCLUSIVE | none      | All abstained        |

## Decision Tree

```
Start
├─ All agents agree?
│  ├─ Yes (AAA) → VALIDATED (strong) ✓
│  └─ Yes (RRR) → REJECTED (strong) ✗
│
├─ 2 or more APPROVE?
│  ├─ Yes (AAR or AAB) → VALIDATED (weak) ✓
│  └─ No → Continue
│
├─ 2 or more REJECT?
│  ├─ Yes (ARR or RRB) → REJECTED (weak) ✗
│  └─ No → INCONCLUSIVE ⚠
│
└─ Otherwise → INCONCLUSIVE ⚠
```

## Tie-Breaking Rules

**Note**: With 3 agents, true ties (1-1-1) are rare but possible.

When votes are tied (1 approve, 1 reject, 1 abstain):

1. Result: **INCONCLUSIVE**
2. Action: Flag for human review
3. Reasoning: Need more information or fourth opinion

Alternative approach (not recommended):

- Use severity as tie-breaker (high severity → approve, low severity → reject)
- Risk: Could override agent judgment

## Abstention Guidelines

Agents should abstain when:

1. **Insufficient Context**
   - Code snippet too small
   - Missing business logic context
   - External dependencies not documented

2. **Outside Expertise**
   - Security agent: Non-security issue
   - Architect agent: Low-level implementation detail
   - Builder agent: High-level architecture decision

3. **Conflicting Information**
   - Finding description contradicts code
   - Multiple interpretations possible
   - Unclear what "correct" behavior should be

**Important**: Abstentions should be rare (< 10% of votes). High abstention rate indicates:

- Poor finding descriptions
- Insufficient context provided
- Agent prompts need refinement

## Metrics and Monitoring

Track these metrics over time:

```python
def calculate_panel_metrics(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate validation panel effectiveness metrics."""
    total = len(results)
    if total == 0:
        return {}

    return {
        "validation_rate": sum(
            1 for r in results
            if r["validation_result"] == "VALIDATED"
        ) / total,

        "rejection_rate": sum(
            1 for r in results
            if r["validation_result"] == "REJECTED"
        ) / total,

        "inconclusive_rate": sum(
            1 for r in results
            if r["validation_result"] == "INCONCLUSIVE"
        ) / total,

        "strong_consensus_rate": sum(
            1 for r in results
            if r["consensus_type"] == "strong"
        ) / total,

        "abstention_rate": sum(
            sum(1 for v in r["votes"] if v["vote"] == "ABSTAIN")
            for r in results
        ) / (total * 3),  # 3 agents per finding
    }
```

## Quality Thresholds

**Healthy validation panel:**

- Validation rate: 60-80%
- Rejection rate: 15-30%
- Inconclusive rate: < 10%
- Strong consensus rate: > 50%
- Abstention rate: < 10%

**Warning signs:**

- Validation rate > 95% (rubber stamping)
- Validation rate < 40% (too strict)
- Inconclusive rate > 20% (poor context)
- Abstention rate > 20% (agent tuning needed)
