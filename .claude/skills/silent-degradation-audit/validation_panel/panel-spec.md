# Validation Panel Specification

## Purpose

Multi-agent validation panel ensures findings are legitimate before applying fixes. Uses 2/3 consensus mechanism to prevent false positives and unnecessary changes.

## Panel Composition

Three specialized agents vote on each finding:

1. **Security Agent** - Assesses security implications
2. **Architect Agent** - Evaluates design and architectural impact
3. **Builder Agent** - Considers implementation complexity and cost

## Voting Process

### Step 1: Present Finding

Each finding is presented to all three agents simultaneously with:

- Finding details (file, line, description, category)
- Code context (surrounding lines)
- Impact assessment from category agent
- Proposed fix recommendation

### Step 2: Independent Evaluation

Each agent evaluates the finding independently based on their specialty:

**Security Agent Focus:**

- Does this finding represent a real security risk?
- Could this lead to data exposure or unauthorized access?
- Is the impact correctly assessed?

**Architect Agent Focus:**

- Is this finding consistent with system architecture?
- Does fixing it improve or harm design quality?
- Are there broader architectural implications?

**Builder Agent Focus:**

- Is this finding actionable (can be fixed)?
- What is the implementation complexity?
- Are there dependencies or side effects?

### Step 3: Vote Casting

Each agent casts one vote:

- **APPROVE**: Finding is valid, should be fixed
- **REJECT**: Finding is false positive or not worth fixing
- **ABSTAIN**: Agent lacks context to decide (rarely used)

### Step 4: Consensus Determination

**2/3 Consensus Required:**

- Need 2 out of 3 APPROVE votes to validate finding
- 2 or more REJECT votes invalidates finding
- ABSTAIN votes don't count toward consensus

**Consensus Outcomes:**

