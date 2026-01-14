---
name: DEBATE_WORKFLOW
version: 1.0.0
description: Multi-agent structured debate for complex decisions requiring diverse perspectives
steps: 8
phases:
  - decision-framing
  - perspective-initialization
  - initial-positions
  - challenge-and-respond
  - common-ground-synthesis
  - facilitator-synthesis
  - decision-documentation
  - implementation
success_criteria:
  - "Decision clearly framed with evaluation criteria"
  - "Multiple perspectives (3-7) provide independent analysis"
  - "Arguments supported by evidence, not opinions"
  - "Facilitator synthesizes consensus or hybrid approach"
  - "Decision documented with rationale and dissent"
philosophy_alignment:
  - principle: Perspective Diversity
    application: Multiple viewpoints surface hidden trade-offs
  - principle: Evidence-Based Decisions
    application: Arguments must be supported with data
  - principle: Transparent Trade-offs
    application: Dissent documented, not hidden
  - principle: Structured Exploration
    application: Debate format prevents premature convergence
references:
  workflows:
    - DEFAULT_WORKFLOW.md
    - CONSENSUS_WORKFLOW.md
customizable: true
---

# Debate Workflow

This workflow implements structured multi-perspective debate for important architectural decisions, design trade-offs, and complex problems where multiple valid approaches exist.

> **DEPRECATION WARNING**: Markdown workflows deprecated. See `docs/WORKFLOW_TO_SKILLS_MIGRATION.md`

## Configuration

### Core Parameters

**Number of Perspectives**: How many viewpoints to include in debate

- `3` - Default (security, performance, simplicity)
- `5` - Extended (add: maintainability, user-experience)
- `7` - Comprehensive (add: scalability, cost)

**Debate Rounds**: How many rounds of discussion

- `2` - Quick (position + challenge)
- `3` - Standard (position + challenge + synthesis)
- `4-5` - Deep (multiple challenge/response cycles)

**Convergence Criteria**: When to conclude debate

- `100%` - Strong consensus (all perspectives agree)
- `2/3` - Majority rule (two-thirds agreement)
- `synthesis` - Facilitator synthesizes best hybrid
- `evidence` - Follow strongest evidence/arguments

### Standard Perspective Profiles

**Security Perspective**:

- Focus: Vulnerabilities, attack vectors, data protection
- Questions: "What could go wrong? How do we prevent breaches?"
- Agent: security agent

**Performance Perspective**:

- Focus: Speed, scalability, resource efficiency
- Questions: "Will this scale? What are the bottlenecks?"
- Agent: optimizer agent

**Simplicity Perspective**:

- Focus: Minimal complexity, ruthless simplification
- Questions: "Is this the simplest solution? Can we remove abstractions?"
- Agent: cleanup agent + reviewer agent

**Maintainability Perspective**:

- Focus: Long-term evolution, technical debt
- Questions: "Can future developers understand this? How hard to change?"
- Agent: reviewer agent + architect agent

**User Experience Perspective**:

- Focus: API design, usability, developer experience
- Questions: "Is this intuitive? How will users interact with this?"
- Agent: api-designer agent

**Scalability Perspective**:

- Focus: Growth capacity, distributed systems
- Questions: "What happens at 10x load? 100x?"
- Agent: optimizer agent + architect agent

**Cost Perspective**:

- Focus: Resource usage, infrastructure costs, development time
- Questions: "What's the ROI? Are we over-engineering?"
- Agent: analyzer agent

### Cost-Benefit Analysis

**When to Use:**

- Major architectural decisions (framework selection, system design)
- Complex trade-offs with no clear winner
- Controversial changes affecting multiple teams
- High-impact decisions requiring buy-in
- When perspectives genuinely conflict

**When NOT to Use:**

- Simple implementation choices
- Decisions with obvious correct answer
- Time-sensitive hot fixes
- Minor refactoring
- Routine feature additions

**Trade-offs:**

