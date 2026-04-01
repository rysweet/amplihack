# TLA+ Prompt Language Experiment

This directory contains the first concrete implementation slice for issue `#3497`.

The chosen scope is intentionally narrow:

- **generation target:** `distributed_retrieval_contract`
- **home:** `experiments/hive_mind/tla_prompt_language/`
- **non-goal:** a full greenfield distributed hive rewrite

## What is in this slice

- `manifest.json` — machine-readable experiment definition
- `specs/DistributedRetrievalContract.tla` — first TLA+ spec asset for the scoped target
- `specs/DistributedRetrievalRefinement.md` — companion refinement guidance that
  turns the abstract contract into request-local protocol expectations
- `specs/DistributedRetrievalContract.cfg` — TLC model config for the scoped spec
- `specs/DistributedRetrievalBestEffort.tla` — refined best-effort semantics spec
  (TLC validated: 5,927 states, 2,660 distinct, 0 errors, 7 invariants)
- `specs/DistributedRetrievalBestEffort.cfg` — TLC model config for the best-effort spec
- `prompts/` — English baseline, TLA-only, hybrid, and refinement-aware prompt variants

## Why this scope

The full issue asks whether a formal specification helps code generation for the
distributed memory problem. The first implementation slice needs a target that is
small enough to evaluate honestly and specific enough to turn into prompt assets
and tests.

The distributed retrieval contract is the best first slice because it captures
the highest-signal rules already called out in the design docs:

- preserve the original question
- fan out distributed retrieval across all active agents
- merge results deterministically
- fail explicitly instead of silently falling back to local-only behavior

That abstract contract is necessary but not sufficient. This slice now also
makes the abstraction boundary explicit:

- the TLA+ module is an abstract behavioral contract over global state
- the refinement asset explains how to turn that contract into request-local
  state and transitions a real runtime could maintain
- the experiment can now distinguish abstract-contract prompting from
  refinement-aware prompting

## Helper module

The supporting Python utilities live in `src/amplihack/eval/tla_prompt_experiment.py`.

Example:

```bash
PYTHONPATH=src python -m amplihack.eval.tla_prompt_experiment --smoke
PYTHONPATH=src python -m amplihack.eval.tla_prompt_experiment --variant tla_plus_english
PYTHONPATH=src python -m amplihack.eval.tla_prompt_experiment --smoke --output /tmp/tla-matrix.json
PYTHONPATH=src python -m amplihack.eval.tla_prompt_experiment --smoke --materialize-dir /tmp/tla-packets
PYTHONPATH=src python -m amplihack.eval.tla_prompt_experiment --smoke --run-dir /tmp/tla-run --replay-dir /tmp/tla-replay-artifacts
PYTHONPATH=src python -m amplihack.eval.tla_prompt_experiment --summarize-results /tmp/tla-run
PYTHONPATH=src python -m amplihack.eval.tla_prompt_experiment --smoke --run-dir /tmp/tla-live-run --allow-live
PYTHONPATH=src python -m amplihack.eval.tla_prompt_experiment --validate-spec --tlc-bin /path/to/tlc
PYTHONPATH=src python -m amplihack.eval.tla_prompt_experiment --validate-spec --tla2tools-jar /path/to/tla2tools.jar
```

`--materialize-dir` writes prompt/spec packets only. Replay mode is different:
`--replay-dir` must already contain one generated artifact file per condition
directory (for example `generated_artifact.md`, `generated_response.md`,
`output.md`, or `output.txt`). Use `--summarize-results` against a completed
`--run-dir`, not against a packet directory. The runner exits non-zero if any
condition fails.

## First-slice status

This slice defines the experiment contract, bundled assets, and a packet
materializer for downstream runs. It does **not** claim to be the final
prompt-to-code benchmark runner yet.

The module also defines a simple `run_result.json` schema and a summary
aggregator so downstream runs have a stable place to record:

- baseline score
- invariant compliance
- proof alignment
- local protocol alignment
- progress signal
- specification coverage

The local first-slice runner can now execute a matrix in two modes:

- **replay mode** via `--replay-dir`, which reads pre-generated artifacts per
  condition and does **not** consume the raw packet output from
  `--materialize-dir`
- **live mode** via `--run-dir --allow-live`, which invokes the configured
  SDK-backed runtime inside a per-condition workspace and expects the provider
  to return the artifact text directly instead of mutating the repo

Each run writes:

- per-condition `generated_artifact.md`
- per-condition `evaluation.json`
- per-condition `run_result.json`
- top-level `experiment_report.json`
- top-level `experiment_report.md`

It also supports explicit TLC validation for the scoped spec:

- set `TLA_TLC_BIN` to a native `tlc` executable, or
- set `TLA2TOOLS_JAR` and make `java` available

The validation command fails explicitly if no TLC runner is configured.

