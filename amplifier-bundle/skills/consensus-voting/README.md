# Consensus Voting Skill

Multi-agent consensus voting with domain-weighted expertise for critical decisions.

## Quick Start

### Auto-Activation

The skill automatically activates when working with:

- Security implementations (authentication, authorization)
- Encryption and cryptographic code
- Sensitive data handling (PII, credentials)
- Permission and access control changes

### Explicit Trigger

```bash
/amplihack:consensus-vote "Should we use JWT or session cookies for auth?"
```

Or invoke programmatically:

```python
Skill(skill="consensus-voting")
```

## How It Works

1. **Domain Detection** - Analyzes change to determine expertise area
2. **Agent Selection** - Selects relevant agents with domain-specific weights
3. **Voting** - Each agent votes with confidence level
4. **Weighted Calculation** - Applies expertise weights to votes
5. **Threshold Check** - Validates against voting mode (supermajority default)
6. **Result Report** - Documents decision with reasoning and dissent

## Key Concept: Weighted Voting

Unlike simple majority voting, this skill weights votes by domain expertise:

| Domain    | Top Expert (3x) | Strong (2x)       | Standard (1x)    |
| --------- | --------------- | ----------------- | ---------------- |
| Security  | security        | architect         | reviewer, tester |
| Auth      | security        | architect         | reviewer, tester |
| Data      | security        | architect         | reviewer, tester |
| Algorithm | optimizer       | architect, tester | reviewer         |

## When to Use vs Alternatives

| Scenario               | Use This         | Alternative        |
| ---------------------- | ---------------- | ------------------ |
| Binary security choice | consensus-voting | -                  |
| Complex trade-offs     | -                | debate-workflow    |
| Code generation        | -                | n-version-workflow |
| Design exploration     | -                | debate-workflow    |
| Risk validation        | consensus-voting | -                  |

## Voting Modes

- **supermajority** (66%+) - Default for security, requires strong consensus
- **simple-majority** (50%+) - Faster decisions, lower bar
- **unanimous** (100%) - Highest bar, all must agree

## Example Output

```markdown
## Consensus Voting Result

**Decision:** Use argon2id for password hashing
**Domain:** AUTH
**Threshold:** Supermajority (66%+)
**Result:** PASSED (68.2%)

### Vote Summary

| Agent     | Weight | Vote     | Confidence |
| --------- | ------ | -------- | ---------- |
| security  | 2.5    | argon2id | HIGH       |
| architect | 2.0    | argon2id | MEDIUM     |
| reviewer  | 1.5    | bcrypt   | HIGH       |
| tester    | 1.5    | argon2id | MEDIUM     |

### Key Reasoning

- **security (2.5):** "OWASP current recommendation, memory-hard"

### Dissenting View

- **reviewer (1.5):** "bcrypt more battle-tested in production"
```

## Integration

### With Debate Workflow

When voting fails to reach consensus, escalate:

```
No consensus (52.1%) → Invoke debate-workflow
```

### With N-Version Workflow

Use voting to select between N-version implementations:

```
N-version → 3 implementations → Consensus vote → Winner
```

## Files

- `SKILL.md` - Full skill definition with execution process
- `README.md` - This documentation (usage guide)

## Philosophy Alignment

- **Evidence-Based:** All votes require reasoning
- **Expertise-Weighted:** Domain knowledge matters
- **Transparent:** Dissent documented, not hidden
- **Appropriate Rigor:** Auto-triggers for high-risk domains
