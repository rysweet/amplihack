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
