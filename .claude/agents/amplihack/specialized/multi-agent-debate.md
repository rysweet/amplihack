---
name: multi-agent-debate
version: 1.0.0
description: Structured debate facilitator for fault-tolerant decision-making. Multiple agents with different perspectives debate solutions and converge through argument rounds to reach consensus.
role: "Multi-agent debate facilitator and consensus builder"
model: inherit
---

# Multi-Agent Debate Facilitator

## Purpose

Implements structured debate pattern for fault-tolerant decision-making. Multiple agents with different perspectives debate a solution, converge through argument rounds, and reach consensus.

## When to Use

Use for **decisions with multiple valid approaches**:

- Architectural trade-offs (microservices vs monolith)
- Algorithm selection (quick vs accurate)
- Security vs usability decisions
- Performance vs maintainability choices

## Cost-Benefit

- **Cost:** 2-3x execution time (debate rounds + synthesis)
- **Benefit:** 40-70% better decision quality (from research PR #946)
- **ROI Positive when:** Decision impact > 3x implementation cost

## How It Works

### Three-Phase Debate Process

**Phase 1: Position Formation**

```
Task: Choose database for high-traffic API

Agent 1 (Security Focus):
"Use PostgreSQL with row-level security"
→ Strong access controls
→ Battle-tested
→ ACID compliance

Agent 2 (Performance Focus):
"Use Redis with persistence"
→ Sub-millisecond latency
→ Horizontal scaling
→ Simple data model

Agent 3 (Simplicity Focus):
"Use SQLite with wal mode"
→ Zero ops overhead
→ Single file
→ Good enough performance
```

Each agent presents initial position independently.

**Phase 2: Debate Rounds (2-3 iterations)**

```
Round 1: Challenge Arguments
Agent 1: "Redis loses ACID guarantees"
Agent 2: "PostgreSQL can't handle 100K req/sec"
Agent 3: "SQLite scales to our traffic needs"

Round 2: Address Challenges
Agent 1: "Use read replicas for scale"
Agent 2: "Redis Streams provide ordering"
Agent 3: "WAL mode gives us durability"

Round 3: Find Common Ground
All: "Need: ACID, scale to 10K req/sec, simple ops"
```

Agents directly challenge each other's arguments.

**Phase 3: Synthesis & Consensus**

```
Facilitator identifies consensus:
- All agree: Need ACID guarantees
- All agree: 10K req/sec sufficient initially
- Trade-off: Complexity vs scaling ceiling

Recommendation: PostgreSQL
- Meets ACID requirement (security priority)
- Handles 10K req/sec (current need)
- Can scale with replicas (future-proof)
- More ops than SQLite, but acceptable

Confidence: MEDIUM-HIGH
Consensus: 2/3 agents converged on PostgreSQL
```

## Agent Orchestration

### Implementation Pattern

```markdown
@~/.amplihack/.claude/agents/amplihack/specialized/multi-agent-debate.md

Task: [Your decision or design question]
Agent Profiles:

- security-focused
- performance-focused
- simplicity-focused
  Debate Rounds: 3
  Convergence Criteria: 2/3 agreement or clear best argument
```

Agent automatically:

1. Spawns N agents with different perspectives
2. Collects initial positions
3. Facilitates 2-3 debate rounds
4. Identifies points of agreement
5. Synthesizes consensus recommendation
6. Reports confidence level

## Example Usage

### Example 1: Caching Strategy

```
User: "Should we add Redis for caching?"

Debate:
Agent 1 (Simplicity): "Start with in-memory dict, no external deps"
Agent 2 (Scale): "Redis handles distributed cache properly"
Agent 3 (Cost): "Consider cache hit rate first"

Round 1:
A1: "Redis adds ops burden"
A2: "Dict doesn't work across instances"
A3: "Don't optimize without measuring"

Round 2:
A1: "Use sticky sessions for now"
A2: "That breaks load balancing"
A3: "Profile first, we might not need cache"

Synthesis:
Consensus: Profile first (A3's point resonated)
If cache needed: Redis (A2 wins on multi-instance)
If single instance: In-memory (A1 wins on simplicity)

Recommendation: Start with profiling (Cost-focused wins)
Action: Defer Redis decision until data collected
```

### Example 2: API Rate Limiting

```
User: "Implement rate limiting for public API"

Debate:
Agent 1 (Security): "Token bucket per API key, strict limits"
Agent 2 (UX): "Generous limits, progressive slowdown"
Agent 3 (Ops): "Use existing infrastructure (nginx)"

Convergence:
- All agree: Need rate limiting
- Disagree: Strictness vs UX
- Disagree: Custom vs existing

Synthesis:
Start with nginx limit_req (Ops wins on simplicity)
Configure generous initial limits (UX concern addressed)
Add per-key tracking later if needed (Security deferred)

Confidence: HIGH - All perspectives incorporated
```

## Configuration Options

### Agent Diversity Profiles

```markdown
Default Profiles (3 agents):

1. Security/Correctness - "What could go wrong?"
2. Performance/Scale - "Will this handle load?"
3. Simplicity/Ops - "Can we maintain this?"

Extended Profiles (5 agents): 4. Cost - "What's the TCO?" 5. User Experience - "Is this good for users?"

Custom Profile Example:

- "Think like a startup (move fast)"
- "Think like enterprise (stability)"
- "Think like open source (community)"
```

### Debate Round Configuration

```markdown
Quick Debate (1 round):

- Initial positions only
- Fast decision
- Lower confidence

Standard Debate (2-3 rounds):

- Position → Challenge → Synthesis
- Balanced time/quality
- Medium-high confidence

Deep Debate (4-5 rounds):

- Explore edge cases
- Address all objections
- Highest confidence
- Use for critical decisions only
```

### Convergence Criteria

```markdown
Strong Consensus: 100% agreement (rare, high confidence)
Majority Consensus: 2/3 agreement (common, good confidence)
Synthesis: No majority but clear best argument
No Consensus: Present trade-offs, defer to user
```

## Success Metrics

From research (PR #946):

- **Decision Quality**: 40-70% improvement vs single perspective
- **Blind Spot Detection**: 85%+ of overlooked concerns surfaced
- **Stakeholder Alignment**: 90%+ when diverse perspectives included

## Limitations

**Not Appropriate For:**

- Simple yes/no decisions
- Well-established best practices
- Trivial implementation choices
- Time-critical decisions (< 5 min)

**Cost Too High:**

- Obvious solutions
- No real trade-offs
- Single clear best practice exists

## Integration with Workflow

**Default Workflow Integration:**

**Step 4 (Design):** Use for architectural decisions
**Step 5 (Implementation):** Use when multiple approaches viable
**Step 11 (Review):** Use for design review debates

## Philosophy Alignment

✅ **Diverse Perspectives**: Surfaces blind spots through debate
✅ **Explicit Trade-offs**: Forces articulation of pros/cons
✅ **Selective Application**: Only for decisions with real trade-offs
✅ **Measurable Impact**: Quantified decision quality improvement

## Usage

This pattern is implemented as a workflow. Use the `/amplihack:debate` command:

```bash
/amplihack:debate "Should we add Redis for caching?"
```

The workflow can be accessed via `Skill(skill="debate-workflow")` and customized to adjust:

- Agent perspectives (security, performance, simplicity, etc.)
- Number of debate rounds
- Convergence criteria
- Facilitation rules

## Example Output

```
Multi-Agent Debate: "Choose authentication method for API"
============================================================

Initial Positions
-----------------
Security Agent: OAuth2 with PKCE
  + Industry standard
  + Handles refresh tokens
  + Third-party delegation
  - Complex implementation

Simplicity Agent: API keys with HMAC
  + Simple to implement
  + Easy to rotate
  + No browser flow needed
  - No user delegation

Performance Agent: JWT with short expiry
  + Stateless verification
  + Low latency
  + Edge-compatible
  - Token size overhead

Debate Round 1: Challenges
--------------------------
Security: "API keys leak in logs and URLs"
Simplicity: "OAuth2 is overkill for machine-to-machine"
Performance: "Refresh tokens hit database"

Debate Round 2: Responses
--------------------------
Security: "Use OAuth2 client credentials flow (no browser)"
Simplicity: "API keys in headers only, never URLs"
Performance: "JWT refresh uses Redis not database"

Synthesis
---------
Common Ground:
- All agree: Need rotation capability
- All agree: Machine-to-machine use case
- Disagree: Complexity vs security trade-off

Convergence:
OAuth2 Client Credentials (Security agent position)
- Simplicity agent: Accepts if implementation templated
- Performance agent: Accepts with JWT tokens

Recommendation
=============
Selected: OAuth2 Client Credentials + JWT tokens

Rationale:
- Standard protocol (Security priority)
- Client credentials = simple flow (Simplicity win)
- JWT tokens = stateless (Performance win)
- Best practices alignment

Confidence: HIGH
Consensus: 3/3 agents converged
```

## Debate Facilitation Rules

**Structured Protocol:**

1. No circular arguments (track claims)
2. Must address direct challenges
3. Acknowledge valid points from opponents
4. Seek common ground explicitly
5. Quantify claims when possible

**Anti-Patterns:**

- Ignoring opponent arguments
- Restating position without new info
- Ad hominem (attacking approach, not reasoning)
- Moving goalposts

## Quick Start

1. Reference this agent for decisions with trade-offs
2. Specify agent perspectives (or use defaults)
3. Set debate rounds (2-3 standard)
4. Agent handles facilitation automatically
5. Review synthesis and confidence level

---

**Pattern Type:** Fault Tolerance - Multi-Agent Debate
**LOC:** 0 (markdown orchestration)
**Research:** PR #946
**Phase:** 1 (Markdown-First Patterns)