- Cost: Multiple agent cycles, longer decision time
- Benefit: Well-reasoned decisions, surface hidden risks
- Best for: Decisions that are expensive to reverse

## How This Workflow Works

**Integration with DEFAULT_WORKFLOW:**

This workflow replaces Step 4 (Research and Design) of the DEFAULT_WORKFLOW when complex decisions require multi-perspective analysis. Implementation (Step 5) proceeds with the consensus decision.

**Execution:**

- Invoke via `/ultrathink --workflow debate` for complex decisions
- Or manually execute for specific architectural choices
- Each perspective runs in isolated subprocess
- Facilitator synthesizes debate results

## The Debate Workflow

### Step 1: Frame the Decision

- [ ] **Use** ambiguity agent to clarify the decision to be made
- [ ] **Use** prompt-writer agent to create clear decision prompt
- [ ] Define decision scope and constraints
- [ ] Identify stakeholder concerns
- [ ] List evaluation criteria
- [ ] Document explicit user requirements that constrain options
- [ ] **CRITICAL: Frame decision as question, not predetermined answer**

**Decision Framing Template:**

```markdown
# Decision: [Brief Title]

## Question

[One-sentence question to be debated]

## Context

[Why this decision matters, background information]

## Constraints

[Non-negotiable requirements, technical limitations]

## Evaluation Criteria

[How we'll judge proposed solutions]

## Perspectives to Include

[Which viewpoints are most relevant]
```

**Example:**

```markdown
# Decision: Data Storage Strategy for User Analytics

## Question

Should we use PostgreSQL with JSONB, MongoDB, or ClickHouse
for storing and querying user analytics events?

## Context

- 10M events/day expected at launch
- 100M events/day within 2 years
- Complex queries for dashboard analytics
- Real-time and historical reporting needed

## Constraints

- Must handle 10M events/day minimum
- Query latency < 200ms for dashboards
- Budget: $5K/month infrastructure
- Team familiar with PostgreSQL, not ClickHouse

## Evaluation Criteria

1. Performance at scale
2. Query flexibility
3. Operational complexity
4. Cost at scale
5. Team learning curve

## Perspectives to Include

Performance, Cost, Maintainability, Scalability
```

### Step 2: Initialize Perspectives

- [ ] Select N perspectives relevant to decision
- [ ] **Spawn Claude subprocess for each perspective**
- [ ] Each subprocess receives decision framing doc
- [ ] Each subprocess assigned perspective profile
- [ ] **No context sharing between perspectives yet**
- [ ] Each forms initial position independently

**Subprocess Assignment:**

```
Subprocess 1: Security perspective
Subprocess 2: Performance perspective
Subprocess 3: Simplicity perspective
[Additional subprocesses for extended perspectives]
```

**Initial Position Requirements:**

- State recommended approach
- Provide 3-5 supporting arguments
- Identify risks of alternative approaches
- Quantify claims where possible

### Step 3: Debate Round 1 - Initial Positions

- [ ] Collect initial positions from all perspectives
- [ ] **Use** analyzer agent to synthesize positions
- [ ] Document each perspective's recommendation
- [ ] Identify areas of agreement
- [ ] Identify areas of conflict
- [ ] Surface assumptions made by each perspective

**Round 1 Output Structure:**

```markdown
## Security Perspective: [Recommendation]

Arguments For:

1. [Argument with evidence]
2. [Argument with evidence]
3. [Argument with evidence]

Concerns About Alternatives:

- [Alternative A]: [Specific concern]
- [Alternative B]: [Specific concern]

Assumptions:

- [Assumption 1]
- [Assumption 2]
```

**Example:**

```markdown
## Performance Perspective: Recommends ClickHouse

Arguments For:

1. Columnar storage: 10-100x faster for analytics queries
2. Proven at scale: Handles billions of events at Cloudflare, Uber
3. Time-series optimized: Built specifically for this use case

Concerns About Alternatives:

- PostgreSQL: JSONB queries don't scale past 50M rows efficiently
- MongoDB: Aggregation pipeline slower than ClickHouse for analytics

Assumptions:

- Analytics queries dominate over transactional writes
- Team can learn new technology in 2-3 weeks
```

