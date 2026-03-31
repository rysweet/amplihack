# Gherkin/BDD Prompt Language Experiment

**Experiment ID**: `gherkin-prompt-language-v1`
**Status**: Active
**Related**: Issue #3497 (TLA+ experiment), Issue #3939 (TLA+ integration roadmap)

## Hypothesis

Gherkin Given/When/Then specifications improve code generation quality for
behavioral/feature tasks the same way TLA+ specifications improve it for
concurrent/state tasks (ref: #3497, where TLA+ doubled baseline from 0.57 to
0.86).

## Generation Target

**User Authentication REST API** — a feature-oriented task with:

- Registration with email/password validation
- Login with JWT access tokens and refresh tokens
- Account lockout after 5 failed attempts
- Protected resource access with token validation
- Password hashing (bcrypt)

This target was chosen because it is representative of common feature
development work: CRUD + security + error handling + tests.

## Prompt Variants

| Variant                   | Description                                 | Spec Appended? |
| ------------------------- | ------------------------------------------- | -------------- |
| `english`                 | Natural language requirements only          | No             |
| `gherkin_only`            | Minimal instructions + Gherkin feature file | Yes            |
| `gherkin_plus_english`    | English guidance + Gherkin scenarios        | Yes            |
| `gherkin_plus_acceptance` | Acceptance criteria + Gherkin scenarios     | Yes            |

## Scoring Dimensions

Heuristic keyword-based scoring (same approach as TLA+ experiment):

| Dimension              | What It Measures                                    | Check Count |
| ---------------------- | --------------------------------------------------- | ----------- |
| `scenario_coverage`    | All 12 behavioral scenarios addressed               | 12 checks   |
| `edge_case_handling`   | 7 error/negative scenarios handled                  | 7 checks    |
| `step_implementation`  | Real code, not stubs                                | 1 check     |
| `test_generation`      | Tests matching scenarios exist                      | 1 check     |
| `behavioral_alignment` | Composite of coverage + implementation + edge cases | Composite   |

## Running

```bash
# Print smoke matrix
PYTHONPATH=src python -m amplihack.eval.gherkin_prompt_experiment --smoke

# Materialize packets only
PYTHONPATH=src python -m amplihack.eval.gherkin_prompt_experiment --smoke --materialize-dir /tmp/packets

# Run with live model generation
PYTHONPATH=src python -m amplihack.eval.gherkin_prompt_experiment --smoke --run-dir /tmp/results --allow-live

# Run with replay artifacts
PYTHONPATH=src python -m amplihack.eval.gherkin_prompt_experiment --smoke --run-dir /tmp/results --replay-dir /tmp/packets

# Print a single variant's combined prompt
PYTHONPATH=src python -m amplihack.eval.gherkin_prompt_experiment --variant gherkin_only
```

## Tests

```bash
PYTHONPATH=src python -m pytest tests/eval/test_gherkin_prompt_experiment.py -v
```

## Design Decisions

1. **Separate module, shared infrastructure**: `gherkin_prompt_experiment.py`
   imports common data structures from `tla_prompt_experiment.py` but provides
   its own `evaluate_gherkin_artifact()`. This avoids polluting TLA+ scoring
   with unrelated heuristics.

2. **Reused manifest schema**: Same JSON schema as TLA+. The `spec_asset` field
   points to a `.feature` file instead of a `.tla` file. The `append_spec`
   mechanism works identically.

3. **Metric field reuse**: `ConditionMetrics` fields are reused with different
   semantics (documented in report headers). This allows reusing the entire
   reporting/summarization infrastructure without code changes.

4. **User authentication target**: Chosen over alternatives (shopping cart, todo
   API) because it has the highest density of error scenarios, security
   requirements, and behavioral edge cases per endpoint.
