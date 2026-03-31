# How to Use the Crusty Old Engineer Advisor

Get grounded, skeptical engineering feedback on architectural decisions, legacy refactors, tooling choices, and broad planning questions.

## Contents

- [When to Use It](#when-to-use-it)
- [Invoke the Skill](#invoke-the-skill)
- [What to Expect](#what-to-expect)
- [Get Better Answers](#get-better-answers)
- [When NOT to Use It](#when-not-to-use-it)

## When to Use It

Use the Crusty Old Engineer (COE) when you need a reality check:

- **Architectural decisions**: "Should I switch from monolith to microservices?"
- **Legacy refactors**: "We want to replace our ORM with raw SQL."
- **New tooling evaluation**: "Is it worth adopting this new framework?"
- **Broad planning**: "How should I start building a CI pipeline from scratch?"
- **Sanity checks**: "What could go wrong with this migration plan?"

## Invoke the Skill

Invoke the skill directly:

```
/crusty-old-engineer
```

Or reference it by keyword in your prompt:

```
Give me a crusty reality check on replacing our PostgreSQL database with a graph database
for our user authentication system.
```

The skill also auto-activates when your prompt contains phrases like "reality check", "what could go wrong", "should I use", "is this a good idea", or "crusty".

## What to Expect

Responses follow a consistent structure. Not every section appears in every response — the skill includes what is relevant and omits what is not.

### 1. Short Framing

A plain statement of what the problem actually is. No hype, no sugar coating.

> This is not a database migration. It is a data model redesign with operational fallout.

### 2. Key Risks / Sharp Edges

Concrete, experience-backed points. Each risk is specific and actionable, not vague hand-waving.

> - Graph databases solve traversal problems. Authentication is not a traversal problem.
> - You lose ACID transactions on the critical path where you need them most.
> - Operational tooling for graph databases is years behind PostgreSQL.

### 3. Recommended Approach

A viable path forward, including constraints, sequencing, or validation steps.

> Keep PostgreSQL for auth. If you have a genuine graph traversal need elsewhere,
> prototype it in isolation. Ship results before committing to a migration.

### 4. References (when available)

Pointers to relevant primary sources — postmortems, SRE books, canonical papers — when they exist for the topic. Not every response includes references.

### 5. Optional Aside

Brief historical or experiential context when it adds clarity. Omitted when it would be filler.

> Most "we need a graph database" conversations end with "we needed a JOIN and an index."

## Get Better Answers

The COE rewards preparation. To get the most useful feedback:

1. **State what you have already tried or researched.** The skill checks for prior effort. If your question suggests no investigation, expect a pointed question back about what you have already looked at.

2. **Be specific about constraints.** "Should I use Kubernetes?" gets a worse answer than "We have 3 services, 2 engineers, no SRE team, and a deadline in Q3. Should we adopt Kubernetes?"

3. **Include the real context.** Team size, timeline, existing infrastructure, and what triggered the decision matter more than the technology name.

4. **Ask about trade-offs, not validation.** "Is X a good idea?" gets a useful answer. "Convince me X is a good idea" does not — the skill will not do that.

## When NOT to Use It

The COE is not useful for:

- **Mechanical tasks**: "Format this JSON" or "Write a unit test for this function"
- **Emotional support**: The skill is deliberately not encouraging
- **Exhaustive research**: It provides pointers, not bibliographies
- **Policy decisions**: It does not override organizational or security requirements

For code review, use the [reviewer agent](../claude/agents/amplihack/core/reviewer.md). For architecture design, use the [architect agent](../claude/agents/amplihack/core/architect.md). The COE is for judgment calls where you want an unimpressed second opinion.