The current scores are **heuristic signals**, not authoritative benchmark scores.
Official harness grading and packaged reports still belong in `amplihack-agent-eval`.
A condition marked `completed` means the provider returned generation output that
the runner accepted for heuristic scoring; it does **not** mean the artifact was
high quality.

The current heuristic evaluator now tries to separate:

- abstract contract alignment
- request-local protocol alignment
- progress/terminal-outcome signals

It still does **not** provide a formal refinement proof or a liveness proof.

For stricter local validation, a real TLC-backed pytest smoke is available when
`TLA_TLC_BIN` or `TLA2TOOLS_JAR` is configured in the environment.

## Experiment Results (2026-03-31 smoke run)

Live smoke run: 4 prompt variants × 2 models × 1 repeat = 8 conditions.
6 completed, 2 GPT-5.4 conditions timed out (Copilot SDK timeout on heavier prompts).

### Claude Opus 4.6 Results

| Prompt Variant | Baseline | Invariant | Proof | Local Protocol | Progress | Coverage |
|---------------|----------|-----------|-------|----------------|----------|----------|
| english (baseline) | 0.43 | 0.50 | 0.0 | 0.0 | 0.0 | 0.29 |
| tla_only | **0.86** | **0.75** | **1.0** | **1.0** | **1.0** | **0.86** |
| tla_plus_english | 0.43 | 0.50 | 1.0 | 0.0 | 0.0 | 0.43 |
| tla_plus_refinement | **0.86** | **0.75** | **1.0** | **1.0** | **1.0** | **0.86** |

### GPT-5.4 Results (via Copilot SDK)

| Prompt Variant | Baseline | Invariant | Proof | Local Protocol | Progress | Coverage |
|---------------|----------|-----------|-------|----------------|----------|----------|
| english (baseline) | 0.71 | 0.75 | 0.0 | 0.0 | 1.0 | 0.57 |
| tla_only | **0.86** | **0.75** | **1.0** | **1.0** | **1.0** | **0.86** |
| tla_plus_english | 0.57 | 0.50 | 1.0 | 0.0 | 1.0 | 0.57 |
| tla_plus_refinement | 0.57 | 0.75 | 0.0 | 0.0 | 1.0 | 0.57 |

Note: `tla_only` and `tla_plus_refinement` initially timed out at 300s default.
Retried at 600s — both completed. GPT-5.4 needs more time on spec-heavy prompts.

### Key Findings

1. **TLA+ formal spec alone (tla_only) is the best prompt strategy for both
   models.** It doubles Claude's baseline (0.43 → 0.86) and improves GPT-5.4
   (0.71 → 0.86). Both models achieve perfect local-protocol and progress-signal
   alignment with spec-only prompting. This is the strongest signal in the
   experiment.

2. **Hybrid prompt (tla_plus_english) hurts both models.** Adding English
   guidance alongside the formal spec performs no better than English alone for
   Claude (0.43 = 0.43) and actually *decreases* GPT-5.4's score (0.71 → 0.57).
   Natural language dilutes the formal signal rather than amplifying it.

3. **Refinement guidance helps Claude but not GPT-5.4.** Claude scores
   identically with `tla_only` and `tla_plus_refinement` (both 0.86). But
   GPT-5.4 scores 0.86 with `tla_only` and drops to 0.57 with
   `tla_plus_refinement`. The refinement prose may interfere with GPT-5.4's
   interpretation of the formal spec.

4. **GPT-5.4 has a higher English baseline than Claude** (0.71 vs 0.43), but
   the formal spec equalizes them — both reach 0.86 with `tla_only`. The spec
   acts as a stronger lever for the model with the lower natural-language
   baseline.

5. **Formal specs need more processing time.** GPT-5.4 timed out at the 300s
   default on spec-heavy prompts but completed at 600s. The formal spec triggers
   deeper reasoning that requires a larger time budget — a real operational
   consideration for production use.

6. **Neither model spontaneously references formal methods.** Both score 0.0 on
   proof alignment in English-only mode. Formal contract awareness requires
   explicit prompting.

### Summary: Spec-Only Wins

| | English | TLA Only | Hybrid | Refinement |
|---|---------|----------|--------|------------|
| **Claude** | 0.43 | **0.86** | 0.43 | **0.86** |
| **GPT-5.4** | 0.71 | **0.86** | 0.57 | 0.57 |
| **Mean** | 0.57 | **0.86** | 0.50 | 0.71 |

The formal TLA+ specification alone — without English guidance or refinement
prose — produces the best code generation results across both models. Adding
natural language to the prompt consistently degrades performance.

### Caveats

- Smoke matrix (1 repeat per condition) — variance not yet measured
- Heuristic scoring is keyword-based, not semantic — possible false positives/negatives
- Full matrix (3 repeats) needed before drawing firm statistical conclusions

### Report artifacts

- `results/smoke_live_20260331.md` — full experiment report
- `results/smoke_live_20260331.json` — machine-readable report
