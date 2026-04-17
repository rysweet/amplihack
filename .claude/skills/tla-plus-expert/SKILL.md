---
name: tla-plus-expert
version: 1.0.0
description: TLA+ formal specification expert for writing specs, model checking, and applying formal methods to amplihack workflows
activation_keywords:
  - "TLA+"
  - "TLA"
  - "formal specification"
  - "formal spec"
  - "model checking"
  - "model checker"
  - "TLC"
  - "PlusCal"
  - "invariant"
  - "liveness property"
  - "safety property"
  - "temporal logic"
  - "state machine spec"
  - "protocol verification"
agent: amplihack:specialized:tla-plus-expert
---

# TLA+ Expert Skill

## Purpose

Provides expert-level TLA+ formal specification assistance for designing, verifying, and reasoning about concurrent and distributed systems within amplihack.

## When This Skill Activates

- User asks to write or review a TLA+ specification
- User needs help with model checking (TLC) configuration or output interpretation
- User wants to formally verify a protocol or workflow design
- User asks about invariants, liveness properties, or safety properties
- User wants to apply formal methods to amplihack components
- User mentions PlusCal or wants to translate between PlusCal and TLA+
- User references Lamport, Demirbas, or formal methods best practices

## How It Works

This skill delegates to the `tla-plus-expert` agent which has deep knowledge of:

1. **TLA+ language and idioms** — writing specs, operators, temporal formulas
2. **TLC model checker** — configuration, trace interpretation, state space management
3. **Seven mental models** (Demirbas) — abstraction, global shared memory, local guards, invariants, stepwise refinement, atomicity refinement, communication
4. **Industry case studies** — 8 production uses from AWS, MongoDB, Microsoft Azure
5. **AI + TLA+ limitations** — SysMoBench findings on LLM capabilities and guardrails
6. **amplihack experiment infrastructure** — manifest-driven experiments, heuristic scoring, TLC validation integration

## Integration with Existing Infrastructure

The amplihack repo includes a TLA+ experiment runner at `crates/amplihack-eval/src/tla_prompt_experiment.rs` with:

- Manifest-driven experiment matrix (models x prompt variants x repeats)
- 6 heuristic scoring dimensions
- Real TLC validation support
- Replay and live execution modes

TLA+ specs live in `experiments/hive_mind/tla_prompt_language/specs/`.

## Usage Examples

```
# Write a spec for a new protocol
/tla-plus-expert Write a TLA+ spec for our consensus voting workflow

# Review an existing spec
/tla-plus-expert Review specs/SmartOrchestrator.tla for correctness

# Help with TLC output
/tla-plus-expert TLC found a counterexample in my spec, help me understand it

# Decide if TLA+ is appropriate
/tla-plus-expert Should I formally specify this retry cascade logic?

# Generate invariants
/tla-plus-expert What invariants should I check for a parallel workstream manager?
```

## Key Resources

- TLA+ specs: `experiments/hive_mind/tla_prompt_language/specs/`
- Experiment runner: `crates/amplihack-eval/src/tla_prompt_experiment.rs`
- TLC binary: `/usr/local/bin/tlc` (if installed)
- Issue #3939: TLA+ integration roadmap
