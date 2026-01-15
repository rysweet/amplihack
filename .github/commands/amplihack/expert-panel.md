---
name: amplihack:expert-panel
version: 1.0.0
description: Expert panel review with voting and consensus decision-making
triggers:
- need multiple expert reviews
- code review approval gate
- design review board
- release decision
invokes:
- type: subagent
  path: .claude/agents/amplihack/security.md
- type: subagent
  path: .claude/agents/amplihack/optimizer.md
- type: subagent
  path: .claude/agents/amplihack/specialized/philosophy-guardian.md
philosophy:
- principle: Analysis First
  application: Multiple independent expert analyses before decision
- principle: Trust in Emergence
  application: Best decisions emerge from diverse expert perspectives
dependencies:
  optional:
  - .claude/tools/amplihack/orchestration/patterns/expert_panel.py
examples:
- /amplihack:expert-panel Review authentication implementation
- /amplihack:expert-panel --unanimous Security-critical code review
---

# Expert Panel Review Command

Execute the Expert Panel Review orchestration pattern where multiple expert agents independently review a solution, each casting a vote with detailed rationale, and votes are aggregated for a final decision.

## Pattern Overview

**Expert Panel Review** provides Byzantine-robust decision-making through:

1. **Parallel Expert Reviews**: Multiple domain experts (security, performance, simplicity) independently analyze solution
2. **Individual Voting**: Each expert casts APPROVE/REJECT/ABSTAIN vote with confidence level
3. **Aggregated Decision**: Votes combined using configurable aggregation method (simple majority, weighted, unanimous)
4. **Dissent Reporting**: Minority opinions preserved and highlighted for transparency

## When to Use

Use Expert Panel Review when you need:

- **Multiple Expert Judgments**: Diverse expertise to evaluate solution quality
- **Quantifiable Decision**: Clear vote-based decision rather than subjective synthesis
- **Byzantine Robustness**: Protection against individual expert bias/hallucination
- **Code Review Approvals**: Multiple reviewers for merge decisions
- **Design Review Boards**: Multi-stakeholder approval gates
- **Quality Gates**: Critical checkpoints requiring consensus
- **Release Decisions**: Go/no-go votes from multiple perspectives

## Basic Usage

```python
from .claude.tools.amplihack.orchestration.patterns import run_expert_panel

# Review a code implementation
result = run_expert_panel(
    solution="def hash_password(pwd): ...",
    aggregation_method="simple_majority",
    quorum=3
)

print(f"Decision: {result['decision'].decision.value}.md"
print(f"Confidence: {result['decision'].confidence:.2f}.md"
print(f"Votes: {result['decision'].approve_votes} approve, {result['decision'].reject_votes} reject.md"
```

## Configuration Options

### Default Experts (3 experts)

```python
# Default panel covers essential domains
result = run_expert_panel(
    solution=code_to_review,
    aggregation_method="simple_majority",
    quorum=3
)
```

Default experts:

- **Security**: Vulnerabilities, attack vectors, security best practices
- **Performance**: Speed, scalability, resource efficiency
- **Simplicity**: Minimal complexity, maintainability, clarity

### Custom Experts

```python
# Define custom expert panel
custom_experts = [
    {"domain": "security", "focus": "threat modeling, input validation"},
    {"domain": "api_design", "focus": "REST API design, endpoint structure"},
    {"domain": "data_modeling", "focus": "schema design, data validation"},
    {"domain": "compliance", "focus": "regulatory requirements, audit trails"},
    {"domain": "ux", "focus": "user experience, API usability"},
]

result = run_expert_panel(
    solution=api_implementation,
    experts=custom_experts,
    aggregation_method="simple_majority",
    quorum=3
)
```

### Aggregation Methods

**Simple Majority (Default)**

```python
# Count votes, majority wins
result = run_expert_panel(
    solution=code,
    aggregation_method="simple_majority",
    quorum=3
)
# 2 approve + 1 reject = APPROVE
```

**Weighted by Confidence**

```python
# Weight votes by expert confidence scores
result = run_expert_panel(
    solution=code,
    aggregation_method="weighted",
    quorum=3
)
# High-confidence votes carry more weight
```

**Unanimous**