### Step 4: Debate Round 2 - Challenge and Respond

- [ ] Share all Round 1 positions with all perspectives
- [ ] Each perspective challenges other perspectives' arguments
- [ ] Each perspective defends their position against challenges
- [ ] **Use** analyzer agent to track argument strength
- [ ] Identify which arguments withstand scrutiny
- [ ] Document concessions and refinements

**Challenge Format:**

```markdown
## [Perspective A] challenges [Perspective B]

Challenge: [Question or counter-argument]
Evidence: [Supporting data or examples]
Request: [What would change your position?]
```

**Response Format:**

```markdown
## [Perspective B] responds to [Perspective A]

Response: [Address the challenge]
Concession: [Points where you agree or adjust]
Counter: [Additional evidence or reasoning]
```

**Example Exchange:**

```markdown
## Simplicity challenges Performance

Challenge: ClickHouse adds significant operational complexity.
Our team knows PostgreSQL deeply but has zero ClickHouse experience.
Learning curve could delay project by months.

Evidence: ClickHouse requires:

- Separate replication configuration
- Different backup strategies
- New monitoring tooling
- ZooKeeper for clustering

Request: What's the learning curve timeline, realistically?

## Performance responds to Simplicity

Response: Valid concern. ClickHouse does add complexity.

Concession: If we stay under 50M events, PostgreSQL might suffice.
Let's validate current growth projections.

Counter: However, PostgreSQL also needs optimization at scale:

- Partitioning strategy for time-series data
- Index tuning for JSONB queries
- Vacuum and maintenance procedures
  Both have learning curves, just different ones.
```

### Step 5: Debate Round 3 - Find Common Ground

- [ ] Identify points of consensus across perspectives
- [ ] Surface remaining disagreements explicitly
- [ ] Explore hybrid approaches combining insights
- [ ] **Use** architect agent to design synthesis options
- [ ] Validate hybrid approaches against all perspectives
- [ ] Document convergence or divergence

**Convergence Analysis:**

```markdown
## Areas of Agreement

1. [Consensus point 1]
2. [Consensus point 2]

## Remaining Disagreements

1. [Disagreement 1]
   - Security says: [position]
   - Performance says: [position]
   - Potential resolution: [hybrid approach]

## Hybrid Approaches Identified

1. [Hybrid Option 1]
   - Combines: [which perspectives]
   - Trade-offs: [explicit costs/benefits]
2. [Hybrid Option 2]
   - Combines: [which perspectives]
   - Trade-offs: [explicit costs/benefits]
```

**Example:**

```markdown
## Areas of Agreement

1. Current PostgreSQL setup won't scale to 100M events/day
2. We need to plan for growth, not just current requirements
3. Operational complexity is a real concern given team size

## Remaining Disagreements

### Storage Technology Choice

- Performance says: ClickHouse is necessary for scale
- Simplicity says: Optimize PostgreSQL first, migrate later if needed
- Cost says: PostgreSQL cheaper short-term, ClickHouse cheaper long-term

Potential resolution: Start with PostgreSQL, prototype ClickHouse in parallel

## Hybrid Approaches Identified

### Option A: PostgreSQL with Migration Path

- Use PostgreSQL with time-series partitioning
- Set up ClickHouse dev environment for learning
- Define migration trigger: when queries exceed 200ms
- Estimated migration: 1-2 weeks when triggered

Trade-offs:

- Lower risk: familiar technology
- Defer learning curve

* Potential future migration cost
* May hit performance limits sooner

### Option B: ClickHouse with PostgreSQL Fallback

- Primary storage in ClickHouse
- Keep PostgreSQL for transactional data
- Use ClickHouse for analytics only

Trade-offs:

- Optimal long-term performance
- No future migration needed

* Immediate learning curve
* Two databases to maintain
```

