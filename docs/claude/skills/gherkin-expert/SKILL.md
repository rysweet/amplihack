---
name: gherkin-expert
version: 1.0.0
description: Gherkin/BDD specification expert for writing behavioral scenarios, acceptance criteria, and applying structured specifications to improve code generation quality
activation_keywords:
  - "Gherkin"
  - "BDD"
  - "behavior-driven"
  - "Given When Then"
  - "Given/When/Then"
  - "Feature:"
  - "Scenario:"
  - "Scenario Outline:"
  - "acceptance criteria"
  - "behavioral specification"
  - "feature file"
  - "cucumber"
  - "SpecFlow"
agent: amplihack:specialized:gherkin-expert
---

# Gherkin Expert Skill

## Purpose

Provides expert-level Gherkin/BDD specification assistance for writing behavioral scenarios that clarify acceptance criteria and improve downstream code generation quality.

## When This Skill Activates

- User asks to write or review Gherkin feature files or scenarios
- User needs help structuring complex acceptance criteria
- User wants to translate business requirements into Given/When/Then format
- User asks about BDD methodology or scenario design
- User wants behavioral specifications for multi-actor or multi-step workflows
- User mentions Cucumber, SpecFlow, or BDD frameworks
- User is working on features with complex acceptance criteria that would benefit from structured scenarios

## How It Works

This skill delegates to the `gherkin-expert` agent which has knowledge of:

1. **Gherkin syntax and idioms** — Feature/Scenario/Given/When/Then, backgrounds, scenario outlines, data tables, tags
2. **BDD methodology** — discovery workshops, living documentation, specification by example
3. **Scenario design** — single-behavior focus, declarative style, avoiding implementation details
4. **Domain modeling** — ubiquitous language, bounded contexts expressed through scenarios
5. **AI prompt improvement** — using Gherkin specs as prompt context for better code generation (empirically validated: +26% over English-only)

## When Gherkin Adds Value (Judgment Call)

Gherkin is a tool, not a rule. Use judgment:

**Good fit:**

- Complex multi-step behavioral requirements with many edge cases
- Multi-actor scenarios (user does X, system responds Y, admin sees Z)
- Business rules with combinatorial conditions (scenario outlines)
- Acceptance criteria that stakeholders need to validate
- Features where "what done looks like" is ambiguous in English

**English is fine:**

- Simple CRUD operations with obvious behavior
- Internal tooling with a single developer as audience
- Config changes, styling, documentation
- Requirements where the hard part is algorithm design, not behavior specification

## Usage Examples

```
# Write scenarios for a feature
/gherkin-expert Write Gherkin scenarios for our user authentication flow

# Review existing scenarios
/gherkin-expert Review these acceptance criteria for completeness

# Translate requirements to BDD
/gherkin-expert Convert these business rules into Given/When/Then scenarios

# Decide if Gherkin is appropriate
/gherkin-expert Should I write Gherkin scenarios for this retry cascade feature?

# Improve scenarios
/gherkin-expert These scenarios feel too implementation-focused, help me make them declarative
```

## Key Resources

- Gherkin experiment results: `experiments/hive_mind/gherkin_v2_recipe_executor/`
- Issue #3939: Formal specification integration roadmap
- Gherkin reference: https://cucumber.io/docs/gherkin/reference/