- `AAA` (3 approve) → **VALIDATED** (strong consensus)
- `AAR` (2 approve, 1 reject) → **VALIDATED** (weak consensus)
- `ARR` (1 approve, 2 reject) → **REJECTED**
- `RRR` (3 reject) → **REJECTED** (strong rejection)
- `AAB`, `ARB` → **VALIDATED** (abstain doesn't block)
- `RRB`, `RBB` → **REJECTED** (abstain doesn't block)
- `ABB` → **INCONCLUSIVE** (requeue for human review)

## Validation Criteria

### Criteria for APPROVE Vote

Agent should vote APPROVE if finding meets ALL:

1. **Real Issue**: Not a false positive, issue actually exists
2. **Actionable**: Can be fixed with reasonable effort
3. **Impactful**: Fixing improves code quality, security, or reliability
4. **Scope-Appropriate**: Within scope of current audit (not general refactoring)

### Criteria for REJECT Vote

Agent should vote REJECT if finding meets ANY:

1. **False Positive**: Issue doesn't actually exist
2. **Not Fixable**: Fixing would require unreasonable effort or break things
3. **No Impact**: Fixing provides no meaningful benefit
4. **Out of Scope**: Not a silent degradation issue (different category)
5. **Already Addressed**: Issue fixed elsewhere or mitigated

### Criteria for ABSTAIN Vote

Agent should vote ABSTAIN if:

1. **Insufficient Context**: Not enough information to decide
2. **Outside Expertise**: Issue outside agent's specialty area
3. **Conflicting Information**: Finding contains contradictory data

## Vote Justification

Each vote must include brief justification:

```json
{
  "agent": "security",
  "vote": "APPROVE",
  "justification": "Missing exception logging creates security blind spot - attackers can probe without detection"
}
```

## Batch Processing

For efficiency, validation panel can process findings in batches:

1. Group findings by category or file
2. Present batch to all three agents
3. Collect votes for entire batch
4. Apply consensus logic to each finding

## Conflict Resolution

**When 3-agent panel can't reach consensus (rare):**

1. **Inconclusive Result** (e.g., `ABB`):
   - Flag for human review
   - Include all agent justifications
   - Don't apply automatic fix

2. **Split Decision** (`AAR`):
   - Proceed with caution
   - Apply fix but mark for review
   - Monitor for unintended consequences

## Output Format

```json
{
  "finding_id": "dep-001",
  "validation_result": "VALIDATED|REJECTED|INCONCLUSIVE",
  "consensus_type": "strong|weak|none",
  "votes": [
    {
      "agent": "security",
      "vote": "APPROVE",
      "justification": "Real security risk"
    },
    {
      "agent": "architect",
      "vote": "APPROVE",
      "justification": "Improves error handling design"
    },
    {
      "agent": "builder",
      "vote": "REJECT",
      "justification": "Fix would require refactoring 10+ files"
    }
  ],
  "recommendation": "Proceed with fix (2/3 approval)",
  "review_required": false
}
```

## Integration with Audit Workflow

### Before Fix Application

1. Category agents complete wave and generate findings
2. **Validation panel reviews all findings**
3. Only VALIDATED findings proceed to fix phase
4. REJECTED findings added to exclusion list
5. INCONCLUSIVE findings flagged for human review

### During Waves

Each wave:

1. Category agents find new issues (6 agents in parallel)
2. Validation panel reviews findings (3 agents in parallel)
3. Validated findings counted toward convergence
4. Process repeats until convergence

## Metrics

Track validation panel effectiveness:

- **Validation Rate**: % of findings validated
- **Rejection Rate**: % of findings rejected
- **Consensus Strength**: % strong consensus (AAA or RRR)
- **Agent Agreement**: How often each pair agrees
- **False Positive Rate**: % of validated findings that were actually false (requires manual audit)

## Tuning Thresholds

If validation panel is:

**Too Strict** (rejecting valid findings):

- Review REJECT justifications
- Adjust agent prompts to be more permissive
- Consider 1/3 threshold for low-severity findings

**Too Permissive** (approving false positives):

- Review APPROVE justifications
- Require stronger evidence in prompts
- Consider requiring unanimous approval for high-severity

## Examples

### Example 1: Strong Approval (AAA)

**Finding**: Exception caught but not logged

**Votes:**

- Security: APPROVE - "Log gap creates security blind spot"
- Architect: APPROVE - "Violates observability principles"
- Builder: APPROVE - "One-line fix, add logger.error()"

**Result**: VALIDATED (strong consensus) → Apply fix

### Example 2: Weak Approval (AAR)

**Finding**: Optional dependency missing silent fallback

**Votes:**

- Security: APPROVE - "Dependency failure should be visible"
- Architect: APPROVE - "Fallback violates fail-fast principle"
- Builder: REJECT - "Optional dependency intended to be optional"

**Result**: VALIDATED (weak consensus) → Apply fix but mark for review

### Example 3: Rejection (ARR)

**Finding**: Empty list returned from get_items()

**Votes:**

- Security: APPROVE - "Stub in production code"
- Architect: REJECT - "Empty list is valid response for 'no items'"
- Builder: REJECT - "Method works correctly, not a stub"

**Result**: REJECTED → Add to exclusion list

### Example 4: Inconclusive (ABB)

**Finding**: Complex validation method returns true

**Votes:**

- Security: APPROVE - "Looks like stub, validation not implemented"
- Architect: ABSTAIN - "Need business context to determine if valid"
- Builder: ABSTAIN - "Can't tell if intentional or stub without docs"

**Result**: INCONCLUSIVE → Flag for human review

## Anti-Patterns to Avoid

1. **Rubber Stamping**: Agents always voting APPROVE
2. **Over-Rejection**: Agents being overly conservative
3. **Insufficient Justification**: Votes without reasoning
4. **Agent Bias**: One agent's opinion dominating
5. **Context Blindness**: Not considering full code context

## Quality Assurance

Periodically audit validation panel by:

1. Manually reviewing sample of VALIDATED findings
2. Manually reviewing sample of REJECTED findings
3. Checking if INCONCLUSIVE findings need process improvement
4. Comparing validation outcomes across different codebases
5. Measuring fix success rate (do validated fixes actually improve code?)