### Step 6: Facilitator Synthesis

- [ ] **Use** architect agent as neutral facilitator
- [ ] **Use** analyzer agent to evaluate all arguments
- [ ] Review all debate rounds systematically
- [ ] Identify strongest evidence-based arguments
- [ ] Make recommendation with confidence level
- [ ] Document decision rationale thoroughly
- [ ] Include dissenting views explicitly

**Synthesis Structure:**

```markdown
## Facilitator Synthesis

### Recommendation

[Clear statement of recommended approach]

### Confidence Level

[High/Medium/Low] confidence based on:

- Consensus level: [X% of perspectives agree]
- Evidence quality: [Strong/Moderate/Weak]
- Risk level: [Low/Medium/High if wrong]

### Rationale

[Explanation of why this recommendation]

### Key Arguments That Won

1. [Argument that swayed decision]
2. [Argument that swayed decision]
3. [Argument that swayed decision]

### Key Arguments Against (Dissenting Views)

1. [Strongest counter-argument]
2. [Remaining concern]

### Implementation Guidance

[How to execute this decision]

### Success Metrics

[How we'll know if this was the right choice]

### Revisit Triggers

[Conditions that would require reconsidering this decision]
```

**Example:**

```markdown
## Facilitator Synthesis

### Recommendation

Start with PostgreSQL using time-series best practices, with
planned ClickHouse migration when query performance degrades.

### Confidence Level

MEDIUM-HIGH confidence based on:

- Consensus level: 3/4 perspectives support phased approach
- Evidence quality: Strong evidence for both technologies
- Risk level: Low (clear migration path if PostgreSQL insufficient)

### Rationale

The debate revealed PostgreSQL can handle our launch requirements
(10M events/day) with proper partitioning. ClickHouse offers
superior long-term performance but introduces operational risk
given team inexperience. A phased approach balances these concerns:
start simple, migrate when data validates the need.

### Key Arguments That Won

1. Team's PostgreSQL expertise reduces time-to-market risk
2. PostgreSQL sufficient for validated current scale (10M events/day)
3. 100M events/day is projection, not validated requirement
4. Migration cost (1-2 weeks) is acceptable when actually needed

### Key Arguments Against (Dissenting Views)

1. Performance perspective warns: Migration might come sooner than
   expected if growth accelerates (valid concern)
2. May encounter PostgreSQL limitations we haven't anticipated

### Implementation Guidance

1. Implement PostgreSQL with time-series partitioning (by day)
2. Index strategy for common query patterns
3. Set up monitoring: track query latency, table sizes
4. Parallel: Dev environment with ClickHouse, experiment on copy of data
5. Define migration trigger: sustained 200ms+ query latency

### Success Metrics

- Query latency < 200ms for 95th percentile
- Can scale to 20M events/day before migration
- Team can add ClickHouse expertise in parallel (non-blocking)

### Revisit Triggers

- Query latency consistently exceeds 200ms
- Event volume grows faster than projected
- New analytics requirements exceed PostgreSQL capabilities
- ClickHouse team expertise established (enables lower-risk migration)
```

### Step 7: Decision Documentation

- [ ] Create decision record: `decisions/YYYY-MM-DD-decision-name.md`
- [ ] Document full debate transcript
- [ ] Include all perspective arguments
- [ ] Record synthesis and final decision
- [ ] Add to `@amplihack:context/DISCOVERIES.md`
- [ ] Update relevant architecture docs

**Decision Record Template:**

```markdown
# Decision Record: [Title]

Date: [YYYY-MM-DD]
Status: Accepted
Decision Makers: [List perspectives included]

## Context

[What decision was needed and why]

## Decision

[What was decided]

## Consequences

[What happens because of this decision]

## Alternatives Considered

[What other options were debated]

## Debate Summary

[Key arguments from each perspective]

## Dissenting Opinions

[Perspectives that disagreed and why]

## Review Date

[When to revisit this decision]

---

## Full Debate Transcript

### Round 1: Initial Positions

[Complete positions from all perspectives]

### Round 2: Challenges and Responses

[All challenge/response exchanges]

### Round 3: Convergence Analysis

[Common ground and hybrid approaches]

### Facilitator Synthesis

[Complete synthesis document]
```

