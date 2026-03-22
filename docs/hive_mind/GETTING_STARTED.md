# Distributed Hive Eval Getting Started

This page is the fastest way to get from a clean checkout to a real distributed eval.

## Prerequisites

You need both repositories:

- `amplihack` - agent runtime and Azure deployment assets
- `amplihack-agent-eval` - dataset generation, distributed runner, and reports

You also need:

- Azure CLI authenticated to the target subscription
- a working Python environment in both repos
- `ANTHROPIC_API_KEY` set for grading and the default learning-agent runtime

## Local Smoke Run From This Repo

Use the thin wrapper when you are editing `amplihack` and want a fast local check.

```bash
cd /path/to/amplihack

PYTHONPATH=/path/to/amplihack-agent-eval/src:/path/to/amplihack/src \
python -m amplihack.eval.long_horizon_memory \
  --turns 100 \
  --questions 20 \
  --question-set standard \
  --output-dir /tmp/eval-run
```

## Real Azure Distributed Run

Switch to the eval repo for the end-to-end wrapper.

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

Reuse an existing deployment instead of redeploying:

```bash
SKIP_DEPLOY=1 \
HIVE_NAME=amplihive3175e \
HIVE_RESOURCE_GROUP=hive-pr3175-rg \
./run_distributed_eval.sh \
  --agents 100 \
  --turns 5000 \
  --questions 50 \
  --question-set holdout
```

## What To Expect

- the wrapper deploys or refreshes Azure Container Apps from `deploy/azure_hive/`
- agent traffic uses Event Hubs, not Service Bus
- the result bundle includes the final report JSON, logs, and rerun metadata

## Standard vs Holdout

Use `--question-set standard` for the canonical slice and `--question-set holdout` for a deterministic alternate slice.

That makes it possible to re-evaluate the same runtime against a different question subset without changing the fact-generation path.

## Where To Read Next

- [Distributed Hive Evaluation](./EVAL.md)
- [Current validation results](./current-validation-results.md)
- [How to Run the Learning Eval Harness](../howto/agent-learning-eval-harness.md)
- `amplihack-agent-eval/docs/distributed-hive-eval.md`