```python
# Require all experts to agree
result = run_expert_panel(
    solution=critical_code,
    aggregation_method="unanimous",
    quorum=3
)
# Any dissent = REJECT (conservative)
```

### Quorum Requirements

```python
# Set minimum non-abstain votes required
result = run_expert_panel(
    solution=code,
    aggregation_method="simple_majority",
    quorum=3  # Need at least 3 non-abstain votes
)

# Abstentions don't count toward quorum
# If 2 abstain, quorum=3 not met (even if 1 approves)
```

## Result Structure

```python
result = {
    "reviews": [ExpertReview, ...],  # All expert reviews
    "decision": AggregatedDecision,   # Final decision
    "dissent_report": DissentReport,  # If split decision
    "session_id": "expert-panel-20251020-123456",
    "success": True  # Quorum met
}

# Access decision details
decision = result["decision"]
print(f"Decision: {decision.decision.value}.md"  # APPROVE/REJECT
print(f"Confidence: {decision.confidence:.2f}.md"
print(f"Consensus: {decision.consensus_type}.md"  # unanimous/strong_majority/simple_majority/split
print(f"Votes: {decision.approve_votes}A / {decision.reject_votes}R / {decision.abstain_votes}Ab.md"

# Access individual reviews
for review in result["reviews"]:
    print(f"{review.domain} Expert: {review.vote.value} (confidence: {review.confidence:.2f}).md"
    print(f"  Rationale: {review.vote_rationale}.md"
    print(f"  Strengths: {review.strengths}.md"
    print(f"  Weaknesses: {review.weaknesses}.md"

# Handle dissent
if result["dissent_report"]:
    report = result["dissent_report"]
    print(f"Dissenting experts: {report.dissent_experts}.md"
    print(f"Concerns raised: {report.concerns_raised}.md"
```

## Integration with N-Version

Combine Expert Panel with N-Version Programming for ultimate robustness:

```python
from .claude.tools.amplihack.orchestration.patterns import run_n_version, run_expert_panel

# Step 1: Generate 3 implementations
n_version_result = run_n_version(
    task_prompt="Implement password hashing with bcrypt",
    n=3
)

# Step 2: Expert panel reviews each implementation
panel_results = []
for i, version_result in enumerate(n_version_result["versions"]):
    if version_result.exit_code == 0:
        panel_result = run_expert_panel(
            solution=version_result.output,
            aggregation_method="simple_majority",
            quorum=3
        )
        panel_results.append({
            "version": i + 1,
            "decision": panel_result["decision"],
            "panel_result": panel_result
        })

# Step 3: Select version with strongest approval
best_version = max(
    panel_results,
    key=lambda x: (
        x["decision"].approve_votes,
        x["decision"].confidence
    )
)

print(f"Selected version {best_version['version']} with {best_version['decision'].approve_votes} approvals.md"
```

## Common Patterns

### Code Review Gate

```python
def code_review_gate(pr_code: str) -> bool:
    """Gate PR merge on expert panel approval."""
    result = run_expert_panel(
        solution=pr_code,
        aggregation_method="simple_majority",
        quorum=3
    )

    if not result["success"]:
        print("Quorum not met - request more reviews.md"
        return False

    if result["decision"].decision == VoteChoice.APPROVE:
        print(f"PR approved ({result['decision'].consensus_type}).md"
        return True
    else:
        print("PR rejected - review feedback:.md"
        for review in result["reviews"]:
            if review.vote == VoteChoice.REJECT:
                print(f"  {review.domain}: {review.vote_rationale}.md"
        return False
```

### Security Audit

```python
# Security-critical code requires unanimous approval
security_experts = [
    {"domain": "authentication", "focus": "auth mechanisms, session management"},
    {"domain": "authorization", "focus": "access control, permissions"},
    {"domain": "cryptography", "focus": "encryption, key management"},
    {"domain": "input_validation", "focus": "injection attacks, sanitization"},
]

result = run_expert_panel(
    solution=security_critical_code,
    experts=security_experts,
    aggregation_method="unanimous",  # ALL must approve
    quorum=4
)

if result["decision"].decision == VoteChoice.APPROVE:
    print("Security audit passed - all experts approved.md"
else:
    print("Security concerns found - deployment blocked.md"
```

