# How to Run the Learning Eval Harness

Use this guide when you want to run the current long-horizon harness without having to rediscover which command belongs in which repo.

## Run a Local Wrapper From `amplihack`

Use the in-repo wrapper while you are changing `amplihack` runtime code.

```bash
cd /path/to/amplihack

PYTHONPATH=/path/to/amplihack-agent-eval/src:/path/to/amplihack/src \
python -m amplihack.eval.long_horizon_memory \
  --turns 100 \
  --questions 20 \
  --question-set standard \
  --sdk mini \
  --output-dir /tmp/eval-run
```

This wrapper is intentionally thin. It keeps the command surface in this repo, but it still depends on `amplihack_eval` for dataset generation and grading.

## Compare Standard and Holdout Question Sets

```bash
cd /path/to/amplihack

PYTHONPATH=/path/to/amplihack-agent-eval/src:/path/to/amplihack/src \
python -m amplihack.eval.long_horizon_multi_seed \
  --turns 100 \
  --questions 20 \
  --seeds 42,123,456 \
  --question-set holdout \
  --output-dir /tmp/eval-compare
```

Use the same runtime settings for both runs. Change only `--question-set` when you want an anti-overfitting comparison.

## Run the Distributed Azure Harness

Use the sibling eval repo for the real Azure path.

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

If the Azure hive is already live, skip the deploy step:

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

## Run the Distributed Runner Directly

Use the direct module when you already have the Event Hubs connection string and hub names.

```bash
cd /path/to/amplihack-agent-eval

python -m amplihack_eval.azure.eval_distributed \
  --connection-string "<event-hubs-connection-string>" \
  --input-hub "hive-events-amplihive3175e" \
  --response-hub "eval-responses-amplihive3175e" \
  --agents 100 \
  --agents-per-app 5 \
  --turns 5000 \
  --questions 50 \
  --question-set standard \
  --parallel-workers 1 \
  --question-failover-retries 2 \
  --answer-timeout 0 \
  --output /tmp/eval_report.json
```

## Avoid the Common Source-Checkout Trap

Because both repos use a `src/` layout, do not rely on `PYTHONPATH=src` alone when you are validating sibling checkouts.

Use both source roots explicitly:

```bash
PYTHONPATH=/path/to/amplihack-agent-eval/src:/path/to/amplihack/src
```

That prevents Python from silently importing an unrelated installed `amplihack_eval` package.

## Current Validation Snapshot

The latest accepted Azure scores and the local reproduction commands are tracked in:

- [Current validation results](../hive_mind/current-validation-results.md)

## Related Docs

- [Distributed Hive Evaluation](../hive_mind/EVAL.md)
- [Distributed Hive Eval Getting Started](../hive_mind/GETTING_STARTED.md)
- `amplihack-agent-eval/docs/distributed-hive-eval.md`