### Step 8: Implement Decision

- [ ] **Use** builder agent to implement chosen approach
- [ ] Follow the decided path from synthesis
- [ ] Implement monitoring for success metrics
- [ ] Set up alerts for revisit triggers
- [ ] Document decision in code comments
- [ ] Create runbook if operational complexity added

**Implementation Includes:**

- Code implementing the decision
- Tests validating the approach
- Monitoring for success metrics
- Documentation for team
- Contingency plans for revisit triggers

## Return to DEFAULT_WORKFLOW

After completing these steps:

- [ ] Continue with Step 5 (Implement the Solution) of DEFAULT_WORKFLOW
- [ ] Use debate decision as architectural specification
- [ ] All subsequent steps (testing, CI/CD, PR) proceed normally

## Examples

### Example 1: API Design - REST vs GraphQL

**Configuration:**

- Perspectives: 5 (Simplicity, Performance, User-Experience, Maintainability, Cost)
- Rounds: 3
- Convergence: Synthesis

**Debate Summary:**

- Simplicity: REST is straightforward, well-understood
- Performance: GraphQL reduces over-fetching, fewer round trips
- UX: GraphQL gives frontend flexibility, better DX
- Maintainability: REST easier to version and evolve
- Cost: GraphQL higher learning curve, more complex infrastructure

**Result**: REST for initial MVP, GraphQL for v2

- Rationale: Team knows REST, faster to ship
- Migration path: Add GraphQL layer in 6 months
- Trigger: When frontend requests 3+ endpoints per view

### Example 2: Testing Strategy - Unit vs Integration Heavy

**Configuration:**

- Perspectives: 3 (Simplicity, Maintainability, Performance)
- Rounds: 2
- Convergence: 2/3 majority

**Debate Summary:**

- Simplicity: Unit tests, mock all dependencies
- Maintainability: Integration tests, test real interactions
- Performance: Mix, optimize for feedback speed

**Result**: 70% unit, 30% integration (Majority agreed)

- Rationale: Unit tests faster feedback, integration tests catch real issues
- Dissent: Simplicity wanted 90% unit tests (overruled by maintainability concerns)

### Example 3: Deployment Strategy - Kubernetes vs Serverless

**Configuration:**

- Perspectives: 5 (Cost, Simplicity, Scalability, Performance, Maintainability)
- Rounds: 4
- Convergence: Synthesis (no majority)

**Debate Summary:**

- Long, contentious debate with no clear winner
- Cost and Simplicity favored serverless
- Scalability and Performance favored Kubernetes
- Maintainability split (serverless simpler, k8s more control)

**Result**: Serverless with k8s option researched

- Rationale: Start simple, team small, serverless faster
- Hybrid: Evaluate k8s at 10x scale or complex networking needs
- Strong dissent documented: Performance perspective believes this will need revisiting soon

## Customization

To customize this workflow:

1. Edit Configuration section to adjust perspectives, rounds, or convergence criteria
2. Add or modify perspective profiles for your domain
3. Adjust debate round structure (add rounds, change focus)
4. Modify synthesis criteria based on project needs
5. Save changes - updated workflow applies to future executions

## Philosophy Notes

This workflow enforces:

- **Perspective Diversity**: Multiple viewpoints surface hidden trade-offs
- **Evidence-Based**: Arguments must be supported, not just opinions
- **Transparent Trade-offs**: Dissent is documented, not hidden
- **Structured Exploration**: Debate format prevents premature convergence
- **Decision Quality**: Better decisions through rigorous analysis
- **Learning**: Debate transcripts become organizational knowledge