### Design Review Board

```python
# Multi-stakeholder design approval
stakeholder_experts = [
    {"domain": "architecture", "focus": "system design, scalability"},
    {"domain": "security", "focus": "threat modeling"},
    {"domain": "operations", "focus": "deployment, monitoring"},
    {"domain": "product", "focus": "user needs, requirements"},
    {"domain": "compliance", "focus": "regulatory requirements"},
]

result = run_expert_panel(
    solution=design_proposal,
    experts=stakeholder_experts,
    aggregation_method="weighted",  # Weight by confidence
    quorum=4  # At least 4 must vote
)

# Generate report
print(f"Design Review Decision: {result['decision'].decision.value}.md"
print(f"Consensus: {result['decision'].consensus_type}.md"

if result["dissent_report"]:
    print("\nDissenting Opinions:.md"
    for expert, rationale in zip(
        result["dissent_report"].dissent_experts,
        result["dissent_report"].dissent_rationales
    ):
        print(f"  {expert}: {rationale}.md"
```

## Pattern Comparison

### Expert Panel vs N-Version

- **N-Version**: Creates diversity in SOLUTIONS (multiple implementations)
- **Expert Panel**: Creates diversity in EVALUATION (multiple reviewers)
- **Use Together**: N-Version generates alternatives, Expert Panel selects best

### Expert Panel vs Debate

- **Debate**: Interactive discussion, facilitator synthesizes
- **Expert Panel**: Independent reviews, mechanical vote aggregation
- **When to Use Debate**: Need to explore trade-offs through discussion
- **When to Use Panel**: Need quantifiable decision without groupthink

## Success Metrics

Track effectiveness:

```python
# Track decision quality
panel_decisions = []

result = run_expert_panel(solution, ...)
panel_decisions.append({
    "decision": result["decision"].decision.value,
    "consensus": result["decision"].consensus_type,
    "confidence": result["decision"].confidence
})

# Analyze patterns
unanimous_rate = sum(1 for d in panel_decisions if d["consensus"] == "unanimous.md" / len(panel_decisions)
print(f"Unanimous rate: {unanimous_rate:.1%}.md"  # Target: 70-80%
```

## Advanced Usage

### Conditional Escalation

```python
# Start with simple majority, escalate to unanimous if split
result = run_expert_panel(solution, aggregation_method="simple_majority", quorum=3)

if result["decision"].consensus_type == "split":
    print("Split decision - escalating to larger panel with unanimous requirement.md"

    extended_experts = [
        # Original 3 plus 2 more
        *DEFAULT_EXPERTS,
        {"domain": "reliability", "focus": "failure modes, error handling"},
        {"domain": "maintainability", "focus": "code clarity, documentation"},
    ]

    result = run_expert_panel(
        solution,
        experts=extended_experts,
        aggregation_method="unanimous",
        quorum=5
    )
```

### Time-Bounded Reviews

```python
# Set timeout per expert review
result = run_expert_panel(
    solution=code,
    aggregation_method="simple_majority",
    quorum=3,
    timeout=120  # 2 minutes per expert
)
```

## Implementation Notes

- **Parallel Execution**: All experts review simultaneously
- **Independence**: Experts don't see each other's reviews
- **Confidence Scores**: Experts express uncertainty (0.0 - 1.0)
- **Abstentions**: Experts can abstain if lacking information
- **Quorum Rules**: Abstentions don't count toward quorum
- **Conservative Ties**: Ties default to REJECT

## Session Logs

All expert reviews and decisions logged:

```python
result = run_expert_panel(...)
print(f"Session logs: {result['session_id']}.md"
# Logs location: .claude/runtime/logs/<session_id>/
```

## Error Handling

```python
result = run_expert_panel(...)

if not result["success"]:
    if len(result["reviews"]) == 0:
        print("ERROR: All expert reviews failed.md"
    elif not result["decision"].quorum_met:
        print(f"ERROR: Quorum not met ({len(result['reviews'])} votes, need {quorum}).md"
else:
    # Process successful result
    pass
```

---

**Pattern**: Expert Panel Review
**Status**: Production Ready
**Version**: 1.0
**Related**: N-Version Programming, Multi-Agent Debate