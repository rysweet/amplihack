# How to Use the Gherkin Expert Skill

## What It Does

The `/gherkin-expert` skill helps you write Gherkin/BDD behavioral specifications that clarify acceptance criteria and improve downstream code generation quality.

## When to Use It

Use Gherkin specs when behavioral complexity is high:

- **Multi-step workflows** with many edge cases
- **Multi-actor scenarios** (user, system, admin interactions)
- **Business rules** with combinatorial conditions
- **Features** where "done" is ambiguous in English

**Don't use it** for simple CRUD, config changes, or straightforward bug fixes — English is fine.

## Quick Start

```
# Write scenarios for a feature
/gherkin-expert Write Gherkin scenarios for our user authentication flow

# Review existing acceptance criteria
/gherkin-expert Review these acceptance criteria for completeness

# Translate requirements to Given/When/Then
/gherkin-expert Convert these business rules into Gherkin scenarios

# Check if Gherkin is appropriate
/gherkin-expert Should I write Gherkin scenarios for this retry cascade feature?
```

## Example Output

The skill produces structured scenarios like:

```gherkin
Feature: User Authentication
  As a registered user
  I want to log in securely
  So that I can access my account

  Scenario: Successful login with valid credentials
    Given I am a registered user
    When I log in with valid credentials
    Then I should see my dashboard

  Scenario: Account lockout after failed attempts
    Given I am a registered user
    When I submit invalid credentials 3 times
    Then my account is locked
    And I receive a lockout notification
```

## How It Relates to TLA+

Gherkin and TLA+ are complementary formal specification tools:

| Aspect       | Gherkin                              | TLA+                                   |
| ------------ | ------------------------------------ | -------------------------------------- |
| Best for     | Behavioral requirements              | Safety invariants                      |
| Key question | "What does done look like?"          | "What must always/never be true?"      |
| Evidence     | +26% over English (behavioral tasks) | +51% over English (concurrent systems) |

The `prompt-writer` agent uses a tri-path judgment system to recommend the right specification language for each task.

## Evidence

Gherkin specifications used as prompt context produce measurably better code:

| Prompt Variant    | Average Score |
| ----------------- | ------------- |
| English only      | 0.713         |
| **Gherkin only**  | **0.898**     |
| Gherkin + English | 0.842         |

Source: N=3 agent consensus experiment, recipe step executor task. See `experiments/hive_mind/gherkin_v2_recipe_executor/`.
