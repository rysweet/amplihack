# How to Use the Crusty Old Engineer (COE) Advisor

The `crusty-old-engineer` skill provides grounded, skeptical engineering advice
for architectural decisions, legacy replacements, and tooling choices. It gives
you a second opinion that prioritizes long-term consequences over short-term
enthusiasm.

## Invoke the Skill

Say any of the following in a Claude Code session:

```
/crusty-old-engineer Should I replace our Postgres queue with a dedicated message broker?
```

```
/coe Is this a good idea?
```

Or trigger auto-activation with natural language:

```
Reality check: we're planning to rewrite the auth layer in Rust. What could go wrong?
```

**Auto-activation keywords**: `crusty`, `coe`, `old engineer`, `engineering judgment`,
`should I use`, `is this a good idea`, `what could go wrong`, `reality check`

## When to Use It

Use the COE advisor when you are:

- Proposing or evaluating an architectural decision
- Replacing or refactoring a legacy system
- Evaluating new tooling, frameworks, or automation
- Asking broad "how should I start?" questions
- Treating a known hard problem as if it were novel

Skip it for purely mechanical tasks — code formatting, renaming, simple refactors.

## What to Expect

The COE advisor returns a structured response:

| Section | What it contains |
|---|---|
| **Short framing** | What the problem actually is, stated plainly |
| **Key risks / sharp edges** | Concrete, experience-backed points |
| **Recommended approach** | How to proceed responsibly, with trade-offs explicit |
| **References** | Links to vetted primary sources (postmortems, SRE references) |
| **Optional aside** | Historical or experiential context when relevant |

## Example Interaction

**You:**

```
Is it a good idea to replace our synchronous HTTP calls with an event-driven
message bus for our internal microservices?
```

**COE advisor (representative output):**

> **Short framing:** This is not a simplification. It's a trade of one failure mode
> for several others.
>
> **Key risks:**
> - Observability degrades immediately. Distributed tracing across a bus requires
>   explicit instrumentation; synchronous traces come for free.
> - At-least-once delivery introduces duplicate processing unless every consumer
>   is idempotent. Most are not.
> - Local development complexity increases. Your engineers now need a running bus
>   to test anything.
>
> **Recommended approach:** Map which call paths actually need decoupling and why.
> If your answer is "latency" — measure first. If it's "resilience" — consider
> retries with backoff before a bus. Migrate one bounded context at a time.
>
> **References:**
> - Martin Fowler, "What do you mean by Event-Driven?": https://martinfowler.com/articles/201701-event-driven.html
>
> **Aside:** Teams that adopt event buses for all communication usually adopt
> a synchronous escape hatch six months later.

## When Not to Use This Skill

- Pure implementation help (writing code, fixing bugs, explaining a function)
- Questions where you need encouragement rather than assessment
- Tasks that are already decided and in progress — the COE is for decisions, not post-hoc validation

## Related Skills

- [`supply-chain-audit`](run-supply-chain-audit.md) — security-focused risk assessment for dependencies and CI
- [`philosophy-guardian`](../claude/skills/philosophy-guardian/SKILL.md) — amplihack philosophy compliance review
