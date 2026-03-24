# Distributed Hive Evaluation

This repo owns the **agent/runtime side** of the distributed eval story.

- `deploy/azure_hive/` contains the Azure Container Apps and Event Hubs deployment assets
- `src/amplihack/eval/long_horizon_memory.py` is the thin local wrapper used from this repo
- `src/amplihack/eval/long_horizon_multi_seed.py` is the thin multi-seed wrapper used from this repo

The authoritative long-horizon dataset generator and Azure distributed runner live in the sibling `amplihack-agent-eval` repo.

## Read This Next

- [Day-zero operator guide](./EVAL_OPERATOR_GUIDE.md) — exact commands for local wrappers, the eval CLI, Azure distributed runs, and Aspire flows
- [How the eval stack fits together](./EVAL_COMPONENTS.md) — five-minute walkthrough of repo ownership, local versus distributed paths, Event Hubs, Container Apps, why Aspire is in C#, and how `EH_CONN` reaches runners without going through `argv`

## Use This Repo For

- changing the agent runtime
- changing the Azure deployment shape
- running the thin local wrappers while you are editing `amplihack`

## Use `amplihack-agent-eval` For

- authoritative long-horizon question generation
- the Event Hubs distributed runner
- packaged eval reports and rerun metadata
- the end-to-end `run_distributed_eval.sh` wrapper

## Local Wrapper: Single Run

The wrapper in this repo delegates to `amplihack_eval`, so include both repos on `PYTHONPATH` when you are testing sibling checkouts.

```bash
PYTHONPATH=/path/to/amplihack-agent-eval/src:/path/to/amplihack/src \
python -m amplihack.eval.long_horizon_memory \
  --turns 100 \
  --questions 20 \
  --output-dir /tmp/eval-run
```

Useful flags from this wrapper:

- `--sdk {mini,claude,copilot,microsoft}`
- `--memory-type {auto,hierarchical,cognitive}`
- `--answer-mode {single-shot,agentic}`
- `--parallel-workers`
- `--load-db` and `--skip-learning`

If you need `standard` versus `holdout` question slices, use the `amplihack-agent-eval` CLI or distributed runner rather than the thin wrappers in this repo.

## Local Wrapper: Multi-Seed Comparison

```bash
PYTHONPATH=/path/to/amplihack-agent-eval/src:/path/to/amplihack/src \
python -m amplihack.eval.long_horizon_multi_seed \
  --turns 100 \
  --questions 20 \
  --seeds 42,123,456,789 \
  --output-dir /tmp/eval-compare
```

## Distributed Azure Run

For real Azure distributed runs, switch to the sibling `amplihack-agent-eval` repo and use its wrapper or direct runner.

```bash
cd /path/to/amplihack-agent-eval

export ANTHROPIC_API_KEY=...
export AMPLIHACK_SOURCE_ROOT=/path/to/amplihack

./run_distributed_eval.sh \
  --agents 100 \
  --turns 5000 \
  --questions 50 \
  --question-set standard
```

That path drives the Azure deployment assets from this repo, but the harness and reporting stay centralized in `amplihack-agent-eval`.

## Question Sets

| Value      | Meaning                                                       |
| ---------- | ------------------------------------------------------------- |
| `standard` | Canonical deterministic question slice                        |
| `holdout`  | Alternate deterministic slice for anti-overfitting validation |

`holdout` changes which questions are asked. It does not generate a second fact universe.

## Important Checkout Note

This repo uses a `src/` layout. If you run the wrappers with only `PYTHONPATH=src`, Python may resolve a globally installed `amplihack_eval` instead of the sibling checkout you are editing. Include both source roots explicitly when validating local changes.

## Current Verified Results

A current validation snapshot, including the accepted Azure scores and the latest reproducible local test commands, lives here:

- [Current validation results](./current-validation-results.md)

## Related Docs

- [Day-zero operator guide](./EVAL_OPERATOR_GUIDE.md)
- [How the eval stack fits together](./EVAL_COMPONENTS.md)
- `amplihack-agent-eval/docs/distributed-hive-eval.md`
- `amplihack-agent-eval/docs/running-evals.md`
- [Getting Started](./GETTING_STARTED.md)
- [How to Run the Learning Eval Harness](../howto/agent-learning-eval-harness.md)
