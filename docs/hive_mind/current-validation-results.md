# Current Validation Results

This page records the current verified validation snapshot for the distributed hive work and the commands used to reproduce it.

## Accepted Azure Distributed Eval Results

These are the currently accepted full Azure runs for the live `amplihive3175e` path after the final code change that fixed the late infrastructure relation follow-up issue.

| Run | Score    |
| --- | -------- |
| 1   | `98.20%` |
| 2   | `98.80%` |
| 3   | `98.23%` |

Key blocker questions that stayed fixed across the accepted set:

- `Q11 = 1.00`
- `Q12 = 1.00`
- `Q13 = 1.00`
- `Q40 = 1.00`
- `Q48 = 1.00`
- `Q49 = 1.00`
- `Q50 = 1.00`

Accepted image tag:

- `q49-infrastructure-relation-followup-20260322T064641Z`

## Current Local Validation Slices

### Main `amplihack` repo

Current wrapper-validation result:

- `64 passed`
- `ruff check` passed for the touched wrapper files

Reproduction command:

```bash
cd /path/to/amplihack

PYTHONPATH=/path/to/amplihack-agent-eval/src:/path/to/amplihack/src \
.venv/bin/python -m pytest -q tests/eval/test_long_horizon_memory.py

.venv/bin/ruff check \
  src/amplihack/eval/long_horizon_memory.py \
  src/amplihack/eval/long_horizon_multi_seed.py \
  tests/eval/test_long_horizon_memory.py
```

### `amplihack-agent-eval` repo

Current source-accurate validation result:

- `42 passed, 1 warning`
- `ruff check` passed for the touched eval files
- `bash -n run_distributed_eval.sh` passed

Reproduction command:

```bash
cd /path/to/amplihack-agent-eval

uv run --with pytest --with ruff python -m pytest -q \
  tests/test_data_generation.py \
  tests/test_datasets.py

uv run --with ruff ruff check \
  src/amplihack_eval/data/long_horizon.py \
  src/amplihack_eval/core/runner.py \
  src/amplihack_eval/core/multi_seed.py \
  src/amplihack_eval/cli.py \
  src/amplihack_eval/azure/eval_distributed.py \
  tests/test_data_generation.py \
  tests/test_datasets.py

bash -n run_distributed_eval.sh
```

### Why the eval repo reproduction uses `uv run`

In this checkout, running the same CLI integration slice through `.venv/bin/python -m pytest` can pick up a stale installed `amplihack-eval` console script and fail the `--question-set` help assertion even though the source checkout is correct.

Use `uv run` for a source-accurate reproduction, or reinstall the repo in editable mode before relying on the `amplihack-eval` console script.

## How to Reproduce the Accepted Azure Path

### Full clean rerun from source

Run from the eval repo and let the wrapper redeploy current code:

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

### Reuse an already deployed hive

```bash
cd /path/to/amplihack-agent-eval

export ANTHROPIC_API_KEY=...
export AMPLIHACK_SOURCE_ROOT=/path/to/amplihack
export SKIP_DEPLOY=1
export HIVE_NAME=amplihive3175e
export HIVE_RESOURCE_GROUP=hive-pr3175-rg

./run_distributed_eval.sh \
  --agents 100 \
  --turns 5000 \
  --questions 50 \
  --question-set standard
```

If you need to reproduce the exact accepted image rather than the latest source tree, redeploy the same image tag before launching the wrapper.
